"""Explicit original-result publication. Authored callbacks qualify no private runtime."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.store import StoreError
from autoengineering.utility import scoring
from autoengineering.utility.costs import join_confirmation_costs
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.report import accounting_report
from autoengineering.utility.scoring import PublicScore, validate_score
from autoengineering.utility.store import SuiteStore
from test_utility_scoring import setup


class SavedScorer:
    def __init__(self, result=None):
        self.calls = 0
        self.recoveries = 0
        self.saved = None
        self.result = result or PublicScore("success", "power", "W", 3.0, True)

    def __call__(self, *_):
        self.calls += 1
        self.saved = self.result
        return self.saved

    def recover(self, *_):
        self.recoveries += 1
        if self.saved is None:
            raise RuntimeError("PRIVATE-RECOVERY-CANARY: original result absent")
        return self.saved


def fail_at(store, boundary):
    def fault(point):
        if point == boundary:
            raise RuntimeError("authored publication interruption")

    store.fault = fault


def pending(tmp_path, *, boundary="confirmation_score_created", result=None):
    scorer = SavedScorer(result)
    store, grant, service, contract = setup(tmp_path, scorer)
    fail_at(store, boundary)
    with pytest.raises(RuntimeError):
        service.confirm(grant)
    store.fault = lambda _: None
    return store, grant, service, scorer, contract


@pytest.mark.parametrize(
    "status",
    [
        "scientific_infeasible",
        "model_failure",
        "timeout",
        "infrastructure_failure",
        "insufficient_data",
    ],
)
def test_recovery_preserves_original_failure_without_penalty_or_reselection(tmp_path, status):
    result = PublicScore(
        status, "power", "W", None, False if status == "scientific_infeasible" else None
    )
    store, grant, service, scorer, _ = pending(tmp_path, result=result)
    frozen = store.replay()["frozen"]
    receipt = service.recover(grant)
    assert receipt.score == result and receipt.score.value is None
    assert scorer.calls == scorer.recoveries == 1
    assert store.replay()["frozen"] == frozen


def test_cancelled_suite_can_settle_original_result_without_reopening_work(tmp_path):
    store, grant, service, scorer, _ = pending(tmp_path)
    with store.writer():
        store.append(
            request_id="cancel-after-original-score",
            operation="cancel",
            cell_digest=grant.cell_digest,
            attempt_id="suite-cancel",
            child_digest=grant.digest,
        )
    before = store.replay()
    receipt = service.recover(grant)
    after = store.replay()
    assert receipt.recovery is not None and after["cancelled"] is True
    assert after["used"] == before["used"] and after["phase_used"] == before["phase_used"]
    assert scorer.calls == scorer.recoveries == 1


def test_recovery_publishes_original_without_new_reservation_or_clock(tmp_path, monkeypatch):
    store, grant, service, scorer, _ = pending(tmp_path)
    original = store.replay()
    monkeypatch.setattr(scoring.time, "monotonic", lambda: pytest.fail("new callback timing"))
    receipt = service.recover(grant)
    assert receipt.score == scorer.saved and scorer.calls == scorer.recoveries == 1
    assert receipt.measurement is None and receipt.recovery is not None
    assert receipt.recovery.grant_digest == grant.digest
    assert receipt.recovery.scorer_digest == grant.scorer_digest
    assert receipt.recovery.score_digest == receipt.score.digest
    final = store.replay()
    assert final["used"] == original["used"] and final["phase_used"] == original["phase_used"]
    assert final["confirmation_accesses"] == original["confirmation_accesses"]
    assert len(final["confirmation_scores"]) == 1
    assert service.confirm(grant) == service.recover(grant) == receipt
    assert scorer.calls == scorer.recoveries == 1
    costs = {row.resource: row.quantity for row in join_confirmation_costs(SuiteStore(store.root))}
    assert costs["confirmation_reservations"] == costs["confirmation_access_intents"] == 1
    assert costs["confirmation_recoveries_committed"] == costs["confirmation_scores_committed"] == 1
    assert costs["confirmation_callback_duration"] is None
    assert costs["confirmation_callbacks_completed"] is None
    assert costs["confirmation_scoring_starts"] is None
    assert accounting_report(store)["complete_cost_evidence"] is False


def test_access_without_original_result_stays_charged_without_fallback(tmp_path):
    store, grant, service, scorer, _ = pending(tmp_path, boundary="confirmation_access_committed")
    before = store.replay()
    with pytest.raises(StoreError) as error:
        service.recover(grant)
    assert "PRIVATE-RECOVERY-CANARY" not in str(error.value)
    assert "charges retained" in str(error.value)
    assert scorer.calls == 0 and scorer.recoveries == 1
    assert store.replay()["head"] == before["head"]
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)


def test_recovery_without_reservation_does_not_authorize_first_score(tmp_path):
    scorer = SavedScorer()
    store, grant, service, _ = setup(tmp_path, scorer)
    before = store.replay()["head"]
    with pytest.raises(StoreError, match="original charged"):
        service.recover(grant)
    assert scorer.calls == scorer.recoveries == 0
    assert store.replay()["head"] == before


def test_reserved_attempt_without_access_does_not_invoke_recover(tmp_path):
    scorer = SavedScorer()
    store, grant, service, _ = setup(tmp_path, scorer)
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
    with pytest.raises(StoreError, match="committed access"):
        service.recover(grant)
    assert scorer.calls == scorer.recoveries == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("scorer_digest", "2" * 64),
        ("partition_digest", "2" * 64),
        ("selection_digest", "2" * 64),
        ("model_digest", "2" * 64),
        (
            "resources",
            (
                ResourceCap("scientific_starts", "count", 1, "reservation"),
                ResourceCap("active_time", "s", 1, "reservation"),
            ),
        ),
    ],
)
def test_changed_grant_refuses_before_recovery_callback(tmp_path, field, value):
    store, grant, service, scorer, _ = pending(tmp_path)
    head = store.replay()["head"]
    with pytest.raises(StoreError):
        service.recover(replace(grant, **{field: value}))
    assert scorer.recoveries == 0 and scorer.calls == 1
    assert store.replay()["head"] == head


@pytest.mark.parametrize(
    "boundary,extra_reads",
    [
        ("confirmation_recovery_score_created", 1),
        ("confirmation_recovery_score_committed", 0),
    ],
)
def test_recovery_publication_crashes_repeat_only_original_result_reads(
    tmp_path, boundary, extra_reads
):
    store, grant, service, scorer, _ = pending(tmp_path)
    fail_at(store, boundary)
    with pytest.raises(RuntimeError):
        service.recover(grant)
    assert scorer.calls == scorer.recoveries == 1
    store.fault = lambda _: None
    receipt = service.recover(grant)
    assert receipt.recovery is not None
    assert scorer.calls == 1 and scorer.recoveries == 1 + extra_reads
    state = store.replay()
    assert len(state["confirmation_accesses"]) == len(state["confirmation_scores"]) == 1
    assert state["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")] == 1


def test_committed_original_receipt_keeps_original_measurement(tmp_path):
    _, grant, service, scorer, _ = pending(tmp_path, boundary="confirmation_score_committed")
    receipt = service.recover(grant)
    assert receipt.measurement is not None and receipt.recovery is None
    assert scorer.calls == 1 and scorer.recoveries == 0


def test_scorer_without_recovery_cannot_use_an_orphan_receipt(tmp_path):
    calls = []

    def scorer(*_):
        calls.append(1)
        return PublicScore("success", "power", "W", 3.0, True)

    store, grant, service, _ = setup(tmp_path, scorer)
    fail_at(store, "confirmation_score_created")
    with pytest.raises(RuntimeError):
        service.confirm(grant)
    store.fault = lambda _: None
    with pytest.raises(StoreError, match="no original-result recovery"):
        service.recover(grant)
    assert calls == [1]


@pytest.mark.parametrize("problem", ["grant", "access", "score", "measurement"])
def test_recovery_record_cannot_change_outer_receipt_identity(tmp_path, problem):
    _, grant, service, _, _ = pending(tmp_path)
    receipt = service.recover(grant)
    if problem == "measurement":
        measured = scoring.ConfirmationMeasurement(
            "utility-confirmation-callback-measurement-v1",
            grant.digest,
            grant.scorer_digest,
            receipt.score.digest,
            1.0,
        )
        with pytest.raises(ValueError, match="invent"):
            replace(receipt, measurement=measured)
    else:
        field = {"grant": "grant_digest", "access": "access_digest", "score": "score_digest"}[
            problem
        ]
        with pytest.raises(ValueError, match="recovery differs"):
            replace(receipt, recovery=replace(receipt.recovery, **{field: "2" * 64}))


@pytest.mark.parametrize(
    "field,value", [("scorer_digest", "2" * 64), ("attempt_id", "confirmation-other")]
)
def test_foreign_recovery_cannot_enter_the_journal(tmp_path, field, value):
    store, grant, service, _, _ = pending(tmp_path)
    receipt = service.recover(grant)
    altered = replace(receipt, recovery=replace(receipt.recovery, **{field: value}))
    ref = put_bytes(
        store.root,
        altered.to_json().encode(),
        name="confirmation-score.json",
        media_type="application/json",
        producer="authored-foreign-recovery",
    )
    attempt = "confirmation-" + grant.cell_digest[:48]
    with pytest.raises(StoreError, match="another scorer or attempt"):
        validate_score(
            store,
            SimpleNamespace(result_digest=ref.sha256, attempt_id=attempt),
            store.replay()["confirmation_accesses"][attempt],
            store.replay()["frozen"],
        )
