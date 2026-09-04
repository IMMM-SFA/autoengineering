"""Deterministic scalar-output networks for the Item 8 comparison."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Mapping

import numpy as np

from autoengineering.optimization import (
    BudgetSpec,
    CategoricalParameter,
    ConstraintSpec,
    ContinuousParameter,
    CouplingSpec,
    EvaluationScope,
    FunctionComponentSpec,
    FunctionNetworkSpec,
    FunctionPortSpec,
    NoiseSpec,
    ObjectiveSpec,
    ScalarOutputSpec,
    SearchSpace,
    StudySpec,
    TerminalConstraintSpec,
    TerminalObjectiveSpec,
)
from autoengineering.system.graph import System


@dataclass(frozen=True)
class FullNetworkProblem:
    """One benchmark network with an analytic deterministic evaluator."""

    name: str
    system: System
    network: FunctionNetworkSpec
    space: SearchSpace
    source_arrays: Mapping[str, np.ndarray]
    runner: Callable
    analytic: Callable[[Mapping[str, object]], Mapping[str, float]]
    optimum: float
    regret_scale: float

    def study(self, seed: int, backend: str) -> StudySpec:
        return StudySpec(
            name=f"full-network-{self.name}-{seed}-{backend}",
            objective=ObjectiveSpec(
                self.network.objective.outcome, self.network.objective.direction
            ),
            constraints=tuple(
                ConstraintSpec(item.outcome, item.operator, item.threshold)
                for item in self.network.constraints
            ),
            budget=BudgetSpec(10.0, "evaluation", max_evaluations=10),
            noise=NoiseSpec("deterministic", 1e-6),
            backend=backend,
            seed=10_000 + seed,
        )

    @property
    def alternatives(self) -> Mapping[str, Mapping[str, object]]:
        choices = {}
        for component in self.network.components:
            if any(parameter.name == "choice" for parameter in component.parameters):
                choices[component.component] = MappingProxyType(
                    {"base": self.system.get_component(component.component)}
                )
        return MappingProxyType(choices)

    def normalized_regret(self, best: float | None) -> float:
        if best is None:
            return 1.0
        return float(np.clip((self.optimum - best) / self.regret_scale, 0.0, 1.0))

    def feasible(self, outcomes: Mapping[str, float]) -> bool:
        return all(
            outcomes[item.outcome] >= item.threshold
            if item.operator == ">="
            else outcomes[item.outcome] <= item.threshold
            for item in self.network.constraints
        )


def _port(name: str, direction: str, units: str = "unit") -> FunctionPortSpec:
    return FunctionPortSpec(name, direction, "scalar", units)


def _choice_and(name: str) -> tuple[object, ...]:
    return (
        CategoricalParameter("choice", ("base",)),
        ContinuousParameter(name, 0.0, 1.0),
    )


def _runnable(entry: str, inputs: list[str], outputs: list[str], params: dict) -> dict:
    return {
        "runnable": {
            "kind": "python",
            "entry": entry,
            "inputs": inputs,
            "outputs": outputs,
            "params": params,
        }
    }


def _set_units(component, *, inputs=(), outputs=()) -> None:
    for port, units in zip(component.inputs, inputs, strict=True):
        port.units = units
    for port, units in zip(component.outputs, outputs, strict=True):
        port.units = units


def _smooth_chain() -> FullNetworkProblem:
    system = System("smooth-chain")
    source = system.add_component("source", outputs={"driver": "scalar"})
    _set_units(source, outputs=("unit",))
    warp = system.add_component(
        "warp",
        inputs={"driver": "scalar"},
        outputs={"latent": "scalar"},
        metadata=_runnable(
            "autoengineering.benchmarks.full_network.problems:_smooth_warp",
            ["driver"],
            ["latent"],
            {"x": 0.5},
        ),
    )
    _set_units(warp, inputs=("unit",), outputs=("unit",))
    terminal = system.add_component(
        "terminal",
        inputs={"latent": "scalar"},
        outputs={"utility_series": "scalar"},
        metadata=_runnable(
            "autoengineering.benchmarks.full_network.problems:_smooth_terminal",
            ["latent"],
            ["utility_series"],
            {"y": 0.3},
        ),
    )
    _set_units(terminal, inputs=("unit",), outputs=("point",))
    system.connect("source", "warp", "driver", "driver")
    system.connect("warp", "terminal", "latent", "latent")
    both = (EvaluationScope.SYSTEM, EvaluationScope.COMPONENT)
    network = FunctionNetworkSpec(
        name="smooth-chain",
        components=(
            FunctionComponentSpec(
                "source",
                None,
                (),
                (),
                (_port("driver", "out"),),
                (ScalarOutputSpec("driver", "driver", "last", (EvaluationScope.SYSTEM,)),),
                0.0,
                "evaluation",
                (EvaluationScope.SYSTEM,),
            ),
            FunctionComponentSpec(
                "warp",
                "autoengineering.benchmarks.full_network.problems:_smooth_warp",
                _choice_and("x"),
                (_port("driver", "in"),),
                (_port("latent", "out"),),
                (ScalarOutputSpec("latent", "latent", "last", both),),
                0.45,
                "evaluation",
                both,
            ),
            FunctionComponentSpec(
                "terminal",
                "autoengineering.benchmarks.full_network.problems:_smooth_terminal",
                _choice_and("y"),
                (_port("latent", "in"),),
                (_port("utility_series", "out", "point"),),
                (ScalarOutputSpec("utility", "utility_series", "last", both),),
                0.55,
                "evaluation",
                both,
            ),
        ),
        couplings=(
            CouplingSpec("source", "driver", "warp", "driver"),
            CouplingSpec("warp", "latent", "terminal", "latent"),
        ),
        objective=TerminalObjectiveSpec("utility", "terminal", "utility", "maximize"),
        constraints=(),
        evaluation_scopes=both,
    )
    space = _global_space(network)
    return FullNetworkProblem(
        "smooth_chain",
        system,
        network,
        space,
        MappingProxyType({"source.driver": _frozen_array([1.0])}),
        _benchmark_runner,
        _smooth_analytic,
        1.0,
        1.0,
    )


def _constrained_branch() -> FullNetworkProblem:
    system = System("constrained-branch")
    source = system.add_component("source", outputs={"driver": "scalar"})
    _set_units(source, outputs=("unit",))
    left = system.add_component(
        "left",
        inputs={"driver": "scalar"},
        outputs={"left_signal": "scalar"},
        metadata=_runnable(
            "autoengineering.benchmarks.full_network.problems:_left_branch",
            ["driver"],
            ["left_signal"],
            {"x": 0.5},
        ),
    )
    _set_units(left, inputs=("unit",), outputs=("unit",))
    right = system.add_component(
        "right",
        inputs={"driver": "scalar"},
        outputs={"right_signal": "scalar"},
        metadata=_runnable(
            "autoengineering.benchmarks.full_network.problems:_right_branch",
            ["driver"],
            ["right_signal"],
            {"y": 0.5},
        ),
    )
    _set_units(right, inputs=("unit",), outputs=("unit",))
    terminal = system.add_component(
        "terminal",
        inputs={"left_signal": "scalar", "right_signal": "scalar"},
        outputs={"utility_series": "scalar", "balance_series": "scalar"},
        metadata=_runnable(
            "autoengineering.benchmarks.full_network.problems:_branch_terminal",
            ["left_signal", "right_signal"],
            ["utility_series", "balance_series"],
            {},
        ),
    )
    _set_units(terminal, inputs=("unit", "unit"), outputs=("point", "unit"))
    system.connect("source", "left", "driver", "driver")
    system.connect("source", "right", "driver", "driver")
    system.connect("left", "terminal", "left_signal", "left_signal")
    system.connect("right", "terminal", "right_signal", "right_signal")
    both = (EvaluationScope.SYSTEM, EvaluationScope.COMPONENT)
    network = FunctionNetworkSpec(
        name="constrained-branch",
        components=(
            FunctionComponentSpec(
                "source",
                None,
                (),
                (),
                (_port("driver", "out"),),
                (ScalarOutputSpec("driver", "driver", "last", (EvaluationScope.SYSTEM,)),),
                0.0,
                "evaluation",
                (EvaluationScope.SYSTEM,),
            ),
            FunctionComponentSpec(
                "left",
                "autoengineering.benchmarks.full_network.problems:_left_branch",
                _choice_and("x"),
                (_port("driver", "in"),),
                (_port("left_signal", "out"),),
                (ScalarOutputSpec("left_signal", "left_signal", "last", both),),
                0.3,
                "evaluation",
                both,
            ),
            FunctionComponentSpec(
                "right",
                "autoengineering.benchmarks.full_network.problems:_right_branch",
                _choice_and("y"),
                (_port("driver", "in"),),
                (_port("right_signal", "out"),),
                (ScalarOutputSpec("right_signal", "right_signal", "last", both),),
                0.3,
                "evaluation",
                both,
            ),
            FunctionComponentSpec(
                "terminal",
                "autoengineering.benchmarks.full_network.problems:_branch_terminal",
                (),
                (_port("left_signal", "in"), _port("right_signal", "in")),
                (
                    _port("utility_series", "out", "point"),
                    _port("balance_series", "out"),
                ),
                (
                    ScalarOutputSpec("utility", "utility_series", "last", both),
                    ScalarOutputSpec("balance", "balance_series", "last", both),
                ),
                0.4,
                "evaluation",
                both,
            ),
        ),
        couplings=(
            CouplingSpec("source", "driver", "left", "driver"),
            CouplingSpec("source", "driver", "right", "driver"),
            CouplingSpec("left", "left_signal", "terminal", "left_signal"),
            CouplingSpec("right", "right_signal", "terminal", "right_signal"),
        ),
        objective=TerminalObjectiveSpec("utility", "terminal", "utility", "maximize"),
        constraints=(TerminalConstraintSpec("balance", "terminal", "balance", ">=", 0.8),),
        evaluation_scopes=both,
    )
    return FullNetworkProblem(
        "constrained_branch",
        system,
        network,
        _global_space(network),
        MappingProxyType({"source.driver": _frozen_array([1.0])}),
        _benchmark_runner,
        _branch_analytic,
        1.0,
        1.0,
    )


def _global_space(network: FunctionNetworkSpec) -> SearchSpace:
    parameters = []
    for component in network.components:
        prefix = f"{component.component}."
        for parameter in component.parameters:
            if isinstance(parameter, CategoricalParameter):
                parameters.append(
                    CategoricalParameter(prefix + parameter.name, parameter.categories)
                )
            else:
                parameters.append(
                    ContinuousParameter(
                        prefix + parameter.name,
                        parameter.lower,
                        parameter.upper,
                        parameter.scale,
                        {prefix + name: values for name, values in parameter.active_when.items()},
                    )
                )
    return SearchSpace(tuple(parameters))


def _frozen_array(values) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    result.setflags(write=False)
    return result


def _benchmark_runner(component, inputs):
    params = component.metadata["runnable"]["params"]
    if component.name == "warp":
        return {"latent": _smooth_warp(inputs["driver"], **params)}
    if component.name == "left":
        return {"left_signal": _left_branch(inputs["driver"], **params)}
    if component.name == "right":
        return {"right_signal": _right_branch(inputs["driver"], **params)}
    if component.name == "terminal" and "latent" in inputs:
        return {"utility_series": _smooth_terminal(inputs["latent"], **params)}
    utility, balance = _branch_terminal(inputs["left_signal"], inputs["right_signal"], **params)
    return {"utility_series": utility, "balance_series": balance}


def _smooth_warp(driver, x=0.5):
    return np.asarray(driver) * np.sin(np.pi * x)


def _smooth_terminal(latent, y=0.3):
    latent = np.asarray(latent)
    return 1.0 - (latent - 0.7) ** 2 - (y - 0.3) ** 2


def _left_branch(driver, x=0.5):
    return np.asarray(driver) * x


def _right_branch(driver, y=0.5):
    return np.asarray(driver) * y**2


def _branch_terminal(left_signal, right_signal):
    left_signal = np.asarray(left_signal)
    right_signal = np.asarray(right_signal)
    utility = 1.0 - (left_signal - 0.7) ** 2 - (right_signal - 0.25) ** 2
    return utility, left_signal + right_signal


def _smooth_analytic(config: Mapping[str, object]) -> Mapping[str, float]:
    x = float(config["warp.x"])
    y = float(config["terminal.y"])
    latent = math_sin_pi(x)
    return MappingProxyType({"utility": 1.0 - (latent - 0.7) ** 2 - (y - 0.3) ** 2})


def _branch_analytic(config: Mapping[str, object]) -> Mapping[str, float]:
    left = float(config["left.x"])
    right = float(config["right.y"]) ** 2
    return MappingProxyType(
        {
            "utility": 1.0 - (left - 0.7) ** 2 - (right - 0.25) ** 2,
            "balance": left + right,
        }
    )


def math_sin_pi(value: float) -> float:
    return float(np.sin(np.pi * value))


def benchmark_problems() -> tuple[FullNetworkProblem, ...]:
    """Return the frozen problem order."""
    problems = (_smooth_chain(), _constrained_branch())
    for problem in problems:
        problem.network.validate(problem.system)
    return problems


def problem_by_name(name: str) -> FullNetworkProblem:
    """Return one frozen problem by its evidence name."""
    for problem in benchmark_problems():
        if problem.name == name:
            return problem
    raise ValueError(f"unknown full-network benchmark problem: {name!r}")
