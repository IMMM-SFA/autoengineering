"""Bounded real-model development calibration through batch and optimizer journals."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore, PhysicalReservation, PhysicalObservation
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_source_identity, host_environment_identity
from autoengineering.agents.records import HostSelection, ResourceLimits
from autoengineering.campaign.acceptance import CheckContext, CheckRegistry
from autoengineering.campaign.records import EvaluationRecord
from autoengineering.campaign.serialization import digest
from autoengineering.optimization import (
    OptimizationRunSpec, StudySpec, ObjectiveSpec, BudgetSpec, NoiseSpec, SearchSpace, ContinuousParameter,
)
from autoengineering.utility.outcomes import OutcomeRegistry
from autoengineering.utility.studies import EngineeringStudySpec, EngineeringStudy
from examples.utility.engineering import ROOT, adapter, context, required_voltage, rules, source_power


def run(output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    grounds = {"low-ground": -.05, "nominal-ground": 0., "high-ground": .05}
    sources = ("examples/utility/engineering_study.py", "examples/utility/engineering.py",
               "src/autoengineering/utility/studies.py", "src/autoengineering/utility/outcomes.py",
               "examples/interoperability/circuit/model.py", "pixi.lock")
    closure = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
    spec = EngineeringStudySpec(OptimizationRunSpec(
        StudySpec("circuit-development-fit", ObjectiveSpec("source_power", "minimize"), (),
                  BudgetSpec(12, "physical_executions", 4), NoiseSpec(), "system", 17),
        SearchSpace((ContinuousParameter("source_current", .01, .1),)), "sobol", {},
        "autoengineering.utility.studies:engineering_evaluator"), rules(.62, .001),
        tuple(grounds), digest(closure))
    (output / "source-inventory.json").write_text(json.dumps(closure, indent=2) + "\n")
    (output / "protocol.json").write_text(spec.to_json() + "\n")
    batch_spec = BatchSpec("1.0", "engineering-development", host_source_identity(),
                          host_environment_identity(), HostSelection("fake", "none", "not-used", "1.0"),
                          FakeHost(()).capabilities(), digest({"hosts": "not_invoked"}),
                          ResourceLimits(1, 1, 0, 0, 120., 10., 1024, 1024), 12,
                          (BatchCase("calibration", "comparison", spec.digest, 0, 12),))
    batch = BatchStore.create(output / "batch", batch_spec)
    batch.start_case("calibration", spec.digest)
    scratch = batch.root / "cases/calibration"
    scratch.mkdir(mode=0o700)

    def evaluate(action):
        contexts, duration = {}, 0.
        for scenario_id, ground in grounds.items():
            ctx = context(action.config["source_current"], scratch)
            forcing = {"ground_voltage": np.array(ground)}
            identity = digest({"action": action.to_dict(), "scenario": scenario_id, "profile": spec.digest})
            reservation = PhysicalReservation("science-" + identity[:32], "calibration", "science",
                                               identity, None, batch.clock(), 10., 0, 0, 0)

            def perform(_):
                return run_lifecycle(adapter(), ctx, forcing, ctx.model.inputs, ctx.model.outputs)

            def observe(reservation, result):
                evidence = batch.evidence({"profile": "trusted-synchronous-lifecycle-v1",
                    "action": action.to_dict(), "scenario_id": scenario_id,
                    "ground_voltage_V": ground,
                    "outputs": {name: float(value) for name, value in result.outputs.items()},
                    "solver_work": {name: float(value) for name, value in result.diagnostics.items()},
                    "cleanup": "lifecycle_returned", "seconds": result.elapsed_seconds})
                return PhysicalObservation(reservation.id, "success", True, 0, {}, None,
                                           "not_applicable", result.elapsed_seconds, (evidence,))

            result = batch.execute(reservation, perform, observe)
            duration += result.elapsed_seconds
            contexts[scenario_id] = CheckContext(result.outputs, forcing, ctx.parameters)
        template = EvaluationRecord(action.id, "circuit", action.config, "success", {}, (), (),
                                    "development-fitting", action.id, duration, {})
        return OutcomeRegistry({"source_power": source_power}).evaluate(
            spec.rules, contexts, CheckRegistry({("node_voltage", "1"): required_voltage}), template)

    bridge = EngineeringStudy(spec, batch, "calibration", evaluate)
    bridge.run(max_new_evaluations=1)
    starts_before_resume = len(batch.replay().reservations)
    resumed = EngineeringStudy(spec, batch, "calibration", evaluate)
    recommendation = resumed.run()
    starts_after_resume = len(batch.replay().reservations)
    resumed.run()
    assert len(batch.replay().reservations) == starts_after_resume
    proof = batch.evidence({"recommendation": recommendation.to_dict(), "profile": spec.digest,
                            "study_directory": str(resumed.directory.relative_to(batch.root))})
    batch.finish_case("calibration", "passed", (proof,))
    summary = {"purpose": "exposed development calibration; not independent confirmation",
               "physical_starts_before_resume": starts_before_resume,
               "physical_starts_total": starts_after_resume,
               "repeat_completed_run_added_starts": 0, "host_invocations": 0,
               "recommendation": recommendation.to_dict(), "utility_verdict": "not_attempted",
               "batch_integrity": batch.report(),
               "profile_limit": "Trusted synchronous lifecycle, no subprocess interruption qualification"}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: summary[k] for k in ("physical_starts_before_resume", "physical_starts_total",
                                              "repeat_completed_run_added_starts", "utility_verdict")}))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
