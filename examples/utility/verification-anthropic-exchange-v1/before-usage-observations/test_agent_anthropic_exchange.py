"""Authored complete Messages fixtures, no SDK, credential, network or host grant."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from autoengineering.agents.hosts.anthropic_boundary import WIRE_SCHEMA, validate_anthropic_response
from autoengineering.agents.hosts.anthropic_exchange import AnthropicExchange
from autoengineering.agents.hosts.brokered_host import WIRE_SCHEMA as EXISTING_WIRE_SCHEMA
from autoengineering.agents.hosts.response_boundary import ResponseBoundaryError, MAX_RESPONSE_BYTES
from autoengineering.agents.hosts.text_exchange import TextExchange
from autoengineering.campaign.store import WriterBusy

MODEL = "claude-authored-fixture"
PROMPT = "approved role brief"
INNER = '{"role":"reviewer","synthetic":true}'


def message(**updates):
    value = {
        "id": "msg_authored", "type": "message", "role": "assistant", "model": MODEL,
        "stop_reason": "end_turn", "stop_sequence": None,
        "content": [{"type": "text", "text": json.dumps({"handoff_json": INNER})}],
        "usage": {"input_tokens": 5, "cache_read_input_tokens": 2,
                  "cache_creation_input_tokens": 3, "output_tokens": 7},
    }
    return json.dumps(value | updates).encode()


def validate(raw):
    return validate_anthropic_response(
        raw, requested_model=MODEL, max_text_bytes=32768, max_output_tokens=1024,
    )


def client(prompt=PROMPT):
    return json.dumps({
        "model": MODEL, "stream": True,
        "messages": [
            {"role": "assistant", "content": "unapproved ambient history"},
            {"role": "user", "content": [{"type": "text", "text": prompt,
                                           "cache_control": {"canary": "unapproved cache"}}]},
        ],
        "system": "unapproved native instructions", "metadata": {"user_id": "unapproved account"},
        "tools": [{"name": "exec_command"}], "max_tokens": 999999,
        "output_config": {"schema": "unapproved override"},
        "headers": {"Authorization": "unapproved credential"},
    }).encode()


def exchange(tmp_path, **kwargs):
    tmp_path.chmod(0o700)
    return AnthropicExchange.create(
        tmp_path / "exchange", invocation_id="call-one", requested_model=MODEL,
        approved_prompt=PROMPT, output_schema=WIRE_SCHEMA, max_output_tokens=1024, **kwargs,
    )


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_wire_contract_matches_existing_role_envelope_and_usage_is_cache_aware():
    assert WIRE_SCHEMA == EXISTING_WIRE_SCHEMA
    response = validate(message())
    assert json.loads(response.text) == {"handoff_json": INNER}
    assert response.reported_model == MODEL
    assert response.usage["input_tokens"] == 10
    assert response.usage["total_tokens"] == 17
    events = [json.loads(frame.split(b"data: ", 1)[1])
              for frame in response.normalized_sse.strip().split(b"\n\n")]
    assert [e["type"] for e in events] == [
        "message_start", "content_block_start", "content_block_delta", "content_block_stop",
        "message_delta", "message_stop",
    ]
    assert events[1]["content_block"]["name"] == "StructuredOutput"
    assert json.loads(events[2]["delta"]["partial_json"]) == {"handoff_json": INNER}
    assert events[4]["usage"]["output_tokens"] == 7
    with pytest.raises(TypeError):
        response.usage["input_tokens"] = 0


@pytest.mark.parametrize("missing", ["cache_read_input_tokens", "cache_creation_input_tokens"])
def test_missing_cache_counts_stay_unknown_and_are_not_synthesized(missing):
    usage = json.loads(message())["usage"]
    del usage[missing]
    value = validate(message(usage=usage))
    assert value.usage["input_tokens"] is None and value.usage["total_tokens"] is None
    start = json.loads(value.normalized_sse.split(b"\n\n")[0].split(b"data: ")[1])
    assert missing not in start["message"]["usage"]


@pytest.mark.parametrize("updates", [
    {"type": "error"}, {"model": "claude-other"}, {"role": "user"}, {"id": "\ud800"},
    {"stop_reason": "tool_use"}, {"stop_reason": "max_tokens"}, {"stop_reason": "refusal"},
    {"stop_reason": "pause_turn"}, {"stop_sequence": "private-canary"},
    {"content": [{"type": "tool_use", "name": "exec_command", "input": "private-canary"}]},
    {"content": [{"type": "thinking", "thinking": "private-canary"}]},
    {"content": [{"type": "text", "text": '{"handoff_json":"not JSON"}'}]},
    {"content": [{"type": "text", "text": '{"handoff_json":"{}","extra":1}'}]},
    {"usage": None}, {"usage": {"input_tokens": 2}},
    {"usage": {"input_tokens": True, "output_tokens": 2}},
    {"usage": {"input_tokens": 1, "output_tokens": 1025}},
    {"usage": {"input_tokens": 1, "output_tokens": 1,
               "server_tool_use": {"web_search_requests": 1}}},
])
def test_unsupported_or_incomplete_upstream_never_becomes_native_output(updates):
    with pytest.raises(ResponseBoundaryError) as error:
        validate(message(**updates))
    assert "private-canary" not in str(error.value)


@pytest.mark.parametrize("raw", [b"", b"not json", b'{"type":"message","type":"error"}',
                                  b'{"x":NaN}', b"x" * (MAX_RESPONSE_BYTES + 1)])
def test_bad_framing_and_oversize_rejected(raw):
    with pytest.raises(ResponseBoundaryError):
        validate(raw)


def test_frozen_request_replaces_all_native_context_and_one_dispatch_is_replayed(tmp_path):
    broker = exchange(tmp_path)
    calls = []

    def upstream(raw):
        calls.append(raw)
        return message(metadata={"private": "unapproved response metadata"})

    result = broker.execute(client(), upstream)
    assert result.status == "completed" and result.provider_requests_reserved == 1
    outbound = json.loads(calls[0])
    assert set(outbound) == {"model", "system", "messages", "max_tokens", "stream", "tools", "output_config"}
    assert outbound["messages"] == [{"role": "user", "content": [{"type": "text", "text": PROMPT}]}]
    assert outbound["tools"] == [] and outbound["stream"] is False
    assert outbound["max_tokens"] == 1024
    assert outbound["output_config"] == {"format": {"type": "json_schema", "schema": WIRE_SCHEMA}}
    assert b"unapproved" not in calls[0] and b"unapproved" not in result.response.normalized_sse
    before = snapshot(broker.root)
    for replay in (broker.execute(client(), upstream), AnthropicExchange(broker.root).recover()):
        assert replay.replayed and replay.response == result.response
    assert snapshot(broker.root) == before and len(calls) == 1
    with pytest.raises(ValueError, match="conflicting"):
        broker.execute(client("changed"), upstream)
    with pytest.raises(ValueError, match="incompatible"):
        TextExchange(broker.root)


@pytest.mark.parametrize("stage,reserved,count,status", [
    ("request_saved", 0, 0, "reconciliation_required"),
    ("dispatch_committed", 1, 0, "reconciliation_required"),
    ("raw_saved", 1, 1, "completed"),
    ("before_outcome_commit", 1, 1, "completed"),
])
def test_fault_windows_keep_original_reservation_without_retry(tmp_path, stage, reserved, count, status):
    def fault(where):
        if where == stage:
            raise OSError("acknowledgment loss")
    broker = exchange(tmp_path, fault=fault)
    calls = []
    with pytest.raises(OSError, match="acknowledgment"):
        broker.execute(client(), lambda raw: calls.append(raw) or message())
    restored = AnthropicExchange(broker.root)
    for result in (restored.recover(), restored.execute(client(), lambda _: pytest.fail("retry"))):
        assert result.status == status and result.provider_requests_reserved == reserved
        assert result.replayed
    assert len(calls) == count


def test_bad_prompt_rejects_before_dispatch_and_provider_error_stays_unknown(tmp_path):
    broker = exchange(tmp_path)
    result = broker.execute(client("wrong"), lambda _: pytest.fail("must not dispatch"))
    assert result.status == "rejected" and result.provider_requests_reserved == 0
    assert broker.recover().provider_requests_reserved == 0
    second_root = tmp_path / "second"
    second_root.mkdir(mode=0o700)
    second = exchange(second_root)
    def failure(_):
        raise RuntimeError("secret-auth-canary")
    result = second.execute(client(), failure)
    assert result.status == "reconciliation_required" and result.provider_requests_reserved == 1
    assert "secret-auth-canary" not in repr(snapshot(second.root))
    assert second.recover().status == "reconciliation_required"


def test_tool_payload_saved_before_rejection_and_missing_usage_is_not_zero(tmp_path):
    broker = exchange(tmp_path)
    raw = message(content=[{"type": "tool_use", "name": "exec_command", "input": {}}])
    result = broker.execute(client(), lambda _: raw)
    assert result.status == "rejected" and result.response is None
    assert list(broker.root.glob("artifacts/*/upstream-response.json"))[0].read_bytes() == raw
    assert not list(broker.root.glob("artifacts/*/client-response.sse"))
    assert broker.recover().reason == result.reason
    assert json.loads((broker.root / "outcome.json").read_text())["usage"] is None


def test_writer_lock_and_schema_type_mismatch_refuse(tmp_path):
    broker = exchange(tmp_path)
    with broker._lease(), pytest.raises(WriterBusy):
        AnthropicExchange(broker.root).execute(client(), lambda _: pytest.fail("dispatch"))
    bad = deepcopy(WIRE_SCHEMA)
    bad["additionalProperties"] = 0
    with pytest.raises(ValueError):
        AnthropicExchange.create(
            tmp_path / "wrong", invocation_id="other", requested_model=MODEL,
            approved_prompt=PROMPT, output_schema=bad, max_output_tokens=1024,
        )
    assert not (tmp_path / "wrong").exists()


def test_actual_native_request_shape_uses_only_the_bound_role_packet(tmp_path):
    path = Path(__file__).parents[1] / "examples/utility/development/claude-loopback-v7/request-1.json"
    native = json.loads(path.read_bytes())
    native["model"] = MODEL
    native["messages"][-1]["content"][0]["text"] = PROMPT
    broker = exchange(tmp_path)
    seen = []
    assert broker.execute(json.dumps(native).encode(), lambda raw: seen.append(raw) or message()).status == "completed"
    assert b"CWD:" not in seen[0] and b"user_id" not in seen[0]
