"""Complete text-only Messages validation before native Claude receives bytes.

The upstream uses JSON output, with no tools or native CLI context. Only the
application constructs the native StructuredOutput pseudo-tool after validating
all bytes. This module opens no socket, reads no key and grants no host admission.

Protocol: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
Stops: https://platform.claude.com/docs/en/build-with-claude/handling-stop-reasons
"""

from __future__ import annotations

import hashlib
import re

from autoengineering.campaign.serialization import canonical_json, unique_json
from .response_boundary import MAX_RESPONSE_BYTES, ResponseBoundaryError, TextResponse

VERSION = "anthropic-json-handoff-1.0"
WIRE_SCHEMA = {
    "type": "object",
    "properties": {"handoff_json": {"type": "string"}},
    "required": ["handoff_json"],
    "additionalProperties": False,
}


def _reject(code):
    raise ResponseBoundaryError("anthropic_" + code)


def _count(usage, name):
    value = usage.get(name)
    if value is not None and (type(value) is not int or not 0 <= value <= 10**12):
        _reject("invalid_usage")
    return value


def validate_anthropic_response(
    raw: bytes, *, requested_model: str, max_text_bytes: int, max_output_tokens: int,
) -> TextResponse:
    """Validate one complete JSON message and build a new native output stream.

    Unknown cache counts remain unknown in broker usage. Native CLI counters are
    separate diagnostics and must never fill these gaps. No provider tool event,
    header, metadata, reasoning block or arbitrary native instruction is forwarded.
    """
    if (
        type(requested_model) is not str
        or re.fullmatch(r"claude-[A-Za-z0-9._-]{1,128}", requested_model) is None
        or type(max_text_bytes) is not int or not 0 < max_text_bytes <= 65536
        or type(max_output_tokens) is not int or not 0 < max_output_tokens <= 32768
    ):
        raise ValueError("invalid Anthropic response policy")
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        _reject("response_size_limit")
    try:
        value = unique_json(raw.decode())
    except (ValueError, UnicodeError, RecursionError):
        _reject("invalid_response_json")
    if (
        not isinstance(value, dict) or value.get("type") != "message"
        or value.get("role") != "assistant"
        or type(value.get("id")) is not str
        or re.fullmatch(r"msg_[A-Za-z0-9_-]{1,252}", value["id"]) is None
        or value.get("model") != requested_model
    ):
        _reject("response_identity_mismatch")
    if (
        value.get("stop_reason") != "end_turn" or value.get("stop_sequence") is not None
        or value.get("stop_details") is not None or value.get("error") is not None
    ):
        _reject("incomplete_response")
    blocks = value.get("content")
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= 128:
        _reject("invalid_content")
    if any(
        not isinstance(block, dict) or block.get("type") != "text"
        or type(block.get("text")) is not str for block in blocks
    ):
        _reject("forbidden_content")
    text = "".join(block["text"] for block in blocks)
    try:
        if not 0 < len(text.encode()) <= max_text_bytes:
            _reject("text_limit")
        payload = unique_json(text)
        if (
            not isinstance(payload, dict) or set(payload) != {"handoff_json"}
            or type(payload["handoff_json"]) is not str or not payload["handoff_json"].strip()
            or not isinstance(unique_json(payload["handoff_json"]), dict)
        ):
            _reject("invalid_handoff_envelope")
        text = canonical_json(payload)
        if len(text.encode()) > max_text_bytes:
            _reject("text_limit")
    except (ValueError, UnicodeError, RecursionError) as error:
        if isinstance(error, ResponseBoundaryError):
            raise
        _reject("invalid_handoff_envelope")
    supplied = value.get("usage")
    if not isinstance(supplied, dict):
        _reject("missing_usage")
    uncached = _count(supplied, "input_tokens")
    output = _count(supplied, "output_tokens")
    cached = _count(supplied, "cache_read_input_tokens")
    created = _count(supplied, "cache_creation_input_tokens")
    if uncached is None or output is None:
        _reject("missing_usage")
    if output > max_output_tokens:
        _reject("output_token_cap_exceeded")
    server_tools = supplied.get("server_tool_use", {})
    if not isinstance(server_tools, dict) or any(
        type(n) is not int or n != 0 for n in server_tools.values()
    ):
        _reject("forbidden_tool_usage")
    inputs = uncached + cached + created if cached is not None and created is not None else None
    usage = {
        "uncached_input_tokens": uncached, "cached_input_tokens": cached,
        "cache_creation_input_tokens": created, "input_tokens": inputs,
        "output_tokens": output, "total_tokens": inputs + output if inputs is not None else None,
        "reasoning_output_tokens": None,
    }
    start_usage = {"input_tokens": uncached, "output_tokens": 0}
    for key in ("cache_read_input_tokens", "cache_creation_input_tokens"):
        if supplied.get(key) is not None:
            start_usage[key] = supplied[key]
    message = {
        "id": value["id"], "type": "message", "role": "assistant", "model": requested_model,
        "content": [], "stop_reason": None, "stop_sequence": None, "usage": start_usage,
    }
    events = (
        {"type": "message_start", "message": message},
        {"type": "content_block_start", "index": 0, "content_block": {
            "type": "tool_use", "id": "toolu_validated_handoff", "name": "StructuredOutput",
            "input": {},
        }},
        {"type": "content_block_delta", "index": 0, "delta": {
            "type": "input_json_delta", "partial_json": text,
        }},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use", "stop_sequence": None},
         "usage": {"output_tokens": output}},
        {"type": "message_stop"},
    )
    normalized = b"".join(
        f"event: {event['type']}\ndata: {canonical_json(event)}\n\n".encode() for event in events
    )
    return TextResponse(text, requested_model, usage, hashlib.sha256(raw).hexdigest(), normalized)
