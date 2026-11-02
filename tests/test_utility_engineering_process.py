"""Real owned subprocesses for supplied engineering, with no provider or private data."""
from dataclasses import replace
from pathlib import Path

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.store import StoreError
from autoengineering.utility.engineering_process import (
    EngineeringScenario, EngineeringExecutionSpec, SupervisedEngineeringExecutor, execution_identity,
)
from autoengineering.utility.studies import EngineeringStudy, EngineeringReconciliationRequired
from test_agent_batch import specification
from test_utility_studies import profile

ROOT = Path(__file__).resolve().parents[1]
CALLBACK = '''
import time
from pathlib import Path
from autoengineering.utility.engineering_process import EngineeringScenarioResult, SupervisedEngineeringExecutor
from autoengineering.utility.outcomes import ScenarioScore
from autoengineering.campaign.records import CheckResult

def execute(job):
    if job.configuration.get("x") == 1.:
        raise RuntimeError("PRIVATE-DIAGNOSTIC-CANARY")
    if job.scenario_id == "scenario-0" and job.configuration.get("x") == 0.:
        time.sleep(60)
    score = ScenarioScore(job.scenario_id, SupervisedEngineeringExecutor._forcing_digest(
        next(s for s in job.execution.scenarios if s.scenario_id == job.scenario_id)),
        {"power":10.-job.configuration["x"], "revenue":5.},
        (CheckResult("physics","1","pass",True,"scenario",None,None,"Authored supplied check",()),))
    return EngineeringScenarioResult("utility-engineering-result-v1",job.digest,score,{"solves":1.},.01, {"solves":"count"})
'''


def setup(tmp_path, *, timeout=5., one_scenario=False):
    source = tmp_path / "captured"
    source.mkdir(mode=0o700)
    paths = [(p, str(p.relative_to(ROOT))) for p in (ROOT / "src/autoengineering").rglob("*.py")]
    for path, relative in paths:
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    (source / "scenario_fixture.py").write_text(CALLBACK)
    (source / "lock.json").write_text('{"fixture":"no model dependencies"}')
    names = [relative for _, relative in paths]+["scenario_fixture.py"]
    refs = tuple(reference(source, name, media_type="text/plain", producer="authored-fixture") for name in names)
    lock = reference(source, "lock.json", media_type="application/json", producer="authored-fixture")
    scenarios = tuple(EngineeringScenario("scenario-"+str(i), {"forcing":float(i)}) for i in range(1 if one_scenario else 2))
    study = profile()
    study = replace(study, scenario_ids=tuple(s.scenario_id for s in scenarios), source_identity=execution_identity(
        "scenario_fixture:execute", refs, lock, scenarios, timeout, 16384))
    execution = EngineeringExecutionSpec("utility-engineering-execution-v1", study, "scenario_fixture:execute",
                                         refs, lock, scenarios, timeout, 16384)
    batch_spec = specification(science=4)
    batch_spec = replace(batch_spec, limits=replace(batch_spec.limits, elapsed_seconds=180., worker_seconds=15.))
    batch = BatchStore.create(tmp_path / "batch", batch_spec)
    batch.start_case("first", batch.spec.cases[0].configuration_digest)
    return batch, execution, source


def test_supervised_study_and_finished_resume_use_original_processes(tmp_path):
    batch, spec, source = setup(tmp_path)
    runner = SupervisedEngineeringExecutor(spec, batch, "first", source)
    study = EngineeringStudy(spec.study, batch, "first", runner)
    study.run(max_new_evaluations=1)
    assert len(batch.replay().reservations) == 2
    resumed = EngineeringStudy(spec.study, batch, "first", SupervisedEngineeringExecutor(spec, batch, "first", source))
    resumed.run()
    assert len(batch.replay().reservations) == 4 and not batch.replay().pending
    resumed.run()
    assert len(batch.replay().reservations) == 4
    assert EngineeringExecutionSpec.from_json(spec.to_json()) == spec


def test_partial_scenarios_resume_only_on_explicit_authority(tmp_path):
    batch, spec, source = setup(tmp_path)
    def lost(stage):
        if stage == "engineering_scenario_observed":
            raise RuntimeError("owner lost after original scenario")
    runner = SupervisedEngineeringExecutor(spec, batch, "first", source, fault=lost)
    with pytest.raises(EngineeringReconciliationRequired):
        EngineeringStudy(spec.study, batch, "first", runner).run(max_new_evaluations=1)
    assert len(batch.replay().reservations) == 1 and not batch.replay().pending
    reopened = SupervisedEngineeringExecutor(spec, batch, "first", source)
    with pytest.raises(EngineeringReconciliationRequired):
        EngineeringStudy(spec.study, batch, "first", reopened)
    assert len(batch.replay().reservations) == 1
    resumed = EngineeringStudy(spec.study, batch, "first", reopened, resume_scenarios=True)
    assert len(batch.replay().reservations) == 2
    resumed.run()
    assert len(batch.replay().reservations) == 4


def test_saved_process_before_observation_recovers_without_relaunch(tmp_path):
    batch, spec, source = setup(tmp_path)
    def lost(stage):
        if stage == "engineering_scenario_process_saved":
            raise RuntimeError("lost before physical acknowledgement")
    with pytest.raises(EngineeringReconciliationRequired):
        EngineeringStudy(spec.study, batch, "first", SupervisedEngineeringExecutor(spec,batch,"first",source,fault=lost)).run(max_new_evaluations=1)
    assert len(batch.replay().pending) == 1
    recovered = EngineeringStudy(spec.study,batch,"first",SupervisedEngineeringExecutor(spec,batch,"first",source),resume_scenarios=True)
    assert len(batch.replay().reservations) == 2 and not batch.replay().pending
    recovered.run()
    assert len(batch.replay().reservations) == 4


def test_reserved_without_process_keeps_charge_and_refuses_retry(tmp_path):
    batch, spec, source = setup(tmp_path)
    def lost(stage):
        if stage == "engineering_scenario_reserved":
            raise RuntimeError("lost before launch")
    with pytest.raises(EngineeringReconciliationRequired):
        EngineeringStudy(spec.study,batch,"first",SupervisedEngineeringExecutor(spec,batch,"first",source,fault=lost)).run(max_new_evaluations=1)
    with pytest.raises(EngineeringReconciliationRequired):
        EngineeringStudy(spec.study,batch,"first",SupervisedEngineeringExecutor(spec,batch,"first",source),resume_scenarios=True)
    assert len(batch.replay().reservations) == 1 and len(batch.replay().pending) == 1


def test_changed_or_undeclared_sources_reject_before_physical_reservation(tmp_path):
    batch, spec, source = setup(tmp_path)
    (source / "extra.py").write_text("raise RuntimeError('must not import')")
    with pytest.raises(StoreError, match="undeclared"):
        SupervisedEngineeringExecutor(spec,batch,"first",source)
    assert not batch.replay().reservations


def test_timeout_is_a_charged_scientific_outcome_with_verified_stop(tmp_path):
    from autoengineering.optimization.records import EvaluationAction
    batch, spec, source = setup(tmp_path, timeout=1., one_scenario=True)
    runner = SupervisedEngineeringExecutor(spec, batch, "first", source)
    action = EvaluationAction("timeout-action", {"x":0.}, "system", None, seed=17)
    value = runner(action)
    assert value.evaluation.status == "timeout"
    assert value.evaluation.metrics["power"] is None
    assert len(batch.replay().reservations) == 1 and not batch.replay().pending
    assert runner.recover_completed(action) == value


def test_changed_completed_process_output_cannot_be_accepted(tmp_path):
    batch, spec, source = setup(tmp_path)
    from autoengineering.optimization.records import EvaluationAction
    runner = SupervisedEngineeringExecutor(spec,batch,"first",source)
    action = EvaluationAction("original-action", {"x":.5}, "system", None, seed=17)
    runner(action)
    output = next(runner.directory.glob("*/process/stdout.bin"))
    output.write_bytes(b"altered")
    with pytest.raises(ValueError):
        runner.recover_completed(action)
    assert len(batch.replay().reservations) == 2


def test_source_parent_inspection_does_not_execute_module_code(tmp_path):
    batch, spec, source = setup(tmp_path)
    folder=source / "parent"
    folder.mkdir()
    (folder / "__init__.py").write_text("raise RuntimeError('parent imported before reservation')")
    (folder / "worker.py").write_text(CALLBACK)
    refs=(*spec.sources, *(reference(source, name, media_type="text/plain", producer="fixture")
                          for name in ("parent/__init__.py","parent/worker.py")))
    entry="parent.worker:execute"
    study=replace(spec.study,source_identity=execution_identity(entry,refs,spec.lock,spec.scenarios,spec.timeout_seconds,spec.output_bytes))
    altered=replace(spec,study=study,entrypoint=entry,sources=refs)
    SupervisedEngineeringExecutor(altered,batch,"first",source)
    assert not batch.replay().reservations


def test_coupled_model_runs_in_supervised_scenario_processes(tmp_path):
    import importlib.util
    if importlib.util.find_spec("openmdao") is None:
        pytest.skip("optional OpenMDAO environment required")
    from examples.utility.engineering import rules
    from autoengineering.optimization.records import EvaluationAction
    batch, original, source = setup(tmp_path)
    paths=("examples/utility/__init__.py","examples/utility/engineering.py","examples/utility/engineering_scenario.py",
           "examples/interoperability/circuit/model.py","examples/interoperability/circuit/fixture.py")
    refs=list(original.sources)
    for name in paths:
        target=source/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
        refs.append(reference(source,name,media_type="text/plain",producer="circuit-fixture"))
    (source / "pixi.lock").write_bytes((ROOT / "pixi.lock").read_bytes())
    # Keep the authored lock.json as declared evidence; context uses the actual Pixi lock.
    refs.append(reference(source,"pixi.lock",media_type="text/plain",producer="circuit-fixture"))
    scenarios=tuple(EngineeringScenario("scenario-"+str(i),{"ground_voltage":g}) for i,g in enumerate((-.05,.05)))
    entry="examples.utility.engineering_scenario:execute"
    from autoengineering.optimization import ContinuousParameter, SearchSpace
    run=replace(original.study.run,study=replace(original.study.run.study,
        objective=replace(original.study.run.study.objective,outcome="source_power")),
        search_space=SearchSpace((ContinuousParameter("source_current",.01,.1),)))
    study=replace(original.study,run=run,rules=rules(.62,.001),source_identity=execution_identity(
        entry,refs,original.lock,scenarios,10.,32768))
    spec=EngineeringExecutionSpec("utility-engineering-execution-v1",study,entry,tuple(refs),original.lock,scenarios,10.,32768)
    runner=SupervisedEngineeringExecutor(spec,batch,"first",source)
    value=runner(EvaluationAction("circuit-action",{"source_current":.05},"system",None,seed=17))
    assert value.evaluation.status == "success"
    assert all(s.values["source_power"] > 0 for s in value.scenarios)
    assert all(c.status == "pass" for c in value.evaluation.checks)
    assert len(batch.replay().reservations) == 2 and not batch.replay().pending


def test_changed_input_root_or_runtime_binding_rejects_without_new_starts(tmp_path, monkeypatch):
    import shutil
    import autoengineering.agents.identity as identities
    batch, spec, source = setup(tmp_path)
    SupervisedEngineeringExecutor(spec,batch,"first",source)
    copied=tmp_path / "other-captured"
    shutil.copytree(source,copied)
    with pytest.raises(StoreError,match="identity changed"):
        SupervisedEngineeringExecutor(spec,batch,"first",copied)
    monkeypatch.setattr(identities,"host_environment_identity",lambda:"f"*64)
    with pytest.raises(StoreError,match="identity changed"):
        SupervisedEngineeringExecutor(spec,batch,"first",source)
    assert not batch.replay().reservations



def test_out_of_domain_action_starts_no_scientific_work(tmp_path):
    from autoengineering.optimization.records import EvaluationAction
    batch, spec, source = setup(tmp_path)
    runner=SupervisedEngineeringExecutor(spec,batch,"first",source)
    with pytest.raises(ValueError):
        runner(EvaluationAction("invalid-point",{"x":10.},"system",None,seed=17))
    assert not batch.replay().reservations



def test_supplied_failure_is_not_an_infrastructure_failure_or_public_exception_payload(tmp_path):
    from autoengineering.optimization.records import EvaluationAction
    batch, spec, source = setup(tmp_path)
    runner=SupervisedEngineeringExecutor(spec,batch,"first",source)
    value=runner(EvaluationAction("failed-model",{"x":1.},"system",None,seed=17))
    assert value.evaluation.status == "model_failure"
    assert all(v is None for v in value.evaluation.metrics.values())
    assert not batch.replay().pending
    for path in runner.directory.glob("*/process/stderr.bin"):
        assert b"PRIVATE-DIAGNOSTIC-CANARY" not in path.read_bytes()


def test_child_preflight_failure_preserves_infrastructure_status(tmp_path):
    from autoengineering.optimization.records import EvaluationAction
    batch, spec, source = setup(tmp_path)
    runner=None
    def corrupt(stage):
        if stage == "engineering_scenario_reserved":
            (runner.directory / "execution.json").write_text("{}")
    runner=SupervisedEngineeringExecutor(spec,batch,"first",source,fault=corrupt)
    value=runner(EvaluationAction("failed-preflight",{"x":.5},"system",None,seed=17))
    assert value.evaluation.status == "infrastructure_failure"
    assert len(batch.replay().reservations) == 2 and not batch.replay().pending
