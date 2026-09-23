"""Physical and integration checks for the optional real model examples."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from autoengineering.execute.swap import swap_component
from autoengineering.research.runner import run_component
from autoengineering.system.graph import System
from examples.open_chains.common import digest, verify_file

ROOT = Path(__file__).resolve().parents[1] / "examples/open_chains"
SOLAR = importlib.util.find_spec("pvlib") is not None
WIND = (
    importlib.util.find_spec("py_wake") is not None
    and importlib.util.find_spec("topfarm") is not None
)
HYBRID = importlib.util.find_spec("hopp") is not None


def test_input_integrity_rejects_changed_bytes(tmp_path):
    path = tmp_path / "data.csv"
    path.write_bytes(b"original")
    expected = {"bytes": path.stat().st_size, "sha256": digest(path)}
    verify_file(path, expected)
    path.write_bytes(b"modified")
    with pytest.raises(ValueError, match="integrity mismatch"):
        verify_file(path, expected)


@pytest.mark.skipif(not SOLAR, reason="requires solar environment")
def test_solar_dc_agrees_with_independent_brent_solver():
    import pvlib
    from examples.open_chains.solar.models import dc_power, inverter

    irradiance = np.array([0, 50, 300, 1000.0])
    temperature = np.array([0, -10, 25, 60.0])
    module = pvlib.pvsystem.retrieve_sam("cecmod")["First_Solar__Inc__FS_4117_3"]
    parameters = pvlib.pvsystem.calcparams_cec(
        irradiance,
        temperature,
        module.alpha_sc,
        module.a_ref,
        module.I_L_ref,
        module.I_o_ref,
        module.R_sh_ref,
        module.R_s,
        module.Adjust,
    )
    reference = pvlib.pvsystem.max_power_point(*parameters, method="brentq")
    p, v = dc_power(irradiance, temperature)
    factor = 1 - pvlib.pvsystem.pvwatts_losses(shading=0, availability=0) / 100
    np.testing.assert_allclose(p, reference["p_mp"] * 15 * 1344 * factor, atol=1e-4)
    assert p[0] == pytest.approx(0, abs=1e-8)
    assert np.all(inverter(p, v) <= 1833 + 1)


@pytest.mark.skipif(not SOLAR, reason="requires solar environment")
def test_transient_temperature_is_causal_and_resets_at_gap():
    import pandas as pd
    from examples.open_chains.solar.models import temperature

    times = pd.date_range("2018-01-01", periods=30, freq="5min", tz="UTC").as_unit("ns").asi8
    poa = np.linspace(100, 800, 30)
    air, wind = np.full(30, 20.0), np.full(30, 2.0)
    full = temperature(poa, air, wind, times)
    prefix = temperature(poa[:15], air[:15], wind[:15], times[:15])
    np.testing.assert_allclose(full[:15], prefix)
    with_gap = times.copy()
    with_gap[15:] += 3600_000_000_000
    reset = temperature(poa, air, wind, with_gap)
    standalone = temperature(poa[15:], air[15:], wind[15:], with_gap[15:])
    np.testing.assert_allclose(reset[15:], standalone)


@pytest.mark.skipif(not SOLAR, reason="requires solar environment")
def test_solar_component_swap_changes_output_without_mutating_baseline():
    from copy import deepcopy
    import pandas as pd

    system = System.from_yaml(ROOT / "solar/system.yaml")
    component = deepcopy(system.get_component("temperature"))
    component.metadata["runnable"]["params"]["method"] = "sapm_module"
    swapped = swap_component(system, "temperature", component)
    inputs = {
        "poa": np.linspace(100, 800, 20),
        "ambient": np.full(20, 20.0),
        "wind": np.full(20, 2.0),
        "timestamp": pd.date_range("2018", periods=20, freq="5min", tz="UTC").as_unit("ns").asi8,
    }
    original = run_component(system.get_component("temperature"), inputs)["module_temperature"]
    changed = run_component(swapped.get_component("temperature"), inputs)["module_temperature"]
    assert not np.allclose(original, changed)
    assert (
        system.get_component("temperature").metadata["runnable"]["params"]["method"]
        == "faiman_prilliman"
    )


@pytest.mark.skipif(not WIND, reason="requires wind environment")
def test_wind_adapter_matches_upstream_and_rejects_invalid_layout():
    from py_wake import NOJ
    from py_wake.examples.data.hornsrev1 import Hornsrev1Site, V80, wt16_x, wt16_y
    from examples.open_chains.wind.models import feasible, wakes

    x, y = np.asarray(wt16_x), np.asarray(wt16_y)
    feasible(x, y, x, y)
    reference = NOJ(Hornsrev1Site(), V80())(x, y, wd=np.arange(0, 360, 30), ws=np.arange(4, 26, 2))
    actual, _ = wakes(x, y)
    np.testing.assert_allclose(actual, reference.aep().values)
    with pytest.raises(ValueError, match="separation"):
        feasible(np.full_like(x, x[0]), np.full_like(y, y[0]), x, y)


@pytest.mark.skipif(not WIND, reason="requires wind environment")
def test_topfarm_returns_feasible_layout_and_nonnegative_power():
    from py_wake.examples.data.hornsrev1 import wt16_x, wt16_y
    from examples.open_chains.wind.models import feasible, layout, wakes

    x, y = np.asarray(wt16_x), np.asarray(wt16_y)
    updated_x, updated_y, diagnostics = layout(x, y, method="topfarm", maxiter=2)
    feasible(updated_x, updated_y, x, y)
    assert diagnostics[0] in [1, 2] and diagnostics[1] > 0
    aep, power = wakes(updated_x, updated_y)
    assert np.all(power >= 0) and aep.sum() > 0


@pytest.mark.skipif(not HYBRID, reason="requires hybrid environment")
def test_hopp_dispatch_runs_actual_solver_and_obeys_limits():
    from examples.open_chains.common import verify_sources
    from examples.open_chains.hybrid.models import check_physics
    from examples.open_chains.hybrid.run_workflow import run_chain

    verify_sources(ROOT / "hybrid")
    system = System.from_yaml(ROOT / "hybrid/system.yaml")
    system.get_component("dispatch").metadata["runnable"]["params"]["method"] = "simple"
    arrays = run_chain(system, smoke=True)
    check_physics(arrays)
    assert len(arrays["grid_kw"]) == 120
    assert arrays["grid_kw"].sum() > 0
    np.testing.assert_allclose(arrays["revenue_usd"], arrays["grid_kw"] * arrays["price"])
    assert np.ptp(arrays["soc"]) > 0


@pytest.mark.skipif(not SOLAR, reason="requires solar environment")
def test_invalid_temperature_sensor_is_flagged_not_repaired():
    from examples.open_chains.solar.run_workflow import temperature_quality

    values = np.array([20.0, 25.0, 2000.0])
    result = temperature_quality(values)
    assert result["status"] == "invalid_observation_range"
    assert result["invalid_count"] == 1
    np.testing.assert_array_equal(values, [20, 25, 2000])


@pytest.mark.parametrize(
    "domain,external",
    [
        ("solar", {"poa", "ambient", "wind", "timestamp"}),
        ("wind", {"x", "y"}),
        ("hybrid", {"smoke_flag"}),
    ],
)
def test_graph_declares_internal_inputs_and_units(domain, external):
    system = System.from_yaml(ROOT / domain / "system.yaml")
    for component in system.components:
        wired = {edge["port_to"] for edge in system.connections if edge["target"] == component.name}
        for port in component.inputs:
            assert port.units
            assert port.name in wired or port.name in external
        assert all(port.units for port in component.outputs)
    assert len(system.topological_order()) == len(system.components)


@pytest.mark.skipif(not SOLAR, reason="requires solar environment")
def test_solar_graph_runner_agrees_with_procedural_adapter():
    import pandas as pd
    from autoengineering.research.runner import build_feedforward_runner
    from examples.open_chains.solar.run_workflow import run_chain, POA, AIR, WIND

    index = pd.date_range("2018-01-01", periods=20, freq="5min", tz="UTC")
    frame = pd.DataFrame({POA: np.linspace(100, 800, 20), AIR: 20.0, WIND: 2.0}, index=index)
    drivers = {
        "poa": frame[POA].to_numpy(),
        "ambient": frame[AIR].to_numpy(),
        "wind": frame[WIND].to_numpy(),
        "timestamp": index.as_unit("ns").asi8,
    }
    system = System.from_yaml(ROOT / "solar/system.yaml")
    expected = run_chain(system, frame)
    actual = build_feedforward_runner(system, drivers)(system)
    np.testing.assert_allclose(actual["inverter.ac_kw"], expected["ac_kw"])
