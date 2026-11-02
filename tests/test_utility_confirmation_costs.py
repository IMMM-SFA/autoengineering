"""Public confirmation timing and cost projection with authored callbacks only."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.store import StoreError
from autoengineering.utility import scoring
from autoengineering.utility.costs import join_confirmation_costs
from autoengineering.utility.report import accounting_report
from autoengineering.utility.scoring import (
    ConfirmationReceipt,
    PublicScore,
    validate_score,
)
from autoengineering.utility.store import SuiteStore
from test_utility_scoring import setup


def completed(tmp_path, monkeypatch, *, score=None):
    calls = []

    def scorer(*_):
        calls.append(1)
        return score or PublicScore("success", "power", "W", 3, True)

    store, grant, service, contract = setup(tmp_path, scorer)
    ticks = iter((100.0, 102.5))
    monkeypatch.setattr(scoring.time, "monotonic", lambda: next(ticks))
    receipt = service.confirm(grant)
    return store, grant, service, receipt, contract, calls


def values(store):
    records = join_confirmation_costs(store)
    assert all(r.category == "confirmation" and len(r.cell_digests) == 1 for r in records)
    return {r.resource: r.quantity for r in records}


def test_completed_callback_cost_is_measured_without_inventing_worker_starts(tmp_path, monkeypatch):
    store, grant, service, receipt, _, calls = completed(tmp_path, monkeypatch)
    assert receipt.measurement.elapsed_seconds == 2.5
    assert receipt.measurement.grant_digest == grant.digest
    assert receipt.measurement.scorer_digest == grant.scorer_digest
    assert receipt.measurement.score_digest == receipt.score.digest
    assert values(store) == {
        "confirmation_reservations": 1,
        "confirmation_access_intents": 1,
        "confirmation_scores_committed": 1,
        "confirmation_callbacks_completed": 1,
        "confirmation_callback_duration": 2.5,
        "confirmation_scoring_starts": None,
    }
    before = join_confirmation_costs(store)
    assert service.confirm(grant) == receipt and calls == [1]
    assert join_confirmation_costs(SuiteStore(store.root)) == before
    report = accounting_report(store)
    assert any(r["category"] == "confirmation" for r in report["receipts"])
    assert report["confirmation_state"] == "scored_unanalyzed"
    assert not report["complete_cost_evidence"]


def test_legacy_receipt_retains_exact_serialized_shape_and_unknown_duration(tmp_path, monkeypatch):
    store, grant, _, measured, contract, _ = completed(tmp_path, monkeypatch)
    legacy = ConfirmationReceipt(grant.digest, measured.access_digest, measured.score, contract)
    assert set(legacy.to_dict()) == {"grant_digest", "access_digest", "score", "outcome_contract"}
    assert ConfirmationReceipt.from_json(legacy.to_json()) == legacy
    # A trusted legacy public receipt fixture, not a rewritten suite journal.
    monkeypatch.setattr(scoring, "read_receipt", lambda *_: legacy)
    cost = values(store)
    assert cost["confirmation_callback_duration"] is None
    assert cost["confirmation_callbacks_completed"] is None
    assert cost["confirmation_scores_committed"] == 1
    assert cost["confirmation_scoring_starts"] is None


@pytest.mark.parametrize("stage", ["confirmation_access_committed", "confirmation_score_created"])
def test_interrupted_confirmation_retains_charge_and_unknown_callback_cost(
    tmp_path, monkeypatch, stage
):
    store, grant, service, _ = setup(
        tmp_path, lambda *_: PublicScore("success", "power", "W", 3, True)
    )
    ticks = iter((100.0, 102.5))
    monkeypatch.setattr(scoring.time, "monotonic", lambda: next(ticks))

    def fault(point):
        if point == stage:
            raise RuntimeError("authored confirmation interruption")

    store.fault = fault
    with pytest.raises(RuntimeError):
        service.confirm(grant)
    cost = values(store)
    assert cost["confirmation_reservations"] == cost["confirmation_access_intents"] == 1
    assert cost["confirmation_scores_committed"] == 0
    assert cost["confirmation_callback_duration"] is None
    assert cost["confirmation_callbacks_completed"] is None
    assert accounting_report(store)["confirmation_state"] == "reconciliation_required"
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)


def test_reservation_before_access_is_not_reported_as_unattempted(tmp_path):
    store, grant, _, _ = setup(tmp_path, lambda *_: pytest.fail("callback invoked"))
    attempt = "confirmation-" + grant.cell_digest[:48]
    with store.writer():
        store.append(
            request_id=attempt + "-reserve",
            operation="reserve",
            resources=grant.resources,
            cell_digest=grant.cell_digest,
            attempt_id=attempt,
            child_digest=grant.digest,
            phase="confirmation",
        )
    cost = values(store)
    assert cost["confirmation_reservations"] == 1 and cost["confirmation_access_intents"] == 0
    assert cost["confirmation_scoring_starts"] is None
    assert accounting_report(store)["confirmation_state"] == "reconciliation_required"


def test_no_confirmation_produces_no_invented_cost_records(tmp_path):
    store, _, _, _ = setup(tmp_path, lambda *_: pytest.fail("callback invoked"))
    assert join_confirmation_costs(store) == ()
    assert accounting_report(store)["confirmation_state"] == "not_attempted"


@pytest.mark.parametrize("problem", ["grant", "score", "negative", "boolean", "nonfinite"])
def test_measurement_must_match_its_score_and_finite_nonnegative_clock(
    tmp_path, monkeypatch, problem
):
    _, _, _, receipt, _, _ = completed(tmp_path, monkeypatch)
    if problem == "grant":
        with pytest.raises(ValueError, match="grant or score"):
            replace(receipt, measurement=replace(receipt.measurement, grant_digest="2" * 64))
    elif problem == "score":
        with pytest.raises(ValueError, match="grant or score"):
            replace(receipt, measurement=replace(receipt.measurement, score_digest="2" * 64))
    else:
        duration = {"negative": -1, "boolean": True, "nonfinite": float("inf")}[problem]
        with pytest.raises(ValueError):
            replace(receipt.measurement, elapsed_seconds=duration)


def test_measurement_from_another_scorer_cannot_enter_the_journal(tmp_path, monkeypatch):
    store, grant, _, receipt, _, _ = completed(tmp_path, monkeypatch)
    altered = replace(receipt, measurement=replace(receipt.measurement, scorer_digest="2" * 64))
    ref = put_bytes(
        store.root,
        altered.to_json().encode(),
        name="confirmation-score.json",
        media_type="application/json",
        producer="authored-foreign-scorer",
    )
    access = store.replay()["confirmation_accesses"]["confirmation-" + grant.cell_digest[:48]]
    with pytest.raises(StoreError, match="another scorer"):
        validate_score(
            store, SimpleNamespace(result_digest=ref.sha256), access, store.replay()["frozen"]
        )


def test_failed_scientific_score_still_has_callback_cost(tmp_path, monkeypatch):
    store, _, _, receipt, _, _ = completed(
        tmp_path, monkeypatch, score=PublicScore("scientific_infeasible", "power", "W", None, False)
    )
    assert receipt.score.value is None and values(store)["confirmation_callback_duration"] == 2.5


def test_tampered_public_receipt_is_refused_without_private_scorer(tmp_path, monkeypatch):
    store, _, _, _, _, _ = completed(tmp_path, monkeypatch)
    identity = next(iter(store.replay()["confirmation_scores"].values()))
    (store.root / f"artifacts/{identity}/confirmation-score.json").write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        join_confirmation_costs(store)


def test_csv_export_includes_confirmation_time_without_unknown_zero_fill(tmp_path, monkeypatch):
    from autoengineering.utility.reporting import comparative_report, report_files
    from test_utility_reporting import report_fixture, rows

    store, request, calls, _, _ = report_fixture(tmp_path)
    before = store.replay()["head"]
    monkeypatch.setattr(
        scoring,
        "time",
        SimpleNamespace(monotonic=lambda: pytest.fail("report attempted a fresh measurement")),
    )
    document = comparative_report(store, request)
    files = report_files(document)
    costs = {
        r["resource"]: r
        for r in rows(files["physical-costs.csv"])
        if r["category"] == "confirmation"
    }
    measured = document["accounting"]["confirmation_receipts"][0]["receipt"]["measurement"]
    assert float(costs["confirmation_callback_duration"]["quantity"]) == measured["elapsed_seconds"]
    assert costs["confirmation_scoring_starts"]["quantity"] == ""
    allocated = [r for r in rows(files["cost-allocations.csv"]) if r["category"] == "confirmation"]
    assert len(allocated) == 6
    assert all(float(r["allocation"]) == 1 for r in allocated)
    assert calls == [1] and store.replay()["head"] == before
