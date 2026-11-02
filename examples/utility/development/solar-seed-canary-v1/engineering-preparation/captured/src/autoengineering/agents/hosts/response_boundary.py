"""Bounded text-only Responses normalization before a host receives any bytes.

This is one broker primitive, not a qualified network proxy. Callers must retain
raw upstream bytes before validation and must not forward partial upstream SSE.
Unsupported event types fail closed. No tool invocation is forwarded.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from types import MappingProxyType

from autoengineering.campaign.serialization import canonical_json, unique_json

VERSION = "text-response-1.1"
MAX_RESPONSE_BYTES = 524288
MAX_EVENTS = 4096


class ResponseBoundaryError(ValueError):
    """An error code containing no untrusted response content."""


def _reject(code):
    raise ResponseBoundaryError(code)


def _string(value, limit):
    try:
        return type(value) is str and 0 < len(value.encode("utf-8")) <= limit
    except UnicodeEncodeError:
        return False


def _item(item):
    if not isinstance(item, dict):
        _reject("invalid_response_item")
    kind = item.get("type")
    if kind == "reasoning":
        # Reasoning remains in the caller's raw upstream evidence. It is never
        # converted to instructions or forwarded as a client output item.
        return []
    if kind != "message":
        _reject("forbidden_response_item")
    if item.get("role") != "assistant" or not isinstance(item.get("content"), list):
        _reject("invalid_assistant_message")
    return [_part(part) for part in item["content"]]


def _part(part):
    if not isinstance(part, dict) or part.get("type") != "output_text":
        _reject("forbidden_response_content")
    if type(part.get("text")) is not str:
        _reject("invalid_response_text")
    return part["text"]


@dataclass(frozen=True)
class TextResponse:
    text: str
    reported_model: str
    usage: Mapping[str, int | None]
    raw_sha256: str
    normalized_sse: bytes

    def __post_init__(self):
        object.__setattr__(self, "usage", MappingProxyType(dict(self.usage)))


def validate_text_response(raw: bytes, *, max_text_bytes: int = 32768) -> TextResponse:
    """Validate a complete response, then build a fresh text-only SSE stream.

    The whole input is checked before any output is returned. An actionable
    event followed by a benign completion is rejected, not silently hidden.
    Requested model identity is never substituted for reported identity. Missing
    usage is unsupported here and must remain unknown in the caller's failure
    receipt. Auth, request counting, egress and process limits belong to callers.
    """
    if type(max_text_bytes) is not int or not 0 < max_text_bytes <= 65536:
        raise ValueError("invalid text response limit")
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_RESPONSE_BYTES:
        _reject("response_size_limit")
    try:
        stream = raw.decode("utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError:
        _reject("invalid_response_encoding")
    if "\r" in stream or not stream.endswith("\n\n"):
        _reject("incomplete_response_stream")
    completed, count, end_marker = None, 0, False
    metadata_response_ids = set()
    for frame in stream.split("\n\n"):
        if not frame:
            continue
        count += 1
        if count > MAX_EVENTS:
            _reject("response_event_limit")
        event_name, data = None, []
        for line in frame.split("\n"):
            if line.startswith(":"):
                continue
            if line.startswith("event:") and event_name is None:
                event_name = line[6:].lstrip(" ")
            elif line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
            else:
                _reject("unsupported_sse_field")
        if not data and event_name is None:
            continue
        encoded = "\n".join(data)
        if encoded == "[DONE]" and completed is not None and not end_marker:
            end_marker = True
            continue
        if completed is not None:
            _reject("events_after_response_completion")
        try:
            event = unique_json(encoded)
        except (ValueError, TypeError, RecursionError):
            _reject("invalid_response_json")
        if not isinstance(event, dict) or type(event.get("type")) is not str:
            _reject("invalid_response_event")
        kind = event["type"]
        if event_name is not None and event_name != kind:
            _reject("conflicting_response_event")
        if kind in {"response.created", "response.in_progress", "response.completed"}:
            response = event.get("response")
            if not isinstance(response, dict) or not isinstance(response.get("output"), list):
                _reject("invalid_response_envelope")
            for item in response["output"]:
                _item(item)
            if kind == "response.completed":
                if response.get("status") != "completed":
                    _reject("incomplete_response")
                completed = response
        elif kind in {"response.output_item.added", "response.output_item.done"}:
            _item(event.get("item"))
        elif kind in {"response.content_part.added", "response.content_part.done"}:
            _part(event.get("part"))
        elif kind in {"response.output_text.delta", "response.output_text.done"}:
            key = "delta" if kind.endswith(".delta") else "text"
            if type(event.get(key)) is not str:
                _reject("invalid_response_text")
        elif kind == "response.metadata":
            if (
                set(event) - {"sequence_number"} != {"type", "response_id", "metadata"}
                or not _string(event.get("response_id"), 256)
                or not isinstance(event.get("metadata"), dict)
                or (
                    "sequence_number" in event
                    and (type(event["sequence_number"]) is not int or event["sequence_number"] < 0)
                )
            ):
                _reject("invalid_response_metadata")
            # Provider metadata is inert and never enters the rebuilt client stream.
            metadata_response_ids.add(event["response_id"])
        elif kind in {
            "response.reasoning_summary_part.added",
            "response.reasoning_summary_part.done",
            "response.reasoning_summary_text.delta",
            "response.reasoning_summary_text.done",
            "response.reasoning_text.delta",
            "response.reasoning_text.done",
        }:
            # These events are discarded. Their payload is never reserialized.
            pass
        else:
            _reject("unsupported_response_event")
    if completed is None:
        _reject("missing_response_completion")
    text = "".join(part for item in completed["output"] for part in _item(item))
    if not _string(text, max_text_bytes):
        _reject("response_text_limit")
    model = completed.get("model")
    if not _string(model, 256) or not _string(completed.get("id"), 256):
        _reject("missing_response_identity")
    if metadata_response_ids - {completed["id"]}:
        _reject("foreign_response_metadata")
    usage = completed.get("usage")
    if not isinstance(usage, dict) or any(
        type(usage.get(key)) is not int or not 0 <= usage[key] <= 10**12
        for key in ("input_tokens", "output_tokens")
    ):
        _reject("missing_or_invalid_response_usage")
    kept_usage = {key: usage[key] for key in ("input_tokens", "output_tokens")}
    kept_usage["total_tokens"] = kept_usage["input_tokens"] + kept_usage["output_tokens"]
    if "total_tokens" in usage and (
        type(usage["total_tokens"]) is not int
        or usage["total_tokens"] != kept_usage["total_tokens"]
    ):
        _reject("inconsistent_response_usage")
    observed_usage = dict(kept_usage)
    for details, field, label in (
        ("input_tokens_details", "cached_tokens", "cached_input_tokens"),
        ("output_tokens_details", "reasoning_tokens", "reasoning_output_tokens"),
    ):
        value = usage.get(details, {})
        if not isinstance(value, dict):
            _reject("invalid_response_usage_details")
        count = value.get(field)
        token_total = usage[
            "input_tokens" if details == "input_tokens_details" else "output_tokens"
        ]
        if count is not None and (type(count) is not int or not 0 <= count <= token_total):
            _reject("invalid_response_usage_details")
        observed_usage[label] = count
        if count is not None:
            kept_usage[details] = {field: count}
    message = {
        "id": "msg_validated_text",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }
    response = {
        "id": completed["id"],
        "object": "response",
        "created_at": 0,
        "status": "completed",
        "model": model,
        "output": [message],
        "usage": kept_usage,
    }
    events = (
        {
            "type": "response.created",
            "response": {**response, "status": "in_progress", "output": []},
        },
        {"type": "response.output_item.done", "output_index": 0, "item": message},
        {"type": "response.completed", "response": response},
    )
    normalized = b"".join(
        f"event: {event['type']}\ndata: {canonical_json(event)}\n\n".encode() for event in events
    )
    return TextResponse(text, model, observed_usage, hashlib.sha256(raw).hexdigest(), normalized)
