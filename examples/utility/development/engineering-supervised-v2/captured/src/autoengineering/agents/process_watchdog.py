"""Standalone trusted watchdog for an explicitly owned POSIX process group.

This is lifecycle supervision of trusted executables, not an escape boundary.
The nonce-bearing group leader must remain alive until its descendants stop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import stat
import subprocess
import time


def describe(pid):
    result = subprocess.run(
        ["/bin/ps", "-p", str(pid), "-o", "lstart=", "-o", "stat=", "-o", "command="],
        capture_output=True,
        text=True,
        timeout=1,
        check=False,
    )
    line = result.stdout.strip()
    if result.returncode or not line:
        return None
    rest = line[24:].strip().split(None, 1)
    if len(rest) != 2 or rest[0].startswith("Z"):
        return None
    return line[:24], rest[1]


def members(pgid):
    result = subprocess.run(
        ["/bin/ps", "-axo", "pid=,pgid=,stat="],
        capture_output=True,
        text=True,
        timeout=1,
        check=True,
    )
    return tuple(
        int(parts[0])
        for line in result.stdout.splitlines()
        if len(parts := line.split()) == 3
        and int(parts[1]) == pgid
        and not parts[2].startswith("Z")
    )


def matches(target):
    description = describe(target["pid"])
    if description is None:
        return False
    try:
        return (
            description[0] == target["started"]
            and f"--nonce {target['nonce']}" in description[1]
            and os.getpgid(target["pid"]) == target["pgid"] == target["pid"]
        )
    except ProcessLookupError:
        return False


def save(path, payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    pending = path.with_name(path.name + ".pending")
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(pending, path)
    pending.unlink()
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def watch(job, ready, owner_lost):
    target = job["target"]
    if not matches(target):
        return "ownership_unverified", not members(target["pgid"])
    ready()
    while members(target["pgid"]):
        reason = (
            "owner_lost"
            if owner_lost()
            else "timeout"
            if time.monotonic() >= job["deadline_monotonic"]
            else None
        )
        if reason is None:
            time.sleep(0.02)
            continue
        for sig, grace in ((signal.SIGTERM, job["grace_seconds"]), (signal.SIGKILL, 1.0)):
            if not members(target["pgid"]):
                return reason, True
            if not matches(target):
                # The supervising owner may have stopped the group between the
                # membership observation and identity check. Reobserve absence.
                if not members(target["pgid"]):
                    return reason, True
                return "ownership_unverified", False
            try:
                os.killpg(target["pgid"], sig)
            except ProcessLookupError:
                return reason, not members(target["pgid"])
            deadline = time.monotonic() + grace
            while time.monotonic() < deadline:
                if not members(target["pgid"]):
                    return reason, True
                time.sleep(0.01)
        return reason, not members(target["pgid"])
    return "group_stopped", True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--owner-fd", type=int, required=True)
    args = parser.parse_args()
    raw = args.job.read_bytes()
    job = json.loads(raw)
    binding = {"nonce": args.nonce, "job_sha256": hashlib.sha256(raw).hexdigest()}
    if job["nonce"] != args.nonce or job.get("owner_lease") != "pipe-eof-v1":
        return 125
    if not stat.S_ISFIFO(os.fstat(args.owner_fd).st_mode):
        return 125

    def owner_lost():
        if not select.select([args.owner_fd], [], [], 0)[0]:
            return False
        if os.read(args.owner_fd, 1) != b"":
            raise ValueError("unexpected owner lease data")
        return True

    try:
        reason, stopped = watch(
            job,
            lambda: save(
                args.job.with_name("watchdog-ready.json"),
                {
                    **binding,
                    "pid": os.getpid(),
                },
            ),
            owner_lost,
        )
    except (OSError, ValueError, subprocess.SubprocessError):
        reason, stopped = "observation_failed", False
    save(
        args.job.with_name("watchdog-result.json"),
        {
            **binding,
            "reason": reason,
            "stopped": stopped,
        },
    )
    return 0 if stopped else 125


if __name__ == "__main__":
    raise SystemExit(main())
