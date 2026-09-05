"""Physical and numerical checks for the larger BMI chains."""

from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pytest

pytest.importorskip("bmipy")
pytest.importorskip("pvlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from examples.complex_models import models
from examples.local_models.bmi_chain import run_components


def test_hymod_conservation_and_causal_prefix():
    data = models.load_data("hymod")
    for config in [
        models.BASELINES["hymod"],
        dict(models.BASELINES["hymod"], cmax=50, beta=3, pet_scale=1.5),
    ]:
        out = models.evaluate("hymod", data, config)
        assert np.max(np.abs(out["balance_residual"])) < 1e-10
        assert np.min(out["storage"]) >= 0
        assert np.min(out["prediction"]) >= 0
        prefix = models.evaluate("hymod", data.iloc[:365], config)
        np.testing.assert_array_equal(out["prediction"][:365], prefix["prediction"])


def test_routing_impulse_and_mass():
    config = dict(alpha=0.6, kfast=0.5, kslow=0.1, end_time=1000)
    rain = np.r_[1.0, np.zeros(999)]
    out = run_components(
        {"r": models.ParallelRoutingBmi(config)}, [], {"r": {"excess_water": rain}}, 1000
    )["r"]
    assert out["flow"][0] == pytest.approx(0.4 * 0.1 + 0.6 * 0.5**3)
    assert out["flow"].sum() + out["routing_storage"][-1] == pytest.approx(1.0)


def test_single_diode_bmi_matches_vectorized_pvlib():
    p = models.BASELINES["solar_diode"]
    irradiance = np.array([50, 100, 300, 600, 1000.0])
    temperature = np.array([-5, 0, 25, 45, 60.0])
    out = run_components(
        {"d": models.SingleDiodeBmi(dict(p, end_time=5))},
        [],
        {"d": {"effective_irradiance": irradiance, "module_temperature": temperature}},
        5,
    )
    np.testing.assert_allclose(
        out["d"]["dc_power"], models.diode_power(irradiance, temperature, p), rtol=1e-10
    )


def test_zero_sun_and_inverter_limit():
    data = models.load_data("solar_diode").iloc[:5].copy()
    data["poa_w_m2"] = 0
    out = models.evaluate("solar_diode", data, models.BASELINES["solar_diode"])
    np.testing.assert_array_equal(out["prediction"], np.zeros(5))
    data["poa_w_m2"] = 2000
    out = models.evaluate("solar_diode", data, models.BASELINES["solar_diode"])
    assert np.all(out["prediction"] <= 1910)


@pytest.mark.parametrize("domain", ["hymod", "solar_diode"])
def test_held_out_labels_do_not_change_model(domain):
    data = models.load_data(domain)
    first = models.evaluate(domain, data, models.BASELINES[domain])["prediction"]
    data.loc[data.split == "test", models.original.TARGETS[models.BASE_DOMAIN[domain]]] += 1000
    second = models.evaluate(domain, data, models.BASELINES[domain])["prediction"]
    np.testing.assert_array_equal(first, second)


@pytest.mark.parametrize("domain", ["hymod", "solar_diode"])
def test_search_space_baseline_is_valid(domain):
    space = models.search_space(domain)
    np.testing.assert_allclose(
        space.encode(space.decode(space.encode(models.BASELINES[domain]))),
        space.encode(models.BASELINES[domain]),
    )


def test_brent_solver_matches_independent_lambert_solution():
    from pvlib.pvsystem import calcparams_desoto, singlediode

    p = models.BASELINES["solar_diode"]
    m = models.MODULE
    for rs, io, a in [(0.5, 0.3, 0.8), (1, 1, 1), (2, 3, 1.2)]:
        config = dict(p, rs_scale=rs, io_scale=io, a_scale=a)
        g = np.array([50, 300, 1000.0])
        t = np.array([-10, 25, 60.0])
        params = calcparams_desoto(
            g,
            t,
            alpha_sc=m["alpha_sc"],
            a_ref=m["a_ref"] * a,
            I_L_ref=m["I_L_ref"],
            I_o_ref=m["I_o_ref"] * io,
            R_s=m["R_s"] * rs,
            R_sh_ref=m["R_sh_ref"],
        )
        expected = singlediode(*params, method="lambertw")["p_mp"] * 2369 / m["STC"] * p["loss"]
        np.testing.assert_allclose(models.diode_power(g, t, config), expected, rtol=1e-8)


def test_checkpoint_driver_freezes_observed_recommendations(tmp_path):
    import json
    from examples.complex_models.run import study

    row = study("copper", "sobol", 0, 4, tmp_path / "run", {}, checkpoints=(2, 4))
    ledger = [json.loads(x) for x in (tmp_path / "run/observations.jsonl").read_text().splitlines()]
    assert row["evaluations"] == 4
    assert [c["evaluations"] for c in row["checkpoints"]] == [2, 4]
    for checkpoint in row["checkpoints"]:
        n = checkpoint["evaluations"]
        frozen = json.loads((tmp_path / f"run/frozen-{n}.json").read_text())
        assert "test" not in frozen
        assert frozen["recommendation"] == checkpoint["recommendation"]
        assert checkpoint["recommendation"]["outcomes"]["rmse"] == min(
            e["result"]["outcomes"]["rmse"] for e in ledger[:n]
        )


def test_target_mode_stops_without_running_later_checkpoints(tmp_path):
    from examples.complex_models.run import study

    row = study("copper", "sobol", 0, 200, tmp_path / "run", {}, target=1e6)
    assert row["evaluations"] == 1
    assert row["target_reached"]
    assert row["checkpoints"] == []


def test_freezing_rejects_incomplete_fixed_runs(tmp_path):
    from examples.complex_models.run import freeze_targets, DOMAINS, METHODS
    from examples.local_models.run import write_json

    rows = [
        {
            "domain": d,
            "method": m,
            "seed": s,
            "evaluations": 1,
            "stop_reason": "backend_stopped",
            "checkpoints": [],
        }
        for d in DOMAINS
        for m in METHODS
        for s in [0, 1, 2]
    ]
    write_json(tmp_path / "results.json", {"runs": rows})
    write_json(tmp_path / "manifest.json", {"inputs": {}})
    first = rows[0]
    directory = tmp_path / f"{first['domain']}-{first['method']}-{first['seed']}"
    directory.mkdir()
    (directory / "observations.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="Incomplete fixed study"):
        freeze_targets(tmp_path, tmp_path / "targets.json")
    assert not (tmp_path / "targets.json").exists()


def test_pdm_known_storage_integral_and_evaporation_limit():
    p = dict(models.BASELINES["hymod"], cmax=100, beta=1, end_time=2)
    soil = models.PdmSoilBmi(p)
    soil.initialize()
    soil.set_value("soil_storage", np.array([0.0]))
    soil.set_value("precipitation", np.array([50.0]))
    soil.set_value("potential_evaporation", np.array([0.0]))
    soil.update()
    assert soil.get_value_ptr("soil_storage")[0] == pytest.approx(37.5)
    assert soil.get_value_ptr("excess_water")[0] == pytest.approx(12.5)
    soil.set_value("precipitation", np.array([0.0]))
    soil.set_value("potential_evaporation", np.array([1000.0]))
    soil.update()
    assert soil.get_value_ptr("soil_storage")[0] == pytest.approx(0)
    assert soil.get_value_ptr("actual_evaporation")[0] == pytest.approx(37.5)
    soil.finalize()


def test_cec_snapshot_matches_pinned_package_source():
    import json
    import hashlib
    import pvlib
    from pvlib.pvsystem import retrieve_sam

    snapshot = json.loads((models.ROOT / "module.json").read_text())
    path = Path(pvlib.__file__).parent / "data/sam-library-cec-modules-2019-03-05.csv"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == snapshot["source_sha256"]
    module = retrieve_sam("CECMod")[snapshot["name"]]
    assert {k: float(module[k]) for k in snapshot["parameters"]} == snapshot["parameters"]


def test_workflow_swaps_execute_distinct_models():
    from autoengineering.system.graph import System
    import copy
    from autoengineering.execute.swap import swap_component

    for domain, owner, cls in [
        ("hymod", "routing", "SingleFastRoutingBmi"),
        ("solar_diode", "diode", "EmpiricalDcBmi"),
    ]:
        data = models.load_data(domain).iloc[:50]
        system = System.from_yaml(models.ROOT / f"{domain}-system.yaml")
        replacement = copy.deepcopy(system.get_component(owner))
        replacement.metadata["bmi_class"] = f"examples.complex_models.models:{cls}"
        swapped = swap_component(system, owner, replacement)
        first = models.evaluate(domain, data, models.BASELINES[domain], system)["prediction"]
        second = models.evaluate(domain, data, models.BASELINES[domain], swapped)["prediction"]
        assert not np.allclose(first, second)


def test_numerical_audit_rejects_missing_successful_recommendation(tmp_path):
    from examples.complex_models.run import study
    from examples.local_models.run import write_json
    from scripts.audit_complex_models import audit

    row = study("copper", "sobol", 0, 2, tmp_path / "copper-sobol-0", {}, checkpoints=())
    row["recommendation"] = {"action_id": None}
    row["test"] = None
    write_json(tmp_path / "results.json", {"runs": [row]})
    with pytest.raises(AssertionError):
        audit(tmp_path)


def test_unusable_module_sensor_is_flagged_and_diagnostic_withdrawn():
    from scripts.check_complex_data_quality import quality
    from examples.complex_models.workflow import diagnostic_score

    qa = quality()
    assert qa["invalid_module_temperature_rows"] == qa["columns"]["module_c"]["count"]
    assert qa["module_temperature_status"] == "unavailable"
    data = models.load_data("solar_diode")
    outputs = models.evaluate("solar_diode", data, models.BASELINES["solar_diode"])
    result = diagnostic_score("solar_diode", data, outputs, "validation")
    assert "temperature_rmse" not in result
    assert "unavailable" in result["module_temperature_observation_status"]
    assert result["rmse"] > 0
