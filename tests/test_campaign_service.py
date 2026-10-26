"""Public request behavior: duplicate delivery, conflicts, repair and authority limits."""

from dataclasses import replace
import json

from autoengineering.campaign.records import Request, Response
from autoengineering.campaign.service import CampaignService, Transition
from autoengineering.campaign.store import EventStore
from examples.campaign_contracts.build_fixture import fixture


def service(tmp_path, spec=None):
    calls = []

    def evaluate(request, projection):
        calls.append(request.request_id)
        return Transition("baseline_ready", {"evaluation_id": "baseline"})

    store = EventStore.create(tmp_path / "campaign")
    instance = CampaignService(
        store, spec or fixture(), allow_scientific=True, handlers={"evaluate": evaluate}
    )
    return instance, calls


def test_duplicate_checked_before_revision_and_conflicts_never_execute(tmp_path):
    instance, calls = service(tmp_path)
    request = Request(
        "1.0",
        "contract-fixture",
        "evaluate-1",
        0,
        "evaluate",
        {"candidate_id": "baseline", "mode": "fixed"},
    )
    first = instance.handle(request)
    assert first.status == "ok"
    assert instance.handle(request) == first
    assert (
        instance.handle(
            replace(request, payload={"candidate_id": "baseline", "mode": "calibrate"})
        ).error
        == "request_conflict"
    )
    assert calls == ["evaluate-1"]
    stale = instance.handle(replace(request, request_id="evaluate-2"))
    assert stale.error == "stale_revision"
    assert len(calls) == 1
    # A new service/caller uses the committed digest and response index.
    restarted = CampaignService(instance.store, instance.spec)
    assert restarted.handle(request) == first  # Also valid for a read-only reconnect.


def test_state_is_read_only_and_invalid_payload_rejected_before_handler(tmp_path):
    instance, calls = service(tmp_path)
    read = Request("1.0", "contract-fixture", "state-1", 0, "state", {})
    assert instance.handle(read).result["state"] == "created"
    assert instance.store.replay().revision == 0
    invalid = replace(read, operation="evaluate", payload={"command": "untrusted"})
    response = instance.handle(invalid)
    assert response.error == "schema_error"
    assert not calls
    other = CampaignService(instance.store, instance.spec)
    assert (
        other.handle(replace(read, operation="evaluate", request_id="new-readonly")).error
        == "invalid_transition"
    )


def test_repair_count_survives_restart_and_branching_requests(tmp_path):
    instance, _ = service(tmp_path)
    request = Request(
        "1.0", "contract-fixture", "bad-1", 0, "diagnostics", {"artifact_id": "unknown"}
    )
    response = instance.handle(request)  # Wrong state.
    assert response.error == "invalid_transition"
    for index in (1, 2):
        request = replace(
            request,
            request_id=f"repair-{index}",
            expected_revision=response.revision,
            payload={"artifact_id": "unknown", "repair_of": "bad-1"},
        )
        instance = CampaignService(instance.store, instance.spec, allow_scientific=True)
        response = instance.handle(request)
        assert response.result["repair_count"] == index
    request = replace(request, request_id="repair-3", expected_revision=response.revision)
    assert instance.handle(request).error == "budget_exhausted"


def test_transport_rejections_are_bounded_and_not_domain_events(tmp_path):
    spec = replace(fixture(), workflow=replace(fixture().workflow, max_transport_requests=2))
    instance, _ = service(tmp_path, spec)
    for _ in range(2):
        response = Response.from_json(instance.request_json('{"incomplete":'))
        assert response.error == "schema_error"
    assert Response.from_json(instance.request_json("not json")).error == "budget_exhausted"
    assert instance.store.replay().revision == 0
    assert len(list((instance.store.root / "control").glob("transport-*.json"))) == 2
    assert len(json.loads(instance.request_json('"scalar"'))) > 0


def test_schema_rejection_with_valid_id_is_durable_and_idempotent(tmp_path):
    instance, calls = service(tmp_path)
    payload = {
        "schema_version": "2.0",
        "campaign_id": "contract-fixture",
        "request_id": "bad-schema",
        "expected_revision": 0,
        "operation": "execute_code",
        "payload": {"code": "private"},
    }
    raw = json.dumps(payload)
    first = Response.from_json(instance.request_json(raw))
    assert first.error == "schema_error"
    assert first.request_id == "bad-schema"
    assert instance.store.replay().revision == 1
    assert Response.from_json(instance.request_json(raw)) == first
    assert not list((instance.store.root / "control").glob("transport-*.json"))
    payload["payload"] = {}
    assert (
        Response.from_json(instance.request_json(json.dumps(payload))).error == "request_conflict"
    )
    assert not calls


def test_stale_and_conflicting_rejections_share_the_persistent_transport_limit(tmp_path):
    spec = replace(fixture(), workflow=replace(fixture().workflow, max_transport_requests=3))
    instance, _ = service(tmp_path, spec)
    request = Request("1.0", spec.name, "stale-1", 999, "freeze", {})
    assert instance.handle(request).error == "stale_revision"
    assert instance.handle(request).error == "stale_revision"
    assert instance.handle(replace(request, request_id="stale-2")).error == "stale_revision"
    conflicting = replace(request, payload={"unsupported": True})
    rejected = instance.handle(conflicting)
    assert rejected.error == "request_conflict"
    assert instance.handle(conflicting) == rejected
    assert instance.handle(replace(request, request_id="stale-3")).error == "budget_exhausted"
    assert instance.store.replay().revision == 2


def test_malformed_schema_repairs_cannot_reset_the_root_counter(tmp_path):
    instance, _ = service(tmp_path)
    base = {"request_id": "root", "operation": "unsupported", "payload": {}}
    response = Response.from_json(instance.request_json(json.dumps(base)))
    assert response.error == "schema_error"
    for index in range(1, 5):
        base["request_id"] = f"repair-{index}"
        base["payload"] = {"repair_of": "root" if index < 4 else "repair-3"}
        response = Response.from_json(instance.request_json(json.dumps(base)))
        assert response.result["repair_root"] == "root"
        assert response.result["repair_count"] == index
        assert response.error == ("schema_error" if index <= 2 else "budget_exhausted")
