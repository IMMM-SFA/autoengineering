"""Contracts for the preregistered Release A optimization benchmark."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys

import pytest

from autoengineering.benchmarks.release_a.methods import METHOD_NAMES
from autoengineering.benchmarks.release_a.problems import (
    EVALUATIONS_PER_RUN,
    benchmark_problems,
    problem_by_name,
)
from autoengineering.benchmarks.release_a.runner import (
    execute_run,
    execute_suite,
    read_raw_records,
    scientific_signature,
    write_raw_records,
)
from autoengineering.benchmarks.release_a.summary import (
    evaluate_gate,
    gate_json,
    summarize_records,
    summary_csv,
)
from autoengineering.optimization import EvaluationAction, EvaluationStatus


def _action(config: dict[str, object], *, index: int = 0) -> EvaluationAction:
    return EvaluationAction.system(f"eval-{index:06d}", config, seed=17)


def _configs(records: list[dict[str, object]]) -> list[dict[str, object]]:
    return [dict(record["action"]["config"]) for record in records]


def test_frozen_problem_definitions_and_reference_points():
    problems = benchmark_problems()

    assert [problem.name for problem in problems] == [
        "smooth_continuous",
        "constrained_continuous",
        "mixed_space",
        "conditional_space",
        "noisy_chain",
    ]
    assert [problem.study(3).seed for problem in problems] == [10003, 20003, 30003, 40003, 50003]
    for problem in problems[:4]:
        action = _action(problem.reference_config)
        result = problem.evaluate(action, benchmark_seed=0, evaluation_index=0)
        assert result.status is EvaluationStatus.SUCCESS
        assert result.outcomes[problem.objective.outcome] == pytest.approx(1.0)
        assert problem.is_feasible(result)

    noisy = problems[-1]
    result = noisy.evaluate(_action(noisy.reference_config), benchmark_seed=0, evaluation_index=0)
    assert result.status is EvaluationStatus.SUCCESS
    assert result.standard_errors == {"score": 0.02, "stability_margin": 1e-6}
    assert result.cost == pytest.approx(1.92)
    assert noisy.is_feasible(result)


def test_frozen_constraint_and_failure_semantics():
    constrained = problem_by_name("constrained_continuous")
    result = constrained.evaluate(
        _action({"x": 0.0, "y": 0.0}), benchmark_seed=0, evaluation_index=0
    )
    assert constrained.constraint_violation(result)
    assert not constrained.is_feasible(result)

    noisy = problem_by_name("noisy_chain")
    failure_config = {"architecture": "turbo", "control": 0.95, "stages": 4, "boost": 0.8}
    failure = noisy.evaluate(_action(failure_config), benchmark_seed=0, evaluation_index=0)
    assert failure.status is EvaluationStatus.MODEL_FAILURE
    assert failure.cost == pytest.approx(noisy.preview_cost(failure_config))
    with pytest.raises(ValueError, match="0 through 29"):
        noisy.study(30)


@pytest.mark.parametrize("method", ["fixed", "random", "sobol"])
def test_base_methods_complete_exactly_ten_valid_evaluations(method):
    problem = problem_by_name("conditional_space")
    records = execute_run(problem, method, 7)

    assert len(records) == EVALUATIONS_PER_RUN
    assert [record["evaluation_index"] for record in records] == list(range(10))
    assert records[-1]["cumulative_cost"] <= problem.cost_budget
    assert all(not record["invalid_configuration"] for record in records)
    for record in records:
        problem.space.encode(record["action"]["config"])


def test_fixed_configuration_order_is_unscrambled_and_seed_independent():
    problem = problem_by_name("smooth_continuous")
    first = execute_run(problem, "fixed", 0)
    second = execute_run(problem, "fixed", 29)

    assert _configs(first) == _configs(second)
    assert _configs(first)[0] == {"x": 0.0, "y": 0.0}


@pytest.mark.parametrize("method", ["fixed", "random", "sobol"])
def test_native_scientific_records_replay_exactly(method):
    problem = problem_by_name("mixed_space")
    first = execute_run(problem, method, 11)
    second = execute_run(problem, method, 11)

    assert scientific_signature(first) == scientific_signature(second)


@pytest.mark.skipif(
    importlib.util.find_spec("botorch") is None or importlib.util.find_spec("smac") is None,
    reason="Bayesian benchmark dependencies are unavailable",
)
def test_modeled_methods_share_the_sobol_warm_start():
    problem = problem_by_name("mixed_space")
    sobol = execute_run(problem, "sobol", 2)
    smac = execute_run(problem, "smac", 2)
    botorch = execute_run(problem, "botorch", 2)

    assert _configs(smac)[:5] == _configs(sobol)[:5]
    assert _configs(botorch)[:5] == _configs(sobol)[:5]


def test_benchmark_imports_do_not_load_optional_backends():
    command = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "import autoengineering.benchmarks.release_a.problems; "
            "import autoengineering.benchmarks.release_a.summary; "
            "blocked=('torch','botorch','gpytorch','smac'); "
            "raise SystemExit(any(name in sys.modules for name in blocked))"
        ),
    ]

    completed = subprocess.run(command, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr


def test_raw_records_reconstruct_summary_and_failing_gate(tmp_path):
    problem = problem_by_name("smooth_continuous")
    records = execute_suite(
        problems=(problem,), methods=("fixed", "random"), seeds=(0,), progress=False
    )
    raw_path = tmp_path / "raw-records.jsonl"
    write_raw_records(raw_path, records)

    loaded = read_raw_records(raw_path)
    rows = summarize_records(loaded)
    gate = evaluate_gate(loaded, provenance={"test": True})

    assert loaded == records
    assert len(rows) == 2
    assert summary_csv(rows) == summary_csv(summarize_records(read_raw_records(raw_path)))
    assert gate["passed"] is False
    assert json.loads(gate_json(gate)) == gate


def test_raw_reader_rejects_an_invalid_envelope(tmp_path):
    path = tmp_path / "raw-records.jsonl"
    path.write_text('{"record_type":"unknown","schema_version":"1.0"}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="envelope"):
        read_raw_records(path)


def test_preregistered_method_order_is_stable():
    assert METHOD_NAMES == ("fixed", "random", "sobol", "smac", "botorch")
