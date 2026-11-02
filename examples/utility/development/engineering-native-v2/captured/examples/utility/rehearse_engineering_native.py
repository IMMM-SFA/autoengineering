"""Native SLSQP and fresh scenario checks on the exposed coupled circuit."""

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
from autoengineering.campaign.records import Request
from autoengineering.campaign.serialization import digest
from autoengineering.optimization import (
    BudgetSpec,
    ContinuousParameter,
    NoiseSpec,
    ObjectiveSpec,
    OptimizationRunSpec,
    SearchSpace,
    StudySpec,
)
from autoengineering.utility.engineering_campaign import (
    EngineeringCampaign,
    EngineeringNativeCampaignSpec,
    EngineeringDesign,
)
from autoengineering.utility.engineering_native import NativeDriverSpec
from autoengineering.utility.engineering_process import (
    EngineeringExecutionSpec,
    EngineeringScenario,
    SupervisedEngineeringExecutor,
    execution_identity,
)
from autoengineering.utility.studies import EngineeringStudySpec
from examples.utility.engineering import ROOT, context, rules


def run(output: Path):
    output = output.absolute()
    output.mkdir(mode=0o700, parents=True)
    source = output / "captured"
    source.mkdir(mode=0o700)
    names = [str(p.relative_to(ROOT)) for p in (ROOT / "src/autoengineering").rglob("*.py")]
    names += [
        "examples/utility/__init__.py",
        "examples/utility/engineering.py",
        "examples/utility/engineering_scenario.py",
        "examples/interoperability/circuit/model.py",
        "examples/interoperability/circuit/fixture.py",
        "examples/utility/rehearse_engineering_native.py",
        "examples/utility/engineering_native.py",
    ]
    for name in (*names, "pixi.lock"):
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    refs = tuple(
        reference(source, name, media_type="text/plain", producer="development-capture")
        for name in names
    )
    lock = reference(source, "pixi.lock", media_type="text/plain", producer="development-capture")
    scenarios = tuple(
        EngineeringScenario(name, {"ground_voltage": ground})
        for name, ground in (("low-ground", -0.05), ("nominal-ground", 0.0), ("high-ground", 0.05))
    )
    entry = "examples.utility.engineering_scenario:execute"
    run_spec = OptimizationRunSpec(
        StudySpec(
            "engineering-native-development",
            ObjectiveSpec("source_power", "minimize"),
            (),
            BudgetSpec(6, "physical_executions", 2),
            NoiseSpec(),
            "system",
            17,
        ),
        SearchSpace((ContinuousParameter("source_current", 0.01, 0.1),)),
        "sobol",
        {},
        "autoengineering.utility.studies:engineering_evaluator",
    )
    study = EngineeringStudySpec(
        run_spec,
        rules(0.62, 0.001),
        tuple(s.scenario_id for s in scenarios),
        execution_identity(entry, refs, lock, scenarios, 10.0, 32768),
    )
    execution = EngineeringExecutionSpec(
        "utility-engineering-execution-v1", study, entry, refs, lock, scenarios, 10.0, 32768
    )
    declared = {ref.path: ref for ref in (*refs, lock)}
    model = context(0.1, output / "unused-context-scratch", source_root=source).model
    model = replace(model, source_bundle=tuple(declared[ref.path] for ref in model.source_bundle))
    spec = EngineeringNativeCampaignSpec(
        "utility-engineering-campaign-v2",
        "exposed-circuit-tools",
        execution,
        model,
        {"source_current": 0.1},
        (EngineeringDesign("supplied-current", {"source_current": 0.03}),),
        10,
        native=NativeDriverSpec(
            "utility-native-driver-v1",
            execution,
            "examples.utility.engineering_native:execute",
            20,
            40,
            10.0,
            65536,
        ),
    )
    batch_spec = BatchSpec(
        "1.0",
        "engineering-native-development",
        host_source_identity(),
        host_environment_identity(),
        HostSelection("fake", "none", "not-used", "1.0"),
        FakeHost(()).capabilities(),
        digest({"host": "not_invoked"}),
        ResourceLimits(1, 1, 0, 0, 240.0, 15.0, 1048576, 1048576),
        spec.scientific_starts,
        (BatchCase("selection", "comparison", spec.digest, 0, spec.scientific_starts),),
    )
    batch = BatchStore.create(output / "batch", batch_spec)
    batch.start_case("selection", spec.digest)
    executor = SupervisedEngineeringExecutor(execution, batch, "selection", source)
    campaign = EngineeringCampaign.create(output / "campaign", spec, executor)

    def call(operation, payload=None, id=None):
        request = Request(
            "1.0",
            spec.name,
            id or operation,
            campaign.state()["projection"].revision,
            operation,
            payload or {},
        )
        response = campaign.handle(request)
        if response.status != "ok":
            raise RuntimeError("Engineering tool request failed: " + str(response.error))
        return request

    original = call("evaluate", {"candidate_id": "baseline", "mode": "fixed"}, "baseline")
    before = len(batch.replay().reservations)
    campaign = EngineeringCampaign(
        campaign.store.root,
        batch,
        executor=SupervisedEngineeringExecutor(execution, batch, "selection", source),
    )
    call("evaluate", {"candidate_id": "supplied-current", "mode": "fixed"}, "supplied-current")
    call("evaluate", {"candidate_id": "calibration", "mode": "calibrated"}, "numerical")
    native_request = call("evaluate", {"candidate_id": "native", "mode": "native"}, "native")
    call("review")
    call("freeze")
    after = len(batch.replay().reservations)
    reader = EngineeringCampaign(campaign.store.root, batch)
    assert reader.handle(original).status == "ok"
    assert reader.handle(native_request).status == "ok"
    final = reader.state()
    assert final["projection"].state == "selection_frozen" and final["selected"] is not None
    assert len(batch.replay().reservations) == after
    proof = batch.evidence(
        {
            "campaign": spec.digest,
            "head": final["projection"].head_hash,
            "decision": final["decision"].to_dict(),
            "selected_state": final["selected"].to_dict(),
        }
    )
    batch.finish_case("selection", "passed", (proof,))
    summary = {
        "purpose": "exposed engineering scientific tools; no independent confirmation or route comparison",
        "physical_reservations_before_reopen": before,
        "physical_reservations_total": after,
        "verified_process_stops": sum(
            o.stop_verified for o in batch.replay().observations.values()
        ),
        "repeat_request_added_reservations": len(batch.replay().reservations) - after,
        "evaluation_count": len(final["evaluations"]),
        "native_reports": [r.to_dict() for r in final["native_reports"]],
        "native_inner_model_calls": sum(
            len(r.result.solves) for r in final["native_reports"] if r.result is not None
        ),
        "decision": final["decision"].to_dict(),
        "selected_state": final["selected"].to_dict(),
        "utility_verdict": "not_attempted",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: v
                for k, v in summary.items()
                if k not in ("selected_state", "decision", "native_reports")
            }
        )
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
