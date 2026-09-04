"""Raw-to-summary reconstruction and frozen Release A gate evaluation."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
import csv
import io
import json
from statistics import fmean

import numpy as np

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
    expected_runs = len(benchmark_problems()) * len(METHOD_NAMES) * len(BENCHMARK_SEEDS)
    complete_rows = [row for row in rows if row["completed"] is True]
    criteria = []

    def add(name: str, passed: bool, details: Mapping[str, object]) -> None:
        criteria.append({"name": name, "passed": bool(passed), "details": dict(details)})

    add(
        "complete_matrix",
        len(rows) == expected_runs
        and len(complete_rows) == expected_runs
        and len(evaluations) == expected_runs * EVALUATIONS_PER_RUN,
        {
            "expected_runs": expected_runs,
            "observed_runs": len(rows),
            "complete_runs": len(complete_rows),
            "expected_evaluations": expected_runs * EVALUATIONS_PER_RUN,
            "observed_evaluations": len(evaluations),
        },
    )
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
            "",
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
