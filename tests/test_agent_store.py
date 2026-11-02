"""Worker evidence survives lost acknowledgments without repeating physical calls."""

from dataclasses import replace

import pytest

from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.records import WorkerInvocation
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.store import StoreError, WriterBusy
from test_agent_contracts import H, run_spec, task_assignment


def reservation(store, *, id="invocation-1", attempt=0, task_id="investigate"):
    prompt = store.put_private(b"bounded brief", name="prompt.txt", media_type="text/plain")
    return WorkerInvocation(
        "1.0",
        id,
        store.spec.id,
        task_id,
        attempt,
        "reserved",
        prompt,
        FakeHost(()).capabilities(),
        "scripted",
        None,
        H,
        f"nonce-{id}",
        None,
        None,
        None,
        None,
        0,
        None,
        {"tokens": None},
    )


def initialized(tmp_path, **kwargs):
    store = WorkerStore.create(tmp_path / "worker", run_spec(), clock=lambda: 0, **kwargs)
    with store.writer():
        store.commit(task_assignment())
    return store


def test_reservation_is_durable_and_unknown_usage_survives_restart(tmp_path):
    store = initialized(tmp_path)
    with store.writer():
        invocation = store.commit(reservation(store))
    restarted = WorkerStore(store.root)
    assert restarted.replay().pending == (invocation,)
    assert restarted.replay().pending[0].usage["tokens"] is None
    with restarted.writer():
        assert restarted.mark_unresolved() == (invocation.id,)
        with pytest.raises(StoreError, match="reconciliation"):
            restarted.commit(reservation(restarted, id="invocation-2", attempt=1))
    assert restarted.replay().pending[0].state == "reconciliation_required"


def test_operation_lease_is_independent_and_released_after_process_death(tmp_path):
    import os
    from pathlib import Path
    import select
    import subprocess
    import sys
    import autoengineering

    store = initialized(tmp_path)
    source = """import sys,time
from pathlib import Path
from autoengineering.agents.store import WorkerStore
with WorkerStore(Path(sys.argv[1])).operation():
 print('leased',flush=True)
 time.sleep(60)
"""
    environment = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(Path(autoengineering.__file__).parent.parent),
    }
    process = subprocess.Popen(
        [sys.executable, "-c", source, str(store.root)],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        ready, _, _ = select.select([process.stdout], [], [], 5)
        assert ready and process.stdout.readline() == b"leased\n"
        assert process.poll() is None
        with pytest.raises(WriterBusy, match="operation"), store.operation():
            pass
        with store.writer():
            assert len(store.replay().tasks) == 1
        # A second descriptor on the same object must also be excluded.
        process.kill()
        process.wait(timeout=5)
        assert os.path.isfile(store.root / ".operation.lock")
        with store.operation():
            with pytest.raises(WriterBusy, match="operation"), store.operation():
                pass
            with store.writer():
                assert len(store.replay().tasks) == 1
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        process.stdout.close()
        process.stderr.close()


def test_operation_lease_rejects_symlink_without_changing_target(tmp_path):
    store = initialized(tmp_path)
    target = tmp_path / "private"
    target.write_bytes(b"preserve")
    (store.root / ".operation.lock").symlink_to(target)
    with pytest.raises(OSError), store.operation():
        pass
    assert target.read_bytes() == b"preserve"


@pytest.mark.parametrize(
    "boundary,committed", [("before_event_commit", False), ("after_event_commit", True)]
)
def test_commit_fault_replays_authoritative_evidence(tmp_path, boundary, committed):
    store = initialized(tmp_path)

    def fail(stage):
        if stage == boundary:
            raise RuntimeError("power loss")

    store.fault = fail
    with store.writer():
        invocation = reservation(store)
        with pytest.raises(RuntimeError, match="power loss"):
            store.commit(invocation)
    restarted = WorkerStore(store.root)
    assert (invocation.id in restarted.replay().invocations) is committed
    if committed:
        with restarted.writer(), pytest.raises(StoreError, match="immutable|transition"):
            restarted.commit(invocation)


def test_repairs_and_invocation_ceilings_do_not_reset(tmp_path):
    store = initialized(tmp_path)
    for attempt in range(3):
        store = WorkerStore(store.root)
        with store.writer():
            value = store.commit(reservation(store, id=f"call-{attempt}", attempt=attempt))
            store.commit(replace(value, state="invalid_output"))
    assert store.replay().repairs_used == 2
    with store.writer(), pytest.raises(StoreError, match="repair allowance"):
        store.commit(reservation(store, id="call-3", attempt=3))
    spec = replace(run_spec(), limits=replace(run_spec().limits, max_invocations=1))
    other = WorkerStore.create(tmp_path / "limited", spec, clock=lambda: 0)
    with other.writer():
        other.commit(task_assignment())
        value = other.commit(reservation(other))
        other.commit(replace(value, state="host_failure"))
        with pytest.raises(StoreError, match="invocation limit"):
            other.commit(reservation(other, id="second", attempt=1))


def test_completed_task_and_evidence_are_immutable(tmp_path):
    store = initialized(tmp_path)
    with store.writer():
        value = store.commit(reservation(store))
        raw = store.put_private(b'{"raw":"output"}', name="raw.json", media_type="application/json")
        normalized = store.put_private(
            b'{"normalized":true}', name="normalized.json", media_type="application/json"
        )
        receipt = store.put_private(
            b'{"stopped":true}', name="receipt.json", media_type="application/json"
        )
        value = store.commit(
            replace(
                value,
                state="completed",
                raw_response=raw,
                normalized_output=normalized,
                completion_receipt=receipt,
                elapsed_seconds=1,
            )
        )
        with pytest.raises(StoreError, match="immutable"):
            store.commit(replace(value, resolved_model="invented"))
        with pytest.raises(StoreError, match="completed task"):
            store.commit(reservation(store, id="again", attempt=1))
    (store.root / raw.path).write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="mismatch"):
        WorkerStore(store.root).replay()


def test_manifest_identity_limits_and_task_allowance(tmp_path):
    store = initialized(tmp_path)
    for changed in (
        replace(run_spec(), host=replace(run_spec().host, requested_model="other")),
        replace(run_spec(), limits=replace(run_spec().limits, max_invocations=100)),
        replace(run_spec(), role_templates={**run_spec().role_templates, "reviewer": "b" * 64}),
    ):
        with pytest.raises(StoreError, match="identity mismatch"):
            store.require_identity(changed)
    with store.writer():
        with pytest.raises(StoreError, match="duplicate task"):
            store.commit(task_assignment())
        with pytest.raises(StoreError, match="parent"):
            store.commit(replace(task_assignment(), id="new", parent_task="absent"))
        invocation = reservation(store)
        with pytest.raises(StoreError, match="policy/model"):
            store.commit(replace(invocation, requested_model="other"))
    store.spec.to_dict()  # An external caller can edit a copy, never retained state.
    (store.root / "run.json").write_text(replace(run_spec(), campaign_id="other").to_json())
    with pytest.raises(StoreError, match="manifest changed"):
        store.replay()


def test_independent_cancel_inbox_and_single_writer(tmp_path):
    store = initialized(tmp_path)
    other = WorkerStore(store.root)
    with store.writer():
        with pytest.raises(WriterBusy), other.writer():
            pass
        nonce = other.request_cancel()
        assert (store.root / "control" / f"cancel-{nonce}.json").is_file()
    assert not store.replay().invocations


def test_corrupt_event_and_unsafe_directory_rejected(tmp_path):
    store = initialized(tmp_path)
    event = store.events_path / "000000000001.json"
    event.write_text(event.read_text().replace("bounded", "tampered") + " ")
    with pytest.raises(StoreError, match="checksum/canonical"):
        store.replay()
    symlink = tmp_path / "alias"
    symlink.symlink_to(store.root, target_is_directory=True)
    with pytest.raises(StoreError, match="symlink"):
        WorkerStore(symlink)


def test_invocation_1_0_serialization_remains_stable_and_version_cannot_change(tmp_path):
    from autoengineering.agents.records import WorkerInvocation
    from autoengineering.campaign.serialization import unique_json

    store = initialized(tmp_path)
    with store.writer():
        value = store.commit(reservation(store))
    historical = value.to_json()
    assert "final_response" not in historical and "stderr_response" not in historical
    assert WorkerInvocation.from_json(historical).to_json() == historical
    extended = replace(value, schema_version="1.1")
    assert "final_response" in extended.to_json() and "stderr_response" in extended.to_json()
    forged = unique_json(historical)
    forged["stderr_response"] = None
    with pytest.raises(ValueError, match="1.0 cannot contain"):
        WorkerInvocation.from_dict(forged)
    with store.writer(), pytest.raises(StoreError, match="identity changed"):
        store.commit(replace(extended, state="reconciliation_required"))
