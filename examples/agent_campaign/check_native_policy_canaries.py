"""Run synthetic macOS permission canaries, without a model or real credentials."""

from __future__ import annotations

import argparse
from pathlib import Path

from autoengineering.agents.hosts.native_canaries import (
    probe_native_policy,
    recover_native_policy_probe,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--expected-digest", help="Verify saved evidence at this pin instead of rerunning probes"
    )
    args = parser.parse_args()
    receipt = (
        recover_native_policy_probe(args.output, expected_digest=args.expected_digest)
        if args.expected_digest is not None
        else probe_native_policy(args.output)
    )
    print(f"Native policy canaries: {receipt['status']}; host qualified: false", flush=True)
    return 0 if receipt["status"] == "passed" else 4


if __name__ == "__main__":
    raise SystemExit(main())
