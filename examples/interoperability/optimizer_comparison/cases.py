"""Frozen analytic comparison tasks, without external scientific data."""
from autoengineering.optimization.space import (
    CategoricalParameter, ContinuousParameter, IntegerParameter, SearchSpace,
)
from .branches import BranchMapping


def case(name):
    parameters = [ContinuousParameter("x", 0., 1.), ContinuousParameter("y", 0., 1.)]
    defaults = {}
    if name == "mixed":
        parameters += [IntegerParameter("n", 1, 4),
                       CategoricalParameter("family", ("linear", "quadratic"))]
    elif name == "conditional":
        parameters += [
            CategoricalParameter("family", ("linear", "quadratic")),
            ContinuousParameter("linear_curvature", 0., 1., active_when={"family": ("linear",)}),
            ContinuousParameter("quadratic_slope", 0., 1., active_when={"family": ("quadratic",)}),
        ]
        defaults = {"linear_curvature": 0., "quadratic_slope": 0.}
    elif name != "continuous":
        raise ValueError("unknown comparison case")
    return BranchMapping(SearchSpace(tuple(parameters)), defaults)


def evaluate(config, index):
    """One injected model failure at the same physical ordinal for every route."""
    if index == 1:
        return {"status": "model_failure", "feasible": False, "objective": None,
                "reason": "frozen_failure_control"}
    feasible = config["x"] + config["y"] <= 1.
    value = (config["x"] - .2) ** 2 + (config["y"] - .3) ** 2
    value += .01 * (config.get("n", 2) - 2) ** 2
    if "family" in config:
        value += .01 if config["family"] == "linear" else 0.
    for name in ("linear_curvature", "quadratic_slope"):
        if name in config:
            value += .1 * (config[name] - .4) ** 2
    return {"status": "success" if feasible else "scientific_infeasible",
            "feasible": feasible, "objective": value if feasible else None,
            "constraint_residual": config["x"] + config["y"] - 1.}
