"""Reconstruct Item 9 evidence and evaluate its frozen criteria."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
import csv
import io
from itertools import product
import json
import math

import numpy as np

from autoengineering.optimization import EvaluationAction, EvaluationResult, EvaluationScope

from .problems import benchmark_problems, problem_by_name
from .runner import BENCHMARK_SEEDS, BUDGET, MAX_ACTIONS, METHODS, WARM_START_COUNT

SUMMARY_FIELDS = (
    "problem",
    "method",
    "seed",
    "completed",
    "stop_reason",
    "evaluation_count",
    "system_count",
    "component_count",
    "post_warm_system_count",
    "final_regret",
    "regret_area",
    "total_cost",
    "replay_consistent",
    "cost_conservative",
    "unresolved_fallbacks",
    "recommendation_action_id",
    "recommendation_is_observed_system",
    "optimizer_overhead_seconds",
    "error",
)

COMPONENT_FIELDS = ("problem", "method", "component", "selection_count")


def summarize_records(records: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    evaluations, acquisitions, endings, errors = _group_records(records)
    expected = product((item.name for item in benchmark_problems()), METHODS, BENCHMARK_SEEDS)
    rows = []
    for key in expected:
        group = sorted(evaluations[key], key=lambda item: int(item["evaluation_index"]))
        decisions = acquisitions[key]
        run_ends = endings[key]
        run_errors = errors[key]
        end = run_ends[0] if len(run_ends) == 1 else None
        system_ids = {
            item["action"]["id"]
            for item in group
            if item["action"]["scope"] == EvaluationScope.SYSTEM.value
        }
        recommendation_id = (
            None if end is None else end["recommendation"]["action_id"]
        )
        rows.append(
            {
                "problem": key[0],
                "method": key[1],
                "seed": key[2],
                "completed": end is not None and not run_errors,
                "stop_reason": "" if end is None else end["stop_reason"],
                "evaluation_count": len(group),
                "system_count": sum(
                    item["action"]["scope"] == EvaluationScope.SYSTEM.value
                    for item in group
                ),
                "component_count": sum(
                    item["action"]["scope"] == EvaluationScope.COMPONENT.value
                    for item in group
                ),
                "post_warm_system_count": sum(
                    int(item["evaluation_index"]) >= WARM_START_COUNT
                    and item["action"]["scope"] == EvaluationScope.SYSTEM.value
                    for item in group
                ),
                "final_regret": "" if not group else float(group[-1]["normalized_regret"]),
                "regret_area": _regret_area(group),
                "total_cost": 0.0 if not group else float(group[-1]["cumulative_cost"]),
                "replay_consistent": bool(group)
                and all(item["replay_consistent"] is True for item in (*group, *decisions)),
                "cost_conservative": all(
                    float(item["estimated_cost"]) + 1e-12
                    >= float(item["result"]["cost"])
                    for item in group
                ),
                "unresolved_fallbacks": sum(_unresolved_fallback(item) for item in decisions),
                "recommendation_action_id": recommendation_id or "",
                "recommendation_is_observed_system": recommendation_id in system_ids,
                "optimizer_overhead_seconds": sum(
                    float(item["optimizer_overhead_seconds"]) for item in group
                ),
                "error": " | ".join(
                    f"{item['error_type']}: {item['error']}" for item in run_errors
                ),
            }
        )
    return rows


def _group_records(records):
    groups = tuple(defaultdict(list) for _ in range(4))
    names = {"evaluation": 0, "acquisition": 1, "run_end": 2, "run_error": 3}
    for record in records:
        record_type = str(record.get("record_type"))
        if record_type not in names:
            raise ValueError(f"unknown raw record type: {record_type!r}")
        key = (str(record["problem"]), str(record["method"]), int(record["seed"]))
        groups[names[record_type]][key].append(record)
    return groups


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
    area += max(0.0, BUDGET - previous_cost) * previous_regret
    return area / BUDGET


def _unresolved_fallback(record: Mapping[str, object]) -> bool:
    diagnostics = record["diagnostics"]
    if diagnostics["fit_state"] == "fallback":
        return True
    return any(
        str(reason).startswith(("component_fit_failure", "value_scoring_failure"))
        for reason in diagnostics["fallback_reasons"]
    )


def summary_csv(rows: Iterable[Mapping[str, object]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def component_summary(records: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    counts = Counter()
    for record in records:
        if record["record_type"] != "evaluation":
            continue
        action = record["action"]
        if (
            int(record["evaluation_index"]) >= WARM_START_COUNT
            and action["scope"] == EvaluationScope.COMPONENT.value
        ):
            counts[(record["problem"], record["method"], action["component"])] += 1
    rows = []
    for problem in benchmark_problems():
        for method in METHODS:
            for component in problem.network.components:
                if EvaluationScope.COMPONENT not in component.evaluation_scopes:
                    continue
                rows.append(
                    {
                        "problem": problem.name,
                        "method": method,
                        "component": component.component,
                        "selection_count": counts[
                            (problem.name, method, component.component)
                        ],
                    }
                )
    return rows


def component_csv(rows: Iterable[Mapping[str, object]]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=COMPONENT_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def value_cost_payload(records: Iterable[Mapping[str, object]]) -> dict[str, object]:
    decisions = []
    for record in records:
        if record["record_type"] != "acquisition":
            continue
        diagnostics = record["diagnostics"]
        decisions.append(
            {
                "problem": record["problem"],
                "method": record["method"],
                "seed": record["seed"],
                "evaluation_index": record["evaluation_index"],
                "selected_action": record["action"],
                "estimated_cost": record["estimated_cost"],
                "fit_state": diagnostics["fit_state"],
                "fallback_reasons": diagnostics["fallback_reasons"],
                "candidate_scores": diagnostics["details"].get("candidate_scores", ()),
                "maximum_value_per_cost_bound": diagnostics["details"].get(
                    "maximum_value_per_cost_bound"
                ),
            }
        )
    return {"schema_version": "1.0", "decisions": decisions}


def evaluate_gate(
    records: Iterable[Mapping[str, object]], *, provenance: Mapping[str, object]
) -> dict[str, object]:
    records = list(records)
    rows = summarize_records(records)
    components = component_summary(records)
    criteria = []

    def add(name: str, passed: bool, details: Mapping[str, object]) -> None:
        criteria.append({"name": name, "passed": bool(passed), "details": dict(details)})

    errors = [item for item in records if item["record_type"] == "run_error"]
    accepted_stops = {
        "max_cost",
        "max_evaluations",
        "marginal_value_below_cost",
        "insufficient_remaining_budget",
    }
    add(
        "complete_matrix",
        len(rows) == 40
        and not errors
        and all(row["completed"] and row["stop_reason"] in accepted_stops for row in rows)
        and all(int(row["evaluation_count"]) <= MAX_ACTIONS for row in rows)
        and all(float(row["total_cost"]) <= BUDGET + 1e-12 for row in rows),
        {
            "expected_runs": 40,
            "observed_runs": len(rows),
            "complete_runs": sum(bool(row["completed"]) for row in rows),
            "run_errors": len(errors),
            "maximum_cost": max((float(row["total_cost"]) for row in rows), default=None),
        },
    )
    audit = _audit_records(records)
    add("raw_reconstruction", audit["passed"], audit)
    add(
        "deterministic_action_and_result_replay",
        all(row["replay_consistent"] for row in rows),
        {"consistent_runs": sum(bool(row["replay_consistent"]) for row in rows)},
    )
    lineage = _lineage_audit(records)
    add("verified_system_parent_lineage", lineage["passed"], lineage)
    add(
        "system_refresh_and_observed_recommendation",
        all(
            int(row["post_warm_system_count"]) >= 1
            and bool(row["recommendation_is_observed_system"])
            for row in rows
        ),
        {
            "runs_with_refresh": sum(int(row["post_warm_system_count"]) >= 1 for row in rows),
            "observed_system_recommendations": sum(
                bool(row["recommendation_is_observed_system"]) for row in rows
            ),
        },
    )
    component_lookup = {
        (row["problem"], row["method"], row["component"]): row["selection_count"]
        for row in components
    }
    left = component_lookup[("informative_branch", "function_network_partial", "left")]
    right = component_lookup[("informative_branch", "function_network_partial", "right")]
    add(
        "controlled_informative_component",
        left > right,
        {"left_selections": left, "right_selections": right},
    )
    performance = _performance(rows)
    pooled_final = performance["pooled_final_difference"]
    problem_final = performance["problem_final_differences"]
    add(
        "final_regret_tolerance",
        pooled_final is not None
        and pooled_final <= 0.15
        and all(value is not None and value <= 0.25 for value in problem_final.values()),
        {
            "pooled_difference_limit": 0.15,
            "problem_difference_limit": 0.25,
            **performance,
        },
    )
    add(
        "regret_area_tolerance",
        performance["pooled_area_difference"] is not None
        and performance["pooled_area_difference"] <= 0.15,
        {
            "difference_limit": 0.15,
            "pooled_area_difference": performance["pooled_area_difference"],
        },
    )
    random_differences = performance["random_area_differences"]
    observed_random_differences = [
        value for value in random_differences.values() if value is not None
    ]
    add(
        "random_component_control",
        len(observed_random_differences) == len(random_differences)
        and min(observed_random_differences) <= -0.005
        and max(observed_random_differences) <= 0.10,
        {
            "required_improvement": -0.005,
            "maximum_other_problem_difference": 0.10,
            "voi_minus_random_by_problem": random_differences,
        },
    )
    add(
        "conservative_component_costs",
        all(row["cost_conservative"] for row in rows),
        {"conservative_runs": sum(bool(row["cost_conservative"]) for row in rows)},
    )
    fallback = _fallback_metrics(records)
    add(
        "bounded_fit_and_scoring_fallbacks",
        fallback["pooled_rate"] <= 0.10
        and all(value <= 0.20 for value in fallback["problem_rates"].values()),
        {"pooled_limit": 0.10, "problem_limit": 0.20, **fallback},
    )
    terminal = _terminal_separation(records)
    add("terminal_observation_separation", terminal["passed"], terminal)
    return {
        "schema_version": "1.0",
        "passed": all(item["passed"] for item in criteria),
        "criteria": criteria,
        "provenance": dict(provenance),
    }


def _audit_records(records):
    evaluations, acquisitions, endings, errors = _group_records(records)
    issues = []
    expected_keys = set(
        product((item.name for item in benchmark_problems()), METHODS, BENCHMARK_SEEDS)
    )
    if set(evaluations) | set(acquisitions) | set(endings) | set(errors) != expected_keys:
        issues.append("raw run keys differ from the preregistered matrix")
    for key in expected_keys:
        problem = problem_by_name(key[0])
        group = sorted(evaluations[key], key=lambda item: int(item["evaluation_index"]))
        cumulative = 0.0
        system_actions = {}
        artifact_producers = {}
        best = None
        for index, record in enumerate(group):
            try:
                action = EvaluationAction.from_dict(record["action"])
                result = EvaluationResult.from_dict(record["result"])
            except (TypeError, ValueError) as error:
                issues.append(f"invalid action or result at {key!r} index {index}: {error}")
                continue
            if action.id != f"eval-{index:06d}" or result.action_id != action.id:
                issues.append(f"nonsequential action at {key!r} index {index}")
            expected_cost = problem.expected_cost(action.component)
            cumulative = math.fsum((cumulative, result.cost))
            if not math.isclose(result.cost, expected_cost, rel_tol=0.0, abs_tol=1e-12):
                issues.append(f"cost differs at {key!r} index {index}")
            if not math.isclose(
                cumulative, float(record["cumulative_cost"]), rel_tol=0.0, abs_tol=1e-12
            ):
                issues.append(f"cumulative cost differs at {key!r} index {index}")
            if action.scope is EvaluationScope.SYSTEM:
                system_actions[action.id] = action
                for artifact_id in result.artifacts:
                    artifact_producers[artifact_id] = action
                truth = problem.analytic(action.config)
                if any(
                    not math.isclose(result.outcomes[name], value, rel_tol=0.0, abs_tol=1e-12)
                    for name, value in truth.items()
                ):
                    issues.append(f"system truth differs at {key!r} index {index}")
                if problem.feasible(result.outcomes):
                    objective = result.outcomes["utility"]
                    best = objective if best is None else max(best, objective)
            else:
                if len(action.parent_artifact_ids) != 1:
                    issues.append(f"component parent count differs at {key!r} index {index}")
                elif action.parent_artifact_ids[0] in artifact_producers:
                    parent = artifact_producers[action.parent_artifact_ids[0]]
                    truth = problem.component_truth(action.component, action.config, parent.config)
                    if set(truth) != set(result.outcomes) or any(
                        not math.isclose(
                            result.outcomes[name], value, rel_tol=0.0, abs_tol=1e-12
                        )
                        for name, value in truth.items()
                    ):
                        issues.append(f"component truth differs at {key!r} index {index}")
            expected_regret = problem.normalized_regret(best)
            if not math.isclose(
                expected_regret,
                float(record["normalized_regret"]),
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                issues.append(f"regret differs at {key!r} index {index}")
        if len(endings[key]) != 1:
            issues.append(f"run end count differs at {key!r}")
        if errors[key]:
            issues.append(f"run error retained at {key!r}")
    return {
        "passed": not issues,
        "issue_count": len(issues),
        "reported_issues": issues[:100],
    }


def _lineage_audit(records):
    evaluations, _, _, _ = _group_records(records)
    issues = []
    checked = 0
    for key, group in evaluations.items():
        problem = problem_by_name(key[0])
        artifacts = {}
        for record in sorted(group, key=lambda item: int(item["evaluation_index"])):
            action = EvaluationAction.from_dict(record["action"])
            result = EvaluationResult.from_dict(record["result"])
            if action.scope is EvaluationScope.COMPONENT:
                checked += 1
                parent_id = action.parent_artifact_ids[0]
                parent = artifacts.get(parent_id)
                if parent is None:
                    issues.append(f"unknown or non-system parent {parent_id!r} at {key!r}")
                    continue
                required = {
                    f"{coupling.source_component}.{coupling.source_port}"
                    for coupling in problem.network.couplings
                    if coupling.target_component == action.component
                }
                if not required.issubset(parent):
                    issues.append(f"parent members are incompatible at {key!r}: {parent_id}")
            if action.scope is EvaluationScope.SYSTEM:
                for artifact_id, members in record["artifact_members"].items():
                    artifacts[artifact_id] = set(members)
            elif result.artifacts and any(
                artifact_id in artifacts for artifact_id in result.artifacts
            ):
                issues.append(f"component artifact collided with a system artifact at {key!r}")
    return {
        "passed": not issues and checked > 0,
        "checked_component_actions": checked,
        "issue_count": len(issues),
        "reported_issues": issues[:100],
    }


def _performance(rows):
    def median(problem, method, field):
        values = [
            float(row[field])
            for row in rows
            if (problem is None or row["problem"] == problem)
            and row["method"] == method
            and row[field] != ""
        ]
        return None if not values else float(np.median(values))

    def difference(left, right):
        return None if left is None or right is None else left - right

    voi = "function_network_partial"
    full = "function_network_full"
    random = "function_network_partial_random"
    problems = [item.name for item in benchmark_problems()]
    return {
        "pooled_final_difference": difference(
            median(None, voi, "final_regret"), median(None, full, "final_regret")
        ),
        "problem_final_differences": {
            problem: difference(
                median(problem, voi, "final_regret"),
                median(problem, full, "final_regret"),
            )
            for problem in problems
        },
        "pooled_area_difference": difference(
            median(None, voi, "regret_area"), median(None, full, "regret_area")
        ),
        "random_area_differences": {
            problem: difference(
                median(problem, voi, "regret_area"),
                median(problem, random, "regret_area"),
            )
            for problem in problems
        },
    }


def _fallback_metrics(records):
    by_problem = Counter()
    failures = Counter()
    for record in records:
        if (
            record["record_type"] != "acquisition"
            or record["method"] != "function_network_partial"
        ):
            continue
        by_problem[record["problem"]] += 1
        failures[record["problem"]] += _unresolved_fallback(record)
    total = sum(by_problem.values())
    return {
        "fallback_count": sum(failures.values()),
        "decision_count": total,
        "pooled_rate": 0.0 if total == 0 else sum(failures.values()) / total,
        "problem_rates": {
            problem.name: (
                0.0
                if by_problem[problem.name] == 0
                else failures[problem.name] / by_problem[problem.name]
            )
            for problem in benchmark_problems()
        },
    }


def _terminal_separation(records):
    issues = []
    checked = 0
    for record in records:
        if record["record_type"] != "evaluation":
            continue
        action = record["action"]
        if action["scope"] != EvaluationScope.COMPONENT.value:
            continue
        checked += 1
        problem = problem_by_name(record["problem"])
        terminal_names = {"utility", *(item.outcome for item in problem.network.constraints)}
        overlap = terminal_names & set(record["result"]["outcomes"])
        if overlap:
            issues.append(f"component action contains terminal outcomes: {sorted(overlap)}")
    return {
        "passed": not issues and checked > 0,
        "checked_component_actions": checked,
        "issue_count": len(issues),
        "reported_issues": issues[:100],
    }


def gate_json(gate: Mapping[str, object]) -> str:
    return json.dumps(gate, indent=2, sort_keys=True, allow_nan=False) + "\n"


def value_cost_json(payload: Mapping[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"


def render_report(rows, gate, components) -> str:
    performance = _performance(rows)
    final_difference = performance["pooled_final_difference"]
    area_difference = performance["pooled_area_difference"]
    lines = [
        "# Partial-network benchmark",
        "",
        f"Overall gate: **{'PASS' if gate['passed'] else 'FAIL'}**",
        "",
        "## Evidence",
        "",
        f"- Runs: {len(rows)}",
        f"- Complete runs: {sum(bool(row['completed']) for row in rows)}",
        "- Pooled final-regret difference, partial minus full: "
        + ("unavailable" if final_difference is None else f"{final_difference:.6f}"),
        "- Pooled regret-area difference, partial minus full: "
        + ("unavailable" if area_difference is None else f"{area_difference:.6f}"),
        "",
        "## Criteria",
        "",
    ]
    lines.extend(
        f"- {'PASS' if criterion['passed'] else 'FAIL'}: `{criterion['name']}`"
        for criterion in gate["criteria"]
    )
    lines.extend(["", "## Component selections", ""])
    lines.extend(
        f"- `{row['problem']}` / `{row['method']}` / `{row['component']}`: {row['selection_count']}"
        for row in components
        if row["selection_count"]
    )
    lines.extend(
        [
            "",
            "The gate evaluates Decision 0007 without changing its thresholds. Raw errors and adverse results remain in the evidence.",
            "",
        ]
    )
    return "\n".join(lines)
