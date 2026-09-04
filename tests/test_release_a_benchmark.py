"""Contracts for the preregistered Release A optimization benchmark."""

# waterology: allow-unseeded - noise probes use the benchmark's explicit SeedSequence.

from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from autoengineering.benchmarks.release_a import __main__ as benchmark_main
from autoengineering.benchmarks.release_a import runner as benchmark_runner
from autoengineering.benchmarks.release_a.methods import METHOD_NAMES, Suggestion, _smac_cost
from autoengineering.benchmarks.release_a.problems import (
    EVALUATIONS_PER_RUN,
    benchmark_problems,
    problem_by_name,
)
from autoengineering.benchmarks.release_a.runner import (
    BudgetOverrunError,
    execute_run,
    execute_suite,
    read_raw_records,
    scientific_signature,
    write_raw_records,
)
from autoengineering.benchmarks.release_a.summary import (
    evaluate_gate,
    gate_json,
    render_report,
    summarize_records,
    summary_csv,
)
from autoengineering.optimization import EvaluationAction, EvaluationResult, EvaluationStatus


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


def test_frozen_off_optimum_equations_and_branches():
    smooth = problem_by_name("smooth_continuous")
    smooth_result = smooth.evaluate(
        _action({"x": 0.0, "y": 0.0}), benchmark_seed=0, evaluation_index=0
    )
    assert smooth_result.outcomes["score"] == pytest.approx(4.0 / 9.0)

    mixed = problem_by_name("mixed_space")
    robust = mixed.evaluate(
        _action({"algorithm": "robust", "depth": 3, "rate": 0.5}),
        benchmark_seed=0,
        evaluation_index=0,
    )
    fast = mixed.evaluate(
        _action({"algorithm": "fast", "depth": 4, "rate": 0.2}),
        benchmark_seed=0,
        evaluation_index=0,
    )
    assert robust.outcomes["score"] == pytest.approx(0.9375)
    assert fast.outcomes["score"] == pytest.approx(0.7375)

    conditional = problem_by_name("conditional_space")
    linear = conditional.evaluate(
        _action({"family": "linear", "slope": 0.2}), benchmark_seed=0, evaluation_index=0
    )
    quadratic = conditional.evaluate(
        _action({"family": "quadratic", "curvature": 0.5, "shift": 0.8}),
        benchmark_seed=0,
        evaluation_index=0,
    )
    assert linear.outcomes["score"] == pytest.approx(0.74)
    assert quadratic.outcomes["score"] == pytest.approx(0.71)


def test_frozen_noisy_chain_seed_constraints_and_costs():
    problem = problem_by_name("noisy_chain")
    reliable_config = {"architecture": "reliable", "control": 0.5, "stages": 4}
    turbo_config = {"architecture": "turbo", "control": 0.8, "stages": 2, "boost": 0.1}
    reliable = problem.evaluate(
        _action(reliable_config, index=2), benchmark_seed=7, evaluation_index=2
    )
    turbo = problem.evaluate(_action(turbo_config, index=2), benchmark_seed=7, evaluation_index=2)
    noise = float(np.random.default_rng(np.random.SeedSequence([50007, 2, 5])).normal(0.0, 0.02))

    assert reliable.outcomes["score"] == pytest.approx(0.81 + noise)
    assert reliable.outcomes["stability_margin"] == pytest.approx(0.14)
    assert reliable.cost == pytest.approx(1.45)
    assert turbo.outcomes["score"] == pytest.approx(0.9795 + noise)
    assert turbo.outcomes["stability_margin"] == pytest.approx(0.066)
    assert turbo.cost == pytest.approx(1.63)


@pytest.mark.parametrize("method", ["fixed", "random", "sobol"])
def test_base_methods_complete_exactly_ten_valid_evaluations(method):
    problem = problem_by_name("conditional_space")
    records = execute_run(problem, method, 7)

    assert len(records) == EVALUATIONS_PER_RUN
    assert [record["evaluation_index"] for record in records] == list(range(10))
    assert records[-1]["cumulative_cost"] <= problem.cost_budget
    assert all(not record["invalid_configuration"] for record in records)
    assert all(record["fallback_events"] == [] for record in records)
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


@pytest.mark.parametrize("invalid_seed", [30, True, 0.0])
def test_raw_reader_rejects_an_out_of_matrix_seed(tmp_path, invalid_seed):
    records = execute_run(problem_by_name("smooth_continuous"), "fixed", 0)
    records[0]["seed"] = invalid_seed
    path = tmp_path / "raw-records.jsonl"
    write_raw_records(path, records)

    with pytest.raises(ValueError, match="seed differs"):
        read_raw_records(path)


def test_gate_rejects_duplicate_evaluation_indices():
    records = execute_suite(
        problems=(problem_by_name("smooth_continuous"),),
        methods=("fixed",),
        seeds=(0,),
        replay_native=True,
        progress=False,
    )
    records[1]["evaluation_index"] = 0

    gate = evaluate_gate(records, provenance={"test": True})
    criteria = {criterion["name"]: criterion for criterion in gate["criteria"]}

    assert criteria["complete_matrix"]["passed"] is False
    assert criteria["scientific_record_audit"]["passed"] is False


def test_completed_evaluation_survives_observe_failure(monkeypatch):
    problem = problem_by_name("smooth_continuous")
    delegate = benchmark_runner.build_method("fixed", problem, 0)

    class FailingObserveAdapter:
        name = "fixed"
        replayable = True

        def suggest(self, ledger):
            return delegate.suggest(ledger)

        def observe(self, action, result, selected_problem):
            raise RuntimeError("observe failed")

        def close(self):
            delegate.close()

    monkeypatch.setattr(
        benchmark_runner,
        "build_method",
        lambda method, selected_problem, seed: FailingObserveAdapter(),
    )

    records = execute_suite(
        problems=(problem,), methods=("fixed",), seeds=(0,), replay_native=False, progress=False
    )

    assert [record["record_type"] for record in records] == ["evaluation", "run_error"]
    assert records[0]["result"]["status"] == "success"
    assert records[0]["optimizer_overhead_seconds"] >= 0
    assert records[1]["stage"] == "primary"


def test_completed_run_survives_cleanup_failure(monkeypatch):
    problem = problem_by_name("smooth_continuous")
    delegate = benchmark_runner.build_method("fixed", problem, 0)

    class FailingCloseAdapter:
        name = "fixed"
        replayable = True

        def suggest(self, ledger):
            return delegate.suggest(ledger)

        def observe(self, action, result, selected_problem):
            return delegate.observe(action, result, selected_problem)

        def close(self):
            raise RuntimeError("cleanup failed")

    monkeypatch.setattr(
        benchmark_runner,
        "build_method",
        lambda method, selected_problem, seed: FailingCloseAdapter(),
    )

    records = execute_suite(
        problems=(problem,), methods=("fixed",), seeds=(0,), replay_native=False, progress=False
    )

    assert len([record for record in records if record["record_type"] == "evaluation"]) == 10
    assert records[-1]["record_type"] == "run_error"
    assert records[-1]["error"] == "cleanup failed"


def test_only_boundary_exceptions_set_invalid_and_budget_flags(monkeypatch):
    problem = problem_by_name("smooth_continuous")
    delegate = benchmark_runner.build_method("fixed", problem, 0)

    class InvalidAdapter:
        name = "fixed"
        replayable = True

        def suggest(self, ledger):
            suggestion = delegate.suggest(ledger)
            return Suggestion(replace(suggestion.action, config={"unknown": 1.0}))

        def observe(self, action, result, selected_problem):
            return None

        def close(self):
            return None

    monkeypatch.setattr(
        benchmark_runner,
        "build_method",
        lambda method, selected_problem, seed: InvalidAdapter(),
    )
    records = execute_suite(
        problems=(problem,), methods=("fixed",), seeds=(0,), replay_native=False, progress=False
    )
    internal = benchmark_runner._error_record(
        problem, "fixed", 0, ValueError("internal"), "primary"
    )
    budget = benchmark_runner._error_record(
        problem, "fixed", 0, BudgetOverrunError("over"), "primary"
    )

    assert len(records) == 1
    assert records[0]["record_type"] == "run_error"
    assert records[0]["invalid_configuration"] is True
    assert records[0]["budget_overrun"] is False
    assert internal["invalid_configuration"] is False
    assert internal["budget_overrun"] is False
    assert budget["invalid_configuration"] is False
    assert budget["budget_overrun"] is True


def test_budget_boundary_records_only_the_blocked_evaluation():
    problem = replace(problem_by_name("smooth_continuous"), cost_budget=9.5)

    records = execute_suite(
        problems=(problem,), methods=("fixed",), seeds=(0,), replay_native=False, progress=False
    )

    assert len([record for record in records if record["record_type"] == "evaluation"]) == 9
    assert records[-1]["record_type"] == "run_error"
    assert records[-1]["invalid_configuration"] is False
    assert records[-1]["budget_overrun"] is True


def test_smac_uses_one_fixed_penalty_for_infeasible_results():
    problem = problem_by_name("constrained_continuous")
    infeasible = problem.evaluate(
        _action({"x": 0.0, "y": 0.0}), benchmark_seed=0, evaluation_index=0
    )
    failure = EvaluationResult.model_failure(
        "eval-000000", "failed", cost=1.0, cost_unit="evaluation_cost"
    )

    assert _smac_cost(problem, infeasible) == 10.0
    assert _smac_cost(problem, failure) == 10.0


def test_new_benchmark_refuses_a_dirty_checkout(monkeypatch, tmp_path):
    monkeypatch.setattr(
        benchmark_main,
        "_git_output",
        lambda root, *arguments: " M source.py",
    )

    with pytest.raises(ValueError, match="clean Git checkout"):
        benchmark_main._provenance(tmp_path, tmp_path / "results")


def test_failed_benchmark_publication_leaves_no_output(monkeypatch, tmp_path):
    output = tmp_path / "results"
    monkeypatch.setattr(benchmark_main, "_provenance", lambda root, selected: {"test": True})
    monkeypatch.setattr(
        benchmark_main,
        "execute_suite",
        lambda: (_ for _ in ()).throw(RuntimeError("suite failed")),
    )

    with pytest.raises(RuntimeError, match="suite failed"):
        benchmark_main.run_new(output)

    assert not output.exists()
    assert not list(tmp_path.iterdir())


def test_existing_benchmark_output_is_never_changed(monkeypatch, tmp_path):
    output = tmp_path / "results"
    output.mkdir()
    evidence = output / "evidence.txt"
    evidence.write_bytes(b"original")
    monkeypatch.setattr(
        benchmark_main,
        "_provenance",
        lambda root, selected: (_ for _ in ()).throw(AssertionError("must not run")),
    )

    with pytest.raises(ValueError, match="already exists"):
        benchmark_main.run_new(output)

    assert evidence.read_bytes() == b"original"


def test_concurrent_output_is_not_replaced(monkeypatch, tmp_path):
    output = tmp_path / "results"
    monkeypatch.setattr(benchmark_main, "_provenance", lambda root, selected: {"test": True})
    monkeypatch.setattr(benchmark_main, "execute_suite", lambda: [])

    def create_competing_output(path, records):
        output.mkdir()
        (output / "evidence.txt").write_bytes(b"competing")
        path.write_text("", encoding="utf-8")

    monkeypatch.setattr(benchmark_main, "write_raw_records", create_competing_output)
    monkeypatch.setattr(
        benchmark_main,
        "_artifact_texts",
        lambda records, provenance: ({}, {"passed": True}),
    )

    with pytest.raises(ValueError, match="appeared before atomic publication"):
        benchmark_main.run_new(output)

    assert (output / "evidence.txt").read_bytes() == b"competing"
    assert not (tmp_path / ".results.lock").exists()


def test_checked_release_a_artifacts_reconstruct_from_raw_records():
    root = Path(__file__).resolve().parents[1]
    output = root / "benchmarks/release_a/results"
    records = read_raw_records(output / "raw-records.jsonl")
    existing_gate = json.loads((output / "gate.json").read_text(encoding="utf-8"))
    rows = summarize_records(records)
    rebuilt_gate = evaluate_gate(records, provenance=existing_gate["provenance"])

    assert summary_csv(rows) == (output / "run-summary.csv").read_text(encoding="utf-8")
    assert gate_json(rebuilt_gate) == (output / "gate.json").read_text(encoding="utf-8")
    assert render_report(rows, rebuilt_gate) == (output / "report.md").read_text(encoding="utf-8")


def test_preregistered_method_order_is_stable():
    assert METHOD_NAMES == ("fixed", "random", "sobol", "smac", "botorch")
