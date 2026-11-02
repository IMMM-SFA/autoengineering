"""Verify original wind jobs/results and archived sources without wind imports."""

import builtins
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.store import durable_write
from autoengineering.utility.engineering_process import (
    EngineeringScenarioJob,
    EngineeringScenarioResult,
)
from autoengineering.utility.outcomes import EngineeringEvaluation

root = Path("examples/utility/development/wind-scenario-v2").absolute()
batch = BatchStore(root / "batch")
original_state = batch.replay()
jobs = {}
refs = {}


def document(relative):
    path = confined_file(batch.root, relative)
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("wind reader input exceeds size limit")
    return unique_json(path.read_text())


for reservation in original_state.reservations.values():
    folder = f"cases/{reservation.case_id}/engineering-processes/{reservation.invocation_digest}"
    job = EngineeringScenarioJob.from_dict(document(folder + "/scenario.json"))
    jobs[reservation.case_id] = (reservation, folder, job)
    for ref in (*job.execution.sources, job.execution.lock):
        if ref.path in refs and refs[ref.path] != ref:
            raise ValueError("wind jobs have conflicting source identities")
        refs[ref.path] = ref
# Archive only bytes already bound to original execution. This is not a model run.
archive = root / "archived-sources"
archive.mkdir(mode=0o700, exist_ok=True)
for ref in refs.values():
    raw = read_bytes(root / "captured", ref)
    path = archive / ref.path
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists():
        read_bytes(archive, ref)
    else:
        durable_write(path, raw)
original_import = importlib.import_module


def denied(*args, **kwargs):
    raise AssertionError("Wind reader attempted model/network/process dispatch")


def guarded_import(name, *args, **kwargs):
    if name.startswith(("examples.", "py_wake", "topfarm", "openmdao")):
        raise AssertionError("Wind reader imported a scientific implementation")
    return original_import(name, *args, **kwargs)


def guarded_open(original):
    def opened(path, *args, **kwargs):
        if not isinstance(path, int) and Path(os.fsdecode(path)).absolute().is_relative_to(
            root / "captured"
        ):
            raise AssertionError("Wind reader accessed original captured inputs")
        return original(path, *args, **kwargs)

    return opened


with (
    patch("subprocess.Popen", denied),
    patch("socket.socket", denied),
    patch("importlib.import_module", guarded_import),
    patch("os.open", guarded_open(os.open)),
    patch("builtins.open", guarded_open(builtins.open)),
    patch("io.open", guarded_open(io.open)),
):
    state = batch.replay()
    assert len(state.reservations) == len(state.observations) == len(state.finished) == 2
    assert not state.pending
    metrics = []
    for case, (reservation, folder, job) in jobs.items():
        binding = document(f"cases/{case}/engineering-processes/execution.json")
        assert digest(binding) == job.binding_digest
        assert binding["execution"] == job.execution.to_dict()
        assert binding["source_root"] == job.source_root
        completion = document(folder + "/process/completion.json")
        process_job = confined_file(batch.root, folder + "/process/job.json").read_bytes()
        assert hashlib.sha256(process_job).hexdigest() == completion["job_sha256"]
        assert (
            completion["status"] == "completed"
            and completion["returncode"] == 0
            and completion["stopped"]
        )
        assert (
            completion["identity"]["nonce"] == "engineering-" + reservation.invocation_digest[:32]
        )
        stdout = ArtifactRef(
            folder + "/process/stdout.bin",
            completion["stdout_sha256"],
            completion["stdout_bytes"],
            "application/json",
            "original-supervisor",
            {},
        )
        result = EngineeringScenarioResult.from_json(
            read_bytes(batch.root, stdout, max_bytes=job.execution.output_bytes).decode()
        )
        assert result.job_digest == job.digest and result.score.scenario_id == job.scenario_id
        assert all(c.required and c.status == "pass" for c in result.score.checks)
        assert {c.name for c in result.score.checks} == {
            c.name for c in job.execution.study.rules.checks
        }
        assert result.solver_work == {"wind_evaluations": 1.0} and result.solver_units == {
            "wind_evaluations": "count"
        }
        observation = state.observations[reservation.id]
        assert observation.stop_verified and observation.status == "success"
        proof = unique_json(read_bytes(batch.root, observation.evidence[0]).decode())
        assert proof["job_digest"] == job.digest and proof["result"] == result.to_dict()
        assert proof["process_identity"] == completion["identity"]
        finished = state.finished[case]
        assert finished.status == "passed"
        recorded = unique_json(read_bytes(batch.root, finished.evidence[0]).decode())
        evaluation = EngineeringEvaluation.from_dict(recorded["result"])
        assert evaluation.scenarios == (result.score,) and evaluation.evaluation.eligible
        assert evaluation.evaluation.configuration == job.configuration
        metrics.append(evaluation.evaluation.metrics["annual_energy"])
    assert math.isclose(*metrics, rel_tol=1e-12, abs_tol=0.0)
    for ref in refs.values():
        read_bytes(archive, ref)
summary = {
    "cases": 2,
    "original_process_stops_verified": 2,
    "modelled_annual_energy_GWh": metrics,
    "parity": "passed",
    "source_files_verified": len(refs),
    "models_network_processes": "denied",
    "original_captured_source_access": "denied_after_archive",
    "reader_runtime": "base without PyWake/TOPFARM",
    "relocation": "not_attempted",
    "confirmation": "not_attempted",
    "utility_verdict": "not_attempted",
}
Path("examples/utility/verification-wind-parameters-v1/offline-reader.json").write_text(
    json.dumps(summary, indent=2) + "\n"
)
print(json.dumps(summary))
