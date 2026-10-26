"""Physical attempt ceilings, active cancellation and descendant lifecycle tests."""

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from autoengineering.campaign.budget import BudgetAccount, BudgetExhausted
from autoengineering.campaign.execution import (
    ProcessIdentity,
    cancellation_intent,
    identity_matches,
    live_members,
    supervise,
)
from autoengineering.campaign.records import AttemptRecord
from autoengineering.campaign.spec import ExecutionSpec
from autoengineering.campaign.store import EventStore


def attempt(name="attempt-1", reservation="reservation-1"):
    return AttemptRecord(
        name, reservation, "launched", None, f"nonce-{name}", None, None, True, None
    )


def test_full_reservations_count_attempts_once_and_release_only_when_reconciled():
    account = BudgetAccount(3, 100, 10).reserve("reservation-1", 2)
    assert account.committed_capacity == 2
    with pytest.raises(BudgetExhausted):
        account.reserve("too-much", 2)
    account = account.start(attempt())
    assert account.unresolved_attempts == 1
    assert account.charged_seconds == 10
    with pytest.raises(BudgetExhausted, match="reconciliation"):
        account.start(attempt("attempt-2"))
    with pytest.raises(ValueError, match="uncertain"):
        account.release("reservation-1")
    finished = replace(
        attempt(), state="finished", measured_cost=1.0, elapsed_seconds=0.2, uncertain_cost=False
    )
    account = account.resolve(finished)
    assert account.resolve(finished) == account
    assert account.measured_cost == 1  # Reservation is capacity, never added to measured cost.
    account = account.start(attempt("attempt-2"))
    uncertain = replace(attempt("attempt-2"), state="uncertain", measured_cost=None)
    account = account.resolve(uncertain)
    assert account.cost_is_uncertain
    assert account.confirmed_attempts == account.unresolved_attempts == 1
    # Existing child recovery's zero cost does not erase the campaign uncertainty.
    assert account.charged_seconds == 10.2
    reconciled = replace(uncertain, state="reconciled", elapsed_seconds=1.0)
    account = account.resolve(reconciled).release("reservation-1")
    assert account.cost_is_uncertain
    assert account.committed_capacity == 2
    assert BudgetAccount.from_json(account.to_json()) == account
    with pytest.raises(ValueError, match="rewrite"):
        account.resolve(replace(finished, measured_cost=0.0))


def test_no_extra_start_or_invocation_expansion():
    account = BudgetAccount(1, 100, 10)
    with pytest.raises(BudgetExhausted, match="invocation"):
        account.reserve("reservation-1", 1, invocation_remaining=0)
    account = account.reserve("reservation-1", 1).start(attempt())
    account = account.resolve(
        replace(
            attempt(),
            state="finished",
            measured_cost=0.0,
            elapsed_seconds=1.0,
            uncertain_cost=False,
        )
    )
    with pytest.raises(ValueError, match="exceed"):
        account.start(attempt("attempt-2"))
    with pytest.raises(BudgetExhausted):
        BudgetAccount(10, 15, 10).reserve("reservation-1", 2)


def settings(timeout=3.0):
    return ExecutionSpec(
        ("test",), timeout_seconds=timeout, termination_grace_seconds=0.2, kill_wait_seconds=1.0
    )


def run(tmp_path, code, *, timeout=3.0):
    store = EventStore.create(tmp_path / "campaign")
    result = supervise(
        (sys.executable, "-c", code),
        root=store.root,
        attempt_id="attempt-1",
        campaign_id="test",
        settings=settings(timeout),
        cwd=Path.cwd(),
    )
    return store, result


def test_supervised_success_and_failure_have_durable_receipts(tmp_path):
    store, result = run(tmp_path, "print('completed')")
    assert result.status == "success"
    assert result.receipt_valid and result.stopped
    assert not live_members(result.identity.pgid)
    folder = store.root / "attempts/attempt-1"
    assert "completed" in (folder / "stdout.log").read_text()
    assert json.loads((folder / "process.json").read_text())["nonce"] == result.identity.nonce
    other = tmp_path / "other"
    other.mkdir()
    _, failed = run(other, "raise ValueError('model failure')")
    assert failed.status == "model_failure"
    assert failed.receipt_valid


def test_timeout_terminates_descendant_group(tmp_path):
    # The model starts a descendant that ignores TERM, requiring group KILL.
    code = (
        "import subprocess,sys,time; "
        "subprocess.Popen([sys.executable,'-c', "
        "'import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(30)']); "
        "time.sleep(30)"
    )
    _, result = run(tmp_path, code, timeout=1.0)
    assert result.status == "timeout"
    assert result.stop_reason == "timeout"
    assert result.stopped
    assert not live_members(result.identity.pgid)


def test_cancel_does_not_wait_for_campaign_lock_and_stops_running_work(tmp_path):
    store = EventStore.create(tmp_path / "campaign")
    sent = []

    def cancel_after_launch():
        deadline = time.monotonic() + 5
        while not (store.root / "attempts/attempt-1/action-start.json").exists():
            if time.monotonic() > deadline:
                return
            time.sleep(0.02)
        sent.append(cancellation_intent(store.root, "stop-1", campaign_id="test"))

    thread = threading.Thread(target=cancel_after_launch)
    thread.start()
    with store.writer():
        result = supervise(
            (sys.executable, "-c", "import time; time.sleep(30)"),
            root=store.root,
            attempt_id="attempt-1",
            campaign_id="test",
            settings=settings(5),
            cwd=Path.cwd(),
        )
    thread.join(timeout=5)
    assert sent
    assert result.stop_reason == "cancelled"
    assert result.stopped
    assert not live_members(result.identity.pgid)
    # Cancel retries do not create a second intent.
    cancellation_intent(store.root, "stop-1", campaign_id="test")
    assert len(list((store.root / "control").glob("cancel-*.json"))) == 1
    with pytest.raises(ValueError, match="pending"):
        supervise(
            (sys.executable, "-c", "print('must not run')"),
            root=store.root,
            attempt_id="attempt-2",
            campaign_id="test",
            settings=settings(),
            cwd=Path.cwd(),
        )


def test_reused_pid_does_not_match_launch_nonce():
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"], start_new_session=True
    )
    try:
        identity = ProcessIdentity(process.pid, process.pid, "unrelated-nonce", "unknown")
        assert not identity_matches(identity)
        assert process.poll() is None
    finally:
        os.killpg(process.pid, 15)
        process.wait(timeout=2)


def test_failed_stop_is_reported_and_recovery_never_signals_wrong_nonce(tmp_path, monkeypatch):
    import autoengineering.campaign.execution as execution

    monkeypatch.setattr(execution, "_terminate_owned", lambda *args: False)
    _, result = run(tmp_path, "import time; time.sleep(30)", timeout=1.0)
    try:
        assert result.status == "infrastructure_failure"
        assert not result.stopped
        assert result.stop_reason == "timeout"
        assert live_members(result.identity.pgid)
        fake = replace(result.identity, nonce="different-generation")
        assert not execution.stop_recovered(fake, settings())
        assert live_members(result.identity.pgid)
    finally:
        assert execution.stop_recovered(result.identity, settings())
    assert not live_members(result.identity.pgid)
