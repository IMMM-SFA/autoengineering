"""Local coupled-circuit development evidence, with native optimization separate."""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import durable_write
from autoengineering.optimization import (
    BudgetSpec, ConstraintSpec, ContinuousParameter, EvaluationResult, NoiseSpec,
    ObjectiveSpec, ObservationLedger, OptimizationStudy, SearchSpace, StudySpec,
)
from autoengineering.optimization.optuna_backend import OptunaBackend
from .fixture import VARIABLES, adapter, context
from .model import diagnostics, factory

HERE = Path(__file__).resolve().parent


def direct(current, scratch, *, derivatives=False):
    p = factory(context(current, scratch))
    started = time.perf_counter()
    try:
        p.setup()
        p.final_setup()
        p.set_val("source.I", current)
        p.run_model()
        outputs = {name: float(p.get_val(variable).item())
                   for name, (variable, _) in VARIABLES.items()}
        derivative = None
        if derivatives:
            totals = p.compute_totals(of=["circuit.n2.V"], wrt=["source.I"])
            derivative = float(totals["circuit.n2.V", "source.I"].item())
        return {"outputs": outputs, "work": diagnostics(p).to_dict(),
                "seconds": time.perf_counter() - started, "derivative": derivative}
    finally:
        p.cleanup()


def run(output):
    import openmdao.api as om

    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    protocol = json.loads((HERE / "protocol.json").read_text())
    upstream = Path(__import__("openmdao.test_suite.scripts.circuit_analysis",
                              fromlist=["__file__"]).__file__)
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob("*.py")}
    manifest = {"protocol": protocol, "sources": sources,
                "upstream_circuit_sha256": hashlib.sha256(upstream.read_bytes()).hexdigest(),
                "versions": {p: version(p) for p in ("openmdao", "optuna", "numpy", "scipy")}}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    started = time.perf_counter()
    parity = []
    for current in protocol["parity_currents_A"]:
        reference = direct(current, output)
        ctx = context(current, output)
        wrapped = run_lifecycle(adapter(), ctx, {}, (), ctx.model.outputs)
        arrays = {name: float(value) for name, value in wrapped.outputs.items()}
        for name, (_, units) in VARIABLES.items():
            tolerance = protocol["voltage_atol_V" if units == "V" else "current_atol_A"]
            if not np.isclose(arrays[name], reference["outputs"][name], atol=tolerance,
                              rtol=protocol["parity_rtol"]):
                raise ValueError("circuit direct/wrapped parity failed")
        parity.append({"current": current, "direct": reference, "wrapped": arrays,
                       "wrapped_work": {k: float(v) for k, v in wrapped.diagnostics.items()}})
    (output / "parity.json").write_text(json.dumps(parity, indent=2))
    # Derivative audit is separately charged model work, outside optimization.
    center, step = .05, 1e-6
    analytic = direct(center, output, derivatives=True)
    left, right = direct(center - step, output), direct(center + step, output)
    finite_difference = (right["outputs"]["node2_voltage"] - left["outputs"]["node2_voltage"]) / (2*step)
    (output / "derivatives.json").write_text(json.dumps({"analytic": analytic,
        "left": left, "right": right, "finite_difference": finite_difference}, indent=2))
    if not np.isclose(analytic["derivative"], finite_difference,
                      atol=protocol["derivative_atol"], rtol=protocol["derivative_rtol"]):
        raise ValueError("circuit total derivative mismatch")
    (output / "derivatives.json").write_text(json.dumps({"analytic": analytic,
        "left": left, "right": right, "finite_difference": finite_difference}, indent=2))
    spec = StudySpec("circuit-optuna", ObjectiveSpec("error", "minimize"),
                     (ConstraintSpec("node1", "<=", 10.), ConstraintSpec("node2", "<=", .8)),
                     BudgetSpec(12., "coupled_attempt", 12), NoiseSpec(), "system", 17)
    space = SearchSpace((ContinuousParameter("source_current", .01, .1),))
    records = []

    def evaluator(action):
        ctx = context(action.config["source_current"], output)
        result = run_lifecycle(adapter(), ctx, {}, (), ctx.model.outputs)
        values = {name: float(value) for name, value in result.outputs.items()}
        records.append({"action": action.to_dict(), "outputs": values,
                        "work": {name: float(v) for name, v in result.diagnostics.items()}})
        (output / f"optuna-physical-{len(records):03d}.json").write_text(json.dumps(records[-1]))
        outcomes = {"error": (values["node2_voltage"] - .65)**2,
                    "node1": values["node1_voltage"], "node2": values["node2_voltage"]}
        return EvaluationResult.success(action.id, outcomes, {}, 1., "coupled_attempt",
                                        evaluator_seconds=result.elapsed_seconds)

    study_root = output / "study"
    study = OptimizationStudy(spec, space, OptunaBackend(spec, space),
                              ObservationLedger(study_root / "observations.jsonl"),
                              evaluator, study_root)
    study.run()
    first_current = records[0]["action"]["config"]["source_current"]
    # Native driver retains coupled solver and derivative methods. Count every
    # coupled solve, and fail at the frozen ceiling rather than hide inner work.
    native = factory(context(first_current, output))
    native.model.add_subsystem("objective", om.ExecComp(
        "error=(v-.65)**2", v={"units": "V"}, error={"units": "V**2"}))
    native.model.connect("circuit.n2.V", "objective.v")
    native.model.add_design_var("source.I", lower=.01, upper=.1)
    native.model.add_objective("objective.error")
    native.model.add_constraint("circuit.n1.V", upper=10.)
    native.model.add_constraint("circuit.n2.V", upper=.8)
    native.driver = om.ScipyOptimizeDriver(optimizer="SLSQP", tol=1e-10, disp=False,
                                          maxiter=protocol["native_max_iterations"])
    calls = []
    iterations = []
    native_records = output / "native-solves"
    native_records.mkdir(mode=0o700)
    try:
        native.setup()
        native.final_setup()
        native.set_val("source.I", first_current)
        solve = native.model.circuit._solve_nonlinear

        def counted(*args, **kwargs):
            number = len(calls) + 1
            if number > protocol["native_coupled_solve_ceiling"]:
                raise RuntimeError("native coupled solve budget exhausted")
            calls.append(number)
            durable_write(native_records / f"solve-{number:04d}-intent.json", json.dumps({
                "solve": number, "source_current": float(native.get_val("source.I").item()),
            }, allow_nan=False).encode())
            completed = False
            try:
                result = solve(*args, **kwargs)
                completed = True
                return result
            finally:
                iterations.append(native.model.circuit.nonlinear_solver._iter_count)
                durable_write(native_records / f"solve-{number:04d}-receipt.json", json.dumps({
                    "solve": number, "status": "success" if completed else "failed",
                    "solver_iterations": iterations[-1],
                    "derivative_calls_cumulative": native.derivative_calls,
                    "component_calls_cumulative": sum(
                        c.iter_count + c.iter_count_apply
                        for c in native.model.circuit.system_iter(recurse=True)
                    ),
                }).encode())

        native.model.circuit._solve_nonlinear = counted
        native_started = time.perf_counter()
        driver_result = native.run_driver()
        native_result = {"source_current": float(native.get_val("source.I").item()),
                         "objective": float(native.get_val("objective.error").item()),
                         "work": diagnostics(native).to_dict(), "coupled_solves": len(calls),
                         "solver_iterations_total": sum(iterations),
                         "solver_iterations_per_solve": iterations,
                         "outputs": {name: float(native.get_val(variable).item())
                                     for name, (variable, _) in VARIABLES.items()},
                         "seconds": time.perf_counter() - native_started,
                         "driver_result": str(driver_result),
                         "budget_match": "unmatched_inner_solve_budget"}
    finally:
        native.cleanup()
    report = {"manifest_digest": digest(manifest), "parity_cases": len(parity),
              "derivative_audit_coupled_starts": 3, "parity_coupled_starts": 6,
              "optuna_physical_starts": len(records), "native": native_result,
              "optuna_recommendation": study.backend.recommend(study.ledger).to_dict(),
              "total_seconds": time.perf_counter() - started,
              "claims": "development interoperability only; unmatched native inner budget"}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
