"""One-persona comparator over unchanged supplied scientific rules. No live model."""

from dataclasses import replace
from itertools import repeat
import json
import time

import pytest
from click.testing import CliRunner

from autoengineering.agents.broker import CampaignBroker, workflow_broker, WorkflowStopped
from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.hosts.scripted import scripted_host, single_supplied_reply
from autoengineering.agents.permissions import read_granted, validate_handoff
from autoengineering.agents.records import (
    AgentRunSpec,
    CandidateBrief,
    NextStep,
    ReviewFindings,
    RoleHandoff,
    SINGLE_ROLE,
    SuppliedConfiguration,
    TaskAssignment,
)
from autoengineering.agents.report import evidence_report, render_report
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.single_agent import single_agent_spec, HISTORY_BYTES, HISTORY_ITEMS
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError
from autoengineering.cli import cli
from examples.agent_campaign.run import prepare


def fixture(tmp_path, *, route="single_agent", responder=None, repairs=None):
    controller, spec = prepare(tmp_path, workflow_route=route)
    if repairs is not None:
        spec = replace(
            spec, limits=replace(spec.limits, max_repairs=repairs, repairs_per_task=repairs)
        )
        (tmp_path / "agent-run.json").write_text(spec.to_json())
    store = WorkerStore.create(tmp_path / "worker", spec)
    host = FakeHost(repeat(responder)) if responder else scripted_host(route)
    scheduler = SerialScheduler(store, host)
    return workflow_broker(controller, scheduler)


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def summary(prompt):
    frame = json.loads(prompt[prompt.index('{"approved_evidence"') :])
    return json.loads(frame["approved_evidence"][0]["content"])


def test_single_route_has_four_calls_one_persona_and_same_science_as_four_roles(tmp_path):
    single = fixture(tmp_path / "single")
    four = fixture(tmp_path / "four", route="four_role")
    for broker in (single, four):
        broker.advance()
    a, b = evidence_report(single.store), evidence_report(four.store)
    assert a["status"] == b["status"] == "completed"
    assert a["roles_ran"] == [SINGLE_ROLE]
    assert a["workflow_route"] == "single_agent" and a["review_context"] == "self_review"
    assert b["workflow_route"] == "four_role" and b["review_context"] == "independent_role"
    assert len(single.scheduler.host.calls) == 4 and len(four.scheduler.host.calls) == 7
    assert "self_review" in render_report(a)
    for key in ("selected_configuration", "objective_value", "outcome", "confirmation"):
        assert a["scientific_evidence"][key] == b["scientific_evidence"][key]
    assert a["physical_work"]["attempts"] == b["physical_work"]["attempts"] == 2
    assert single.controller.spec.acceptance == four.controller.spec.acceptance
    assert [a.request.operation for a in single.store.replay().actions.values() if a.request] == [
        a.request.operation for a in four.store.replay().actions.values() if a.request
    ]
    assert [
        type(single.scheduler.handoff(v).output) for v in single.store.replay().invocations.values()
    ] == [CandidateBrief, SuppliedConfiguration, ReviewFindings, NextStep]
    before = snapshot(single.store.root)
    single.advance()
    assert len(single.scheduler.host.calls) == 4 and snapshot(single.store.root) == before


def test_old_record_serialization_and_explicit_route_versions_are_preserved(tmp_path):
    _, four = prepare(tmp_path / "four")
    assert "workflow_route" not in four.to_dict()
    assert AgentRunSpec.from_json(four.to_json()) == four
    with pytest.raises(ValueError, match="schema 1.1"):
        AgentRunSpec.from_dict({**four.to_dict(), "workflow_route": "four_role"})
    single = single_agent_spec(four, run_id="one-persona")
    assert single.to_dict()["workflow_route"] == "single_agent" and single.schema_version == "1.1"
    assert AgentRunSpec.from_json(single.to_json()) == single
    for change in (
        {"schema_version": "1.0"},
        {"workflow_route": "four_role"},
        {"execution_mode": "generated"},
        {"role_templates": four.role_templates},
    ):
        with pytest.raises(ValueError):
            replace(single, **change)
    value = single.to_dict()
    del value["workflow_route"]
    with pytest.raises(ValueError):
        AgentRunSpec.from_dict(value)


def test_single_grants_are_exact_and_history_contains_no_raw_transcripts(tmp_path):
    def response(task, prompt, invocation):
        return replace(
            single_supplied_reply(task, prompt, invocation), raw_transcript=b"RAW_TRANSPORT_MARKER"
        )

    broker = fixture(tmp_path, responder=response)
    broker.advance()
    for index, (_, task, prompt) in enumerate(broker.scheduler.host.calls):
        assert task.schema_version == "1.1" and task.expected_schema == "role-handoff-1.2"
        assert task.role == SINGLE_ROLE and all(
            g.role == SINGLE_ROLE and g.schema_version == "1.1" for g in task.grants
        )
        data = summary(prompt)
        assert len(data["agent_history"]) == index
        assert data["history_policy"]["raw_transcripts_included"] is False
        assert "RAW_TRANSPORT_MARKER" not in prompt
        with pytest.raises(PermissionError):
            read_granted(broker.store.root, task, "f" * 64, run_id=task.run_id, role=SINGLE_ROLE)
        with pytest.raises(PermissionError):
            read_granted(
                broker.store.root,
                task,
                task.grants[0].artifact.sha256,
                run_id=task.run_id,
                role="reviewer",
            )
    assert all(
        b"RAW_TRANSPORT_MARKER" == read_bytes(broker.store.root, v.raw_response)
        for v in broker.store.replay().invocations.values()
    )


def test_history_limits_whole_handoffs_and_records_omitted_ids(tmp_path):
    def response(task, prompt, invocation):
        reason = "x" * 9000 if task.id == "task-4" else "Stop this isolated history probe"
        handoff = RoleHandoff(
            "1.2",
            "handoff-" + invocation,
            task.id,
            invocation,
            SINGLE_ROLE,
            0,
            "complete",
            NextStep("stop", None, reason),
            (),
            (),
            "stop",
        )
        return HostResult("completed", handoff.to_json(), None, {}, 0)

    broker = fixture(tmp_path, responder=response)
    for i in range(6):
        task = TaskAssignment(
            "1.1",
            f"task-{i}",
            broker.store.spec.id,
            SINGLE_ROLE,
            None,
            0,
            "History probe",
            (),
            "role-handoff-1.2",
            ("stop",),
            time.time() + 60,
            0,
        )
        broker.scheduler.dispatch(task, campaign_revision=0)
    data = broker.summary()
    assert len(data["agent_history"]) <= HISTORY_ITEMS
    assert len(canonical_json(data["agent_history"]).encode()) <= HISTORY_BYTES
    assert data["history_policy"]["omitted_invocation_ids"] == [
        "call-000001",
        "call-000002",
        "call-000005",
    ]
    assert [v["invocation_id"] for v in data["agent_history"]] == [
        "call-000003",
        "call-000004",
        "call-000006",
    ]


def test_wrong_phase_consumes_one_repair_and_never_adds_science(tmp_path):
    broken = []

    def response(task, prompt, invocation):
        result = single_supplied_reply(task, prompt, invocation)
        handoff = RoleHandoff.from_json(result.raw_output)
        if isinstance(handoff.output, SuppliedConfiguration) and not broken:
            broken.append(invocation)
            wrong = CandidateBrief(
                handoff.output.candidate_id,
                "routing",
                "linear-v2",
                "Wrong phase",
                "Not admissible here",
                handoff.supporting_artifact_ids,
                (),
            )
            return replace(
                result,
                raw_output=replace(handoff, output=wrong, proposed_next_action="propose").to_json(),
            )
        return result

    broker = fixture(tmp_path, responder=response)
    broker.advance()
    calls = list(broker.store.replay().invocations.values())
    assert len(calls) == 5 and broker.store.replay().repairs_used == 1
    rejected = next(v for v in calls if v.id == broken[0])
    assert rejected.state == "invalid_output" and rejected.parse_failure is not None
    assert evidence_report(broker.store)["physical_work"]["attempts"] == 2
    repaired = next(v for v in calls if v.task_id == rejected.task_id and v.attempt == 1)
    assert repaired.id != rejected.id and repaired.state == "completed"


def test_repair_exhaustion_persists_across_reopen(tmp_path):
    calls = []

    def response(task, prompt, invocation):
        calls.append(invocation)
        return HostResult("completed", "not json", None, {}, 0)

    broker = fixture(tmp_path, responder=response, repairs=0)
    with pytest.raises(StoreError, match="repair allowance"):
        broker.advance()
    assert len(calls) == 1
    reopened = workflow_broker(
        CampaignController.open(broker.controller.store.root),
        SerialScheduler(WorkerStore(broker.store.root), FakeHost(repeat(response))),
    )
    with pytest.raises(StoreError, match="repair allowance"):
        reopened.advance()
    assert len(calls) == 1


def test_self_review_block_is_preserved_until_trusted_disposition(tmp_path):
    def response(task, prompt, invocation):
        result = single_supplied_reply(task, prompt, invocation)
        handoff = RoleHandoff.from_json(result.raw_output)
        if isinstance(handoff.output, ReviewFindings):
            return replace(
                result,
                raw_output=replace(
                    handoff,
                    output=replace(
                        handoff.output,
                        recommendation="repair",
                        missing_evidence=("A trusted decision is required",),
                    ),
                ).to_json(),
            )
        return result

    broker = fixture(tmp_path, responder=response)
    with pytest.raises(WorkflowStopped, match="self review"):
        broker.advance()
    review = list(broker.store.replay().invocations.values())[-1]
    assert evidence_report(broker.store)["status"] == "stopped"
    broker.dispose_review(
        review.id, reason="Synthetic fixture: all required executed checks are present"
    )
    broker.advance()
    assert evidence_report(broker.store)["status"] == "completed"
    assert len(broker.scheduler.host.calls) == 4


def test_route_mixing_and_typed_action_mismatch_are_rejected(tmp_path):
    broker = fixture(tmp_path)
    with pytest.raises(StoreError, match="workflow route"):
        CampaignBroker(broker.controller, broker.scheduler)
    task = TaskAssignment(
        "1.0",
        "other",
        broker.store.spec.id,
        "investigator",
        None,
        0,
        "Wrong role",
        (),
        "role-handoff-1.0",
        ("propose",),
        time.time() + 60,
        0,
    )
    with pytest.raises(ValueError, match="workflow route"):
        broker.scheduler.dispatch(task, campaign_revision=0)
    with broker.store.writer():
        with pytest.raises(ValueError, match="workflow route"):
            broker.store.commit(task)
    single = TaskAssignment(
        "1.1",
        "single",
        broker.store.spec.id,
        SINGLE_ROLE,
        None,
        0,
        "Stop",
        (),
        "role-handoff-1.2",
        ("freeze", "stop"),
        time.time() + 60,
        0,
    )
    handoff = RoleHandoff(
        "1.2",
        "one",
        "single",
        "call",
        SINGLE_ROLE,
        0,
        "complete",
        NextStep("stop", None, "Stop"),
        (),
        (),
        "freeze",
    )
    with pytest.raises(ValueError, match="typed output"):
        validate_handoff(
            handoff, single, invocation_id="call", campaign_revision=0, permitted_implementations=()
        )
    with pytest.raises(ValueError):
        replace(handoff, schema_version="1.1")


def test_existing_cli_selects_single_route_and_replay_starts_no_work(tmp_path):
    _, spec = prepare(tmp_path, workflow_route="single_agent")
    args = [
        "agents",
        "run",
        str(tmp_path / "agent-run.json"),
        "--campaign",
        str(tmp_path / "campaign"),
        "--workdir",
        str(tmp_path / "worker"),
    ]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["roles_ran"] == [SINGLE_ROLE] and report["allowances"]["invocations_used"] == 4
    before = snapshot(tmp_path / "worker")
    resumed = CliRunner().invoke(
        cli,
        ["agents", "resume", str(tmp_path / "worker"), "--campaign", str(tmp_path / "campaign")],
    )
    assert resumed.exit_code == 0 and json.loads(resumed.stdout) == report
    assert snapshot(tmp_path / "worker") == before
    assert WorkerStore(tmp_path / "worker").spec == spec


@pytest.mark.parametrize("state", ["reconciliation_required", "completed"])
def test_saved_single_handoff_ack_recovers_without_duplicate_host_or_science(tmp_path, state):
    broker = fixture(tmp_path)

    def fault(point):
        calls = broker.store.replay().invocations
        if (
            point == "after_event_commit"
            and "call-000001" in calls
            and calls["call-000001"].state == state
        ):
            raise RuntimeError("authored single handoff acknowledgment loss")

    broker.store.fault = fault
    with pytest.raises(RuntimeError, match="acknowledgment"):
        broker.advance()
    assert len(broker.scheduler.host.calls) == 1
    resumed_host = scripted_host("single_agent")
    reopened = workflow_broker(
        CampaignController.open(broker.controller.store.root),
        SerialScheduler(WorkerStore(broker.store.root), resumed_host),
    )
    reopened.advance()
    assert len(resumed_host.calls) == 3
    assert evidence_report(reopened.store)["status"] == "completed"
    assert evidence_report(reopened.store)["physical_work"]["attempts"] == 2
    assert len(reopened.store.replay().invocations) == 4


def test_single_source_workspace_and_past_grants_do_not_become_capabilities(tmp_path):
    broker = fixture(tmp_path)
    broker.advance()
    tasks = list(broker.store.replay().tasks.values())
    last = tasks[-1]
    past = tasks[0].grants[0].artifact.sha256
    with pytest.raises(PermissionError):
        read_granted(broker.store.root, last, past, run_id=last.run_id, role=SINGLE_ROLE)
    forbidden = replace(last, grants=(replace(last.grants[0], visibility="candidate_source"),))
    with pytest.raises(ValueError, match="restricted"):
        read_granted(
            broker.store.root,
            forbidden,
            forbidden.grants[0].artifact.sha256,
            run_id=last.run_id,
            role=SINGLE_ROLE,
        )


def test_invalid_single_candidate_stops_before_proposal_and_candidate_execution(tmp_path):
    def response(task, prompt, invocation):
        result = single_supplied_reply(task, prompt, invocation)
        handoff = RoleHandoff.from_json(result.raw_output)
        return replace(
            result,
            raw_output=replace(
                handoff, output=replace(handoff.output, target="unlisted-component")
            ).to_json(),
        )

    broker = fixture(tmp_path, responder=response, repairs=0)
    with pytest.raises(StoreError, match="repair allowance"):
        broker.advance()
    state = broker.controller.state()
    assert len(broker.scheduler.host.calls) == 1 and not state.proposals
    assert len(state.budget.attempts) == 1  # The declared baseline, no candidate work.
    invocation = next(iter(broker.store.replay().invocations.values()))
    assert invocation.state == "invalid_output"
    assert (
        "untried supplied intervention"
        in read_bytes(broker.store.root, invocation.parse_failure).decode()
    )


def test_single_proposal_cannot_exceed_candidate_allowance_even_with_untried_pool(tmp_path):
    def response(task, prompt, invocation):
        evidence = task.grants[0].artifact.sha256
        output = CandidateBrief(
            "candidate", "routing", "linear-v2", "Try another", "Outside allowance", (evidence,), ()
        )
        handoff = RoleHandoff(
            "1.2",
            "handoff-" + invocation,
            task.id,
            invocation,
            SINGLE_ROLE,
            task.campaign_revision,
            "complete",
            output,
            (evidence,),
            (),
            "propose",
        )
        return HostResult("completed", handoff.to_json(), None, {}, 0)

    broker = fixture(tmp_path, responder=response, repairs=0)
    with pytest.raises(StoreError, match="repair allowance"):
        broker._propose_or_freeze("exhausted", False, lambda _: None)
    assert len(broker.scheduler.host.calls) == 1 and not broker.store.replay().actions
    call = next(iter(broker.store.replay().invocations.values()))
    assert call.state == "invalid_output"
    assert (
        "candidate allowance exhausted"
        in read_bytes(broker.store.root, call.parse_failure).decode()
    )
    assert not broker.controller.state().budget.attempts


@pytest.mark.parametrize(
    "stage,calls,starts",
    [("proposal", 1, 1), ("configuration", 2, 1), ("review", 3, 2), ("freeze", 4, 2)],
)
def test_typed_stop_is_preserved_in_every_stage_and_replays_without_work(
    tmp_path, stage, calls, starts
):
    def responder(task, prompt, invocation_id):
        context = summary(prompt)
        state = context["state"]
        tried = bool(context["proposed_interventions"])
        current = (
            "configuration"
            if state == "candidate_pending"
            else "review"
            if state == "evidence_ready"
            else "freeze"
            if tried
            else "proposal"
        )
        result = single_supplied_reply(task, prompt, invocation_id)
        if current == stage:
            handoff = RoleHandoff.from_json(result.raw_output)
            result = replace(
                result,
                raw_output=replace(
                    handoff,
                    output=NextStep("stop", None, f"Authored stop during {stage}"),
                    proposed_next_action="stop",
                ).to_json(),
            )
        return result

    broker = fixture(tmp_path / stage, responder=responder)
    with pytest.raises(WorkflowStopped, match="stopped"):
        broker.advance()
    projection = broker.store.replay()
    assert len(projection.invocations) == calls and projection.repairs_used == 0
    assert len(broker.controller.state().budget.attempts) == starts
    last = list(projection.invocations.values())[-1]
    assert last.state == "completed"
    handoff = broker.scheduler.handoff(last)
    assert handoff.output == NextStep("stop", None, f"Authored stop during {stage}")
    assert handoff.proposed_next_action == "stop"
    before = snapshot(broker.store.root), snapshot(broker.controller.store.root)
    host = FakeHost(())
    reopened = workflow_broker(
        CampaignController.open(broker.controller.store.root),
        SerialScheduler(WorkerStore(broker.store.root), host),
    )
    with pytest.raises(WorkflowStopped, match="stopped"):
        reopened.advance()
    assert not host.calls
    assert (snapshot(broker.store.root), snapshot(broker.controller.store.root)) == before
