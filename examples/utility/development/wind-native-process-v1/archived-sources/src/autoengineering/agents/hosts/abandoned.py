"""Read-only stop proof for an abandoned owned brokered invocation.

This never reconstructs a successful host response, token usage or duration.
The SDK creates the endpoint in its supervisor process and passes no listener
descriptor to either owned worker. The registered host uses exactly one fixed
subscription command. Both groups and that original supervisor must be gone.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import subprocess

from autoengineering.agents.process import recover_completed_process, recover_watchdog_stop
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.store import checked_directory

from .base import HostResult
from .command_upstream import OUTPUT_LIMIT, VERSION as UPSTREAM_VERSION, _check_sources
from .response_boundary import MAX_RESPONSE_BYTES
from .text_exchange import MAX_REQUEST_BYTES, TextExchange


def _json(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 1048576:
        raise ValueError("abandoned receipt exceeds size limit")
    return unique_json(path.read_text())


def _bytes(root, name, limit):
    path = confined_file(root, name)
    if path.stat().st_size > limit:
        raise ValueError("abandoned input exceeds size limit")
    return path.read_bytes()


def _owner_absent(pid, started):
    if (
        type(pid) is not int
        or pid <= 1
        or type(started) is not str
        or not started.strip()
        or started == "unknown"
    ):
        raise ValueError("invalid abandoned supervisor identity")
    # A failed ps must never become evidence of death. List start times without
    # command lines, and fail if any row cannot be interpreted.
    try:
        result = subprocess.run(
            ("/bin/ps", "-axo", "pid=,lstart="),
            capture_output=True,
            text=True,
            check=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        raise ValueError("supervisor observation is unavailable") from None
    if result.stderr or len(result.stdout) > 4194304 or not result.stdout.strip():
        raise ValueError("supervisor observation is unavailable")
    found = set()
    for line in result.stdout.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or not parts[0].isdigit() or int(parts[0]) in found:
            raise ValueError("invalid supervisor process observation")
        found.add(int(parts[0]))
        if int(parts[0]) == pid:
            return " ".join(parts[1].split()) != " ".join(started.split())
    return True


def _stopped(root, *, nonce, expected_job, max_output_bytes):
    stop = recover_watchdog_stop(root)
    identity = _json(root, "process.json")
    if identity["nonce"] != nonce or _json(root, "job.json") != expected_job:
        raise ValueError("abandoned process differs from its bound command")
    if (root / "completion.json").exists() or (root / "completion.json").is_symlink():
        recover_completed_process(root, nonce=nonce, max_output_bytes=max_output_bytes)
    owner = _json(root, "watchdog-job.json")
    if stop["stopped"] is not True:
        raise ValueError("abandoned group stop is unverified")
    return owner["owner_pid"], owner["owner_started"]


def recover_abandoned_brokered_transport(root: Path, *, upstream_attempt: Path) -> HostResult:
    """Verify an in-flight abandonment, never launch, signal or contact an old port.

    The registered caller must separately verify its fixed subscription policy.
    Other gaps with missing ownership evidence remain pending. Existing complete
    transport recovery takes precedence, including all its corruption checks.
    """
    from .codex_brokered import OWNED_VERSION, _manifest

    root, upstream = checked_directory(root), checked_directory(upstream_attempt)
    manifest = _manifest(root)
    if manifest["version"] != OWNED_VERSION:
        raise ValueError("abandoned recovery requires the owned native protocol")
    # This initial protocol covers an in-flight owner death before SDK result
    # commits. Never hide malformed completed evidence behind a generic failure.
    for path in ("client/completion.json", "timing.json", "transport-outcome.json"):
        if (root / path).exists() or (root / path).is_symlink():
            raise ValueError("committed or partial result needs its normal decoder")
    if any(checked_directory(root / "stops").iterdir()):
        raise ValueError("saved endpoint stop needs its normal decoder")
    prompt = read_bytes(root, ArtifactRef.from_dict(manifest["prompt"]), max_bytes=65536)
    schema = read_bytes(root, ArtifactRef.from_dict(manifest["schema"]), max_bytes=65536)
    endpoint = read_bytes(root, ArtifactRef.from_dict(manifest["endpoint"]), max_bytes=16384)
    if _bytes(root, "endpoint/endpoint.json", 16384) != endpoint:
        raise ValueError("abandoned endpoint metadata changed")
    metadata = unique_json(endpoint.decode())
    if (
        metadata["invocation_id"] != manifest["exchange_invocation_id"]
        or metadata["owner_source_identity"] != manifest["source_identity"]
        or metadata["address"] != "127.0.0.1"
    ):
        raise ValueError("abandoned endpoint scope mismatch")
    policy = manifest["boundary_policy"]
    if policy is None or set(policy) != {"path", "artifact"}:
        raise ValueError("abandoned boundary policy binding is missing")
    saved_policy = read_bytes(root, ArtifactRef.from_dict(policy["artifact"]), max_bytes=65536)
    relative_policy = str(Path(policy["path"]).relative_to(root))
    if _bytes(root, relative_policy, 65536) != saved_policy:
        raise ValueError("abandoned boundary policy changed")
    native_job = _json(root, "client/job.json")
    if (
        digest(native_job["command"]) != manifest["command_sha256"]
        or _bytes(root, "client/stdin.bin", 65536) != prompt
    ):
        raise ValueError("abandoned native command or prompt changed")
    expected_native_job = {
        "command": native_job["command"],
        "cwd": manifest["workspace"],
        "environment": manifest["environment"],
        "keep_group_leader": True,
        "owner_lease": "pipe-eof-v1",
    }
    owner = _stopped(
        root / "client",
        nonce=manifest["nonce"],
        expected_job=expected_native_job,
        max_output_bytes=manifest["max_output_bytes"],
    )
    if not _owner_absent(*owner):
        raise ValueError("original endpoint supervisor is still live or ambiguous")
    exchange = TextExchange(root / "exchange")
    if (
        exchange.manifest["invocation_id"] != manifest["exchange_invocation_id"]
        or exchange.manifest["requested_model"] != manifest["requested_model"]
        or exchange.manifest["approved_prompt"].encode() != prompt
        or exchange.manifest["output_schema"] != unique_json(schema.decode())
    ):
        raise ValueError("abandoned exchange scope mismatch")
    dispatch = _json(exchange.root, "dispatch.json")
    if (
        set(dispatch) != {"client", "upstream_request", "provider_requests_reserved"}
        or type(dispatch["provider_requests_reserved"]) is not int
        or dispatch["provider_requests_reserved"] != 1
    ):
        raise ValueError("invalid abandoned provider reservation")
    client = ArtifactRef.from_dict(dispatch["client"])
    if client.to_dict() != _json(exchange.root, "client.json"):
        raise ValueError("abandoned client request changed")
    original = read_bytes(exchange.root, client, max_bytes=MAX_REQUEST_BYTES)
    request = read_bytes(
        exchange.root,
        ArtifactRef.from_dict(dispatch["upstream_request"]),
        max_bytes=MAX_REQUEST_BYTES,
    )
    if request != exchange._request(original):
        raise ValueError("abandoned approved request changed")
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
