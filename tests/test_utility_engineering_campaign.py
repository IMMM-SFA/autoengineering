"""Durable engineering scientific tools use real supervised scenario processes."""

from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.records import ModelSnapshot, PortContract, Request
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.engineering_campaign import (
    EngineeringCampaign,
    EngineeringCampaignSpec,
    EngineeringDesign,
)
from autoengineering.utility.engineering_process import SupervisedEngineeringExecutor
from test_utility_engineering_process import setup as execution_setup


def setup(
    tmp_path, *, fault=lambda _: None, executor_fault=lambda _: None, baseline=0.2, max_requests=16
):
    original, execution, source = execution_setup(tmp_path)
    source_ref = next(ref for ref in execution.sources if ref.path == "scenario_fixture.py")
    port = PortContract("power", (), "W", "float", (), "scalar", digest({"grid": "scalar"}), None)
    model = ModelSnapshot(
        digest({"model": "authored"}),
        {"fixture": "1"},
        (source_ref,),
        execution.lock.sha256,
        (),
        (port,),
    )
    spec = EngineeringCampaignSpec(
        "utility-engineering-campaign-v1",
        "engineering-tools",
        execution,
        model,
        {"x": baseline},
        (EngineeringDesign("better", {"x": 0.8}), EngineeringDesign("broken", {"x": 1.0})),
        max_requests,
    )
    batch_spec = replace(
        original.spec,
        scientific_starts=spec.scientific_starts,
        cases=(
            replace(original.spec.cases[0], scientific_starts=spec.scientific_starts),
            original.spec.cases[1],
        ),
    )
    batch = BatchStore.create(tmp_path / "campaign-batch", batch_spec)
    batch.start_case("first", batch.spec.cases[0].configuration_digest)
    runner = SupervisedEngineeringExecutor(execution, batch, "first", source, fault=executor_fault)
    campaign = EngineeringCampaign.create(tmp_path / "engineering", spec, runner, fault=fault)
    return campaign, batch, source


def request(campaign, operation, payload=None, *, id=None):
    return Request(
        "1.0",
        campaign.spec.name,
        id or operation,
        campaign.state()["projection"].revision,
        operation,
        payload or {},
    )


def test_registered_baseline_design_calibration_review_and_freeze(tmp_path):
    campaign, batch, source = setup(tmp_path)
    assert (
        campaign.handle(
            request(campaign, "evaluate", {"candidate_id": "better", "mode": "fixed"})
        ).error
        == "invalid_transition"
    )
    for name in ("baseline", "better", "broken"):
        response = campaign.handle(
            request(campaign, "evaluate", {"candidate_id": name, "mode": "fixed"}, id=name)
        )
        assert response.status == "ok"
    assert len(batch.replay().reservations) == 6
    campaign.handle(
        request(
            campaign,
            "evaluate",
            {"candidate_id": "calibration", "mode": "calibrated"},
            id="numerical",
        )
    )
    assert len(batch.replay().reservations) == 10
    state = campaign.state()
    assert len(state["evaluations"]) == 5
    failed = next(
        v for v in state["evaluations"] if v.evaluation.id == campaign.spec.action("broken").id
    )
    assert failed.evaluation.status == "model_failure" and all(
        v is None for v in failed.evaluation.metrics.values()
    )
    assert campaign.handle(request(campaign, "review")).status == "ok"
    assert campaign.handle(request(campaign, "freeze")).status == "ok"
    selected = campaign.state()["selected"]
    assert selected.model == campaign.spec.model
    assert selected.evaluation.configuration["x"] == 0.2
    assert campaign.state()["decision"].outcome == "retain_baseline"
    reader = EngineeringCampaign(campaign.store.root, batch)
    assert reader.state()["selected"] == selected
    assert (
        reader.handle(
            request(reader, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="late")
        ).error
        == "invalid_transition"
    )
    assert len(batch.replay().reservations) == 10


def test_lost_event_ack_replays_original_response_and_prevents_conflict(tmp_path):
    def lost(stage):
        if stage == "before_acknowledgment":
            raise RuntimeError("ack lost")

    campaign, batch, source = setup(tmp_path, fault=lost)
    original = request(
        campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="baseline"
    )
    with pytest.raises(RuntimeError, match="ack lost"):
        campaign.handle(original)
    reader = EngineeringCampaign(campaign.store.root, batch)
    assert reader.handle(original).status == "ok"
    assert (
        reader.handle(replace(original, payload={"candidate_id": "better", "mode": "fixed"})).error
        == "request_conflict"
    )
    assert len(batch.replay().reservations) == 2


def test_completed_processes_before_event_recover_without_dispatch(tmp_path):
    def lost(stage):
        if stage == "engineering_campaign_result_ready":
            raise RuntimeError("before event")

    campaign, batch, source = setup(tmp_path, fault=lost)
    original = request(
        campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="baseline"
    )
    with pytest.raises(RuntimeError):
        campaign.handle(original)
    assert len(batch.replay().reservations) == 2
    reopened = EngineeringCampaign(campaign.store.root, batch, executor=campaign.executor)
    assert reopened.handle(request(reopened, "review")).error == "reconciliation_required"
    assert reopened.handle(original).status == "ok"
    assert len(batch.replay().reservations) == 2


def test_partial_scenario_continuation_requires_explicit_option(tmp_path):
    def lost(stage):
        if stage == "engineering_scenario_observed":
            raise RuntimeError("after scenario")

    campaign, batch, source = setup(tmp_path, executor_fault=lost)
    original = request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"})
    with pytest.raises(RuntimeError):
        campaign.handle(original)
    assert len(batch.replay().reservations) == 1
    runner = SupervisedEngineeringExecutor(campaign.spec.execution, batch, "first", source)
    reopened = EngineeringCampaign(campaign.store.root, batch, executor=runner)
    with pytest.raises(StoreError):
        reopened.handle(original)
    assert len(batch.replay().reservations) == 1
    assert reopened.handle(original, resume_scenarios=True).status == "ok"
    assert len(batch.replay().reservations) == 2


def test_completed_calibration_before_event_reuses_optimizer(tmp_path):
    campaign, batch, source = setup(tmp_path)
    campaign.handle(
        request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="baseline")
    )
    original = request(
        campaign, "evaluate", {"candidate_id": "calibration", "mode": "calibrated"}, id="numerical"
    )

    def lost(stage):
        if stage == "engineering_campaign_result_ready":
            raise RuntimeError("before event")

    campaign.fault = lost
    with pytest.raises(RuntimeError):
        campaign.handle(original)
    assert len(batch.replay().reservations) == 6
    reopened = EngineeringCampaign(campaign.store.root, batch, executor=campaign.executor)
    assert reopened.handle(original).status == "ok"
    assert len(batch.replay().reservations) == 6


def test_exact_schema_domain_sources_and_complete_reserve(tmp_path):
    campaign, batch, source = setup(tmp_path)
    assert EngineeringCampaignSpec.from_json(campaign.spec.to_json()) == campaign.spec
    with pytest.raises(ValueError):
        replace(campaign.spec, baseline_configuration={"x": 2.0})
    with pytest.raises(ValueError):
        replace(campaign.spec, designs=(EngineeringDesign("other", {"x": 0.3}),) * 2)
    assert (
        campaign.handle(
            request(
                campaign,
                "evaluate",
                {"candidate_id": "baseline", "mode": "fixed", "configuration": "override"},
            )
        ).error
        == "schema_error"
    )
    reader = EngineeringCampaign(campaign.store.root, batch)
    with pytest.raises(StoreError, match="read-only"):
        reader.handle(request(reader, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}))
    assert len(batch.replay().reservations) == 0


def test_incomplete_calibration_never_continues_on_default_retry(tmp_path):
    calls = []

    def lost(stage):
        if stage == "engineering_scenario_observed":
            calls.append(stage)
            if len(calls) == 3:
                raise RuntimeError("partial calibration")

    campaign, batch, source = setup(tmp_path, executor_fault=lost)
    campaign.handle(
        request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="baseline")
    )
    original = request(
        campaign, "evaluate", {"candidate_id": "calibration", "mode": "calibrated"}, id="numerical"
    )
    from autoengineering.utility.studies import EngineeringReconciliationRequired

    with pytest.raises(EngineeringReconciliationRequired):
        campaign.handle(original)
    assert len(batch.replay().reservations) == 3
    runner = SupervisedEngineeringExecutor(campaign.spec.execution, batch, "first", source)
    reopened = EngineeringCampaign(campaign.store.root, batch, executor=runner)
    with pytest.raises(EngineeringReconciliationRequired):
        reopened.handle(original)
    assert len(batch.replay().reservations) == 3
    assert reopened.handle(original, resume_scenarios=True).status == "ok"
    assert len(batch.replay().reservations) == 6


def test_empty_predispatch_directory_can_recover_without_free_retry(tmp_path):
    def lost(stage):
        if stage == "engineering_campaign_before_intent":
            raise RuntimeError("before intent")

    campaign, batch, source = setup(tmp_path, fault=lost)
    original = request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"})
    with pytest.raises(RuntimeError):
        campaign.handle(original)
    assert not batch.replay().reservations
    reopened = EngineeringCampaign(campaign.store.root, batch, executor=campaign.executor)
    assert reopened.handle(original).status == "ok"
    assert len(batch.replay().reservations) == 2


def test_reader_cannot_mutate_and_replay_needs_no_model_process(tmp_path, monkeypatch):
    campaign, batch, source = setup(tmp_path)
    original = request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"})
    campaign.handle(original)

    def denied(*args, **kwargs):
        raise AssertionError("offline read attempted scientific execution")

    import autoengineering.utility.engineering_process as process

    monkeypatch.setattr(process, "supervise_process", denied)
    monkeypatch.setattr(process, "recover_completed_process", denied)
    monkeypatch.setattr(SupervisedEngineeringExecutor, "__init__", denied)
    reader = EngineeringCampaign(campaign.store.root, batch)
    assert reader.handle(original).status == "ok"
    assert len(reader.state()["evaluations"]) == 1
    with pytest.raises(StoreError, match="read-only"):
        reader.handle(request(reader, "review"))
    assert len(batch.replay().reservations) == 2


def test_failed_baseline_can_freeze_explicit_no_eligible_selection(tmp_path):
    campaign, batch, source = setup(tmp_path, baseline=1.0)
    campaign.handle(request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}))
    assert campaign.handle(request(campaign, "review")).result["outcome"] == "no_eligible_model"
    assert campaign.handle(request(campaign, "freeze")).status == "ok"
    state = campaign.state()
    assert state["selected"] is None and state["decision"].selected_id is None
    assert len(batch.replay().reservations) == 2


def test_one_case_cannot_bind_another_campaign_or_expand_grants(tmp_path):
    campaign, batch, source = setup(tmp_path)
    with pytest.raises(StoreError, match="different campaign"):
        EngineeringCampaign.create(tmp_path / "second-controller", campaign.spec, campaign.executor)
    with pytest.raises(StoreError, match="different campaign"):
        EngineeringCampaign.create(
            tmp_path / "second-controller",
            replace(campaign.spec, max_requests=100),
            campaign.executor,
        )
    assert not batch.replay().reservations


def test_repeated_design_stale_request_and_unknown_tool_do_not_add_science(tmp_path):
    campaign, batch, source = setup(tmp_path, max_requests=4)
    original = request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"})
    assert campaign.handle(original).status == "ok"
    assert campaign.handle(replace(original, request_id="stale")).error == "stale_revision"
    assert campaign.handle(request(campaign, "confirm")).error == "schema_error"
    for name in ("repeat-one", "repeat-two", "repeat-three"):
        assert (
            campaign.handle(
                request(
                    campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id=name
                )
            ).status
            == "ok"
        )
    assert len(campaign.state()["evaluations"]) == 1
    assert campaign.handle(request(campaign, "review")).error == "budget_exhausted"
    assert len(batch.replay().reservations) == 2
