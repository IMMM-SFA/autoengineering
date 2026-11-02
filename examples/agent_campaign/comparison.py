"""Run, resume or inspect the frozen authored synthetic comparison.

Status imports only the evidence reader. Execution APIs remain available through
lazy attributes for existing Python callers and preparation builders.
"""

from __future__ import annotations

import argparse
from importlib import import_module
from pathlib import Path

from autoengineering.campaign.serialization import canonical_json
from .comparison_status import read_report, reconstruct_report

_RUNTIME_EXPORTS = frozenset(
    (
        "VERSION",
        "CANDIDATES",
        "DRIVER_FILES",
        "PROTOCOL",
        "PROTOCOL_DIGEST",
        "FrozenPool",
        "MatchedFourRoleBroker",
        "MatchedSingleAgentBroker",
        "ComparisonCase",
        "ComparisonPreparation",
        "batch_cases",
        "load",
        "Runtime",
    )
)


def __getattr__(name):
    if name in _RUNTIME_EXPORTS:
        return getattr(import_module(".comparison_runtime", __package__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def report(batch, preparation_digest):
    """Preserve the Python reader API without importing the execution module."""
    return reconstruct_report(batch, preparation_digest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "resume", "status"))
    parser.add_argument("--preparation", type=Path)
    parser.add_argument("--preparation-digest")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--runtime-digest")
    parser.add_argument("--max-new-cases", type=int, default=3)
    parser.add_argument("--max-new-evaluations", type=int)
    args = parser.parse_args()
    if not 1 <= args.max_new_cases <= 3 or (
        args.max_new_evaluations is not None and args.max_new_evaluations < 1
    ):
        parser.error("case cap must be in 1..3 and evaluation pause must be positive")
    if args.action == "status":
        if args.runtime is None or args.runtime_digest is None:
            parser.error("status requires --runtime and --runtime-digest")
        value = read_report(args.runtime, expected_digest=args.runtime_digest)
    else:
        from autoengineering.agents.store import WorkerStore
        from .comparison_runtime import Runtime

        if args.preparation is None or args.preparation_digest is None:
            parser.error("execution requires --preparation and --preparation-digest")
        if args.action == "run":
            runtime = Runtime.create(args.preparation, expected_digest=args.preparation_digest)
        else:
            if args.runtime_digest is None:
                parser.error("resume requires --runtime-digest")
            runtime = Runtime.open(
                args.preparation,
                expected_digest=args.preparation_digest,
                runtime_digest=args.runtime_digest,
            )
        import sys

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
        old_calls = sum(
            len(WorkerStore(runtime.batch.root / "cases" / c.id / "worker").replay().invocations)
            for c in runtime.plan.cases
            if (runtime.batch.root / "cases" / c.id / "worker").exists()
        )
        value = runtime.advance(
            max_new_cases=args.max_new_cases, max_new_evaluations=args.max_new_evaluations
        )
        new_calls = sum(
            len(WorkerStore(runtime.batch.root / "cases" / c.id / "worker").replay().invocations)
            for c in runtime.plan.cases
            if (runtime.batch.root / "cases" / c.id / "worker").exists()
        )
        print(
            canonical_json(
                {
                    "execution_delta": {
                        "scientific_reservations_added": value["scientific_reservations_charged"]
                        - before["scientific_reservations_charged"],
                        "logical_invocations_added": new_calls - old_calls,
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
