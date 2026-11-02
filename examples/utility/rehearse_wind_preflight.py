"""Reject impossible geometry before dispatch, then run one feasible wind scenario."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.records import HostSelection, ResourceLimits
from autoengineering.campaign.artifacts import reference
from autoengineering.optimization import EvaluationAction
from autoengineering.utility.engineering_process import (
    SupervisedEngineeringExecutor,
    execution_identity,
)
from examples.utility.rehearse_wind_scenario import prepare
from examples.utility.wind import ROOT


def run(output):
    output, source, geometry, executions = prepare(output)
    spec = executions[1]
    name = "examples/utility/rehearse_wind_preflight.py"
    (source / name).write_bytes((ROOT / name).read_bytes())
    refs = (
        *spec.sources,
        reference(source, name, media_type="text/plain", producer="preflight-development"),
    )
    identity = execution_identity(
        spec.entrypoint,
        refs,
        spec.lock,
        spec.scenarios,
        spec.timeout_seconds,
        spec.output_bytes,
        profile="supervised-engineering-v3",
        preflight=spec.preflight,
    )
    spec = replace(spec, sources=refs, study=replace(spec.study, source_identity=identity))
    batch_spec = BatchSpec(
        "1.0",
        "wind-preflight-development",
        host_source_identity(),
        host_environment_identity(),
        HostSelection("fake", "none", "unused", "1.0"),
        FakeHost(()).capabilities(),
        spec.digest,
        ResourceLimits(1, 1, 0, 0, 180.0, 10.0, 8388608, 1048576),
        1,
        (BatchCase("wind", "comparison", spec.digest, 0, 1),),
    )
    batch = BatchStore.create(output / "batch", batch_spec)
    batch.start_case("wind", spec.digest)
    executor = SupervisedEngineeringExecutor(spec, batch, "wind", source)
    invalid = dict(geometry.baseline)
    invalid["x_1"] = invalid["x_0"]
    invalid["y_1"] = invalid["y_0"]
    bad = EvaluationAction.system(
        "too-close", invalid, seed=17, suggested_by="preflight-development"
    )

    def denied(*args, **kwargs):
        raise AssertionError("infeasible point dispatched a model process")

    print("Wind preflight: invalid layout, dispatch denied", flush=True)
    with patch("autoengineering.utility.engineering_process.supervise_process", denied):
        rejected = executor(bad)
        assert executor.recover_completed(bad) == rejected
    assert rejected.evaluation.status == "scientific_infeasible" and not batch.replay().reservations
    valid = EvaluationAction.system(
        "baseline", geometry.baseline, seed=17, suggested_by="preflight-development"
    )
    print("Wind preflight: feasible baseline, one supervised process", flush=True)
    fresh = executor(valid)
    assert fresh.evaluation.status == "success" and fresh.evaluation.eligible
    proof = batch.evidence(
        {
            "rejected_action": bad.to_dict(),
            "rejected": rejected.to_dict(),
            "feasible_action": valid.to_dict(),
            "feasible": fresh.to_dict(),
        }
    )
    batch.finish_case("wind", "passed", (proof,))
    count = len(batch.replay().reservations)
    assert (
        executor.recover_completed(bad) == rejected and executor.recover_completed(valid) == fresh
    )
    assert count == len(batch.replay().reservations) == 1 and not batch.replay().pending
    (output / "execution.json").write_text(spec.to_json())
    summary = {
        "purpose": "bundled wind preflight development, not independent weather",
        "rejected_status": rejected.evaluation.status,
        "rejected_model_starts": 0,
        "physical_reservations": 1,
        "observed_stops": len(batch.replay().observations),
        "feasible_annual_energy_GWh": fresh.evaluation.metrics["annual_energy"],
        "completed_recovery_added_reservations": 0,
        "execution": spec.digest,
        "confirmation": "not_attempted",
        "utility_verdict": "not_attempted",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
