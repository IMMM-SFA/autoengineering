"""One trusted upstream command with hard local ownership and bounded response.

This grants no provider or network authority. The caller supplies a fixed
transport implementation and separately qualifies its credentials and egress.
Arguments must contain no credentials. No shell or inherited environment is used.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import math
from pathlib import Path
import time
import uuid

from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import (
    recover_completed_process,
    recover_watchdog_stop,
    supervise_process,
)
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write

from .response_boundary import MAX_RESPONSE_BYTES
from .text_exchange import MAX_REQUEST_BYTES

VERSION = "command-upstream-1.0"
OUTPUT_LIMIT = 8192


class UpstreamProcessError(ValueError):
    """Static public status. Raw executable diagnostics remain private evidence."""

    def __init__(self, status):
        self.status = status
        super().__init__("upstream process: " + status)


def _file_identity(path):
    path = Path(path).resolve(strict=True)
    regular = confined_file(path.parent, path.name)
    if regular.stat().st_size > 134217728:
        raise ValueError("upstream executable/source exceeds size limit")
    with regular.open("rb") as stream:
        return str(path), hashlib.file_digest(stream, "sha256").hexdigest()


def _json(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise ValueError("upstream receipt exceeds size limit")
    return unique_json(path.read_text())


def _check_sources(manifest):
    if manifest.get("source_identity") != host_source_identity():
        raise ValueError("upstream host source identity changed")
    for path, expected in manifest["sources"].items():
        resolved, actual = _file_identity(path)
        if resolved != path or actual != expected:
            raise ValueError("upstream executable/source changed")


class CommandUpstream:
    """Single-use callback for TextExchange. Existing attempts are never relaunched.

    Command arguments contain exactly one `{request}` and one `{response}` slot.
    Both are private file paths. stdout/stderr are bounded diagnostics, not the
    response channel. Declared sources include the executable automatically.
    The absolute monotonic deadline includes preparation and process startup.
    """

    def __init__(
        self,
        directory: Path,
        *,
        command: tuple[str, ...],
        source_files: tuple[Path, ...],
        deadline_monotonic: float,
        cancelled: Callable[[], bool] = lambda: False,
        fault: Callable[[str], None] = lambda _stage: None,
        on_launch: Callable[[dict], None] = lambda _receipt: None,
    ):
        if (
            not command
            or any(type(arg) is not str or not arg or "\x00" in arg for arg in command)
            or command.count("{request}") != 1
            or command.count("{response}") != 1
            or not Path(command[0]).is_absolute()
            or type(deadline_monotonic) not in (int, float)
            or not math.isfinite(deadline_monotonic)
            or deadline_monotonic <= 0
        ):
            raise ValueError("invalid fixed upstream command or deadline")
        self.directory = Path(directory).absolute()
        files = (Path(command[0]), *source_files)
        identities = tuple(_file_identity(path) for path in files)
        aliases = {
            alias: resolved
            for path, (resolved, _) in zip(files, identities)
            for alias in (str(path), str(path.absolute()))
        }
        # Execute the same physical files whose bytes were hashed. In particular,
        # changing an interpreter or declared script symlink cannot retarget it.
        self.command = tuple(aliases.get(arg, arg) for arg in command)
        self.sources = dict(identities)
        self.deadline = deadline_monotonic
        self.cancelled, self.fault, self.on_launch = cancelled, fault, on_launch

    def __call__(self, request: bytes) -> bytes:
        if type(request) is not bytes or not 0 < len(request) <= MAX_REQUEST_BYTES:
            raise ValueError("upstream request size limit")
        root = self.directory
        checked_directory(root.parent)
        root.mkdir(mode=0o700)
        nonce = "upstream-" + uuid.uuid4().hex
        manifest = {
            "version": VERSION,
            "nonce": nonce,
            "source_identity": host_source_identity(),
            "command": list(self.command),
            "sources": self.sources,
            "request_sha256": hashlib.sha256(request).hexdigest(),
            "request_bytes": len(request),
            "deadline_monotonic": self.deadline,
            "max_output_bytes": OUTPUT_LIMIT,
            "max_response_bytes": MAX_RESPONSE_BYTES,
        }
        durable_write(root / "upstream.json", canonical_json(manifest).encode())
        durable_write(root / "request.bin", request)
        durable_write(root / "response.bin", b"")
        _check_sources(manifest)
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            durable_write(root / "outcome.json", canonical_json({"status": "timeout"}).encode())
            raise UpstreamProcessError("timeout")
        command = tuple(
            str(root / "request.bin")
            if arg == "{request}"
            else str(root / "response.bin")
            if arg == "{response}"
            else arg
            for arg in self.command
        )
        result = supervise_process(
            command,
            directory=root / "process",
            cwd=root,
            environment={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            nonce=nonce,
            stdin=b"",
            timeout_seconds=remaining,
            max_output_bytes=OUTPUT_LIMIT,
            on_launch=self.on_launch,
            cancelled=self.cancelled,
            parent_watchdog=True,
        )
        _check_sources(manifest)
        if result.status != "completed" or not result.stopped:
            durable_write(root / "outcome.json", canonical_json({"status": result.status}).encode())
            raise UpstreamProcessError(result.status)
        if time.monotonic() >= self.deadline:
            durable_write(root / "outcome.json", canonical_json({"status": "timeout"}).encode())
            raise UpstreamProcessError("timeout")
        try:
            response = confined_file(root, "response.bin")
            if not 0 < response.stat().st_size <= MAX_RESPONSE_BYTES:
                raise ValueError("response size")
            with response.open("rb") as stream:
                raw = stream.read(MAX_RESPONSE_BYTES + 1)
            if not 0 < len(raw) <= MAX_RESPONSE_BYTES:
                raise ValueError("response size")
        except (OSError, ValueError):
            durable_write(
                root / "outcome.json", canonical_json({"status": "invalid_response"}).encode()
            )
            raise UpstreamProcessError("invalid_response") from None
        request_ref = ArtifactRef(
            "request.bin",
            manifest["request_sha256"],
            len(request),
            "application/octet-stream",
            nonce,
            {},
        )
        read_bytes(root, request_ref, max_bytes=MAX_REQUEST_BYTES)
        accepted = time.monotonic()
        if accepted >= self.deadline:
            durable_write(root / "outcome.json", canonical_json({"status": "timeout"}).encode())
            raise UpstreamProcessError("timeout")
        reference = ArtifactRef(
            "response.bin",
            hashlib.sha256(raw).hexdigest(),
            len(raw),
            "application/octet-stream",
            nonce,
            {"accepted_monotonic": accepted},
        )
        durable_write(root / "response.json", canonical_json(reference.to_dict()).encode())
        self.fault("before_outcome_commit")
        durable_write(root / "outcome.json", canonical_json({"status": "completed"}).encode())
        return raw


def recover_command_upstream(directory: Path) -> bytes:
    """Read-only recovery of saved complete response bytes. Never start a command.

    Missing response receipts remain uncertain, including after supervisor death.
    Watchdog evidence alone cannot invent response bytes or provider usage.
    """
    root = checked_directory(directory)
    manifest = _json(root, "upstream.json")
    if (
        manifest.get("version") != VERSION
        or manifest.get("max_output_bytes") != OUTPUT_LIMIT
        or manifest.get("max_response_bytes") != MAX_RESPONSE_BYTES
    ):
        raise ValueError("incompatible upstream attempt")
    _check_sources(manifest)
    request = ArtifactRef(
        "request.bin",
        manifest["request_sha256"],
        manifest["request_bytes"],
        "application/octet-stream",
        manifest["nonce"],
        {},
    )
    read_bytes(root, request, max_bytes=MAX_REQUEST_BYTES)
    result = recover_completed_process(
        root / "process", nonce=manifest["nonce"], max_output_bytes=OUTPUT_LIMIT
    )
    command = [
        str(root / "request.bin")
        if arg == "{request}"
        else str(root / "response.bin")
        if arg == "{response}"
        else arg
        for arg in manifest["command"]
    ]
    job = _json(root / "process", "job.json")
    if job != {
        "command": command,
        "cwd": str(root),
        "environment": {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        "keep_group_leader": True,
        "owner_lease": "pipe-eof-v1",
    }:
        raise ValueError("upstream process command binding mismatch")
    if result.status != "completed":
        raise UpstreamProcessError(result.status)
    if (root / "outcome.json").exists():
        outcome = _json(root, "outcome.json")
        if outcome != {"status": "completed"}:
            raise UpstreamProcessError(outcome.get("status", "reconciliation_required"))
    reference = ArtifactRef.from_dict(_json(root, "response.json"))
    if reference.path != "response.bin" or reference.producer != manifest["nonce"]:
        raise ValueError("upstream response ownership mismatch")
    accepted = reference.metadata.get("accepted_monotonic")
    if (
        type(accepted) not in (int, float)
        or not math.isfinite(accepted)
        or not 0 < accepted < manifest["deadline_monotonic"]
    ):
        raise ValueError("upstream response acceptance exceeded deadline")
    return read_bytes(root, reference, max_bytes=MAX_RESPONSE_BYTES)


def inspect_command_stop(directory: Path) -> dict:
    """Observe an owned command stop without changing its original result.

    This proves local group absence only. It never turns an uncertain or failed
    command into a completed response. The caller supplies trusted configuration.
    """
    root = Path(directory).absolute()
    if not root.exists() and not root.is_symlink():
        return {"state": "not_launched"}
    try:
        root = checked_directory(root)
        process = root / "process"
        if not process.exists() and not process.is_symlink():
            # The durable process directory precedes Popen in this protocol.
            return {"state": "not_launched"}
        manifest = _json(root, "upstream.json")
        _check_sources(manifest)
        command = [
            str(root / "request.bin")
            if arg == "{request}"
            else str(root / "response.bin")
            if arg == "{response}"
            else arg
            for arg in manifest["command"]
        ]
        if (
            _json(process, "job.json")
            != {
                "command": command,
                "cwd": str(root),
                "environment": {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
                "keep_group_leader": True,
                "owner_lease": "pipe-eof-v1",
            }
            or _json(process, "process.json")["nonce"] != manifest["nonce"]
        ):
            raise ValueError("command stop scope mismatch")
        stopped = recover_watchdog_stop(process)
        result_name = (
            "watchdog-aborted.json"
            if (process / "watchdog-aborted.json").exists()
            else "watchdog-result.json"
        )
        return {
            "state": "verified_stopped",
            "watchdog_reason": stopped["reason"],
            "bindings": {
                name: hashlib.sha256(confined_file(root, name).read_bytes()).hexdigest()
                for name in (
                    "upstream.json",
                    "process/job.json",
                    "process/process.json",
                    "process/watchdog-job.json",
                    "process/" + result_name,
                )
            },
        }
    except (ValueError, OSError, KeyError):
        return {"state": "unresolved"}
