"""Public execution bindings with authored metadata, not physical qualification."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.store import StoreError
from autoengineering.utility.costs import join_confirmation_costs
from autoengineering.utility.execution_receipts import ConfirmationContainerExecution
from autoengineering.utility.report import accounting_report
from autoengineering.utility.scoring import validate_score
from test_utility_scoring import setup
from test_utility_confirmation_recovery import SavedScorer, fail_at

H = "1" * 64


def authored(grant, score, seconds=0.25):
    return ConfirmationContainerExecution(
        "utility-confirmation-container-execution-v1",
        grant.digest,
        grant.scorer_digest,
        score.digest,
        H,
        "a" * 64,
        "b" * 32,
        "sha256:" + H,
        H,
        H,
        H,
        H,
        H,
        H,
        1,
        1,
        seconds,
    )


class EvidenceScorer(SavedScorer):
    def __init__(self):
        super().__init__()
        self.exports = 0

    def public_execution(self, grant, model, score):
        self.exports += 1
        return authored(grant, score)


def test_known_physical_starts_and_nested_duration_are_public(tmp_path):
    scorer = EvidenceScorer()
    store, grant, service, _ = setup(tmp_path, scorer)
    receipt = service.confirm(grant)
    assert receipt.execution == authored(grant, receipt.score)
    assert receipt.execution.lifecycle_seconds == 0.25
    costs = {r.resource: r.quantity for r in join_confirmation_costs(store)}
    assert costs["confirmation_scoring_starts"] == 1
    assert costs["confirmation_container_starts"] == 1
    assert costs["confirmation_container_lifecycle_duration"] == 0.25
    assert accounting_report(store)["complete_cost_evidence"] is False
    assert service.confirm(grant) == receipt
    assert scorer.calls == scorer.exports == 1


def test_recovered_execution_retains_known_worker_cost_and_unknown_callback(tmp_path):
    scorer = EvidenceScorer()
    store, grant, service, _ = setup(tmp_path, scorer)
    fail_at(store, "confirmation_score_created")
    with pytest.raises(RuntimeError):
        service.confirm(grant)
    store.fault = lambda _: None
    receipt = service.recover(grant)
    assert receipt.execution == authored(grant, receipt.score)
    assert receipt.measurement is None and receipt.recovery is not None
    costs = {r.resource: r.quantity for r in join_confirmation_costs(store)}
    assert costs["confirmation_scoring_starts"] == costs["confirmation_container_starts"] == 1
    assert costs["confirmation_callback_duration"] is None
    assert costs["confirmation_container_lifecycle_duration"] == 0.25
    assert scorer.calls == 1 and scorer.exports == 2


def test_execution_without_original_timing_does_not_fill_zero(tmp_path):
    scorer = EvidenceScorer()
    scorer.public_execution = lambda grant, model, score: authored(grant, score, None)
    store, grant, service, _ = setup(tmp_path, scorer)
    receipt = service.confirm(grant)
    assert receipt.execution.lifecycle_seconds is None
    costs = {r.resource: r.quantity for r in join_confirmation_costs(store)}
    assert costs["confirmation_container_lifecycle_duration"] is None
    assert costs["confirmation_scoring_starts"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("container_starts", 0),
        ("container_starts", True),
        ("scoring_process_starts", 2),
        ("lifecycle_seconds", True),
        ("lifecycle_seconds", -1.0),
        ("lifecycle_seconds", float("inf")),
        ("container_id", "not-an-id"),
        ("nonce", "not-a-nonce"),
        ("image_id", "latest"),
    ],
)
def test_invalid_or_unknown_start_claims_are_rejected(tmp_path, field, value):
    scorer = EvidenceScorer()
    _, grant, service, _ = setup(tmp_path, scorer)
    receipt = service.confirm(grant)
    with pytest.raises(ValueError):
        replace(receipt.execution, **{field: value})


@pytest.mark.parametrize("field", ["grant_digest", "score_digest", "scorer_digest"])
def test_foreign_execution_cannot_be_published(tmp_path, field):
    scorer = EvidenceScorer()
    scorer.public_execution = lambda grant, model, score: replace(
        authored(grant, score), **{field: "2" * 64}
    )
    store, grant, service, _ = setup(tmp_path, scorer)
    with pytest.raises(StoreError, match="execution evidence unverified"):
        service.confirm(grant)
    state = store.replay()
    assert len(state["confirmation_accesses"]) == 1 and not state["confirmation_scores"]
    assert scorer.calls == 1
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)


def test_private_export_exception_is_sanitized_and_never_starts_again(tmp_path):
    scorer = EvidenceScorer()

    def fail(*_):
        raise RuntimeError("PRIVATE-EXPORT-CANARY")

    scorer.public_execution = fail
    store, grant, service, _ = setup(tmp_path, scorer)
    with pytest.raises(StoreError) as error:
        service.confirm(grant)
    assert "PRIVATE-EXPORT-CANARY" not in str(error.value)
    assert scorer.calls == 1 and not store.replay()["confirmation_scores"]


def test_wrong_scorer_execution_cannot_enter_journal(tmp_path):
    scorer = EvidenceScorer()
    store, grant, service, _ = setup(tmp_path, scorer)
    receipt = service.confirm(grant)
    changed = replace(receipt, execution=replace(receipt.execution, scorer_digest="2" * 64))
    ref = put_bytes(
        store.root,
        changed.to_json().encode(),
        name="confirmation-score.json",
        media_type="application/json",
        producer="authored-foreign-scorer",
    )
    attempt = "confirmation-" + grant.cell_digest[:48]
    with pytest.raises(StoreError, match="execution belongs to another scorer"):
        validate_score(
            store,
            SimpleNamespace(result_digest=ref.sha256),
            store.replay()["confirmation_accesses"][attempt],
            store.replay()["frozen"],
        )
