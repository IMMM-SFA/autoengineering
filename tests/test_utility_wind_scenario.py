"""Registered wind scenario rejects unsupported inputs before model execution."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import importlib.util

import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.utility.engineering_process import EngineeringScenario
from examples.utility.wind_parameters import WindGeometry
from examples.utility.wind_scenario import execute, rules, GEOMETRY_PATH


def job(tmp_path):
    geometry = WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0))
    path = tmp_path / GEOMETRY_PATH
    path.parent.mkdir(mode=0o700)
    path.write_text(geometry.to_json())
    ref = reference(
        tmp_path, GEOMETRY_PATH, media_type="application/json", producer="authored-fixture"
    )
    scenario = EngineeringScenario("bundled-distribution", {"direction_step": 30.0})
    return SimpleNamespace(
        execution=SimpleNamespace(
            sources=(ref,), scenarios=(scenario,), study=SimpleNamespace(rules=rules())
        ),
        source_root=str(tmp_path),
        scratch_path=str(tmp_path / "scratch"),
        configuration=geometry.baseline,
        seed=17,
        scenario_id=scenario.scenario_id,
        action_id="wind-action",
        digest="1" * 64,
    )


@pytest.mark.parametrize(
    "change", ["geometry", "weather", "duplicate_scenario", "rules", "corrupt"]
)
def test_invalid_wind_scenario_does_not_reach_model(tmp_path, monkeypatch, change):
    task = job(tmp_path)

    def denied(*args, **kwargs):
        raise AssertionError("Unsupported wind scenario reached model execution")

    monkeypatch.setattr("examples.utility.wind_scenario.run_lifecycle", denied)
    if change == "geometry":
        task.configuration["x_1"] = task.configuration["x_0"]
    elif change == "weather":
        task.execution.scenarios = (EngineeringScenario(task.scenario_id, {"wind_speed": 9.0}),)
    elif change == "duplicate_scenario":
        task.execution.scenarios += (EngineeringScenario("another-grid", {"direction_step": 15.0}),)
    elif change == "rules":
        task.execution.study.rules = replace(rules(), minimum_gain=1.0)
    else:
        (Path(task.source_root) / GEOMETRY_PATH).write_text("changed")
    with pytest.raises(ValueError):
        execute(task)


@pytest.mark.skipif(importlib.util.find_spec("py_wake") is None, reason="optional wind runtime")
def test_registered_wind_result_has_all_required_checks(tmp_path):
    from examples.utility.wind import ROOT

    task = job(tmp_path)
    for name in (
        "examples/utility/wind.py",
        "examples/open_chains/wind/models.py",
        "pixi.lock",
        "examples/utility/wind_parameters.py",
    ):
        target = tmp_path / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    result = execute(task)
    assert result.score.values["annual_energy"] > 0
    assert {c.name for c in result.score.checks} == {c.name for c in rules().checks}
    assert all(c.status == "pass" and c.required for c in result.score.checks)
    assert result.solver_work == {"wind_evaluations": 1.0}
    assert result.solver_units == {"wind_evaluations": "count"}
