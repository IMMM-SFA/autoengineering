"""Whole-problem OpenMDAO evaluation through trusted factories.

No OpenMDAO import is needed to reconstruct records or import the base package.
Factories supply an unconfigured Problem with its coupled solvers and explicit
nonconvergence policy. This adapter calls run_model, never run_driver.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from autoengineering.campaign.serialization import Record

from .contracts import PrepareContext, TrainingResult, validate_arrays


@dataclass(frozen=True)
class VariableBinding(Record):
    variable: str
    units: str | None


@dataclass(frozen=True)
class SolveDiagnostics(Record):
    converged: bool
    residual_norm: float
    residual_tolerance: float
    solver_iterations: int
    component_calls: int
    derivative_calls: int

    def _validate(self):
        if self.residual_norm < 0 or self.residual_tolerance < 0:
            raise ValueError("solver residual and tolerance must be nonnegative")
        if min(self.solver_iterations, self.component_calls, self.derivative_calls) < 0:
            raise ValueError("solver work counters cannot be negative")
        if self.converged and self.residual_norm > self.residual_tolerance:
            raise ValueError("convergence contradicts residual tolerance")


@dataclass
class OpenMdaoHandle:
    problem: object
    context: PrepareContext
    closed: bool = False
    consumed: bool = False
    diagnostics: SolveDiagnostics | None = None


class OpenMdaoAdapter:
    """Scalar model interface around an intact coupled Problem.

    The trusted inspector must report convergence and actual inner work, even
    when all outputs are finite. It belongs in the registered source closure,
    together with factory, mappings, solver settings and framework identity.
    Objective/constraint interpretation remains with the campaign controller.
    """

    def __init__(
        self,
        factory: Callable[[PrepareContext], object],
        *,
        inputs: Mapping[str, VariableBinding],
        outputs: Mapping[str, VariableBinding],
        parameters: Mapping[str, VariableBinding],
        inspector: Callable[[object], SolveDiagnostics],
    ):
        if not callable(factory) or not callable(inspector):
            raise ValueError("OpenMDAO requires trusted factory and convergence inspector")
        self.factory, self.inspector = factory, inspector
        self.inputs, self.outputs, self.parameters = (
            MappingProxyType(dict(mapping)) for mapping in (inputs, outputs, parameters)
        )
        bindings = [*self.inputs.values(), *self.parameters.values()]
        if len({b.variable for b in bindings}) != len(bindings):
            raise ValueError("an OpenMDAO input cannot have multiple sources")

    def prepare(self, context: PrepareContext) -> OpenMdaoHandle:
        handle = OpenMdaoHandle(self.factory(context), context)
        try:
            handle.problem.setup()
            handle.problem.final_setup()
            self.validate(handle)
        except BaseException as error:
            try:
                self.cleanup(handle)
            except Exception as cleanup_error:
                error.add_note(f"OpenMDAO cleanup failed: {cleanup_error}")
            raise
        return handle

    def validate(self, handle: OpenMdaoHandle) -> None:
        if handle.closed:
            raise ValueError("OpenMDAO handle is closed")
        snapshot = handle.context.model
        for ports, mapping in ((snapshot.inputs, self.inputs), (snapshot.outputs, self.outputs)):
            if set(mapping) != {p.name for p in ports}:
                raise ValueError("OpenMDAO port mapping differs from declared ports")
            for port in ports:
                if port.time is not None or port.dtype_family != "float":
                    raise ValueError("OpenMDAO initial profile requires scalar float ports")
                if mapping[port.name].units != port.units:
                    raise ValueError("OpenMDAO binding units differ from port units")
        if set(self.parameters) != set(handle.context.parameters):
            raise ValueError("OpenMDAO parameter mapping differs from declared parameters")
        metadata = handle.problem.model.get_io_metadata(metadata_keys=["units", "shape"])
        for binding in (*self.inputs.values(), *self.outputs.values(), *self.parameters.values()):
            matches = [
                item for name, item in metadata.items()
                if name == binding.variable or item.get("prom_name") == binding.variable
            ]
            if not matches or any(
                item["units"] != binding.units or tuple(item["shape"]) != (1,)
                for item in matches
            ):
                raise ValueError("OpenMDAO variable units or scalar shape mismatch")

    def train(self, handle, fitting_data) -> TrainingResult:
        if fitting_data:
            raise ValueError("OpenMDAO adapter does not train models")
        return TrainingResult("not_applicable", None, None)

    def run(self, handle: OpenMdaoHandle, forcing: Mapping[str, np.ndarray]):
        self.validate(handle)
        if handle.consumed:
            raise ValueError("OpenMDAO attempt cannot run twice")
        context, problem = handle.context, handle.problem
        inputs = validate_arrays(forcing, context.model.inputs, context.model.inputs)
        for name, value in context.parameters.items():
            if type(value) not in (int, float) or not np.isfinite(value):
                raise ValueError("OpenMDAO parameters must be finite numbers")
        handle.consumed = True
        for mapping, values in ((self.inputs, inputs), (self.parameters, context.parameters)):
            for name, binding in mapping.items():
                problem.set_val(binding.variable, np.array([values[name]], dtype=float).copy())
        problem.run_model()
        diagnostics = self.inspector(problem)
        if not isinstance(diagnostics, SolveDiagnostics):
            raise ValueError("OpenMDAO inspector must return solver diagnostics")
        handle.diagnostics = diagnostics
        if not diagnostics.converged:
            raise RuntimeError("OpenMDAO coupled solve did not converge")
        outputs = {}
        for name, binding in self.outputs.items():
            value = np.asarray(problem.get_val(binding.variable))
            if value.shape != (1,) or value.dtype.kind != "f":
                raise ValueError("OpenMDAO output is not scalar floating point")
            outputs[name] = np.array(value[0], copy=True)
        return validate_arrays(outputs, context.model.outputs, context.model.outputs)

    def inspect(self, handle: OpenMdaoHandle, outputs):
        if handle.diagnostics is None:
            raise ValueError("OpenMDAO solve diagnostics are unavailable")
        return {
            name: np.asarray(value, dtype=float)
            for name, value in handle.diagnostics.to_dict().items()
        }

    def cleanup(self, handle: OpenMdaoHandle | None) -> None:
        if handle is not None and not handle.closed:
            handle.closed = True
            handle.problem.cleanup()
