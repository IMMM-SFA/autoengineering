"""Baseline reuse cannot replace different scenarios or hide charged work."""

from dataclasses import replace

import pytest

from autoengineering.utility.analysis import analyze, analyze_confirmation
from autoengineering.utility.baselines import SharedBaseline
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService, PublicScore
from test_utility_analysis import fixture
from test_utility_baselines import shared_fixture
from test_utility_confirmation import selected_suite
from test_utility_contracts import H


def test_shared_baseline_cannot_cross_scenario_identity():
    spec, plan, scores, allocation = shared_fixture()
    changed = tuple(
        replace(c, scenario_digest="2" * 64) if c.repetition == 1 else c for c in spec.cells
    )
    scores = tuple(replace(s, cell_digest=c.digest) for s, c in zip(scores, changed))
    spec = replace(spec, cells=changed)
    allocation = replace(
        allocation, cell_digests=tuple(s.cell_digest for s in scores if s.score_digest == H)
    )
    with pytest.raises(ValueError, match="scenario"):
        analyze(spec, plan, scores, shared_baselines=(allocation,))


def committed_baseline(tmp_path):
    plan = fixture((2.0,))[1]
    store, manifest, contract = selected_suite(
        tmp_path, analysis_plan=plan, all_selected=True, baseline_routes=True
    )
    calls = []

    def scorer(*_):
        calls.append(1)
        return PublicScore("success", "power", "W", 3.0, True)

    grants = tuple(
        ConfirmationGrant(
            store.spec.digest,
            c.cell_digest,
            store.spec.tasks[0].partition_digest,
            H,
            contract.digest,
            c.model.sha256,
            store.replay()["frozen"],
            (ResourceCap("scientific_starts", "count", 1, "reservation"),),
        )
        for c in manifest.cells
    )
    service = ConfirmationService(store, scorer, scorer_digest=H, outcome_contract=contract)
    service.confirm(grants[0])
    identity = next(iter(store.replay()["confirmation_scores"].values()))
    allocation = SharedBaseline(identity, tuple(c.cell_digest for c in manifest.cells), (0.5, 0.5))
    return store, plan, grants, service, allocation, calls


def test_never_attempted_identical_reference_still_reuses_without_scoring(tmp_path):
    store, plan, _, _, allocation, calls = committed_baseline(tmp_path)
    before = store.replay()
    report = analyze_confirmation(store, plan, shared_baselines=(allocation,))
    assert report["scored_cells"] == 2 and report["physical_score_receipts"] == 1
    assert calls == [1]
    assert store.replay()["head"] == before["head"]


@pytest.mark.parametrize("phase", ["reserved", "started", "scored"])
def test_reference_cannot_hide_any_original_confirmation_charge(tmp_path, phase):
    store, plan, grants, service, allocation, calls = committed_baseline(tmp_path)
    target = grants[1]
    if phase == "reserved":
        with store.writer():
            store.append(
                request_id="authored-reserve",
                operation="reserve",
                attempt_id="confirmation-" + target.cell_digest[:48],
                cell_digest=target.cell_digest,
                child_digest=target.digest,
                resources=target.resources,
                phase="confirmation",
            )
    elif phase == "started":

        def fault(point):
            if point == "confirmation_access_committed":
                raise RuntimeError("authored interruption before callback")

        store.fault = fault
        with pytest.raises(RuntimeError):
            service.confirm(target)
        store.fault = lambda _: None
    else:
        service.confirm(target)
    before = store.replay()
    with pytest.raises(ValueError):
        analyze_confirmation(store, plan, shared_baselines=(allocation,))
    after = store.replay()
    assert after["head"] == before["head"] and after["used"] == before["used"]
    assert len(calls) == (2 if phase == "scored" else 1)
