"""Scalar wind parameters retain geometry, hardware and immutable model identity."""

import importlib.util

import numpy as np
import pytest

from examples.utility.wind_parameters import WindGeometry


def geometry():
    return WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0))


def test_geometry_copies_inputs_and_roundtrips_scalar_parameters():
    x, y = [0.0, 600.0], [0.0, 600.0]
    profile = WindGeometry(x, y)
    x[1] = 0.0
    assert profile.x == (0.0, 600.0)
    assert WindGeometry.from_json(profile.to_json()) == profile
    assert profile.configuration(*profile.positions(profile.baseline)) == profile.baseline
    assert set(profile.bounds) == set(profile.baseline)
    changed = profile.baseline
    changed["x_1"] = 0.0
    assert profile.baseline["x_1"] == 600.0


@pytest.mark.parametrize("change", ["missing", "extra", "bool", "nan", "spacing", "boundary"])
def test_bad_geometry_stops_before_wake_execution(monkeypatch, change):
    def denied(*args, **kwargs):
        raise AssertionError("Invalid geometry reached the wake model")

    monkeypatch.setattr("examples.utility.wind.WindTask.physical", denied)
    profile = geometry()
    configuration = profile.baseline
    if change == "missing":
        del configuration["x_0"]
    elif change == "extra":
        configuration["unknown"] = 0.0
    elif change == "bool":
        configuration["x_0"] = True
    elif change == "nan":
        configuration["x_0"] = float("nan")
    elif change == "spacing":
        configuration["x_1"] = configuration["x_0"]
    else:
        configuration["x_0"] = -1.0
    with pytest.raises(ValueError):
        profile.physical({}, configuration)


def test_profile_rejects_degenerate_hardware_and_changed_turbine_count():
    with pytest.raises(ValueError, match="positive area"):
        WindGeometry((0.0, 0.0), (0.0, 600.0))
    with pytest.raises(ValueError, match="turbine count"):
        geometry().configuration((0.0, 600.0), (0.0, 600.0))


@pytest.mark.skipif(importlib.util.find_spec("py_wake") is None, reason="optional wind runtime")
def test_parameterized_wind_keeps_one_model_and_matches_direct_execution(tmp_path):
    from autoengineering.adapters.python import run_lifecycle

    profile = geometry()
    first = profile.context(profile.baseline, tmp_path)
    changed = profile.baseline | {"x_0": 10.0}
    second = profile.context(changed, tmp_path)
    assert first.model == second.model
    assert first.parameters != second.parameters
    direct = profile.physical({}, changed)
    wrapped = run_lifecycle(profile.adapter(), second, {}, (), second.model.outputs)
    for name in direct:
        np.testing.assert_allclose(direct[name], wrapped.outputs[name], rtol=1e-12)
    assert wrapped.training.status == "not_applicable"
    assert all(not p.dimensions for p in second.model.outputs)


def test_parameter_domain_does_not_silently_absorb_physical_tolerance():
    from examples.utility.wind import WindTask

    profile = geometry()
    outside = profile.baseline | {"x_0": -0.0005}
    positions = profile.positions(outside)
    WindTask({"native": positions}, (profile.x, profile.y)).validate({"layout_id": "native"})
    with pytest.raises(ValueError, match="parameter domain"):
        profile.validate(outside)


@pytest.mark.skipif(importlib.util.find_spec("py_wake") is None, reason="optional wind runtime")
def test_parameter_context_binds_caller_captured_sources(tmp_path):
    from examples.utility.wind import ROOT
    from autoengineering.campaign.artifacts import read_bytes

    source = tmp_path / "captured"
    names = (
        "examples/utility/wind.py",
        "examples/open_chains/wind/models.py",
        "pixi.lock",
        "examples/utility/wind_parameters.py",
    )
    for name in names:
        target = source / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    profile = geometry()
    ctx = profile.context(profile.baseline, tmp_path / "scratch", source_root=source)
    assert {r.path for r in ctx.model.source_bundle} == set(names)
    for ref in ctx.model.source_bundle:
        read_bytes(source, ref)
    (source / "examples/utility/wind_parameters.py").write_text("changed")
    with pytest.raises(ValueError, match="mismatch"):
        read_bytes(source, ctx.model.source_bundle[-1])
