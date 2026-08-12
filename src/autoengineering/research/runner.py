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
import math
import os
import subprocess
import sys
import tempfile
import time
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


class _ModelContractError(Exception):
    """A runnable or outcome callable did not meet the evaluator contract."""


class _ArtifactVerificationError(Exception):
    """A required artifact could not be safely loaded or verified."""


class _ArtifactStorageError(Exception):
    """A produced artifact could not be durably persisted."""


class _ModelExecutionError(Exception):
    """A runner raised while evaluating a declared model."""


class _InfrastructureExecutionError(Exception):
    """A runner failed because of an operating-system service or filesystem error."""


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
    ``cost_unit``; successful calls have a one-machine-epsilon minimum charge so a
    completed attempt is never recorded as free when a test clock has zero ticks.

    The action seed is durable provenance.  The runner protocol has no seed
    argument, so runners that use randomness must consume an explicitly configured
    seed; this evaluator never mutates NumPy's global random state.
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

    def __post_init__(self) -> None:
        if not isinstance(self.system, System):
            raise TypeError("system must be a System")
        if not isinstance(self.cost_unit, str) or not self.cost_unit.strip():
            raise ValueError("cost_unit must be a non-empty string")
        if (
            isinstance(self.cost_per_evaluator_second, bool)
            or not isinstance(self.cost_per_evaluator_second, (int, float))
            or not math.isfinite(self.cost_per_evaluator_second)
            or self.cost_per_evaluator_second <= 0
        ):
            raise ValueError("cost_per_evaluator_second must be a positive finite number")
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
                frozen_choices[choice] = component
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
            object.__setattr__(self, "artifact_dir", Path(self.artifact_dir).expanduser().resolve())
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
    started = clock()
    artifacts: dict[str, str] = {}
    digests: dict[str, str] = {}
    try:
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
        elapsed = _elapsed(started, clock)
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
            _cost(elapsed, context, completed=True),
            context.cost_unit,
            artifacts=artifacts,
            artifact_sha256=digests,
            evaluator_seconds=elapsed,
        )
    except ScientificInfeasibleError as error:
        return _failure_result(
            EvaluationResult.scientific_infeasible,
            action,
            context,
            started,
            clock,
            error,
            artifacts,
            digests,
        )
    except (TimeoutError, subprocess.TimeoutExpired) as error:
        return _failure_result(
            EvaluationResult.timeout, action, context, started, clock, error, artifacts, digests
        )
    except (
        _ArtifactVerificationError,
        _ArtifactStorageError,
        _InfrastructureExecutionError,
    ) as error:
        return _failure_result(
            EvaluationResult.infrastructure_failure,
            action,
            context,
            started,
            clock,
            error,
            artifacts,
            digests,
        )
    except Exception as error:
        return _failure_result(
            EvaluationResult.model_failure,
            action,
            context,
            started,
            clock,
            error,
            artifacts,
            digests,
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
        except OSError as error:
            raise _InfrastructureExecutionError(
                f"runner infrastructure failure: {error}"
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
        if not reference.path.is_file():
            raise _ArtifactVerificationError(f"parent artifact {artifact_id!r} does not exist")
        if _sha256(reference.path) != reference.sha256:
            raise _ArtifactVerificationError(
                f"parent artifact {artifact_id!r} SHA-256 does not match"
            )
        try:
            with np.load(reference.path, allow_pickle=False) as parent:
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


def _validate_outputs(outputs: Mapping[str, np.ndarray]) -> None:
    if not isinstance(outputs, Mapping) or not outputs:
        raise _ModelContractError("runner must produce a non-empty output mapping")
    for name, value in outputs.items():
        if not isinstance(name, str) or not name:
            raise _ModelContractError("runner output names must be non-empty strings")
        array = np.asarray(value)
        if not np.issubdtype(array.dtype, np.number) or not np.all(np.isfinite(array)):
            raise ScientificInfeasibleError(
                f"runner output {name!r} must contain finite numeric values"
            )


def _validate_declared_outputs(component: Component, outputs: Mapping[str, np.ndarray]) -> None:
    runnable = component.metadata.get("runnable")
    if not isinstance(runnable, Mapping):
        raise _ModelContractError(f"component {component.name!r} has no runnable specification")
    output_names = runnable.get("outputs", [])
    if not isinstance(output_names, list):
        raise _ModelContractError(f"component {component.name!r} runnable outputs must be a list")
    missing = [name for name in output_names if name not in outputs]
    if missing:
        raise _ModelContractError(
            f"component {component.name!r} did not produce declared output(s): {missing}"
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
    directory: Path, artifact_id: str, outputs: Mapping[str, np.ndarray]
) -> tuple[Path, str]:
    try:
        directory.mkdir(parents=True, exist_ok=True)
        destination = (directory / f"{artifact_id}.npz").resolve()
        temporary = directory / f".{artifact_id}.tmp"
        with temporary.open("wb") as handle:
            np.savez(handle, **{name: np.asarray(value) for name, value in outputs.items()})
            handle.flush()
            os.fsync(handle.fileno())
        digest = _sha256(temporary)
        if destination.exists():
            if _sha256(destination) != digest:
                raise _ArtifactStorageError(
                    f"artifact {destination} exists with different bytes; refusing overwrite"
                )
            temporary.unlink()
        else:
            os.replace(temporary, destination)
        return destination, digest
    except _ArtifactStorageError:
        raise
    except OSError as error:
        raise _ArtifactStorageError(
            f"could not persist artifact {artifact_id!r}: {error}"
        ) from error


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _elapsed(started: float, clock: Callable[[], float]) -> float:
    return max(0.0, float(clock()) - float(started))


def _cost(elapsed: float, context: EvaluationContext, *, completed: bool) -> float:
    measured = elapsed * float(context.cost_per_evaluator_second)
    return max(measured, np.finfo(float).eps) if completed else measured


def _failure_result(
    factory: Callable[..., EvaluationResult],
    action: EvaluationAction,
    context: EvaluationContext,
    started: float,
    clock: Callable[[], float],
    error: Exception,
    artifacts: Mapping[str, str],
    digests: Mapping[str, str],
) -> EvaluationResult:
    elapsed = _elapsed(started, clock)
    return factory(
        action.id,
        str(error),
        cost=_cost(elapsed, context, completed=False),
        cost_unit=context.cost_unit,
        artifacts=artifacts,
        artifact_sha256=digests,
        evaluator_seconds=elapsed,
    )
