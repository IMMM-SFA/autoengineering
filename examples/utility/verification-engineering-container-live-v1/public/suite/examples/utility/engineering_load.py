"""Trusted scalar load scenarios around the existing coupled OpenMDAO circuit.

Resistance values are scenario inputs, not design variables. The upstream
resistor implementation exposes them as options. This wrapper sets those
options once before the authoritative adapter runs the intact coupled solve.
It supplies no privacy boundary or final-scenario admission.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np

from autoengineering.adapters.contracts import PrepareContext, validate_arrays
from autoengineering.adapters.openmdao import OpenMdaoAdapter, OpenMdaoHandle, VariableBinding
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import digest
from examples.interoperability.circuit.fixture import VARIABLES
from examples.interoperability.circuit.model import factory
from examples.utility.engineering import context as ground_context
from examples.utility.engineering import diagnostics as ground_diagnostics

LOADS = {"resistor1_ohm": "R1", "resistor2_ohm": "R2"}
UNITS = {"ground_voltage": "V", "resistor1_ohm": "ohm", "resistor2_ohm": "ohm"}


def context(current: float, scratch: Path, *, source_root: Path | None = None) -> PrepareContext:
    """Bind the load input contract without evaluating any scenario."""
    ctx = ground_context(current, scratch, source_root=source_root)
    root = source_root or Path(__file__).resolve().parents[2]
    own = reference(root, "examples/utility/engineering_load.py", media_type="text/plain",
                    producer="utility-circuit-load")
    ground = ctx.model.inputs[0]
    ports = tuple(replace(ground, name=name, units=unit) for name, unit in UNITS.items())
    model = replace(ctx.model, graph_digest=digest({"circuit": "coupled-load-v1"}),
                    source_bundle=(*ctx.model.source_bundle, own), inputs=ports)
    return replace(ctx, model=model)


def diagnostics(problem):
    """Retain native counters and check constitutive laws at the actual loads."""
    # The original inspector assumes nominal resistances. Its counters and diode
    # checks remain useful, but its nominal Ohm residual is not a load residual.
    original = ground_diagnostics(problem)

    def value(name):
        return float(problem.get_val(name).item())

    circuit = problem.model.circuit
    r1, r2 = (float(getattr(circuit, name).options["R"]) for name in ("R1", "R2"))
    ground, v1, v2 = (value(name) for name in ("ground.V", "circuit.n1.V", "circuit.n2.V"))
    i1, i2, diode = (value(name) for name in ("circuit.R1.I", "circuit.R2.I", "circuit.D1.I"))
    residuals = [value("source.I") - i1 - i2, i2 - diode,
                 (v1 - ground) / r1 - i1, (v1 - v2) / r2 - i2,
                 1e-15 * np.expm1((v2 - ground) / .025875) - diode]
    if not np.isfinite(residuals).all():
        raise ValueError("nonfinite load-circuit constitutive residual")
    residual = float(max(abs(r) for r in residuals))
    return replace(original, converged=residual <= original.residual_tolerance,
                   residual_norm=residual)


@dataclass
class LoadHandle:
    context: PrepareContext
    native: OpenMdaoHandle


class LoadCircuitAdapter:
    """Project load forcing onto native options, then reuse the scalar adapter."""

    def __init__(self):
        self.native = OpenMdaoAdapter(factory,
            inputs={"ground_voltage": VariableBinding("ground.V", "V")},
            outputs={name: VariableBinding(variable, unit)
                     for name, (variable, unit) in VARIABLES.items()},
            parameters={"source_current": VariableBinding("source.I", "A")},
            inspector=diagnostics)

    @staticmethod
    def _contract(ctx):
        if ({p.name: p.units for p in ctx.model.inputs} != UNITS
                or any(p.time is not None or p.dtype_family != "float" for p in ctx.model.inputs)):
            raise ValueError("load circuit needs its three scalar forcing ports and exact units")
        if set(ctx.parameters) != {"source_current"}:
            raise ValueError("load circuit admits only source-current design")
        current = ctx.parameters["source_current"]
        if type(current) not in (int, float) or not np.isfinite(current) or not .01 <= current <= .1:
            raise ValueError("load circuit source current must be between 0.01 and 0.1 A")

    def prepare(self, ctx):
        self._contract(ctx)
        # The parent adapter binds actual OpenMDAO variables. Resistance ports
        # are handled explicitly here, so only ground enters that internal view.
        projected = replace(ctx, model=replace(ctx.model, inputs=tuple(
            p for p in ctx.model.inputs if p.name == "ground_voltage")))
        return LoadHandle(ctx, self.native.prepare(projected))

    def validate(self, handle):
        self._contract(handle.context)
        self.native.validate(handle.native)

    def train(self, handle, fitting_data):
        return self.native.train(handle.native, fitting_data)

    def run(self, handle, forcing):
        self.validate(handle)
        if handle.native.consumed:
            raise ValueError("load circuit attempt cannot run twice")
        inputs = validate_arrays(forcing, handle.context.model.inputs, handle.context.model.inputs)
        if any(float(inputs[name]) <= 0 for name in LOADS):
            raise ValueError("load resistances must be positive")
        for name, component in LOADS.items():
            getattr(handle.native.problem.model.circuit, component).options["R"] = float(inputs[name])
        return self.native.run(handle.native, {"ground_voltage": inputs["ground_voltage"]})

    def inspect(self, handle, outputs):
        return self.native.inspect(handle.native, outputs)

    def cleanup(self, handle):
        if handle is not None:
            self.native.cleanup(handle.native)


def adapter():
    return LoadCircuitAdapter()


def execute(job):
    """Use the existing supervised development executor, without private access."""
    from autoengineering.adapters.python import run_lifecycle
    from autoengineering.campaign.acceptance import CheckContext, CheckRegistry
    from autoengineering.campaign.records import EvaluationRecord
    from autoengineering.utility.engineering_process import EngineeringScenarioResult
    from autoengineering.utility.outcomes import OutcomeRegistry
    from examples.utility.engineering import required_voltage, source_power

    if set(job.configuration) != {"source_current"}:
        raise ValueError("load circuit admits only source-current design")
    scenario = next(s for s in job.execution.scenarios if s.scenario_id == job.scenario_id)
    if set(scenario.forcing) != set(UNITS):
        raise ValueError("load circuit needs ground voltage and both resistances")
    ctx = context(job.configuration["source_current"], Path(job.scratch_path),
                  source_root=Path(job.source_root))
    ctx = replace(ctx, seed=job.seed)
    forcing = {name: np.asarray(value) for name, value in scenario.forcing.items()}
    result = run_lifecycle(adapter(), ctx, forcing, ctx.model.inputs, ctx.model.outputs)
    if result.training.status != "not_applicable":
        raise ValueError("load circuit does not admit training")
    template = EvaluationRecord(job.action_id, ctx.model.digest, job.configuration, "success",
        {}, (), (), "development-fitting", job.action_id, result.elapsed_seconds, {})
    scored = OutcomeRegistry({"source_power": source_power}).evaluate(job.execution.study.rules,
        {scenario.scenario_id: CheckContext(result.outputs, forcing, ctx.parameters)},
        CheckRegistry({("node_voltage", "1"): required_voltage}), template)
    return EngineeringScenarioResult("utility-engineering-result-v1", job.digest,
        scored.scenarios[0], {name: float(value) for name, value in result.diagnostics.items()},
        result.elapsed_seconds, {"converged": "boolean", "residual_norm": "A",
        "residual_tolerance": "A", "solver_iterations": "count", "component_calls": "count",
        "derivative_calls": "count"})
