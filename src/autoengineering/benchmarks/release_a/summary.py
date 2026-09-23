"""Raw-to-summary reconstruction and frozen Release A gate evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import csv
import io
from itertools import product
import json
import math
from statistics import fmean

import numpy as np

from autoengineering.optimization import EvaluationAction, EvaluationResult

from .methods import METHOD_NAMES, NATIVE_METHODS, WARM_START_COUNT
from .problems import BENCHMARK_SEEDS, EVALUATIONS_PER_RUN, benchmark_problems, problem_by_name
from .runner import canonical_json

SUMMARY_FIELDS = (
    "problem",
    "method",
    "seed",
    "completed",
    "evaluation_count",
    "final_regret",
    "regret_area",
    "cost_to_first_feasible",
    "total_cost",
    "constraint_violations",
    "successes",
    "scientific_infeasible",
    "model_failures",
    "timeouts",
    "infrastructure_failures",
    "optimizer_overhead_seconds",
    "fallback_events",
    "unresolved_fallback_suggestions",
    "invalid_configurations",
    "budget_overruns",
    "replay_consistent",
    "error",
)


def summarize_records(records: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    """Build one summary row per observed problem-method-seed combination."""
    evaluations: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    errors: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        key = (str(record["problem"]), str(record["method"]), int(record["seed"]))
        if record["record_type"] == "evaluation":
            evaluations[key].append(record)
        else:
            errors[key].append(record)
    problem_order = {problem.name: problem.ordinal for problem in benchmark_problems()}
    method_order = {method: index for index, method in enumerate(METHOD_NAMES)}
    keys = sorted(
        set(evaluations) | set(errors),
        key=lambda key: (problem_order[key[0]], method_order[key[1]], key[2]),
    )
    rows = []
    for problem_name, method, seed in keys:
        group = sorted(
            evaluations[(problem_name, method, seed)],
            key=lambda record: int(record["evaluation_index"]),
        )
        problem = problem_by_name(problem_name)
        statuses = defaultdict(int)
        for record in group:
            statuses[str(record["result"]["status"])] += 1
        replay_values = [record["replay_consistent"] for record in group]
        replay = ""
        if method in NATIVE_METHODS:
            replay = bool(group) and all(value is True for value in replay_values)
        first_feasible = next(
            (float(record["cumulative_cost"]) for record in group if record["feasible"]),
            "",
        )
        run_errors = errors[(problem_name, method, seed)]
        rows.append(
            {
                "problem": problem_name,
                "method": method,
                "seed": seed,
                "completed": len(group) == EVALUATIONS_PER_RUN and not run_errors,
                "evaluation_count": len(group),
                "final_regret": "" if not group else float(group[-1]["normalized_regret"]),
                "regret_area": _regret_area(group, problem.cost_budget),
                "cost_to_first_feasible": first_feasible,
                "total_cost": 0.0 if not group else float(group[-1]["cumulative_cost"]),
                "constraint_violations": sum(
                    bool(record["constraint_violation"]) for record in group
                ),
                "successes": statuses["success"],
                "scientific_infeasible": statuses["scientific_infeasible"],
                "model_failures": statuses["model_failure"],
                "timeouts": statuses["timeout"],
                "infrastructure_failures": statuses["infrastructure_failure"],
                "optimizer_overhead_seconds": sum(
                    float(record["optimizer_overhead_seconds"]) for record in group
                ),
                "fallback_events": sum(len(record["fallback_events"]) for record in group),
                "unresolved_fallback_suggestions": sum(
                    bool(record["unresolved_fallback_events"]) for record in group
                ),
                "invalid_configurations": sum(
                    bool(record["invalid_configuration"]) for record in group
                )
                + sum(bool(record["invalid_configuration"]) for record in run_errors),
                "budget_overruns": sum(bool(record["budget_overrun"]) for record in group)
                + sum(bool(record["budget_overrun"]) for record in run_errors),
                "replay_consistent": replay,
                "error": " | ".join(
                    f"{record['stage']} {record['error_type']}: {record['error']}"
                    for record in run_errors
                ),
            }
        )
    return rows


def _regret_area(records: list[dict[str, object]], budget: float) -> float | str:
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
    area += max(0.0, budget - previous_cost) * previous_regret
    return area / budget


def summary_csv(rows: Iterable[Mapping[str, object]]) -> str:
    """Serialize summary rows with stable columns and line endings."""
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return stream.getvalue()


def evaluate_gate(
    records: Iterable[dict[str, object]],
    *,
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Evaluate every preregistered criterion without changing its threshold."""
    records = list(records)
    rows = summarize_records(records)
    evaluations = [record for record in records if record["record_type"] == "evaluation"]
    expected_keys = set(
        product(
            (problem.name for problem in benchmark_problems()),
            METHOD_NAMES,
            BENCHMARK_SEEDS,
        )
    )
    expected_runs = len(expected_keys)
    complete_rows = [row for row in rows if row["completed"] is True]
    observed_keys = {(row["problem"], row["method"], row["seed"]) for row in rows}
    indices_by_run: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    for record in evaluations:
        indices_by_run[(record["problem"], record["method"], record["seed"])].append(
            int(record["evaluation_index"])
        )
    exact_indices = all(
        sorted(indices_by_run[key]) == list(range(EVALUATIONS_PER_RUN)) for key in expected_keys
    )
    criteria = []

    def add(name: str, passed: bool, details: Mapping[str, object]) -> None:
        criteria.append({"name": name, "passed": bool(passed), "details": dict(details)})

    add(
        "complete_matrix",
        observed_keys == expected_keys
        and len(complete_rows) == expected_runs
        and len(evaluations) == expected_runs * EVALUATIONS_PER_RUN
        and exact_indices,
        {
            "expected_runs": expected_runs,
            "observed_runs": len(rows),
            "missing_runs": len(expected_keys - observed_keys),
            "unexpected_runs": len(observed_keys - expected_keys),
            "complete_runs": len(complete_rows),
            "expected_evaluations": expected_runs * EVALUATIONS_PER_RUN,
            "observed_evaluations": len(evaluations),
            "exact_evaluation_indices": exact_indices,
        },
    )
    audit = _audit_records(records, expected_keys)
    add("scientific_record_audit", audit["passed"], audit)
    invalid = sum(int(row["invalid_configurations"]) for row in rows)
    overruns = sum(int(row["budget_overruns"]) for row in rows)
    add(
        "valid_and_within_budget",
        invalid == 0 and overruns == 0,
        {"invalid_configurations": invalid, "budget_overruns": overruns},
    )
    native = [row for row in rows if row["method"] in NATIVE_METHODS]
    add(
        "native_replay",
        len(native) == 600 and all(row["replay_consistent"] is True for row in native),
        {
            "expected_native_runs": 600,
            "observed_native_runs": len(native),
            "consistent_native_runs": sum(row["replay_consistent"] is True for row in native),
        },
    )
    smac = [row for row in rows if row["method"] == "smac"]
    add(
        "smac_completion",
        len(smac) == 150 and all(row["completed"] is True for row in smac),
        {
            "expected_smac_runs": 150,
            "observed_smac_runs": len(smac),
            "complete_smac_runs": sum(row["completed"] is True for row in smac),
        },
    )
    modeled = [
        record
        for record in evaluations
        if record["method"] == "botorch" and int(record["evaluation_index"]) >= WARM_START_COUNT
    ]
    unresolved = sum(bool(record["unresolved_fallback_events"]) for record in modeled)
    bayes_rows = [row for row in rows if row["method"] == "botorch"]
    max_run_unresolved = max(
        (int(row["unresolved_fallback_suggestions"]) for row in bayes_rows),
        default=0,
    )
    fallback_rate = 1.0 if not modeled else unresolved / len(modeled)
    add(
        "bounded_botorch_fallbacks",
        len(modeled) == 750 and fallback_rate <= 0.10 and max_run_unresolved <= 3,
        {
            "modeled_suggestions": len(modeled),
            "unresolved_suggestions": unresolved,
            "unresolved_rate": fallback_rate,
            "maximum_in_one_run": max_run_unresolved,
        },
    )
    comparisons = _numeric_comparisons(rows)
    add(
        "botorch_vs_random_pooled",
        comparisons["complete"]
        and comparisons["botorch_final"] <= 0.90 * comparisons["random_final"] + 0.02
        and comparisons["botorch_area"] <= 0.90 * comparisons["random_area"] + 0.02,
        comparisons,
    )
    add(
        "botorch_vs_sobol_pooled",
        comparisons["complete"]
        and comparisons["botorch_final"] <= 1.10 * comparisons["sobol_final"] + 0.01
        and comparisons["botorch_area"] <= 1.10 * comparisons["sobol_area"] + 0.01,
        comparisons,
    )
    per_problem = comparisons["per_problem"]
    per_problem_pass = comparisons["complete"] and all(
        values["botorch_final"] <= values["random_final"] + 0.10
        and values["botorch_final"] <= values["sobol_final"] + 0.12
        for values in per_problem.values()
    )
    wins = (
        sum(values["botorch_final"] <= values["random_final"] for values in per_problem.values())
        if comparisons["complete"]
        else 0
    )
    add(
        "botorch_problem_limits",
        per_problem_pass and wins >= 3,
        {"random_wins_or_ties": wins, "per_problem": per_problem},
    )
    return {
        "schema_version": "1.0",
        "passed": all(criterion["passed"] for criterion in criteria),
        "criteria": criteria,
        "provenance": dict(provenance),
    }


def _audit_records(
    records: list[dict[str, object]],
    expected_keys: set[tuple[str, str, int]],
) -> dict[str, object]:
    """Recompute scientific fields for every exact benchmark run."""
    issues: list[str] = []
    issue_count = 0

    def report(message: str) -> None:
        nonlocal issue_count
        issue_count += 1
        if len(issues) < 100:
            issues.append(message)

    groups: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        key = (record["problem"], record["method"], record["seed"])
        if key not in expected_keys:
            report(f"unexpected run {key!r}")
            continue
        if record["record_type"] == "run_error":
            report(
                f"run error {key!r} at {record['stage']}: {record['error_type']}: {record['error']}"
            )
            continue
        groups[key].append(record)

    for key in sorted(expected_keys):
        group = groups[key]
        indices = [int(record["evaluation_index"]) for record in group]
        if sorted(indices) != list(range(EVALUATIONS_PER_RUN)):
            report(f"evaluation indices differ for {key!r}: {indices!r}")
            continue
        problem_name, method, seed = key
        problem = problem_by_name(problem_name)
        cumulative_cost = 0.0
        best_feasible: float | None = None
        for record in sorted(group, key=lambda item: int(item["evaluation_index"])):
            index = int(record["evaluation_index"])
            label = f"{problem_name}/{method}/{seed}/{index}"
            try:
                action = EvaluationAction.from_dict(record["action"])
                result = EvaluationResult.from_dict(record["result"])
                problem.space.encode(action.config)
            except (KeyError, TypeError, ValueError) as error:
                report(f"invalid action or result at {label}: {error}")
                continue
            expected_result = problem.evaluate(
                action,
                benchmark_seed=seed,
                evaluation_index=index,
            )
            if not _scientific_values_equal(result.to_dict(), expected_result.to_dict()):
                report(f"scientific result differs at {label}")
            preview_cost = problem.preview_cost(dict(action.config))
            if not math.isclose(result.cost, preview_cost, rel_tol=0.0, abs_tol=1e-12):
                report(f"evaluator cost differs at {label}")
            cumulative_cost += result.cost
            feasible = problem.is_feasible(result)
            if feasible:
                objective = result.outcomes[problem.objective.outcome]
                best_feasible = (
                    objective if best_feasible is None else max(best_feasible, objective)
                )
            expected_fields = {
                "study_seed": problem.study(seed).seed,
                "cumulative_cost": cumulative_cost,
                "cost_budget": problem.cost_budget,
                "feasible": feasible,
                "constraint_violation": problem.constraint_violation(result),
                "best_feasible_objective": best_feasible,
                "normalized_regret": problem.normalized_regret(best_feasible),
                "invalid_configuration": False,
                "budget_overrun": False,
                "replay_consistent": True if method in NATIVE_METHODS else None,
            }
            for field, expected in expected_fields.items():
                observed = record[field]
                if isinstance(expected, float):
                    matches = (
                        not isinstance(observed, bool)
                        and isinstance(observed, (int, float))
                        and math.isclose(float(observed), expected, rel_tol=0.0, abs_tol=1e-12)
                    )
                else:
                    matches = observed == expected
                if not matches:
                    report(f"{field} differs at {label}")
            fallback_events = record["fallback_events"]
            unresolved = [
                event
                for event in fallback_events
                if index >= WARM_START_COUNT
                or not event.startswith("cold_start_insufficient_usable_observations")
            ]
            if record["unresolved_fallback_events"] != unresolved:
                report(f"unresolved fallback classification differs at {label}")
            overhead = record["optimizer_overhead_seconds"]
            if (
                isinstance(overhead, bool)
                or not isinstance(overhead, (int, float))
                or not math.isfinite(float(overhead))
                or overhead < 0
            ):
                report(f"optimizer overhead differs at {label}")
        if cumulative_cost > problem.cost_budget + 1e-12:
            report(f"cumulative budget overrun for {key!r}")
    return {
        "passed": issue_count == 0,
        "issue_count": issue_count,
        "reported_issues": issues,
    }


def _scientific_values_equal(observed: object, expected: object) -> bool:
    """Compare reconstructed result values across supported floating-point platforms."""
    if isinstance(expected, float):
        return (
            not isinstance(observed, bool)
            and isinstance(observed, (int, float))
            and math.isclose(float(observed), expected, rel_tol=0.0, abs_tol=1e-12)
        )
    if isinstance(expected, Mapping):
        return (
            isinstance(observed, Mapping)
            and set(observed) == set(expected)
            and all(_scientific_values_equal(observed[key], value) for key, value in expected.items())
        )
    if isinstance(expected, (list, tuple)):
        return (
            isinstance(observed, (list, tuple))
            and len(observed) == len(expected)
            and all(
                _scientific_values_equal(observed_value, expected_value)
                for observed_value, expected_value in zip(observed, expected, strict=True)
            )
        )
    return observed == expected


def _numeric_comparisons(rows: list[dict[str, object]]) -> dict[str, object]:
    selected = {
        method: [row for row in rows if row["method"] == method and row["completed"] is True]
        for method in ("random", "sobol", "botorch")
    }
    complete = all(len(method_rows) == 150 for method_rows in selected.values())

    def mean(method: str, field: str) -> float | None:
        values = [float(row[field]) for row in selected[method] if row[field] != ""]
        return None if not values else fmean(values)

    per_problem = {}
    for problem in benchmark_problems():
        per_problem[problem.name] = {
            f"{method}_final": mean_rows(
                [row for row in selected[method] if row["problem"] == problem.name],
                "final_regret",
            )
            for method in ("random", "sobol", "botorch")
        }
    return {
        "complete": complete,
        "random_final": mean("random", "final_regret"),
        "random_area": mean("random", "regret_area"),
        "sobol_final": mean("sobol", "final_regret"),
        "sobol_area": mean("sobol", "regret_area"),
        "botorch_final": mean("botorch", "final_regret"),
        "botorch_area": mean("botorch", "regret_area"),
        "per_problem": per_problem,
    }


def mean_rows(rows: list[dict[str, object]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row[field] != ""]
    return None if not values else fmean(values)


def render_report(rows: list[dict[str, object]], gate: Mapping[str, object]) -> str:
    """Render aggregate distributions and every gate decision as Markdown."""
    lines = [
        "# Release A benchmark report",
        "",
        f"Gate result: {'PASS' if gate['passed'] else 'FAIL'}",
        "",
        "## Aggregate results",
        "",
        "| Problem | Method | Runs | Mean final regret | Median | P10 | P90 | Mean regret area |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for problem in benchmark_problems():
        for method in METHOD_NAMES:
            selected = [
                row
                for row in rows
                if row["problem"] == problem.name
                and row["method"] == method
                and row["final_regret"] != ""
            ]
            values = [float(row["final_regret"]) for row in selected]
            areas = [float(row["regret_area"]) for row in selected]
            if values:
                statistics = (
                    fmean(values),
                    float(np.median(values)),
                    float(np.quantile(values, 0.1)),
                    float(np.quantile(values, 0.9)),
                    fmean(areas),
                )
                formatted = " | ".join(f"{value:.6f}" for value in statistics)
            else:
                formatted = "n/a | n/a | n/a | n/a | n/a"
            lines.append(f"| {problem.name} | {method} | {len(values)} | {formatted} |")
    lines.extend(
        [
            "",
            "## Release criteria",
            "",
            "| Criterion | Result | Details |",
            "| --- | --- | --- |",
        ]
    )
    for criterion in gate["criteria"]:
        result = "PASS" if criterion["passed"] else "FAIL"
        details = canonical_json(criterion["details"]).replace("|", "\\|")
        lines.append(f"| {criterion['name']} | {result} | `{details}` |")
    failed = [row for row in rows if row["completed"] is not True]
    lines.extend(
        [
            "",
            "## Run failures",
            "",
            f"Incomplete runs: {len(failed)}",
        ]
    )
    for row in failed:
        lines.append(
            f"- `{row['problem']}/{row['method']}/{row['seed']}`: "
            f"{row['error'] or 'incomplete evaluation count'}"
        )
    return "\n".join(lines) + "\n"


def gate_json(gate: Mapping[str, object]) -> str:
    """Serialize the machine gate with readable stable formatting."""
    return json.dumps(gate, indent=2, sort_keys=True, allow_nan=False) + "\n"
