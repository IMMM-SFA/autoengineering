"""Native circuit SLSQP recipe under fixed iteration and model-call ceilings."""

from __future__ import annotations

from pathlib import Path

from autoengineering.utility.engineering_native import (
    NativeDriverResult,
    NativeSolveRecord,
    NativeSolverState,
)
from examples.utility.engineering import native_design, rules as circuit_rules


def execute(job):
    spec = job.specification
    rules = spec.execution.study.rules
    if (
        rules.primary_metric != "source_power"
        or rules.direction != "minimize"
        or {p.name for p in spec.execution.study.run.search_space.parameters} != {"source_current"}
    ):
        raise ValueError("native circuit profile requires its source-power design question")
    if any(set(s.forcing) != {"ground_voltage"} for s in spec.execution.scenarios):
        raise ValueError("native circuit profile requires its ground-voltage scenarios")
    check = next(c for c in rules.checks if c.name == "node_voltage" and c.required)
    minimum = check.options["minimum_V"]
    parameter = spec.execution.study.run.search_space.parameters[0]
    if (
        getattr(parameter, "lower", None),
        getattr(parameter, "upper", None),
        getattr(parameter, "scale", None),
    ) != (0.01, 0.1, "linear") or rules != circuit_rules(minimum, rules.minimum_gain):
        raise ValueError("native circuit recipe differs from its qualified bounds or acceptance")
    result = native_design(
        tuple(s.forcing["ground_voltage"] for s in spec.execution.scenarios),
        minimum,
        Path(job.scratch_path),
        max_iterations=spec.max_iterations,
        max_solves=spec.max_model_solves,
    )

    def state(work):
        return NativeSolverState(
            work["converged"],
            work["residual_norm"],
            work["residual_tolerance"],
            "A",
            work["solver_iterations"],
            work["component_calls"],
            work["derivative_calls"],
        )

    calls = [
        NativeSolveRecord("driver", None, "shared_problem_snapshot", state(r["work"]))
        for r in result["native_solves"]
    ]
    calls += [
        NativeSolveRecord("scenario", s.scenario_id, "independent_problem", state(r["work"]))
        for s, r in zip(spec.execution.scenarios, result["scenario_solves"])
    ]
    if result["physical_solves"] != len(calls):
        raise ValueError("native model-call accounting differs")
    return NativeDriverResult(
        "utility-native-result-v1",
        job.digest,
        {"source_current": result["source_current_A"]},
        result["driver_success"],
        tuple(calls),
    )
