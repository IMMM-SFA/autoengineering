"""Analytic paired effects and full-denominator failure accounting."""
from dataclasses import replace

import numpy as np
import pytest
from scipy.stats import t

from autoengineering.campaign.serialization import digest
from autoengineering.utility.analysis import AnalysisPlan, ContrastSpec, ScoredCell, analyze
from test_utility_contracts import H, suite


def fixture(values=(1., 2., 3.)):
    contrast = ContrastSpec("task", "multi", "conventional", "power", "W", "minimize", .1,
                            1., .95, "paired_student_t", 500, 17, "single_prespecified")
    plan = AnalysisPlan("utility-analysis-v1", (contrast,),
                        "complete_pairs_and_full_denominators", H)
    spec = replace(suite(len(values)), analysis_digest=plan.digest)
    scores = tuple(ScoredCell(cell.digest, digest({"cell": cell.digest}), "success", "power", "W",
                              10.-values[cell.repetition] if cell.route_id == "multi" else 10.,
                              True, 1., False) for cell in spec.cells)
    return spec, plan, scores


def test_known_paired_student_interval_and_no_global_score():
    spec, plan, scores = fixture()
    report = analyze(spec, plan, scores)
    result = report["contrasts"][0]
    radius = t.ppf(.975, 2)/np.sqrt(3)
    np.testing.assert_allclose(result["interval"], [2-radius, 2+radius])
    assert result["mean_gain"] == 2
    assert result["assigned_pairs"] == result["valid_pairs"] == 3
    assert report["global_scientific_score"] is None
    assert result["verdict"] == "inconclusive"
    assert result["repetition_verdict"] == "inconclusive"
    assert result["route_counts"]["multi"]["target_censored"] == 3


def test_missing_and_failed_pairs_remain_in_denominator():
    spec, plan, scores = fixture((2., 2., 2.))
    scores = (replace(scores[0], status="timeout", value=None, feasible=None), *scores[1:-1])
    result = analyze(spec, plan, scores)["contrasts"][0]
    assert result["assigned_pairs"] == 3
    assert result["valid_pairs"] == 1
    assert result["verdict"] == "inconclusive"
    assert result["route_counts"]["conventional"]["statuses"]["timeout"] == 1
    assert result["route_counts"]["multi"]["statuses"]["missing_evidence"] == 1


def test_gain_supported_only_with_complete_feasible_pairs():
    spec, plan, scores = fixture((2., 2., 2.))
    result = analyze(spec, plan, scores)["contrasts"][0]
    assert result["verdict"] == "inconclusive"
    assert result["repetition_verdict"] == "scientific_gain_supported"
    result = analyze(spec, plan, scores[:2])["contrasts"][0]
    assert result["verdict"] == "inconclusive"


def test_duplicate_score_references_and_units_reject():
    spec, plan, scores = fixture()
    with pytest.raises(ValueError, match="duplicate physical"):
        analyze(spec, plan, (scores[0], replace(scores[1], score_digest=scores[0].score_digest)))
    with pytest.raises(ValueError, match="units"):
        analyze(spec, plan, (replace(scores[0], units="GWh"), *scores[1:]))
    with pytest.raises(ValueError, match="frozen"):
        analyze(spec, replace(plan, dependence_policy_digest="2" * 64), scores)


def test_seeded_bootstrap_and_small_sample():
    spec, plan, scores = fixture((2., 2., 2.))
    plan = replace(plan, contrasts=(replace(plan.contrasts[0], interval="paired_percentile_bootstrap"),))
    spec = replace(spec, analysis_digest=plan.digest)
    report = analyze(spec, plan, scores)
    assert report == analyze(spec, plan, scores)
    assert report["contrasts"][0]["interval"] == [2., 2.]
    spec, plan, scores = fixture((5.,))
    result = analyze(spec, plan, scores)["contrasts"][0]
    assert result["interval"] is None and result["verdict"] == "inconclusive"


def test_complete_evidence_of_failed_feasibility_remains_failure():
    spec, plan, scores = fixture((2., 2., 2.))
    scores = tuple(replace(s, feasible=False) if i == 1 else s for i, s in enumerate(scores))
    result = analyze(spec, plan, scores)["contrasts"][0]
    assert result["verdict"] == "failed_confirmation"
    assert result["valid_pairs"] == 2
    assert result["successful_feasible_rates"]["multi"] == 2/3


def test_pinned_public_receipt_reader_reconstructs_and_rejects_tampering(tmp_path):
    from autoengineering.campaign.artifacts import put_bytes
    from autoengineering.campaign.serialization import canonical_json
    from autoengineering.campaign.store import EventStore
    from autoengineering.utility.analysis import analyze_receipts
    root = EventStore.create(tmp_path / "evidence").root
    spec, plan, scores = fixture((2., 2., 2.))
    refs = []
    for score in scores:
        document = score.to_dict()
        document.pop("score_digest")
        raw = canonical_json({"schema": "utility-public-score-v1", "suite_digest": spec.digest,
                              "score": document}).encode()
        refs.append(put_bytes(root, raw, name="score.json", media_type="application/json",
                              producer="authored-test-fixture"))
    report = analyze_receipts(spec, plan, root, tuple(refs))
    assert report["contrasts"][0]["mean_gain"] == 2.
    assert len(report["score_references"]) == 6
    with pytest.raises(ValueError, match="unique assigned cell"):
        analyze_receipts(spec, plan, root, (refs[0], refs[0]))
    (root / refs[0].path).write_text("tampered")
    with pytest.raises(ValueError):
        analyze_receipts(spec, plan, root, tuple(refs))
