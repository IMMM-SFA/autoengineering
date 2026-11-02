"""Suite identities reject ambiguous matrices before execution."""
from dataclasses import FrozenInstanceError

import pytest

from autoengineering.utility.contracts import (
    BudgetSpec, ComparisonCell, ResourceCap, RouteSpec, TaskSpec, UtilitySuiteSpec,
)

H = "1" * 64


def suite(repetitions=1):
    caps = tuple(ResourceCap(n, u, v, "reservation") for n, u, v in (
        ("scientific_starts", "count", 100), ("host_invocations", "count", 50),
        ("training_starts", "count", 0), ("active_time", "s", 600),
    ))
    return UtilitySuiteSpec(
        "utility-suite-v1", "fixture", [TaskSpec("task", "engineering", H, H, H, [H], [])],
        [RouteSpec("conventional", "conventional", H, H),
         RouteSpec("multi", "multi_agent", H, H)],
        [BudgetSpec("fixed_evaluations", caps,
                    [ResourceCap("scientific_starts", "count", 2, "reservation")])],
        [ComparisonCell("task", route, "fixed_evaluations", rep, rep, H)
         for rep in range(repetitions) for route in ("conventional", "multi")],
        H, H, H, H, H,
    )


def test_roundtrip_identity_and_freezing():
    spec = suite()
    assert UtilitySuiteSpec.from_json(spec.to_json()) == spec
    assert isinstance(spec.tasks, tuple)
    with pytest.raises(FrozenInstanceError):
        spec.suite_id = "changed"
    data = spec.to_dict()
    data["analysis_digest"] = "2" * 64
    assert UtilitySuiteSpec.from_dict(data).digest != spec.digest
    data["cells"][0]["seed"] = 100
    assert spec.cells[0].seed == 0


def test_strict_json():
    spec = suite()
    with pytest.raises(ValueError, match="duplicate"):
        UtilitySuiteSpec.from_json('{"suite_id":"a","suite_id":"b"}')
    data = spec.to_dict()
    data["extra"] = 1
    with pytest.raises(ValueError, match="unknown"):
        UtilitySuiteSpec.from_dict(data)


@pytest.mark.parametrize("mutation", ["missing", "seed", "scenario", "duplicate", "unknown"])
def test_matrix_rejects_unpaired_or_conflicting_cells(mutation):
    data = suite().to_dict()
    if mutation == "missing":
        data["cells"].pop()
    elif mutation == "seed":
        data["cells"][0]["seed"] += 1
    elif mutation == "scenario":
        data["cells"][0]["scenario_digest"] = "2" * 64
    elif mutation == "duplicate":
        data["cells"].append(data["cells"][0])
    else:
        data["cells"][0]["task_id"] = "unknown"
    with pytest.raises(ValueError):
        UtilitySuiteSpec.from_dict(data)


@pytest.mark.parametrize("limit", [None, True, float("nan"), float("inf"), -1, 0.5])
def test_invalid_count_caps(limit):
    with pytest.raises(ValueError):
        ResourceCap("starts", "count", limit, "reservation")


def test_child_batch_partition_preserves_parent_identity():
    spec = suite(35)
    batches = spec.child_batches()
    assert [len(b) for b in batches] == [32, 32, 6]
    assert tuple(c for batch in batches for c in batch) == spec.cells
    assert len({c.digest for b in batches for c in b}) == 70
    assert len(spec.budgets) == 1


def test_reserve_and_grants():
    data = suite().to_dict()
    data["budgets"][0]["confirmation_reserve"][0]["limit"] = 101
    with pytest.raises(ValueError, match="reserve"):
        UtilitySuiteSpec.from_dict(data)
    data = suite().to_dict()
    data["routes"][1]["grants_digest"] = "2" * 64
    with pytest.raises(ValueError, match="grants"):
        UtilitySuiteSpec.from_dict(data)
