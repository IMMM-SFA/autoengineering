"""A reduced budget must never select improvements observed after its cutoff."""

import json
from pathlib import Path
import sys

import pytest

pytest.importorskip("bmipy")
pytest.importorskip("pvlib")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.cap_complex_models import cutoff


def evidence(values, target):
    entries, trajectory = [], []
    best = float("inf")
    for i, value in enumerate(values):
        best = min(best, value)
        entries.append(
            {
                "action": {"id": f"eval-{i:06d}", "config": {"x": i}},
                "result": {
                    "status": "success",
                    "cost": 1.0,
                    "cost_unit": "model_call",
                    "outcomes": {"rmse": value},
                },
            }
        )
        trajectory.append(
            {"evaluations": i + 1, "best_validation_rmse": best, "target_reached": best <= target}
        )
    return entries, trajectory


def test_later_improvement_and_target_hit_are_excluded():
    entries, trajectory = evidence([9.0, 8.0, 4.0, 1.0], target=2.0)
    kept, steps, rec = cutoff(entries, trajectory, 2, 2.0)
    assert len(kept) == 2
    assert rec["config"] == {"x": 1}
    assert rec["outcomes"] == {"rmse": 8.0}
    assert not steps[-1]["target_reached"]


def test_earlier_target_hit_is_preserved():
    entries, trajectory = evidence([9.0, 1.0, 0.5], target=2.0)
    kept, steps, rec = cutoff(entries, trajectory, 3, 2.0)
    assert len(kept) == 2
    assert rec["action_id"] == "eval-000001"
    assert steps[-1]["target_reached"]


def test_partial_source_beyond_cutoff_is_sufficient():
    entries, trajectory = evidence([9.0, 8.0, 7.0], target=2.0)
    assert len(cutoff(entries, trajectory, 2, 2.0)[0]) == 2


def test_insufficient_prefix_is_not_a_completed_study():
    entries, trajectory = evidence([9.0], target=2.0)
    with pytest.raises(ValueError, match="Incomplete prefix"):
        cutoff(entries, trajectory, 2, 2.0)


def test_trajectory_mismatch_is_rejected():
    entries, trajectory = evidence([9.0, 8.0], target=2.0)
    trajectory[1]["best_validation_rmse"] = 1.0
    with pytest.raises(ValueError, match="Trajectory disagrees"):
        cutoff(entries, trajectory, 2, 2.0)


def test_failed_observation_and_equal_minimum_preserve_first_success():
    entries, trajectory = evidence([9.0, 8.0, 8.0], target=2.0)
    entries[0]["result"]["status"] = "model_failure"
    entries[0]["result"]["outcomes"] = {}
    trajectory[0]["best_validation_rmse"] = None
    assert cutoff(entries, trajectory, 3, 2.0)[2]["action_id"] == "eval-000001"


def test_projection_freezes_cutoff_config_before_scoring(tmp_path, monkeypatch):
    from scripts import cap_complex_models as module

    source, output = tmp_path / "raw", tmp_path / "derived"
    source.mkdir()
    entries, trajectory = evidence([9.0, 8.0, 1.0], target=2.0)
    for i, step in enumerate(trajectory):
        step.update(study_seconds=float((i + 1) * 10), model_seconds=float(i + 1))
    raw = b"".join((json.dumps(e) + "\n").encode() for e in entries)
    (source / "observations.jsonl").write_bytes(raw)
    (source / "trajectory.json").write_text(json.dumps(trajectory))
    monkeypatch.setattr(module, "load_data", lambda domain: "data")

    def evaluate(domain, data, config):
        assert config == {"x": 1}
        assert json.loads((output / "frozen-recommendation.json").read_text())["config"] == config
        return config

    monkeypatch.setattr(module, "evaluate", evaluate)
    monkeypatch.setattr(module, "score", lambda domain, data, output, split: {"rmse": 42.0})
    row = module.project(source, output, "copper", "random", 3, 2, 2.0)
    assert row["test"] == {"rmse": 42.0}
    assert row["study_seconds"] == 20.0
    assert row["model_seconds"] == 2.0
    assert row["controller_and_optimizer_seconds"] == 18.0
    assert row["projection"]["discarded_from_analysis"] == 1
    assert row["projection"]["source_ledger_sha256"] == module.digest(source / "observations.jsonl")
    assert (source / "observations.jsonl").read_bytes() == raw
    assert (output / "observations.jsonl").read_bytes() == b"".join(
        raw.splitlines(keepends=True)[:2]
    )
    assert not (output / "study.json").exists()
