"""Run the production ledger and recovery contract tests with the benchmark adapter."""

import autoengineering.optimization as api
from examples.complex_models.ledger import BenchmarkLedger

# This assignment also runs in spawned test processes. The production implementation
# on disk is unchanged, and each process exits after this check.
api.ObservationLedger = BenchmarkLedger

if __name__ == "__main__":
    import pytest

    raise SystemExit(
        pytest.main(
            ["tests/test_optimization_ledger.py", "tests/test_optimization_recovery.py", "-q"]
        )
    )
