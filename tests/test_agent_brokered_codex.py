"""Version 2 transport using a trusted executable and authored local responses."""

from __future__ import annotations

import json
import shutil
import sys
import threading
import time

import pytest

from autoengineering.agents.hosts.base import InvocationContext
from autoengineering.agents.hosts.codex_brokered import (
    BROKERED_FLAGS,
    WrappedCommand,
    capture_endpoint_stop,
    execute_brokered_codex,
    inspect_brokered_codex,
    recover_brokered_transport,
)
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL, response_stream

PROMPT = b"approved brokered prompt"


def program(root, mode="normal"):
    path = root / "fake-codex"
    source = f"""#!{sys.executable}
import json,os,sys,time,urllib.request
from pathlib import Path
if sys.argv[1:]==['--version']:
 print('codex-cli 0.164.0')
elif sys.argv[1:]==['exec','--help']:
 print({" ".join(BROKERED_FLAGS)!r})
else:
 assert '--sandbox' not in sys.argv
 assert '--dangerously-bypass-approvals-and-sandbox' in sys.argv
 assert not os.environ.get('OPENAI_API_KEY')
 assert not (Path(os.environ['CODEX_HOME'])/'auth.json').exists()
 options=dict(sys.argv[i+1].split('=',1) for i,v in enumerate(sys.argv) if v=='-c')
 assert options['model_providers.bounded_text.requires_openai_auth']=='false'
 assert options['model_providers.bounded_text.request_max_retries']=='0'
 prompt=sys.stdin.read()
 mode={mode!r}
 if mode=='sleep':
  Path(__file__).with_name('native-started').touch()
  time.sleep(5)
 if mode!='no_source':
  model=sys.argv[sys.argv.index('--model')+1]
  url=json.loads(options['model_providers.bounded_text.base_url'])+'/responses'
  request=json.dumps({{'model':model,'stream':True,'input':[{{'type':'message','role':'user','content':[{{'type':'input_text','text':prompt}}]}}]}}).encode()
  with urllib.request.urlopen(urllib.request.Request(url,data=request),timeout=5) as response:
   stream=response.read().decode()
  completed=[json.loads(line[6:]) for line in stream.splitlines() if line.startswith('data: ')][-1]['response']
  text=''.join(p['text'] for i in completed['output'] for p in i.get('content',[]))
 else:text='{{"ok":true}}'
 if mode=='after_source_sleep':time.sleep(5)
 if mode=='lie':text='{{"different":true}}'
 if mode=='partial':print('{{partial');sys.exit(0)
 if mode=='flood':print('x'*100000);sys.exit(0)
 for event in [{{'type':'thread.started','thread_id':'fixture'}},{{'type':'turn.started'}},
  {{'type':'item.completed','item':{{'type':'agent_message','text':text}}}},
  {{'type':'turn.completed','usage':{{'input_tokens':1,'output_tokens':1,'cached_input_tokens':0}}}}]:print(json.dumps(event))
"""
    path.write_text(source)
    path.chmod(0o700)
    return path


def prepare(
    tmp_path, *, mode="normal", seconds=3, launched=lambda _: None, cancelled=lambda: False
):
    tmp_path.mkdir(mode=0o700, exist_ok=True)
    tmp_path.chmod(0o700)
    for name in ("workspace", "home"):
        (tmp_path / name).mkdir(mode=0o700)
    schema = tmp_path / "workspace/schema.json"
    schema.write_text('{"type":"object"}')
    inventory = inspect_brokered_codex(program(tmp_path, mode))
    context = InvocationContext(
        "call-one", "bridge-nonce", tmp_path / "transport", seconds, 65536, launched, cancelled
    )
    return dict(
        inventory=inventory,
        model=OFFLINE_MODEL,
        schema=schema,
        workspace=tmp_path / "workspace",
        home=tmp_path / "home",
        prompt=PROMPT,
        context=context,
        boundary_identity="0" * 64,
        # Trusted fixture only. This is not an OS boundary qualification.
        wrap_command=lambda command, _endpoint: command,
    )


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_explicit_catalog_is_pinned_and_changed_client_copy_blocks_recovery(tmp_path):
    catalog = json.dumps(
        {"models": [{"slug": OFFLINE_MODEL, "description": "catalog-canary"}]}
    ).encode()
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream()

    result = execute_brokered_codex(**prepare(tmp_path), model_catalog=catalog, upstream=upstream)
    assert result.host_result.status == "completed"
    assert len(calls) == 1 and b"catalog-canary" not in calls[0]
    assert recover_brokered_transport(result.root).host_result.status == "completed"
    (tmp_path / "home/model-catalog.json").write_bytes(catalog.replace(b"canary", b"changed"))
    with pytest.raises(ValueError, match="catalog changed"):
        recover_brokered_transport(result.root)


def test_complete_transport_and_readonly_recovery_bind_all_three_layers(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-credential-never-forward")
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream()

    def launched(_receipt):
        assert (tmp_path / "transport/transport.json").is_file()
        assert not calls

    result = execute_brokered_codex(**prepare(tmp_path, launched=launched), upstream=upstream)
    assert result.host_result.status == "completed"
    assert result.host_result.raw_output == '{"ok":true}'
    assert result.host_result.resolved_model == OFFLINE_MODEL
    assert result.host_result.usage["total_tokens"] == 2
    assert result.endpoint_stop.upstream_callbacks == 1 and len(calls) == 1
    before = snapshot(result.root)
    recovered = recover_brokered_transport(result.root)
    assert recovered.host_result == result.host_result
    assert before == snapshot(result.root) and len(calls) == 1
    assert b"ambient-credential" not in b"".join(before.values())


@pytest.mark.parametrize("mode", ["lie", "partial", "flood"])
def test_client_cannot_replace_broker_output_or_hide_its_usage(tmp_path, mode):
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream()

    result = execute_brokered_codex(**prepare(tmp_path, mode=mode), upstream=upstream)
    assert result.host_result.status == "host_failure" and result.host_result.raw_output == ""
    assert result.host_result.usage["total_tokens"] == 2 and len(calls) == 1
    assert result.host_result.stop_verified


def test_native_completion_without_a_provider_response_remains_unreconciled(tmp_path):
    result = execute_brokered_codex(
        **prepare(tmp_path, mode="no_source"), upstream=lambda _: pytest.fail("unexpected callback")
    )
    assert result.host_result.status == "reconciliation_required"
    assert not result.host_result.raw_output
    assert result.exchange_result.provider_requests_reserved == 0


def test_callback_acknowledgment_failure_is_recoverable_without_launch_or_provider(tmp_path):
    def fail(_receipt):
        raise OSError("launch acknowledgment loss")

    args = prepare(tmp_path, launched=fail)
    with pytest.raises(OSError, match="acknowledgment"):
        execute_brokered_codex(**args, upstream=lambda _: pytest.fail("unexpected callback"))
    recovered = recover_brokered_transport(tmp_path / "transport")
    assert recovered.host_result.status == "host_failure"
    assert recovered.exchange_result.provider_requests_reserved == 0


def test_lost_final_acknowledgment_replays_saved_native_and_provider_bytes(tmp_path):
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream()

    def fault(_stage):
        raise OSError("final acknowledgment loss")

    with pytest.raises(OSError, match="final acknowledgment"):
        execute_brokered_codex(**prepare(tmp_path), upstream=upstream, fault=fault)
    root = tmp_path / "transport"
    before = snapshot(root)
    assert recover_brokered_transport(root).host_result.status == "completed"
    assert before == snapshot(root) and len(calls) == 1


def test_whole_deadline_includes_prelaunch_preparation(tmp_path):
    args = prepare(tmp_path, seconds=0.1)

    def delayed(command, _endpoint):
        time.sleep(0.15)
        return command

    args["wrap_command"] = delayed
    result = execute_brokered_codex(**args, upstream=lambda _: pytest.fail("expired call"))
    assert result.native.identity is None
    assert result.host_result.status == "timeout"
    assert result.endpoint_stop.upstream_callbacks == 0


def test_queued_cancellation_does_not_start_client_or_upstream(tmp_path):
    result = execute_brokered_codex(
        **prepare(tmp_path, cancelled=lambda: True),
        upstream=lambda _: pytest.fail("cancelled call"),
    )
    assert result.host_result.status == "cancelled" and result.native.identity is None
    assert result.endpoint_stop.upstream_callbacks == 0 and result.host_result.stop_verified


def test_active_callback_stop_remains_pending_then_resolves_without_another_call(tmp_path):
    started, release = threading.Event(), threading.Event()
    calls = []

    def upstream(raw):
        calls.append(raw)
        started.set()
        assert release.wait(timeout=5)
        return response_stream()

    result = None
    try:
        result = execute_brokered_codex(**prepare(tmp_path, seconds=0.3), upstream=upstream)
        assert started.is_set()
        assert result.host_result.status == "reconciliation_required"
        assert not result.host_result.stop_verified
        original = (result.root / "transport-outcome.json").read_bytes()
    finally:
        release.set()
        if result is not None:
            capture_endpoint_stop(result.root, result.endpoint, wait_seconds=2)
    assert len(calls) == 1
    recovered = recover_brokered_transport(result.root)
    assert recovered.host_result.status == "timeout" and recovered.host_result.stop_verified
    assert recovered.host_result.usage["total_tokens"] == 2
    assert (result.root / "transport-outcome.json").read_bytes() == original


def test_provider_usage_unknown_fields_are_not_replaced_by_client_zeroes(tmp_path):
    raw = response_stream().replace(b'"input_tokens_details":{"cached_tokens":0},', b"")
    result = execute_brokered_codex(**prepare(tmp_path), upstream=lambda _: raw)
    assert result.host_result.status == "completed"
    assert result.host_result.usage["cached_input_tokens"] is None
    assert b'"cached_input_tokens": 0' in result.native.stdout


def test_cross_transport_native_receipts_and_corrupted_stop_capture_are_rejected(tmp_path):
    a = execute_brokered_codex(**prepare(tmp_path / "a"), upstream=lambda _: response_stream())
    b = execute_brokered_codex(**prepare(tmp_path / "b"), upstream=lambda _: response_stream())
    for path in (b.root / "client").iterdir():
        if path.is_file():
            shutil.copyfile(path, a.root / "client" / path.name)
    with pytest.raises(ValueError, match="binding mismatch"):
        recover_brokered_transport(a.root)
    capture = next((b.root / "stops").glob("*.json"))
    value = json.loads(capture.read_text())
    value["transport_sha256"] = "0" * 64
    capture.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="stop binding"):
        recover_brokered_transport(b.root)


def test_declared_boundary_bytes_are_retained_and_mutation_rejects_success(tmp_path):
    args = prepare(tmp_path)
    policy = tmp_path / "boundary.sb"
    policy.write_text("authored fixture policy")
    # Trusted fixture: records policy provenance, but makes no OS-boundary claim.
    args["wrap_command"] = lambda command, _: WrappedCommand(command, policy)

    def upstream(_request):
        policy.write_text("changed policy")
        return response_stream()

    result = execute_brokered_codex(**args, upstream=upstream)
    assert result.host_result.status == "host_failure"
    assert (
        next(result.root.glob("artifacts/*/boundary-policy.sb")).read_text()
        == "authored fixture policy"
    )
    assert recover_brokered_transport(result.root).host_result.status == "host_failure"


def test_original_outcome_status_cannot_be_relabelled(tmp_path):
    result = execute_brokered_codex(**prepare(tmp_path), upstream=lambda _: response_stream())
    path = result.root / "transport-outcome.json"
    saved = json.loads(path.read_text())
    saved["status"] = "cancelled"
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="contradicts evidence"):
        recover_brokered_transport(result.root)


def test_cross_run_exchange_cannot_replace_the_same_logical_call(tmp_path):
    a = execute_brokered_codex(**prepare(tmp_path / "a"), upstream=lambda _: response_stream())
    b = execute_brokered_codex(**prepare(tmp_path / "b"), upstream=lambda _: response_stream())
    # Even the trusted fixture reuses its logical call ID and nonce. The two
    # physical invocation directories must still have different exchange IDs.
    for path in (b.root / "exchange").rglob("*"):
        target = a.root / "exchange" / path.relative_to(b.root / "exchange")
        if path.is_dir():
            target.mkdir(exist_ok=True)
        else:
            shutil.copyfile(path, target)
    with pytest.raises(ValueError, match="exchange policy binding mismatch"):
        recover_brokered_transport(a.root)


def test_stale_success_receipt_does_not_override_live_process_observation(tmp_path, monkeypatch):
    result = execute_brokered_codex(**prepare(tmp_path), upstream=lambda _: response_stream())
    monkeypatch.setattr(
        "autoengineering.agents.hosts.codex_brokered.live_members", lambda _: (999,)
    )
    with pytest.raises(ValueError, match="still live or ambiguous"):
        recover_brokered_transport(result.root)
