"""Registered SLSQP recipe for the declared engineering-v3 load envelope.

The 0.62001 V optimizer target includes a numerical buffer. Physical acceptance
still requires 0.62 V. The corner is selection support, outside the scored
scenario population. Every fresh solve remains in the returned work record.
"""

from __future__ import annotations

import math
from pathlib import Path

from autoengineering.utility.engineering_native import (
    NativeDriverResultV3,
    NativeSolveRecord,
    NativeSolverState,
    NativeSupportSolve,
)
from autoengineering.utility.engineering_process import EngineeringScenario
from examples.utility import engineering_load_native as native
from examples.utility.engineering import rules as circuit_rules

MINIMUM_VOLTAGE = 0.62
OPTIMIZER_TARGET = 0.62001
SUPPORT_ID = "declared-envelope-corner"
BOUNDS = {
    "ground_voltage": (-0.02, 0.02),
    "resistor1_ohm": (90.0, 110.0),
    "resistor2_ohm": (9000.0, 11000.0),
}


def _validate(spec):
    execution = spec.execution
    parameters = execution.study.run.search_space.parameters
    if (
        execution.entrypoint != "examples.utility.engineering_load:execute"
        or len(parameters) != 1
        or parameters[0].name != "source_current"
        or (getattr(parameters[0], "lower", None), getattr(parameters[0], "upper", None),
            getattr(parameters[0], "scale", None)) != (0.01, 0.1, "linear")
        or getattr(parameters[0], "active_when", None)
        or execution.study.rules != circuit_rules(MINIMUM_VOLTAGE, execution.study.rules.minimum_gain)
        or spec.max_iterations != 20
        or not 1 <= len(execution.scenarios) <= 24
        or not len(execution.scenarios) + 1 < spec.max_model_solves <= 64
    ):
        raise ValueError("native envelope recipe differs from its declared domain or rules")
    seen = set()
    for scenario in execution.scenarios:
        if (
            scenario.scenario_id == SUPPORT_ID
            or scenario.scenario_id in seen
            or set(scenario.forcing) != set(BOUNDS)
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   or not BOUNDS[name][0] <= value <= BOUNDS[name][1]
                   for name, value in scenario.forcing.items())
        ):
            raise ValueError("native scenario is outside the declared load envelope")
        seen.add(scenario.scenario_id)


def _state(work):
    return NativeSolverState(
        work["converged"], work["residual_norm"], work["residual_tolerance"], "A",
        work["solver_iterations"], work["component_calls"], work["derivative_calls"],
    )


def _physical(row):
    work, outputs = row["work"], row["outputs"]
    return (
        all(math.isfinite(value) for value in outputs.values())
        and outputs["node2_voltage"] >= MINIMUM_VOLTAGE
        and work["converged"]
        and work["residual_tolerance"] == 1e-10
        and work["residual_norm"] <= 1e-10
        and work["solver_iterations"] <= 100
    )


def execute(job):
    """Select on the public envelope, then freshly check the supplied scenarios.

    The controller must still score the returned configuration through its
    authoritative evaluator. These native checks do not replace that score.
    """
    spec = job.specification
    _validate(spec)
    scratch, root = Path(job.scratch_path), Path(job.source_root)
    corner = EngineeringScenario(SUPPORT_ID, {
        "ground_voltage": -0.02, "resistor1_ohm": 90.0, "resistor2_ohm": 11000.0,
    })
    design = native.native_design(
        (corner,), OPTIMIZER_TARGET, scratch, max_iterations=spec.max_iterations,
        max_solves=spec.max_model_solves - len(spec.execution.scenarios), source_root=root,
    )
    current = design["source_current_A"]
    if not math.isfinite(current) or not 0.01 <= current <= 0.1:
        raise ValueError("native design returned current outside the declared domain")
    corner_rows = design["scenario_solves"]
    if len(corner_rows) != 1 or design["physical_solves"] != len(design["native_solves"]) + 1:
        raise ValueError("native corner work differs from the declared recipe")
    checked = [native.direct(current, case, scratch, source_root=root)
               for case in spec.execution.scenarios]
    calls = tuple(NativeSolveRecord(
        "driver", None, "shared_problem_snapshot", _state(row["work"]),
    ) for row in design["native_solves"])
    calls += tuple(NativeSolveRecord(
        "scenario", case.scenario_id, "independent_problem", _state(row["work"]),
    ) for case, row in zip(spec.execution.scenarios, checked, strict=True))
    return NativeDriverResultV3(
        "utility-native-result-v3", job.digest, {"source_current": current},
        bool(design["driver_success"] and all(_physical(row) for row in [*corner_rows, *checked])),
        calls, _state(design["driver_final_work"]),
        (NativeSupportSolve(SUPPORT_ID, _state(corner_rows[0]["work"])),),
        design["feasible"],
    )
