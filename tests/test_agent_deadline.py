"""Worker-run expiry prevents new actions and cancels an active scientific process."""

import sys
import time
import json

import pytest

from autoengineering.agents.broker import WorkflowStopped
from autoengineering.agents.report import evidence_report
from test_agent_broker import create


def test_expired_run_never_starts_baseline_or_host(tmp_path):
    broker, _ = create(tmp_path, clock=lambda: time.time() - 301)
    with pytest.raises(WorkflowStopped, match="deadline"):
        broker.advance()
    assert not broker.controller.state().budget.attempts
    assert not broker.scheduler.host.calls
    assert not broker.store.replay().actions
    report = evidence_report(broker.store)
    assert report["deadline_notices"][0]["scientific_intent_id"]
    assert report["deadline_notices"][0]["failures"] == []
    assert report["worker_stop"] == "queued"


def test_active_scientific_process_stops_at_worker_deadline(tmp_path, monkeypatch):
    import autoengineering.campaign.controller as module
    from autoengineering.campaign.execution import live_members

    broker, _ = create(tmp_path, clock=lambda: time.time() - 299.5)
    original = module.supervise
    results = []

    def slow(command, **kwargs):
        # Trusted bounded fault fixture, using the real scientific supervisor,
        # reservation, cancellation polling and ownership verification.
        result = original((sys.executable, "-c", "import time;time.sleep(0.8)"), **kwargs)
        results.append(result)
        return result

    monkeypatch.setattr(module, "supervise", slow)
    with pytest.raises(WorkflowStopped, match="cancellation"):
        broker.advance()
    assert len(results) == 1
    assert results[0].stop_reason == "cancelled" and results[0].stopped
    assert not live_members(results[0].identity.pgid)
    assert broker.controller.state().outcome == "cancelled"
    assert len(broker.controller.state().budget.attempts) == 1
    assert not broker.scheduler.host.calls
    report = evidence_report(broker.store)
    assert report["deadline_notices"][0]["action_id"] in broker.store.replay().actions
    assert report["scientific_evidence"]["outcome"] == "cancelled"
    assert report["physical_work"]["attempts"] == 1
    assert report["campaign_outcome"] == "cancelled"


def test_expired_recovery_replays_original_committed_request_without_restart(tmp_path):
    broker, _ = create(tmp_path)
    original = broker.controller.service.handle
    envelopes = []
    responses = []

    def lose(request):
        envelopes.append(request.to_json())
        responses.append(original(request))
        raise RuntimeError("lost scientific acknowledgment")

    broker.controller.service.handle = lose
    with pytest.raises(RuntimeError, match="lost scientific"):
        broker.advance()
    assert len(broker.controller.state().budget.attempts) == 1
    broker.scheduler.clock = lambda: time.time() + 301

    def replay(request):
        assert not list((broker.controller.store.root / "control").glob("cancel-*.json"))
        envelopes.append(request.to_json())
        return original(request)

    broker.controller.service.handle = replay
    broker.reconcile_actions()
    action = next(iter(broker.store.replay().actions.values()))
    assert envelopes[0] == envelopes[1]
    assert action.response == responses[0]
    assert len(broker.controller.state().budget.attempts) == 1
    assert not broker.scheduler.host.calls
    assert evidence_report(broker.store)["deadline_notices"][0]["action_id"] == action.id


def test_expired_uncommitted_request_reconciles_without_scientific_execution(tmp_path):
    from autoengineering.agents.records import CampaignAction
    from autoengineering.campaign.records import Request

    broker, _ = create(tmp_path, clock=lambda: time.time() - 301)
    request = Request(
        "1.0",
        broker.controller.spec.name,
        "reserved-evaluation",
        0,
        "evaluate",
        {"candidate_id": "baseline", "mode": "fixed"},
    )
    with broker.store.writer():
        broker.store.commit(
            CampaignAction(
                "1.0",
                request.request_id,
                broker.store.spec.id,
                "request",
                "reserved",
                None,
                None,
                request,
                None,
                None,
            )
        )
    broker.reconcile_actions()
    action = broker.store.replay().actions[request.request_id]
    assert action.state == "completed" and action.request == request
    assert action.response.status == "ok"
    assert broker.controller.state().outcome == "cancelled"
    assert not broker.controller.state().budget.attempts
    assert not broker.controller.state().budget.reservations


@pytest.mark.parametrize("failed", ["worker", "scientific"])
def test_failed_forwarding_preserves_other_intent_and_requires_reconciliation(
    tmp_path, monkeypatch, failed
):
    from autoengineering.agents.deadline import ScientificDeadline
    from autoengineering.campaign.store import StoreError

    broker, _ = create(tmp_path, clock=lambda: time.time() - 301)

    def fail(*_):
        raise OSError("private failure details must not enter the notice")

    if failed == "worker":
        monkeypatch.setattr(broker.store, "request_cancel", fail)
    else:
        monkeypatch.setattr(broker.controller, "cancel", fail)
    guard = ScientificDeadline(
        broker.store, clock=time.time, cancel_science=broker.controller.cancel
    )
    with pytest.raises(StoreError, match="forwarding failed"):
        with guard:
            pytest.fail("failed cancellation cannot admit the external action")
    report = evidence_report(broker.store)
    assert report["status"] == "reconciliation_required"
    notice = report["deadline_notices"][0]
    assert notice["failures"] == [f"{failed}_cancel_failed"]
    surviving = "scientific_intent_id" if failed == "worker" else "worker_intent_id"
    assert notice[surviving] is not None
    assert "private failure" not in json.dumps(report)


def test_finished_action_disarms_timer_without_late_cancellation(tmp_path):
    from autoengineering.agents.deadline import ScientificDeadline

    broker, _ = create(tmp_path)
    expires = broker.store.replay().started_at + broker.store.spec.limits.elapsed_seconds
    guard = ScientificDeadline(
        broker.store, clock=lambda: expires - 0.02, cancel_science=broker.controller.cancel
    )
    with guard:
        pass
    time.sleep(0.04)
    assert not list((broker.store.root / "control").glob("*.json"))
    assert not guard.timer.is_alive()


@pytest.mark.parametrize("field", ["run_digest", "deadline_at", "action_id", "worker_intent_id"])
def test_changed_deadline_identity_or_missing_intent_fails_report(tmp_path, field):
    from autoengineering.campaign.store import StoreError

    broker, _ = create(tmp_path, clock=lambda: time.time() - 301)
    with pytest.raises(WorkflowStopped):
        broker.advance()
    path = next((broker.store.root / "control").glob("deadline-*.json"))
    record = json.loads(path.read_text())
    record[field] = {
        "run_digest": "f" * 64,
        "deadline_at": 1,
        "action_id": "absent-action",
        "worker_intent_id": "absent-intent",
    }[field]
    path.write_text(json.dumps(record))
    with pytest.raises((ValueError, StoreError, OSError)):
        evidence_report(broker.store)


def test_successful_forwarding_reconciles_but_preserves_failed_notice(tmp_path):
    from autoengineering.agents.deadline import ScientificDeadline
    from autoengineering.campaign.store import StoreError

    broker, _ = create(tmp_path, clock=lambda: time.time() - 301)

    def fail(*_):
        raise OSError("injected forwarding failure")

    with pytest.raises(StoreError, match="forwarding failed"):
        with ScientificDeadline(broker.store, clock=time.time, cancel_science=fail):
            pass
    before = evidence_report(broker.store)["deadline_notices"][0]
    with ScientificDeadline(broker.store, clock=time.time, cancel_science=broker.controller.cancel):
        pass
    report = evidence_report(broker.store)
    assert report["status"] == "cancel_queued"
    assert len(report["deadline_notices"]) == 2
    old = next(n for n in report["deadline_notices"] if n["id"] == before["id"])
    assert old["failures"] == before["failures"] and old["forwarding_resolved"]
    new = next(n for n in report["deadline_notices"] if n["id"] != before["id"])
    assert new["reconciles"] == [old["id"]]


def test_deadline_status_and_markdown_are_read_only_and_link_receipt(tmp_path):
    from click.testing import CliRunner
    from autoengineering.cli import cli

    broker, _ = create(tmp_path, clock=lambda: time.time() - 301)
    with pytest.raises(WorkflowStopped):
        broker.advance()
    before = {str(p): p.read_bytes() for p in broker.store.root.rglob("*") if p.is_file()}
    runner = CliRunner()
    status = runner.invoke(cli, ["agents", "status", str(broker.store.root)])
    assert status.exit_code == 0, status.output
    notice = json.loads(status.stdout)["deadline_notices"][0]
    assert (broker.store.root / notice["path"]).is_file()
    report = runner.invoke(
        cli, ["agents", "report", str(broker.store.root), "--format", "markdown"]
    )
    assert report.exit_code == 0, report.output
    assert f"]({notice['path']})" in report.stdout
    after = {str(p): p.read_bytes() for p in broker.store.root.rglob("*") if p.is_file()}
    assert after == before


def test_cli_reports_failed_forwarding_as_reconciliation_not_schema_error(tmp_path, monkeypatch):
    from click.testing import CliRunner
    from autoengineering.campaign.controller import CampaignController
    from autoengineering.cli import cli

    broker, _ = create(tmp_path, clock=lambda: time.time() - 301)

    def fail(*_):
        raise OSError("injected unavailable cancellation inbox")

    monkeypatch.setattr(CampaignController, "cancel", fail)
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "resume",
            str(broker.store.root),
            "--campaign",
            str(broker.controller.store.root),
        ],
    )
    assert result.exit_code == 4, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "reconciliation_required"
    assert "forwarding failed" in report["workflow_stop"]
    assert not broker.controller.state().budget.attempts


def test_expiry_during_fitting_preserves_child_ledger_and_prevents_more_starts(
    tmp_path, monkeypatch
):
    from pathlib import Path
    import threading
    import autoengineering.campaign.controller as module
    from autoengineering.campaign.execution import live_members
    from autoengineering.optimization import ObservationLedger
    from test_campaign_studies import calibrated_spec

    broker, _ = create(tmp_path, spec=calibrated_spec())
    offset = {"seconds": 0.0}
    broker.scheduler.clock = lambda: time.time() + offset["seconds"]
    deadline = broker._deadline
    active = {}

    def capture(action=None):
        guard = deadline(action)
        if action is not None:
            record = broker.store.replay().actions[action]
            if record.request and record.request.payload.get("mode") == "calibrate":
                active["guard"] = guard
        return guard

    monkeypatch.setattr(broker, "_deadline", capture)
    original = module.supervise
    results = []
    failures = []

    def slow_fitting(command, **kwargs):
        job = json.loads(Path(command[-1]).read_text())
        if job["role"] != "fitting":
            return original(command, **kwargs)

        def expire_after_launch():
            try:
                ownership = kwargs["root"] / "attempts" / kwargs["attempt_id"] / "process.json"
                until = time.monotonic() + 5
                while not ownership.exists() and time.monotonic() < until:
                    time.sleep(0.01)
                assert ownership.exists()
                guard = active["guard"]
                offset["seconds"] = guard.deadline - time.time() + 0.01
                # Inject clock expiry only after the real scientific launch.
                # The fixed-evaluation test separately exercises Timer firing.
                guard.expire()
            except BaseException as error:
                failures.append(error)

        timer = threading.Thread(target=expire_after_launch)
        timer.start()
        try:
            result = original((sys.executable, "-c", "import time;time.sleep(.8)"), **kwargs)
            results.append(result)
            return result
        finally:
            timer.join(timeout=6)
            assert not timer.is_alive()

    monkeypatch.setattr(module, "supervise", slow_fitting)
    with pytest.raises(WorkflowStopped, match="cancellation"):
        broker.advance()
    assert not failures and len(results) == 1
    assert results[0].stop_reason == "cancelled" and results[0].stopped
    assert not live_members(results[0].identity.pgid)
    state = broker.controller.state()
    assert state.outcome == "cancelled" and len(state.budget.attempts) == 3
    assert state.budget.unresolved_attempts == 0
    fitting = [e for e in state.evaluations if e.split_id == "fitting"]
    assert len(fitting) == 1 and fitting[0].status == "infrastructure_failure"
    link = state.studies[0]
    rows = ObservationLedger(
        broker.controller.store.root / link.work_path / "observations.jsonl"
    ).entries()
    assert len(rows) == 1
    assert rows[0][1].status.value == "infrastructure_failure"
    attempts = len(state.budget.attempts)
    with pytest.raises(WorkflowStopped, match="cancellation"):
        broker.advance()
    assert len(broker.controller.state().budget.attempts) == attempts
