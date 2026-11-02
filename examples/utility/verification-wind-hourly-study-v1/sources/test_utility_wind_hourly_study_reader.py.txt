"""Archived stop receipts reconstruct without current process or model access."""

from pathlib import Path
import shutil

import pytest

from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.utility.engineering_process import (
    EngineeringExecutionSpec,
    decode_scenario,
    EngineeringScenarioJob,
)
from examples.utility.wind_hourly_study_reader import read_stopped_process

ARCHIVE = (
    Path(__file__).resolve().parents[1]
    / "examples/utility/verification-wind-hourly-study-v1/public"
)


def inputs(tmp_path):
    spec = EngineeringExecutionSpec.from_dict(
        unique_json((ARCHIVE / "request.json").read_text())["execution"]
    )
    scenario = next(
        (ARCHIVE / "batch/cases/hourly-development/engineering-processes").glob("*/scenario.json")
    )
    shutil.copytree(scenario.parent / "process", tmp_path / "process")
    return spec, scenario, tmp_path / "process"


def test_saved_receipts_reconstruct_without_process_or_clock(tmp_path, monkeypatch):
    spec, scenario, directory = inputs(tmp_path)

    def denied(*a, **kw):
        pytest.fail("offline reader inspected or started a process")

    monkeypatch.setattr("autoengineering.agents.process.live_members", denied)
    monkeypatch.setattr("subprocess.Popen", denied)
    monkeypatch.setattr("time.time", denied)
    result = read_stopped_process(directory, ARCHIVE / "source", spec.sources, spec.output_bytes)
    job = EngineeringScenarioJob.from_json(scenario.read_text())
    status, decoded = decode_scenario(job, result)
    assert status == "success" and result.stopped
    assert decoded.solver_work == {"wind_evaluations": 1.0}


@pytest.mark.parametrize(
    "change",
    [
        "stdout",
        "nonce",
        "stop",
        "reason",
        "duration",
        "source",
        "cap",
        "job",
        "bool_exit",
        "float_exit",
    ],
)
def test_changed_saved_receipts_refuse(tmp_path, change):
    spec, _, directory = inputs(tmp_path)
    files = {
        "nonce": "intent.json",
        "stop": "watchdog-result.json",
        "reason": "watchdog-result.json",
        "duration": "completion.json",
        "source": "watchdog-job.json",
    }
    if change == "stdout":
        (directory / "stdout.bin").write_bytes(b"altered")
    elif change == "job":
        with (directory / "job.json").open("ab") as f:
            f.write(b" ")
    elif change in ("bool_exit", "float_exit"):
        path = directory / "completion.json"
        value = unique_json(path.read_text())
        value["returncode"] = False if change == "bool_exit" else 0.0
        path.write_text(canonical_json(value))
    elif change in files:
        path = directory / files[change]
        value = unique_json(path.read_text())
        key = {
            "nonce": "nonce",
            "stop": "stopped",
            "reason": "reason",
            "duration": "elapsed_seconds",
            "source": "worker_sha256",
        }[change]
        value[key] = {
            "nonce": "different",
            "stop": False,
            "reason": "timeout",
            "duration": -1.0,
            "source": "0" * 64,
        }[change]
        path.write_text(canonical_json(value))
    with pytest.raises(ValueError):
        read_stopped_process(
            directory, ARCHIVE / "source", spec.sources, 1 if change == "cap" else spec.output_bytes
        )
