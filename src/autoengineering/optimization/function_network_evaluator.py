"""Evaluation and verified replay for immutable function networks."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
import hashlib
import io
import math
import os
from pathlib import Path
import stat
import time
from types import MappingProxyType
from typing import TYPE_CHECKING
import zipfile

import numpy as np

from autoengineering.system.graph import System

from .function_network import (
    FunctionComponentSpec,
    FunctionNetworkSpec,
    ScalarOutputSpec,
    reduce_scalar,
    scalar_observation_name,
    validate_local_parameter_values,
)
from .ledger import ObservationLedgerReader
from .records import (
    EvaluationAction,
    EvaluationResult,
    EvaluationScope,
    EvaluationStatus,
    Scalar,
)

if TYPE_CHECKING:
    from autoengineering.research.runner import EvaluationContext, Runner


_DEFAULT_MAX_COMPRESSED_BYTES = 64 * 1024 * 1024
_DEFAULT_MAX_MEMBERS = 128
_DEFAULT_MAX_MEMBER_BYTES = 64 * 1024 * 1024
_DEFAULT_MAX_TOTAL_BYTES = 128 * 1024 * 1024
_SCALAR_ABSOLUTE_TOLERANCE = 1e-12


class FunctionNetworkArtifactError(ValueError):
    """A trace artifact failed lineage, digest, archive, or scalar checks."""


def _freeze_scalars(values: Mapping[str, Scalar], label: str) -> Mapping[str, Scalar]:
    result: dict[str, Scalar] = {}
    for name, value in values.items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"{label} names must be non-empty strings")
        if not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"{label} values must be scalar")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{label} float values must be finite")
        result[name] = value
    return MappingProxyType(result)


def _freeze_floats(values: Mapping[str, float], label: str) -> Mapping[str, float]:
    result: dict[str, float] = {}
    for name, value in values.items():
        if not isinstance(name, str) or not name:
            raise ValueError(f"{label} names must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{label} values must be numeric")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError(f"{label} values must be finite")
        result[name] = numeric
    return MappingProxyType(result)


def _freeze_strings(values: Mapping[str, str], label: str) -> Mapping[str, str]:
    result: dict[str, str] = {}
    for name, value in values.items():
        if not isinstance(name, str) or not name or not isinstance(value, str) or not value:
            raise ValueError(f"{label} must map non-empty strings to non-empty strings")
        result[name] = value
    return MappingProxyType(result)


@dataclass(frozen=True)
class ComponentTrainingRow:
    """One scalar component observation reconstructed from durable traces."""

    action_id: str
    component: str
    scope: EvaluationScope
    inputs: Mapping[str, Scalar]
    outputs: Mapping[str, float]
    artifact_ids: tuple[str, ...]
    artifact_sha256: Mapping[str, str]
    cost: float
    cost_unit: str

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not self.action_id:
            raise ValueError("training action_id must be a non-empty string")
        if not isinstance(self.component, str) or not self.component:
            raise ValueError("training component must be a non-empty string")
        object.__setattr__(self, "scope", EvaluationScope(self.scope))
        object.__setattr__(self, "inputs", _freeze_scalars(self.inputs, "training inputs"))
        outputs = _freeze_floats(self.outputs, "training outputs")
        if not outputs:
            raise ValueError("training outputs must not be empty")
        object.__setattr__(self, "outputs", outputs)
        artifact_ids = tuple(self.artifact_ids)
        if not artifact_ids or any(not isinstance(item, str) or not item for item in artifact_ids):
            raise ValueError("training artifact_ids must contain non-empty strings")
        if len(set(artifact_ids)) != len(artifact_ids):
            raise ValueError("training artifact_ids must be unique")
        object.__setattr__(self, "artifact_ids", artifact_ids)
        hashes = _freeze_strings(self.artifact_sha256, "training artifact_sha256")
        if set(hashes) != set(artifact_ids):
            raise ValueError("training artifact hashes must match artifact_ids")
        object.__setattr__(self, "artifact_sha256", hashes)
        if (
            isinstance(self.cost, bool)
            or not isinstance(self.cost, (int, float))
            or not math.isfinite(self.cost)
            or self.cost < 0
        ):
            raise ValueError("training cost must be a non-negative finite number")
        object.__setattr__(self, "cost", float(self.cost))
        if not isinstance(self.cost_unit, str) or not self.cost_unit:
            raise ValueError("training cost_unit must be a non-empty string")

    def to_dict(self) -> dict[str, object]:
        """Return a scalar-only representation suitable for reports and tests."""
        return {
            "action_id": self.action_id,
            "component": self.component,
            "scope": self.scope.value,
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "artifact_ids": list(self.artifact_ids),
            "artifact_sha256": dict(self.artifact_sha256),
            "cost": self.cost,
            "cost_unit": self.cost_unit,
        }


@dataclass(frozen=True)
class NpzReadLimits:
    """Resource limits applied before NumPy allocates trace arrays."""

    max_compressed_bytes: int = _DEFAULT_MAX_COMPRESSED_BYTES
    max_members: int = _DEFAULT_MAX_MEMBERS
    max_member_bytes: int = _DEFAULT_MAX_MEMBER_BYTES
    max_total_bytes: int = _DEFAULT_MAX_TOTAL_BYTES

    def __post_init__(self) -> None:
        for name in (
            "max_compressed_bytes",
            "max_members",
            "max_member_bytes",
            "max_total_bytes",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class FunctionNetworkEvaluator:
    """Validate and execute function-network actions through the existing runner."""

    spec: FunctionNetworkSpec
    context: EvaluationContext
    runner: Runner | None = field(default=None, compare=False, repr=False)
    clock: Callable[[], float] = field(default=time.perf_counter, compare=False, repr=False)

    def __post_init__(self) -> None:
        from autoengineering.research.runner import EvaluationContext, Runner

        if not isinstance(self.spec, FunctionNetworkSpec):
            raise TypeError("spec must be a FunctionNetworkSpec")
        if not isinstance(self.context, EvaluationContext):
            raise TypeError("context must be an EvaluationContext")
        if self.runner is not None and not isinstance(self.runner, Runner):
            raise TypeError("runner must satisfy the Runner protocol")
        if not callable(self.clock):
            raise TypeError("clock must be callable")
        self.spec.validate(self.context.system)
        if any(component.cost_unit != self.context.cost_unit for component in self.spec.components):
            raise ValueError("function network and evaluator cost units must match")
        for component in self.spec.components:
            choices = next(
                (item for item in component.parameters if item.name == "choice"), None
            )
            alternatives = self.context.alternatives.get(component.component)
            if choices is None:
                if alternatives:
                    raise ValueError(
                        f"component {component.component!r} has undeclared evaluator alternatives"
                    )
            elif alternatives is None or set(choices.categories) != set(alternatives):
                raise ValueError(
                    f"component {component.component!r} choice categories differ from evaluator "
                    "alternatives"
                )

    def evaluate(self, action: EvaluationAction) -> EvaluationResult:
        """Evaluate one declared action and record only scalar features plus NPZ references."""
        from autoengineering.research.runner import execute_action, run_component

        if not isinstance(action, EvaluationAction):
            raise TypeError("action must be an EvaluationAction")
        if action.scope not in self.spec.evaluation_scopes:
            raise ValueError(f"action scope {action.scope.value!r} is not permitted by the network")
        components = self.spec.component_map
        if action.scope is EvaluationScope.SYSTEM:
            selected = self.spec.components
        else:
            component = components.get(action.component or "")
            if component is None:
                raise ValueError(f"unknown component in action: {action.component!r}")
            if EvaluationScope.COMPONENT not in component.evaluation_scopes:
                raise ValueError(f"component {component.component!r} does not permit component scope")
            if any(
                coupling.target_component == component.component for coupling in self.spec.couplings
            ) and not action.parent_artifact_ids:
                raise ValueError("component action requires declared parent artifacts")
            selected = (component,)
        self._validate_action_config(action, selected)
        functions = self._observation_functions(action.scope, selected)
        if not functions:
            raise ValueError("action has no declared observable scalar output")
        evaluation_context = replace(self.context, outcome_functions=functions)
        runner = run_component if self.runner is None else self.runner
        return execute_action(action, evaluation_context, runner=runner, clock=self.clock)

    def _validate_action_config(
        self,
        action: EvaluationAction,
        selected: tuple[FunctionComponentSpec, ...],
    ) -> None:
        declared = {
            f"{component.component}.{parameter.name}"
            for component in selected
            for parameter in component.parameters
        }
        unknown = set(action.config) - declared
        if unknown:
            raise ValueError(f"action configuration contains undeclared parameters: {sorted(unknown)}")
        for component in selected:
            prefix = f"{component.component}."
            local = {
                name.removeprefix(prefix): value
                for name, value in action.config.items()
                if name.startswith(prefix)
            }
            validate_local_parameter_values(component, local)

    def _observation_functions(
        self,
        scope: EvaluationScope,
        selected: tuple[FunctionComponentSpec, ...],
    ) -> Mapping[str, Callable[[dict[str, np.ndarray]], float]]:
        functions: dict[str, Callable[[dict[str, np.ndarray]], float]] = {}
        scalar_lookup: dict[tuple[str, str], ScalarOutputSpec] = {}
        for component in selected:
            for output in component.scalar_outputs:
                if scope not in output.observed_in:
                    continue
                scalar_lookup[(component.component, output.name)] = output
                key = scalar_observation_name(component.component, output.name)
                functions[key] = _reducer_function(component.component, output)
        if scope is EvaluationScope.SYSTEM:
            terminal = (self.spec.objective, *self.spec.constraints)
            for outcome in terminal:
                output = scalar_lookup[(outcome.component, outcome.scalar_output)]
                if outcome.outcome in functions:
                    raise ValueError("terminal outcome collides with a scalar observation name")
                functions[outcome.outcome] = _reducer_function(outcome.component, output)
        return MappingProxyType(functions)


def _reducer_function(
    component_name: str, output: ScalarOutputSpec
) -> Callable[[dict[str, np.ndarray]], float]:
    qualified_port = f"{component_name}.{output.port}"

    def calculate(values: dict[str, np.ndarray]) -> float:
        if qualified_port not in values:
            raise KeyError(f"trace does not contain declared output {qualified_port!r}")
        return reduce_scalar(values[qualified_port], output.reducer)

    return calculate


def read_verified_npz(
    path: str | Path,
    sha256: str,
    *,
    limits: NpzReadLimits = NpzReadLimits(),
) -> Mapping[str, np.ndarray]:
    """Read a digest-bound, resource-bounded NPZ artifact without pickle support."""
    candidate = Path(path)
    if candidate.is_symlink():
        raise FunctionNetworkArtifactError("trace artifact must not be a symlink")
    try:
        descriptor = os.open(candidate, os.O_RDONLY)
    except OSError as error:
        raise FunctionNetworkArtifactError(f"trace artifact cannot be opened: {candidate}") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise FunctionNetworkArtifactError("trace artifact must be a regular file")
        if metadata.st_size > limits.max_compressed_bytes:
            raise FunctionNetworkArtifactError("trace artifact exceeds compressed byte limit")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(limits.max_compressed_bytes + 1)
    finally:
        os.close(descriptor)
    if len(data) > limits.max_compressed_bytes:
        raise FunctionNetworkArtifactError("trace artifact exceeds compressed byte limit")
    if not isinstance(sha256, str) or hashlib.sha256(data).hexdigest() != sha256:
        raise FunctionNetworkArtifactError("trace artifact SHA-256 does not match")
    _validate_npz_archive(data, limits)
    try:
        with np.load(io.BytesIO(data), allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
    except (OSError, ValueError) as error:
        raise FunctionNetworkArtifactError("trace artifact is not a readable NPZ file") from error
    for array in arrays.values():
        array.setflags(write=False)
    return MappingProxyType(arrays)


def _validate_npz_archive(data: bytes, limits: NpzReadLimits) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if not members:
                raise FunctionNetworkArtifactError("trace artifact must contain arrays")
            if len(members) > limits.max_members:
                raise FunctionNetworkArtifactError("trace artifact exceeds member-count limit")
            total = 0
            names: set[str] = set()
            for member in members:
                name = _logical_npz_name(member.filename)
                if name in names:
                    raise FunctionNetworkArtifactError("trace artifact has duplicate member names")
                names.add(name)
                total += member.file_size
                if member.file_size > limits.max_member_bytes:
                    raise FunctionNetworkArtifactError("trace artifact member exceeds byte limit")
                if total > limits.max_total_bytes:
                    raise FunctionNetworkArtifactError("trace artifact exceeds total byte limit")
                _validate_npy_header(archive, member, limits)
    except FunctionNetworkArtifactError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise FunctionNetworkArtifactError("trace artifact is not a safe NPZ archive") from error


def _logical_npz_name(filename: str) -> str:
    if not isinstance(filename, str) or not filename.endswith(".npy"):
        raise FunctionNetworkArtifactError("trace artifact contains a non-NPY member")
    name = filename.removesuffix(".npy")
    if not name or name in {".", ".."} or "/" in name or "\\" in name or "\x00" in name:
        raise FunctionNetworkArtifactError("trace artifact member name is unsafe")
    return name


def _validate_npy_header(
    archive: zipfile.ZipFile,
    member: zipfile.ZipInfo,
    limits: NpzReadLimits,
) -> None:
    with archive.open(member) as stream:
        version = np.lib.format.read_magic(stream)
        if version == (1, 0):
            shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
        elif version in {(2, 0), (3, 0)}:
            shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
        else:
            raise FunctionNetworkArtifactError("trace artifact has an unsupported NPY version")
    if dtype.hasobject:
        raise FunctionNetworkArtifactError("trace artifact object arrays are not allowed")
    elements = 1
    for dimension in shape:
        if not isinstance(dimension, int) or dimension < 0:
            raise FunctionNetworkArtifactError("trace artifact has an invalid array shape")
        elements *= dimension
        if elements > limits.max_total_bytes:
            raise FunctionNetworkArtifactError("trace artifact declared array is too large")
    if elements * dtype.itemsize > limits.max_member_bytes:
        raise FunctionNetworkArtifactError("trace artifact declared array exceeds byte limit")


def reconstruct_component_training_tables(
    spec: FunctionNetworkSpec,
    system: System,
    ledger: ObservationLedgerReader,
    *,
    limits: NpzReadLimits = NpzReadLimits(),
) -> Mapping[str, tuple[ComponentTrainingRow, ...]]:
    """Reconstruct deterministic scalar training tables from verified ledger traces."""
    order = spec.validate(system)
    entries = ledger.entries()
    tables: dict[str, list[ComponentTrainingRow]] = {name: [] for name in order}
    registry: dict[str, tuple[Path, str]] = {}
    seen_artifact_ids: set[str] = set()
    ledger_path = getattr(ledger, "path", None)
    base = None if ledger_path is None else Path(ledger_path).parent

    for action, result in entries:
        for parent_id in action.parent_artifact_ids:
            if parent_id not in registry:
                raise FunctionNetworkArtifactError(
                    f"parent artifact {parent_id!r} is unknown or not from an earlier success"
                )
        current = _register_artifacts(result, registry, seen_artifact_ids, base)
        if result.status is not EvaluationStatus.SUCCESS:
            continue
        if not current:
            raise FunctionNetworkArtifactError(
                f"successful action {action.id!r} has no trace artifact"
            )
        current_arrays = [
            read_verified_npz(path, digest, limits=limits) for _, path, digest in current
        ]
        parent_arrays = [
            read_verified_npz(*registry[parent_id], limits=limits)
            for parent_id in action.parent_artifact_ids
        ]
        if action.scope is EvaluationScope.SYSTEM:
            selected = [spec.component_map[name] for name in order]
        else:
            selected = [spec.component_map[action.component or ""]]
        for component in selected:
            prefix = f"{component.component}."
            validate_local_parameter_values(
                component,
                {
                    name.removeprefix(prefix): value
                    for name, value in action.config.items()
                    if name.startswith(prefix)
                },
            )
            observable = tuple(
                output for output in component.scalar_outputs if action.scope in output.observed_in
            )
            if not observable:
                continue
            rows = _component_trace_rows(
                spec,
                component,
                action,
                current_arrays,
                parent_arrays,
            )
            averaged_inputs = _average_inputs(tuple(item[0] for item in rows))
            averaged_outputs = _average_floats(tuple(item[1] for item in rows))
            for name, value in averaged_outputs.items():
                ledger_name = scalar_observation_name(component.component, name)
                recorded = result.outcomes.get(ledger_name)
                if recorded is None or not math.isclose(
                    recorded, value, rel_tol=0.0, abs_tol=_SCALAR_ABSOLUTE_TOLERANCE
                ):
                    raise FunctionNetworkArtifactError(
                        f"scalar observation {ledger_name!r} differs from verified trace"
                    )
            artifact_ids = (
                *action.parent_artifact_ids,
                *(artifact_id for artifact_id, _, _ in current),
            )
            tables[component.component].append(
                ComponentTrainingRow(
                    action_id=action.id,
                    component=component.component,
                    scope=action.scope,
                    inputs=averaged_inputs,
                    outputs=averaged_outputs,
                    artifact_ids=artifact_ids,
                    artifact_sha256={artifact_id: registry[artifact_id][1] for artifact_id in artifact_ids},
                    cost=result.cost,
                    cost_unit=result.cost_unit,
                )
            )
    return MappingProxyType({name: tuple(tables[name]) for name in order})


def _register_artifacts(
    result: EvaluationResult,
    registry: dict[str, tuple[Path, str]],
    seen_artifact_ids: set[str],
    base: Path | None,
) -> tuple[tuple[str, Path, str], ...]:
    current: list[tuple[str, Path, str]] = []
    for artifact_id, value in result.artifacts.items():
        if artifact_id in seen_artifact_ids:
            raise FunctionNetworkArtifactError(f"duplicate artifact ID: {artifact_id!r}")
        seen_artifact_ids.add(artifact_id)
        path = Path(value)
        if not path.is_absolute():
            if base is None:
                raise FunctionNetworkArtifactError("relative artifacts require a ledger path")
            path = base / path
        digest = result.artifact_sha256[artifact_id]
        if result.status is EvaluationStatus.SUCCESS:
            registry[artifact_id] = (path, digest)
        current.append((artifact_id, path, digest))
    return tuple(current)


def _component_trace_rows(
    spec: FunctionNetworkSpec,
    component: FunctionComponentSpec,
    action: EvaluationAction,
    current_arrays: list[Mapping[str, np.ndarray]],
    parent_arrays: list[Mapping[str, np.ndarray]],
) -> tuple[tuple[Mapping[str, Scalar], Mapping[str, float]], ...]:
    rows = []
    parent_values: dict[str, np.ndarray] = {}
    for artifact in parent_arrays:
        parent_values.update(artifact)
    for artifact in current_arrays:
        available = {**parent_values, **artifact}
        inputs: dict[str, Scalar] = {
            parameter.name: action.config[f"{component.component}.{parameter.name}"]
            for parameter in component.parameters
            if f"{component.component}.{parameter.name}" in action.config
        }
        for coupling in spec.couplings:
            if coupling.target_component != component.component:
                continue
            source = spec.component_map[coupling.source_component]
            for output in source.scalar_outputs:
                if output.port != coupling.source_port:
                    continue
                key = (
                    f"__input__.{component.component}.{coupling.target_port}"
                    if action.scope is EvaluationScope.COMPONENT
                    else f"{source.component}.{output.port}"
                )
                if key not in available:
                    raise FunctionNetworkArtifactError(
                        f"trace lacks upstream coupling output {key!r}"
                    )
                inputs[scalar_observation_name(source.component, output.name)] = reduce_scalar(
                    available[key], output.reducer
                )
        outputs = {
            output.name: _trace_scalar(available, component.component, output)
            for output in component.scalar_outputs
            if action.scope in output.observed_in
        }
        rows.append((MappingProxyType(inputs), MappingProxyType(outputs)))
    return tuple(rows)


def _trace_scalar(
    available: Mapping[str, np.ndarray],
    component_name: str,
    output: ScalarOutputSpec,
) -> float:
    key = f"{component_name}.{output.port}"
    if key not in available:
        raise FunctionNetworkArtifactError(f"trace lacks declared component output {key!r}")
    return reduce_scalar(available[key], output.reducer)


def _average_inputs(rows: tuple[Mapping[str, Scalar], ...]) -> Mapping[str, Scalar]:
    if not rows:
        raise FunctionNetworkArtifactError("trace reconstruction produced no rows")
    names = tuple(rows[0])
    if any(tuple(row) != names for row in rows[1:]):
        raise FunctionNetworkArtifactError("replicate input features differ in structure")
    result: dict[str, Scalar] = {}
    for name in names:
        values = [row[name] for row in rows]
        first = values[0]
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            result[name] = float(np.mean(values))
        elif all(type(value) is type(first) and value == first for value in values):
            result[name] = first
        else:
            raise FunctionNetworkArtifactError("replicate categorical input features differ")
    return MappingProxyType(result)


def _average_floats(rows: tuple[Mapping[str, float], ...]) -> Mapping[str, float]:
    if not rows:
        raise FunctionNetworkArtifactError("trace reconstruction produced no outputs")
    names = tuple(rows[0])
    if any(tuple(row) != names for row in rows[1:]):
        raise FunctionNetworkArtifactError("replicate output features differ in structure")
    return MappingProxyType(
        {name: float(np.mean([row[name] for row in rows])) for name in names}
    )
