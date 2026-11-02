"""Bounded native TOPFARM selection with exclusive wake and derivative receipts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from autoengineering.campaign.serialization import Record
from examples.utility.wind import WindTask


@dataclass(frozen=True)
class NativeCall(Record):
    kind: Literal["wake", "gradient"]
    index: int
    status: Literal["started", "completed", "failed"]
    x: tuple[float, ...]
    y: tuple[float, ...]
    energy_gwh: float | None

    def _validate(self):
        if self.index < 1 or len(self.x) < 2 or len(self.x) != len(self.y):
            raise ValueError("invalid native call index or coordinates")
        if (self.kind == "wake" and self.status == "completed") != (self.energy_gwh is not None):
            raise ValueError("energy must belong to a completed wake call")


@dataclass(frozen=True)
class NativeWindResult(Record):
    status: Literal["converged", "not_converged", "budget_exhausted", "failed"]
    driver_success: bool | None
    feasible: bool
    x: tuple[float, ...]
    y: tuple[float, ...]
    calls: tuple[NativeCall, ...]
    maximum_wake_calls: int
    maximum_gradient_calls: int
    maximum_iterations: int

    def _validate(self):
        if (
            len(self.x) < 2
            or len(self.x) != len(self.y)
            or min(self.maximum_wake_calls, self.maximum_gradient_calls, self.maximum_iterations)
            < 1
        ):
            raise ValueError("invalid native result coordinates or limits")
        for kind, maximum in (
            ("wake", self.maximum_wake_calls),
            ("gradient", self.maximum_gradient_calls),
        ):
            calls = [c for c in self.calls if c.kind == kind]
            if len(calls) > maximum or [c.index for c in calls] != list(range(1, len(calls) + 1)):
                raise ValueError("native receipts exceed limits or contain conflicting indices")
        if self.status == "converged" and self.driver_success is not True:
            raise ValueError("converged native result needs driver success")


def native_layout(initial, *, max_iterations, max_wake_calls, max_gradient_calls, resource=None):
    """Keep the native driver/derivatives and count before invoking each callback.

    Iteration caps are not wake-call caps. Rejected work does not start. Returned
    failed/budget records retain all work already attempted. Every result still
    requires separate final-layout evaluation under a reserved physical budget.
    """
    for cap in (max_iterations, max_wake_calls, max_gradient_calls):
        if type(cap) is not int or cap < 1:
            raise ValueError("native wind limits must be positive integer counts")
    if resource is not None:
        from examples.utility.wind_resource import WindResource

        if not isinstance(resource, WindResource):
            raise ValueError("native wind requires a validated explicit resource")
    step = 30 if resource is None else resource.direction_step
    task = WindTask({"baseline": initial}, initial, direction_step=step)
    task.validate({"layout_id": "baseline"})
    x, y = task.baseline
    from py_wake import NOJ
    from py_wake.examples.data.hornsrev1 import Hornsrev1Site, V80
    from topfarm import TopFarmProblem
    from topfarm.constraint_components.boundary import XYBoundaryConstraint
    from topfarm.constraint_components.spacing import SpacingConstraint
    from topfarm.cost_models.py_wake_wrapper import PyWakeAEPCostModelComponent
    from topfarm.easy_drivers import EasyScipyOptimizeDriver

    if resource is None:
        model, directions, speeds = (
            NOJ(Hornsrev1Site(), V80()),
            np.arange(0, 360, 30),
            np.arange(4, 26, 2),
        )
    else:
        model, directions, speeds = (
            resource.wake_model(),
            resource.directions_deg,
            resource.speeds_m_s,
        )
    cost = PyWakeAEPCostModelComponent(model, len(x), wd=directions, ws=speeds, n_cpu=1)
    calls, exhausted = [], False

    def bounded(function, kind, maximum):
        def invoke(**kwargs):
            nonlocal exhausted
            count = sum(c.kind == kind for c in calls)
            if count >= maximum:
                exhausted = True
                raise RuntimeError("native wind physical allowance exhausted")
            index = len(calls)
            record = NativeCall(
                kind,
                count + 1,
                "started",
                tuple(float(v) for v in kwargs["x"]),
                tuple(float(v) for v in kwargs["y"]),
                None,
            )
            calls.append(record)
            try:
                value = function(**kwargs)
                if not np.isfinite(value).all():
                    raise ValueError("nonfinite native wake/gradient result")
                energy = float(value) if kind == "wake" else None
                calls[index] = NativeCall(kind, count + 1, "completed", record.x, record.y, energy)
                return value
            except BaseException:
                calls[index] = NativeCall(kind, count + 1, "failed", record.x, record.y, None)
                raise

        return invoke

    cost.cost_function = bounded(cost.cost_function, "wake", max_wake_calls)
    cost.cost_gradient_function = bounded(
        cost.cost_gradient_function, "gradient", max_gradient_calls
    )
    boundary = np.array(
        [[x.min(), y.min()], [x.max(), y.min()], [x.max(), y.max()], [x.min(), y.max()]]
    )
    problem = None
    final_x, final_y = x.copy(), y.copy()
    status, driver_success = "failed", None
    try:
        problem = TopFarmProblem(
            design_vars={"x": x.copy(), "y": y.copy()},
            cost_comp=cost,
            driver=EasyScipyOptimizeDriver(maxiter=max_iterations, tol=1e-6, disp=False),
            constraints=[XYBoundaryConstraint(boundary, "polygon"), SpacingConstraint(320)],
            expected_cost=1,
            reports=False,
        )
        _, state, _ = problem.optimize()
        final_x, final_y = np.asarray(state["x"]).copy(), np.asarray(state["y"]).copy()
        driver_success = bool(problem.driver.result.success)
        status = "converged" if driver_success else "not_converged"
    except Exception:
        status = "budget_exhausted" if exhausted else "failed"
    finally:
        if problem is not None:
            problem.cleanup()
    feasible = False
    if status in ("converged", "not_converged"):
        try:
            WindTask({"final": (final_x, final_y)}, task.baseline, direction_step=step).validate(
                {"layout_id": "final"}
            )
            feasible = True
        except ValueError:
            pass
    return NativeWindResult(
        status,
        driver_success,
        feasible,
        tuple(float(v) for v in final_x),
        tuple(float(v) for v in final_y),
        tuple(calls),
        max_wake_calls,
        max_gradient_calls,
        max_iterations,
    )
