"""Private supervisor trampoline. Commands come only from the trusted local broker."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import time

from .store import durable_write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nonce", required=True)
    parser.add_argument("--job", type=Path, required=True)
    args = parser.parse_args()
    job = json.loads(args.job.read_text())
    receipt = args.job.parent / "action-start.json"
    durable_write(
        receipt, json.dumps({"nonce": args.nonce, "monotonic": time.monotonic()}).encode()
    )
    result = subprocess.run(job["command"], check=False, cwd=job["cwd"])
    durable_write(
        args.job.parent / "action-finish.json",
        json.dumps(
            {
                "nonce": args.nonce,
                "returncode": result.returncode,
                "monotonic": time.monotonic(),
            }
        ).encode(),
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
