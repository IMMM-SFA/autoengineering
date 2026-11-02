"""Source-bound hourly scenarios refuse changes before any optional model call."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.utility.engineering_process import (
    EngineeringScenario,
    SupervisedEngineeringExecutor,
)
from examples.utility import wind_hourly_scenario as scenario
from examples.utility.wind_hourly import WindHourly


def job(tmp_path):
    tmp_path.chmod(0o700)
    binding = scenario.materialize_inputs(tmp_path)
    names = (
        *scenario.MODEL_SOURCES,
        scenario.BINDING_PATH,
        scenario.POINT_PATH,
        scenario.REVIEW_PATH,
    )
    for name in scenario.MODEL_SOURCES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((scenario.ROOT / name).read_bytes())
    refs = tuple(
        reference(tmp_path, n, media_type="text/plain", producer="authored-test")
        for n in names
        if n not in (scenario.POINT_PATH, scenario.REVIEW_PATH)
    ) + (binding.point, binding.assumptions)
    return SimpleNamespace(
        execution=SimpleNamespace(
            sources=refs,
            scenarios=(EngineeringScenario(scenario.SCENARIO_ID, scenario.SCENARIO_FORCING),),
            study=SimpleNamespace(rules=scenario.rules()),
        ),
        source_root=str(tmp_path),
        scratch_path=str(tmp_path / "scratch"),
        configuration=binding.geometry.baseline,
        seed=17,
        scenario_id=scenario.SCENARIO_ID,
        action_id="hourly-action",
        digest="1" * 64,
    ), binding


def test_binding_roundtrip_and_materialization_does_not_start_models(tmp_path, monkeypatch):
    monkeypatch.setattr("examples.utility.wind_hourly._backend", lambda: pytest.fail("model start"))
    task, binding = job(tmp_path)
    assert scenario.HourlyBinding.from_json(binding.to_json()) == binding
    loaded, profile, _ = scenario.load_inputs(task)
    assert loaded == binding and len(profile.speed) == 8760
    assert not loaded.task_admitted
    assert profile.point_sha256 == scenario.POINT_SHA
    with pytest.raises(FileExistsError):
        scenario.materialize_inputs(tmp_path)


@pytest.mark.parametrize(
    "change", ["point", "review", "geometry", "policy", "completion", "admission"]
)
def test_binding_rejects_unsupported_profile(tmp_path, change):
    _, binding = job(tmp_path)
    edits = {
        "point": {"point": replace(binding.point, sha256="0" * 64)},
        "review": {"assumptions": replace(binding.assumptions, sha256="0" * 64)},
        "geometry": {"geometry": replace(binding.geometry, x=(0.0, 600.0), y=(0.0, 600.0))},
        "policy": {"policy_digest": "0" * 64},
        "completion": {"acquisition_completion_digest": "0" * 64},
        "admission": {"task_admitted": True},
    }
    with pytest.raises(ValueError):
        replace(binding, **edits[change])


@pytest.mark.parametrize(
    "change",
    [
        "point",
        "review",
        "binding",
        "undeclared",
        "duplicate",
        "scenario",
        "forcing",
        "rules",
        "spacing",
        "source",
    ],
)
def test_invalid_job_stops_before_optional_runtime(tmp_path, monkeypatch, change):
    task, _ = job(tmp_path)
    monkeypatch.setattr(WindHourly, "physical", lambda *a: pytest.fail("physical execution"))
    monkeypatch.setattr(scenario, "version", lambda *a: pytest.fail("optional version access"))
    if change in ("point", "review", "binding"):
        name = {
            "point": scenario.POINT_PATH,
            "review": scenario.REVIEW_PATH,
            "binding": scenario.BINDING_PATH,
        }[change]
        (tmp_path / name).write_bytes(b"changed")
    elif change == "undeclared":
        task.execution.sources = tuple(
            r for r in task.execution.sources if r.path != scenario.POINT_PATH
        )
    elif change == "duplicate":
        task.execution.sources += task.execution.sources[:1]
    elif change == "scenario":
        task.scenario_id = "different"
    elif change == "forcing":
        task.execution.scenarios = (EngineeringScenario(scenario.SCENARIO_ID, {"height_m": 70.0}),)
    elif change == "rules":
        task.execution.study.rules = replace(scenario.rules(), minimum_gain=1.0)
    elif change == "spacing":
        task.configuration["x_1"] = 0.0
    else:
        (tmp_path / "examples/utility/wind_hourly.py").write_bytes(b"changed")
    with pytest.raises(ValueError):
        scenario.execute(task)


@pytest.mark.parametrize("bad_power", [False, True])
def test_adapter_routes_scalars_and_veto_through_authoritative_checks(
    tmp_path, monkeypatch, bad_power
):
    task, _ = job(tmp_path)
    monkeypatch.setattr(scenario, "version", lambda n: "2.6.20")
    calls = []

    def physical(self, forcing, configuration):
        calls.append(1)
        self.geometry.validate(configuration)
        assert not forcing
        return {
            k: np.asarray(v, dtype=float)
            for k, v in dict(
                annual_energy=30.0,
                minimum_spacing=600.0,
                boundary_violation=0.0,
                maximum_power=3e6 if bad_power else 2e6,
                minimum_power=0.0,
            ).items()
        }

    monkeypatch.setattr(WindHourly, "physical", physical)
    result = scenario.execute(task)
    assert calls == [1]
    assert result.solver_work == {"wind_evaluations": 1.0}
    assert result.score.values["annual_energy"] == 30.0
    assert result.score.forcing_digest == SupervisedEngineeringExecutor._forcing_digest(
        task.execution.scenarios[0]
    )
    assert len(result.score.checks) == 5
    failed = [c.name for c in result.score.checks if c.status != "pass"]
    assert failed == (["wind_rated_power"] if bad_power else [])
