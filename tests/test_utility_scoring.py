"""Synthetic private scorer accounting, not real data-custody qualification."""
from dataclasses import replace

import pytest

from autoengineering.campaign.store import StoreError
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService, PublicScore
from autoengineering.utility.store import SuiteStore
from test_utility_confirmation import selected_suite
from test_utility_contracts import H


def setup(tmp_path, scorer, *, analysis_plan=None):
    store, manifest, contract = selected_suite(tmp_path, analysis_plan=analysis_plan)
    selected = manifest.cells[0]
    grant = ConfirmationGrant(store.spec.digest, selected.cell_digest,
        store.spec.tasks[0].partition_digest, H, contract.digest, selected.model.sha256,
        store.replay()["frozen"], (ResourceCap("scientific_starts", "count", 1, "reservation"),))
    service = ConfirmationService(store, scorer, scorer_digest=H, outcome_contract=contract)
    return store, grant, service, contract


def test_saved_score_replays_without_private_scorer(tmp_path):
    calls = []

    def scorer(grant, model):
        calls.append(1)
        return PublicScore("success", "power", "W", 3., True)

    store, grant, service, contract = setup(tmp_path, scorer)
    receipt = service.confirm(grant)
    assert receipt.score.value == 3
    assert calls == [1]
    resumed = ConfirmationService(SuiteStore(store.root), lambda *_: pytest.fail("must not rescore"),
                                  scorer_digest=H, outcome_contract=contract)
    assert resumed.confirm(grant) == receipt
    assert calls == [1]
    assert store.replay()["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")] == 1


@pytest.mark.parametrize("boundary,resumable", [("confirmation_access_committed", False),
                                                ("confirmation_score_created", False),
                                                ("confirmation_score_committed", True)])
def test_confirmation_interruption_never_restarts_scorer(tmp_path, boundary, resumable):
    calls = []

    def scorer(*args):
        calls.append(1)
        return PublicScore("success", "power", "W", 3., True)

    store, grant, service, contract = setup(tmp_path, scorer)

    def fail(stage):
        if stage == boundary:
            raise RuntimeError("interrupted")

    store.fault = fail
    with pytest.raises(RuntimeError):
        service.confirm(grant)
    resumed = ConfirmationService(SuiteStore(store.root), lambda *_: pytest.fail("never retry"),
                                  scorer_digest=H, outcome_contract=contract)
    if resumable:
        assert resumed.confirm(grant).score.value == 3
    else:
        with pytest.raises(StoreError, match="uncertain"):
            resumed.confirm(grant)
    assert len(calls) == (0 if boundary == "confirmation_access_committed" else 1)
    assert len(store.replay()["confirmation_accesses"]) == 1


def test_private_exception_is_sanitized_and_charge_retained(tmp_path):
    def scorer(*args):
        raise RuntimeError("PRIVATE-LABEL-CANARY")

    store, grant, service, _ = setup(tmp_path, scorer)
    with pytest.raises(StoreError) as error:
        service.confirm(grant)
    assert "PRIVATE-LABEL-CANARY" not in str(error.value)
    assert store.replay()["confirmation_accesses"]
    with pytest.raises(StoreError, match="uncertain"):
        service.confirm(grant)


def test_stale_data_grant_and_wrong_public_units_reject(tmp_path):
    store, grant, service, _ = setup(tmp_path, lambda *_: PublicScore("success", "power", "kW", 3., True))
    with pytest.raises(StoreError, match="data/outcome"):
        service.confirm(replace(grant, partition_digest="2" * 64))
    with pytest.raises(ValueError, match="semantics"):
        service.confirm(grant)
    assert len(store.replay()["confirmation_accesses"]) == 1


def test_public_reporting_reads_saved_confirmation_without_scorer(tmp_path):
    from autoengineering.utility.report import accounting_report
    store, grant, service, _ = setup(tmp_path, lambda *_: PublicScore("success", "power", "W", 3., True))
    service.confirm(grant)
    report = accounting_report(SuiteStore(store.root))
    assert report["evidence_blockers"] == []
    assert report["confirmation_state"] == "scored_unanalyzed"
    assert len(report["confirmation_receipts"]) == 1
    assert report["utility_verdict"] == "not_attempted"


def test_committed_confirmation_analysis_uses_no_scorer_and_retains_missing_pair(tmp_path):
    from autoengineering.utility.analysis import AnalysisPlan, ContrastSpec, analyze_confirmation
    contrast = ContrastSpec("task", "multi", "conventional", "power", "W", "minimize", .1,
                            1., .95, "paired_student_t", 500, 17, "single_prespecified")
    plan = AnalysisPlan("utility-analysis-v1", (contrast,),
                        "complete_pairs_and_full_denominators", H)
    calls = []

    def scorer(*args):
        calls.append(1)
        return PublicScore("success", "power", "W", 3., True)

    store, grant, service, _ = setup(tmp_path, scorer, analysis_plan=plan)
    service.confirm(grant)
    result = analyze_confirmation(SuiteStore(store.root), plan)
    assert calls == [1]
    assert result["assigned_cells"] == 2 and result["physical_score_receipts"] == 1
    assert result["contrasts"][0]["verdict"] == "inconclusive"
    assert result["contrasts"][0]["missing_pairs"] == 1
