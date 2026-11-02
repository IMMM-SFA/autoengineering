"""Strict resource inputs and analytic weighting; no independent observations."""

from dataclasses import replace
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.utility.engineering_process import EngineeringScenario
from examples.utility.wind_parameters import WindGeometry
from examples.utility.wind_resource import RESOURCE_PATH, WindResource, read_resource
from examples.utility.wind_resource_scenario import execute, direct
from examples.utility.wind_scenario import GEOMETRY_PATH, rules


def resource():
    return WindResource(
        "utility-wind-resource-v1", (0.0, 90.0, 180.0, 270.0), (4.0, 12.0), ((0.1, 0.15),) * 4
    )


def geometry():
    return WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0), 90)


def test_joint_probability_contract_is_immutable_and_roundtrips():
    value = resource()
    assert value.direction_step == 90 and value.annualization_hours == 8760
    assert WindResource.from_json(value.to_json()) == value
    raw = value.to_dict()
    raw["probability"][0][0] = 1.0
    assert value.probability[0][0] == 0.1
    with pytest.raises(TypeError):
        value.probability[0][0] = 1.0
    with pytest.raises(ValueError, match="grid"):
        value.validate_geometry(replace(geometry(), direction_step=30))


@pytest.mark.parametrize(
    "field,value",
    [
        ("directions_deg", (0.0, 90.0)),
        ("directions_deg", (0.0, 180.0, 90.0, 270.0)),
        ("directions_deg", (0.0, 90.0, 180.0, 360.0)),
        ("speeds_m_s", (12.0, 4.0)),
        ("speeds_m_s", (4.0, 4.0)),
        ("speeds_m_s", (-1.0, 12.0)),
        ("speeds_m_s", (4.0, 101.0)),
        ("probability", ((0.1, 0.15),)),
        ("probability", ((0.1, 0.15, 0.0),) * 4),
        ("probability", ((-0.1, 0.35),) * 4),
        ("probability", ((0.1, 0.1),) * 4),
        ("probability", ((False, 0.25),) * 4),
        ("probability", ((float("nan"), 0.25),) * 4),
        ("turbulence_intensity", 0.0),
        ("turbulence_intensity", 2.0),
        ("annualization_hours", 8784),
    ],
)
def test_invalid_resource_is_rejected_before_any_model_import(field, value):
    with pytest.raises(ValueError):
        replace(resource(), **{field: value})


def test_artifact_size_path_digest_and_symlink_checks(tmp_path):
    path = tmp_path / RESOURCE_PATH
    path.parent.mkdir()
    path.write_text(resource().to_json())
    ref = reference(tmp_path, RESOURCE_PATH, media_type="application/json", producer="test")
    assert read_resource(tmp_path, ref) == resource()
    with pytest.raises(ValueError, match="path"):
        read_resource(tmp_path, replace(ref, path="other.json"))
    path.write_text("{}")
    with pytest.raises(ValueError):
        read_resource(tmp_path, ref)
    path.unlink()
    path.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(ValueError):
        read_resource(tmp_path, ref)


def job(tmp_path):
    root = Path(tmp_path)
    refs = []
    for name, value in ((GEOMETRY_PATH, geometry()), (RESOURCE_PATH, resource())):
        path = root / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_text(value.to_json())
        refs.append(reference(root, name, media_type="application/json", producer="authored"))
    scenario = EngineeringScenario("supplied-resource", {"direction_step": 90.0})
    return SimpleNamespace(
        execution=SimpleNamespace(
            sources=tuple(refs), scenarios=(scenario,), study=SimpleNamespace(rules=rules())
        ),
        source_root=str(root),
        scratch_path=str(root / "scratch"),
        configuration=geometry().baseline,
        seed=17,
        scenario_id=scenario.scenario_id,
        action_id="wind-resource-action",
        digest="1" * 64,
    )


@pytest.mark.parametrize(
    "change", ["missing", "mass", "geometry", "forcing", "scenario", "rules", "coordinates"]
)
def test_bad_scenario_cannot_reach_physical_execution(tmp_path, monkeypatch, change):
    task = job(tmp_path)
    monkeypatch.setattr(
        "examples.utility.wind_resource_scenario.run_lifecycle",
        lambda *_a, **_k: pytest.fail("physical start"),
    )
    if change == "missing":
        task.execution.sources = task.execution.sources[:1]
    elif change == "mass":
        (tmp_path / RESOURCE_PATH).write_text("{}")
    elif change == "geometry":
        path = tmp_path / GEOMETRY_PATH
        path.write_text(replace(geometry(), direction_step=30).to_json())
        task.execution.sources = (
            reference(tmp_path, GEOMETRY_PATH, media_type="application/json", producer="test"),
            *task.execution.sources[1:],
        )
    elif change == "forcing":
        task.execution.scenarios = (EngineeringScenario(task.scenario_id, {"wind_speed": 12.0}),)
    elif change == "scenario":
        task.scenario_id = "unregistered"
    elif change == "rules":
        task.execution.study.rules = replace(rules(), minimum_gain=1.0)
    else:
        task.configuration["x_1"] = 0.0
    with pytest.raises(ValueError):
        execute(task)


def test_native_v2_binds_resource_and_keeps_legacy_serialization(monkeypatch):
    from examples.utility.wind_proposal import WindNativeSpec, propose
    from test_utility_wind_proposal import result, specification

    old = specification()
    assert "resource_digest" not in old.to_dict()
    assert WindNativeSpec.from_json(old.to_json()) == old
    with pytest.raises(ValueError):
        WindNativeSpec.from_dict({**old.to_dict(), "resource_digest": None})
    new = replace(
        old,
        schema="utility-wind-native-spec-v2",
        geometry=geometry(),
        resource_digest=resource().digest,
    )
    seen = []

    def native(*args, **kwargs):
        seen.append(kwargs["resource"])
        return result()

    monkeypatch.setattr("examples.utility.wind_proposal.native_layout", native)
    with pytest.raises(ValueError):
        propose(new)
    with pytest.raises(ValueError):
        propose(old, resource=resource())
    changed = replace(resource(), probability=((0.25, 0.0),) * 4)
    with pytest.raises(ValueError):
        propose(new, resource=changed)
    value = propose(new, resource=resource())
    assert (
        value.schema == "utility-wind-native-proposal-v2"
        and value.configuration == geometry().baseline
    )
    assert seen == [resource()]


@pytest.mark.skipif(importlib.util.find_spec("py_wake") is None, reason="optional wind runtime")
def test_pinned_pywake_weights_match_analytic_power_and_change_with_resource():
    value = resource()
    aep, power = value.evaluate(*geometry().positions(geometry().baseline))
    np.testing.assert_allclose(aep, power * np.array(value.probability)[None, :, :] * 8760 / 1e9)
    slow = replace(value, probability=((0.25, 0.0),) * 4)
    fast = replace(value, probability=((0.0, 0.25),) * 4)
    assert np.sum(fast.evaluate(geometry().x, geometry().y)[0]) > np.sum(
        slow.evaluate(geometry().x, geometry().y)[0]
    )
    calm = replace(value, speeds_m_s=(0.0, 12.0), probability=((0.25, 0.0),) * 4)
    np.testing.assert_allclose(calm.evaluate(geometry().x, geometry().y)[0], 0.0)
    asymmetric = replace(value, directions_deg=(0.0, 180.0), probability=((0.1, 0.2), (0.3, 0.4)))
    aep, power = asymmetric.evaluate(geometry().x, geometry().y)
    np.testing.assert_allclose(
        aep, power * np.array(asymmetric.probability)[None, :, :] * 8760 / 1e9
    )


@pytest.mark.skipif(importlib.util.find_spec("py_wake") is None, reason="optional wind runtime")
def test_direct_and_wrapped_resource_scenario_agree_and_keep_checks(tmp_path):
    task = job(tmp_path)
    from examples.utility.wind import ROOT

    for name in (
        "examples/utility/wind.py",
        "examples/open_chains/wind/models.py",
        "pixi.lock",
        "examples/utility/wind_parameters.py",
        "examples/utility/wind_resource.py",
        "examples/utility/wind_resource_scenario.py",
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    wrapped = execute(task)
    original = direct(task)
    assert wrapped.score == original.score
    assert all(c.status == "pass" for c in wrapped.score.checks)
    assert wrapped.solver_work == {"wind_evaluations": 1.0}
