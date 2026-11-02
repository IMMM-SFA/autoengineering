"""Durable, single-attempt Anthropic Messages exchange for native Claude.

No credential, HTTP client or provider SDK is supplied here. A trusted upstream
callback owns authentication, timeout and network policy. Native metadata never
becomes provider input. A committed intent is never retried automatically.
"""

from __future__ import annotations

from collections.abc import Mapping
import re

from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import durable_write
from .anthropic_boundary import (
    VERSION,
    WIRE_SCHEMA,
    validate_anthropic_response,
    observe_anthropic_usage,
)
from .subscription_worker import TRUSTED_INSTRUCTIONS
from .response_boundary import MAX_RESPONSE_BYTES
from .text_exchange import TextExchange, MAX_REQUEST_BYTES, APPROVED_PROMPT_BYTES
from autoengineering.campaign.serialization import unique_json


class AnthropicExchange(TextExchange):
    """Same durable evidence protocol, distinct request/response policy identity."""

    BOUNDARY_VERSION = VERSION
    RAW_RESPONSE_NAME = "upstream-response.json"
    MANIFEST_FIELDS = TextExchange.MANIFEST_FIELDS | {"max_output_tokens"}

    @classmethod
    def _validate_manifest(cls, data):
        super()._validate_manifest(data)
        if (
            re.fullmatch(r"claude-[A-Za-z0-9._-]{1,128}", data["requested_model"]) is None
            or type(data.get("max_output_tokens")) is not int
            or not 0 < data["max_output_tokens"] <= 32768
            or canonical_json(data["output_schema"]) != canonical_json(WIRE_SCHEMA)
        ):
            raise ValueError("invalid Anthropic role exchange policy")

    @classmethod
    def create(
        cls,
        root,
        *,
        invocation_id: str,
        requested_model: str,
        approved_prompt: str,
        output_schema: Mapping,
        max_output_tokens: int,
        max_text_bytes: int = 32768,
        **kwargs,
    ):
        manifest = {
            "schema_version": "1.0",
            "invocation_id": invocation_id,
            "requested_model": requested_model,
            "approved_prompt": approved_prompt,
            "output_schema": dict(output_schema),
            "max_output_tokens": max_output_tokens,
            "max_text_bytes": max_text_bytes,
            "response_boundary": cls.BOUNDARY_VERSION,
            "source_identity": host_source_identity(),
        }
        return cls._create_manifest(root, manifest, **kwargs)

    def _request(self, raw):
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_REQUEST_BYTES:
            raise ValueError("client_request_size_limit")
        try:
            request = unique_json(raw.decode())
        except (ValueError, UnicodeError, RecursionError):
            raise ValueError("invalid_client_request") from None
        if (
            not isinstance(request, dict)
            or request.get("model") != self.manifest["requested_model"]
            or request.get("stream") is not True
            or not isinstance(request.get("messages"), list)
            or not request["messages"]
        ):
            raise ValueError("client_request_policy_mismatch")
        last = request["messages"][-1]
        if not isinstance(last, dict) or last.get("role") != "user":
            raise ValueError("client_prompt_mismatch")
        content = last.get("content")
        if isinstance(content, str):
            text = content
        elif (
            isinstance(content, list)
            and len(content) == 1
            and isinstance(content[0], dict)
            and content[0].get("type") == "text"
            and type(content[0].get("text")) is str
        ):
            text = content[0]["text"]
        else:
            raise ValueError("client_prompt_mismatch")
        if text != self.manifest["approved_prompt"] or len(text.encode()) > APPROVED_PROMPT_BYTES:
            raise ValueError("client_prompt_mismatch")
        # The native output tool is generated locally after validation. Neither
        # it nor any other native context, cache hint, header or metadata is sent.
        outgoing = {
            "model": self.manifest["requested_model"],
            "system": TRUSTED_INSTRUCTIONS,
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}],
            "max_tokens": self.manifest["max_output_tokens"],
            "stream": False,
            "tools": [],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": self.manifest["output_schema"],
                }
            },
        }
        return canonical_json(outgoing).encode()

    def _parse_response(self, raw):
        return validate_anthropic_response(
            raw,
            requested_model=self.manifest["requested_model"],
            max_text_bytes=self.manifest["max_text_bytes"],
            max_output_tokens=self.manifest["max_output_tokens"],
        )

    def _validate(self, reference, *, replayed):
        raw = read_bytes(self.root, reference, max_bytes=MAX_RESPONSE_BYTES)
        observation = observe_anthropic_usage(raw)
        path = self.root / "usage-observation.json"
        if path.exists():
            if self._json(path.name) != observation:
                raise ValueError("immutable Anthropic usage observation mismatch")
        else:
            durable_write(path, canonical_json(observation).encode())
        return super()._validate(reference, replayed=replayed)
