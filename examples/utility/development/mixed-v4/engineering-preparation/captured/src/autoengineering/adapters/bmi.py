"""Trusted BMI factories with explicit scalar float64, daily exchange.

The factory receives the immutable prepare context. No import strings, unit
conversion, interpolation, training or checkpoint restoration are supported.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from autoengineering.adapters.contracts import PrepareContext, TrainingResult, validate_arrays
from autoengineering.campaign.records import TimeContract


@dataclass
class BmiHandle:
    model: object
    context: PrepareContext
    initialized: bool = False
    finalized: bool = False
    consumed: bool = False
    cleanup_errors: list[str] = field(default_factory=list)


class BmiAdapter:
    """One fresh model per attempt, forcing then update then output collection.

    ``origin`` is the date at BMI numeric time zero. Every declared port must
    specify its semantics and start/end timestamp convention. Instantaneous
    inputs are sampled at interval start and outputs are collected at interval end.
    Initialization failures trigger best-effort finalization without replacing
    the primary exception. Cleanup failures remain on the handle.
    """

    def __init__(self, factory: Callable[[PrepareContext], object], *, origin: str):
        if not callable(factory):
            raise ValueError("BMI requires a trusted callable factory")
        self.factory = factory
        self.origin = date.fromisoformat(origin)
        if self.origin.isoformat() != origin:
            raise ValueError("BMI origin requires a canonical ISO date")

    def prepare(self, context: PrepareContext) -> BmiHandle:
        handle = BmiHandle(self.factory(context), context)
        try:
            handle.model.initialize()
            handle.initialized = True
            self.validate(handle)
        except BaseException as error:
            try:
                self.cleanup(handle)
            except Exception as cleanup_error:
                error.add_note(f"BMI cleanup failed: {cleanup_error}")
            raise
        return handle

    def validate(self, handle: BmiHandle) -> None:
        model, snapshot = handle.model, handle.context.model
        if handle.finalized:
            raise ValueError("BMI handle is finalized")
        for actual, ports in (
            (model.get_input_var_names(), snapshot.inputs),
            (model.get_output_var_names(), snapshot.outputs),
        ):
            names = tuple(actual)
            if len(names) != len(set(names)) or set(names) != {p.name for p in ports}:
                raise ValueError("BMI variable names differ from declared ports")
        ports = (*snapshot.inputs, *snapshot.outputs)
        if not ports or any(p.time is None for p in ports):
            raise ValueError("BMI profile requires daily ports")
        count = len(ports[0].time.dates)
        mapped = [(port, "start") for port in snapshot.inputs] + [
            (port, "end") for port in snapshot.outputs
        ]
        for port, instantaneous_timestamp in mapped:
            time = port.time
            if port.dtype_family != "float" or not isinstance(time, TimeContract):
                raise ValueError("BMI profile requires float daily values")
            if time.semantics == "instantaneous" and time.timestamp != instantaneous_timestamp:
                raise ValueError("BMI instantaneous inputs require start and outputs require end")
            first = self.origin + timedelta(days=1 if time.timestamp == "end" else 0)
            if time.dates != tuple((first + timedelta(days=i)).isoformat() for i in range(count)):
                raise ValueError("BMI dates differ from explicit origin/timestamp mapping")
            grid = model.get_var_grid(port.name)
            if (
                model.get_grid_type(grid) != "scalar"
                or model.get_grid_rank(grid) != 0
                or model.get_grid_size(grid) != 1
                or model.get_var_type(port.name) != "float64"
                or model.get_var_units(port.name) != port.units
            ):
                raise ValueError("BMI dtype, grid or units differ from declared scalar profile")
        times = np.asarray([
            model.get_start_time(), model.get_current_time(),
            model.get_end_time(), model.get_time_step(),
        ], dtype=float)
        if (
            not np.isfinite(times).all()
            or not np.array_equal(times, [0.0, 0.0, float(count), 1.0])
            or model.get_time_units() != "d"
        ):
            raise ValueError("BMI profile requires start=current=0, end=count, step=1, units=d")

    def train(self, handle: BmiHandle, fitting_data: Mapping[str, np.ndarray]) -> TrainingResult:
        if fitting_data:
            raise ValueError("BMI profile does not support training")
        return TrainingResult("not_applicable", None, None)

    def run(
        self, handle: BmiHandle, forcing: Mapping[str, np.ndarray]
    ) -> Mapping[str, np.ndarray]:
        if handle.consumed:
            raise ValueError("BMI attempt cannot restart or run twice")
        self.validate(handle)
        snapshot, model = handle.context.model, handle.model
        inputs = validate_arrays(forcing, snapshot.inputs, snapshot.inputs)
        count = len(snapshot.outputs[0].time.dates)
        outputs = {p.name: np.empty(count, dtype=np.float64) for p in snapshot.outputs}
        handle.consumed = True
        for row in range(count):
            if model.get_current_time() != float(row):
                raise ValueError("BMI time changed outside the declared stepping sequence")
            for name, values in inputs.items():
                model.set_value(name, np.array([values[row]], dtype=np.float64))
            model.update()
            if model.get_current_time() != float(row + 1):
                raise ValueError("BMI did not advance exactly one day")
            for name, values in outputs.items():
                value = np.asarray(model.get_value_ptr(name))
                if value.shape != (1,) or value.dtype != np.dtype("float64"):
                    raise ValueError("BMI output must be a scalar float64 exchange buffer")
                if not np.isfinite(value).all():
                    raise ValueError("BMI output is nonfinite")
                values[row] = value[0]
        return validate_arrays(outputs, snapshot.outputs, snapshot.outputs)

    def inspect(
        self, handle: BmiHandle, outputs: Mapping[str, np.ndarray]
    ) -> Mapping[str, np.ndarray]:
        return validate_arrays(outputs, handle.context.model.outputs, handle.context.model.outputs)

    def cleanup(self, handle: BmiHandle | None) -> None:
        if handle is None or handle.finalized:
            return
        handle.finalized = True
        try:
            handle.model.finalize()
        except Exception as error:
            handle.cleanup_errors.append(f"{type(error).__name__}: {error}")
            raise
