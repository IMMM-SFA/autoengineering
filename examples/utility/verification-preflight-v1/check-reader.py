"""Verify the rejected action offline without model code or captured input reads."""

import builtins
import importlib
import io
import json
import os
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.optimization import EvaluationAction
from autoengineering.utility.engineering_process import EngineeringExecutionSpec
from autoengineering.utility.outcomes import EngineeringEvaluation
from autoengineering.utility.preflight import verify_rejection

root = Path("examples/utility/development/wind-preflight-v1").absolute()
forbidden = root / "captured"
original_import = importlib.import_module
original_builtin = builtins.__import__


def denied(*args, **kwargs):
    raise AssertionError("Offline reader attempted process/network dispatch")


def guarded_import(name, *args, **kwargs):
    if name.startswith(("examples.", "py_wake", "topfarm", "openmdao", "pvlib")):
        raise AssertionError("Offline reader imported a scientific implementation")
    return original_import(name, *args, **kwargs)


def guarded_builtin(name, globals=None, locals=None, fromlist=(), level=0):
    if name.startswith(("examples.", "py_wake", "topfarm", "openmdao", "pvlib")):
        raise AssertionError("Offline reader imported a scientific implementation")
    return original_builtin(name, globals, locals, fromlist, level)


def guarded_open(original):
    def opened(path, *args, **kwargs):
        if not isinstance(path, int) and Path(os.fsdecode(path)).absolute().is_relative_to(forbidden):
            raise AssertionError("Offline reader accessed original captured inputs")
        return original(path, *args, **kwargs)

    return opened


with (
    patch("subprocess.Popen", denied),
    patch("socket.socket", denied),
    patch("importlib.import_module", guarded_import),
    patch("builtins.__import__", guarded_builtin),
    patch("builtins.open", guarded_open(builtins.open)),
    patch("io.open", guarded_open(io.open)),
    patch("os.open", guarded_open(os.open)),
):
    spec = EngineeringExecutionSpec.from_json((root / "execution.json").read_text())
    batch = BatchStore(root / "batch")
    state = batch.replay()
    before = (len(state.events), len(state.reservations), len(state.observations))
    proof = unique_json(read_bytes(batch.root, state.finished["wind"].evidence[0]).decode())
    action = EvaluationAction.from_dict(proof["rejected_action"])
    value = EngineeringEvaluation.from_dict(proof["rejected"])
    binding = unique_json(
        (batch.root / "cases/wind/engineering-processes/execution.json").read_text()
    )
    assert verify_rejection(spec, digest(binding), batch, "wind", action, value)
    assert len(state.reservations) == len(state.observations) == 1 and not state.pending
    assert all(o.stop_verified for o in state.observations.values())
    current = batch.replay()
    assert before == (len(current.events), len(current.reservations), len(current.observations))
    summary = {
        "rejected_action": action.id,
        "status": value.evaluation.status,
        "rejected_model_starts": 0,
        "total_reservations": 1,
        "new_events": 0,
        "model_imports_and_dispatch": "denied",
        "captured_input_reads": "denied",
        "scope": "preflight rejection and physical stop accounting, not feasible output replay",
    }
(root / "reader-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
