"""Permanent reservations survive owner loss and commit interruption."""
from dataclasses import replace

import pytest

from autoengineering.campaign.store import StoreError, WriterBusy
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.store import SuiteStore
from test_utility_contracts import H, suite


def operation(spec, **changes):
    return dict(request_id="reserve-one", operation="reserve", cell_digest=spec.cells[0].digest,
                attempt_id="attempt-one", child_digest=H,
                resources=(ResourceCap("scientific_starts", "count", 60, "reservation"),),
                **changes)


def test_permanent_parent_allowance_and_idempotency(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    args = operation(spec)
    with store.writer():
        first = store.append(**args)
        assert store.append(**args) == first
    resumed = SuiteStore(store.root, expected=spec)
    with resumed.writer():
        with pytest.raises(StoreError, match="unresolved"):
            resumed.append(**(args | {"request_id": "retry", "attempt_id": "retry"}))
        args.update(request_id="start", operation="start", resources=())
        resumed.append(**args)
        args.update(request_id="finish", operation="finish", result_digest=H)
        resumed.append(**args)
        with pytest.raises(StoreError, match="exhausted"):
            resumed.append(**(operation(spec) | {"request_id": "next", "attempt_id": "next"}))
    assert resumed.replay()["used"] == {("fixed_evaluations", "scientific_starts"): 60}


@pytest.mark.parametrize("boundary,committed", [("before_suite_commit", False),
                                                ("after_suite_commit", True)])
def test_commit_failure_recovery(tmp_path, boundary, committed):
    spec = suite()

    def fail(stage):
        if stage == boundary:
            raise RuntimeError("interrupted")

    store = SuiteStore.create(tmp_path / "suite", spec, fault=fail)
    with store.writer(), pytest.raises(RuntimeError):
        store.append(**operation(spec))
    resumed = SuiteStore(store.root)
    assert len(resumed.replay()["events"]) == int(committed)
    with resumed.writer():
        resumed.append(**operation(spec))
    assert len(resumed.replay()["events"]) == 1


def test_lock_identity_and_offline_replay(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    other = SuiteStore(store.root)
    with store.writer():
        with pytest.raises(WriterBusy), other.writer():
            pass
    with pytest.raises(StoreError, match="identity"):
        SuiteStore(store.root, expected=replace(spec, analysis_digest="2" * 64))
    with pytest.raises(StoreError, match="lock"):
        store.append(**operation(spec))
    # Disposable unrelated projection cannot grant new work.
    (store.root / "state.json").write_text('broken projection')
    assert store.replay()["events"] == ()


def test_cancel_preserves_charge_and_blocks_start(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    args = operation(spec)
    with store.writer():
        store.append(**args)
        store.append(**(args | {"request_id": "cancel", "operation": "cancel", "resources": ()}))
        with pytest.raises(StoreError, match="transition"):
            store.append(**(args | {"request_id": "start", "operation": "start", "resources": ()}))
    assert store.replay()["used"][("fixed_evaluations", "scientific_starts")] == 60


def test_symlink_and_tamper_rejected(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    with store.writer():
        store.append(**operation(spec))
    event = store.events_path / "000000000001.json"
    saved = event.read_text()
    event.write_text(saved.replace('reserve-one', 'reserve-two'))
    with pytest.raises(StoreError, match="digest"):
        store.replay()
    event.unlink()
    target = tmp_path / "outside.json"
    target.write_text(saved)
    event.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        store.replay()


def test_more_than_32_cells_share_parent_cap(tmp_path):
    spec = suite(20)
    store = SuiteStore.create(tmp_path / "suite", spec)
    with store.writer():
        for index, cell in enumerate(c for b in spec.child_batches() for c in b):
            store.append(request_id=f"reserve-{index}", operation="reserve", cell_digest=cell.digest,
                         attempt_id=f"attempt-{index}", child_digest=H,
                         resources=(ResourceCap("scientific_starts", "count", 2, "reservation"),))
    assert len(store.replay()["attempts"]) == 40
    assert store.replay()["used"][("fixed_evaluations", "scientific_starts")] == 80


def test_manifest_change_rejected_after_open(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    (store.root / "suite.json").write_text(replace(spec, suite_id="changed").to_json())
    with pytest.raises(StoreError, match="manifest changed"):
        store.replay()


def test_started_attempt_cannot_restart_or_change_child(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    args = operation(spec)
    with store.writer():
        store.append(**args)
        store.append(**(args | {"request_id": "start", "operation": "start", "resources": ()}))
    resumed = SuiteStore(store.root)
    with resumed.writer():
        with pytest.raises(StoreError, match="transition"):
            resumed.append(**(args | {"request_id": "restart", "operation": "start",
                                     "resources": ()}))
        with pytest.raises(StoreError, match="binding"):
            resumed.append(**(args | {"request_id": "finish", "operation": "finish",
                                     "resources": (), "result_digest": H,
                                     "child_digest": "2" * 64}))
        with pytest.raises(StoreError, match="changed payload"):
            resumed.append(**(args | {"child_digest": "2" * 64}))
    assert resumed.replay()["attempts"]["attempt-one"][1] == "started"


def test_selection_cannot_spend_confirmation_reserve(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    with store.writer():
        store.append(**(operation(spec) | {"resources": (
            ResourceCap("scientific_starts", "count", 98, "reservation"),)}))
        with pytest.raises(StoreError, match="exhausted"):
            store.append(**(operation(spec) | {
                "request_id": "second", "attempt_id": "second",
                "cell_digest": spec.cells[1].digest,
                "resources": (ResourceCap("scientific_starts", "count", 1, "reservation"),)}))
