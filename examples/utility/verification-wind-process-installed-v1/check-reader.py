"""Reconstruct native wind work and its separate fresh evaluation from saved bytes."""

import argparse
import builtins
import hashlib
import importlib
import io
import json
import os
import sys

import autoengineering
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

parser = argparse.ArgumentParser()
parser.add_argument("archive", type=Path)
parser.add_argument("--forbidden", required=True, type=Path)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
root = args.archive.absolute()
forbidden = args.forbidden.resolve()
assert Path(autoengineering.__file__).resolve().is_relative_to(Path(sys.prefix))
assert not Path(autoengineering.__file__).resolve().is_relative_to(forbidden)
batch = BatchStore(root / "batch")
state = batch.replay()
assert len(state.finished) == 1 and not state.pending
proof = unique_json(read_bytes(batch.root, state.finished["native"].evidence[0]).decode())
report = WindDriverReport.from_dict(proof["native"])
native_root = batch.root / "cases/native/native-drivers" / report.specification_digest
job = WindDriverJob.from_json(confined_file(native_root, "job.json").read_text())
installed_package = Path(autoengineering.__file__).resolve().parent
installed_site = installed_package.parent
assert (
    Path(sys.modules[WindDriverReport.__module__].__file__).resolve().is_relative_to(installed_site)
)
installed_sources_verified = 0
for ref in job.specification.execution.sources:
    if ref.path.startswith("src/autoengineering/"):
        installed = installed_package / ref.path.removeprefix("src/autoengineering/")
    elif ref.path.startswith("examples/utility/"):
        installed = installed_site / ref.path
    else:
        continue
    assert hashlib.sha256(installed.read_bytes()).hexdigest() == ref.sha256
    installed_sources_verified += 1
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
            forbidden
        ):
            raise AssertionError("Wind native reader read original captured source")
        return original(path, *args, **kwargs)

    return opened


archive = root / "archived-sources"
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
    "installed_package": autoengineering.__file__,
    "installed_sources_verified": installed_sources_verified,
    "science_reservations": 2,
    "observed_stops": 2,
    "native_driver_status": report.result.proposal.result.status,
    "native_callback_work": report.result.proposal.work,
    "fresh_modelled_annual_energy_GWh": fresh.evaluation.metrics["annual_energy"],
    "source_files_verified": len(job.specification.execution.sources) + 1,
    "native_costs": [c.to_dict() for c in costs],
    "scientific_imports_network_dispatch": "denied",
    "original_captured_source_access": "denied_for_original_checkout",
    "confirmation": "not_attempted",
    "utility_verdict": "not_attempted",
}
args.output.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "native_costs"}))
