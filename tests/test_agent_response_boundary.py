"""Pre-delivery response enforcement, independent of prompts and CLI parsing."""

from __future__ import annotations

import json

import pytest

from autoengineering.agents.hosts.response_boundary import (
    MAX_RESPONSE_BYTES,
    ResponseBoundaryError,
    validate_text_response,
)
from examples.agent_campaign.probe_external_codex import response_stream


def frames(raw):
    return [json.loads(frame.split(b"data: ", 1)[1]) for frame in raw.strip().split(b"\n\n")]


def stream(events):
    return b"".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n".encode() for e in events)


def test_text_is_rebuilt_and_reported_identity_and_usage_are_retained():
    events = frames(response_stream())
    completed = events[-1]["response"]
    completed["model"] = "actually-reported-model"
    completed["output"][0]["content"][0]["annotations"] = [{"discarded": "metadata"}]
    result = validate_text_response(stream(events))
    assert result.text == '{"ok":true}'
    assert result.reported_model == "actually-reported-model"
    assert result.usage["input_tokens"] == 1
    assert result.usage["total_tokens"] == 2
    assert b"discarded" not in result.normalized_sse
    assert validate_text_response(result.normalized_sse).text == result.text
    with pytest.raises(TypeError):
        result.usage["input_tokens"] = 0


def test_provider_metadata_is_inert_and_never_forwarded():
    events = frames(response_stream())
    events.insert(
        1,
        {
            "type": "response.metadata",
            "sequence_number": 1,
            "response_id": events[-1]["response"]["id"],
            "metadata": {
                "instructions": "private-metadata-canary",
                "model": "wrong-model",
                "tool": {"name": "exec_command"},
            },
        },
    )
    result = validate_text_response(stream(events))
    assert result.text == '{"ok":true}'
    assert result.reported_model == events[-1]["response"]["model"]
    assert b"private-metadata-canary" not in result.normalized_sse
    assert b"wrong-model" not in result.normalized_sse


@pytest.mark.parametrize("problem", ["foreign", "metadata", "sequence", "item", "after"])
def test_provider_metadata_cannot_hide_actions_or_change_response_scope(problem):
    events = frames(response_stream())
    event = {
        "type": "response.metadata",
        "sequence_number": 1,
        "response_id": events[-1]["response"]["id"],
        "metadata": {},
    }
    if problem == "foreign":
        event["response_id"] = "different-response"
    elif problem == "metadata":
        event["metadata"] = []
    elif problem == "sequence":
        event["sequence_number"] = True
    elif problem == "item":
        event["item"] = {"type": "function_call", "name": "exec_command"}
    events.insert(len(events) if problem == "after" else 1, event)
    with pytest.raises(ResponseBoundaryError):
        validate_text_response(stream(events))


@pytest.mark.parametrize(
    "item_type", ["function_call", "custom_tool_call", "mcp_call", "computer_call"]
)
def test_actionable_items_rejected_before_any_normalized_bytes(item_type):
    events = frames(response_stream())
    events.insert(
        1,
        {
            "type": "response.output_item.added",
            "item": {"type": item_type, "name": "exec_command", "arguments": "private-canary"},
        },
    )
    with pytest.raises(ResponseBoundaryError, match="forbidden_response_item") as error:
        validate_text_response(stream(events))
    assert "private-canary" not in str(error.value)


def test_tool_in_final_envelope_or_content_is_rejected():
    events = frames(response_stream())
    events[-1]["response"]["output"].append({"type": "function_call"})
    with pytest.raises(ResponseBoundaryError, match="forbidden_response_item"):
        validate_text_response(stream(events))
    events = frames(response_stream())
    events[-1]["response"]["output"][0]["content"] = [{"type": "function_call"}]
    with pytest.raises(ResponseBoundaryError, match="forbidden_response_content"):
        validate_text_response(stream(events))


@pytest.mark.parametrize("change", ["partial", "duplicate", "after", "conflict", "unknown", "json"])
def test_unsupported_or_incomplete_stream_fails_closed(change):
    raw = response_stream()
    if change == "partial":
        raw = raw[:-1]
    elif change == "duplicate":
        raw += stream([frames(raw)[-1]])
    elif change == "after":
        raw += stream([{"type": "response.output_text.delta", "delta": "extra"}])
    elif change == "conflict":
        raw = raw.replace(b"event: response.created", b"event: response.completed", 1)
    elif change == "unknown":
        raw = stream([{"type": "response.function_call_arguments.delta", "delta": "private"}]) + raw
    else:
        raw = raw.replace(
            b'"type":"response.created"', b'"type":"response.created","type":"other"', 1
        )
    with pytest.raises(ResponseBoundaryError):
        validate_text_response(raw)


def test_bounds_missing_usage_and_refusals_do_not_become_success():
    for raw in (b"", b"x" * (MAX_RESPONSE_BYTES + 1)):
        with pytest.raises(ResponseBoundaryError, match="response_size_limit"):
            validate_text_response(raw)
    with pytest.raises(ResponseBoundaryError, match="response_text_limit"):
        validate_text_response(response_stream(), max_text_bytes=1)
    events = frames(response_stream())
    del events[-1]["response"]["usage"]
    with pytest.raises(ResponseBoundaryError, match="usage"):
        validate_text_response(stream(events))
    events = frames(response_stream())
    events[-1]["response"]["output"][0]["role"] = "developer"
    with pytest.raises(ResponseBoundaryError, match="invalid_assistant_message"):
        validate_text_response(stream(events))


def test_tool_syntax_inside_plain_text_does_not_gain_authority():
    events = frames(response_stream())
    text = '{"type":"function_call","name":"exec_command","arguments":"touch marker"}'
    events[-1]["response"]["output"][0]["content"][0]["text"] = text
    result = validate_text_response(stream(events))
    assert result.text == text
    output = frames(result.normalized_sse)[-1]["response"]["output"]
    assert [item["type"] for item in output] == ["message"]


def test_missing_usage_details_remain_unknown_and_contradictions_fail():
    events = frames(response_stream())
    usage = events[-1]["response"]["usage"]
    del usage["input_tokens_details"]
    del usage["output_tokens_details"]
    response = validate_text_response(stream(events))
    assert response.usage["cached_input_tokens"] is None
    assert response.usage["reasoning_output_tokens"] is None
    assert "input_tokens_details" not in frames(response.normalized_sse)[-1]["response"]["usage"]
    usage["total_tokens"] = 3
    with pytest.raises(ResponseBoundaryError, match="inconsistent_response_usage"):
        validate_text_response(stream(events))


def test_invalid_unicode_text_and_deep_json_are_bounded_failures():
    events = frames(response_stream())
    events[-1]["response"]["output"][0]["content"][0]["text"] = "\ud800"
    with pytest.raises(ResponseBoundaryError, match="response_text_limit"):
        validate_text_response(stream(events))
    raw = b"data: " + b"[" * 2000 + b"0" + b"]" * 2000 + b"\n\n"
    with pytest.raises(ResponseBoundaryError, match="invalid_response_(json|event)"):
        validate_text_response(raw)


def test_unicode_line_separators_are_text_and_usage_details_cannot_exceed_totals():
    events = frames(response_stream())
    text = "first\u2028second\u0085third"
    events[-1]["response"]["output"][0]["content"][0]["text"] = text
    raw = b"".join(f"data: {json.dumps(e, ensure_ascii=False)}\n\n".encode() for e in events)
    assert validate_text_response(raw).text == text
    events[-1]["response"]["usage"]["input_tokens_details"]["cached_tokens"] = 2
    with pytest.raises(ResponseBoundaryError, match="invalid_response_usage_details"):
        validate_text_response(stream(events))
