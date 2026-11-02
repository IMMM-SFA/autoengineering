"""Owned Claude composition with authored CLI/JSON and loopback traffic only."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import pytest

from autoengineering.agents.hosts.base import InvocationContext
from autoengineering.agents.hosts.claude import ClaudeInventory, REQUIRED_FLAGS, SUPPORTED_VERSION
from autoengineering.agents.hosts.claude_brokered import (
    capture_claude_endpoint_stop,
    execute_brokered_claude,
    recover_brokered_claude,
)
from autoengineering.agents.hosts.codex_brokered import WrappedCommand
from autoengineering.campaign.serialization import canonical_json
from test_agent_claude import MODEL, document

PROMPT = "approved role evidence"
INNER = '{"role":"reviewer","fixture":true}'


def setup(tmp_path, *, mode="normal", missing_cache=False, response_updates=None):
    tmp_path.chmod(0o700)
    executable = tmp_path / "authored-claude"
    executable.write_text(f"""#!{Path(sys.executable).resolve()}
import http.client,json,shlex,subprocess,sys,time
from urllib.parse import urlsplit
prompt=sys.stdin.read()
assert prompt=={PROMPT!r}
settings=json.loads(sys.argv[sys.argv.index('--settings')+1])
token=subprocess.run(shlex.split(settings['apiKeyHelper']),capture_output=True,check=True).stdout.strip().decode()
if {mode!r}=='timeout': time.sleep(10)
base=urlsplit(settings['env']['ANTHROPIC_BASE_URL'])
assert base.hostname=='127.0.0.1'
connection=http.client.HTTPConnection(base.hostname,base.port,timeout=3)
connection.request('POST','/v1/messages?beta=true',body=json.dumps({{
 'model':{MODEL!r},'stream':True,'messages':[{{'role':'user','content':prompt}}],
 'system':'native context must not escape',
}}).encode(),headers={{'x-api-key':token,'Content-Type':'application/json'}})
response=connection.getresponse(); raw=response.read(); connection.close()
if response.status!=200:
 print('native refused response'); sys.exit(1)
events=[json.loads(line[6:]) for line in raw.decode().splitlines() if line.startswith('data: ')]
payload=[event['delta']['partial_json'] for event in events if event['type']=='content_block_delta']
result={document()!r}
result['structured_output']=json.loads(''.join(payload))
if {mode!r}=='mismatch': result['structured_output']={{'handoff_json':'different'}}
print(json.dumps(result))
""")
    executable.chmod(0o700)
    inventory = ClaudeInventory(
        str(executable),
        hashlib.sha256(executable.read_bytes()).hexdigest(),
        SUPPORTED_VERSION,
        REQUIRED_FLAGS,
    )
    calls, launches = [], []
    state = {"cancelled": False}
    usage = {"input_tokens": 7, "output_tokens": 10}
    if not missing_cache:
        usage.update(cache_read_input_tokens=2, cache_creation_input_tokens=3)
    response = {
        "id": "msg_owned_composition",
        "type": "message",
        "role": "assistant",
        "model": MODEL,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "content": [{"type": "text", "text": canonical_json({"handoff_json": INNER})}],
        "usage": usage,
    } | (response_updates or {})

    def upstream(raw):
        request = json.loads(raw)
        assert request["messages"] == [
            {"role": "user", "content": [{"type": "text", "text": PROMPT}]}
        ]
        assert request["tools"] == [] and request["stream"] is False
        assert b"native context must not escape" not in raw
        calls.append(raw)
        if mode == "upstream-failure":
            raise RuntimeError("authored uncertain transport")
        if mode == "cancel":
            state["cancelled"] = True
        return canonical_json(response).encode()

    def launched(identity):
        root = tmp_path / "transport"
        assert (root / "job-binding.json").exists()
        # The identity is still held behind the process supervisor's launch gate.
        assert not (root / "client/launch-gate.json").exists()
        launches.append(identity)

    def wrapper(command, endpoint, helper, capability):
        assert helper.parent == capability.parent
        assert capability.read_text() == endpoint.bootstrap_token
        policy = tmp_path / "authored-policy.txt"
        policy.write_text("authored identity wrapper; not an OS boundary")
        return WrappedCommand(command, policy)

    options = dict(
        model=MODEL,
        prompt=PROMPT,
        context=InvocationContext(
            "call-one",
            "owned-claude",
            tmp_path / "transport",
            4,
            65536,
            launched,
            lambda: state["cancelled"],
        ),
        upstream=upstream,
        boundary_identity="f" * 64,
        max_output_tokens=512,
        estimated_budget_usd=0.1,
        wrap_command=wrapper,
    )
    return inventory, options, calls, launches


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("missing_cache", [False, True])
@pytest.mark.parametrize("lost_ack", [False, True])
def test_owned_roundtrip_and_saved_recovery_use_broker_usage(tmp_path, missing_cache, lost_ack):
    inventory, options, calls, launches = setup(tmp_path, missing_cache=missing_cache)

    def fault(stage):
        assert stage == "before_outcome_commit"
        raise RuntimeError("lost acknowledgement")

    if lost_ack:
        with pytest.raises(RuntimeError, match="acknowledgement"):
            execute_brokered_claude(inventory, **options, fault=fault)
    else:
        result = execute_brokered_claude(inventory, **options)
        assert result.host_result.status == "completed" and result.host_result.stop_verified
    root = options["context"].directory
    before = snapshot(root)
    recovered = recover_brokered_claude(root)
    assert snapshot(root) == before
    host = recovered.host_result
    assert host.status == "completed" and host.stop_verified
    assert json.loads(host.raw_output) == {"handoff_json": INNER}
    assert host.usage["total_tokens"] == (None if missing_cache else 22)
    assert host.usage["output_tokens"] == 10
    assert recovered.native.parsed.usage["total_tokens"] == 14
    assert recovered.native.parsed.estimated_cost_usd == 0.01
    assert len(calls) == len(launches) == 1
    with pytest.raises(FileExistsError):
        execute_brokered_claude(inventory, **options)
    assert len(calls) == len(launches) == 1


@pytest.mark.parametrize(
    "mode,updates",
    [
        ("mismatch", {}),
        ("normal", {"model": "claude-unrequested"}),
        ("normal", {"stop_reason": "max_tokens"}),
        ("normal", {"content": [{"type": "tool_use", "name": "Read", "input": {}}]}),
        ("upstream-failure", {}),
    ],
)
def test_refused_native_or_broker_output_never_becomes_handoff(tmp_path, mode, updates):
    inventory, options, calls, launches = setup(tmp_path, mode=mode, response_updates=updates)
    result = execute_brokered_claude(inventory, **options)
    assert result.host_result.status != "completed" and result.host_result.raw_output == ""
    assert result.host_result.stop_verified
    before = snapshot(result.root)
    recovered = recover_brokered_claude(result.root)
    assert recovered.host_result == result.host_result
    assert snapshot(result.root) == before and len(calls) == len(launches) == 1
    if mode != "upstream-failure":
        assert recovered.host_result.usage["total_tokens"] == 22


@pytest.mark.parametrize("mode", ["timeout", "cancel"])
def test_interruption_preserves_stops_and_never_retries(tmp_path, mode):
    inventory, options, calls, launches = setup(tmp_path, mode=mode)
    if mode == "timeout":
        options["context"] = replace(options["context"], timeout_seconds=0.8)
    result = execute_brokered_claude(inventory, **options)
    assert result.host_result.status == ("timeout" if mode == "timeout" else "cancelled")
    assert result.host_result.stop_verified and len(launches) == 1
    assert len(calls) == (0 if mode == "timeout" else 1)
    assert recover_brokered_claude(result.root).host_result == result.host_result


@pytest.mark.parametrize(
    "path",
    [
        "prompt.txt",
        "auth/helper",
        "auth/capability",
        "workspace/schema.json",
        "endpoint/endpoint.json",
        "client/job.json",
        "job-binding.json",
        "timing.json",
        "stops/000001.json",
        "outcome.json",
    ],
)
def test_changed_original_evidence_cannot_recover(tmp_path, path):
    inventory, options, calls, _ = setup(tmp_path)
    result = execute_brokered_claude(inventory, **options)
    (result.root / path).write_text("{}")
    with pytest.raises((ValueError, KeyError)):
        recover_brokered_claude(result.root)
    assert len(calls) == 1


def test_prelaunch_cancel_stops_endpoint_without_a_native_or_upstream_call(tmp_path):
    inventory, options, calls, launches = setup(tmp_path)
    options["context"] = replace(options["context"], cancelled=lambda: True)
    result = execute_brokered_claude(inventory, **options)
    assert result.host_result.status == "cancelled" and result.host_result.stop_verified
    assert calls == launches == []
    assert recover_brokered_claude(result.root).host_result == result.host_result


def test_damaged_transport_binding_still_closes_owned_endpoint(tmp_path):
    inventory, options, _calls, _launches = setup(tmp_path)

    def damage(_identity):
        (options["context"].directory / "transport.json").write_text('{}')

    options["context"] = replace(options["context"], on_launch=damage)
    with pytest.raises(ValueError, match="identity"):
        execute_brokered_claude(inventory, **options)
    root = options["context"].directory
    saved = json.loads((root / "endpoint/stop-000001.json").read_text())
    assert saved["listener_closed"] and saved["handler_stopped"]
    assert saved["upstream_callback_stopped"]
    assert list((root / "stops").iterdir()) == []


def test_later_bound_stop_appends_without_rewriting_original_outcome(tmp_path):
    inventory, options, calls, launches = setup(tmp_path)
    result = execute_brokered_claude(inventory, **options)
    before = snapshot(result.root)
    capture_claude_endpoint_stop(result.root, result.endpoint)
    assert all((result.root / path).read_bytes() == raw for path, raw in before.items())
    assert (result.root / "stops/000002.json").exists()
    assert recover_brokered_claude(result.root).host_result == result.host_result
    assert len(calls) == len(launches) == 1
