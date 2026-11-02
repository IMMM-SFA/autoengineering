"""Six supervised coupled solves on exposed development assumptions only."""
from __future__ import annotations

import argparse
from pathlib import Path
import json

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.records import HostSelection, ResourceLimits
from autoengineering.campaign.artifacts import reference, read_bytes
from autoengineering.campaign.serialization import digest
from autoengineering.optimization import (BudgetSpec, ContinuousParameter, NoiseSpec, ObjectiveSpec,
                                        OptimizationRunSpec, SearchSpace, StudySpec)
from autoengineering.utility.engineering_process import (
    EngineeringExecutionSpec, EngineeringScenario, SupervisedEngineeringExecutor, execution_identity,
)
from autoengineering.utility.studies import EngineeringStudy, EngineeringStudySpec
from examples.utility.engineering import ROOT, rules


def run(output):
    output = output.absolute()
    output.mkdir(mode=0o700, parents=True)
    source = output / "captured"
    source.mkdir(mode=0o700)
    names = [str(p.relative_to(ROOT)) for p in (ROOT / "src/autoengineering").rglob("*.py")]
    names += ["examples/utility/__init__.py", "examples/utility/engineering.py",
              "examples/utility/engineering_scenario.py", "examples/interoperability/circuit/model.py",
              "examples/interoperability/circuit/fixture.py", "examples/utility/rehearse_supervised_engineering.py"]
    for name in (*names, "pixi.lock"):
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    refs = tuple(reference(source, name, media_type="text/plain", producer="development-capture") for name in names)
    lock = reference(source,"pixi.lock",media_type="text/plain",producer="development-capture")
    scenarios = tuple(EngineeringScenario(name,{"ground_voltage":ground}) for name,ground in (
        ("low-ground",-.05),("nominal-ground",0.),("high-ground",.05)))
    entry = "examples.utility.engineering_scenario:execute"
    run_spec = OptimizationRunSpec(StudySpec("supervised-circuit-development", ObjectiveSpec("source_power","minimize"), (),
        BudgetSpec(6,"physical_executions",2),NoiseSpec(),"system",17),
        SearchSpace((ContinuousParameter("source_current",.01,.1),)),"sobol",{},
        "autoengineering.utility.studies:engineering_evaluator")
    study = EngineeringStudySpec(run_spec,rules(.62,.001),tuple(s.scenario_id for s in scenarios),
        execution_identity(entry,refs,lock,scenarios,10.,32768))
    execution = EngineeringExecutionSpec("utility-engineering-execution-v1",study,entry,refs,lock,scenarios,10.,32768)
    (output / "execution.json").write_text(execution.to_json())
    batch_spec = BatchSpec("1.0","supervised-engineering-development",host_source_identity(),host_environment_identity(),
        HostSelection("fake","none","not-used","1.0"),FakeHost(()).capabilities(),digest({"host":"not_invoked"}),
        ResourceLimits(1,1,0,0,180.,15.,1048576,1048576),6,(BatchCase("calibration","comparison",study.digest,0,6),))
    batch = BatchStore.create(output / "batch",batch_spec)
    batch.start_case("calibration",study.digest)
    runner = SupervisedEngineeringExecutor(execution,batch,"calibration",source)
    bridge = EngineeringStudy(study,batch,"calibration",runner)
    bridge.run(max_new_evaluations=1)
    before = len(batch.replay().reservations)
    resumed = EngineeringStudy(study,batch,"calibration",SupervisedEngineeringExecutor(execution,batch,"calibration",source))
    recommendation = resumed.run()
    after = len(batch.replay().reservations)
    resumed.run()
    assert len(batch.replay().reservations) == after
    proof = batch.evidence({"study":study.digest,"execution":execution.digest,"recommendation":recommendation.to_dict()})
    batch.finish_case("calibration","passed",(proof,))
    diagnostics = [json.loads(read_bytes(batch.root, ref).decode()) for observed in batch.replay().observations.values()
                   for ref in observed.evidence]
    summary = {"purpose":"exposed engineering development; not independent confirmation",
        "physical_reservations_before_resume":before,"physical_reservations_total":after,
        "verified_process_stops":sum(o.stop_verified for o in batch.replay().observations.values()),
        "repeat_resume_added_reservations":0,"solver_diagnostics":diagnostics,
        "recommendation":recommendation.to_dict(),"utility_verdict":"not_attempted"}
    (output / "summary.json").write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ("solver_diagnostics","recommendation")}))
    return summary


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    run(parser.parse_args().output)
