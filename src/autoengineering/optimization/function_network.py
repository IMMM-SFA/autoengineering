"""Immutable function-network contracts with strict ``System`` validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Literal, Mapping

import networkx as nx
import numpy as np
import yaml

from autoengineering.system.graph import System

from .records import EvaluationScope
from .space import (
    CategoricalParameter,
    ContinuousParameter,
    IntegerParameter,
    Parameter,
)
from .yaml_utils import safe_load_unique


FUNCTION_NETWORK_SCHEMA_VERSION = "1.0"
ScalarReducer = Literal["mean", "sum", "minimum", "maximum", "last"]


def _require_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_exact_keys(data: Mapping[str, Any], required: set[str], label: str) -> None:
    if not isinstance(data, Mapping):
        raise TypeError(f"{label} must be a mapping")
    if set(data) != required:
        raise ValueError(f"{label} keys must be exactly {sorted(required)}")


def _scopes(values: object, label: str) -> tuple[EvaluationScope, ...]:
    if isinstance(values, str) or not isinstance(values, (list, tuple)):
        raise TypeError(f"{label} must be a list or tuple")
    try:
        scopes = tuple(EvaluationScope(value) for value in values)
    except ValueError as error:
        raise ValueError(f"{label} contains an invalid evaluation scope") from error
    if not scopes:
        raise ValueError(f"{label} must not be empty")
    if len(set(scopes)) != len(scopes):
        raise ValueError(f"{label} must not contain duplicates")
    return scopes


def _finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    result = float(value)
    if result < 0:
        raise ValueError(f"{label} must be non-negative")
    return result


def _parameter_from_dict(data: object) -> Parameter:
    if not isinstance(data, Mapping):
        raise TypeError("component parameter must be a mapping")
    loaders = {
        "categorical": CategoricalParameter.from_dict,
        "continuous": ContinuousParameter.from_dict,
        "integer": IntegerParameter.from_dict,
    }
    kind = data.get("type")
    if kind not in loaders:
        raise ValueError(f"unknown component parameter type: {kind!r}")
    return loaders[kind](data)


@dataclass(frozen=True)
class FunctionPortSpec:
    """One named input or output port in a function-network component."""

    name: str
    direction: Literal["in", "out"]
    data_type: str = "any"
    units: str = ""

    def __post_init__(self) -> None:
        _require_name(self.name, "port name")
        if self.direction not in ("in", "out"):
            raise ValueError("port direction must be 'in' or 'out'")
        _require_name(self.data_type, "port data_type")
        if not isinstance(self.units, str):
            raise TypeError("port units must be a string")

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "direction": self.direction,
            "data_type": self.data_type,
            "units": self.units,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FunctionPortSpec":
        _require_exact_keys(data, {"name", "direction", "data_type", "units"}, "port")
        return cls(**data)


@dataclass(frozen=True)
class ScalarOutputSpec:
    """A scalar surrogate feature reduced from one component output port."""

    name: str
    port: str
    reducer: ScalarReducer
    observed_in: tuple[EvaluationScope, ...]

    def __post_init__(self) -> None:
        _require_name(self.name, "scalar output name")
        _require_name(self.port, "scalar output port")
        if self.reducer not in ("mean", "sum", "minimum", "maximum", "last"):
            raise ValueError("scalar output reducer is invalid")
        object.__setattr__(self, "observed_in", _scopes(self.observed_in, "observed_in"))

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "port": self.port,
            "reducer": self.reducer,
            "observed_in": [scope.value for scope in self.observed_in],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ScalarOutputSpec":
        required = {"name", "port", "reducer", "observed_in"}
        _require_exact_keys(data, required, "scalar output")
        return cls(
            name=data["name"],
            port=data["port"],
            reducer=data["reducer"],
            observed_in=data["observed_in"],
        )


@dataclass(frozen=True)
class FunctionComponentSpec:
    """A component function and its local optimization contract."""

    component: str
    entry_point: str | None
    parameters: tuple[Parameter, ...]
    inputs: tuple[FunctionPortSpec, ...]
    outputs: tuple[FunctionPortSpec, ...]
    scalar_outputs: tuple[ScalarOutputSpec, ...]
    expected_cost: float
    cost_unit: str
    evaluation_scopes: tuple[EvaluationScope, ...]

    def __post_init__(self) -> None:
        _require_name(self.component, "component name")
        if self.entry_point is not None:
            _require_name(self.entry_point, "component entry point")
            if self.entry_point.count(":") != 1:
                raise ValueError("component entry point must be a module:callable reference")
        parameters = tuple(self.parameters)
        if not all(
            isinstance(item, (CategoricalParameter, ContinuousParameter, IntegerParameter))
            for item in parameters
        ):
            raise TypeError("component parameters contain an invalid parameter")
        parameter_names = [item.name for item in parameters]
        if len(set(parameter_names)) != len(parameter_names):
            raise ValueError(f"component {self.component!r} has duplicate parameter names")
        choices = [item for item in parameters if item.name == "choice"]
        if choices and (
            not isinstance(choices[0], CategoricalParameter)
            or not all(isinstance(value, str) and value for value in choices[0].categories)
        ):
            raise ValueError("component choice must be a categorical parameter of non-empty strings")
        if any(item.name != "choice" for item in parameters) and not choices:
            raise ValueError("component design parameters require a categorical choice parameter")
        object.__setattr__(self, "parameters", parameters)

        inputs = tuple(self.inputs)
        outputs = tuple(self.outputs)
        if not all(isinstance(item, FunctionPortSpec) for item in (*inputs, *outputs)):
            raise TypeError("component ports must be FunctionPortSpec records")
        if any(item.direction != "in" for item in inputs):
            raise ValueError("component inputs must have direction 'in'")
        if any(item.direction != "out" for item in outputs):
            raise ValueError("component outputs must have direction 'out'")
        port_names = [item.name for item in (*inputs, *outputs)]
        if len(set(port_names)) != len(port_names):
            raise ValueError(f"component {self.component!r} has duplicate port names")
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "outputs", outputs)

        scalar_outputs = tuple(self.scalar_outputs)
        if not all(isinstance(item, ScalarOutputSpec) for item in scalar_outputs):
            raise TypeError("scalar_outputs must contain ScalarOutputSpec records")
        scalar_names = [item.name for item in scalar_outputs]
        if len(set(scalar_names)) != len(scalar_names):
            raise ValueError(f"component {self.component!r} has duplicate scalar output names")
        output_names = {item.name for item in outputs}
        unknown_ports = {item.port for item in scalar_outputs} - output_names
        if unknown_ports:
            raise ValueError(
                f"component {self.component!r} scalar outputs reference unknown ports: "
                f"{sorted(unknown_ports)}"
            )
        object.__setattr__(self, "scalar_outputs", scalar_outputs)
        object.__setattr__(
            self, "expected_cost", _finite_nonnegative(self.expected_cost, "expected_cost")
        )
        _require_name(self.cost_unit, "component cost_unit")
        scopes = _scopes(self.evaluation_scopes, "component evaluation_scopes")
        object.__setattr__(self, "evaluation_scopes", scopes)
        for output in scalar_outputs:
            if not set(output.observed_in).issubset(scopes):
                raise ValueError(
                    f"component {self.component!r} scalar output {output.name!r} has an "
                    "observation scope not permitted by the component"
                )

    def to_dict(self) -> dict[str, object]:
        return {
            "component": self.component,
            "entry_point": self.entry_point,
            "parameters": [item.to_dict() for item in self.parameters],
            "inputs": [item.to_dict() for item in self.inputs],
            "outputs": [item.to_dict() for item in self.outputs],
            "scalar_outputs": [item.to_dict() for item in self.scalar_outputs],
            "expected_cost": self.expected_cost,
            "cost_unit": self.cost_unit,
            "evaluation_scopes": [scope.value for scope in self.evaluation_scopes],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FunctionComponentSpec":
        required = {
            "component",
            "entry_point",
            "parameters",
            "inputs",
            "outputs",
            "scalar_outputs",
            "expected_cost",
            "cost_unit",
            "evaluation_scopes",
        }
        _require_exact_keys(data, required, "function component")
        for field_name in ("parameters", "inputs", "outputs", "scalar_outputs"):
            if not isinstance(data[field_name], list):
                raise TypeError(f"function component {field_name} must be a list")
        return cls(
            component=data["component"],
            entry_point=data["entry_point"],
            parameters=tuple(_parameter_from_dict(item) for item in data["parameters"]),
            inputs=tuple(FunctionPortSpec.from_dict(item) for item in data["inputs"]),
            outputs=tuple(FunctionPortSpec.from_dict(item) for item in data["outputs"]),
            scalar_outputs=tuple(
                ScalarOutputSpec.from_dict(item) for item in data["scalar_outputs"]
            ),
            expected_cost=data["expected_cost"],
            cost_unit=data["cost_unit"],
            evaluation_scopes=data["evaluation_scopes"],
        )


@dataclass(frozen=True)
class CouplingSpec:
    """A directed binding between one output and one input port."""

    source_component: str
    source_port: str
    target_component: str
    target_port: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.source_component, "coupling source component"),
            (self.source_port, "coupling source port"),
            (self.target_component, "coupling target component"),
            (self.target_port, "coupling target port"),
        ):
            _require_name(value, label)

    def to_dict(self) -> dict[str, str]:
        return {
            "source_component": self.source_component,
            "source_port": self.source_port,
            "target_component": self.target_component,
            "target_port": self.target_port,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CouplingSpec":
        required = {"source_component", "source_port", "target_component", "target_port"}
        _require_exact_keys(data, required, "coupling")
        return cls(**data)


@dataclass(frozen=True)
class TerminalObjectiveSpec:
    """The terminal objective derived from a system-observable scalar output."""

    outcome: str
    component: str
    scalar_output: str
    direction: Literal["maximize", "minimize"]

    def __post_init__(self) -> None:
        _require_name(self.outcome, "terminal objective outcome")
        _require_name(self.component, "terminal objective component")
        _require_name(self.scalar_output, "terminal objective scalar output")
        if self.direction not in ("maximize", "minimize"):
            raise ValueError("terminal objective direction must be 'maximize' or 'minimize'")

    def to_dict(self) -> dict[str, str]:
        return {
            "outcome": self.outcome,
            "component": self.component,
            "scalar_output": self.scalar_output,
            "direction": self.direction,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TerminalObjectiveSpec":
        required = {"outcome", "component", "scalar_output", "direction"}
        _require_exact_keys(data, required, "terminal objective")
        return cls(**data)


@dataclass(frozen=True)
class TerminalConstraintSpec:
    """A terminal threshold derived from a system-observable scalar output."""

    outcome: str
    component: str
    scalar_output: str
    operator: Literal[">=", "<="]
    threshold: float

    def __post_init__(self) -> None:
        _require_name(self.outcome, "terminal constraint outcome")
        _require_name(self.component, "terminal constraint component")
        _require_name(self.scalar_output, "terminal constraint scalar output")
        if self.operator not in (">=", "<="):
            raise ValueError("terminal constraint operator must be '>=' or '<='")
        if (
            isinstance(self.threshold, bool)
            or not isinstance(self.threshold, Real)
            or not math.isfinite(self.threshold)
        ):
            raise ValueError("terminal constraint threshold must be finite")
        object.__setattr__(self, "threshold", float(self.threshold))

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome,
            "component": self.component,
            "scalar_output": self.scalar_output,
            "operator": self.operator,
            "threshold": self.threshold,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TerminalConstraintSpec":
        required = {"outcome", "component", "scalar_output", "operator", "threshold"}
        _require_exact_keys(data, required, "terminal constraint")
        return cls(**data)


@dataclass(frozen=True)
class FunctionNetworkSpec:
    """A serializable function network kept separate from the core ``System``."""

    name: str
    components: tuple[FunctionComponentSpec, ...]
    couplings: tuple[CouplingSpec, ...]
    objective: TerminalObjectiveSpec
    constraints: tuple[TerminalConstraintSpec, ...]
    evaluation_scopes: tuple[EvaluationScope, ...]
    schema_version: str = FUNCTION_NETWORK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_name(self.name, "function network name")
        components = tuple(self.components)
        if not components or not all(isinstance(item, FunctionComponentSpec) for item in components):
            raise TypeError("components must contain FunctionComponentSpec records")
        component_names = [item.component for item in components]
        if len(set(component_names)) != len(component_names):
            raise ValueError("function network has duplicate component names")
        if len({item.cost_unit for item in components}) != 1:
            raise ValueError("function network component cost units must match")
        object.__setattr__(self, "components", components)
        couplings = tuple(self.couplings)
        if not all(isinstance(item, CouplingSpec) for item in couplings):
            raise TypeError("couplings must contain CouplingSpec records")
        coupling_keys = [
            (item.source_component, item.source_port, item.target_component, item.target_port)
            for item in couplings
        ]
        if len(set(coupling_keys)) != len(coupling_keys):
            raise ValueError("function network has duplicate couplings")
        targets = [(item.target_component, item.target_port) for item in couplings]
        if len(set(targets)) != len(targets):
            raise ValueError("a coupling input may have only one owner")
        object.__setattr__(self, "couplings", couplings)
        if not isinstance(self.objective, TerminalObjectiveSpec):
            raise TypeError("objective must be a TerminalObjectiveSpec")
        constraints = tuple(self.constraints)
        if not all(isinstance(item, TerminalConstraintSpec) for item in constraints):
            raise TypeError("constraints must contain TerminalConstraintSpec records")
        outcomes = [self.objective.outcome, *(item.outcome for item in constraints)]
        if len(set(outcomes)) != len(outcomes):
            raise ValueError("terminal outcome names must be unique")
        scalar_names = {
            scalar_observation_name(component.component, output.name)
            for component in components
            for output in component.scalar_outputs
        }
        if set(outcomes) & scalar_names:
            raise ValueError("terminal outcome names must not collide with scalar observations")
        object.__setattr__(self, "constraints", constraints)
        scopes = _scopes(self.evaluation_scopes, "network evaluation_scopes")
        if EvaluationScope.SYSTEM not in scopes:
            raise ValueError("function network must permit system evaluation")
        object.__setattr__(self, "evaluation_scopes", scopes)
        if self.schema_version != FUNCTION_NETWORK_SCHEMA_VERSION:
            raise ValueError(
                f"function network schema_version must be {FUNCTION_NETWORK_SCHEMA_VERSION!r}"
            )
        for component in components:
            if not set(component.evaluation_scopes).issubset(scopes):
                raise ValueError(
                    f"component {component.component!r} permits a scope disabled by the network"
                )

    @property
    def component_map(self) -> Mapping[str, FunctionComponentSpec]:
        """Return components in declaration order as a new read-only mapping."""
        from types import MappingProxyType

        return MappingProxyType({item.component: item for item in self.components})

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "components": [item.to_dict() for item in self.components],
            "couplings": [item.to_dict() for item in self.couplings],
            "objective": self.objective.to_dict(),
            "constraints": [item.to_dict() for item in self.constraints],
            "evaluation_scopes": [scope.value for scope in self.evaluation_scopes],
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FunctionNetworkSpec":
        required = {
            "name",
            "components",
            "couplings",
            "objective",
            "constraints",
            "evaluation_scopes",
            "schema_version",
        }
        _require_exact_keys(data, required, "function network")
        for field_name in ("components", "couplings", "constraints"):
            if not isinstance(data[field_name], list):
                raise TypeError(f"function network {field_name} must be a list")
        if not isinstance(data["objective"], Mapping):
            raise TypeError("function network objective must be a mapping")
        return cls(
            name=data["name"],
            components=tuple(FunctionComponentSpec.from_dict(item) for item in data["components"]),
            couplings=tuple(CouplingSpec.from_dict(item) for item in data["couplings"]),
            objective=TerminalObjectiveSpec.from_dict(data["objective"]),
            constraints=tuple(
                TerminalConstraintSpec.from_dict(item) for item in data["constraints"]
            ),
            evaluation_scopes=data["evaluation_scopes"],
            schema_version=data["schema_version"],
        )

    def to_json(self) -> str:
        """Serialize to canonical compact JSON."""
        return json.dumps(
            self.to_dict(), allow_nan=False, ensure_ascii=False, separators=(",", ":")
        )

    @classmethod
    def from_json(cls, value: str) -> "FunctionNetworkSpec":
        """Deserialize from canonical JSON data."""
        return cls.from_dict(json.loads(value))

    def to_yaml(self, path: str | Path) -> None:
        """Write stable safe YAML."""
        Path(path).write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "FunctionNetworkSpec":
        """Read strict safe YAML with duplicate-key rejection."""
        data = safe_load_unique(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def validate(self, system: System) -> tuple[str, ...]:
        """Validate this representation against ``system`` and return its execution order."""
        if not isinstance(system, System):
            raise TypeError("system must be a System")
        represented = self.component_map
        actual_names = system.component_names
        if len(set(actual_names)) != len(actual_names):
            raise ValueError("System contains duplicate component names")
        missing = set(actual_names) - set(represented)
        unknown = set(represented) - set(actual_names)
        if missing or unknown:
            raise ValueError(
                f"function network components differ from System; missing={sorted(missing)}, "
                f"unknown={sorted(unknown)}"
            )

        for name in actual_names:
            _validate_component(represented[name], system.get_component(name))

        represented_edges = {
            (item.source_component, item.source_port, item.target_component, item.target_port)
            for item in self.couplings
        }
        actual_edges = {
            (item["source"], item["port_from"], item["target"], item["port_to"])
            for item in system.connections
        }
        if represented_edges != actual_edges:
            raise ValueError(
                "function network couplings differ from System; "
                f"missing={sorted(actual_edges - represented_edges)}, "
                f"extra={sorted(represented_edges - actual_edges)}"
            )
        for coupling in self.couplings:
            _validate_coupling(coupling, represented)

        graph = nx.DiGraph()
        graph.add_nodes_from(actual_names)
        graph.add_edges_from(
            (item.source_component, item.target_component) for item in self.couplings
        )
        if not nx.is_directed_acyclic_graph(graph):
            raise ValueError("function network couplings must form a directed acyclic graph")
        try:
            system_order = tuple(system.topological_order())
        except nx.NetworkXUnfeasible as error:
            raise ValueError("System graph must be acyclic") from error
        order = tuple(nx.topological_sort(graph))
        if order != system_order:
            raise ValueError("function network topological order differs from System")

        _validate_terminal(self.objective.component, self.objective.scalar_output, represented)
        for constraint in self.constraints:
            _validate_terminal(constraint.component, constraint.scalar_output, represented)
        return order


def _validate_component(spec: FunctionComponentSpec, component: object) -> None:
    system_inputs = tuple(component.inputs)
    system_outputs = tuple(component.outputs)
    _validate_ports(spec.component, spec.inputs, system_inputs, "input")
    _validate_ports(spec.component, spec.outputs, system_outputs, "output")
    runnable = component.metadata.get("runnable")
    if runnable is None:
        if spec.entry_point is not None:
            raise ValueError(f"source component {spec.component!r} must not declare an entry point")
        if EvaluationScope.COMPONENT in spec.evaluation_scopes:
            raise ValueError(f"source component {spec.component!r} cannot use component scope")
        if spec.parameters:
            raise ValueError(f"source component {spec.component!r} cannot own parameters")
        return
    if not isinstance(runnable, Mapping):
        raise ValueError(f"component {spec.component!r} runnable metadata must be a mapping")
    entry = runnable.get("entry")
    if spec.entry_point != entry:
        raise ValueError(f"component {spec.component!r} entry point differs from System")
    params = runnable.get("params", {})
    if not isinstance(params, Mapping):
        raise ValueError(f"component {spec.component!r} runnable params must be a mapping")
    declared = {item.name for item in spec.parameters if item.name != "choice"}
    unknown = declared - set(params)
    if unknown:
        raise ValueError(
            f"component {spec.component!r} owns unknown runnable parameters: {sorted(unknown)}"
        )


def _validate_ports(
    component_name: str,
    represented: tuple[FunctionPortSpec, ...],
    actual: tuple[object, ...],
    direction: str,
) -> None:
    represented_by_name = {item.name: item for item in represented}
    actual_by_name = {item.name: item for item in actual}
    if len(actual_by_name) != len(actual):
        raise ValueError(f"System component {component_name!r} has duplicate {direction} ports")
    if set(represented_by_name) != set(actual_by_name):
        raise ValueError(f"component {component_name!r} {direction} ports differ from System")
    for name, port in represented_by_name.items():
        system_port = actual_by_name[name]
        expected_direction = "in" if direction == "input" else "out"
        if system_port.direction != expected_direction:
            raise ValueError(
                f"System component {component_name!r} port {name!r} has invalid direction"
            )
        if port.data_type != "any" and system_port.data_type != "any":
            if port.data_type != system_port.data_type:
                raise ValueError(
                    f"component {component_name!r} port {name!r} data type differs from System"
                )
        if port.units and system_port.units and port.units != system_port.units:
            raise ValueError(
                f"component {component_name!r} port {name!r} units differ from System"
            )


def _validate_coupling(
    coupling: CouplingSpec, components: Mapping[str, FunctionComponentSpec]
) -> None:
    if coupling.source_component not in components or coupling.target_component not in components:
        raise ValueError("coupling references an unknown component")
    source = components[coupling.source_component]
    target = components[coupling.target_component]
    source_ports = {item.name: item for item in source.outputs}
    target_ports = {item.name: item for item in target.inputs}
    if coupling.source_port not in source_ports:
        raise ValueError("coupling references an unknown source output port")
    if coupling.target_port not in target_ports:
        raise ValueError("coupling references an unknown target input port")
    output = source_ports[coupling.source_port]
    input_ = target_ports[coupling.target_port]
    if output.data_type != "any" and input_.data_type != "any":
        if output.data_type != input_.data_type:
            raise ValueError("coupling source and target data types are incompatible")
    if output.units and input_.units and output.units != input_.units:
        raise ValueError("coupling source and target units are incompatible")
    scalar_outputs = [
        item
        for item in source.scalar_outputs
        if item.port == coupling.source_port and EvaluationScope.SYSTEM in item.observed_in
    ]
    if not scalar_outputs:
        raise ValueError(
            "coupling source port must have a system-observable scalar output for replay"
        )


def _validate_terminal(
    component_name: str,
    scalar_output_name: str,
    components: Mapping[str, FunctionComponentSpec],
) -> None:
    component = components.get(component_name)
    if component is None:
        raise ValueError("terminal outcome references an unknown component")
    outputs = {item.name: item for item in component.scalar_outputs}
    output = outputs.get(scalar_output_name)
    if output is None:
        raise ValueError("terminal outcome references an unknown scalar output")
    if EvaluationScope.SYSTEM not in output.observed_in:
        raise ValueError("terminal outcome must reference a system-observable scalar output")


def scalar_observation_name(component: str, scalar_output: str) -> str:
    """Return the unambiguous ledger key for a component scalar observation."""
    _require_name(component, "component")
    _require_name(scalar_output, "scalar output")
    return f"{component}.{scalar_output}"


def validate_local_parameter_values(
    component: FunctionComponentSpec,
    values: Mapping[str, object],
) -> None:
    """Require one valid value for every active local design parameter."""
    if not isinstance(component, FunctionComponentSpec):
        raise TypeError("component must be a FunctionComponentSpec")
    if not isinstance(values, Mapping):
        raise TypeError("local parameter values must be a mapping")
    declared = {item.name for item in component.parameters}
    unknown = set(values) - declared
    if unknown:
        raise ValueError(
            f"component {component.component!r} has undeclared parameter values: {sorted(unknown)}"
        )
    known: dict[str, object] = {}
    for parameter in component.parameters:
        active = True
        if isinstance(parameter, (ContinuousParameter, IntegerParameter)):
            active = all(
                condition in known
                and any(
                    type(known[condition]) is type(allowed) and known[condition] == allowed
                    for allowed in allowed_values
                )
                for condition, allowed_values in parameter.active_when.items()
            )
        present = parameter.name in values
        if active and not present:
            raise ValueError(
                f"component {component.component!r} is missing active parameter {parameter.name!r}"
            )
        if not active and present:
            raise ValueError(
                f"component {component.component!r} supplies inactive parameter {parameter.name!r}"
            )
        if not active:
            continue
        value = values[parameter.name]
        if isinstance(parameter, CategoricalParameter):
            if not any(
                type(value) is type(category) and value == category
                for category in parameter.categories
            ):
                raise ValueError(
                    f"component {component.component!r} parameter {parameter.name!r} "
                    "is outside its categories"
                )
        elif isinstance(parameter, IntegerParameter):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < parameter.lower
                or value > parameter.upper
            ):
                raise ValueError(
                    f"component {component.component!r} parameter {parameter.name!r} "
                    "is outside its integer bounds"
                )
        elif (
            isinstance(value, bool)
            or not isinstance(value, Real)
            or not math.isfinite(value)
            or value < parameter.lower
            or value > parameter.upper
        ):
            raise ValueError(
                f"component {component.component!r} parameter {parameter.name!r} "
                "is outside its continuous bounds"
            )
        known[parameter.name] = value


def reduce_scalar(values: object, reducer: ScalarReducer) -> float:
    """Reduce one finite numeric array to a finite scalar observation."""
    array = np.asarray(values)
    if array.size == 0 or not np.issubdtype(array.dtype, np.number):
        raise ValueError("scalar observation source must be a non-empty numeric array")
    if not np.all(np.isfinite(array)):
        raise ValueError("scalar observation source must contain only finite values")
    functions = {
        "mean": np.mean,
        "sum": np.sum,
        "minimum": np.min,
        "maximum": np.max,
        "last": lambda item: item.reshape(-1)[-1],
    }
    if reducer not in functions:
        raise ValueError(f"unknown scalar reducer: {reducer!r}")
    value = float(functions[reducer](array))
    if not math.isfinite(value):
        raise ValueError("scalar reducer returned a non-finite value")
    return value
