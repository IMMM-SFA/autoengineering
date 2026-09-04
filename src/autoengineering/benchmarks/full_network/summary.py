"""Reconstruct Item 8 summaries and evaluate its frozen criteria."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import csv
import io
from itertools import product
import json
import math

import numpy as np

from autoengineering.optimization import EvaluationAction, EvaluationResult, EvaluationScope

from .problems import benchmark_problems, problem_by_name
from .runner import (
    BENCHMARK_SEEDS,
    EVALUATIONS_PER_RUN,
    METHODS,
    WARM_START_COUNT,
    canonical_json,
)

SUMMARY_FIELDS = (
    "problem",
    "method",
    "seed",
    "completed",
    "evaluation_count",
    "acquisition_count",
    "final_regret",
    "regret_area",
    "total_cost",
    "system_scope",
    "replay_consistent",
    "unresolved_fallback_suggestions",
    "optimizer_overhead_seconds",
    "error",
)


def summarize_records(records: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    """Build one row for every observed problem, method, and seed."""
    evaluations = defaultdict(list)
    acquisitions = defaultdict(list)
    errors = defaultdict(list)
    for record in records:
        key = (str(record["problem"]), str(record["method"]), int(record["seed"]))
        if record["record_type"] == "evaluation":
            evaluations[key].append(record)
        elif record["record_type"] == "acquisition":
            acquisitions[key].append(record)
        elif record["record_type"] == "run_error":
            errors[key].append(record)
        else:
            raise ValueError(f"unknown raw record type: {record['record_type']!r}")
    problem_order = {item.name: index for index, item in enumerate(benchmark_problems())}
    method_order = {name: index for index, name in enumerate(METHODS)}
    keys = sorted(
        set(evaluations) | set(acquisitions) | set(errors),
        key=lambda key: (problem_order[key[0]], method_order[key[1]], key[2]),
    )
    rows = []
    for key in keys:
        problem_name, method, seed = key
        group = sorted(evaluations[key], key=lambda item: int(item["evaluation_index"]))
        decisions = acquisitions[key]
        run_errors = errors[key]
        rows.append(
            {
                "problem": problem_name,
                "method": method,
                "seed": seed,
                "completed": (
                    len(group) == EVALUATIONS_PER_RUN
                    and len(decisions) == EVALUATIONS_PER_RUN - WARM_START_COUNT
                    and not run_errors
                ),
                "evaluation_count": len(group),
                "acquisition_count": len(decisions),
                "final_regret": "" if not group else float(group[-1]["normalized_regret"]),
                "regret_area": _regret_area(group),
                "total_cost": 0.0 if not group else float(group[-1]["cumulative_cost"]),
                "system_scope": all(
                    item["action"]["scope"] == EvaluationScope.SYSTEM.value
                    for item in group + decisions
                ),
                "replay_consistent": bool(group + decisions)
                and all(item["replay_consistent"] is True for item in group + decisions),
                "unresolved_fallback_suggestions": sum(
                    bool(item["diagnostics"]["fallback_reasons"]) for item in decisions
                ),
                "optimizer_overhead_seconds": sum(
                    float(item["optimizer_overhead_seconds"]) for item in group
                ),
                "error": " | ".join(
                    f"{item['error_type']}: {item['error']}" for item in run_errors
                ),
            }
        )
    return rows


def _regret_area(records: list[Mapping[str, object]]) -> float | str:
    if not records:
        return ""
    area = 0.0
    previous_cost = 0.0
    previous_regret = 1.0
    for record in records:
        cost = float(record["cumulative_cost"])
        area += (cost - previous_cost) * previous_regret
        previous_cost = cost
        previous_regret = float(record["normalized_regret"])
    area += max(0.0, 10.0 - previous_cost) * previous_regret
    return area / 10.0


def summary_csv(rows: Iterable[Mapping[str, object]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def calibration_metrics(
    records: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Recompute held-out coverage and constraint Brier score."""
    records = list(records)
    expected = len(benchmark_problems()) * len(BENCHMARK_SEEDS) * 16
    covered = 0
    finite = True
    brier_terms = []
    issues = []
    seen = set()
    for record in records:
        label = (
            str(record["problem"]),
            int(record["seed"]),
            int(record["heldout_index"]),
        )
        if label in seen:
            issues.append(f"duplicate held-out record: {label!r}")
        seen.add(label)
        problem = problem_by_name(label[0])
        config = record["config"]
        try:
            problem.space.encode(config)
            truth = problem.analytic(config)
        except (TypeError, ValueError, KeyError) as error:
            issues.append(f"invalid held-out configuration {label!r}: {error}")
            continue
        if set(truth) != set(record["truth"]) or any(
            not math.isclose(float(record["truth"][name]), value, rel_tol=0.0, abs_tol=1e-12)
            for name, value in truth.items()
        ):
            issues.append(f"held-out truth differs at {label!r}")
        objective = truth[problem.network.objective.outcome]
        lower = float(record["objective_lower"])
        upper = float(record["objective_upper"])
        mean = float(record["objective_mean"])
        variance = float(record["objective_variance"])
        finite &= all(math.isfinite(value) for value in (lower, upper, mean, variance))
        finite &= variance >= 0.0 and lower <= upper
        covered += lower <= objective <= upper
        constraints = record["constraints"]
        if set(constraints) != {item.outcome for item in problem.network.constraints}:
            issues.append(f"held-out constraint names differ at {label!r}")
            continue
        for constraint in problem.network.constraints:
            observed = constraints[constraint.outcome]
            probability = float(observed["probability"])
            feasible = bool(
                truth[constraint.outcome] >= constraint.threshold
                if constraint.operator == ">="
                else truth[constraint.outcome] <= constraint.threshold
            )
            if observed["feasible"] is not feasible:
                issues.append(f"held-out feasibility differs at {label!r}")
            finite &= math.isfinite(probability) and 0.0 <= probability <= 1.0
            brier_terms.append((probability - float(feasible)) ** 2)
    coverage = None if not records else covered / len(records)
    brier = None if not brier_terms else float(np.mean(brier_terms))
    return {
        "expected_records": expected,
        "observed_records": len(records),
        "unique_records": len(seen),
        "coverage_90": coverage,
        "constraint_brier": brier,
        "finite_moments": finite,
        "issue_count": len(issues),
        "reported_issues": issues[:100],
    }


def evaluate_gate(
    records: Iterable[Mapping[str, object]],
    calibration: Iterable[Mapping[str, object]],
    *,
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Evaluate every preregistered criterion without changing its threshold."""
    records = list(records)
    calibration = list(calibration)
    rows = summarize_records(records)
    expected_keys = set(
        product((item.name for item in benchmark_problems()), METHODS, BENCHMARK_SEEDS)
    )
    observed_keys = {(row["problem"], row["method"], row["seed"]) for row in rows}
    evaluations = [item for item in records if item["record_type"] == "evaluation"]
    acquisitions = [item for item in records if item["record_type"] == "acquisition"]
    criteria = []

    def add(name: str, passed: bool, details: Mapping[str, object]) -> None:
        criteria.append({"name": name, "passed": bool(passed), "details": dict(details)})

    add(
        "complete_matrix",
        observed_keys == expected_keys
        and len(rows) == 40
        and all(row["completed"] is True for row in rows)
        and len(evaluations) == 400
        and len(acquisitions) == 240,
        {
            "expected_runs": 40,
            "observed_runs": len(rows),
            "complete_runs": sum(row["completed"] is True for row in rows),
            "evaluations": len(evaluations),
            "acquisitions": len(acquisitions),
            "missing_runs": len(expected_keys - observed_keys),
        },
    )
    audit = _audit_records(records, expected_keys)
    add("raw_record_audit", audit["passed"], audit)
    add(
        "system_scope",
        len(rows) == 40 and all(row["system_scope"] is True for row in rows),
        {"system_scope_runs": sum(row["system_scope"] is True for row in rows)},
    )
    add(
        "deterministic_replay",
        len(rows) == 40 and all(row["replay_consistent"] is True for row in rows),
        {"consistent_runs": sum(row["replay_consistent"] is True for row in rows)},
    )
    calibration_result = calibration_metrics(calibration)
    coverage = calibration_result["coverage_90"]
    brier = calibration_result["constraint_brier"]
    add(
        "heldout_calibration",
        calibration_result["observed_records"] == calibration_result["expected_records"]
        and calibration_result["unique_records"] == calibration_result["expected_records"]
        and calibration_result["issue_count"] == 0
        and calibration_result["finite_moments"] is True
        and coverage is not None
        and 0.75 <= coverage <= 1.0
        and brier is not None
        and brier <= 0.20,
        calibration_result,
    )
    full_rows = [row for row in rows if row["method"] == "function_network_full"]
    system_rows = [row for row in rows if row["method"] == "system"]
    full_final = _median(full_rows, "final_regret")
    system_final = _median(system_rows, "final_regret")
    final_delta = None if full_final is None or system_final is None else full_final - system_final
    add(
        "pooled_final_regret_match",
        len(full_rows) == len(system_rows) == 20
        and final_delta is not None
        and final_delta <= 0.05,
        {
            "full_median": full_final,
            "system_median": system_final,
            "full_minus_system": final_delta,
            "maximum": 0.05,
        },
    )
    problem_details = {}
    problem_passes = []
    for problem in benchmark_problems():
        full = _median([row for row in full_rows if row["problem"] == problem.name], "final_regret")
        system = _median(
            [row for row in system_rows if row["problem"] == problem.name], "final_regret"
        )
        delta = None if full is None or system is None else full - system
        passed = delta is not None and delta <= 0.10
        problem_passes.append(passed)
        problem_details[problem.name] = {
            "full_median": full,
            "system_median": system,
            "full_minus_system": delta,
            "maximum": 0.10,
        }
    add("problem_final_regret_match", all(problem_passes), problem_details)
    full_area = _median(full_rows, "regret_area")
    system_area = _median(system_rows, "regret_area")
    area_delta = None if full_area is None or system_area is None else full_area - system_area
    add(
        "pooled_regret_area_match",
        len(full_rows) == len(system_rows) == 20 and area_delta is not None and area_delta <= 0.05,
        {
            "full_median": full_area,
            "system_median": system_area,
            "full_minus_system": area_delta,
            "maximum": 0.05,
        },
    )
    full_acquisitions = [item for item in acquisitions if item["method"] == "function_network_full"]
    fallback_count = sum(
        bool(item["diagnostics"]["fallback_reasons"]) for item in full_acquisitions
    )
    overall_rate = 1.0 if not full_acquisitions else fallback_count / len(full_acquisitions)
    rates = {}
    for problem in benchmark_problems():
        selected = [item for item in full_acquisitions if item["problem"] == problem.name]
        rates[problem.name] = (
            1.0
            if not selected
            else sum(bool(item["diagnostics"]["fallback_reasons"]) for item in selected)
            / len(selected)
        )
    add(
        "bounded_full_network_fallbacks",
        len(full_acquisitions) == 120
        and overall_rate <= 0.05
        and all(rate <= 0.15 for rate in rates.values()),
        {
            "modeled_suggestions": len(full_acquisitions),
            "unresolved_suggestions": fallback_count,
            "overall_rate": overall_rate,
            "overall_maximum": 0.05,
            "problem_rates": rates,
            "problem_maximum": 0.15,
        },
    )
    return {
        "schema_version": "1.0",
        "passed": all(item["passed"] for item in criteria),
        "criteria": criteria,
        "provenance": dict(provenance),
    }


def _median(rows: list[Mapping[str, object]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row[field] != ""]
    return None if not values else float(np.median(values))


def _audit_records(
    records: list[Mapping[str, object]], expected_keys: set[tuple[str, str, int]]
) -> dict[str, object]:
    issues = []
    evaluations = defaultdict(list)
    acquisitions = defaultdict(list)
    for record in records:
        key = (str(record["problem"]), str(record["method"]), int(record["seed"]))
        if key not in expected_keys:
            issues.append(f"unexpected run: {key!r}")
        if record["record_type"] == "evaluation":
            evaluations[key].append(record)
        elif record["record_type"] == "acquisition":
            acquisitions[key].append(record)
        elif record["record_type"] == "run_error":
            issues.append(f"run error {key!r}: {record['error_type']}: {record['error']}")
    warm_configs = {}
    for key in expected_keys:
        problem_name, method, seed = key
        problem = problem_by_name(problem_name)
        group = sorted(evaluations[key], key=lambda item: int(item["evaluation_index"]))
        decisions = {int(item["evaluation_index"]): item for item in acquisitions[key]}
        if [int(item["evaluation_index"]) for item in group] != list(range(EVALUATIONS_PER_RUN)):
            issues.append(f"evaluation indices differ for {key!r}")
            continue
        if sorted(decisions) != list(range(WARM_START_COUNT, EVALUATIONS_PER_RUN)):
            issues.append(f"acquisition indices differ for {key!r}")
        best = None
        for index, record in enumerate(group):
            label = f"{problem_name}/{method}/{seed}/{index}"
            try:
                action = EvaluationAction.from_dict(record["action"])
                result = EvaluationResult.from_dict(record["result"])
                problem.space.encode(action.config)
            except (TypeError, ValueError, KeyError) as error:
                issues.append(f"invalid action or result at {label}: {error}")
                continue
            if action.scope is not EvaluationScope.SYSTEM or action.id != f"eval-{index:06d}":
                issues.append(f"action identity or scope differs at {label}")
            truth = problem.analytic(action.config)
            if set(result.outcomes) != set(truth) or any(
                not math.isclose(result.outcomes[name], value, rel_tol=0.0, abs_tol=1e-12)
                for name, value in truth.items()
            ):
                issues.append(f"scientific outcome differs at {label}")
            feasible = problem.feasible(truth)
            if feasible:
                objective = truth[problem.network.objective.outcome]
                best = objective if best is None else max(best, objective)
            expected = {
                "cumulative_cost": float(index + 1),
                "feasible": feasible,
                "best_feasible_objective": best,
                "normalized_regret": problem.normalized_regret(best),
                "invalid_configuration": False,
                "budget_overrun": False,
                "artifact_error": False,
                "replay_consistent": True,
            }
            for name, value in expected.items():
                observed = record[name]
                if isinstance(value, float):
                    matched = (
                        isinstance(observed, (int, float))
                        and not isinstance(observed, bool)
                        and math.isclose(float(observed), value, rel_tol=0.0, abs_tol=1e-12)
                    )
                else:
                    matched = observed == value
                if not matched:
                    issues.append(f"{name} differs at {label}")
            if index >= WARM_START_COUNT:
                decision = decisions.get(index)
                if decision is None or decision["action"] != record["action"]:
                    issues.append(f"acquisition action differs at {label}")
        warm_configs[(problem_name, seed, method)] = tuple(
            canonical_json(item["action"]["config"]) for item in group[:WARM_START_COUNT]
        )
    for problem in benchmark_problems():
        for seed in BENCHMARK_SEEDS:
            if warm_configs.get((problem.name, seed, METHODS[0])) != warm_configs.get(
                (problem.name, seed, METHODS[1])
            ):
                issues.append(f"shared warm starts differ for {problem.name}/{seed}")
    return {
        "passed": not issues,
        "issue_count": len(issues),
        "reported_issues": issues[:100],
    }


def render_report(rows: list[Mapping[str, object]], gate: Mapping[str, object]) -> str:
    """Render the comparison, including adverse or null outcomes."""
    lines = [
        "# Full-observability function-network benchmark",
        "",
        f"Gate result: {'PASS' if gate['passed'] else 'FAIL'}",
        "",
        "The frozen criteria test whether the network method matches the whole-system method. "
        "The evidence is retained whether the comparison is favorable, null, or adverse.",
        "",
        "## Results",
        "",
        "| Problem | Method | Runs | Median final regret | Median regret area | Fallbacks |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for problem in benchmark_problems():
        for method in METHODS:
            selected = [
                row for row in rows if row["problem"] == problem.name and row["method"] == method
            ]
            final = _median(selected, "final_regret")
            area = _median(selected, "regret_area")
            fallback = sum(int(row["unresolved_fallback_suggestions"]) for row in selected)
            lines.append(
                f"| {problem.name} | {method} | {len(selected)} | "
                f"{_format(final)} | {_format(area)} | {fallback} |"
            )
    lines.extend(
        [
            "",
            "## Frozen criteria",
            "",
            "| Criterion | Result | Details |",
            "| --- | --- | --- |",
        ]
    )
    for criterion in gate["criteria"]:
        result = "PASS" if criterion["passed"] else "FAIL"
        details = canonical_json(criterion["details"]).replace("|", "\\|")
        lines.append(f"| {criterion['name']} | {result} | `{details}` |")
    failures = [row for row in rows if row["completed"] is not True]
    lines.extend(["", "## Run failures", "", f"Incomplete runs: {len(failures)}"])
    for row in failures:
        lines.append(
            f"- `{row['problem']}/{row['method']}/{row['seed']}`: "
            f"{row['error'] or 'incomplete record count'}"
        )
    return "\n".join(lines) + "\n"


def _format(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.6f}"


def gate_json(gate: Mapping[str, object]) -> str:
    return json.dumps(gate, indent=2, sort_keys=True, allow_nan=False) + "\n"
