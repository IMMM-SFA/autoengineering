"""Coupled circuit operating-scenario development adapter.

Ground-potential scenarios are supplied engineering assumptions. This scalar
profile does not claim empirical validation or independent utility evidence.
"""
from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

import numpy as np

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.adapters.openmdao import OpenMdaoAdapter, SolveDiagnostics, VariableBinding
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ModelSnapshot, PortContract
from autoengineering.campaign.serialization import digest
from autoengineering.utility.outcomes import EngineeringAcceptance, OutcomeSpec, evaluator_identity
from autoengineering.campaign.spec import CheckSpec
from examples.interoperability.circuit.model import factory
from examples.interoperability.circuit.fixture import VARIABLES

ROOT = Path(__file__).resolve().parents[2]


def diagnostics(problem):
    def value(name):
        return float(problem.get_val(name).item())

    ground = value("ground.V")
    v1, v2 = value("circuit.n1.V"), value("circuit.n2.V")
    i1, i2, diode = (value(n) for n in ("circuit.R1.I", "circuit.R2.I", "circuit.D1.I"))
    residuals = [value("source.I") - i1 - i2, i2 - diode,
                 (v1-ground)/100. - i1, (v1-v2)/10000. - i2,
                 1e-15 * np.expm1((v2-ground)/.025875) - diode]
    if not np.isfinite(residuals).all():
        raise ValueError("nonfinite circuit constitutive residual")
    residual = float(max(abs(r) for r in residuals))
    circuit = problem.model.circuit
    return SolveDiagnostics(residual <= 1e-10, residual, 1e-10,
                            circuit.nonlinear_solver._iter_count,
                            sum(c.iter_count + c.iter_count_apply for c in circuit.system_iter()),
                            problem.derivative_calls)


def context(current: float, scratch: Path, *, source_root: Path | None = None) -> PrepareContext:
    if not np.isfinite(current) or not .01 <= current <= .1:
        raise ValueError("development source current must be between 0.01 and 0.1 A")
    source_root = source_root or ROOT
    sources = tuple(reference(source_root, path, media_type="text/plain", producer="utility-circuit")
                    for path in ("examples/utility/engineering.py",
                                 "examples/interoperability/circuit/model.py",
                                 "examples/interoperability/circuit/fixture.py", "pixi.lock"))
    def port(name, units):
        return PortContract(name, (), units, "float", (), "scalar", digest({"grid": "scalar"}), None)
    model = ModelSnapshot(digest({"circuit": "coupled-ground-v1"}),
                          {"circuit": "openmdao-3.41.0"}, sources,
                          digest({"openmdao": version("openmdao")}),
                          (port("ground_voltage", "V"),),
                          tuple(port(name, unit) for name, (_, unit) in VARIABLES.items()))
    return PrepareContext(model, {"source_current": current}, 17, str(scratch), ())


def adapter():
    return OpenMdaoAdapter(factory, inputs={"ground_voltage": VariableBinding("ground.V", "V")},
                          outputs={name: VariableBinding(variable, unit)
                                   for name, (variable, unit) in VARIABLES.items()},
                          parameters={"source_current": VariableBinding("source.I", "A")},
                          inspector=diagnostics)


def direct(current, ground, scratch, *, derivatives=False):
    """One development solve; every call is separate physical work."""
    ctx = context(current, scratch)
    problem = factory(ctx)
    try:
        problem.setup()
        problem.final_setup()
        problem.set_val("source.I", current, units="A")
        problem.set_val("ground.V", ground, units="V")
        problem.run_model()
        outputs = {name: float(problem.get_val(variable).item())
                   for name, (variable, _) in VARIABLES.items()}
        derivative = None
        if derivatives:
            derivative = float(problem.compute_totals(
                of=["circuit.n2.V"], wrt=["source.I"])["circuit.n2.V", "source.I"].item())
        return {"outputs": outputs, "work": diagnostics(problem).to_dict(),
                "node2_current_derivative": derivative}
    finally:
        problem.cleanup()


def source_power(ctx):
    return float(ctx.parameters["source_current"] * (
        float(ctx.outputs["node1_voltage"]) - float(ctx.forcing["ground_voltage"])))


def required_voltage(ctx, options):
    voltage = float(ctx.outputs["node2_voltage"])
    minimum = float(options["minimum_V"])
    return ("pass" if voltage >= minimum else "fail", voltage, minimum,
            "Node voltage must satisfy the frozen absolute operating requirement")


def rules(minimum_voltage, minimum_gain):
    return EngineeringAcceptance("engineering-acceptance-v1", (
        OutcomeSpec("engineering-outcome-v1", "source_power", "W", "minimize", "mean",
                    evaluator_identity(source_power)),), "source_power", minimum_gain, {}, (
                        CheckSpec("node_voltage", "1", True, "scenario",
                                  {"minimum_V": minimum_voltage}),))


def native_design(grounds, minimum_voltage, scratch, *, max_iterations=20, max_solves=40):
    """Native derivative-based design on the worst ground-potential scenario.

    In this circuit all constitutive laws depend on voltage differences, so
    shifting ground shifts both node voltages equally. The smallest ground is
    the restrictive case for an absolute lower voltage constraint. Every solve
    is counted, including the final explicit scenario checks.
    """
    import openmdao.api as om

    grounds = tuple(float(g) for g in grounds)
    if not grounds or not np.isfinite(grounds).all() or not np.isfinite(minimum_voltage):
        raise ValueError("native design needs finite scenario specifications")
    if type(max_iterations) is not int or type(max_solves) is not int or min(
            max_iterations, max_solves) < 1:
        raise ValueError("native design requires positive iteration and solve caps")
    # Reserve one bounded solve for each final scenario check before optimization.
    if max_solves <= len(grounds):
        raise ValueError("native solve cap cannot cover optimization and scenario checks")
    problem = factory(context(.05, scratch))
    problem.model.add_subsystem("power", om.ExecComp(
        "P=I*(V-G)", I={"units": "A"}, V={"units": "V"}, G={"units": "V"}, P={"units": "W"}))
    problem.model.connect("source.I", "power.I")
    problem.model.connect("ground.V", "power.G")
    problem.model.connect("circuit.n1.V", "power.V")
    problem.model.add_design_var("source.I", lower=.01, upper=.1)
    problem.model.add_objective("power.P")
    problem.model.add_constraint("circuit.n2.V", lower=minimum_voltage)
    problem.driver = om.ScipyOptimizeDriver(optimizer="SLSQP", tol=1e-10, disp=False,
                                           maxiter=max_iterations)
    solve_records = []
    original = problem.model.run_solve_nonlinear

    def counted(*args, **kwargs):
        if len(solve_records) >= max_solves - len(grounds):
            raise RuntimeError("native solve budget exhausted")
        solve_records.append({"status": "started"})
        try:
            result = original(*args, **kwargs)
            solve_records[-1] = {"status": "completed", "work": diagnostics(problem).to_dict()}
            return result
        except BaseException:
            solve_records[-1]["status"] = "failed"
            raise

    problem.model.run_solve_nonlinear = counted
    try:
        problem.setup()
        problem.final_setup()
        problem.set_val("ground.V", min(grounds), units="V")
        driver_result = problem.run_driver()
        current = float(problem.get_val("source.I").item())
        final_work = diagnostics(problem).to_dict()
        # Final checks are separate executions, never hidden in driver trial counts.
        scenarios = [direct(current, ground, scratch) for ground in grounds]
        return {"source_current_A": current, "driver_success": bool(driver_result.success),
                "native_solves": solve_records, "scenario_solves": scenarios,
                "driver_final_work": final_work,
                "physical_solves": len(solve_records) + len(scenarios),
                "feasible": all(s["outputs"]["node2_voltage"] >= minimum_voltage - 1e-8
                                for s in scenarios)}
    finally:
        problem.cleanup()
