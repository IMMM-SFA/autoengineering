"""Physical contracts, data provenance and held-out isolation for local examples."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

pytest.importorskip("bmipy")

ROOT = Path(__file__).resolve().parents[1] / "examples" / "local_models"
sys.path.insert(0, str(ROOT.parents[1]))
spec = importlib.util.spec_from_file_location("local_models_test_module", ROOT / "models.py")
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)


@pytest.mark.parametrize("domain", models.DOMAINS)
def test_held_out_labels_do_not_affect_predictions(domain):
    if domain == "solar":
        pytest.importorskip("pvlib")
    data = models.load_data(domain)
    for config in [models.BASELINES[domain], *models.SWAPS[domain]]:
        expected = models.MODELS[domain](data, config)["prediction"]
        changed = data.copy()
        changed.loc[changed.split != "train", models.TARGETS[domain]] = -99999.0
        actual = models.MODELS[domain](changed, config)["prediction"]
        np.testing.assert_array_equal(actual, expected)
        assert np.isfinite(actual).all()


def test_hydro_water_balance_and_causal_prefix():
    data = models.load_data("hydro")
    for config in [models.BASELINES["hydro"], *models.SWAPS["hydro"]]:
        result = models.hydro_model(data, config)
        assert np.max(np.abs(result["balance_residual"])) < 1e-10
        assert np.all(result["prediction"] >= 0)
        np.testing.assert_array_equal(
            models.hydro_model(data.iloc[:365], config)["prediction"], result["prediction"][:365]
        )


def test_solar_matches_rated_power_and_zero_irradiance():
    pytest.importorskip("pvlib")
    assert models.solar_power(np.array([0.0]), np.array([25.0]), loss=1.0)[0] == 0
    assert models.solar_power(np.array([1000.0]), np.array([25.0]), loss=1.0)[0] == 1910
    np.testing.assert_array_equal(
        models.solar_temperature(np.array([0.0]), np.array([10.0]), model="ross", heat_loss=25.0),
        [10.0],
    )


def test_checked_raw_source_hashes():
    manifest = json.loads((ROOT / "data" / "sources.json").read_text())
    for source in manifest["sources"]:
        path = ROOT / "data" / "raw" / source["file"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == source["stored_sha256"]


def test_temperature_mean_is_not_sufficient_for_power(tmp_path, monkeypatch):
    pytest.importorskip("pvlib")
    monkeypatch.setitem(sys.modules, "models", models)
    spec = importlib.util.spec_from_file_location("component_probe", ROOT / "component_probe.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.probe(tmp_path / "probe")
    assert result["reused_power_matches_full"]
    assert abs(result["temperature_mean_difference"]) < 1e-12
    assert abs(result["mean_power_difference_kw"]) > 0.01


def test_study_feedback_excludes_test_response(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "models", models)
    spec = importlib.util.spec_from_file_location("local_examples_run", ROOT / "run.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    original = models.load_data("copper")
    monkeypatch.setattr(runner, "load_data", lambda _: original.copy())
    first = runner.study_run("copper", "sobol", 0, 4, tmp_path / "first")
    changed = original.copy()
    changed.loc[changed.split == "test", "expansion"] += 1000
    monkeypatch.setattr(runner, "load_data", lambda _: changed.copy())
    second = runner.study_run("copper", "sobol", 0, 4, tmp_path / "second")
    assert first["recommendation"] == second["recommendation"]
    assert first["test"]["rmse"] != second["test"]["rmse"]
    from autoengineering.optimization import ObservationLedger

    entries = ObservationLedger(tmp_path / "first" / "observations.jsonl").entries()
    assert all(set(result.outcomes) == {"rmse"} for _, result in entries)


def test_saved_swapped_system_drives_changed_model(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "models", models)
    spec = importlib.util.spec_from_file_location("local_examples_workflow", ROOT / "run.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.workflow("copper", tmp_path)
    from autoengineering.system.graph import System

    data = models.load_data("copper")
    predictions = []
    for index in [0, 1]:
        system = System.from_yaml(tmp_path / f"copper-candidate-{index}.yaml")
        config = system.get_component("regression").metadata["configuration"]
        predictions.append(models.copper_model(data, config)["prediction"])
    assert not np.allclose(*predictions)
