"""Supplied four-role workflow parity, isolation and exact-envelope recovery."""

from dataclasses import replace
from itertools import repeat
import json

import pytest

from autoengineering.agents.broker import CampaignBroker, WorkflowStopped
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.records import (
    CampaignAction,
    Finding,
    ResourceLimits,
    RoleHandoff,
)
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.records import CandidateProposal
from autoengineering.campaign.store import StoreError
from examples.agent_campaign.fixture import agent_fixture
from examples.agent_campaign.scripted import scripted_host, supplied_reply
from examples.campaign_contracts.build_fixture import ROOT
from test_agent_contracts import run_spec


def create(tmp_path, *, host=None, spec=None, limit=None, clock=None, limits=None):
    path = tmp_path / "input.yaml"
    (spec or agent_fixture()).to_yaml(path)
    controller = CampaignController.create(
        path, ROOT, tmp_path / "campaign", max_new_evaluations=limit
    )
    identity = json.loads((controller.store.root / "identity.json").read_text())
    spec = replace(
        run_spec(),
        campaign_id=controller.spec.name,
        campaign_identity=identity["scientific_identity"],
        permitted_interventions=("linear-v2",),
        role_templates=template_digests(),
        tool_policy_digest=POLICY_DIGEST,
        source_identity=host_source_identity(),
        environment_identity=host_environment_identity(),
        limits=limits or ResourceLimits(20, 16, 4, 2, 300, 30, 262144, 1048576),
    )
    store = WorkerStore.create(tmp_path / "worker", spec, **({"clock": clock} if clock else {}))
    scheduler = SerialScheduler(store, host or scripted_host())
    return CampaignBroker(controller, scheduler), path


def test_four_roles_match_direct_scientific_decision_without_private_prompt_data(tmp_path):
    broker, path = create(tmp_path)
    assert broker.advance().state == "completed"
    state = broker.controller.state()
    direct = CampaignController.create(path, ROOT, tmp_path / "direct")
    assert direct.advance().state == "completed"
    assert state.outcome == direct.state().outcome == "accepted_candidate"
    decision = state.decisions[-1]
    other = direct.state().decisions[-1]
    assert decision.outcome == other.outcome
    assert decision.selected_configuration == other.selected_configuration == {"multiplier": 1.5}
    assert len(state.budget.attempts) == len(direct.state().budget.attempts) == 2
    assert state.confirmation == "confirmation_not_attempted"
    journal = broker.store.replay()
    assert {task.role for task in journal.tasks.values()} == {
        "orchestrator",
        "investigator",
        "implementer",
        "reviewer",
    }
    assert len(journal.invocations) == 7
    assert all(action.state == "completed" for action in journal.actions.values())
    assert {a.request.operation for a in journal.actions.values() if a.request} >= {
        "evaluate",
        "propose",
        "admit",
        "review",
        "freeze",
        "confirm",
        "report",
    }
    for _, task, prompt in broker.scheduler.host.calls:
        assert str(broker.controller.store.root) not in prompt
        assert "comparison.json" not in prompt
        assert "source_bundle" not in prompt
        assert "control/" not in prompt
        assert "process_receipt" not in prompt
        assert all(g.visibility == "worker_summary" for g in task.grants)
    host_calls = len(broker.scheduler.host.calls)
    attempts = len(state.budget.attempts)
    broker.advance()
    assert len(broker.scheduler.host.calls) == host_calls
    assert len(broker.controller.state().budget.attempts) == attempts


def test_external_scientific_actions_release_writer_and_exclude_competing_replay(tmp_path):
    from autoengineering.campaign.store import WriterBusy

    broker, _ = create(tmp_path)
    other = WorkerStore(broker.store.root)
    competing = CampaignBroker(broker.controller, SerialScheduler(other, scripted_host()))
    handle = broker.controller.service.handle
    stage = broker.controller.stage_record
    observations = []

    def check_lock(kind):
        with other.writer():
            assert any(a.state == "reserved" for a in other.replay().actions.values())
        with pytest.raises(WriterBusy, match="operation"):
            competing.reconcile_actions()
        observations.append(kind)

    def checked_handle(request):
        check_lock("request")
        return handle(request)

    def checked_stage(record, name="record.json"):
        check_lock("stage")
        return stage(record, name)

    broker.controller.service.handle = checked_handle
    broker.controller.stage_record = checked_stage
    assert broker.advance().state == "completed"
    assert set(observations) == {"request", "stage"}
    assert len(broker.controller.state().budget.attempts) == 2


def test_lost_scientific_response_replays_original_envelope_and_no_physical_restart(tmp_path):
    broker, _ = create(tmp_path)
    handle = broker.controller.service.handle
    envelopes = []

    def lose(request):
        handle(request)
        envelopes.append(request.to_json())
        raise RuntimeError("lost campaign response")

    broker.controller.service.handle = lose
    with pytest.raises(RuntimeError, match="lost campaign"):
        broker.advance()
    journal = broker.store.replay()
    pending = next(a for a in journal.actions.values() if a.state == "reserved")
    assert pending.request.operation == "evaluate"
    assert len(broker.controller.state().budget.attempts) == 1
    controller = CampaignController.open(broker.controller.store.root)
    original = controller.service.handle

    def observe(request):
        if request.request_id == pending.request.request_id:
            envelopes.append(request.to_json())
        return original(request)

    controller.service.handle = observe
    resumed = CampaignBroker(
        controller, SerialScheduler(WorkerStore(broker.store.root), scripted_host())
    )
    assert resumed.advance().state == "completed"
    assert envelopes == [pending.request.to_json()] * 2
    assert len(controller.state().budget.attempts) == 2


def test_lost_staging_ack_reuses_staged_bytes_and_completed_roles(tmp_path):
    broker, _ = create(tmp_path)
    stage = broker.controller.stage_record
    count = 0

    def lose(record, name="record.json"):
        nonlocal count
        value = stage(record, name)
        if isinstance(record, CandidateProposal):
            count += 1
            raise RuntimeError("lost staging acknowledgment")
        return value

    broker.controller.stage_record = lose
    with pytest.raises(RuntimeError, match="lost staging"):
        broker.advance()
    assert len(broker.scheduler.host.calls) == 2
    broker.controller.stage_record = stage
    assert broker.advance().state == "completed"
    assert count == 1
    assert len(broker.scheduler.host.calls) == 7
    sources = [a for a in broker.store.replay().actions.values() if a.kind == "stage_proposal"]
    assert len(sources) == 1
    assert len(broker.controller.state().proposals) == 1


def test_illegal_orchestrator_assignment_consumes_repairs_before_science(tmp_path):
    def bad(task, prompt, invocation):
        result = supplied_reply(task, prompt, invocation)
        handoff = RoleHandoff.from_json(result.raw_output)
        return replace(
            result,
            raw_output=replace(handoff, output=replace(handoff.output, role="reviewer")).to_json(),
        )

    broker, _ = create(tmp_path, host=FakeHost(repeat(bad)))
    with pytest.raises(StoreError, match="repair allowance"):
        broker.advance()
    assert len(broker.scheduler.host.calls) == 3
    assert all(v.state == "invalid_output" for v in broker.store.replay().invocations.values())
    assert not broker.controller.state().proposals
    assert len(broker.controller.state().budget.attempts) == 1
    assert broker.store.replay().repairs_used == 2


@pytest.mark.parametrize("repairs", [0, 1])
def test_invalid_candidate_stops_at_frozen_repair_limit_across_reopen(tmp_path, repairs):
    def ineligible(task, prompt, invocation):
        result = supplied_reply(task, prompt, invocation)
        if task.role == "investigator":
            handoff = RoleHandoff.from_json(result.raw_output)
            result = replace(
                result,
                raw_output=replace(
                    handoff,
                    output=replace(handoff.output, eligibility_gaps=("missing evidence",)),
                ).to_json(),
            )
        return result

    host = FakeHost(repeat(ineligible))
    broker, _ = create(
        tmp_path,
        host=host,
        limits=ResourceLimits(20, 16, repairs, repairs, 300, 30, 262144, 1048576),
    )
    for _ in range(2):
        with pytest.raises(WorkflowStopped, match="investigator repair allowance exhausted"):
            broker.advance()
        assert len(host.calls) == 2 + repairs
        assert len(broker.controller.state().budget.attempts) == 1
        assert not broker.controller.state().proposals
        assert not broker.store.replay().pending
        broker = CampaignBroker(
            broker.controller, SerialScheduler(WorkerStore(broker.store.root), host)
        )


def test_descriptive_check_citation_stops_without_acceptance_or_repair(tmp_path):
    def descriptive(task, prompt, invocation):
        result = supplied_reply(task, prompt, invocation)
        if task.role == "reviewer":
            handoff = RoleHandoff.from_json(result.raw_output)
            review = replace(
                handoff.output,
                findings=(
                    Finding(
                        "relative-objective-met",
                        "information",
                        "The supplied evidence reports a passing finite check.",
                        ("evaluation-attempt-000002-comparison: finite, version 1, status=pass",),
                        handoff.output.evidence_ids,
                    ),
                ),
            )
            result = replace(result, raw_output=replace(handoff, output=review).to_json())
        return result

    host = FakeHost(repeat(descriptive))
    broker, _ = create(
        tmp_path,
        host=host,
        limits=ResourceLimits(20, 16, 0, 0, 300, 30, 262144, 1048576),
    )
    for _ in range(2):
        with pytest.raises(WorkflowStopped, match="reviewer repair allowance exhausted"):
            broker.advance()
        journal = broker.store.replay()
        assert len(host.calls) == 6
        assert list(journal.invocations.values())[-1].state == "invalid_output"
        assert len(broker.controller.state().budget.attempts) == 2
        assert broker.controller.store.replay().state == "evidence_ready"
        assert not broker.controller.state().decisions
        broker = CampaignBroker(
            broker.controller, SerialScheduler(WorkerStore(broker.store.root), host)
        )


def test_blocking_review_pauses_science_and_is_not_dispatched_again(tmp_path):
    def block(task, prompt, invocation):
        result = supplied_reply(task, prompt, invocation)
        if task.role != "reviewer":
            return result
        handoff = RoleHandoff.from_json(result.raw_output)
        review = replace(
            handoff.output,
            recommendation="repair",
            findings=(
                Finding(
                    "blocked",
                    "blocking",
                    "Required evidence needs a trusted disposition",
                    ("finite",),
                    handoff.output.evidence_ids,
                ),
            ),
        )
        return replace(result, raw_output=replace(handoff, output=review).to_json())

    broker, _ = create(tmp_path, host=FakeHost(repeat(block)))
    with pytest.raises(WorkflowStopped, match="unresolved findings"):
        broker.advance()
    assert broker.controller.store.replay().state == "evidence_ready"
    assert not broker.controller.state().decisions
    host_calls = len(broker.scheduler.host.calls)
    with pytest.raises(WorkflowStopped, match="unresolved findings"):
        broker.advance()
    assert len(broker.scheduler.host.calls) == host_calls
    # A trusted caller can explicitly dispose of advisory findings. The
    # original review remains immutable and the controller still decides.
    review_invocation = next(
        v
        for v in broker.store.replay().invocations.values()
        if broker.store.replay().tasks[v.task_id].role == "reviewer"
    )
    with pytest.raises(ValueError):
        broker.dispose_review(review_invocation.id, reason=" ")
    disposition = broker.dispose_review(
        review_invocation.id, reason="Reviewed the development evidence"
    )
    assert disposition.review_digest == broker.scheduler.handoff(review_invocation).output.digest
    assert broker.advance().state == "completed"
    assert len(broker.scheduler.host.calls) == host_calls + 1  # final orchestrator only


def test_favorable_reviewer_cannot_override_executed_ineligibility(tmp_path):
    spec = agent_fixture()
    spec = replace(
        spec,
        acceptance=replace(
            spec.acceptance,
            checks=tuple(
                replace(check, version="not-registered") for check in spec.acceptance.checks
            ),
        ),
    )
    broker, _ = create(tmp_path, spec=spec)
    assert broker.advance().state == "completed"
    assert broker.controller.state().outcome == "no_eligible_model"
    assert broker.controller.state().decisions[-1].selected_id is None


def test_summary_needs_no_private_arrays_and_cannot_follow_private_artifacts(tmp_path, monkeypatch):
    broker, _ = create(tmp_path)
    monkeypatch.setattr(broker.controller, "_arrays", lambda *_: pytest.fail("private read"))
    summary = broker.summary()
    text = json.dumps(summary)
    assert "source_bundle" not in text
    assert "artifacts" not in text
    assert "children" not in text
    assert "comparison.json" not in text
    assert str(ROOT) not in text
    assert set(summary["interface"][0]) == {"name", "units", "dimensions"}


def test_calibrated_review_receives_actual_configuration_and_fit_link_without_private_reads(
    tmp_path, monkeypatch
):
    from test_campaign_studies import calibrated_spec

    captured = []

    def inspect_review(task, prompt, invocation):
        if task.role == "reviewer":
            envelope = json.loads(prompt[prompt.index('{"approved_evidence"') :])
            summary = json.loads(envelope["approved_evidence"][0]["content"])
            current = summary["submitted_handoff"]
            evaluation = next(
                e for e in summary["evaluations"] if e["id"] == current["evaluation_id"]
            )
            assert summary["schema_version"] == "1.1"
            assert summary["calibration"]["owner"] == "trusted_controller"
            assert summary["calibration"]["seed"] == 17
            assert summary["confirmation_policy"] == "disabled"
            assert summary["catalogue"][0]["parameter_role"] == "starting"
            assert evaluation["model_id"] == current["snapshot_digest"]
            assert evaluation["purpose"] == "calibrated"
            link = next(
                item
                for item in summary["calibration_studies"]
                if item["study_id"] == evaluation["calibration_study_id"]
            )
            assert link["candidate_id"] == current["proposal"]["id"]
            assert link["committed_manifest_sha256"]
            assert any(
                item["configuration"] == evaluation["configuration"]
                and item["model_id"] == evaluation["model_id"]
                and item["split_id"] == summary["calibration"]["fitting_data_id"]
                for item in summary["evaluations"]
            )
            captured.append(summary)
        return supplied_reply(task, prompt, invocation)

    broker, _ = create(tmp_path, spec=calibrated_spec(), host=FakeHost(repeat(inspect_review)))
    assert broker.advance().state == "completed"
    assert len(captured) == 1
    monkeypatch.setattr(broker.controller, "_arrays", lambda *_: pytest.fail("private read"))
    summary = broker.summary()
    summary["evaluations"][-1]["configuration"]["multiplier"] = -100
    assert broker.controller.state().evaluations[-1].configuration["multiplier"] != -100
    assert "children" not in json.dumps(summary)
    assert str(ROOT) not in json.dumps(summary)


def test_campaign_action_schema_and_conflicting_reuse(tmp_path):
    broker, _ = create(tmp_path, limit=0)
    response = broker.request("state", key="inspect")
    assert response.status == "ok"
    assert broker.request("state", key="inspect") == response
    with pytest.raises(StoreError, match="different content"):
        broker.request("state", {"unexpected": "value"}, key="inspect")
    action = next(iter(broker.store.replay().actions.values()))
    assert CampaignAction.from_json(action.to_json()) == action
    with pytest.raises(ValueError, match="response identity"):
        replace(action, response=replace(response, request_id="different"))
    with broker.store.writer(), pytest.raises(StoreError, match="immutable"):
        broker.store.commit(action)


def test_cancel_queues_both_intents_while_both_writers_are_busy(tmp_path):
    broker, _ = create(tmp_path, limit=0)
    with broker.store.writer(), broker.controller.store.writer():
        result = broker.cancel()
    assert result["worker_stop"] == result["scientific_stop"] == "queued"
    assert not broker.store.replay().invocations
    with pytest.raises(WorkflowStopped, match="cancellation"):
        broker.advance()
    assert not broker.controller.state().budget.attempts


def test_committed_scientific_error_is_not_blindly_retried_with_a_new_revision(tmp_path):
    broker, _ = create(tmp_path, limit=0)
    with pytest.raises(WorkflowStopped, match="invalid_transition"):
        broker.request("freeze", key="premature")
    actions = broker.store.replay().actions
    with pytest.raises(WorkflowStopped, match="invalid_transition"):
        broker.advance()
    assert broker.store.replay().actions == actions
    assert not broker.scheduler.host.calls
