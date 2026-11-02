"""Reconstruct native wind work and its separate fresh evaluation from saved bytes."""

import builtins
import hashlib
import importlib
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.utility.engineering_process import (
    EngineeringScenarioJob,
    EngineeringScenarioResult,
)
from autoengineering.utility.outcomes import EngineeringEvaluation
from examples.utility.wind_process import (
    WindDriverReport,
    WindDriverJob,
    cost_records,
    verify_report,
)

root = Path("examples/utility/development/wind-native-process-v1").absolute()
batch = BatchStore(root / "batch")
state = batch.replay()
assert len(state.finished) == 1 and not state.pending
proof = unique_json(read_bytes(batch.root, state.finished["native"].evidence[0]).decode())
report = WindDriverReport.from_dict(proof["native"])
native_root = batch.root / "cases/native/native-drivers" / report.specification_digest
job = WindDriverJob.from_json(confined_file(native_root, "job.json").read_text())
original_import = importlib.import_module
original_builtin_import = builtins.__import__
for prefix in ("py_wake", "topfarm", "openmdao"):
    assert not any(n == prefix or n.startswith(prefix + ".") for n in sys.modules)


def guarded_builtin_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name.startswith(("py_wake", "topfarm", "openmdao", "examples.open_chains.wind")):
        raise AssertionError("Wind native reader imported a scientific implementation")
    return original_builtin_import(name, globals, locals, fromlist, level)


def denied(*args, **kwargs):
    raise AssertionError("Wind native reader attempted dispatch")


def guarded_import(name, *args, **kwargs):
    if name.startswith(("py_wake", "topfarm", "openmdao", "examples.open_chains.wind")):
        raise AssertionError("Wind native reader imported a scientific implementation")
    return original_import(name, *args, **kwargs)


def guarded_open(original):
    def opened(path, *args, **kwargs):
        if not isinstance(path, int) and Path(os.fsdecode(path)).absolute().is_relative_to(
            root / "captured"
        ):
            raise AssertionError("Wind native reader read original captured source")
        return original(path, *args, **kwargs)

    return opened


# Archive only exact bytes bound to the original job before denying source access.
archive = root / "archived-sources"
for ref in (*job.specification.execution.sources, job.specification.execution.lock):
    raw = read_bytes(root / "captured", ref)
    target = archive / ref.path
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.exists():
        assert target.read_bytes() == raw
    else:
        target.write_bytes(raw)
with (
    patch("subprocess.Popen", denied),
    patch("socket.socket", denied),
    patch("importlib.import_module", guarded_import),
    patch("builtins.__import__", guarded_builtin_import),
    patch("os.open", guarded_open(os.open)),
    patch("builtins.open", guarded_open(builtins.open)),
    patch("io.open", guarded_open(io.open)),
):
    verify_report(batch, "native", job.specification, report)
    state = batch.replay()
    assert len(state.reservations) == len(state.observations) == 2 and not state.pending
    assert all(o.stop_verified for o in state.observations.values())
    assert report.status == "success" and report.result.proposal.configuration is not None
    fresh = EngineeringEvaluation.from_dict(proof["fresh"])
    assert (
        fresh.evaluation.eligible
        and fresh.evaluation.configuration == report.result.proposal.configuration
    )
    reservation = next(r for r in state.reservations.values() if r.id != report.reservation_id)
    folder = batch.root / "cases/native/engineering-processes" / reservation.invocation_digest
    scenario = EngineeringScenarioJob.from_json(confined_file(folder, "scenario.json").read_text())
    binding = unique_json(confined_file(folder.parent, "execution.json").read_text())
    assert digest(binding) == scenario.binding_digest
    assert (
        binding["execution"]
        == scenario.execution.to_dict()
        == job.specification.execution.to_dict()
    )
    assert scenario.configuration == fresh.evaluation.configuration
    completion = unique_json(confined_file(folder, "process/completion.json").read_text())
    assert (
        completion["stopped"]
        and completion["returncode"] == 0
        and completion["status"] == "completed"
    )
    assert (
        hashlib.sha256(confined_file(folder, "process/job.json").read_bytes()).hexdigest()
        == completion["job_sha256"]
    )
    assert completion["identity"]["nonce"] == "engineering-" + reservation.invocation_digest[:32]
    stdout = ArtifactRef(
        "process/stdout.bin",
        completion["stdout_sha256"],
        completion["stdout_bytes"],
        "application/json",
        "original-supervisor",
        {},
    )
    result = EngineeringScenarioResult.from_json(
        read_bytes(folder, stdout, max_bytes=scenario.execution.output_bytes).decode()
    )
    assert result.job_digest == scenario.digest and fresh.scenarios == (result.score,)
    observation = state.observations[reservation.id]
    observed = unique_json(read_bytes(batch.root, observation.evidence[0]).decode())
    assert observed["job_digest"] == scenario.digest and observed["result"] == result.to_dict()
    assert observed["process_identity"] == completion["identity"]
    assert all(c.required and c.status == "pass" for c in result.score.checks)
    assert {c.name for c in result.score.checks} == {
        c.name for c in scenario.execution.study.rules.checks
    }
    for ref in (*job.specification.execution.sources, job.specification.execution.lock):
        read_bytes(archive, ref)
    costs = cost_records(report, "0" * 64)
summary = {
    "status": "passed",
    "science_reservations": 2,
    "observed_stops": 2,
    "native_driver_status": report.result.proposal.result.status,
    "native_callback_work": report.result.proposal.work,
    "fresh_modelled_annual_energy_GWh": fresh.evaluation.metrics["annual_energy"],
    "source_files_verified": len(job.specification.execution.sources) + 1,
    "native_costs": [c.to_dict() for c in costs],
    "scientific_imports_network_dispatch": "denied",
    "original_captured_source_access": "denied_after_archive",
    "confirmation": "not_attempted",
    "utility_verdict": "not_attempted",
}
Path("examples/utility/verification-wind-process-v1/offline-reader.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)
print(json.dumps({k: v for k, v in summary.items() if k != "native_costs"}))
