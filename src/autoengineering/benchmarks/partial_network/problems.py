"""Deterministic function networks for the Item 9 comparison."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

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
class PartialNetworkProblem:
    """One deterministic benchmark with analytic system and component truth."""

    name: str
    system: System
    network: FunctionNetworkSpec
    space: SearchSpace
    source_arrays: Mapping[str, np.ndarray]
    runner: Callable
    analytic: Callable[[Mapping[str, object]], Mapping[str, float]]
    component_truth: Callable[
        [str, Mapping[str, object], Mapping[str, object]], Mapping[str, float]
    ]

    def study(self, seed: int, backend: str) -> StudySpec:
        return StudySpec(
            name=f"partial-network-{self.name}-{seed}-{backend}",
            objective=ObjectiveSpec("utility", "maximize"),
            constraints=tuple(
                ConstraintSpec(item.outcome, item.operator, item.threshold)
                for item in self.network.constraints
            ),
            budget=BudgetSpec(8.0, "evaluation", max_evaluations=12),
            noise=NoiseSpec("deterministic", 1e-6),
            backend=backend,
            seed=40_000 + seed,
        )

    @property
    def alternatives(self) -> Mapping[str, Mapping[str, object]]:
        return MappingProxyType(
            {
                component.component: MappingProxyType(
                    {"base": self.system.get_component(component.component)}
                )
                for component in self.network.components
                if any(parameter.name == "choice" for parameter in component.parameters)
            }
        )

    def feasible(self, outcomes: Mapping[str, float]) -> bool:
        return all(
            outcomes[item.outcome] >= item.threshold
            if item.operator == ">="
            else outcomes[item.outcome] <= item.threshold
            for item in self.network.constraints
        )

    @staticmethod
    def normalized_regret(best: float | None) -> float:
        return 1.0 if best is None else float(np.clip(1.0 - best, 0.0, 1.0))

    def expected_cost(self, component: str | None) -> float:
        if component is None:
            return float(sum(item.expected_cost for item in self.network.components))
        return float(self.network.component_map[component].expected_cost)


def _port(name: str, direction: str, units: str = "unit") -> FunctionPortSpec:
    return FunctionPortSpec(name, direction, "scalar", units)


def _parameters(name: str) -> tuple[object, ...]:
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


def _frozen_array(values) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    result.setflags(write=False)
    return result


def _global_space(network: FunctionNetworkSpec) -> SearchSpace:
    parameters = []
    for component in network.components:
        prefix = f"{component.component}."
        for parameter in component.parameters:
            data = parameter.to_dict()
            data["name"] = prefix + parameter.name
            parameters.append(
                CategoricalParameter.from_dict(data)
                if data["type"] == "categorical"
                else ContinuousParameter.from_dict(data)
            )
    return SearchSpace(tuple(parameters))


def _source(system: System):
    source = system.add_component("source", outputs={"driver": "scalar"})
    _set_units(source, outputs=("unit",))
    return source


def _informative_chain() -> PartialNetworkProblem:
    system = System("informative-chain")
    _source(system)
    upstream = system.add_component(
        "upstream",
        inputs={"driver": "scalar"},
        outputs={"signal": "scalar"},
        metadata=_runnable(
            "autoengineering.benchmarks.partial_network.problems:_chain_upstream",
            ["driver"],
            ["signal"],
            {"x": 0.5},
        ),
    )
    _set_units(upstream, inputs=("unit",), outputs=("unit",))
    terminal = system.add_component(
        "terminal",
        inputs={"signal": "scalar"},
        outputs={"utility": "scalar"},
        metadata=_runnable(
            "autoengineering.benchmarks.partial_network.problems:_chain_terminal",
            ["signal"],
            ["utility"],
            {"y": 0.3},
        ),
    )
    _set_units(terminal, inputs=("unit",), outputs=("point",))
    system.connect("source", "upstream", "driver", "driver")
    system.connect("upstream", "terminal", "signal", "signal")
    both = (EvaluationScope.SYSTEM, EvaluationScope.COMPONENT)
    network = FunctionNetworkSpec(
        name="informative-chain",
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
                "upstream",
                "autoengineering.benchmarks.partial_network.problems:_chain_upstream",
                _parameters("x"),
                (_port("driver", "in"),),
                (_port("signal", "out"),),
                (ScalarOutputSpec("signal", "signal", "last", both),),
                0.2,
                "evaluation",
                both,
            ),
            FunctionComponentSpec(
                "terminal",
                "autoengineering.benchmarks.partial_network.problems:_chain_terminal",
                _parameters("y"),
                (_port("signal", "in"),),
                (_port("utility", "out", "point"),),
                (ScalarOutputSpec("utility", "utility", "last", both),),
                0.8,
                "evaluation",
                both,
            ),
        ),
        couplings=(
            CouplingSpec("source", "driver", "upstream", "driver"),
            CouplingSpec("upstream", "signal", "terminal", "signal"),
        ),
        objective=TerminalObjectiveSpec("utility", "terminal", "utility", "maximize"),
        constraints=(
            TerminalConstraintSpec("minimum_signal", "upstream", "signal", ">=", 0.4),
        ),
        evaluation_scopes=both,
    )
    return PartialNetworkProblem(
        "informative_chain",
        system,
        network,
        _global_space(network),
        MappingProxyType({"source.driver": _frozen_array([1.0])}),
        _benchmark_runner,
        _chain_analytic,
        _chain_component_truth,
    )


def _informative_branch() -> PartialNetworkProblem:
    system = System("informative-branch")
    _source(system)
    for name, parameter, function in (
        ("left", "x", "_branch_left"),
        ("right", "y", "_branch_right"),
    ):
        component = system.add_component(
            name,
            inputs={"driver": "scalar"},
            outputs={f"{name}_value": "scalar"},
            metadata=_runnable(
                f"autoengineering.benchmarks.partial_network.problems:{function}",
                ["driver"],
                [f"{name}_value"],
                {parameter: 0.5},
            ),
        )
        _set_units(component, inputs=("unit",), outputs=("unit",))
        system.connect("source", name, "driver", "driver")
    terminal = system.add_component(
        "terminal",
        inputs={"left_value": "scalar", "right_value": "scalar"},
        outputs={"utility": "scalar", "balance": "scalar"},
        metadata=_runnable(
            "autoengineering.benchmarks.partial_network.problems:_branch_terminal",
            ["left_value", "right_value"],
            ["utility", "balance"],
            {"z": 0.25},
        ),
    )
    _set_units(terminal, inputs=("unit", "unit"), outputs=("point", "unit"))
    system.connect("left", "terminal", "left_value", "left_value")
    system.connect("right", "terminal", "right_value", "right_value")
    both = (EvaluationScope.SYSTEM, EvaluationScope.COMPONENT)
    source_spec = FunctionComponentSpec(
        "source",
        None,
        (),
        (),
        (_port("driver", "out"),),
        (ScalarOutputSpec("driver", "driver", "last", (EvaluationScope.SYSTEM,)),),
        0.0,
        "evaluation",
        (EvaluationScope.SYSTEM,),
    )
    branch_specs = tuple(
        FunctionComponentSpec(
            name,
            f"autoengineering.benchmarks.partial_network.problems:_branch_{name}",
            _parameters(parameter),
            (_port("driver", "in"),),
            (_port(f"{name}_value", "out"),),
            (ScalarOutputSpec(f"{name}_value", f"{name}_value", "last", both),),
            0.15,
            "evaluation",
            both,
        )
        for name, parameter in (("left", "x"), ("right", "y"))
    )
    terminal_spec = FunctionComponentSpec(
        "terminal",
        "autoengineering.benchmarks.partial_network.problems:_branch_terminal",
        _parameters("z"),
        (_port("left_value", "in"), _port("right_value", "in")),
        (_port("utility", "out", "point"), _port("balance", "out")),
        (
            ScalarOutputSpec("utility", "utility", "last", both),
            ScalarOutputSpec("balance", "balance", "last", both),
        ),
        0.70,
        "evaluation",
        both,
    )
    network = FunctionNetworkSpec(
        name="informative-branch",
        components=(source_spec, *branch_specs, terminal_spec),
        couplings=(
            CouplingSpec("source", "driver", "left", "driver"),
            CouplingSpec("source", "driver", "right", "driver"),
            CouplingSpec("left", "left_value", "terminal", "left_value"),
            CouplingSpec("right", "right_value", "terminal", "right_value"),
        ),
        objective=TerminalObjectiveSpec("utility", "terminal", "utility", "maximize"),
        constraints=(
            TerminalConstraintSpec("balance", "terminal", "balance", ">=", 0.65),
        ),
        evaluation_scopes=both,
    )
    return PartialNetworkProblem(
        "informative_branch",
        system,
        network,
        _global_space(network),
        MappingProxyType({"source.driver": _frozen_array([1.0])}),
        _benchmark_runner,
        _branch_analytic,
        _branch_component_truth,
    )


def _chain_upstream(component, inputs):
    x = float(component.metadata["runnable"]["params"]["x"])
    return {"signal": np.sin(np.pi * x) * np.ones_like(inputs["driver"], dtype=float)}


def _chain_terminal(component, inputs):
    y = float(component.metadata["runnable"]["params"]["y"])
    signal = np.asarray(inputs["signal"], dtype=float)
    return {"utility": 1.0 - (signal - 0.8) ** 2 - 0.2 * (y - 0.3) ** 2}


def _branch_left(component, inputs):
    x = float(component.metadata["runnable"]["params"]["x"])
    return {"left_value": x * np.ones_like(inputs["driver"], dtype=float)}


def _branch_right(component, inputs):
    y = float(component.metadata["runnable"]["params"]["y"])
    return {"right_value": y * np.ones_like(inputs["driver"], dtype=float)}


def _branch_terminal(component, inputs):
    z = float(component.metadata["runnable"]["params"]["z"])
    left = np.asarray(inputs["left_value"], dtype=float)
    right = np.asarray(inputs["right_value"], dtype=float)
    utility = 1.0 - (left - 0.65) ** 2 - 0.02 * (right - 0.5) ** 2 - 0.2 * (z - 0.25) ** 2
    return {"utility": utility, "balance": left + 0.1 * right}


def _benchmark_runner(component, inputs):
    functions = {
        "upstream": _chain_upstream,
        "left": _branch_left,
        "right": _branch_right,
        "terminal": _chain_terminal if "signal" in inputs else _branch_terminal,
    }
    return functions[component.name](component, inputs)


def _chain_analytic(config: Mapping[str, object]) -> Mapping[str, float]:
    signal = float(np.sin(np.pi * float(config["upstream.x"])))
    utility = 1.0 - (signal - 0.8) ** 2 - 0.2 * (float(config["terminal.y"]) - 0.3) ** 2
    return MappingProxyType({"utility": utility, "minimum_signal": signal})


def _chain_component_truth(component, local, parent):
    if component == "upstream":
        signal = float(np.sin(np.pi * float(local["upstream.x"])))
        return MappingProxyType({"upstream.signal": signal})
    signal = float(np.sin(np.pi * float(parent["upstream.x"])))
    utility = 1.0 - (signal - 0.8) ** 2 - 0.2 * (float(local["terminal.y"]) - 0.3) ** 2
    return MappingProxyType({"terminal.utility": utility})


def _branch_analytic(config: Mapping[str, object]) -> Mapping[str, float]:
    left = float(config["left.x"])
    right = float(config["right.y"])
    z = float(config["terminal.z"])
    utility = 1.0 - (left - 0.65) ** 2 - 0.02 * (right - 0.5) ** 2 - 0.2 * (z - 0.25) ** 2
    return MappingProxyType({"utility": utility, "balance": left + 0.1 * right})


def _branch_component_truth(component, local, parent):
    if component == "left":
        return MappingProxyType({"left.left_value": float(local["left.x"])})
    if component == "right":
        return MappingProxyType({"right.right_value": float(local["right.y"])})
    truth = _branch_analytic({**parent, **local})
    return MappingProxyType(
        {"terminal.utility": truth["utility"], "terminal.balance": truth["balance"]}
    )


_PROBLEMS = (_informative_chain(), _informative_branch())


def benchmark_problems() -> tuple[PartialNetworkProblem, ...]:
    return _PROBLEMS


def problem_by_name(name: str) -> PartialNetworkProblem:
    for problem in _PROBLEMS:
        if problem.name == name:
            return problem
    raise KeyError(name)
