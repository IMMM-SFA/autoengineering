"""Original watchdog startup reconciliation on authored daemon observations."""

import pytest

from autoengineering.utility import guest_watchdog as module
import test_utility_guest_watchdog as fixture

metadata = fixture.metadata


def test_original_plan_without_ready_can_be_cleaned_without_new_worker(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, daemon, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)
    before = store.replay()
    with store.writer(), owner.writer():
        outcome = module.reconcile_startup_cleanup(owner, store, api)
    assert outcome.result == "absent" and outcome.reason == "startup_refused"
    assert not outcome.kill_intended and outcome.delete_intended
    assert owner.replay().phase == "created" and store.replay() == before
    assert not (root / "ready.json").exists()
    assert not daemon.exists
    assert module.read_outcome(root, owner, plan) == outcome


def reconcile(owner, store, api):
    with store.writer(), owner.writer():
        return module.reconcile_startup_cleanup(owner, store, api)


def test_original_writers_and_live_cleanup_lease_are_required(tmp_path, metadata, monkeypatch):
    owner, store, api, daemon, root, _ = fixture.prepared(tmp_path, metadata, monkeypatch)
    calls = tuple(daemon.calls)
    with pytest.raises(ValueError, match="writers"):
        module.reconcile_startup_cleanup(owner, store, api)
    with module._cleanup_writer(root), pytest.raises(ValueError, match="lease is held"):
        reconcile(owner, store, api)
    assert tuple(daemon.calls) == calls and not (root / "cleanup-window.json").exists()


@pytest.mark.parametrize(
    "point",
    [
        "before_watchdog_cleanup_kill",
        "after_watchdog_cleanup_kill",
        "before_watchdog_cleanup_delete",
        "after_watchdog_cleanup_delete",
    ],
)
def test_interrupted_cleanup_keeps_original_window_reason_and_consumed_mutations(
    tmp_path, metadata, monkeypatch, point
):
    owner, store, api, daemon, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)
    fixture.running(daemon)

    def fail(stage):
        if stage == point:
            raise KeyboardInterrupt("authored original cleanup loss")

    owner.fault = fail
    with pytest.raises(KeyboardInterrupt):
        module.cleanup(owner, api, plan, root, "owner_lost")
    window = (root / "cleanup-window.json").read_bytes()
    owner.fault = lambda stage: None
    outcome = reconcile(owner, store, api)
    assert outcome.reason == "owner_lost"  # Reconciliation cannot relabel the original cause.
    assert (root / "cleanup-window.json").read_bytes() == window
    assert sum(method == "POST" and "/kill?" in path for method, path, _ in daemon.calls) <= 1
    assert sum(method == "DELETE" for method, _, _ in daemon.calls) <= 1
    if point == "before_watchdog_cleanup_delete":
        assert outcome.result == "unverified" and daemon.exists
    else:
        assert outcome.result == "absent"
    calls = tuple(daemon.calls)
    assert reconcile(owner, store, api) == outcome and tuple(daemon.calls) == calls
    assert module.read_outcome(root, owner, plan) == outcome
    with owner.writer(), pytest.raises(ValueError, match="start authority refused"):
        owner.record("start_intent")


def test_expired_original_cleanup_cannot_obtain_a_new_window(tmp_path, metadata, monkeypatch):
    owner, store, api, daemon, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)

    def fail(stage):
        if stage == "watchdog_cleanup_intended":
            raise KeyboardInterrupt("authored before cleanup API")

    owner.fault = fail
    with pytest.raises(KeyboardInterrupt):
        reconcile(owner, store, api)
    window = module.GuestWatchdogCleanupWindow.from_json((root / "cleanup-window.json").read_text())
    calls = tuple(daemon.calls)
    owner.fault = lambda stage: None
    monkeypatch.setattr(module.time, "monotonic", lambda: window.deadline)
    outcome = reconcile(owner, store, api)
    assert outcome.result == "unverified" and not outcome.absence
    assert tuple(daemon.calls) == calls and daemon.exists
    assert outcome.cleanup_window_digest == window.digest
    assert module.read_outcome(root, owner, plan) == outcome


def test_completed_startup_cleanup_replays_without_runtime_or_clock(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, daemon, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)
    outcome = reconcile(owner, store, api)

    def forbidden(*args, **kwargs):
        raise AssertionError("original replay must not execute or probe runtime")

    monkeypatch.setattr(module.time, "monotonic", forbidden)
    monkeypatch.setattr(module, "GuestDaemonAPI", forbidden)
    assert reconcile(owner, store, None) == outcome
    owner_read, owner_write = module.os.pipe()
    ready_read, ready_write = module.os.pipe()
    try:
        # A delayed original child sees the result before publishing readiness.
        assert module.watch(root, owner_read, ready_write) == outcome
        assert not (root / "ready.json").exists()
        assert module.os.read(ready_read, 1) == b""
    finally:
        for fd in (owner_read, owner_write, ready_read):
            module.os.close(fd)
    assert module.read_outcome(root, owner, plan) == outcome


def test_changed_window_is_rejected_by_saved_outcome(tmp_path, metadata, monkeypatch):
    from dataclasses import replace

    owner, store, api, _, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)
    reconcile(owner, store, api)
    path = root / "cleanup-window.json"
    original = module.GuestWatchdogCleanupWindow.from_json(path.read_text())
    path.write_text(replace(original, deadline=original.deadline - 0.5).to_json())
    with pytest.raises(ValueError, match="original window"):
        module.read_outcome(root, owner, plan)


def test_cancelled_suite_retains_original_startup_cleanup_authority(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, daemon, _, _ = fixture.prepared(tmp_path, metadata, monkeypatch)
    grant = owner.manifest.job.grant
    with store.writer():
        store.append(
            request_id="authored-cancel",
            operation="cancel",
            cell_digest=grant.cell_digest,
            attempt_id="cancel-startup",
            child_digest=grant.digest,
            phase="confirmation",
        )
    daemon.created["HostConfig"]["Memory"] = 0
    fixture.running(daemon)
    assert reconcile(owner, store, api).result == "absent"
    assert store.replay()["cancelled"]


def test_actual_live_watchdog_refuses_parent_cleanup_takeover(tmp_path, metadata):
    import time

    with fixture.native_peer() as (endpoint, peer):
        owner, store, api = fixture.native_prepared(tmp_path, metadata, endpoint, peer)
        with store.writer(), owner.writer():
            handle = module.arm(owner, store, api, deadline=time.monotonic() + 8)
        try:
            calls = tuple(peer["calls"])
            with pytest.raises(ValueError, match="lease is held"):
                reconcile(owner, store, api)
            assert tuple(peer["calls"]) == calls
            handle.cancel()
            outcome = handle.outcome()
            assert outcome.result == "absent" and outcome.reason == "cancelled"
            calls = tuple(peer["calls"])
            assert reconcile(owner, store, None) == outcome
            assert tuple(peer["calls"]) == calls
        finally:
            handle.close_owner()
            handle.process.wait(timeout=15)


def test_native_facade_cleans_failed_watchdog_startup_without_start(tmp_path, metadata):
    from autoengineering.utility.guest_owner import GuestOwnerJournal
    import test_utility_guest_executor as facade

    with facade.prepared(tmp_path, metadata) as (executor, grant, peer, configure):
        before = executor.store.replay()

        def fail(stage):
            configure(stage)
            if stage == "watchdog_intended":
                raise RuntimeError("authored startup interruption")

        executor.store.fault = fail
        with pytest.raises(RuntimeError, match="startup interruption"):
            facade.execute(executor, grant)
        owner = GuestOwnerJournal(executor.work_root / grant.digest, suite_root=executor.store.root)
        root = owner.root / "control/guest-watchdog"
        plan = module.GuestWatchdogPlan.from_json((root / "plan.json").read_text())
        outcome = module.read_outcome(root, owner, plan)
        assert outcome.result == "absent" and outcome.reason == "startup_refused"
        assert peer.daemon.creates == 1 and peer.starts == peer.inputs == 0
        assert executor.store.replay() == before
        calls = tuple(peer.calls)
        executor.store.fault = lambda stage: None
        with executor.store.writer():
            assert executor.cleanup_watchdog_startup(grant) == outcome
        assert tuple(peer.calls) == calls
        with executor.store.writer(), pytest.raises(ValueError):
            executor.recover(grant)
        assert tuple(peer.calls) == calls


def test_delayed_child_resumes_original_cleanup_without_publishing_readiness(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, _, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)

    def fail(stage):
        if stage == "watchdog_cleanup_intended":
            raise KeyboardInterrupt("authored cleanup owner loss")

    owner.fault = fail
    with pytest.raises(KeyboardInterrupt):
        reconcile(owner, store, api)
    monkeypatch.setattr(module, "GuestDaemonAPI", lambda *args, **kwargs: api)
    owner_read, owner_write = module.os.pipe()
    ready_read, ready_write = module.os.pipe()
    module.os.close(owner_write)
    try:
        outcome = module.watch(root, owner_read, ready_write)
        assert outcome.reason == "startup_refused" and outcome.result == "absent"
        assert not (root / "ready.json").exists()
        assert module.os.read(ready_read, 1) == b""
        assert module.read_outcome(root, owner, plan) == outcome
    finally:
        module.os.close(owner_read)
        module.os.close(ready_read)


def test_legacy_interruption_without_window_refuses_new_cleanup_allowance(
    tmp_path, metadata, monkeypatch
):
    from autoengineering.campaign.serialization import canonical_json

    owner, store, api, daemon, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)
    value = {"plan_digest": plan.digest, "container_id": plan.container_id, "reason": "owner_lost"}
    (root / "kill-intent.json").write_text(canonical_json(value))
    calls = tuple(daemon.calls)
    with pytest.raises(ValueError, match="original window"):
        reconcile(owner, store, api)
    assert tuple(daemon.calls) == calls
    assert not (root / "cleanup-window.json").exists()


def test_original_plan_with_no_remaining_window_does_not_contact_runtime(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, daemon, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)
    monkeypatch.setattr(module.time, "monotonic", lambda: plan.deadline + module.CLEANUP_SECONDS)
    calls = tuple(daemon.calls)
    outcome = reconcile(owner, store, api)
    assert outcome.result == "unverified" and not outcome.absence
    assert tuple(daemon.calls) == calls
    assert not (root / "cleanup-window.json").exists()
    assert module.read_outcome(root, owner, plan) == outcome


def test_cleanup_window_cannot_be_removed_from_saved_outcome(tmp_path, metadata, monkeypatch):
    owner, store, api, _, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)
    outcome = reconcile(owner, store, api)
    assert outcome.cleanup_window_digest
    (root / "cleanup-window.json").unlink()
    with pytest.raises(ValueError, match="window is missing"):
        module.read_outcome(root, owner, plan)


def test_copied_control_directory_cannot_obtain_fresh_cleanup_scope(
    tmp_path, metadata, monkeypatch
):
    import shutil

    owner, _, api, daemon, root, plan = fixture.prepared(tmp_path, metadata, monkeypatch)
    copied = tmp_path / "copied-control"
    shutil.copytree(root, copied)
    calls = tuple(daemon.calls)
    with pytest.raises(ValueError, match="original control scope"):
        module.cleanup(owner, api, plan, copied, "owner_lost")
    assert tuple(daemon.calls) == calls
    assert not (copied / ".cleanup.lock").exists()


def test_killed_original_watchdog_child_can_be_cleaned_without_replacement(tmp_path, metadata):
    import time

    with fixture.native_peer() as (endpoint, peer):
        owner, store, api = fixture.native_prepared(tmp_path, metadata, endpoint, peer)
        with store.writer(), owner.writer():
            handle = module.arm(owner, store, api, deadline=time.monotonic() + 8)
        try:
            handle.process.kill()  # Only the exact fixture child returned by Popen.
            assert handle.process.wait(timeout=5) < 0
            handle.close_owner()
            assert not (handle.root / "outcome.json").exists()
            outcome = reconcile(owner, store, api)
            assert outcome.result == "absent" and outcome.reason == "startup_refused"
            assert outcome.stopped and not outcome.kill_intended and outcome.delete_intended
            assert peer["daemon"].creates == 1
            assert not any("/start" in path for _, path in peer["calls"])
            assert (
                peer["calls"].count(("DELETE", f"/containers/{fixture.fixture.H}?force=1&v=0")) == 1
            )
        finally:
            handle.close_owner()
            if handle.process.poll() is None:
                handle.process.kill()
            handle.process.wait(timeout=5)


def test_facade_cleans_original_creation_when_watchdog_popen_fails(tmp_path, metadata, monkeypatch):
    from autoengineering.utility.guest_owner import GuestOwnerJournal
    import test_utility_guest_executor as facade

    with facade.prepared(tmp_path, metadata) as (executor, grant, peer, configure):
        before = executor.store.replay()
        original = module.subprocess.Popen
        refused = []

        def fail_child(args, *positional, **kwargs):
            if "autoengineering.utility.guest_watchdog" in args:
                refused.append(tuple(args))
                raise OSError("authored watchdog Popen failure")
            return original(args, *positional, **kwargs)

        monkeypatch.setattr(module.subprocess, "Popen", fail_child)
        with pytest.raises(OSError, match="authored watchdog Popen failure"):
            facade.execute(executor, grant)
        owner = GuestOwnerJournal(executor.work_root / grant.digest, suite_root=executor.store.root)
        root = owner.root / "control/guest-watchdog"
        plan = module.GuestWatchdogPlan.from_json((root / "plan.json").read_text())
        outcome = module.read_outcome(root, owner, plan)
        assert outcome.result == "absent" and outcome.reason == "startup_refused"
        assert len(refused) == 1 and not (root / "ready.json").exists()
        assert peer.daemon.creates == 1 and peer.starts == peer.inputs == 0
        assert executor.store.replay() == before
