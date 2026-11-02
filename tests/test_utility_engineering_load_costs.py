"""Offline joins use original native metadata and preserve incomplete work."""

from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.store import StoreError
from autoengineering.utility.confirmation import read_selected_state
from autoengineering.utility.costs import reconcile, join_confirmation_costs
from autoengineering.utility.scoring import ConfirmationGrant, validate_grant
from autoengineering.utility.store import SuiteStore
from examples.utility import engineering_load_callback as callback
from examples.utility import engineering_load_costs as costs
from examples.utility import engineering_load_scoring as kernel
from examples.utility import engineering_scenarios as source
from test_utility_engineering_load_callback import setup, authored_solver

ARCHIVE = (
    Path(__file__).resolve().parents[1]
    / "examples/utility/verification-engineering-load-callback-v1"
)


def registration(store, grant, intent, request):
    selected = validate_grant(store, grant, store.replay()["frozen"])
    bound = read_selected_state(store.root, selected.selected_state)
    policy = kernel.LoadScorePolicy(
        "utility-coupled-load-score-v1",
        bound.model.digest,
        request["pins"]["files"]["examples/utility/engineering_load_scoring.py"],
        request["minimum_node2_voltage_V"],
    )
    return costs.LoadCostRegistration(
        "utility-load-cost-registration-v1",
        ArtifactRef.from_dict(intent["source_binding_artifact"]),
        request["pins"]["files"]["examples/utility/engineering_load_callback.py"],
        policy,
    )


def archived(tmp_path):
    shutil.copytree(ARCHIVE / "public/suite", tmp_path / "suite")
    store = SuiteStore(tmp_path / "suite")
    intent = json.loads((ARCHIVE / "public/callback-intent.json").read_text())
    request = json.loads((ARCHIVE / "public/request.json").read_text())
    grant = ConfirmationGrant.from_dict(intent["grant"])
    reg = registration(store, grant, intent, request)
    ref = reference(
        store.root,
        f"engineering-load-work/{grant.digest}.json",
        media_type="application/json",
        producer="engineering-load-work",
    )
    return store, grant, reg, ref


def by_resource(records):
    return {r.resource: r.quantity for r in records}


def test_actual_native_counters_join_without_reopening_or_double_charging(tmp_path, monkeypatch):
    store, grant, reg, ref = archived(tmp_path)
    monkeypatch.setattr(source, "read_private", lambda *a, **k: pytest.fail("private opened"))
    monkeypatch.setattr(kernel, "run_lifecycle", lambda *a, **k: pytest.fail("model ran"))
    records = costs.join_load_costs(store, grant, reg, work_artifact=ref)
    values = by_resource(records)
    assert values["load_case_attempts"] == values["load_model_starts"] == 24
    assert values["load_solver_iterations"] == 395
    assert values["load_component_calls"] == 6440
    assert values["load_component_linearize_calls"] == 1975
    assert values["load_model_start_reservations"] == 24
    assert values["load_solver_iteration_reservations"] == 2400
    assert all(
        r.category == "confirmation" and r.cell_digests == (grant.cell_digest,) for r in records
    )
    combined = (*join_confirmation_costs(store), *records)
    assert len({r.receipt_id for r in combined}) == len(combined)
    # Generic process-start evidence remains unknown for this in-process callback.
    assert not reconcile(combined, tuple(r.receipt_id for r in combined))["complete"]
    with pytest.raises(ValueError, match="duplicate physical receipt"):
        reconcile((*records, *records), tuple(r.receipt_id for r in records))


def test_missing_work_proof_keeps_actual_cost_unknown_despite_committed_score(tmp_path):
    store, grant, reg, ref = archived(tmp_path)
    records = costs.join_load_costs(store, grant, reg)
    values = by_resource(records)
    assert values["load_model_start_reservations"] == 24
    for name in (
        "load_case_attempts",
        "load_model_starts",
        "load_solver_iterations",
        "load_component_calls",
        "load_component_linearize_calls",
    ):
        assert values[name] is None
    known = costs.join_load_costs(store, grant, reg, work_artifact=ref)
    assert [r.receipt_id for r in records] == [r.receipt_id for r in known]
    with pytest.raises(ValueError, match="duplicate physical receipt"):
        reconcile((*records, *known), tuple(r.receipt_id for r in records))


@pytest.mark.parametrize("change", ["bytes", "grant", "registration", "role", "missing", "symlink"])
def test_changed_proof_or_identity_is_rejected(tmp_path, change):
    store, grant, reg, ref = archived(tmp_path)
    path = store.root / ref.path
    if change == "bytes":
        path.write_text(path.read_text() + " ")
    elif change == "grant":
        grant = replace(grant, scorer_digest="0" * 64)
    elif change == "registration":
        reg = replace(reg, callback_source_digest="0" * 64)
    elif change == "role":
        ref = replace(ref, producer="other-role")
    elif change == "missing":
        path.unlink()
    else:
        other = tmp_path / "other"
        other.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(other)
    with pytest.raises((ValueError, StoreError)):
        costs.join_load_costs(store, grant, reg, work_artifact=ref)


@pytest.mark.parametrize(
    "change", ["unknown_field", "counts", "score", "scope", "negative", "over_cap"]
)
def test_refreshed_reference_cannot_hide_inconsistent_work(tmp_path, change):
    store, grant, reg, ref = archived(tmp_path)
    path = store.root / ref.path
    work = json.loads(path.read_text())
    if change == "unknown_field":
        work["extra"] = 1
    elif change == "counts":
        work["completed_model_starts"] = 23
    elif change == "score":
        work["score_digest"] = "0" * 64
    elif change == "scope":
        work["derivative_counter_scope"] = "total derivative calls"
    elif change == "negative":
        work["total_inner_work"]["component_calls"] = -1
    else:
        work["total_inner_work"]["solver_iterations"] = 2401
        work["known_completed_inner_work"]["solver_iterations"] = 2401
    path.write_text(json.dumps(work))
    ref = reference(store.root, ref.path, media_type=ref.media_type, producer=ref.producer)
    with pytest.raises((ValueError, StoreError)):
        costs.join_load_costs(store, grant, reg, work_artifact=ref)


@pytest.mark.parametrize("publication_lost", [False, True])
def test_failed_inner_work_and_missing_publication_stay_unknown(
    tmp_path, monkeypatch, publication_lost
):
    store, grant, service, captured, _ = setup(tmp_path, monkeypatch)
    calls = authored_solver(monkeypatch, change="failure")
    if publication_lost:

        def fail(*a, **k):
            raise OSError("work publication lost")

        monkeypatch.setattr(callback, "durable_write", fail)
        with pytest.raises(StoreError, match="uncertain"):
            service.confirm(grant)
        ref = None
    else:
        assert service.confirm(grant).score.status == "model_failure"
        ref = reference(
            store.root,
            f"engineering-load-work/{grant.digest}.json",
            media_type="application/json",
            producer="engineering-load-work",
        )
    reg = costs.LoadCostRegistration(
        "utility-load-cost-registration-v1",
        captured["source_ref"],
        callback.source_identity(),
        captured["scorer"].policy,
    )
    values = by_resource(costs.join_load_costs(store, grant, reg, work_artifact=ref))
    assert len(calls) == 3 and values["load_model_starts"] is None
    assert values["load_solver_iterations"] is None
    assert values["load_case_attempts"] == (None if publication_lost else 3)
    assert values["load_completed_evaluations"] == (None if publication_lost else 2)
    assert values["load_known_completed_solver_iterations"] == (None if publication_lost else 8)
    assert values["load_known_completed_component_calls"] == (None if publication_lost else 40)


def test_durable_work_survives_lost_suite_score_commit_without_new_model(tmp_path, monkeypatch):
    store, grant, service, captured, _ = setup(tmp_path, monkeypatch)
    calls = authored_solver(monkeypatch)

    def fault(stage):
        if stage == "confirmation_score_created":
            raise RuntimeError("owner lost")

    store.fault = fault
    with pytest.raises(RuntimeError):
        service.confirm(grant)
    assert not store.replay()["confirmation_scores"] and len(calls) == 24
    ref = reference(
        store.root,
        f"engineering-load-work/{grant.digest}.json",
        media_type="application/json",
        producer="engineering-load-work",
    )
    reg = costs.LoadCostRegistration(
        "utility-load-cost-registration-v1",
        captured["source_ref"],
        callback.source_identity(),
        captured["scorer"].policy,
    )
    values = by_resource(costs.join_load_costs(store, grant, reg, work_artifact=ref))
    assert values["load_model_starts"] == 24 and values["load_solver_iterations"] == 96
    assert not store.replay()["confirmation_scores"] and len(calls) == 24


def test_an_uncharged_grant_does_not_invent_a_cost_receipt(tmp_path, monkeypatch):
    store, grant, _, captured, _ = setup(tmp_path, monkeypatch)
    reg = costs.LoadCostRegistration(
        "utility-load-cost-registration-v1",
        captured["source_ref"],
        callback.source_identity(),
        captured["scorer"].policy,
    )
    with pytest.raises(StoreError, match="original charged grant"):
        costs.join_load_costs(store, grant, reg)


@pytest.mark.parametrize("value", [True, 1.5, float("nan"), float("inf")])
def test_noninteger_or_nonfinite_native_work_is_not_a_cost(value):
    with pytest.raises(ValueError):
        costs.CounterWork(value, 1, 1)
