"""A fresh installed reader verifies a completed case without attaching an executor."""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.serialization import unique_json
from autoengineering.utility.callback_native import CallbackDriverJob, CallbackDriverReport
from autoengineering.utility.engineering_native import verify_native_report
from autoengineering.utility.engineering_process import (
    EngineeringScenarioJob,
    EngineeringScenarioResult,
)
from autoengineering.utility.outcomes import EngineeringEvaluation

parser = argparse.ArgumentParser()
parser.add_argument("root", type=Path)
args = parser.parse_args()
root = args.root.resolve()
batch = BatchStore(root / "batch")
before = batch.replay()
count = len(list((batch.root / "events").glob("*.json")))


def denied(*args, **kwargs):
    raise AssertionError("completed resume attempted physical dispatch")


with patch("subprocess.Popen", denied):
    proof = unique_json(read_bytes(batch.root, before.finished["wind"].evidence[0]).decode())
    report = CallbackDriverReport.from_dict(proof["native"])
    folder = batch.root / "cases/wind/native-drivers" / report.specification_digest
    job = CallbackDriverJob.from_json(confined_file(folder, "job.json").read_text())
    verify_native_report(batch, "wind", job.specification, report)
    fresh = EngineeringEvaluation.from_dict(proof["fresh"])
    assert (
        fresh.evaluation.eligible and fresh.evaluation.configuration == report.result.configuration
    )
    reservation = next(r for r in before.reservations.values() if r.id != report.reservation_id)
    scenario_folder = (
        batch.root / "cases/wind/engineering-processes" / reservation.invocation_digest
    )
    scenario = EngineeringScenarioJob.from_json(
        confined_file(scenario_folder, "scenario.json").read_text()
    )
    assert scenario.configuration == fresh.evaluation.configuration
    observation = before.observations[reservation.id]
    observed = unique_json(read_bytes(batch.root, observation.evidence[0]).decode())
    result = EngineeringScenarioResult.from_dict(observed["result"])
    assert result.job_digest == scenario.digest == observed["job_digest"]
    assert fresh.scenarios == (result.score,) and observation.stop_verified
    assert all(c.status == "pass" for c in result.score.checks)
    after = batch.replay()
    assert before.reservations == after.reservations and before.observations == after.observations
    assert len(list((batch.root / "events").glob("*.json"))) == count
summary = {
    "status": "passed",
    "new_science_reservations": 0,
    "new_observations": 0,
    "new_batch_events": 0,
    "fresh_modelled_energy_GWh": fresh.evaluation.metrics["annual_energy"],
    "scope": "fresh installed interpreter, completed-case receipt verification; no executor or model dispatch",
}
(root / "resume-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
