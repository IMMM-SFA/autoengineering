"""Serial dispatch, prompt identity and restart limits without a live host."""

from dataclasses import replace

import pytest

from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.records import ArtifactGrant, NextStep
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.store import StoreError
from test_agent_contracts import handoff, run_spec, task_assignment


def setup(tmp_path, results=None, spec=None):
    spec = spec or replace(
        run_spec(),
        role_templates=template_digests(),
        tool_policy_digest=POLICY_DIGEST,
        source_identity=host_source_identity(),
        environment_identity=host_environment_identity(),
    )
    store = WorkerStore.create(tmp_path / "worker", spec, clock=lambda: 100)
    with store.writer():
        ref = store.put_private(
            b'{"catalogue":["linear"]}', name="summary.json", media_type="application/json"
        )
    grant = ArtifactGrant(
        "1.0", spec.id, "investigate", "investigator", ref, "read", 1000, "worker_summary"
    )
    task = replace(task_assignment((grant,)), deadline=200)
    output = replace(handoff(ref.sha256), invocation_id="call-000001")
    host = FakeHost(
        results
        if results is not None
        else [
            HostResult("completed", output.to_json(), None, {"total_tokens": None}, 1),
        ]
    )
    return store, host, task, output


def test_persisted_prompt_raw_and_normalized_and_completed_replay(tmp_path):
    store, host, task, output = setup(tmp_path)
    scheduler = SerialScheduler(store, host, clock=lambda: 100)
    value = scheduler.dispatch(task, campaign_revision=3)
    assert value.state == "completed"
    assert value.raw_response and value.normalized_output and value.completion_receipt
    assert value.resolved_model is None
    assert value.usage["total_tokens"] is None
    assert scheduler.handoff(value) == output
    assert '"invocation_id":"call-000001"' in host.calls[0][2]
    reopened = SerialScheduler(WorkerStore(store.root), host, clock=lambda: 101)
    assert reopened.dispatch(task, campaign_revision=3) == value
    assert len(host.calls) == 1
    assert len(store.replay().events) == 5  # start, task, reserve, raw, normalized


def test_host_call_releases_journal_writer_but_excludes_dispatch_and_recovery(tmp_path):
    from autoengineering.campaign.store import WriterBusy

    store, host, task, output = setup(tmp_path)
    other = WorkerStore(store.root)
    observations = []

    def reply(*_):
        # A fresh store must acquire the actual OS lock, not a local flag.
        with other.writer():
            observations.append(other.replay().pending[0].id)
        competing = SerialScheduler(other, host, clock=lambda: 101)
        with pytest.raises(WriterBusy, match="operation"):
            competing.recover_invocation("call-000001", campaign_revision=3)
        with pytest.raises(WriterBusy, match="operation"):
            competing.dispatch(task, campaign_revision=3)
        return HostResult("completed", output.to_json(), None, {}, 1)

    host = FakeHost([reply])
    result = SerialScheduler(store, host, clock=lambda: 100).dispatch(task, campaign_revision=3)
    assert result.state == "completed"
    assert observations == ["call-000001"]
    assert len(host.calls) == 1


def test_invalid_output_repairs_are_new_invocations_and_exhaust_across_restart(tmp_path):
    store, host, task, _ = setup(tmp_path, [HostResult("completed", "{broken", None, {}, 1)] * 3)
    for attempt in range(3):
        scheduler = SerialScheduler(WorkerStore(store.root), host, clock=lambda: 100)
        value = scheduler.dispatch(task, campaign_revision=3)
        assert value.state == "invalid_output"
        assert value.attempt == attempt
    with pytest.raises(StoreError, match="repair allowance"):
        scheduler.dispatch(task, campaign_revision=3)
    assert len(host.calls) == 3
    assert len(store.replay().invocations) == 3


def test_cancellation_and_deadline_prevent_dispatch(tmp_path):
    store, host, task, _ = setup(tmp_path)
    scheduler = SerialScheduler(store, host, clock=lambda: 201)
    with pytest.raises(StoreError, match="deadline"):
        scheduler.dispatch(task, campaign_revision=3)
    assert not host.calls
    store.request_cancel()
    with pytest.raises(StoreError, match="cancellation"):
        SerialScheduler(store, host, clock=lambda: 100).dispatch(task, campaign_revision=3)
    assert not store.replay().invocations


def test_pending_raw_output_after_fault_never_relaunches(tmp_path):
    store, host, task, _ = setup(tmp_path)
    commits = 0

    def fail(stage):
        nonlocal commits
        if stage == "after_event_commit":
            commits += 1
            if commits == 3:
                raise RuntimeError("lost raw acknowledgment")

    store.fault = fail
    scheduler = SerialScheduler(store, host, clock=lambda: 100)
    with pytest.raises(RuntimeError, match="lost raw"):
        scheduler.dispatch(task, campaign_revision=3)
    replay = WorkerStore(store.root).replay()
    assert replay.pending[0].raw_response is not None
    assert replay.pending[0].state == "reconciliation_required"
    with pytest.raises(StoreError, match="reconciliation"):
        SerialScheduler(WorkerStore(store.root), host, clock=lambda: 101).dispatch(
            task, campaign_revision=3
        )
    assert len(host.calls) == 1


def test_template_policy_and_generated_mode_changes_fail_before_dispatch(tmp_path):
    store, host, _, _ = setup(tmp_path)
    store.spec = replace(store.spec, tool_policy_digest="0" * 64)
    with pytest.raises(StoreError, match="policy"):
        SerialScheduler(store, host)
    store.spec = replace(store.spec, tool_policy_digest=POLICY_DIGEST, execution_mode="generated")
    store.spec = replace(
        store.spec, host=replace(store.spec.host, kind="codex", auth_mode="subscription")
    )
    with pytest.raises(StoreError, match="boundary"):
        SerialScheduler(store, host)
    store.spec = replace(
        store.spec,
        execution_mode="supplied",
        host=replace(store.spec.host, kind="fake", auth_mode="none"),
        role_templates={**store.spec.role_templates, "reviewer": "0" * 64},
    )
    with pytest.raises(StoreError, match="template"):
        SerialScheduler(store, host)
    assert not host.calls


def test_reviewer_prompt_contains_no_previous_role_transcript(tmp_path):
    store, host, task, _ = setup(tmp_path)
    # Complete an orchestrator invocation with private rationale, then invoke
    # the reviewer with just its explicitly granted evaluation summary.
    orchestrator = replace(
        task, id="orchestrate", role="orchestrator", grants=(), allowed_operations=("stop",)
    )
    secret = "implementer scratch that reviewer must not receive"
    first = replace(
        handoff(),
        role="orchestrator",
        task_id=orchestrator.id,
        invocation_id="call-000001",
        output=NextStep("stop", None, secret),
        proposed_next_action="stop",
        supporting_artifact_ids=(),
    )
    host = FakeHost(
        [
            HostResult("completed", first.to_json(), None, {}, 1),
            HostResult("completed", "{invalid review", None, {}, 1),
        ]
    )
    scheduler = SerialScheduler(store, host, clock=lambda: 100)
    assert scheduler.dispatch(orchestrator, campaign_revision=3).state == "completed"
    reviewer = replace(
        task, id="review", role="reviewer", grants=(), allowed_operations=("review",)
    )
    scheduler.dispatch(reviewer, campaign_revision=3)
    assert secret not in host.calls[1][2]
    assert '"role":"reviewer"' in host.calls[1][2]


def test_run_deadline_starts_at_creation_and_survives_restart(tmp_path):
    store, host, task, _ = setup(tmp_path)
    task = replace(task, deadline=1000)
    reopened = WorkerStore(store.root)
    assert reopened.replay().started_at == 100
    with pytest.raises(StoreError, match="deadline"):
        SerialScheduler(reopened, host, clock=lambda: 221).dispatch(task, campaign_revision=3)
    assert not host.calls


def test_source_environment_and_capability_changes_require_a_new_run(tmp_path, monkeypatch):
    store, host, task, _ = setup(tmp_path, [HostResult("completed", "{invalid", None, {}, 1)])
    scheduler = SerialScheduler(store, host, clock=lambda: 100)
    assert scheduler.dispatch(task, campaign_revision=3).state == "invalid_output"
    capabilities = host.capabilities()
    monkeypatch.setattr(
        host, "capabilities", lambda: replace(capabilities, executable_version="changed")
    )
    with pytest.raises(StoreError, match="capabilities changed"):
        scheduler.dispatch(task, campaign_revision=3)
    assert len(host.calls) == 1
    import autoengineering.agents.scheduler as module

    monkeypatch.setattr(module, "host_source_identity", lambda: "0" * 64)
    with pytest.raises(StoreError, match="source identity"):
        SerialScheduler(WorkerStore(store.root), host)
    monkeypatch.setattr(module, "host_source_identity", lambda: store.spec.source_identity)
    monkeypatch.setattr(module, "host_environment_identity", lambda: "0" * 64)
    with pytest.raises(StoreError, match="environment identity"):
        SerialScheduler(WorkerStore(store.root), host)


def test_saved_raw_result_recovers_without_a_new_host_call(tmp_path):
    store, host, task, output = setup(tmp_path)
    count = 0

    def fail(stage):
        nonlocal count
        if stage == "after_event_commit":
            count += 1
            if count == 3:
                raise RuntimeError("raw acknowledgment lost")

    store.fault = fail
    scheduler = SerialScheduler(store, host, clock=lambda: 100)
    with pytest.raises(RuntimeError, match="raw acknowledgment"):
        scheduler.dispatch(task, campaign_revision=3)
    reopened = SerialScheduler(WorkerStore(store.root), host, clock=lambda: 101)
    result = reopened.recover_invocation("call-000001", campaign_revision=3)
    assert result.state == "completed"
    assert reopened.handoff(result) == output
    assert len(host.calls) == 1
    assert reopened.recover_invocation(result.id, campaign_revision=3) == result
    assert len(host.calls) == 1
