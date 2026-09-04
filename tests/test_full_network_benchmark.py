from __future__ import annotations

import copy
import json

from autoengineering.optimization import EvaluationAction, EvaluationResult
from autoengineering.benchmarks.full_network.problems import (
    benchmark_problems,
    problem_by_name,
)
from autoengineering.benchmarks.full_network.runner import (
    BENCHMARK_SEEDS,
    EVALUATIONS_PER_RUN,
    METHODS,
    WARM_START_COUNT,
    read_raw_records,
    scientific_signature,
    write_raw_records,
)
from autoengineering.benchmarks.full_network.summary import (
    calibration_metrics,
    evaluate_gate,
    render_report,
    summarize_records,
    summary_csv,
)


def _config(problem_name: str, index: int) -> dict[str, object]:
    value = 0.05 + 0.09 * index
    if problem_name == "smooth_chain":
        return {
            "warp.choice": "base",
            "warp.x": value,
            "terminal.choice": "base",
            "terminal.y": 1.0 - value,
        }
    return {
        "left.choice": "base",
        "left.x": value,
        "right.choice": "base",
        "right.y": 1.0 - value,
    }


def _evidence():
    records = []
    calibration = []
    digest = "a" * 64
    for problem in benchmark_problems():
        for seed in BENCHMARK_SEEDS:
            for method in METHODS:
                best = None
                for index in range(EVALUATIONS_PER_RUN):
                    config = _config(problem.name, index)
                    action = EvaluationAction.system(
                        f"eval-{index:06d}",
                        config,
                        seed=index,
                        suggested_by=method,
                    )
                    truth = problem.analytic(config)
                    feasible = problem.feasible(truth)
                    if feasible:
                        objective = truth[problem.network.objective.outcome]
                        best = objective if best is None else max(best, objective)
                    if index >= WARM_START_COUNT:
                        records.append(
                            {
                                "record_type": "acquisition",
                                "schema_version": "1.0",
                                "problem": problem.name,
                                "method": method,
                                "seed": seed,
                                "evaluation_index": index,
                                "action": action.to_dict(),
                                "diagnostics": {"fallback_reasons": []},
                                "replay_consistent": True,
                                "optimizer_overhead_seconds": 0.0,
                            }
                        )
                    result = EvaluationResult.success(
                        action.id,
                        truth,
                        {name: 0.0 for name in truth},
                        1.0,
                        "evaluation",
                        artifacts={action.id: f"trace:{action.id}"},
                        artifact_sha256={action.id: digest},
                        evaluator_seconds=1.0,
                    )
                    records.append(
                        {
                            "record_type": "evaluation",
                            "schema_version": "1.0",
                            "problem": problem.name,
                            "method": method,
                            "seed": seed,
                            "evaluation_index": index,
                            "action": action.to_dict(),
                            "result": result.to_dict(),
                            "cumulative_cost": float(index + 1),
                            "feasible": feasible,
                            "best_feasible_objective": best,
                            "normalized_regret": problem.normalized_regret(best),
                            "invalid_configuration": False,
                            "budget_overrun": False,
                            "artifact_error": False,
                            "replay_consistent": True,
                            "optimizer_overhead_seconds": 0.0,
                        }
                    )
            for heldout_index in range(16):
                config = _config(problem.name, heldout_index % EVALUATIONS_PER_RUN)
                truth = problem.analytic(config)
                constraints = {}
                for constraint in problem.network.constraints:
                    feasible = (
                        truth[constraint.outcome] >= constraint.threshold
                        if constraint.operator == ">="
                        else truth[constraint.outcome] <= constraint.threshold
                    )
                    constraints[constraint.outcome] = {
                        "probability": float(feasible),
                        "feasible": feasible,
                    }
                objective = truth[problem.network.objective.outcome]
                calibration.append(
                    {
                        "schema_version": "1.0",
                        "problem": problem.name,
                        "seed": seed,
                        "heldout_index": heldout_index,
                        "config": config,
                        "truth": dict(truth),
                        "objective_mean": objective,
                        "objective_lower": objective - 0.1,
                        "objective_upper": objective + 0.1,
                        "objective_variance": 0.01,
                        "constraints": constraints,
                    }
                )
    return records, calibration


def test_frozen_problems_validate_and_match_analytic_functions():
    problems = benchmark_problems()
    assert [problem.name for problem in problems] == ["smooth_chain", "constrained_branch"]
    for problem in problems:
        problem.network.validate(problem.system)
        config = _config(problem.name, 5)
        problem.space.encode(config)
        assert all(isinstance(value, float) for value in problem.analytic(config).values())
        assert problem_by_name(problem.name).name == problem.name


def test_raw_evidence_reconstructs_gate_and_serialization(tmp_path):
    records, calibration = _evidence()
    gate = evaluate_gate(records, calibration, provenance={"revision": "test"})
    assert gate["passed"] is True
    assert calibration_metrics(calibration)["coverage_90"] == 1.0
    rows = summarize_records(records)
    assert len(rows) == 40
    assert summary_csv(rows).startswith("problem,method,seed,completed")
    path = tmp_path / "raw.jsonl"
    write_raw_records(path, records)
    assert read_raw_records(path) == json.loads(
        json.dumps(records, sort_keys=True, separators=(",", ":"))
    )
    assert scientific_signature(records) == scientific_signature(read_raw_records(path))


def test_adverse_fallback_result_is_retained_and_fails_gate():
    records, calibration = _evidence()
    adverse = copy.deepcopy(records)
    for record in adverse:
        if record["record_type"] == "acquisition" and record["method"] == "function_network_full":
            record["diagnostics"]["fallback_reasons"] = ["fit_failure"]
    gate = evaluate_gate(adverse, calibration, provenance={"revision": "test"})
    assert gate["passed"] is False
    criterion = next(
        item for item in gate["criteria"] if item["name"] == "bounded_full_network_fallbacks"
    )
    assert criterion["passed"] is False
    assert "favorable, null, or adverse" in render_report(summarize_records(adverse), gate)
