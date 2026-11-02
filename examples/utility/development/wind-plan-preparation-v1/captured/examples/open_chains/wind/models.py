"""DTU Horns Rev engineering wake model and TOPFARM layout optimization."""

from __future__ import annotations

import numpy as np
from py_wake import NOJ
from py_wake.examples.data.hornsrev1 import Hornsrev1Site, V80


def layout(
    x: np.ndarray, y: np.ndarray, method: str = "original", maxiter: int = 20
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if method == "original":
        return x.copy(), y.copy(), np.array([0, 0, 0])
    if method != "topfarm":
        raise ValueError(f"Unknown layout method: {method}")
    from topfarm import TopFarmProblem
    from topfarm.constraint_components.boundary import XYBoundaryConstraint
    from topfarm.constraint_components.spacing import SpacingConstraint
    from topfarm.cost_models.py_wake_wrapper import PyWakeAEPCostModelComponent
    from topfarm.easy_drivers import EasyScipyOptimizeDriver

    boundary = np.array(
        [[x.min(), y.min()], [x.max(), y.min()], [x.max(), y.max()], [x.min(), y.max()]]
    )
    cost = PyWakeAEPCostModelComponent(
        NOJ(Hornsrev1Site(), V80()),
        len(x),
        wd=np.arange(0, 360, 30),
        ws=np.arange(4, 26, 2),
        n_cpu=1,
    )
    problem = TopFarmProblem(
        design_vars={"x": x.copy(), "y": y.copy()},
        cost_comp=cost,
        driver=EasyScipyOptimizeDriver(maxiter=maxiter, tol=1e-6, disp=False),
        constraints=[XYBoundaryConstraint(boundary, "polygon"), SpacingConstraint(4 * 80)],
        expected_cost=1,
        reports=False,
    )
    _, state, _ = problem.optimize()
    return (
        np.asarray(state["x"]),
        np.asarray(state["y"]),
        np.array([1 if problem.driver.result.success else 2, cost.n_func_eval, cost.n_grad_eval]),
    )


def wakes(x: np.ndarray, y: np.ndarray, direction_step: int = 30) -> tuple[np.ndarray, np.ndarray]:
    result = NOJ(Hornsrev1Site(), V80())(
        x,
        y,
        wd=np.arange(0, 360, direction_step),
        ws=np.arange(4, 26, 2),
    )
    return result.aep().values, result.Power.values


def annual_energy(aep_gwh: np.ndarray) -> np.ndarray:
    return np.array([np.sum(aep_gwh)])


def feasible(x: np.ndarray, y: np.ndarray, initial_x: np.ndarray, initial_y: np.ndarray) -> None:
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Nonfinite turbine coordinates")
    if len(x) != len(initial_x) or len(y) != len(initial_y):
        raise ValueError("Turbine count changed")
    tolerance = 1e-3
    for values, original in [(x, initial_x), (y, initial_y)]:
        if values.min() < original.min() - tolerance or values.max() > original.max() + tolerance:
            raise ValueError("Layout outside declared rectangle")
    distance = np.hypot(x[:, None] - x, y[:, None] - y)
    np.fill_diagonal(distance, np.inf)
    if distance.min() < 320 - tolerance:
        raise ValueError("Turbine separation below four rotor diameters")
