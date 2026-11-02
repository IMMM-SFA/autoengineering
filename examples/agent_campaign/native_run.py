"""Run, resume or read the separately authorized native matched comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from autoengineering.campaign.serialization import canonical_json
from .native_status import read_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "resume", "status"))
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--preparation-digest")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--runtime-digest")
    parser.add_argument("--host-config", type=Path)
    parser.add_argument("--conformance-runtime-digest")
    parser.add_argument("--max-new-cases", type=int, default=3)
    parser.add_argument("--max-new-evaluations", type=int)
    args = parser.parse_args()
    if args.action == "status":
        if args.runtime is None or args.runtime_digest is None:
            parser.error("status requires --runtime and --runtime-digest")
        value = read_report(args.runtime, expected_digest=args.runtime_digest)
    else:
        from autoengineering.agents.host_configuration import HostConfiguration
        from .native_runtime import NativeRuntime

        if any(
            v is None
            for v in (
                args.preparation,
                args.preparation_digest,
                args.host_config,
                args.conformance_runtime_digest,
            )
        ):
            parser.error(
                "execution requires preparation, both prerequisite pins and host configuration"
            )
        if not 1 <= args.max_new_cases <= 3 or (
            args.max_new_evaluations is not None and args.max_new_evaluations < 1
        ):
            parser.error("case cap must be in 1..3 and evaluation pause must be positive")
        options = {
            "expected_digest": args.preparation_digest,
            "configuration": HostConfiguration.from_file(args.host_config),
            "conformance_runtime_digest": args.conformance_runtime_digest,
        }
        if args.action == "run":
            runtime = NativeRuntime.create(args.preparation, **options)
        else:
            if args.runtime_digest is None:
                parser.error("resume requires --runtime-digest")
            runtime = NativeRuntime.open(
                args.preparation, runtime_digest=args.runtime_digest, **options
            )
        print(
            canonical_json(
                {
                    "runtime_root": str(runtime.batch.root),
                    "runtime_digest": runtime.batch.digest,
                    "preparation_digest": runtime.pin,
                }
            ),
            file=sys.stderr,
            flush=True,
        )
        before = runtime.batch.report()
        value = runtime.advance(
            max_new_cases=args.max_new_cases, max_new_evaluations=args.max_new_evaluations
        )
        print(
            canonical_json(
                {
                    "execution_delta": {
                        "host_reservations_added": value["host_reservations_charged"]
                        - before["host_reservations_charged"],
                        "scientific_reservations_added": value["scientific_reservations_charged"]
                        - before["scientific_reservations_charged"],
                        "finished_verdicts_reused": len(before["case_results"]),
                    }
                }
            ),
            file=sys.stderr,
            flush=True,
        )
    print(canonical_json(value))
    return (
        4
        if value["status"] == "failed"
        else 3
        if value["status"] == "reconciliation_required"
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
