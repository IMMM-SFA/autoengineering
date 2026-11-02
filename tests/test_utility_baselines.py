"""Baseline reuse is explicit and does not duplicate physical evidence/cost."""
from dataclasses import replace

import pytest

from autoengineering.campaign.serialization import digest
from autoengineering.utility.analysis import analyze
from autoengineering.utility.baselines import SharedBaseline
from autoengineering.utility.costs import CostRecord, reconcile
from test_utility_analysis import fixture
from test_utility_contracts import H


def shared_fixture():
    spec, plan, scores = fixture((2., 2., 2.))
    routes = tuple(replace(route, kind="baseline") if route.route_id == "conventional" else route
                   for route in spec.routes)
    spec = replace(spec, routes=routes)
    scores = tuple(replace(score, score_digest=H) if cell.route_id == "conventional" else score
                   for cell, score in zip(spec.cells, scores))
    cells = tuple(s.cell_digest for s in scores if s.score_digest == H)
    allocation = SharedBaseline(H, cells, (1/3, 1/3, 1/3))
    return spec, plan, scores, allocation


def frozen_shared_fixture():
    from autoengineering.utility.contracts import BaselineReuseGroup, BaselineReusePolicy

    spec, plan, scores, allocation = shared_fixture()
    group = BaselineReuseGroup(allocation.cell_digests, allocation.cell_digests[0],
                              H, H, H, allocation.allocation)
    policy = BaselineReusePolicy("utility-baseline-reuse-v1", spec.protocol_digest, (group,))
    spec = replace(spec, schema="utility-suite-v2", baseline_reuse=policy,
                   protocol_digest=policy.digest)
    return spec, plan, scores, allocation


def test_direct_analysis_respects_frozen_baseline_allocation():
    spec, plan, scores, allocation = frozen_shared_fixture()
    assert analyze(spec, plan, scores, shared_baselines=(allocation,))["scored_cells"] == 6
    with pytest.raises(ValueError, match="frozen baseline"):
        analyze(spec, plan, scores, shared_baselines=(replace(
            allocation, allocation=(.5, .25, .25)),))
    with pytest.raises(ValueError, match="frozen baseline"):
        analyze(spec, plan, scores[:4], shared_baselines=(replace(
            allocation, cell_digests=allocation.cell_digests[:2], allocation=(.5, .5)),))


def test_direct_analysis_leaves_failed_baseline_followers_unscored():
    spec, plan, scores, allocation = frozen_shared_fixture()
    failed = tuple(replace(score, status="timeout", value=None, feasible=None)
                   if score.score_digest == H else score for score in scores)
    with pytest.raises(ValueError, match="successful feasible"):
        analyze(spec, plan, failed, shared_baselines=(allocation,))
    independent = tuple(replace(score, score_digest=digest({"cell": score.cell_digest}))
                        if score.score_digest == H else score for score in scores)
    with pytest.raises(ValueError, match="frozen baseline follower"):
        analyze(spec, plan, independent)
    source_only = tuple(score for score in failed
                        if score.cell_digest not in allocation.cell_digests[1:])
    report = analyze(spec, plan, source_only)
    assert report["scored_cells"] == 4
    assert report["contrasts"][0]["valid_pairs"] == 0


def test_shared_reference_retains_logical_denominators_and_one_physical_receipt():
    spec, plan, scores, allocation = shared_fixture()
    report = analyze(spec, plan, scores, shared_baselines=(allocation,))
    assert report["scored_cells"] == 6
    assert report["physical_score_receipts"] == 4
    assert report["contrasts"][0]["assigned_pairs"] == 3
    assert report["contrasts"][0]["mean_gain"] == 2.
    assert SharedBaseline.from_json(allocation.to_json()) == allocation
    cost = CostRecord("one-baseline", H, "reference", "scientific_starts", "count", 1,
                      (allocation.cell_digests[0],), (1.,))
    cost = allocation.allocate_cost(cost)
    assert reconcile((cost,), (cost.receipt_id,))["known_totals"][0]["quantity"] == 1


def test_reuse_without_declaration_or_with_changed_value_rejects():
    spec, plan, scores, allocation = shared_fixture()
    with pytest.raises(ValueError, match="duplicate physical"):
        analyze(spec, plan, scores)
    changed = (replace(scores[0], value=11.), *scores[1:])
    with pytest.raises(ValueError, match="one unchanged"):
        analyze(spec, plan, changed, shared_baselines=(allocation,))
    with pytest.raises(ValueError, match="every referenced"):
        analyze(spec, plan, scores, shared_baselines=(replace(allocation,
            cell_digests=allocation.cell_digests[:1], allocation=(1.,)),))


def test_adaptive_work_cannot_be_reclassified_as_a_shared_baseline():
    spec, plan, scores, allocation = shared_fixture()
    spec = replace(spec, routes=tuple(replace(r, kind="conventional") for r in spec.routes))
    with pytest.raises(ValueError, match="unchanged-baseline"):
        analyze(spec, plan, scores, shared_baselines=(allocation,))
    with pytest.raises(ValueError, match="sum to one"):
        replace(allocation, allocation=(1., 1., 1.))
    cost = CostRecord("wrong-source", digest({"other": 1}), "reference", "scientific_starts", "count", 1,
                      (allocation.cell_digests[0],), (1.,))
    with pytest.raises(ValueError, match="physical score evidence"):
        allocation.allocate_cost(cost)


@pytest.mark.parametrize("frozen,tamper", [(False, False), (True, False), (True, True)])
def test_shared_public_receipt_expands_without_rescoring(tmp_path, frozen, tamper):
    from autoengineering.campaign.artifacts import put_bytes
    from autoengineering.campaign.serialization import canonical_json
    from autoengineering.campaign.store import EventStore
    from autoengineering.utility.analysis import analyze_receipts
    spec, plan, scores, allocation = frozen_shared_fixture() if frozen else shared_fixture()
    if tamper:
        allocation = replace(allocation, allocation=(.5, .25, .25))
    root = EventStore.create(tmp_path / "evidence").root
    shared = next(s for s in scores if s.score_digest == H).to_dict()
    shared.pop("cell_digest")
    shared.pop("score_digest")
    declaration = allocation.to_dict()
    declaration.pop("score_digest")
    refs = [put_bytes(root, canonical_json({"schema": "utility-shared-baseline-v1",
                    "suite_digest": spec.digest, "score": shared, "allocation": declaration}).encode(),
                      name="baseline.json", media_type="application/json", producer="synthetic")]
    for score in scores:
        if score.score_digest == H:
            continue
        payload = score.to_dict()
        payload.pop("score_digest")
        refs.append(put_bytes(root, canonical_json({"schema": "utility-public-score-v1",
                    "suite_digest": spec.digest, "score": payload}).encode(), name="score.json",
                    media_type="application/json", producer="synthetic"))
    if tamper:
        with pytest.raises(ValueError, match="frozen baseline"):
            analyze_receipts(spec, plan, root, refs)
        return
    report = analyze_receipts(spec, plan, root, refs)
    assert report["physical_score_receipts"] == 4 and report["scored_cells"] == 6
    assert report["contrasts"][0]["valid_pairs"] == 3
    assert len(report["score_references"]) == 4


def test_analysis_cannot_bypass_selection_barrier(tmp_path):
    from autoengineering.utility.analysis import analyze_confirmation
    from autoengineering.utility.store import SuiteStore
    spec, plan, _, _ = shared_fixture()
    store = SuiteStore.create(tmp_path / "suite", spec)
    with pytest.raises(ValueError, match="selection barrier"):
        analyze_confirmation(store, plan)


def test_baseline_model_match_is_insufficient_when_parameter_states_differ():
    from autoengineering.campaign.records import ArtifactRef
    from autoengineering.utility.confirmation import SelectedCell
    _, _, _, allocation = shared_fixture()
    model = ArtifactRef("model.json", H, 1, "application/json", "fixture", {})
    state = ArtifactRef("state.json", H, 1, "application/json", "fixture", {})
    selections = {cell: SelectedCell(cell, "selected", "attempt", H, model, "Fixture", state)
                  for cell in allocation.cell_digests}
    allocation.validate_selections(selections)
    cell = allocation.cell_digests[-1]
    selections[cell] = replace(selections[cell], selected_state=replace(state, sha256="2" * 64))
    with pytest.raises(ValueError, match="parameter state"):
        allocation.validate_selections(selections)
