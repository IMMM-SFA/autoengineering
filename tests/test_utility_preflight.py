"""Preflight failures are scientific results, never fictional physical executions."""

from dataclasses import replace
import json

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.store import StoreError
from autoengineering.optimization import EvaluationAction, ContinuousParameter, SearchSpace
from autoengineering.utility.engineering_process import (
    EngineeringExecutionSpec,
    SupervisedEngineeringExecutor,
    execution_identity,
)
from autoengineering.utility.studies import EngineeringStudy
from test_utility_wind_process import setup as old_setup

FIXTURE = """
def execute(job):
    from autoengineering.campaign.records import CheckResult
    from autoengineering.utility.outcomes import ScenarioScore
    from autoengineering.utility.engineering_process import EngineeringScenarioResult,SupervisedEngineeringExecutor
    scenario=job.execution.scenarios[0]
    checks=tuple(CheckResult(c.name,c.version,"pass",c.required,c.scope,None,None,"Authored fixture",()) for c in job.execution.study.rules.checks)
    score=ScenarioScore(scenario.scenario_id,SupervisedEngineeringExecutor._forcing_digest(scenario),{"annual_energy":1.},checks)
    return EngineeringScenarioResult("utility-engineering-result-v1",job.digest,score,{"fixture_calls":1.},.01,{"fixture_calls":"count"})
"""


def setup(tmp_path, *, fault=lambda _: None, narrow=False):
    driver, original, source = old_setup(tmp_path)
    (source / "scenario_fixture.py").write_text(FIXTURE)
    old = driver.spec.execution
    refs = tuple(
        reference(source, r.path, media_type=r.media_type, producer=r.producer) for r in old.sources
    )
    constraints = driver.spec.native.geometry.preflight
    run = old.study.run
    if narrow:
        run = replace(
            run,
            search_space=SearchSpace(
                tuple(ContinuousParameter(p.name, 0.0, 1.0) for p in run.search_space.parameters)
            ),
        )
    identity = execution_identity(
        old.entrypoint,
        refs,
        old.lock,
        old.scenarios,
        old.timeout_seconds,
        old.output_bytes,
        profile="supervised-engineering-v3",
        preflight=constraints,
    )
    spec = replace(
        old,
        schema="utility-engineering-execution-v3",
        sources=refs,
        preflight=constraints,
        study=replace(old.study, run=run, source_identity=identity),
    )
    batch = BatchStore.create(tmp_path / "preflight-batch", original.spec)
    batch.start_case("first", batch.spec.cases[0].configuration_digest)
    executor = SupervisedEngineeringExecutor(spec, batch, "first", source, fault=fault)
    config = driver.spec.native.geometry.baseline
    invalid = dict(config)
    invalid["x_1"] = invalid["x_0"]
    invalid["y_1"] = invalid["y_0"]
    action = EvaluationAction.system(
        "bad-layout", invalid, seed=17, suggested_by="authored-preflight"
    )
    return executor, batch, source, action, config


def test_infeasible_layout_is_saved_without_process_or_reservation(tmp_path, monkeypatch):
    executor, batch, _, action, _ = setup(tmp_path)

    def denied(*args, **kwargs):
        raise AssertionError("invalid layout started a process")

    monkeypatch.setattr("subprocess.Popen", denied)
    value = executor(action)
    assert value.evaluation.status == "scientific_infeasible"
    assert not value.evaluation.eligible and not value.evaluation.outputs
    assert all(v is None for v in value.evaluation.metrics.values())
    assert all(c.status == "unavailable" for s in value.scenarios for c in s.checks)
    assert not batch.replay().reservations and not batch.replay().observations
    assert executor.reservations(action) == []
    assert executor.verify_preflight(action, value)
    assert executor.recover_completed(action) == value
    reopened = SupervisedEngineeringExecutor(executor.spec, batch, "first", executor.source_root)
    assert reopened.recover_completed(action) == value
    assert EngineeringExecutionSpec.from_json(executor.spec.to_json()) == executor.spec


def test_missing_rejection_is_not_automatically_recreated_on_recovery(tmp_path, monkeypatch):
    executor, batch, _, action, _ = setup(tmp_path)
    with pytest.raises(StoreError, match="undispatched"):
        executor.recover_completed(action)
    assert not batch.replay().reservations


def test_saved_rejection_recovers_after_owner_loss(tmp_path):
    def lost(stage):
        if stage == "engineering_preflight_rejection_saved":
            raise RuntimeError("owner lost")

    executor, batch, _, action, _ = setup(tmp_path, fault=lost)
    with pytest.raises(RuntimeError, match="owner lost"):
        executor(action)
    reopened = SupervisedEngineeringExecutor(executor.spec, batch, "first", executor.source_root)
    assert reopened.recover_completed(action).evaluation.status == "scientific_infeasible"
    assert not batch.replay().reservations


def test_modified_rejection_is_not_accepted(tmp_path):
    executor, _, _, action, _ = setup(tmp_path)
    executor(action)
    path = next(executor.directory.glob("preflight-*.json"))
    data = json.loads(path.read_text())
    data["violated"] = []
    path.write_text(json.dumps(data))
    with pytest.raises(StoreError, match="changed"):
        executor.recover_completed(action)


@pytest.mark.parametrize("saved", [False, True])
def test_preflight_preserves_conflicting_physical_charge(tmp_path, saved):
    from autoengineering.agents.batch import PhysicalReservation

    executor, batch, _, action, _ = setup(tmp_path)
    if saved:
        executor(action)
    identity = executor.identity(action, executor.spec.scenarios[0])
    reservation = PhysicalReservation(
        "uncertain-original", "first", "science", identity, None, batch.clock(), 10.0, 0, 0, 0
    )
    batch.reserve(reservation)
    with pytest.raises(StoreError, match="conflicts"):
        executor(action)
    with pytest.raises(StoreError, match="conflicts"):
        executor.recover_completed(action)
    assert batch.replay().pending == (reservation,)
    assert not batch.replay().observations


def test_cancelled_preflight_cannot_create_new_rejection(tmp_path):
    executor, batch, _, action, _ = setup(tmp_path)
    executor.cancelled = lambda: True
    with pytest.raises(StoreError, match="cancelled"):
        executor(action)
    assert not list(executor.directory.glob("preflight-*.json"))
    assert not batch.replay().reservations


def test_zero_physical_cost_still_stops_at_evaluation_cap(tmp_path, monkeypatch):
    executor, batch, _, _, _ = setup(tmp_path, narrow=True)
    monkeypatch.setattr(
        "autoengineering.utility.engineering_process.supervise_process",
        lambda *a, **k: pytest.fail("all configurations are infeasible"),
    )
    bridge = EngineeringStudy(executor.spec.study, batch, "first", executor)
    bridge.run()
    entries = bridge.study.ledger.entries()
    assert len(entries) == executor.spec.study.run.study.budget.max_evaluations
    assert all(
        result.status.value == "scientific_infeasible" and result.cost == 0 for _, result in entries
    )
    assert not batch.replay().reservations
    resumed = EngineeringStudy(executor.spec.study, batch, "first", executor)
    resumed.run()
    assert resumed.study.ledger.entries() == entries


def test_feasible_action_still_uses_original_supervised_process(tmp_path):
    executor, batch, _, _, config = setup(tmp_path)
    action = EvaluationAction.system(
        "valid-layout", config, seed=17, suggested_by="authored-preflight"
    )
    value = executor(action)
    assert value.evaluation.status == "success" and value.evaluation.eligible
    assert len(batch.replay().reservations) == len(executor.spec.scenarios)
    assert executor.recover_completed(action) == value


def test_legacy_schema_does_not_accept_or_serialize_new_fields(tmp_path):
    driver, _, _ = old_setup(tmp_path)
    original = driver.spec.execution
    document = original.to_dict()
    assert "preflight" not in document
    assert EngineeringExecutionSpec.from_dict(document).to_dict() == document
    with pytest.raises(ValueError, match="legacy"):
        EngineeringExecutionSpec.from_dict({**document, "preflight": []})
    with pytest.raises(ValueError, match="legacy"):
        replace(original, preflight=driver.spec.native.geometry.preflight)


def test_campaign_keeps_preflight_veto_and_relocated_receipt(tmp_path, monkeypatch):
    import shutil
    from autoengineering.campaign.records import ModelSnapshot, PortContract
    from autoengineering.campaign.serialization import digest
    from autoengineering.utility.engineering_campaign import (
        EngineeringCampaign,
        EngineeringCampaignSpec,
        EngineeringDesign,
    )
    from test_utility_engineering_campaign import request

    executor, batch, _, bad, config = setup(tmp_path)
    ref = next(r for r in executor.spec.sources if r.path == "scenario_fixture.py")
    port = PortContract(
        "annual_energy", (), "GWh", "float", (), "scalar", digest({"grid": "scalar"}), None
    )
    model = ModelSnapshot(
        digest({"model": "authored-preflight"}),
        {"fixture": "1"},
        (ref,),
        executor.spec.lock.sha256,
        (),
        (port,),
    )
    spec = EngineeringCampaignSpec(
        "utility-engineering-campaign-v1",
        "preflight-campaign",
        executor.spec,
        model,
        config,
        (EngineeringDesign("too-close", bad.config),),
        16,
    )
    campaign = EngineeringCampaign.create(tmp_path / "campaign", spec, executor)
    assert (
        campaign.handle(
            request(
                campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="baseline"
            )
        ).status
        == "ok"
    )
    before = len(batch.replay().reservations)
    monkeypatch.setattr(
        "autoengineering.utility.engineering_process.supervise_process",
        lambda *a, **k: pytest.fail("invalid design dispatched"),
    )
    assert (
        campaign.handle(
            request(
                campaign, "evaluate", {"candidate_id": "too-close", "mode": "fixed"}, id="invalid"
            )
        ).status
        == "ok"
    )
    assert len(batch.replay().reservations) == before
    assert campaign.state()["evaluations"][-1].evaluation.status == "scientific_infeasible"
    campaign.handle(request(campaign, "review"))
    campaign.handle(request(campaign, "freeze"))
    assert campaign.state()["decision"].outcome == "retain_baseline"
    copied = tmp_path / "archive"
    shutil.copytree(batch.root, copied / "batch")
    shutil.copytree(campaign.store.root, copied / "campaign")
    assert (
        EngineeringCampaign(
            copied / "campaign", BatchStore(copied / "batch"), inspect_only=True
        ).state()["selected"]
        == campaign.state()["selected"]
    )
