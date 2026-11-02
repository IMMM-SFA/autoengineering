"""Aggregate reservations are durable and never become free retries on replay."""

from dataclasses import replace
import json

import pytest

from autoengineering.agents.batch import (
    BatchCase,
    BatchSpec,
    BatchStore,
    PhysicalObservation,
    PhysicalReservation,
)
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.records import HostSelection, ResourceLimits
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError, WriterBusy

H = "0" * 64


def specification(*, hosts=4, science=2, tasks=4, repairs=2, transcript=10000):
    return BatchSpec(
        "1.0",
        "unit-batch",
        host_source_identity(),
        host_environment_identity(),
        HostSelection("fake", "none", "scripted", "1.0"),
        FakeHost(()).capabilities(),
        H,
        ResourceLimits(hosts, tasks, repairs, 1, 100, 10, transcript, 1000),
        science,
        (BatchCase("first", "roles", H, hosts - 1, science), BatchCase("second", "text", H, 1, 0)),
    )


def initialized(tmp_path, **kwargs):
    tmp_path.chmod(0o700)
    store = BatchStore.create(tmp_path / "batch", specification(**kwargs), clock=lambda: 100)
    store.start_case("first", H)
    return store


def reservation(*, id="call-1", case="first", task="task-1", resource="host", at=100, timeout=10):
    return PhysicalReservation(
        id,
        case,
        resource,
        digest({"id": id, "resource": resource}),
        task if resource == "host" else None,
        at,
        timeout,
        10 if resource == "host" else 0,
        100 if resource == "host" else 0,
        100 if resource == "host" else 0,
    )


def observed(store, r, *, status="completed", stopped=True, size=20, usage=None, intent="absent"):
    proof = store.evidence(
        {"fixture": "authored accounting proof only", "id": r.id, "status": status}
    )
    return PhysicalObservation(
        r.id, status, stopped, size, usage or {}, None, intent, None, (proof,)
    )


def finish(store, id="first", status="passed"):
    return store.finish_case(id, status, (store.evidence({"fixture_case": id, "status": status}),))


def test_manifest_roundtrip_is_strict_and_does_not_grant_authority(tmp_path):
    store = initialized(tmp_path)
    assert BatchSpec.from_json(store.spec.to_json()) == store.spec
    assert store.report()["execution_authority"] == "not_granted_by_batch_manifest"
    with pytest.raises(AttributeError):
        store.spec.capabilities.host = "codex"


def test_manifest_and_case_bounds_reject_bad_identity_or_expansion(tmp_path):
    spec = specification()
    with pytest.raises(ValueError):
        replace(spec, cases=(*spec.cases, spec.cases[0]))
    with pytest.raises(ValueError):
        replace(spec, limits=replace(spec.limits, max_invocations=1))
    with pytest.raises(ValueError):
        replace(spec, scientific_starts=1)
    tmp_path.chmod(0o700)
    with pytest.raises(StoreError, match="identity"):
        BatchStore.create(tmp_path / "foreign", replace(spec, source_identity="1" * 64))
    assert not (tmp_path / "foreign").exists()


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_reservation_commit_fault_never_launches_or_grants_a_replay(tmp_path, stage):
    store = initialized(tmp_path)
    calls = []

    def fault(value):
        if value == stage:
            raise RuntimeError("authored reservation acknowledgment loss")

    store.fault = fault
    r = reservation()
    with pytest.raises(RuntimeError):
        store.execute(r, lambda _: calls.append(True), lambda *_: pytest.fail("observer"))
    assert not calls
    reopened = BatchStore(store.root, expected_digest=store.digest, clock=lambda: 100)
    if stage == "after_event_commit":
        assert reopened.report()["host_reservations_charged"] == 1
        with pytest.raises(StoreError, match="duplicate"):
            reopened.execute(r, lambda _: calls.append(True), lambda *_: None)
    else:
        assert reopened.report()["host_reservations_charged"] == 0
    assert not calls


def test_unknown_work_blocks_all_cases_and_preserves_charges(tmp_path):
    store = initialized(tmp_path)
    r = reservation()
    store.reserve(r)
    store.observe(
        observed(
            store, r, status="reconciliation_required", stopped=False, size=None, intent="unknown"
        )
    )
    report = store.report()
    assert report["pending_reservations"] == [r.id]
    assert report["transcript_bytes_charged"] == r.transcript_ceiling
    assert report["host_invocations_with_unknown_usage"] == 1
    assert report["request_intents_unknown"] == 1
    with pytest.raises(StoreError, match="pending physical"):
        store.reserve(reservation(id="call-2"))
    with pytest.raises(StoreError, match="unresolved"):
        finish(store)
    with pytest.raises(StoreError, match="unfinished"):
        store.start_case("second", H)
    result = observed(store, r, status="host_failure", size=None, intent="unknown")
    store.observe(result)
    store.observe(result)
    assert store.report()["host_reservations_charged"] == 1
    assert store.report()["transcript_bytes_charged"] == r.transcript_ceiling
    assert store.report()["host_invocations_with_unknown_usage"] == 1


def test_same_physical_identity_cannot_be_reissued_or_terminal_evidence_rewritten(tmp_path):
    store = initialized(tmp_path)
    r = reservation()
    store.reserve(r)
    result = observed(store, r)
    store.observe(result)
    with pytest.raises(StoreError, match="identity was already"):
        store.reserve(replace(r, id="other"))
    with pytest.raises(StoreError, match="immutable"):
        store.observe(replace(result, status="host_failure"))


def test_repairs_and_science_consume_the_shared_frozen_limits(tmp_path):
    store = initialized(tmp_path, hosts=5, repairs=1, science=1)
    first = reservation()
    store.reserve(first)
    store.observe(observed(store, first, status="invalid_output"))
    second = reservation(id="call-2")
    store.reserve(second)
    store.observe(observed(store, second, status="host_failure"))
    with pytest.raises(StoreError, match="repair allowance"):
        store.reserve(reservation(id="call-3"))
    for i in range(1):
        science = reservation(id=f"science-{i}", resource="science")
        store.reserve(science)
        store.observe(observed(store, science, status="success", size=0, intent="not_applicable"))
    with pytest.raises(StoreError, match="physical batch allowance"):
        store.reserve(reservation(id="science-extra", resource="science"))
    assert store.report()["scientific_reservations_charged"] == 1


def test_task_and_transcript_limits_apply_across_distinct_cases(tmp_path):
    store = initialized(tmp_path, tasks=1, transcript=220)
    r = reservation()
    store.reserve(r)
    # A known stopped failure with unknown byte count retains its whole ceiling.
    store.observe(observed(store, r, status="host_failure", size=None))
    finish(store)
    store.start_case("second", H)
    with pytest.raises(StoreError, match="task or repair"):
        store.reserve(reservation(id="call-2", case="second", task="other"))


def test_transcript_reservation_is_released_only_to_observed_bytes(tmp_path):
    store = initialized(tmp_path, transcript=220)
    r = reservation()
    store.reserve(r)
    assert store.report()["transcript_bytes_charged"] == 210
    store.observe(observed(store, r, status="host_failure", size=None))
    with pytest.raises(StoreError, match="transcript allowance"):
        store.reserve(reservation(id="call-2", task="other"))
    assert store.report()["host_reservations_charged"] == 1


def test_unknown_observation_cannot_erase_known_usage_model_or_request_intent(tmp_path):
    store = initialized(tmp_path)
    r = reservation()
    store.reserve(r)
    observation = replace(
        observed(
            store,
            r,
            status="reconciliation_required",
            stopped=False,
            size=None,
            usage={"total_tokens": 4},
            intent="present",
        ),
        resolved_model="observed-model",
    )
    store.observe(observation)
    with pytest.raises(StoreError, match="erased known"):
        store.observe(replace(observation, usage={}))
    store.observe(replace(observation, status="host_failure", stop_verified=True))
    assert store.replay().observations[r.id].usage["total_tokens"] == 4


def test_deadline_order_and_failed_case_block_future_work(tmp_path):
    store = initialized(tmp_path)
    with pytest.raises(StoreError, match="deadline"):
        store.reserve(reservation(at=199, timeout=2))
    finish(store, status="failed")
    with pytest.raises(StoreError, match="failed case"):
        store.start_case("second", H)


def test_commit_delay_never_launches_after_its_batch_window(tmp_path):
    store = initialized(tmp_path)
    now = [100]
    store.clock = lambda: now[0]
    calls = []

    def delayed(point):
        if point == "after_event_commit":
            now[0] = 195

    store.fault = delayed
    with pytest.raises(StoreError, match="before physical launch"):
        store.execute(reservation(), lambda _: calls.append(True), lambda *_: None)
    assert not calls and store.report()["host_reservations_charged"] == 1
    assert store.report()["status"] == "reconciliation_required"


def test_stale_timestamp_cannot_bypass_deadline_after_reopen(tmp_path):
    store = initialized(tmp_path)
    reopened = BatchStore(store.root, expected_digest=store.digest, clock=lambda: 201)
    with pytest.raises(StoreError, match="clock or deadline"):
        reopened.execute(reservation(at=100), lambda _: pytest.fail("late launch"), lambda *_: None)
    assert not reopened.replay().reservations


def test_reopen_cannot_reset_creation_time_or_mutate_without_a_pin(tmp_path):
    store = initialized(tmp_path)
    read_only = BatchStore(store.root, clock=lambda: 100)
    assert read_only.report() == store.report()
    with pytest.raises(StoreError, match="caller-pinned"):
        read_only.reserve(reservation())
    path = store.root / "batch.json"
    value = json.loads(path.read_text())
    value["created_at"] = 101
    path.write_text(json.dumps(value))
    with pytest.raises(StoreError, match="trusted pin"):
        BatchStore(store.root, expected_digest=store.digest)
    with pytest.raises(StoreError, match="manifest changed"):
        store.replay()


def test_operation_lock_is_independent_of_writer_and_blocks_competing_work(tmp_path):
    store = initialized(tmp_path)
    other = BatchStore(store.root, expected_digest=store.digest, clock=lambda: 100)
    with store.operation():
        with pytest.raises(WriterBusy):
            other.execute(reservation(), lambda _: pytest.fail("launch"), lambda *_: None)
        # A separate read or short writer observation is not blocked by physical work.
        assert other.report()["status"] == "active"
        with other.writer():
            pass


@pytest.mark.parametrize("tamper", ["event", "evidence"])
def test_corruption_fails_without_execution(tmp_path, tamper):
    store = initialized(tmp_path)
    r = reservation()
    store.reserve(r)
    observation = observed(store, r)
    store.observe(observation)
    path = (
        store.events / "000000000002.json"
        if tamper == "event"
        else store.root / observation.evidence[0].path
    )
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        BatchStore(store.root, expected_digest=store.digest).report()
