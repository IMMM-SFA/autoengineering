"""Execute a component's runnable to produce output arrays.

The package normally *describes* systems without executing them. Auto research is
the one place execution is unavoidable: to measure whether a candidate model is an
improvement, we have to run it. Rather than change the ``Component`` schema, the
runnable contract lives in the free-form ``Component.metadata["runnable"]`` dict,
which already round-trips through YAML and survives ``swap_component``'s deepcopy.

Runnable contract (in ``Component.metadata``)::

    runnable:
      kind: python                                  # or "command"
      entry: "models.pet_hargreaves:hargreaves_pet" # module:callable  (python)
      # entry: "python run_pet.py --in {inputs} --out {outputs}"  (command)
      inputs: [tmean, doy]      # named arrays, passed as positional args in order
      outputs: [pet]            # names mapped onto the callable's return value(s)
      params: {latitude: 31.7}  # optional scalar keyword arguments
      sys_path: "."             # optional path prepended to sys.path for imports

Two runner styles are provided:

- :func:`run_component` executes a single component given a dict of named input
  arrays. It is the primitive used by everything else.
- :func:`build_feedforward_runner` wires a whole feed-forward :class:`System`
  together, passing arrays along edges by port name. This produces the
  ``run_chain`` callable that :func:`autoengineering.research.loop.auto_improve`
  consumes, generalizing the hand-wired ``run_chain`` functions in the examples.
"""

from __future__ import annotations

import importlib
import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import io
import math
import os
import re
import secrets
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from types import MappingProxyType
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

import numpy as np

from autoengineering.system.component import Component
from autoengineering.execute.swap import swap_component
from autoengineering.system.graph import System
from autoengineering.optimization.records import (
    EvaluationAction,
    EvaluationResult,
    EvaluationScope,
)


class ScientificInfeasibleError(Exception):
    """Raise only for a valid evaluation that violates a scientific condition."""


class InfrastructureFailure(Exception):
    """Explicit runner signal for scheduler, transport, or storage failure."""


class _ModelContractError(Exception):
    """A runnable or outcome callable did not meet the evaluator contract."""


class _ArtifactVerificationError(Exception):
    """A required artifact could not be safely loaded or verified."""


class _ArtifactStorageError(Exception):
    """A produced artifact could not be durably persisted."""


class _ModelExecutionError(Exception):
    """A runner raised while evaluating a declared model."""


class _InfrastructureExecutionError(Exception):
    """A runner explicitly reported scheduler, transport, or storage failure."""


class _ClockError(Exception):
    """The evaluator's monotonic clock could not provide a valid timestamp."""


class _CostError(Exception):
    """Measured elapsed time cannot be represented in the configured cost unit."""


@dataclass(frozen=True)
class ParentArtifactReference:
    """Immutable location and digest of a reusable parent artifact."""

    path: str | Path
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", Path(self.path).expanduser().resolve())
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(char not in "0123456789abcdef" for char in self.sha256)
        ):
            raise ValueError("parent artifact SHA-256 must be a lowercase 64-character hex digest")


@dataclass(frozen=True)
class EvaluationContext:
    """Frozen inputs to a reproducible action evaluation.

    Source arrays override parent-artifact arrays on matching names.  If two parent
    artifacts define a name, the later ID in ``action.parent_artifact_ids`` wins.
    ``cost_per_evaluator_second`` explicitly converts monotonic elapsed seconds to
    ``cost_unit`` exactly; a successful completed attempt requires a finite,
    strictly increasing clock interval and therefore has a positive measured cost.

    The action seed is durable provenance.  The runner protocol has no seed
    argument, so runners that use randomness must consume an explicitly configured
    seed; this evaluator never mutates NumPy's global random state. Callable
    references are retained, so closure state owned by a callable cannot be frozen.
    """

    system: System
    alternatives: Mapping[str, Mapping[str, Component]]
    source_arrays: Mapping[str, np.ndarray]
    observed: Mapping[str, np.ndarray]
    outcome_functions: Mapping[str, Callable[[dict[str, np.ndarray]], float]]
    cost_unit: str
    artifact_dir: str | Path | None = None
    parent_artifacts: Mapping[str, ParentArtifactReference] = field(default_factory=dict)
    cost_per_evaluator_second: float = 1.0
    max_parent_artifact_bytes: int = 64 * 1024 * 1024
    max_parent_artifact_members: int = 128
    max_parent_artifact_member_bytes: int = 64 * 1024 * 1024
    max_parent_artifact_total_bytes: int = 128 * 1024 * 1024

    def __post_init__(self) -> None:
        if not isinstance(self.system, System):
            raise TypeError("system must be a System")
        object.__setattr__(self, "system", copy.deepcopy(self.system))
        if not isinstance(self.cost_unit, str) or not self.cost_unit.strip():
            raise ValueError("cost_unit must be a non-empty string")
        if (
            isinstance(self.cost_per_evaluator_second, bool)
            or not isinstance(self.cost_per_evaluator_second, (int, float))
            or not math.isfinite(self.cost_per_evaluator_second)
            or self.cost_per_evaluator_second <= 0
        ):
            raise ValueError("cost_per_evaluator_second must be a positive finite number")
        for name in (
            "max_parent_artifact_bytes",
            "max_parent_artifact_members",
            "max_parent_artifact_member_bytes",
            "max_parent_artifact_total_bytes",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        alternatives: dict[str, Mapping[str, Component]] = {}
        for component_name, choices in self.alternatives.items():
            if (
                not isinstance(component_name, str)
                or not component_name
                or not isinstance(choices, Mapping)
            ):
                raise TypeError("alternatives must map component names to choice mappings")
            frozen_choices: dict[str, Component] = {}
            for choice, component in choices.items():
                if (
                    not isinstance(choice, str)
                    or not choice
                    or not isinstance(component, Component)
                ):
                    raise TypeError("alternative choices must map names to Components")
                frozen_choices[choice] = copy.deepcopy(component)
            alternatives[component_name] = MappingProxyType(frozen_choices)
        object.__setattr__(self, "alternatives", MappingProxyType(alternatives))
        object.__setattr__(
            self, "source_arrays", _freeze_arrays(self.source_arrays, "source_arrays")
        )
        object.__setattr__(self, "observed", _freeze_arrays(self.observed, "observed"))
        outcomes: dict[str, Callable[[dict[str, np.ndarray]], float]] = {}
        for name, function in self.outcome_functions.items():
            if not isinstance(name, str) or not name or not callable(function):
                raise TypeError("outcome_functions must map non-empty names to callables")
            outcomes[name] = function
        if not outcomes:
            raise ValueError("outcome_functions must not be empty")
        object.__setattr__(self, "outcome_functions", MappingProxyType(outcomes))
        if self.artifact_dir is not None:
            if not isinstance(self.artifact_dir, (str, Path)):
                raise TypeError("artifact_dir must be a string or Path")
            artifact_dir = (
                self.artifact_dir.expanduser()
                if isinstance(self.artifact_dir, Path)
                else os.path.expanduser(self.artifact_dir)
            )
            if not artifact_dir:
                raise ValueError("artifact_dir must not be empty")
            # Preserve lexical components for the POSIX descriptor walk.  In
            # particular, normalizing here would erase forbidden `.`/`..`.
            object.__setattr__(self, "artifact_dir", artifact_dir)
        parents: dict[str, ParentArtifactReference] = {}
        for artifact_id, reference in self.parent_artifacts.items():
            if not isinstance(artifact_id, str) or not artifact_id:
                raise TypeError("parent artifact IDs must be non-empty strings")
            if not isinstance(reference, ParentArtifactReference):
                raise TypeError("parent_artifacts values must be ParentArtifactReference instances")
            parents[artifact_id] = reference
        object.__setattr__(self, "parent_artifacts", MappingProxyType(parents))


def _freeze_arrays(values: Mapping[str, np.ndarray], label: str) -> Mapping[str, np.ndarray]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{label} must be a mapping")
    frozen: dict[str, np.ndarray] = {}
    for name, value in values.items():
        if not isinstance(name, str) or not name:
            raise TypeError(f"{label} keys must be non-empty strings")
        array = np.array(value, copy=True)
        array.setflags(write=False)
        frozen[name] = array
    return MappingProxyType(frozen)


@runtime_checkable
class Runner(Protocol):
    """Executes one component: named input arrays -> named output arrays.

    Implement this protocol to add new execution backends (e.g. a BMI runner,
    per ``concept.md``). The built-in :func:`run_component` covers the ``python``
    and ``command`` kinds.
    """

    def __call__(
        self, component: Component, inputs: dict[str, np.ndarray]
    ) -> dict[str, np.ndarray]: ...


def _load_callable(entry: str, sys_path: str | None = None) -> Callable:
    """Import a ``module:function`` entry point, optionally extending sys.path."""
    if ":" not in entry:
        raise ValueError(f"python runnable entry must be 'module:callable', got {entry!r}")
    module_name, func_name = entry.split(":", 1)

    added = None
    if sys_path:
        resolved = str(Path(sys_path).resolve())
        if resolved not in sys.path:
            sys.path.insert(0, resolved)
            added = resolved
    try:
        module = importlib.import_module(module_name)
    finally:
        if added is not None and added in sys.path:
            sys.path.remove(added)

    func = getattr(module, func_name, None)
    if func is None or not callable(func):
        raise AttributeError(f"{module_name!r} has no callable {func_name!r}")
    return func


def _as_output_dict(result, output_names: list[str]) -> dict[str, np.ndarray]:
    """Map a callable's return value(s) onto the declared output names."""
    if isinstance(result, tuple):
        values = list(result)
    else:
        values = [result]
    if len(values) < len(output_names):
        raise ValueError(
            f"runnable returned {len(values)} value(s) but declares "
            f"{len(output_names)} output(s): {output_names}"
        )
    return {name: np.asarray(values[i]) for i, name in enumerate(output_names)}


def _run_python(spec: dict, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    func = _load_callable(spec["entry"], spec.get("sys_path"))
    input_names = spec.get("inputs", [])
    output_names = spec.get("outputs", [])
    params = spec.get("params", {}) or {}

    missing = [n for n in input_names if n not in inputs]
    if missing:
        raise KeyError(f"missing input array(s) for runnable: {missing}")

    args = [inputs[n] for n in input_names]
    result = func(*args, **params)
    return _as_output_dict(result, output_names)


def _run_command(spec: dict, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Run a shell command with a numpy .npz I/O contract.

    Input arrays are written to a temp ``inputs.npz``; the command is expected to
    read it and write an ``outputs.npz`` containing the declared output names.
    ``{inputs}`` and ``{outputs}`` in the entry string are substituted with those
    temp paths.
    """
    output_names = spec.get("outputs", [])
    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "inputs.npz"
        out_path = Path(tmp) / "outputs.npz"
        np.savez(in_path, **{k: np.asarray(v) for k, v in inputs.items()})

        cmd = spec["entry"].format(inputs=str(in_path), outputs=str(out_path))
        subprocess.run(cmd, shell=True, check=True, cwd=spec.get("sys_path") or None)

        if not out_path.exists():
            raise FileNotFoundError(f"command runnable did not write outputs to {out_path}")
        loaded = np.load(out_path)
        missing = [n for n in output_names if n not in loaded]
        if missing:
            raise KeyError(f"command outputs.npz missing array(s): {missing}")
        return {n: loaded[n] for n in output_names}


def run_component(component: Component, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Execute a component's runnable and return its named output arrays.

    Args:
        component: A component whose ``metadata["runnable"]`` describes how to run
            it (see module docstring for the contract).
        inputs: Named input arrays, keyed by the names listed in
            ``runnable["inputs"]``.

    Returns:
        Named output arrays, keyed by ``runnable["outputs"]``.

    Raises:
        ValueError: if the component has no runnable spec or an unknown ``kind``.
    """
    spec = component.metadata.get("runnable")
    if not spec:
        raise ValueError(
            f"component '{component.name}' has no metadata['runnable']; cannot "
            "execute it. Add a runnable block to make it runnable."
        )
    kind = spec.get("kind", "python")
    if kind == "python":
        return _run_python(spec, inputs)
    if kind == "command":
        return _run_command(spec, inputs)
    raise ValueError(f"unknown runnable kind {kind!r} (expected 'python' or 'command')")


def build_feedforward_runner(
    system: System,
    source_arrays: dict[str, np.ndarray],
    runner: Runner = run_component,
) -> Callable[[System], dict[str, np.ndarray]]:
    """Build a ``run_chain(system)`` callable for a feed-forward system.

    Walks the system in topological order, executing each runnable component and
    passing its outputs to downstream components along the graph edges (matching
    ``port_from`` -> ``port_to``). Components without a runnable (e.g. a pure
    ``data_source``) are treated as passthroughs whose output ports are supplied
    from ``source_arrays``.

    The returned callable takes a (possibly swapped) ``System`` and returns a dict
    of every output array produced, keyed as ``"<component>.<port>"`` plus bare
    port names for convenience. This is the ``run_chain`` that ``auto_improve``
    calls each iteration.

    Args:
        system: The system whose topology defines the wiring. Only the topology
            and port names are read here; the callable re-reads components from
            whatever system it is handed, so swaps take effect.
        source_arrays: Arrays feeding the source components' output ports, keyed
            by ``"<component>.<port>"`` or by bare port name.
        runner: Component execution backend (defaults to :func:`run_component`).

    Returns:
        A ``run_chain`` callable.
    """
    # Freeze the wiring from the reference system's topology.
    order = system.topological_order()
    edges = system.connections

    def _source_value(comp_name: str, port: str) -> np.ndarray:
        for key in (f"{comp_name}.{port}", port):
            if key in source_arrays:
                return np.asarray(source_arrays[key])
        raise KeyError(
            f"no source array for '{comp_name}.{port}'. Provide it in "
            "source_arrays keyed by '<component>.<port>' or by bare port name."
        )

    def run_chain(sys_to_run: System) -> dict[str, np.ndarray]:
        # available holds "<component>.<port>" -> array as the chain executes.
        available: dict[str, np.ndarray] = {}

        for comp_name in order:
            comp = sys_to_run.get_component(comp_name)
            spec = comp.metadata.get("runnable")

            if not spec:
                # Source / passthrough component: seed its outputs from source_arrays.
                for port in comp.outputs:
                    available[f"{comp_name}.{port.name}"] = _source_value(comp_name, port.name)
                continue

            # Gather inputs by following incoming edges into this component.
            inputs: dict[str, np.ndarray] = {}
            incoming = [e for e in edges if e["target"] == comp_name]
            for edge in incoming:
                src_key = f"{edge['source']}.{edge['port_from']}"
                if src_key in available:
                    inputs[edge["port_to"]] = available[src_key]
            # Any declared input not satisfied by an edge is pulled from sources
            # (covers extra driver arrays like day-of-year).
            for name in spec.get("inputs", []):
                if name not in inputs:
                    try:
                        inputs[name] = _source_value(comp_name, name)
                    except KeyError:
                        pass

            outputs = runner(comp, inputs)
            _validate_declared_outputs(comp, outputs)
            for port_name, arr in outputs.items():
                available[f"{comp_name}.{port_name}"] = arr

        # Expose bare port names too, last-writer-wins, for convenient scoring.
        flat = dict(available)
        for key, arr in available.items():
            flat[key.split(".", 1)[1]] = arr
        return flat

    return run_chain


def execute_action(
    action: EvaluationAction,
    context: EvaluationContext,
    *,
    runner: Runner = run_component,
    clock: Callable[[], float] = time.perf_counter,
) -> EvaluationResult:
    """Execute an optimization action without mutating its baseline inputs.

    ``ValueError`` and ``TypeError`` raised before timing begins identify malformed
    caller configuration and deliberately remain visible.  All exceptions from
    evaluation, outcome calculation, parent verification, and artifact storage are
    converted to exactly one named :class:`EvaluationResult` factory.
    """
    if not isinstance(action, EvaluationAction):
        raise TypeError("action must be an EvaluationAction")
    if not isinstance(context, EvaluationContext):
        raise TypeError("context must be an EvaluationContext")
    if not isinstance(runner, Runner):
        raise TypeError("runner must satisfy the Runner protocol")

    system = _configured_system(action, context)
    timer = _EvaluationTimer(clock)
    artifacts: dict[str, str] = {}
    digests: dict[str, str] = {}
    try:
        timer.start()
        replicate_outcomes: dict[str, list[float]] = {
            name: [] for name in context.outcome_functions
        }
        for replicate in range(action.replicates):
            if action.scope is EvaluationScope.SYSTEM:
                outputs = _execute_system_action(system, context, runner)
            else:
                outputs = _execute_component_action(action, system, context, runner)
            _validate_outputs(outputs)
            outcome_error: Exception | None = None
            for name, function in context.outcome_functions.items():
                try:
                    value = function(outputs)
                except ScientificInfeasibleError:
                    if outcome_error is None:
                        outcome_error = ScientificInfeasibleError(
                            f"outcome {name!r} is scientifically infeasible"
                        )
                except Exception as error:
                    if outcome_error is None:
                        outcome_error = _ModelContractError(f"outcome {name!r} failed: {error}")
                else:
                    try:
                        replicate_outcomes[name].append(_finite_outcome(value, name))
                    except Exception as error:
                        if outcome_error is None:
                            outcome_error = error
            if outcome_error is not None:
                raise outcome_error
            if context.artifact_dir is not None:
                artifact_id = _replicate_artifact_id(action.id, replicate, action.replicates)
                path, digest = _write_artifact(context.artifact_dir, artifact_id, outputs)
                artifacts[artifact_id] = str(path)
                digests[artifact_id] = digest
        elapsed = timer.finish()
        outcomes = {name: float(np.mean(values)) for name, values in replicate_outcomes.items()}
        errors = {
            name: 0.0
            if action.replicates == 1
            else float(np.std(values, ddof=1) / math.sqrt(action.replicates))
            for name, values in replicate_outcomes.items()
        }
        return EvaluationResult.success(
            action.id,
            outcomes,
            errors,
            _cost(elapsed, context),
            context.cost_unit,
            artifacts=artifacts,
            artifact_sha256=digests,
            evaluator_seconds=elapsed,
        )
    except (_ClockError, _CostError) as error:
        return _failure_result(
            EvaluationResult.infrastructure_failure,
            action,
            context,
            error,
            artifacts,
            digests,
            elapsed=timer.elapsed or 0.0,
        )
    except ScientificInfeasibleError as error:
        return _timed_failure(
            EvaluationResult.scientific_infeasible,
            action,
            context,
            timer,
            error,
            artifacts,
            digests,
        )
    except (TimeoutError, subprocess.TimeoutExpired) as error:
        return _timed_failure(
            EvaluationResult.timeout, action, context, timer, error, artifacts, digests
        )
    except (
        _ArtifactVerificationError,
        _ArtifactStorageError,
        _InfrastructureExecutionError,
    ) as error:
        return _timed_failure(
            EvaluationResult.infrastructure_failure,
            action,
            context,
            timer,
            error,
            artifacts,
            digests,
        )
    except Exception as error:
        return _timed_failure(
            EvaluationResult.model_failure, action, context, timer, error, artifacts, digests
        )


def _configured_system(action: EvaluationAction, context: EvaluationContext) -> System:
    """Validate config bindings and create the independently configured system."""
    if (
        action.scope is EvaluationScope.COMPONENT
        and action.component not in context.system.component_names
    ):
        raise ValueError(f"unknown component in action: {action.component!r}")
    choices: dict[str, str] = {}
    parameters: dict[str, dict[str, object]] = {}
    for key, value in action.config.items():
        component_name, binding = _parse_binding(key)
        if component_name not in context.system.component_names:
            raise ValueError(f"unknown component in configuration: {component_name!r}")
        if action.scope is EvaluationScope.COMPONENT and component_name != action.component:
            raise ValueError("component action configuration must target its named component")
        if binding == "choice":
            if not isinstance(value, str) or not value:
                raise ValueError(f"choice binding {key!r} must be a non-empty string")
            if component_name in choices:
                raise ValueError(f"duplicate choice binding for component {component_name!r}")
            choices[component_name] = value
        else:
            _validate_scalar_binding(value, key)
            parameters.setdefault(component_name, {})[binding] = value

    unselected_parameters = set(parameters) - set(choices)
    if unselected_parameters:
        raise ValueError(
            "parameter bindings require an explicit '<component>.choice' for: "
            f"{sorted(unselected_parameters)}"
        )

    configured = copy.deepcopy(context.system)
    for component_name, choice in choices.items():
        alternatives = context.alternatives.get(component_name)
        if alternatives is None or choice not in alternatives:
            raise ValueError(f"unknown alternative {choice!r} for component {component_name!r}")
        replacement = copy.deepcopy(alternatives[choice])
        if replacement.name != component_name:
            raise ValueError(
                "replacement component name must preserve the configured target name "
                f"({component_name!r})"
            )
        configured = swap_component(configured, component_name, replacement)

    for component_name, bindings in parameters.items():
        component = copy.deepcopy(configured.get_component(component_name))
        runnable = component.metadata.get("runnable")
        if not isinstance(runnable, dict):
            raise ValueError(f"component {component_name!r} has no runnable specification")
        params = runnable.get("params")
        if params is None:
            raise ValueError(f"component {component_name!r} has no runnable params mapping")
        if not isinstance(params, dict):
            raise ValueError(f"component {component_name!r} runnable params must be a mapping")
        unknown = set(bindings) - set(params)
        if unknown:
            raise ValueError(
                f"unknown parameter(s) for component {component_name!r}: {sorted(unknown)}"
            )
        component.metadata = copy.deepcopy(component.metadata)
        component.metadata["runnable"] = copy.deepcopy(runnable)
        component.metadata["runnable"]["params"] = {**params, **bindings}
        configured = swap_component(configured, component_name, component)
    return configured


def _parse_binding(key: str) -> tuple[str, str]:
    if not isinstance(key, str) or key.count(".") != 1:
        raise ValueError(
            "configuration keys must be exactly '<component>.choice' or '<component>.<parameter>'"
        )
    component_name, binding = key.split(".")
    if not component_name or not binding:
        raise ValueError("configuration keys must have non-empty component and binding names")
    return component_name, binding


def _validate_scalar_binding(value: object, key: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError(f"configuration binding {key!r} must be a scalar")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"configuration binding {key!r} must be finite")


def _execute_system_action(
    system: System, context: EvaluationContext, runner: Runner
) -> dict[str, np.ndarray]:
    try:
        return build_feedforward_runner(system, dict(context.source_arrays), _safe_runner(runner))(
            system
        )
    except (
        ScientificInfeasibleError,
        TimeoutError,
        subprocess.TimeoutExpired,
        _ModelExecutionError,
        _InfrastructureExecutionError,
    ):
        raise
    except Exception as error:
        raise _ModelContractError(f"system execution failed: {error}") from error


def _execute_component_action(
    action: EvaluationAction, system: System, context: EvaluationContext, runner: Runner
) -> dict[str, np.ndarray]:
    component = system.get_component(action.component or "")
    inputs = _component_inputs(action, context, component.name)
    outputs = _safe_runner(runner)(component, inputs)
    if not isinstance(outputs, Mapping):
        raise _ModelContractError("component runner must return a mapping of output arrays")
    _validate_declared_outputs(component, outputs)
    flattened = {str(name): np.asarray(value) for name, value in outputs.items()}
    for name, value in outputs.items():
        flattened[f"{component.name}.{name}"] = np.asarray(value)
    return flattened


def _safe_runner(runner: Runner) -> Runner:
    """Classify failures at the runner boundary before other evaluator work begins."""

    def invoke(component: Component, inputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
        try:
            return runner(component, inputs)
        except (ScientificInfeasibleError, TimeoutError, subprocess.TimeoutExpired):
            raise
        except InfrastructureFailure as error:
            raise _InfrastructureExecutionError(
                f"runner explicitly reported infrastructure failure: {error}"
            ) from error
        except Exception as error:
            raise _ModelExecutionError(f"runner execution failed: {error}") from error

    return invoke


def _component_inputs(
    action: EvaluationAction, context: EvaluationContext, component_name: str
) -> dict[str, np.ndarray]:
    merged: dict[str, np.ndarray] = {}
    for artifact_id in action.parent_artifact_ids:
        reference = context.parent_artifacts.get(artifact_id)
        if reference is None:
            raise _ArtifactVerificationError(f"parent artifact {artifact_id!r} is not registered")
        try:
            data = _read_parent_artifact_bytes(
                reference.path, max_bytes=context.max_parent_artifact_bytes
            )
        except OSError as error:
            raise _ArtifactVerificationError(
                f"parent artifact {artifact_id!r} does not exist or cannot be read"
            ) from error
        if hashlib.sha256(data).hexdigest() != reference.sha256:
            raise _ArtifactVerificationError(
                f"parent artifact {artifact_id!r} SHA-256 does not match"
            )
        try:
            _validate_parent_npz(data, context)
            with np.load(io.BytesIO(data), allow_pickle=False) as parent:
                for name in parent.files:
                    merged[name] = np.array(parent[name], copy=True)
        except (OSError, ValueError) as error:
            raise _ArtifactVerificationError(
                f"parent artifact {artifact_id!r} is not a readable .npz file"
            ) from error
    # Explicit source arrays take precedence over parent arrays.  Qualified source
    # keys are also available by port suffix for direct component execution.
    for name, value in context.source_arrays.items():
        merged[name] = np.array(value, copy=True)
        if "." in name:
            merged[name.rsplit(".", 1)[1]] = np.array(value, copy=True)
    return merged


def _read_parent_artifact_bytes(path: Path, *, max_bytes: int) -> bytes:
    """Read one parent artifact exactly once for hash verification and loading."""
    descriptor = os.open(path, os.O_RDONLY)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise OSError("parent artifact is not a regular file")
        if metadata.st_size > max_bytes:
            raise OSError("parent artifact exceeds compressed byte limit")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise OSError("parent artifact exceeds compressed byte limit")
        return data
    finally:
        os.close(descriptor)


def _validate_parent_npz(data: bytes, context: EvaluationContext) -> None:
    """Reject unsafe NPZ metadata before NumPy can allocate an array."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > context.max_parent_artifact_members:
                raise _ArtifactVerificationError("parent artifact exceeds member-count limit")
            total = 0
            seen_names: set[str] = set()
            for member in members:
                logical_name = _logical_npz_name(member.filename)
                if logical_name in seen_names:
                    raise _ArtifactVerificationError("parent artifact has duplicate member names")
                seen_names.add(logical_name)
                total += member.file_size
                if member.file_size > context.max_parent_artifact_member_bytes:
                    raise _ArtifactVerificationError("parent artifact member exceeds byte limit")
                if total > context.max_parent_artifact_total_bytes:
                    raise _ArtifactVerificationError("parent artifact exceeds total byte limit")
                _validate_npy_member(archive, member, context)
    except _ArtifactVerificationError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        raise _ArtifactVerificationError("parent artifact is not a safe NPZ archive") from error


def _logical_npz_name(filename: str) -> str:
    if not isinstance(filename, str) or not filename.endswith(".npy"):
        raise _ArtifactVerificationError("parent artifact contains a non-NPY member")
    logical = filename.removesuffix(".npy")
    if "/" in logical or "\\" in logical or logical in {"", ".", ".."}:
        raise _ArtifactVerificationError("parent artifact member path is unsafe")
    if not _safe_output_name(logical):
        raise _ArtifactVerificationError("parent artifact member name is unsafe")
    return logical


def _validate_npy_member(
    archive: zipfile.ZipFile, member: zipfile.ZipInfo, context: EvaluationContext
) -> None:
    with archive.open(member) as handle:
        version = np.lib.format.read_magic(handle)
        if version == (1, 0):
            shape, _, dtype = np.lib.format.read_array_header_1_0(handle)
        elif version == (2, 0):
            shape, _, dtype = np.lib.format.read_array_header_2_0(handle)
        elif version == (3, 0):
            shape, _, dtype = np.lib.format.read_array_header_2_0(handle)
        else:
            raise _ArtifactVerificationError("parent artifact has an unsupported NPY version")
    if dtype.hasobject:
        raise _ArtifactVerificationError("parent artifact object arrays are not allowed")
    elements = 1
    for dimension in shape:
        if not isinstance(dimension, int) or dimension < 0:
            raise _ArtifactVerificationError("parent artifact has an invalid array shape")
        elements *= dimension
        if elements > context.max_parent_artifact_total_bytes:
            raise _ArtifactVerificationError("parent artifact declared array is too large")
    nbytes = elements * dtype.itemsize
    if nbytes > context.max_parent_artifact_member_bytes:
        raise _ArtifactVerificationError("parent artifact declared array exceeds byte limit")


def _validate_outputs(outputs: Mapping[str, np.ndarray]) -> None:
    if not isinstance(outputs, Mapping) or not outputs:
        raise _ModelContractError("runner must produce a non-empty output mapping")
    for name, value in outputs.items():
        if not isinstance(name, str) or not name:
            raise _ModelContractError("runner output names must be non-empty strings")
        if not _safe_output_name(name):
            raise _ModelContractError("runner output names must be safe NPZ logical names")
        array = np.asarray(value)
        if not np.issubdtype(array.dtype, np.number) or not np.all(np.isfinite(array)):
            raise ScientificInfeasibleError(
                f"runner output {name!r} must contain finite numeric values"
            )


def _safe_output_name(name: str) -> bool:
    if not isinstance(name, str) or not name or name in {".", ".."}:
        return False
    try:
        encoded = name.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return len(encoded) <= 255 and "\x00" not in name and "/" not in name and "\\" not in name


def _validate_declared_outputs(component: Component, outputs: Mapping[str, np.ndarray]) -> None:
    runnable = component.metadata.get("runnable")
    if not isinstance(runnable, Mapping):
        raise _ModelContractError(f"component {component.name!r} has no runnable specification")
    output_names = runnable.get("outputs", [])
    if not isinstance(output_names, list):
        raise _ModelContractError(f"component {component.name!r} runnable outputs must be a list")
    if any(not isinstance(name, str) or not name for name in output_names):
        raise _ModelContractError(
            f"component {component.name!r} runnable output names must be non-empty strings"
        )
    if len(set(output_names)) != len(output_names):
        raise _ModelContractError(
            f"component {component.name!r} runnable output names must be unique"
        )
    expected = set(output_names)
    actual = set(outputs)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(str(name) for name in actual - expected)
        raise _ModelContractError(
            f"component {component.name!r} outputs differ from declaration; "
            f"missing={missing}, extra={extra}"
        )


def _finite_outcome(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise _ModelContractError(f"outcome {name!r} must return a scalar float")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ScientificInfeasibleError(f"outcome {name!r} is non-finite")
    return numeric


def _replicate_artifact_id(action_id: str, replicate: int, count: int) -> str:
    return action_id if count == 1 else f"{action_id}-replicate-{replicate + 1:04d}"


def _write_artifact(
    directory: str | Path, artifact_id: str, outputs: Mapping[str, np.ndarray]
) -> tuple[Path, str]:
    """Persist one artifact using a retained POSIX root directory descriptor."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", artifact_id):
        raise _ArtifactStorageError("artifact action ID must be a safe filename")
    if os.name == "nt":
        return _write_artifact_windows_fallback(directory, artifact_id, outputs)
    try:
        root = _open_artifact_root(directory)
    except OSError as error:
        raise _ArtifactStorageError(f"could not open artifact root: {error}") from error
    try:
        return _write_artifact_at(root, artifact_id, outputs)
    finally:
        _close_fd(root.fd)


@dataclass(frozen=True)
class _ArtifactRoot:
    """Display path plus descriptor retained through the complete POSIX operation."""

    path: Path
    fd: int


def _write_artifact_at(
    root: _ArtifactRoot, artifact_id: str, outputs: Mapping[str, np.ndarray]
) -> tuple[Path, str]:
    destination = f"{artifact_id}.npz"
    raw_fd: int | None = None
    handle = None
    temporary: str | None = None
    temporary_stat: os.stat_result | None = None
    try:
        raw_fd, temporary = _create_temp_at(root.fd)
        temporary_stat = os.fstat(raw_fd)
        _assert_inode(temporary_stat, temporary_stat, nlink=1)
        try:
            handle = os.fdopen(raw_fd, "w+b")
            raw_fd = None
        except OSError:
            descriptor = raw_fd
            raw_fd = None
            _close_fd(descriptor)
            raise
        np.savez(handle, **{name: np.asarray(value) for name, value in outputs.items()})
        handle.flush()
        os.fsync(handle.fileno())
        finished_handle = handle
        handle = None
        _close_artifact_handle(finished_handle)
        _assert_at(root.fd, temporary, temporary_stat, nlink=1)
        digest = _hash_at(root.fd, temporary, temporary_stat, single_link=True)
        try:
            os.link(
                temporary,
                destination,
                src_dir_fd=root.fd,
                dst_dir_fd=root.fd,
                follow_symlinks=False,
            )
        except FileExistsError:
            if _replay_digest_at(root.fd, destination) != digest:
                raise _ArtifactStorageError(
                    "existing artifact has different bytes; refusing overwrite"
                )
        else:
            _assert_at(root.fd, destination, temporary_stat, nlink=2)
            if _hash_at(root.fd, destination, temporary_stat, single_link=False) != digest:
                raise _ArtifactStorageError("published artifact digest changed")
            _unlink_at(root.fd, temporary, temporary_stat, nlink=2)
            temporary = None
            _assert_at(root.fd, destination, temporary_stat, nlink=1)
            if _hash_at(root.fd, destination, temporary_stat, single_link=True) != digest:
                raise _ArtifactStorageError("published artifact changed after cleanup")
            os.fsync(root.fd)
        return root.path / destination, digest
    except _ArtifactStorageError:
        raise
    except OSError as error:
        raise _ArtifactStorageError(
            f"could not persist artifact {artifact_id!r}: {error}"
        ) from error
    finally:
        if handle is not None:
            try:
                _close_artifact_handle(handle)
            except _ArtifactStorageError:
                pass
        if raw_fd is not None:
            _close_fd(raw_fd)
        if temporary is not None and temporary_stat is not None:
            _cleanup_at(root.fd, temporary, temporary_stat)


def _create_temp_at(root_fd: int) -> tuple[int, str]:
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    for _ in range(32):
        name = f".{secrets.token_hex(16)}.tmp"
        try:
            return os.open(name, flags, 0o600, dir_fd=root_fd), name
        except FileExistsError:
            continue
    raise _ArtifactStorageError("could not allocate artifact temporary file")


def _open_artifact_root(directory: str | Path) -> _ArtifactRoot:
    raw, anchor, components = _lexical_absolute_artifact_path(directory)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(anchor, flags)
    try:
        _validate_artifact_dir(os.fstat(descriptor), final=not components)
        for index, part in enumerate(components):
            final = index == len(components) - 1
            try:
                metadata = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                os.mkdir(part, 0o700, dir_fd=descriptor)
                metadata = os.stat(part, dir_fd=descriptor, follow_symlinks=False)
            _validate_artifact_dir(metadata, final=final)
            next_descriptor: int | None = None
            try:
                next_descriptor = os.open(part, flags, dir_fd=descriptor)
                opened_metadata = os.fstat(next_descriptor)
                _validate_artifact_dir(opened_metadata, final=final)
                if (
                    opened_metadata.st_dev != metadata.st_dev
                    or opened_metadata.st_ino != metadata.st_ino
                ):
                    raise _ArtifactStorageError(
                        "artifact root directory changed between stat and open"
                    )
            except Exception:
                _close_fd(next_descriptor, suppress=True)
                raise
            previous_descriptor = descriptor
            descriptor = None
            try:
                _close_fd(previous_descriptor)
            except Exception:
                _close_fd(next_descriptor, suppress=True)
                raise
            descriptor = next_descriptor
        return _ArtifactRoot(raw, descriptor)
    except Exception:
        _close_fd(descriptor, suppress=True)
        raise


def _lexical_absolute_artifact_path(directory: str | Path) -> tuple[Path, str, tuple[str, ...]]:
    """Return an absolute artifact path without normalizing lexical components."""
    path = os.fspath(directory)
    if not isinstance(path, str):
        raise TypeError("artifact_dir must be a string or Path")
    absolute = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
    anchor = Path(absolute).anchor
    if not anchor:
        raise _ArtifactStorageError("artifact directory must be absolute")
    suffix = absolute[len(anchor) :]
    components = tuple(suffix.split(os.sep)) if suffix else ()
    if any(not part or part in {".", ".."} for part in components):
        raise _ArtifactStorageError("artifact directory contains unsafe lexical components")
    return Path(anchor, *components), anchor, components


def _validate_artifact_dir(metadata: os.stat_result, *, final: bool) -> None:
    if not stat.S_ISDIR(metadata.st_mode):
        raise _ArtifactStorageError("artifact root ancestry must contain real directories")
    mode = stat.S_IMODE(metadata.st_mode)
    if not final and mode & 0o022 and not metadata.st_mode & stat.S_ISVTX:
        raise _ArtifactStorageError("artifact root ancestor is group/world writable and non-sticky")
    if final and (metadata.st_uid != os.getuid() or mode & 0o077):
        raise _ArtifactStorageError("artifact root must be owner-private")


def _assert_inode(actual: os.stat_result, expected: os.stat_result, *, nlink: int) -> None:
    if (
        not stat.S_ISREG(actual.st_mode)
        or actual.st_dev != expected.st_dev
        or actual.st_ino != expected.st_ino
        or actual.st_nlink != nlink
    ):
        raise _ArtifactStorageError("artifact path identity changed")


def _assert_at(root_fd: int, name: str, expected: os.stat_result, *, nlink: int) -> None:
    _assert_inode(os.stat(name, dir_fd=root_fd, follow_symlinks=False), expected, nlink=nlink)


def _hash_at(root_fd: int, name: str, expected: os.stat_result, *, single_link: bool) -> str:
    descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=root_fd)
    try:
        metadata = os.fstat(descriptor)
        _assert_inode(metadata, expected, nlink=1 if single_link else metadata.st_nlink)
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            digest = _sha256_handle(handle)
        _assert_at(root_fd, name, expected, nlink=metadata.st_nlink)
        return digest
    finally:
        _close_fd(descriptor)


def _replay_digest_at(root_fd: int, name: str) -> str:
    metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    _assert_inode(metadata, metadata, nlink=1)
    digest = _hash_at(root_fd, name, metadata, single_link=True)
    _assert_at(root_fd, name, metadata, nlink=1)
    return digest


def _unlink_at(root_fd: int, name: str, expected: os.stat_result, *, nlink: int) -> None:
    _assert_at(root_fd, name, expected, nlink=nlink)
    os.unlink(name, dir_fd=root_fd)


def _cleanup_at(root_fd: int, name: str, expected: os.stat_result) -> None:
    try:
        _assert_at(root_fd, name, expected, nlink=1)
        os.unlink(name, dir_fd=root_fd)
    except (OSError, _ArtifactStorageError):
        pass


def _close_artifact_handle(handle) -> None:
    try:
        handle.close()
    except OSError as error:
        raise _ArtifactStorageError(f"could not close artifact temporary file: {error}") from error


def _close_fd(descriptor: int | None, *, suppress: bool = False) -> None:
    if descriptor is not None:
        try:
            os.close(descriptor)
        except OSError as error:
            if not suppress:
                raise _ArtifactStorageError(
                    f"could not close artifact descriptor: {error}"
                ) from error


def _write_artifact_windows_fallback(
    directory: Path, artifact_id: str, outputs: Mapping[str, np.ndarray]
) -> tuple[Path, str]:
    """Safe absolute-path fallback; Windows lacks the POSIX retained-dirfd guarantee."""
    root = Path(directory).absolute()
    root.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(prefix=".", suffix=".tmp", dir=root)
    temporary = Path(raw_temporary)
    destination = root / f"{artifact_id}.npz"
    try:
        with os.fdopen(descriptor, "w+b") as handle:
            np.savez(handle, **{name: np.asarray(value) for name, value in outputs.items()})
            handle.flush()
            os.fsync(handle.fileno())
        digest = _sha256(temporary)
        if destination.exists() and _sha256(destination) != digest:
            raise _ArtifactStorageError("existing artifact has different bytes; refusing overwrite")
        if not destination.exists():
            os.link(temporary, destination)
        return destination, digest
    except OSError as error:
        raise _ArtifactStorageError(
            f"could not persist artifact {artifact_id!r}: {error}"
        ) from error
    finally:
        temporary.unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_handle(handle) -> str:
    digest = hashlib.sha256()
    while chunk := handle.read(1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


@dataclass
class _EvaluationTimer:
    """One-shot timer that never retries a clock after it reports a bad value."""

    clock: Callable[[], float]
    started: float | None = None
    elapsed: float | None = None
    finish_error: _ClockError | None = None

    def start(self) -> None:
        self.started = _clock_value(self.clock)

    def finish(self) -> float:
        if self.elapsed is not None:
            return self.elapsed
        if self.finish_error is not None:
            raise self.finish_error
        if self.started is None:
            self.finish_error = _ClockError("clock did not provide a valid start timestamp")
            raise self.finish_error
        try:
            ended = _clock_value(self.clock)
            elapsed = ended - self.started
            if not math.isfinite(elapsed) or elapsed <= 0:
                raise _ClockError("clock timestamps must be strictly increasing")
            self.elapsed = elapsed
            return elapsed
        except _ClockError as error:
            self.finish_error = error
            raise


def _clock_value(clock: Callable[[], float]) -> float:
    try:
        value = clock()
    except Exception as error:
        raise _ClockError(f"clock failed: {error}") from error
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise _ClockError("clock must return a finite scalar number")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise _ClockError("clock must return a finite scalar number")
    return numeric


def _cost(elapsed: float, context: EvaluationContext) -> float:
    value = elapsed * float(context.cost_per_evaluator_second)
    if not math.isfinite(value) or value < 0:
        raise _CostError("measured evaluator cost is not finite")
    return value


def _failure_result(
    factory: Callable[..., EvaluationResult],
    action: EvaluationAction,
    context: EvaluationContext,
    error: Exception,
    artifacts: Mapping[str, str],
    digests: Mapping[str, str],
    *,
    elapsed: float,
) -> EvaluationResult:
    try:
        cost = _cost(elapsed, context)
    except _CostError as cost_error:
        factory = EvaluationResult.infrastructure_failure
        error = cost_error
        cost = 0.0
    try:
        return factory(
            action.id,
            str(error),
            cost=cost,
            cost_unit=context.cost_unit,
            artifacts=artifacts,
            artifact_sha256=digests,
            evaluator_seconds=elapsed,
        )
    except Exception:
        return EvaluationResult.infrastructure_failure(
            action.id,
            "could not construct evaluator failure result",
            cost=0.0,
            cost_unit=context.cost_unit,
            evaluator_seconds=0.0,
        )


def _timed_failure(
    factory: Callable[..., EvaluationResult],
    action: EvaluationAction,
    context: EvaluationContext,
    timer: _EvaluationTimer,
    error: Exception,
    artifacts: Mapping[str, str],
    digests: Mapping[str, str],
) -> EvaluationResult:
    try:
        elapsed = timer.finish()
    except _ClockError as clock_error:
        return _failure_result(
            EvaluationResult.infrastructure_failure,
            action,
            context,
            clock_error,
            artifacts,
            digests,
            elapsed=timer.elapsed or 0.0,
        )
    return _failure_result(
        factory,
        action,
        context,
        error,
        artifacts,
        digests,
        elapsed=elapsed,
    )
