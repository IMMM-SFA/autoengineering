"""One durable, text-only provider exchange behind a host's private endpoint.

The trusted caller supplies the upstream transport and enforces its timeout,
credential and egress policy. This primitive does not authorize network access
or qualify a host. A committed dispatch intent is never retried automatically.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import stat

from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.artifacts import put_bytes, read_bytes, confined_file
from autoengineering.campaign.records import ArtifactRef, identifier
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, WriterBusy

from .response_boundary import MAX_RESPONSE_BYTES, VERSION, ResponseBoundaryError, TextResponse
from .response_boundary import validate_text_response
from .subscription_worker import TRUSTED_INSTRUCTIONS

MAX_REQUEST_BYTES = 524288
APPROVED_PROMPT_BYTES = 65536


@dataclass(frozen=True)
class ExchangeResult:
    status: str
    response: TextResponse | None
    provider_requests_reserved: int
    reason: str | None
    replayed: bool


class TextExchange:
    """Retain client input, reserve one provider request, validate before delivery.

    Only the exact approved prompt and trusted output schema are sent upstream.
    Native CLI context, tools, cache keys and client metadata are not forwarded.
    The original client request remains private evidence. HTTP authentication,
    accepted-client counting and endpoint ownership are caller responsibilities.
    """

    def __init__(self, root: Path, *, fault: Callable[[str], None] = lambda _stage: None):
        self.root = checked_directory(root)
        path = confined_file(self.root, "exchange.json")
        if path.stat().st_size > MAX_REQUEST_BYTES:
            raise ValueError("exchange manifest exceeds size limit")
        manifest = unique_json(path.read_text())
        if (
            not isinstance(manifest, dict)
            or set(manifest)
            != {
                "schema_version",
                "invocation_id",
                "requested_model",
                "approved_prompt",
                "output_schema",
                "max_text_bytes",
                "response_boundary",
                "source_identity",
            }
            or manifest["schema_version"] != "1.0"
            or manifest["response_boundary"] != VERSION
            or manifest["source_identity"] != host_source_identity()
        ):
            raise ValueError("incompatible text exchange identity")
        self._validate_manifest(manifest)
        self._manifest_json = canonical_json(manifest)
        checked_directory(self.root / "artifacts")
        self.fault = fault

    @property
    def manifest(self):
        return unique_json(self._manifest_json)

    def _check_identity(self):
        if (
            canonical_json(self._json("exchange.json")) != self._manifest_json
            or self.manifest["source_identity"] != host_source_identity()
        ):
            raise ValueError("text exchange identity changed")

    @staticmethod
    def _validate_manifest(data):
        identifier(data["invocation_id"])
        if (
            type(data["requested_model"]) is not str
            or not data["requested_model"].strip()
            or len(data["requested_model"].encode()) > 256
            or type(data["approved_prompt"]) is not str
            or not 0 < len(data["approved_prompt"].encode()) <= APPROVED_PROMPT_BYTES
            or not isinstance(data["output_schema"], dict)
            or type(data["max_text_bytes"]) is not int
            or not 0 < data["max_text_bytes"] <= 65536
        ):
            raise ValueError("invalid text exchange policy")
        if len(canonical_json(data["output_schema"]).encode()) > 65536:
            raise ValueError("text exchange schema exceeds size limit")

    @classmethod
    def create(
        cls,
        root: Path,
        *,
        invocation_id: str,
        requested_model: str,
        approved_prompt: str,
        output_schema: Mapping,
        max_text_bytes: int = 32768,
        **kwargs,
    ):
        manifest = {
            "schema_version": "1.0",
            "invocation_id": invocation_id,
            "requested_model": requested_model,
            "approved_prompt": approved_prompt,
            "output_schema": dict(output_schema),
            "max_text_bytes": max_text_bytes,
            "response_boundary": VERSION,
            "source_identity": host_source_identity(),
        }
        cls._validate_manifest(manifest)
        root = Path(root).absolute()
        checked_directory(root.parent)
        root.mkdir(mode=0o700)
        (root / "artifacts").mkdir(mode=0o700)
        durable_write(root / "exchange.json", canonical_json(manifest).encode())
        return cls(root, **kwargs)

    @contextmanager
    def _lease(self):
        descriptor = os.open(
            self.root / ".exchange.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise ValueError("exchange lock is not regular")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise WriterBusy("another owner holds the text exchange") from exc
            yield
        finally:
            os.close(descriptor)

    def _put(self, data, name):
        return put_bytes(
            self.root,
            data,
            name=name,
            media_type="application/octet-stream",
            producer=self.manifest["invocation_id"],
        )

    def _json(self, name):
        path = confined_file(self.root, name)
        if path.stat().st_size > 1048576:
            raise ValueError("exchange record exceeds size limit")
        return unique_json(path.read_text())

    def _request(self, raw):
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_REQUEST_BYTES:
            raise ValueError("client_request_size_limit")
        try:
            request = unique_json(raw.decode())
        except (ValueError, UnicodeDecodeError, RecursionError):
            raise ValueError("invalid_client_request") from None
        if (
            not isinstance(request, dict)
            or request.get("model") != self.manifest["requested_model"]
            or request.get("stream") is not True
            or not isinstance(request.get("input"), list)
            or not request["input"]
        ):
            raise ValueError("client_request_policy_mismatch")
        last = request["input"][-1]
        if (
            not isinstance(last, dict)
            or last.get("type") != "message"
            or last.get("role") != "user"
            or last.get("content")
            != [{"type": "input_text", "text": self.manifest["approved_prompt"]}]
        ):
            raise ValueError("client_prompt_mismatch")
        # Rebuild rather than redact. Even unknown extra client context cannot
        # become provider input, tools, routing, headers or an output schema.
        outgoing = {
            "model": self.manifest["requested_model"],
            "instructions": TRUSTED_INSTRUCTIONS,
            "stream": True,
            "store": False,
            "input": [{"type": "message", "role": "user", "content": last["content"]}],
            "tools": [],
            "tool_choice": "none",
            "parallel_tool_calls": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "role_response",
                    "strict": True,
                    "schema": self.manifest["output_schema"],
                }
            },
        }
        return canonical_json(outgoing).encode()

    def execute(self, client_request: bytes, upstream: Callable[[bytes], bytes]) -> ExchangeResult:
        """The callback may make one provider request. It is never used in recovery."""
        with self._lease():
            self._check_identity()
            if (self.root / "client.json").exists():
                reference = ArtifactRef.from_dict(self._json("client.json"))
                if read_bytes(self.root, reference, max_bytes=MAX_REQUEST_BYTES) != client_request:
                    raise ValueError("conflicting client request for text exchange")
                return self._recover()
            if any(
                (self.root / name).exists()
                for name in (
                    "dispatch.json",
                    "outcome.json",
                    "overflow.json",
                    "preflight-rejection.json",
                )
            ) or any((self.root / "artifacts").iterdir()):
                raise ValueError("exchange client request is missing")
            if (
                type(client_request) is not bytes
                or not 0 < len(client_request) <= MAX_REQUEST_BYTES
            ):
                raise ValueError("client_request_size_limit")
            client = self._put(client_request, "client-request.json")
            durable_write(self.root / "client.json", client.to_json().encode())
            try:
                outgoing = self._request(client_request)
            except ValueError:
                durable_write(
                    self.root / "preflight-rejection.json", b'{"reason":"client_request_rejected"}'
                )
                return ExchangeResult("rejected", None, 0, "client_request_rejected", False)
            request = self._put(outgoing, "upstream-request.json")
            self.fault("request_saved")
            intent = {
                "client": client.to_dict(),
                "upstream_request": request.to_dict(),
                "provider_requests_reserved": 1,
            }
            durable_write(self.root / "dispatch.json", canonical_json(intent).encode())
            self.fault("dispatch_committed")
            try:
                raw = upstream(outgoing)
            except Exception:
                # Transport errors can contain credentials. Do not save their
                # text or assume remote work stopped when the callback returned.
                return self._commit(
                    None, None, "reconciliation_required", "upstream_transport_failure", False
                )
            if type(raw) is bytes and len(raw) > MAX_RESPONSE_BYTES:
                prefix = self._put(raw[:MAX_RESPONSE_BYTES], "upstream-overflow.bin")
                durable_write(
                    self.root / "overflow.json",
                    canonical_json(
                        {
                            "observed_bytes": len(raw),
                            "retained": prefix.to_dict(),
                        }
                    ).encode(),
                )
            if type(raw) is not bytes or len(raw) > MAX_RESPONSE_BYTES:
                return self._commit(None, None, "rejected", "upstream_response_size_limit", False)
            reference = self._put(raw, "upstream-response.sse")
            self.fault("raw_saved")
            return self._validate(reference, replayed=False)

    def recover(self) -> ExchangeResult:
        with self._lease():
            self._check_identity()
            return self._recover()

    def _recover(self):
        if not (self.root / "dispatch.json").exists():
            if (
                (self.root / "outcome.json").exists()
                or (self.root / "overflow.json").exists()
                or any((self.root / "artifacts").glob("*/upstream-response.sse"))
            ):
                raise ValueError("exchange dispatch evidence is missing")
            if (self.root / "preflight-rejection.json").exists():
                client = ArtifactRef.from_dict(self._json("client.json"))
                raw = read_bytes(self.root, client, max_bytes=MAX_REQUEST_BYTES)
                if self._json("preflight-rejection.json") != {"reason": "client_request_rejected"}:
                    raise ValueError("invalid client rejection evidence")
                try:
                    self._request(raw)
                except ValueError:
                    return ExchangeResult("rejected", None, 0, "client_request_rejected", True)
                raise ValueError("contradictory client rejection evidence")
            # No callback can have been called without a durable dispatch intent.
            # Do not silently dispatch from recovery, even in this provable gap.
            return ExchangeResult(
                "reconciliation_required", None, 0, "dispatch_not_committed", True
            )
        intent = self._json("dispatch.json")
        client = ArtifactRef.from_dict(intent["client"])
        original = read_bytes(self.root, client, max_bytes=MAX_REQUEST_BYTES)
        if ArtifactRef.from_dict(self._json("client.json")) != client:
            raise ValueError("exchange client reference mismatch")
        request = ArtifactRef.from_dict(intent["upstream_request"])
        if read_bytes(self.root, request, max_bytes=MAX_REQUEST_BYTES) != self._request(original):
            raise ValueError("exchange upstream request mismatch")
        if intent.get("provider_requests_reserved") != 1:
            raise ValueError("invalid provider reservation")
        saved = self._json("outcome.json") if (self.root / "outcome.json").exists() else None
        # Digest-named immutable artifacts make raw-before-ack recovery possible.
        candidates = list((self.root / "artifacts").glob("*/upstream-response.sse"))
        if len(candidates) > 1:
            raise ValueError("ambiguous saved upstream response")
        reference = None
        if candidates:
            path = confined_file(self.root, str(candidates[0].relative_to(self.root)))
            reference = ArtifactRef(
                str(path.relative_to(self.root)),
                path.parent.name,
                path.stat().st_size,
                "application/octet-stream",
                self.manifest["invocation_id"],
                {},
            )
            read_bytes(self.root, reference, max_bytes=MAX_RESPONSE_BYTES)
        if saved is not None and saved.get("raw") != (
            None if reference is None else reference.to_dict()
        ):
            raise ValueError("saved exchange response mismatch")
        if reference is not None:
            if (self.root / "overflow.json").exists():
                raise ValueError("contradictory upstream size evidence")
            return self._validate(reference, replayed=True)
        if (self.root / "overflow.json").exists():
            overflow = self._json("overflow.json")
            retained = ArtifactRef.from_dict(overflow["retained"])
            if (
                set(overflow) != {"observed_bytes", "retained"}
                or type(overflow["observed_bytes"]) is not int
                or overflow["observed_bytes"] <= MAX_RESPONSE_BYTES
                or retained.size_bytes != MAX_RESPONSE_BYTES
            ):
                raise ValueError("invalid upstream overflow evidence")
            read_bytes(self.root, retained, max_bytes=MAX_RESPONSE_BYTES)
            return self._commit(None, None, "rejected", "upstream_response_size_limit", True)
        if saved is not None:
            if (
                set(saved)
                != {"status", "reason", "raw", "client_response", "usage", "reported_model"}
                or saved["status"] not in {"reconciliation_required", "rejected"}
                or saved["reason"]
                not in {"upstream_transport_failure", "upstream_response_size_limit"}
                or any(
                    saved[key] is not None
                    for key in ("raw", "client_response", "usage", "reported_model")
                )
            ):
                raise ValueError("invalid exchange failure outcome")
            return ExchangeResult(saved["status"], None, 1, saved["reason"], True)
        return ExchangeResult("reconciliation_required", None, 1, "upstream_outcome_unknown", True)

    def _validate(self, reference, *, replayed):
        raw = read_bytes(self.root, reference, max_bytes=MAX_RESPONSE_BYTES)
        try:
            response = validate_text_response(raw, max_text_bytes=self.manifest["max_text_bytes"])
        except ResponseBoundaryError as exc:
            return self._commit(reference, None, "rejected", str(exc), replayed)
        return self._commit(reference, response, "completed", None, replayed)

    def _commit(self, raw, response, status, reason, replayed):
        client = (
            None if response is None else self._put(response.normalized_sse, "client-response.sse")
        )
        outcome = {
            "status": status,
            "reason": reason,
            "raw": None if raw is None else raw.to_dict(),
            "client_response": None if client is None else client.to_dict(),
            "usage": None if response is None else dict(response.usage),
            "reported_model": None if response is None else response.reported_model,
        }
        path = self.root / "outcome.json"
        if path.exists():
            if self._json("outcome.json") != outcome:
                raise ValueError("immutable exchange outcome mismatch")
        else:
            self.fault("before_outcome_commit")
            durable_write(path, canonical_json(outcome).encode())
        return ExchangeResult(status, response, 1, reason, replayed)
