"""Trusted POSIX trampoline. Standalone standard-library script, never worker code.

The launcher persists ownership before opening the gate. If it dies before the
acknowledgment, this process exits without launching the requested executable.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--owner-fd", type=int)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    if job.get("owner_lease") == "pipe-eof-v1" and args.owner_fd is None:
        return 125

    def owner_lost():
        return args.owner_fd is not None and bool(select.select([args.owner_fd], [], [], 0)[0])

    keep_leader = job.get("keep_group_leader", False)
    if keep_leader:
        # Keep the nonce-bearing leader verifiable through TERM/KILL escalation.
        # A caught handler resets to default when the command execs.
        signal.signal(signal.SIGTERM, lambda *_: None)
    gate = args.job.parent / "launch-gate.json"
    deadline = time.monotonic() + 5
    while not gate.exists():
        if owner_lost() or time.monotonic() >= deadline:
            return 125
        time.sleep(0.01)
    if owner_lost() or json.loads(gate.read_text()) != {"nonce": args.nonce}:
        return 125
    prompt = (args.job.parent / "stdin.bin").read_bytes()
    process = subprocess.Popen(
        job["command"], cwd=job["cwd"], env=job["environment"], stdin=subprocess.PIPE
    )
    process.communicate(prompt)
    if keep_leader:
        while True:
            listing = subprocess.run(
                ["/bin/ps", "-axo", "pid=,pgid=,stat="],
                capture_output=True,
                text=True,
                timeout=1,
                check=True,
                start_new_session=True,
            )
            remaining = [
                int(parts[0])
                for line in listing.stdout.splitlines()
                if len(parts := line.split()) == 3
                and int(parts[1]) == os.getpgrp()
                and not parts[2].startswith("Z")
                and int(parts[0]) != os.getpid()
            ]
            if not remaining:
                break
            time.sleep(0.02)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
