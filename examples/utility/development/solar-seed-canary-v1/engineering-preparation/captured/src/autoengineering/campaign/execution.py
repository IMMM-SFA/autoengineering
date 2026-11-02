"""POSIX lifecycle supervision with durable receipts and an independent cancel inbox."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from .records import identifier, Request, Response, sha256
from .serialization import canonical_json, unique_json
from .spec import ExecutionSpec
from .store import checked_directory, durable_write


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    pgid: int
    nonce: str
    started: str

    def to_dict(self):
        return {"pid": self.pid, "pgid": self.pgid, "nonce": self.nonce, "started": self.started}


@dataclass(frozen=True)
class SupervisedResult:
    status: str
    stop_reason: str | None
    returncode: int | None
    elapsed_seconds: float
    identity: ProcessIdentity
    stopped: bool
    receipt_valid: bool


def _process_description(pid: int) -> tuple[str, str] | None:
    result = subprocess.run(
        ["ps", "-p", str(pid), "-o", "lstart=", "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode or not result.stdout.strip():
        return None
    line = result.stdout.strip()
    return line[:24], line[24:].strip()


def identity_matches(identity: ProcessIdentity) -> bool:
    description = _process_description(identity.pid)
    if description is None:
        return False
    started, command = description
    if started != identity.started or f"--nonce {identity.nonce}" not in command:
        return False
    try:
        return os.getpgid(identity.pid) == identity.pgid == identity.pid
    except ProcessLookupError:
        return False


def live_members(pgid: int) -> tuple[int, ...]:
    result = subprocess.run(
        ["ps", "-axo", "pid=,pgid=,stat="], capture_output=True, text=True, check=True
    )
    members = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) == 3 and int(parts[1]) == pgid and not parts[2].startswith("Z"):
            members.append(int(parts[0]))
    return tuple(members)


def cancellation_intent(
    root: Path,
    request_id: str,
    *,
    campaign_id: str,
    envelope: Request | None = None,
    revision: int = 0,
) -> dict:
    """Deposit without acquiring the event-journal lock. Identical retries are harmless."""
    identifier(request_id)
    identifier(campaign_id)
    root = checked_directory(root)
    control = checked_directory(root / "control")
    payload = {
        "schema_version": "1.0",
        "campaign_id": campaign_id,
        "request_id": request_id,
        "operation": "cancel",
    }
    path = control / f"cancel-{request_id}.json"
    if envelope is not None:
        payload["request_digest"] = envelope.digest
        payload["response"] = Response(
            request_id, "ok", revision, {"status": "queued"}, None, ()
        ).to_dict()
    if path.exists():
        if path.is_symlink():
            raise ValueError("cancellation request conflict")
        previous = unique_json(path.read_text())
        if envelope is not None and previous.get("request_digest") == envelope.digest:
            return previous
    raw = (canonical_json(payload) + "\n").encode()
    try:
        durable_write(path, raw)
    except FileExistsError:
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError("cancellation request conflict") from None
    return payload


def pending_cancellations(root: Path, campaign_id: str) -> tuple[dict, ...]:
    control = checked_directory(root / "control")
    intents = []
    for path in sorted(control.glob("cancel-*.json")):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 65536:
            raise ValueError("invalid cancellation intent")
        payload = unique_json(path.read_text())
        expected = {"schema_version", "campaign_id", "request_id", "operation"}
        if (
            not isinstance(payload, dict)
            or not expected <= set(payload)
            or set(payload) - expected - {"request_digest", "response"}
        ):
            raise ValueError("invalid cancellation schema")
        if "request_digest" in payload:
            sha256(payload["request_digest"])
            response = Response.from_dict(payload["response"])
            if response.request_id != payload["request_id"] or response.status != "ok":
                raise ValueError("invalid cancellation response")
        identifier(payload["request_id"])
        if (
            payload["schema_version"] != "1.0"
            or payload["campaign_id"] != campaign_id
            or payload["operation"] != "cancel"
            or path.name != f"cancel-{payload['request_id']}.json"
        ):
            raise ValueError("cancellation identity mismatch")
        intents.append(payload)
    return tuple(intents)


def _terminate_owned(
    process: subprocess.Popen, identity: ProcessIdentity, settings: ExecutionSpec
) -> bool:
    # A live Popen handle owns the original group. If its root has been reused, refuse
    # to signal it. Recovery without that handle requires identity_matches first.
    if process.poll() is None and not identity_matches(identity):
        return False
    if process.poll() is not None and _process_description(identity.pid) is not None:
        return False
    for sig, duration in (
        (signal.SIGTERM, settings.termination_grace_seconds),
        (signal.SIGKILL, settings.kill_wait_seconds),
    ):
        try:
            os.killpg(identity.pgid, sig)
        except ProcessLookupError:
            return True
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            process.poll()
            if not live_members(identity.pgid):
                process.wait(timeout=settings.kill_wait_seconds)
                return True
            time.sleep(0.02)
    return not live_members(identity.pgid)


def supervise(
    command: tuple[str, ...],
    *,
    root: Path,
    attempt_id: str,
    campaign_id: str,
    settings: ExecutionSpec,
    cwd: Path,
    invocation_remaining_seconds: float | None = None,
    launch_nonce: str | None = None,
) -> SupervisedResult:
    """One physical action per supervised process, with per-action timeout.

    The caller must durably commit its AttemptRecord before calling this function.
    A study bridge invokes this for each action; it never times a whole study as one action.
    """
    if os.name != "posix":
        raise ValueError("campaign process supervision requires POSIX")
    identifier(attempt_id)
    root = checked_directory(root)
    attempts = checked_directory(root / "attempts")
    if pending_cancellations(root, campaign_id):
        raise ValueError("cancellation pending before launch")
    if not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("trusted command must be a nonempty argument vector")
    attempt = attempts / attempt_id
    attempt.mkdir(mode=0o700)
    nonce = launch_nonce or uuid.uuid4().hex
    identifier(nonce)
    durable_write(
        attempt / "job.json", canonical_json({"command": list(command), "cwd": str(cwd)}).encode()
    )
    durable_write(attempt / "launch-intent.json", canonical_json({"nonce": nonce}).encode())
    stdout = open(attempt / "stdout.log", "xb")
    stderr = open(attempt / "stderr.log", "xb")
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "autoengineering.campaign.worker",
                "--nonce",
                nonce,
                "--job",
                str(attempt / "job.json"),
            ],
            cwd=cwd,
            start_new_session=True,
            stdout=stdout,
            stderr=stderr,
        )
    finally:
        stdout.close()
        stderr.close()
    try:
        description = _process_description(process.pid)
        identity = ProcessIdentity(
            process.pid, process.pid, nonce, description[0] if description else "unknown"
        )
        durable_write(attempt / "process.json", canonical_json(identity.to_dict()).encode())
    except BaseException:
        # This is the just-created, still-owned Popen group. Do not leave scientific
        # work behind if process inspection or receipt durability itself fails.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=settings.kill_wait_seconds)
        raise
    stop_reason = None
    stopped = False
    deadline = started + settings.timeout_seconds
    if invocation_remaining_seconds is not None:
        deadline = min(deadline, started + invocation_remaining_seconds)
    try:
        while process.poll() is None:
            if pending_cancellations(root, campaign_id):
                stop_reason = "cancelled"
                break
            if time.monotonic() >= deadline:
                stop_reason = "timeout"
                break
            time.sleep(0.02)
        if stop_reason is not None or live_members(identity.pgid):
            stopped = _terminate_owned(process, identity, settings)
        else:
            stopped = True
        if stopped:
            process.wait(timeout=settings.kill_wait_seconds)
    except BaseException:
        _terminate_owned(process, identity, settings)
        raise
    elapsed = time.monotonic() - started
    valid = False
    if (attempt / "action-start.json").is_file() and (attempt / "action-finish.json").is_file():
        try:
            start = json.loads((attempt / "action-start.json").read_text())
            finish = json.loads((attempt / "action-finish.json").read_text())
            valid = (
                start["nonce"] == finish["nonce"] == nonce
                and start["monotonic"] <= finish["monotonic"]
                and finish["returncode"] == process.returncode
            )
        except (ValueError, KeyError, TypeError):
            pass
    if not stopped:
        status = "infrastructure_failure"
    elif stop_reason == "timeout":
        status = "timeout"
    elif stop_reason == "cancelled":
        status = "infrastructure_failure"
    elif not valid:
        status = "infrastructure_failure"
    else:
        status = "success" if process.returncode == 0 else "model_failure"
    result = SupervisedResult(
        status, stop_reason, process.returncode, elapsed, identity, stopped, valid
    )
    durable_write(
        attempt / "supervisor-result.json",
        canonical_json(
            {
                "status": status,
                "stop_reason": stop_reason,
                "returncode": process.returncode,
                "elapsed_seconds": elapsed,
                "identity": identity.to_dict(),
                "stopped": stopped,
                "receipt_valid": valid,
            }
        ).encode(),
    )
    return result


def stop_recovered(identity: ProcessIdentity, settings: ExecutionSpec) -> bool:
    """Explicit reconciliation can stop only a still-verifiable owned process group."""
    if not identity_matches(identity):
        return False
    for sig, duration in (
        (signal.SIGTERM, settings.termination_grace_seconds),
        (signal.SIGKILL, settings.kill_wait_seconds),
    ):
        try:
            os.killpg(identity.pgid, sig)
        except ProcessLookupError:
            return True
        deadline = time.monotonic() + duration
        while time.monotonic() < deadline:
            if not live_members(identity.pgid):
                return True
            time.sleep(0.02)
    return not live_members(identity.pgid)
