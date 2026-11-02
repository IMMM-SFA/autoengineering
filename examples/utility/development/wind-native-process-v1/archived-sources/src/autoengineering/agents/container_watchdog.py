"""Standalone trusted watchdog for one labelled local container.

Runs outside the scientific supervisor's process group. Parent death cannot
leave a sleeping candidate running past its declared wall deadline.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time


def write(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("x") as stream:
        json.dump(value, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(temporary, path)
    temporary.unlink()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    root = args.job.parent
    if job["nonce"] != args.nonce:
        return 125
    command = [job["docker"], "--host", job["endpoint"], "--config", job["config"]]
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}

    def inspect():
        result = subprocess.run(
            command + ["inspect", "--format", "{{json .}}", job["container_id"]],
            capture_output=True,
            timeout=3,
            env=environment,
        )
        if result.returncode:
            raise ValueError("container ownership inspection failed")
        value = json.loads(result.stdout)
        if (
            value["Id"] != job["container_id"]
            or value["Config"]["Labels"].get("autoengineering.nonce") != args.nonce
            or value["Config"]["Labels"].get("autoengineering.intent") != job["intent_digest"]
        ):
            raise ValueError("container ownership mismatch")
        return value

    try:
        inspect()
        write(root / "watchdog-ready.json", {"nonce": args.nonce, "pid": os.getpid()})
        reason = None
        while True:
            current = inspect()
            if current["State"]["Status"] not in ("created", "running", "restarting"):
                break
            if (root / "stop-container.json").exists():
                reason = "cancelled"
            elif time.monotonic() >= job["deadline"]:
                reason = "timeout"
            if reason:
                # Inspect the exact immutable ID and labels again before signalling.
                current = inspect()
                if current["State"]["Status"] == "created":
                    removed = subprocess.run(
                        command + ["rm", job["container_id"]],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=3,
                        env=environment,
                    )
                    if removed.returncode == 0:
                        write(
                            root / "watchdog-result.json",
                            {
                                "nonce": args.nonce,
                                "container_id": job["container_id"],
                                "reason": reason,
                                "stopped": True,
                                "removed_before_start": True,
                                "exitcode": None,
                                "oom_killed": False,
                            },
                        )
                        return 0
                subprocess.run(
                    command + ["kill", job["container_id"]],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=3,
                    env=environment,
                )
                current = inspect()
                if current["State"]["Running"]:
                    raise ValueError("container stop not verified")
                break
            time.sleep(0.05)
        write(
            root / "watchdog-result.json",
            {
                "nonce": args.nonce,
                "container_id": job["container_id"],
                "reason": reason,
                "stopped": not current["State"]["Running"],
                "exitcode": current["State"]["ExitCode"],
                "oom_killed": current["State"]["OOMKilled"],
            },
        )
        return 0
    except Exception:
        write(
            root / "watchdog-result.json",
            {
                "nonce": args.nonce,
                "container_id": job["container_id"],
                "reason": "reconciliation_required",
                "stopped": False,
            },
        )
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
