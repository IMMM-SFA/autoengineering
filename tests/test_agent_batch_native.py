"""Batch/native journal gaps with authored executable, profile and upstream.

These fixtures provide no actual native qualification or provider conformance.
"""

from dataclasses import replace
import shutil

import pytest

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.batch import PhysicalReservation
from autoengineering.agents.hosts.base import HostResult, InvocationContext
from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.store import StoreError
from test_agent_brokered_host import worker

H = "0" * 64


def fixture(tmp_path, monkeypatch):
    original, task, output, calls = worker(tmp_path, monkeypatch)
    spec = original.store.spec
    qualification = tmp_path / "qualification"
    qualification.mkdir(mode=0o700)
    config = HostConfiguration(
        qualification, H, original.host.credential_path, original.host.lease_id
    )
    base = config.build(spec)
    batch_spec = BatchSpec(
        "1.0",
        "native-batch",
        spec.source_identity,
        spec.environment_identity,
        spec.host,
        base.capabilities(),
        config.digest,
        spec.limits,
        0,
        (BatchCase("native", "text", H, 2, 0),),
    )
    batch = BatchStore.create(tmp_path / "batch", batch_spec, clock=lambda: 100)
    batch.start_case("native", H)
    case = batch.root / "cases/native"
    case.mkdir(mode=0o700)
    store = WorkerStore.create(case / "worker", spec, clock=lambda: 100)
    shutil.copytree(original.store.root / "artifacts", store.root / "artifacts", dirs_exist_ok=True)
    host = BatchCodexHost(config, batch, "native")
    monkeypatch.setattr(host, "_upstream", original.host._upstream)
    monkeypatch.setattr(host, "_wrap", original.host._wrap)
    return SerialScheduler(store, host, clock=lambda: 100), batch, config, task, output, calls


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_scheduler_charges_batch_before_native_and_replay_never_relaunches(tmp_path, monkeypatch):
    scheduler, batch, _, task, output, calls = fixture(tmp_path, monkeypatch)
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "completed" and scheduler.handoff(result) == output and len(calls) == 1
    report = batch.report()
    assert report["host_reservations_charged"] == 1 and not report["pending_reservations"]
    assert report["host_invocations_with_unknown_usage"] == 0
    assert report["request_intents_present"] == 0  # Authored callback, no subscription command.
    physical = snapshot(scheduler.store.root / "processes")
    assert scheduler.dispatch(task, campaign_revision=3) == result and len(calls) == 1
    assert snapshot(scheduler.store.root / "processes") == physical
    assert ":batch:" in result.capabilities.executable_version


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_native_result_recovers_across_batch_observation_commit_fault(tmp_path, monkeypatch, stage):
    scheduler, batch, _, task, output, calls = fixture(tmp_path, monkeypatch)

    def fault(point):
        projection = batch.replay()
        if point == stage and projection.reservations:
            # The reservation commit's after-ack fault is covered by the counter
            # tests. Here interrupt only observation, after native work finished.
            physical = scheduler.store.root / "processes"
            if any(physical.rglob("completion.json")):
                raise RuntimeError("authored batch observation acknowledgment loss")

    batch.fault = fault
    pending = scheduler.dispatch(task, campaign_revision=3)
    assert pending.state == "reconciliation_required" and len(calls) == 1
    before = snapshot(scheduler.store.root / "processes")
    batch.fault = lambda _: None
    recovered = scheduler.recover_invocation(pending.id, campaign_revision=3)
    assert recovered.state == "completed" and scheduler.handoff(recovered) == output
    assert len(calls) == 1 and snapshot(scheduler.store.root / "processes") == before
    assert batch.report()["host_reservations_charged"] == 1 and not batch.replay().pending
    assert scheduler.recover_invocation(pending.id, campaign_revision=3) == recovered


def test_batch_configuration_or_scope_cannot_change_before_first_call(tmp_path, monkeypatch):
    scheduler, batch, config, task, _, calls = fixture(tmp_path, monkeypatch)
    with pytest.raises(StoreError, match="configuration differs"):
        BatchCodexHost(replace(config, lease_id="changed"), batch, "native")
    scheduler.host.case_id = "unlisted"
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "reconciliation_required"
    assert not calls and not batch.replay().reservations


def test_abandoned_result_without_reconstructed_bytes_keeps_transcript_ceiling(
    tmp_path, monkeypatch
):
    scheduler, batch, _, _, _, _ = fixture(tmp_path, monkeypatch)
    reservation = PhysicalReservation(
        "abandoned-call", "native", "host", "1" * 64, "unknown-task", 100, 20, 10, 100, 100
    )
    batch.reserve(reservation)
    context = InvocationContext(
        "abandoned-call",
        "unit-nonce",
        scheduler.store.root / "processes/abandoned-call",
        20,
        100,
        lambda _: None,
        lambda: False,
    )
    result = HostResult("host_failure", "", None, {}, None, b"", b"", True)
    observation = scheduler.host._observation(reservation, result, context)
    assert observation.transcript_bytes is None and observation.elapsed_seconds is None
    batch.observe(observation)
    assert batch.report()["transcript_bytes_charged"] == reservation.transcript_ceiling


def test_locally_stopped_but_unreconciled_response_keeps_pending_charge(tmp_path, monkeypatch):
    scheduler, batch, _, _, _, _ = fixture(tmp_path, monkeypatch)
    reservation = PhysicalReservation(
        "pending-call",
        "native",
        "host",
        "1" * 64,
        "pending-task",
        100,
        20,
        10,
        100,
        100,
    )
    batch.reserve(reservation)
    context = InvocationContext(
        "pending-call",
        "unit-nonce",
        scheduler.store.root / "processes/pending-call",
        20,
        100,
        lambda _: None,
        lambda: False,
    )
    result = HostResult("reconciliation_required", "", None, {}, 1.2, b"partial", b"", True)
    observation = scheduler.host._observation(reservation, result, context)
    assert observation.status == "reconciliation_required" and not observation.stop_verified
    assert observation.transcript_bytes is None
    batch.observe(observation)
    assert batch.replay().pending == (reservation,)
    assert batch.report()["transcript_bytes_charged"] == reservation.transcript_ceiling
