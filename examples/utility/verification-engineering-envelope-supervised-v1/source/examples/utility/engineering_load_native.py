"""Native SLSQP for a passive circuit scenario set containing its worst corner.

For positive source current and resistances, node voltage increases with R1
and decreases with R2. Its ground offset is additive. The supplied scenario
with minimum ground, minimum R1 and maximum R2 therefore controls feasibility.
Power increases with current in every case, so minimizing that case's power
has the same current minimizer as mean power. Other scenario sets refuse.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from examples.interoperability.circuit.model import factory
from examples.utility.engineering_load import UNITS, adapter, context, diagnostics


def dominant_scenario(scenarios):
    scenarios = tuple(scenarios)
    if not scenarios or len({s.scenario_id for s in scenarios}) != len(scenarios):
        raise ValueError("native load recipe needs unique supplied scenarios")
    for scenario in scenarios:
        if set(scenario.forcing) != set(UNITS) or any(
            type(value) not in (int, float) or not np.isfinite(value)
            for value in scenario.forcing.values()
        ):
            raise ValueError("native load recipe needs finite scalar forcing")
        if min(scenario.forcing[name] for name in ("resistor1_ohm", "resistor2_ohm")) <= 0:
            raise ValueError("native load resistances must be positive")
    corner = {"ground_voltage": min(s.forcing["ground_voltage"] for s in scenarios),
              "resistor1_ohm": min(s.forcing["resistor1_ohm"] for s in scenarios),
              "resistor2_ohm": max(s.forcing["resistor2_ohm"] for s in scenarios)}
    matches = [s for s in scenarios if dict(s.forcing) == corner]
    if not matches:
        raise ValueError("native load recipe requires a supplied dominating corner")
    return matches[0]


def direct(current, scenario, scratch, *, source_root=None):
    """One fresh load solve, retaining the original native diagnostic types."""
    wrapped = adapter()
    handle = wrapped.prepare(context(current, scratch, source_root=source_root))
    try:
        outputs = wrapped.run(handle, {name: np.array(value)
                                      for name, value in scenario.forcing.items()})
        return {"outputs": {name: float(value) for name, value in outputs.items()},
                "work": diagnostics(handle.native.problem).to_dict()}
    finally:
        wrapped.cleanup(handle)


def native_design(scenarios, minimum_voltage, scratch, *, max_iterations=20, max_solves=40,
                  source_root=None):
    """Optimize the exact controlling case and separately check every supplied case."""
    scenarios = tuple(scenarios)
    worst = dominant_scenario(scenarios)
    if type(minimum_voltage) not in (int, float) or not np.isfinite(minimum_voltage):
        raise ValueError("native load voltage requirement must be finite")
    if (type(max_iterations) is not int or type(max_solves) is not int
            or max_iterations < 1 or max_solves <= len(scenarios)):
        raise ValueError("native load cap cannot cover optimization and fresh scenario checks")
    import openmdao.api as om

    problem = factory(context(.05, scratch, source_root=source_root))
    circuit = problem.model.circuit
    original_configure = circuit.configure

    def configure():
        original_configure()
        circuit.R1.options["R"] = worst.forcing["resistor1_ohm"]
        circuit.R2.options["R"] = worst.forcing["resistor2_ohm"]

    circuit.configure = configure
    problem.model.add_subsystem("power", om.ExecComp("P=I*(V-G)",
        I={"units": "A"}, V={"units": "V"}, G={"units": "V"}, P={"units": "W"}))
    problem.model.connect("source.I", "power.I")
    problem.model.connect("ground.V", "power.G")
    problem.model.connect("circuit.n1.V", "power.V")
    problem.model.add_design_var("source.I", lower=.01, upper=.1)
    problem.model.add_objective("power.P")
    problem.model.add_constraint("circuit.n2.V", lower=minimum_voltage)
    problem.driver = om.ScipyOptimizeDriver(optimizer="SLSQP", tol=1e-10, disp=False,
                                           maxiter=max_iterations)
    records = []
    original = problem.model.run_solve_nonlinear

    def counted(*args, **kwargs):
        if len(records) >= max_solves - len(scenarios):
            raise RuntimeError("native load solve budget exhausted")
        records.append({"status": "started"})
        try:
            result = original(*args, **kwargs)
            records[-1] = {"status": "completed", "work": diagnostics(problem).to_dict()}
            return result
        except BaseException:
            records[-1]["status"] = "failed"
            raise

    problem.model.run_solve_nonlinear = counted
    try:
        problem.setup()
        problem.final_setup()
        problem.set_val("ground.V", worst.forcing["ground_voltage"], units="V")
        driver = problem.run_driver()
        current = float(problem.get_val("source.I").item())
        final_work = diagnostics(problem).to_dict()
        fresh = [direct(current, scenario, scratch, source_root=source_root) for scenario in scenarios]
        return {"source_current_A": current, "driver_success": bool(driver.success),
                "controlling_scenario": worst.scenario_id, "native_solves": records,
                "scenario_solves": fresh, "driver_final_work": final_work,
                "physical_solves": len(records) + len(fresh),
                "feasible": all(s["outputs"]["node2_voltage"] >= minimum_voltage for s in fresh)}
    finally:
        problem.cleanup()


def execute(job):
    """Return the existing native-driver record; final acceptance stays authoritative."""
    from autoengineering.utility.engineering_native import (
        NativeDriverResult, NativeSolveRecord, NativeSolverState,
    )
    from examples.utility.engineering import rules as circuit_rules

    spec = job.specification
    rules = spec.execution.study.rules
    check = next(c for c in rules.checks if c.name == "node_voltage" and c.required)
    minimum = check.options["minimum_V"]
    parameters = spec.execution.study.run.search_space.parameters
    if (len(parameters) != 1 or parameters[0].name != "source_current"
            or (getattr(parameters[0], "lower", None), getattr(parameters[0], "upper", None),
                getattr(parameters[0], "scale", None)) != (.01, .1, "linear")
            or rules != circuit_rules(minimum, rules.minimum_gain)):
        raise ValueError("native load recipe differs from its bounds or acceptance")
    result = native_design(spec.execution.scenarios, minimum, Path(job.scratch_path),
        max_iterations=spec.max_iterations, max_solves=spec.max_model_solves,
        source_root=Path(job.source_root))

    def state(work):
        return NativeSolverState(work["converged"], work["residual_norm"],
            work["residual_tolerance"], "A", work["solver_iterations"],
            work["component_calls"], work["derivative_calls"])

    calls = [NativeSolveRecord("driver", None, "shared_problem_snapshot", state(r["work"]))
             for r in result["native_solves"]]
    calls += [NativeSolveRecord("scenario", scenario.scenario_id, "independent_problem", state(r["work"]))
              for scenario, r in zip(spec.execution.scenarios, result["scenario_solves"])]
    if len(calls) != result["physical_solves"]:
        raise ValueError("native load model-call accounting differs")
    return NativeDriverResult("utility-native-result-v2", job.digest,
        {"source_current": result["source_current_A"]}, result["driver_success"], tuple(calls),
        state(result["driver_final_work"]))
