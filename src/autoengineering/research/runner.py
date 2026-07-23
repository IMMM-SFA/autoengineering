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
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

import numpy as np

from autoengineering.system.component import Component
from autoengineering.system.graph import System


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
        raise ValueError(
            f"python runnable entry must be 'module:callable', got {entry!r}"
        )
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


def _run_python(
    spec: dict, inputs: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
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


def _run_command(
    spec: dict, inputs: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
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
        subprocess.run(
            cmd, shell=True, check=True, cwd=spec.get("sys_path") or None
        )

        if not out_path.exists():
            raise FileNotFoundError(
                f"command runnable did not write outputs to {out_path}"
            )
        loaded = np.load(out_path)
        missing = [n for n in output_names if n not in loaded]
        if missing:
            raise KeyError(f"command outputs.npz missing array(s): {missing}")
        return {n: loaded[n] for n in output_names}


def run_component(
    component: Component, inputs: dict[str, np.ndarray]
) -> dict[str, np.ndarray]:
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
                    available[f"{comp_name}.{port.name}"] = _source_value(
                        comp_name, port.name
                    )
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
            for port_name, arr in outputs.items():
                available[f"{comp_name}.{port_name}"] = arr

        # Expose bare port names too, last-writer-wins, for convenient scoring.
        flat = dict(available)
        for key, arr in available.items():
            flat[key.split(".", 1)[1]] = arr
        return flat

    return run_chain
