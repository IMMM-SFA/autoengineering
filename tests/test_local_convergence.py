"""Check target stopping, call accounting and validation-only feedback."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("bmipy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from examples.local_models import convergence as runner


def test_target_accepts_only_finite_inclusive_observations():
    assert runner.reached({"rmse": 1.0}, 1.0)
    assert not runner.reached({"rmse": 1.01}, 1.0)
    assert not runner.reached({}, 1.0)
    assert not runner.reached({"rmse": float("nan")}, 1.0)
    assert not runner.reached({"rmse": float("inf")}, 1.0)


@pytest.mark.parametrize(
    "target,expected_count,reason", [(1e6, 1, "target_reached"), (0.0, 3, "evaluation_cap")]
)
def test_real_bmi_stopping_and_cap(tmp_path, target, expected_count, reason):
    row = runner.target_run("copper", "sobol", 3, 3, target, tmp_path / "run", {})
    entries = (tmp_path / "run/observations.jsonl").read_text().splitlines()
    assert row["evaluations"] == len(entries) == expected_count
    assert row["stop_reason"] == reason
    assert row["target_reached"] == (reason == "target_reached")
    assert len(row["trajectory"]) == expected_count
    assert all(not step["target_reached"] for step in row["trajectory"][:-1])
    assert row["study_seconds"] >= row["model_seconds"] > 0
    frozen = json.loads((tmp_path / "run/frozen-recommendation.json").read_text())
    assert frozen == row["recommendation"]


def test_test_labels_cannot_affect_stopping(tmp_path, monkeypatch):
    data = runner.load_data("copper")
    monkeypatch.setattr(runner, "load_data", lambda _: data.copy())
    first = runner.target_run("copper", "random", 4, 4, 0.22, tmp_path / "first", {})
    data.loc[data.split == "test", "expansion"] += 1000
    second = runner.target_run("copper", "random", 4, 4, 0.22, tmp_path / "second", {})
    assert first["recommendation"] == second["recommendation"]
    assert first["evaluations"] == second["evaluations"]
    assert first["target_reached"] == second["target_reached"]
    assert first["test"]["rmse"] != second["test"]["rmse"]


def test_failures_consume_calls_without_reaching_target(tmp_path, monkeypatch):
    def fail(*args):
        raise ValueError("Expected model failure")

    monkeypatch.setitem(runner.MODELS, "copper", fail)
    row = runner.target_run("copper", "random", 3, 3, 1e6, tmp_path / "run", {})
    assert row["evaluations"] == 3
    assert not row["target_reached"]
    assert row["test"] is None
    assert row["stop_reason"] == "evaluation_cap"


def test_unexpected_exception_counts_committed_attempts(tmp_path, monkeypatch):
    def fail(*args):
        raise RuntimeError("Expected infrastructure exception")

    monkeypatch.setitem(runner.MODELS, "copper", fail)
    row = runner.target_run("copper", "random", 3, 3, 1e6, tmp_path / "run", {})
    ledger = [
        json.loads(line) for line in (tmp_path / "run/observations.jsonl").read_text().splitlines()
    ]
    assert row["evaluations"] == len(ledger) == len(row["trajectory"])
    assert all(entry["result"]["status"] == "infrastructure_failure" for entry in ledger)
    assert not row["target_reached"]
    assert row["model_seconds"] > 0
    assert row["test"] is None


def test_report_rejects_false_cap_and_retains_backend_stop(tmp_path):
    from scripts.summarize_local_convergence import checked_runs

    output = tmp_path / "study"
    output.mkdir()
    row = runner.target_run("copper", "sobol", 3, 3, 0.0, output / "copper-sobol-3", {})
    row["cap"] = 60
    manifest = {
        "mode": "target",
        "inputs": {},
        "domains": ["copper"],
        "methods": ["sobol"],
        "seeds": [3],
        "targets": {"targets": {"copper": 0.0}},
    }
    runner.write_json(output / "manifest.json", manifest)
    runner.write_json(output / "results.json", {"runs": [row]})
    runner.write_json(output / "copper-sobol-3/application-result.json", row)
    with pytest.raises(AssertionError):
        checked_runs(output)
    row["stop_reason"] = "backend_stopped"
    runner.write_json(output / "results.json", {"runs": [row]})
    runner.write_json(output / "copper-sobol-3/application-result.json", row)
    assert checked_runs(output) == [row]


def test_report_does_not_hide_missing_test_outcomes():
    from scripts.summarize_local_convergence import number, test_median

    assert number(None) == "NA"
    assert test_median([{"test": None}, {"test": {"rmse": 1.0}}]) == "NA (missing test results)"
