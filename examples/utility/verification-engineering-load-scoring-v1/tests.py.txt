"""Authored lifecycle outputs test all-case feasibility, aggregation and failure work."""

from dataclasses import replace
from types import SimpleNamespace
import json

import numpy as np
import pytest

from examples.utility import engineering_load_scoring as module

H = "1" * 64


def cases():
    return tuple(
        {
            "scenario_id": f"authored-{i}",
            "forcing": {"ground_voltage": 0.025, "resistor1_ohm": 110.0, "resistor2_ohm": 8000.0},
            "weight": 1 / 24,
        }
        for i in range(24)
    )


def setup(tmp_path, monkeypatch, change=None):
    root = tmp_path / "private-results"
    root.mkdir(mode=0o700)
    model = SimpleNamespace(digest=H, inputs=(), outputs=())
    monkeypatch.setattr(module.load, "context", lambda *a, **kw: SimpleNamespace(model=model))
    monkeypatch.setattr(module.load, "adapter", lambda: None)
    count = []

    def run(*a, **kw):
        index = len(count)
        count.append(1)
        assert (root / f"{index:02d}-intent.json").exists()
        if change == "failure" and index == 2:
            raise RuntimeError("PRIVATE-ENGINEERING-ERROR")
        diag = {
            "converged": 1.0,
            "residual_norm": 1e-12,
            "residual_tolerance": 1e-10,
            "solver_iterations": 4.0,
            "component_calls": 20.0,
            "derivative_calls": 0.0,
        }
        outputs = {"node1_voltage": 5.025, "node2_voltage": 0.7}
        if index == 4:
            if change == "voltage":
                outputs["node2_voltage"] = 0.6
            elif change == "negative_power":
                outputs["node1_voltage"] = 0.0
            elif change == "residual":
                diag["residual_norm"] = 2e-10
            elif change == "nonfinite":
                outputs["node1_voltage"] = float("nan")
            elif change == "counter":
                diag["component_calls"] = 0.5
        return SimpleNamespace(
            training=SimpleNamespace(status="not_applicable"),
            outputs={k: np.asarray(v) for k, v in outputs.items()},
            diagnostics=diag,
            elapsed_seconds=0.01,
        )

    monkeypatch.setattr(module, "run_lifecycle", run)
    policy = module.LoadScorePolicy(
        "utility-coupled-load-score-v1", H, module.source_identity(), 0.62
    )
    return root, policy, count


def test_exact_mean_all_case_checks_and_native_work(tmp_path, monkeypatch):
    root, policy, count = setup(tmp_path, monkeypatch)
    score = module.score_loads(0.05, cases(), root, tmp_path, policy=policy, execution_digest=H)
    assert score.status == "success" and score.value == pytest.approx(0.25) and score.feasible
    assert len(count) == 24
    result = json.loads((root / "complete.json").read_text())
    assert result["inner_work"] == {
        "solver_iterations": 96,
        "component_calls": 480,
        "derivative_calls": 0,
    }
    assert result["completed_model_starts"] == 24 and not result["task_admitted"]
    with pytest.raises(ValueError, match="consumed"):
        module.score_loads(0.05, cases(), root, tmp_path, policy=policy, execution_digest=H)
    assert len(count) == 24


@pytest.mark.parametrize("change", ["voltage", "negative_power", "residual"])
def test_one_physical_failure_vetoes_aggregate_without_penalty_objective(
    tmp_path, monkeypatch, change
):
    root, policy, count = setup(tmp_path, monkeypatch, change)
    score = module.score_loads(0.05, cases(), root, tmp_path, policy=policy, execution_digest=H)
    assert (
        score.status == "scientific_infeasible" and score.value is None and score.feasible is False
    )
    assert len(count) == 24
    assert not json.loads((root / "complete.json").read_text())["all_cases_feasible"]


@pytest.mark.parametrize(
    "change,attempted,completed", [("failure", 3, 2), ("nonfinite", 5, 4), ("counter", 5, 4)]
)
def test_failed_model_retains_attempts_and_unknown_work_without_error_payload(
    tmp_path, monkeypatch, change, attempted, completed
):
    root, policy, count = setup(tmp_path, monkeypatch, change)
    score = module.score_loads(0.05, cases(), root, tmp_path, policy=policy, execution_digest=H)
    assert score.status == "model_failure" and score.value is None
    failure = json.loads((root / "failed.json").read_text())
    assert failure["attempted_model_starts"] == len(count) == attempted
    assert (
        failure["completed_model_starts"] == completed
        and failure["last_attempt_inner_work_unknown"]
    )
    assert failure["known_completed_inner_work"]["component_calls"] == completed * 20
    assert "PRIVATE-ENGINEERING" not in (root / "failed.json").read_text()
    assert not (root / "complete.json").exists()


@pytest.mark.parametrize(
    "change", ["count", "ids", "resistance", "weight", "policy", "design", "model"]
)
def test_invalid_profile_starts_no_model(tmp_path, monkeypatch, change):
    root, policy, count = setup(tmp_path, monkeypatch)
    rows = list(cases())
    current = 0.05
    if change == "count":
        rows = rows[:23]
    elif change == "ids":
        rows[1] = dict(rows[1]) | {"scenario_id": rows[0]["scenario_id"]}
    elif change == "resistance":
        rows[0] = dict(rows[0]) | {"forcing": dict(rows[0]["forcing"]) | {"resistor1_ohm": -1.0}}
    elif change == "weight":
        rows[0] = dict(rows[0]) | {"weight": 0.5}
    elif change == "policy":
        policy = replace(policy, scorer_source_digest="0" * 64)
    elif change == "design":
        current = True
    else:
        policy = replace(policy, expected_model_digest="0" * 64)
    with pytest.raises(ValueError):
        module.score_loads(current, rows, root, tmp_path, policy=policy, execution_digest=H)
    assert not count and not list(root.iterdir())
