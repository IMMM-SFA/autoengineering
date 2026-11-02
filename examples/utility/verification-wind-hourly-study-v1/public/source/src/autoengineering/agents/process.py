"""Owned POSIX process groups, bounded pipe capture and durable launch receipts.

This is lifecycle supervision. It is not a filesystem or network sandbox.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import os
import math
import hashlib
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
import uuid
from urllib.parse import urlsplit

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.execution import ProcessIdentity, _process_description, live_members
from autoengineering.campaign.records import identifier
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write


@dataclass(frozen=True)
class ProcessResult:
    status: str
    identity: ProcessIdentity | None
    returncode: int | None
    stdout: bytes
    stderr: bytes
    elapsed_seconds: float
    stopped: bool
    truncated: bool


class _WatchdogUnavailable(Exception):
    def __init__(self, status):
        self.status = status


def _stop_owned(process: subprocess.Popen, identity: ProcessIdentity, grace: float) -> bool:
    # An unreaped direct child cannot have its PID reused. After it exits, the
    # original group cannot be reused while any of its descendants remain.
    if process.poll() is None:
        if os.getpgid(process.pid) != identity.pgid:
            return False
    elif _process_description(identity.pid) is not None:
        return False
    for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, 1.0)):
        if not live_members(identity.pgid):
            process.wait(timeout=1)
            return True
        try:
            os.killpg(identity.pgid, sig)
        except ProcessLookupError:
            process.wait(timeout=1)
            return True
        except PermissionError:
            # The independent watchdog may have removed the group between
            # observation and signalling. A denied signal alone proves no stop.
            if live_members(identity.pgid):
                return False
            process.wait(timeout=1)
            return True
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            process.poll()
            if not live_members(identity.pgid):
                process.wait(timeout=1)
                return True
            time.sleep(0.01)
    return not live_members(identity.pgid)


def supervise_process(
    command: tuple[str, ...],
    *,
    directory: Path,
    cwd: Path,
    environment: Mapping[str, str],
    nonce: str,
    stdin: bytes,
    timeout_seconds: float,
    max_output_bytes: int,
    on_launch: Callable[[dict], None],
    cancelled: Callable[[], bool] = lambda: False,
    grace_seconds: float = 0.2,
    parent_watchdog: bool = False,
) -> ProcessResult:
    """Reserve externally first. Launch exactly once, retaining bounded raw bytes.

    The callback must durably record ownership. No executable is launched until
    it returns successfully. Existing directories are never reused.
    """
    if os.name != "posix":
        raise ValueError("host process supervision requires POSIX")
    identifier(nonce)
    if type(parent_watchdog) is not bool:
        raise ValueError("parent watchdog must be a boolean")
    if not command or any(type(value) is not str or not value for value in command):
        raise ValueError("process requires a trusted argument vector")
    if (
        any(
            type(value) not in (int, float) or not math.isfinite(value) or value <= 0
            for value in (timeout_seconds, grace_seconds)
        )
        or type(max_output_bytes) is not int
        or not 0 < max_output_bytes <= 65536
    ):
        raise ValueError("process limits must be positive")
    if type(stdin) is not bytes or len(stdin) > 65536:
        raise ValueError("process input exceeds 64 KiB")
    permitted_environment = {
        "PATH",
        "LANG",
        "LC_ALL",
        "HOME",
        "TMPDIR",
        "CODEX_HOME",
        "CLAUDE_CODE_TMPDIR",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "SSL_CERT_FILE",
    }
    if set(environment) - permitted_environment:
        raise ValueError("process environment contains undeclared or credential variables")
    if any(
        type(key) is not str or type(value) is not str or "\x00" in value
        for key, value in environment.items()
    ):
        raise ValueError("invalid process environment")
    if "CLAUDE_CODE_TMPDIR" in environment and (
        not environment["CLAUDE_CODE_TMPDIR"]
        or environment["CLAUDE_CODE_TMPDIR"] != environment.get("HOME")
    ):
        raise ValueError("Claude internal temporary directory must equal isolated HOME")
    for name in ("HTTP_PROXY", "HTTPS_PROXY"):
        if name in environment:
            parsed = urlsplit(environment[name])
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("proxy credentials cannot enter process artifacts")
    directory = Path(directory).absolute()
    checked_directory(directory.parent)
    directory.mkdir(mode=0o700)  # exclusive physical launch directory
    checked_directory(directory)
    durable_write(directory / "intent.json", canonical_json({"nonce": nonce}).encode())
    durable_write(directory / "stdin.bin", stdin)
    # Only explicit non-secret environment values are retained. Authentication
    # uses a scoped file, never an inherited key or token environment variable.
    job = {"command": list(command), "cwd": str(cwd), "environment": dict(environment)}
    if parent_watchdog:
        job["keep_group_leader"] = True
        job["owner_lease"] = "pipe-eof-v1"
    durable_write(directory / "job.json", canonical_json(job).encode())
    if cancelled():
        result = ProcessResult("cancelled", None, None, b"", b"", 0, True, False)
        _persist_result(directory, result)
        return result
    began = time.monotonic()
    lease = os.pipe() if parent_watchdog else None
    worker_command = [
        sys.executable,
        "-I",
        "-S",
        str(Path(__file__).with_name("process_worker.py")),
        "--nonce",
        nonce,
        "--job",
        str(directory / "job.json"),
    ]
    if lease is not None:
        worker_command.extend(("--owner-fd", str(lease[0])))
    try:
        process = subprocess.Popen(
            worker_command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            start_new_session=True,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            pass_fds=() if lease is None else (lease[0],),
        )
    except BaseException as exc:
        if lease is not None:
            for fd in lease:
                os.close(fd)
        if parent_watchdog and isinstance(exc, OSError):
            result = ProcessResult(
                "host_failure", None, None, b"", b"", time.monotonic() - began, True, False
            )
            _persist_result(directory, result)
            return result
        raise
    identity = ProcessIdentity(process.pid, process.pid, nonce, "unknown")
    selector = selectors.DefaultSelector()
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    status, stopped, truncated = "completed", False, False
    watchdog = None
    try:
        description = _process_description(process.pid)
        if description is None:
            raise ValueError("process ownership could not be established")
        identity = ProcessIdentity(process.pid, process.pid, nonce, description[0])
        durable_write(directory / "process.json", canonical_json(identity.to_dict()).encode())
        if parent_watchdog:
            try:
                watchdog = _start_watchdog(
                    directory, identity, began + timeout_seconds, grace_seconds, lease[0]
                )
            except _WatchdogUnavailable as exc:
                status = exc.status
        if status == "completed":
            on_launch(identity.to_dict())
            if parent_watchdog:
                if time.monotonic() >= began + timeout_seconds:
                    status = "timeout"
                elif cancelled():
                    status = "cancelled"
                elif watchdog.poll() is not None:
                    _abort_watchdog(directory, watchdog, "startup_failure")
                    status = "host_failure"
            if status == "completed":
                durable_write(
                    directory / "launch-gate.json", canonical_json({"nonce": nonce}).encode()
                )
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = began + timeout_seconds
        while selector.get_map() or process.poll() is None:
            if status != "completed":
                break
            if cancelled():
                status = "cancelled"
                break
            if time.monotonic() >= deadline:
                status = "timeout"
                break
            for key, _ in selector.select(timeout=0.02):
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                remaining = max_output_bytes - sum(len(value) for value in captured.values())
                captured[key.data].extend(chunk[:remaining])
                if len(chunk) > remaining:
                    status, truncated = "output_limit", True
                    break
            if truncated:
                break
            if process.poll() is not None and live_members(identity.pgid):
                # A returned executable is not proof that its descendants stopped.
                status = "descendant_survived"
                break
        if process.poll() is None or live_members(identity.pgid):
            stopped = _stop_owned(process, identity, grace_seconds)
        else:
            stopped = True
        if stopped:
            process.wait(timeout=1)
        if not stopped:
            status = "reconciliation_required"
        elif status == "completed" and process.returncode != 0:
            status = "host_failure"
    except BaseException:
        verified_stop = False
        try:
            verified_stop = _stop_owned(process, identity, grace_seconds)
        finally:
            # Evidence is retained even when the launch callback/observer fails.
            _persist_result(
                directory,
                ProcessResult(
                    "host_failure" if verified_stop else "reconciliation_required",
                    identity,
                    process.poll(),
                    bytes(captured["stdout"]),
                    bytes(captured["stderr"]),
                    time.monotonic() - began,
                    verified_stop,
                    truncated,
                ),
            )
        raise
    finally:
        selector.close()
        process.stdout.close()
        process.stderr.close()
        if lease is not None:
            for fd in lease:
                os.close(fd)
        if watchdog is not None:
            try:
                watchdog.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Retain the independent watchdog if group observation is uncertain.
                pass
    result = ProcessResult(
        status,
        identity,
        process.returncode,
        bytes(captured["stdout"]),
        bytes(captured["stderr"]),
        time.monotonic() - began,
        stopped,
        truncated,
    )
    _persist_result(directory, result)
    return result


def _start_watchdog(directory, target, deadline, grace, owner_fd):
    owner = _process_description(os.getpid())
    if owner is None:
        raise ValueError("watchdog owner could not be established")
    nonce = "watchdog-" + uuid.uuid4().hex
    raw = canonical_json(
        {
            "nonce": nonce,
            "target": target.to_dict(),
            "owner_pid": os.getpid(),
            "owner_started": owner[0],
            "deadline_monotonic": deadline,
            "grace_seconds": grace,
            "owner_lease": "pipe-eof-v1",
            "watchdog_sha256": hashlib.sha256(
                Path(__file__).with_name("process_watchdog.py").read_bytes()
            ).hexdigest(),
            "worker_sha256": hashlib.sha256(
                Path(__file__).with_name("process_worker.py").read_bytes()
            ).hexdigest(),
        }
    ).encode()
    path = directory / "watchdog-job.json"
    durable_write(path, raw)
    try:
        watchdog = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                str(Path(__file__).with_name("process_watchdog.py")),
                "--nonce",
                nonce,
                "--job",
                str(path),
                "--owner-fd",
                str(owner_fd),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            pass_fds=(owner_fd,),
        )
    except OSError:
        _abort_watchdog(directory, None, "startup_failure")
        raise _WatchdogUnavailable("host_failure") from None
    ready = directory / "watchdog-ready.json"
    limit = min(deadline, time.monotonic() + 2)
    while not ready.exists() and watchdog.poll() is None and time.monotonic() < limit:
        time.sleep(0.01)
    expected = {"nonce": nonce, "job_sha256": hashlib.sha256(raw).hexdigest(), "pid": watchdog.pid}
    try:
        verified = ready.exists() and _read_receipt(directory, ready.name) == expected
    except (OSError, ValueError):
        verified = False
    if not verified:
        expired = time.monotonic() >= deadline
        _abort_watchdog(directory, watchdog, "startup_timeout" if expired else "startup_failure")
        raise _WatchdogUnavailable("timeout" if expired else "host_failure")
    return watchdog


def _abort_watchdog(directory, watchdog, reason):
    # No launch gate is open. Reap only the direct child handle, never a stale PID.
    if watchdog is not None:
        if watchdog.poll() is None:
            watchdog.kill()
        watchdog.wait(timeout=2)
    job = _read_receipt(directory, "watchdog-job.json")
    durable_write(
        directory / "watchdog-aborted.json",
        canonical_json(
            {
                "nonce": job["nonce"],
                "job_sha256": hashlib.sha256(
                    confined_file(directory, "watchdog-job.json").read_bytes()
                ).hexdigest(),
                "pid": None if watchdog is None else watchdog.pid,
                "returncode": None if watchdog is None else watchdog.returncode,
                "reason": reason,
                "stopped": True,
            }
        ).encode(),
    )


def recover_watchdog_stop(directory: Path) -> dict:
    """Verify independent stop evidence after owner death. Never launch or signal.

    This proves local process termination only. It cannot prove that remote
    provider computation stopped, or reconstruct missing response/usage bytes.
    """
    directory = checked_directory(directory)
    job = _read_receipt(directory, "watchdog-job.json")
    aborted = (directory / "watchdog-aborted.json").exists()
    if aborted:
        result = _read_receipt(directory, "watchdog-aborted.json")
        pid = result.get("pid")
        if (
            (directory / "launch-gate.json").exists()
            or result.get("reason") not in ("startup_timeout", "startup_failure")
            or (pid is None and result.get("returncode") is not None)
            or (
                pid is not None
                and (type(pid) is not int or pid <= 0 or type(result.get("returncode")) is not int)
            )
        ):
            raise ValueError("invalid aborted watchdog receipt")
        if pid is not None:
            current = _process_description(pid)
            if current is not None and f"--nonce {job['nonce']}" in current[1]:
                raise ValueError("aborted watchdog is still live")
        receipts = (result,)
    else:
        ready = _read_receipt(directory, "watchdog-ready.json")
        result = _read_receipt(directory, "watchdog-result.json")
        if (
            type(ready.get("pid")) is not int
            or ready["pid"] <= 0
            or result.get("reason") not in ("group_stopped", "owner_lost", "timeout")
        ):
            raise ValueError("watchdog stop remains unverified")
        receipts = (ready, result)
    target = _read_receipt(directory, "process.json")
    intent = _read_receipt(directory, "intent.json")
    if (
        job.get("target") != target
        or job.get("owner_lease") != "pipe-eof-v1"
        or intent != {"nonce": target.get("nonce")}
        or type(target.get("pid")) is not int
        or target["pid"] <= 0
        or target.get("pgid") != target["pid"]
        or result.get("stopped") is not True
    ):
        raise ValueError("watchdog stop remains unverified")
    identifier(job.get("nonce"))
    job_hash = hashlib.sha256(
        confined_file(directory, "watchdog-job.json").read_bytes()
    ).hexdigest()
    for receipt in receipts:
        if receipt.get("nonce") != job["nonce"] or receipt.get("job_sha256") != job_hash:
            raise ValueError("watchdog receipt binding mismatch")
    for name in ("watchdog", "worker"):
        if (
            job.get(f"{name}_sha256")
            != hashlib.sha256(
                Path(__file__).with_name(f"process_{name}.py").read_bytes()
            ).hexdigest()
        ):
            raise ValueError("watchdog source identity changed")
    launch_job = _read_receipt(directory, "job.json")
    if (
        launch_job.get("keep_group_leader") is not True
        or launch_job.get("owner_lease") != "pipe-eof-v1"
        or live_members(target["pgid"])
    ):
        raise ValueError("watchdog group stop contradicted by current observation")
    return result


def _persist_result(directory: Path, result: ProcessResult):
    durable_write(directory / "stdout.bin", result.stdout)
    durable_write(directory / "stderr.bin", result.stderr)
    durable_write(
        directory / "completion.json",
        canonical_json(
            {
                "status": result.status,
                "identity": result.identity.to_dict() if result.identity else None,
                "returncode": result.returncode,
                "elapsed_seconds": result.elapsed_seconds,
                "stopped": result.stopped,
                "truncated": result.truncated,
                "schema_version": "1.0",
                "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
                "stdout_bytes": len(result.stdout),
                "stderr_bytes": len(result.stderr),
                "job_sha256": hashlib.sha256((directory / "job.json").read_bytes()).hexdigest(),
                "stdin_sha256": hashlib.sha256((directory / "stdin.bin").read_bytes()).hexdigest(),
            }
        ).encode(),
    )


def read_completion(directory: Path) -> dict:
    return _read_receipt(directory, "completion.json")


def _read_receipt(directory: Path, name: str) -> dict:
    path = confined_file(directory, name)
    if path.stat().st_size > 16384:
        raise ValueError("process completion receipt exceeds size limit")
    value = unique_json(path.read_text())
    if not isinstance(value, dict):
        raise ValueError("process receipt must be an object")
    return value


def recover_completed_process(
    directory: Path, *, nonce: str, max_output_bytes: int
) -> ProcessResult:
    """Reconstruct a checksummed completed process. Never launch or signal a process."""
    checked_directory(directory)
    intent = _read_receipt(directory, "intent.json")
    completion = read_completion(directory)
    if intent != {"nonce": nonce} or completion.get("schema_version") != "1.0":
        raise ValueError("process recovery nonce or receipt version mismatch")
    identity = completion.get("identity")
    if identity is not None:
        if not isinstance(identity, dict) or identity.get("nonce") != nonce:
            raise ValueError("process completion ownership mismatch")
        saved = _read_receipt(directory, "process.json")
        if identity != saved:
            raise ValueError("process completion and launch identity differ")
        identity = ProcessIdentity(**identity)
    if completion.get("stopped") is not True:
        raise ValueError("process stop remains unverified")
    for name in ("job", "stdin"):
        path = confined_file(directory, f"{name}.json" if name == "job" else "stdin.bin")
        if path.stat().st_size > 1048576 or hashlib.sha256(
            path.read_bytes()
        ).hexdigest() != completion.get(f"{name}_sha256"):
            raise ValueError("process recovery input digest mismatch")
    if identity is not None and _read_receipt(directory, "job.json").get("keep_group_leader"):
        recover_watchdog_stop(directory)
    captured = {}
    for name in ("stdout", "stderr"):
        ref = ArtifactRef(
            f"{name}.bin",
            completion.get(f"{name}_sha256"),
            completion.get(f"{name}_bytes"),
            "application/octet-stream",
            "process-supervisor",
            {},
        )
        captured[name] = read_bytes(directory, ref, max_bytes=max_output_bytes)
    if sum(map(len, captured.values())) > max_output_bytes:
        raise ValueError("process recovery output exceeds original allowance")
    if completion.get("status") not in (
        "completed",
        "cancelled",
        "timeout",
        "host_failure",
        "output_limit",
        "descendant_survived",
    ):
        raise ValueError("process completion status is not recoverable")
    if (
        type(completion.get("elapsed_seconds")) not in (int, float)
        or not math.isfinite(completion["elapsed_seconds"])
        or completion["elapsed_seconds"] < 0
    ):
        raise ValueError("invalid process recovery duration")
    if type(completion.get("truncated")) is not bool:
        raise ValueError("invalid process truncation receipt")
    if completion["status"] == "completed" and (
        type(completion.get("returncode")) is not int
        or completion["returncode"] != 0
        or completion["truncated"]
    ):
        raise ValueError("completed process has contradictory exit/output receipts")
    return ProcessResult(
        completion["status"],
        identity,
        completion.get("returncode"),
        captured["stdout"],
        captured["stderr"],
        completion["elapsed_seconds"],
        True,
        completion["truncated"],
    )
