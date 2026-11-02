"""One bounded TOPFARM process followed by a separately reserved wind evaluation."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.records import HostSelection, ResourceLimits
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import digest
from autoengineering.optimization import EvaluationAction
from autoengineering.utility.engineering_process import (
    SupervisedEngineeringExecutor,
    execution_identity,
)
from examples.utility.rehearse_wind_scenario import prepare as prepare_scenario
from examples.utility.wind import ROOT
from examples.utility.wind_process import (
    SupervisedWindDriver,
    WindDriverSpec,
    verify_report,
)
from examples.utility.wind_proposal import WindNativeSpec


def prepare(output):
    output, source, geometry, executions = prepare_scenario(output)
    execution = executions[1]
    names = [r.path for r in execution.sources]
    names += [
        "examples/utility/" + n
        for n in (
            "wind_native.py",
            "wind_proposal.py",
            "wind_process.py",
            "rehearse_wind_native.py",
        )
    ]
    for name in names:
        if not (source / name).exists():
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
    refs = tuple(
        reference(source, n, media_type="text/plain", producer="wind-native-capture") for n in names
    )
    identity = execution_identity(
        execution.entrypoint,
        refs,
        execution.lock,
        execution.scenarios,
        execution.timeout_seconds,
        execution.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        execution, sources=refs, study=replace(execution.study, source_identity=identity)
    )
    spec = WindDriverSpec(
        "utility-wind-driver-v1",
        execution,
        WindNativeSpec("utility-wind-native-spec-v1", geometry, 2, 12, 4),
        "examples.utility.wind_process:run_driver",
        45.0,
        65536,
    )
    return output, source, spec


def run(output):
    output, source, spec = prepare(output)
    profile = BatchSpec(
        "1.0",
        "wind-native-development",
        host_source_identity(),
        host_environment_identity(),
        HostSelection("fake", "none", "unused", "1.0"),
        FakeHost(()).capabilities(),
        digest({"wind_native": spec.digest}),
        ResourceLimits(1, 1, 0, 0, 180.0, 10.0, 8388608, 1048576),
        2,
        (BatchCase("native", "comparison", spec.digest, 0, 2),),
    )
    batch = BatchStore.create(output / "batch", profile)
    batch.start_case("native", spec.digest)
    executor = SupervisedEngineeringExecutor(spec.execution, batch, "native", source)
    driver = SupervisedWindDriver(spec, executor)
    print("Wind native: bounded original TOPFARM process", flush=True)
    report = driver.run()
    verify_report(batch, "native", spec, report)
    proposal = report.result.proposal if report.result else None
    configuration = proposal.configuration if proposal else None
    fresh = None
    if configuration is not None:
        print("Wind native: separate fresh scenario evaluation", flush=True)
        action = EvaluationAction(
            "native-fresh",
            configuration,
            "system",
            None,
            seed=17,
            suggested_by="native-wind-unscored-proposal",
        )
        fresh = executor(action)
    evidence = batch.evidence(
        {
            "profile": "wind-native-development-v1",
            "native": report.to_dict(),
            "fresh": fresh.to_dict() if fresh else None,
        }
    )
    status = "passed" if fresh and fresh.evaluation.eligible else "failed"
    batch.finish_case("native", status, (evidence,))
    before = len(batch.replay().reservations)
    assert driver.run(recover_only=True) == report
    if fresh is not None:
        assert executor.recover_completed(action) == fresh
    state = batch.replay()
    assert len(state.reservations) == before == len(state.observations) and not state.pending
    summary = {
        "purpose": "bounded native wind development; not independent weather",
        "native": report.to_dict(),
        "fresh": fresh.to_dict() if fresh else None,
        "callback_work": proposal.work if proposal else "unknown",
        "case_status": status,
        "reservations": before,
        "observed_stops": len(state.observations),
        "completed_replay_added_reservations": 0,
        "confirmation": "not_attempted",
        "utility_verdict": "not_attempted",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in summary.items() if k not in ("native", "fresh")}), flush=True
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
