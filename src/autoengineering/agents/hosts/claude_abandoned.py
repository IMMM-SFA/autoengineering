"""Read-only recovery for an abandoned owned Claude/API invocation.

No native result, duration or usage is reconstructed. Both original worker groups
and their shared supervisor must be conclusively absent. The caller separately
verifies the prepared Anthropic lease/model scope. No lease is opened or port used.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.store import checked_directory
from .abandoned import _json, _bytes, _stopped, _owner_absent
from .anthropic_boundary import WIRE_SCHEMA
from .anthropic_exchange import AnthropicExchange
from .base import HostResult
from .claude_brokered import _manifest, _hash
from .command_upstream import OUTPUT_LIMIT, VERSION as UPSTREAM_VERSION, _check_sources
from .response_boundary import MAX_RESPONSE_BYTES
from .text_exchange import MAX_REQUEST_BYTES


def recover_abandoned_claude(root: Path, *, upstream_attempt: Path) -> HostResult:
    """Verify original immutable inputs, ownership and watchdog stops only."""
    root, upstream = checked_directory(root), checked_directory(upstream_attempt)
    manifest = _manifest(root)
    for name in ("client/completion.json", "timing.json", "outcome.json"):
        if (root / name).exists() or (root / name).is_symlink():
            raise ValueError("committed or partial Claude result needs its normal decoder")
    if any(checked_directory(root / "stops").iterdir()):
        raise ValueError("saved Claude endpoint stop needs its normal decoder")
    for name, field in (
        ("prompt.txt", "prompt_sha256"),
        ("workspace/schema.json", "schema_sha256"),
        ("auth/helper", "helper_sha256"),
        ("auth/capability", "capability_sha256"),
        ("endpoint/endpoint.json", "endpoint_sha256"),
    ):
        if _hash(root / name) != manifest[field]:
            raise ValueError("abandoned Claude input binding changed")
    if _hash(Path(manifest["policy"])) != manifest["policy_sha256"]:
        raise ValueError("abandoned Claude boundary policy changed")
    if _json(root / "client", "job.json") != manifest["job"] or _json(root, "job-binding.json") != {
        "transport_sha256": digest(manifest),
        "job_sha256": _hash(root / "client/job.json"),
    }:
        raise ValueError("abandoned Claude original job binding changed")
    job = manifest["job"]
    if (
        set(job) != {"command", "cwd", "environment", "keep_group_leader", "owner_lease"}
        or job["cwd"] != str(root / "workspace")
        or job["keep_group_leader"] is not True
        or job["owner_lease"] != "pipe-eof-v1"
        or job["environment"]
        != {
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "HOME": str(root / "home"),
            "TMPDIR": str(root / "home"),
            "CLAUDE_CODE_TMPDIR": str(root / "home"),
        }
    ):
        raise ValueError("abandoned Claude process job differs from owned protocol")
    prompt = _bytes(root, "prompt.txt", 65536)
    if _bytes(root, "client/stdin.bin", 65536) != prompt:
        raise ValueError("abandoned Claude original stdin changed")
    metadata = _json(root / "endpoint", "endpoint.json")
    if (
        metadata["invocation_id"] != manifest["invocation_id"]
        or metadata["owner_source_identity"] != manifest["source_identity"]
        or metadata["address"] != "127.0.0.1"
    ):
        raise ValueError("abandoned Claude endpoint scope mismatch")
    owner = _stopped(
        root / "client",
        nonce=manifest["nonce"],
        expected_job=job,
        max_output_bytes=manifest["max_output_bytes"],
    )
    if not _owner_absent(*owner):
        raise ValueError("original Claude endpoint supervisor is still live or ambiguous")
    exchange = AnthropicExchange(root / "exchange")
    if (
        exchange.manifest["invocation_id"] != manifest["invocation_id"]
        or exchange.manifest["requested_model"] != manifest["model"]
        or exchange.manifest["approved_prompt"].encode() != prompt
        or exchange.manifest["output_schema"] != WIRE_SCHEMA
        or unique_json(_bytes(root, "workspace/schema.json", 65536).decode()) != WIRE_SCHEMA
        or exchange.manifest["max_output_tokens"] != manifest["max_output_tokens"]
    ):
        raise ValueError("abandoned Claude exchange scope mismatch")
    dispatch = _json(exchange.root, "dispatch.json")
    if (
        set(dispatch) != {"client", "upstream_request", "provider_requests_reserved"}
        or type(dispatch["provider_requests_reserved"]) is not int
        or dispatch["provider_requests_reserved"] != 1
    ):
        raise ValueError("invalid abandoned Claude provider reservation")
    client = ArtifactRef.from_dict(dispatch["client"])
    if client.to_dict() != _json(exchange.root, "client.json"):
        raise ValueError("abandoned Claude client request changed")
    original = read_bytes(exchange.root, client, max_bytes=MAX_REQUEST_BYTES)
    request = read_bytes(
        exchange.root,
        ArtifactRef.from_dict(dispatch["upstream_request"]),
        max_bytes=MAX_REQUEST_BYTES,
    )
    if request != exchange._request(original):
        raise ValueError("abandoned Claude approved API request changed")
    upstream_manifest = _json(upstream, "upstream.json")
    if (
        set(upstream_manifest)
        != {
            "version",
            "nonce",
            "source_identity",
            "command",
            "sources",
            "request_sha256",
            "request_bytes",
            "deadline_monotonic",
            "max_output_bytes",
            "max_response_bytes",
        }
        or upstream_manifest["version"] != UPSTREAM_VERSION
        or upstream_manifest["max_output_bytes"] != OUTPUT_LIMIT
        or upstream_manifest["max_response_bytes"] != MAX_RESPONSE_BYTES
        or type(upstream_manifest["deadline_monotonic"]) not in (int, float)
        or not math.isfinite(upstream_manifest["deadline_monotonic"])
        or upstream_manifest["deadline_monotonic"] <= 0
    ):
        raise ValueError("incompatible abandoned upstream")
    _check_sources(upstream_manifest)
    if (
        upstream_manifest["request_sha256"] != hashlib.sha256(request).hexdigest()
        or upstream_manifest["request_bytes"] != len(request)
        or _bytes(upstream, "request.bin", MAX_REQUEST_BYTES) != request
        or _bytes(upstream, "process/stdin.bin", 65536) != b""
    ):
        raise ValueError("abandoned upstream request mismatch")
    command = [
        str(upstream / "request.bin")
        if arg == "{request}"
        else str(upstream / "response.bin")
        if arg == "{response}"
        else arg
        for arg in upstream_manifest["command"]
    ]
    upstream_owner = _stopped(
        upstream / "process",
        nonce=upstream_manifest["nonce"],
        expected_job={
            "command": command,
            "cwd": str(upstream),
            "environment": {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            "keep_group_leader": True,
            "owner_lease": "pipe-eof-v1",
        },
        max_output_bytes=OUTPUT_LIMIT,
    )
    if upstream_owner != owner:
        raise ValueError("upstream belongs to another supervisor")
    return HostResult("host_failure", "", None, {}, None, b"", b"", True)
