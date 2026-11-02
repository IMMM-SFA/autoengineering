"""Lifecycle driver for supplied trusted Python models."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import time
from types import MappingProxyType

import numpy as np

from autoengineering.campaign.records import PortContract

from .contracts import ModelAdapter, PrepareContext, TrainingResult, validate_arrays


@dataclass
class PythonHandle:
    context: PrepareContext
    closed: bool = False


class PythonAdapter:
    """Compatibility wrapper for a supplied stateless callable, never an import string.

    Stateful models implement ModelAdapter directly. Optional training is explicit.
    """

    def __init__(
        self,
        function: Callable,
        validate_parameters: Callable,
        trainer: Callable | None = None,
        inspector: Callable | None = None,
    ):
        self.function = function
        self.validate_parameters = validate_parameters
        self.trainer = trainer
        self.inspector = inspector

    def prepare(self, context: PrepareContext) -> PythonHandle:
        return PythonHandle(context)

    def validate(self, handle: PythonHandle) -> None:
        if handle.closed:
            raise ValueError("adapter handle is closed")
        self.validate_parameters(handle.context.parameters)

    def train(self, handle: PythonHandle, fitting_data: Mapping[str, np.ndarray]) -> TrainingResult:
        if self.trainer is None:
            return TrainingResult("not_applicable", None, None)
        return self.trainer(handle, fitting_data)

    def run(self, handle: PythonHandle, forcing: Mapping[str, np.ndarray]):
        self.validate(handle)
        return self.function(forcing, handle.context.parameters)

    def inspect(self, handle: PythonHandle, outputs: Mapping[str, np.ndarray]):
        return {} if self.inspector is None else self.inspector(handle, outputs)

    def cleanup(self, handle: PythonHandle | None) -> None:
        if handle is not None:
            handle.closed = True


@dataclass(frozen=True)
class LifecycleResult:
    outputs: Mapping[str, np.ndarray]
    diagnostics: Mapping[str, np.ndarray]
    training: TrainingResult
    elapsed_seconds: float


def _unchanged(arrays, saved):
    if set(arrays) != set(saved) or any(
        not np.array_equal(arrays[name], value) for name, value in saved.items()
    ):
        raise ValueError("adapter mutated its input arrays")


def run_lifecycle(
    adapter: ModelAdapter,
    context: PrepareContext,
    forcing: Mapping[str, np.ndarray],
    input_contracts: tuple[PortContract, ...],
    output_contracts: tuple[PortContract, ...],
    *,
    fitting_data: Mapping[str, np.ndarray] | None = None,
) -> LifecycleResult:
    """One fresh configuration, with cleanup even after preparation or validation failure.

    The broker supplies only fitting labels to training. Comparison labels never enter
    this driver. Timeout/cancellation is the supervisor's responsibility.
    """
    started = time.monotonic()
    inputs = validate_arrays(forcing, context.model.inputs, input_contracts)
    saved = {name: value.copy() for name, value in inputs.items()}
    fitting = MappingProxyType(
        {name: np.array(value, copy=True) for name, value in (fitting_data or {}).items()}
    )
    for array in fitting.values():
        array.setflags(write=False)
    saved_fitting = {name: value.copy() for name, value in fitting.items()}
    handle = None
    primary_error = None
    try:
        handle = adapter.prepare(context)
        adapter.validate(handle)
        training = adapter.train(handle, fitting)
        if not isinstance(training, TrainingResult):
            raise ValueError("adapter did not return a training record")
        _unchanged(fitting, saved_fitting)
        result = adapter.run(handle, inputs)
        _unchanged(inputs, saved)
        outputs = validate_arrays(result, context.model.outputs, output_contracts)
        saved_outputs = {name: value.copy() for name, value in outputs.items()}
        diagnostics = adapter.inspect(handle, outputs)
        # Inspection may not alter the scientific arrays retained for evaluation.
        _unchanged(outputs, saved_outputs)
        for array in saved_outputs.values():
            array.setflags(write=False)
        frozen_diagnostics = {}
        for name, value in diagnostics.items():
            array = np.array(value, copy=True)
            if array.dtype.kind not in "fiu" or not np.isfinite(array).all():
                raise ValueError("invalid inspection diagnostics")
            array.setflags(write=False)
            frozen_diagnostics[name] = array
        return LifecycleResult(
            MappingProxyType(saved_outputs),
            MappingProxyType(frozen_diagnostics),
            training,
            time.monotonic() - started,
        )
    except BaseException as error:
        primary_error = error
        raise
    finally:
        try:
            adapter.cleanup(handle)
        except Exception as cleanup_error:
            if primary_error is None:
                raise
            primary_error.add_note(f"adapter cleanup failed: {cleanup_error}")
