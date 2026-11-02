"""Wind geometry admission and scalar lifecycle parity."""
import importlib.util

import numpy as np
import pytest

from examples.utility.wind import WindTask


def test_geometry_rejects_before_wake_import_or_call(monkeypatch):
    positions = ([0., 500.], [0., 500.])
    task = WindTask({"invalid": ([0., 0.], [0., 0.])}, positions)
    with pytest.raises(ValueError, match="spacing"):
        task.physical({}, {"layout_id": "invalid"})
    with pytest.raises(ValueError, match="frozen catalogue"):
        task.validate({"layout_id": "unknown"})


def test_catalogue_copies_inputs_and_binds_numerical_profile():
    x, y = np.array([0., 500.]), np.array([0., 500.])
    task = WindTask({"baseline": (x, y)}, (x, y))
    x[:] = 0
    assert task.layouts["baseline"][0][1] == 500
    with pytest.raises(ValueError):
        task.layouts["baseline"][0][0] = 1
    with pytest.raises(ValueError):
        task.layouts["baseline"][0].setflags(write=True)
    with pytest.raises(ValueError, match="divide"):
        WindTask({"baseline": (x, y)}, (x, y), direction_step=7)


@pytest.mark.skipif(importlib.util.find_spec("py_wake") is None,
                    reason="optional wind environment required")
def test_direct_wrapped_wind_parity(tmp_path):
    from py_wake.examples.data.hornsrev1 import wt16_x, wt16_y
    from examples.open_chains.wind.models import wakes
    from autoengineering.adapters.python import run_lifecycle
    corners = [0, 3, 12, 15]
    x, y = np.asarray(wt16_x)[corners], np.asarray(wt16_y)[corners]
    task = WindTask({"baseline": (x, y)}, (x, y))
    reference, power = wakes(x, y, 30)
    ctx = task.context("baseline", tmp_path)
    result = run_lifecycle(task.adapter(), ctx, {}, (), ctx.model.outputs)
    np.testing.assert_allclose(result.outputs["annual_energy"], np.sum(reference), rtol=1e-12)
    assert result.outputs["maximum_power"] <= 2e6
    assert result.outputs["minimum_power"] >= 0
    assert result.outputs["minimum_spacing"] >= 320
    assert result.training.status == "not_applicable"
    assert power.shape[0] == 4


@pytest.mark.skipif(importlib.util.find_spec("topfarm") is None,
                    reason="optional TOPFARM environment required")
def test_native_wind_driver_records_and_enforces_inner_limits():
    from py_wake.examples.data.hornsrev1 import wt16_x, wt16_y
    from examples.utility.wind_native import native_layout, NativeWindResult
    corners = [0, 3, 12, 15]
    positions = (np.asarray(wt16_x)[corners], np.asarray(wt16_y)[corners])
    result = native_layout(positions, max_iterations=2, max_wake_calls=12, max_gradient_calls=4)
    assert result.status in ("converged", "not_converged")
    assert result.feasible
    assert 0 < sum(c.kind == "wake" for c in result.calls) <= 12
    assert 0 < sum(c.kind == "gradient" for c in result.calls) <= 4
    assert NativeWindResult.from_json(result.to_json()) == result
    stopped = native_layout(positions, max_iterations=20, max_wake_calls=1, max_gradient_calls=1)
    assert stopped.status == "budget_exhausted"
    assert sum(c.kind == "wake" for c in stopped.calls) == 1
    assert sum(c.kind == "gradient" for c in stopped.calls) <= 1
