"""Concrete development preparation is finite and never starts model processes."""

import pytest

from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.engineering_process import EngineeringExecutionSpec
from examples.utility import wind_hourly_study as study


def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(study, "pins", lambda: {"authored": True})
    monkeypatch.setattr(
        study,
        "SupervisedEngineeringExecutor",
        lambda *a, **kw: pytest.fail("preparation or invalid input started executor"),
    )
    root = tmp_path / "prepared"
    request = study.prepare(root)
    return root, request


def test_prepare_freezes_entire_local_matrix_and_physics_before_dispatch(tmp_path, monkeypatch):
    root, request = prepared(tmp_path, monkeypatch)
    execution = EngineeringExecutionSpec.from_dict(request["execution"])
    assert request["scientific_starts_cap"] == 5
    assert request["baseline_calls"] == 1 and request["sobol_calls"] == 4
    assert request["provider_calls"] == request["automatic_retries"] == 0
    assert execution.study.run.study.budget.max_evaluations == 4
    assert execution.study.run.policy == "sobol"
    assert execution.timeout_seconds == 60.0
    assert len(execution.preflight) == 6
    for parameter in execution.study.run.search_space.parameters:
        assert parameter.upper - parameter.lower == 40.0
    assert not (root / "batch").exists() and not (root / "consumed.json").exists()
    with pytest.raises(ValueError, match="absent"):
        study.prepare(root)


@pytest.mark.parametrize("change", ["digest", "source", "caps", "consumed"])
def test_changed_or_consumed_scope_starts_no_executor(tmp_path, monkeypatch, change):
    root, request = prepared(tmp_path, monkeypatch)
    expected = digest(request)
    if change == "source":
        (root / "source/examples/utility/wind_hourly_scenario.py").write_text("changed")
    elif change == "caps":
        request["scientific_starts_cap"] = 6
        (root / "request.json").unlink()
        study.save(root, "request.json", request)
        expected = digest(request)
    elif change == "consumed":
        study.save(root, "consumed.json", {"existing": True})
    else:
        expected = "0" * 64
    with pytest.raises((ValueError, StoreError)):
        study.execute(root, expected)
    assert not (root / "batch").exists()
    if change != "consumed":
        assert not (root / "consumed.json").exists()
