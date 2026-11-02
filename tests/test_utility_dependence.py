"""Combined decisions require exact public pairs and frozen dependence coverage."""
from dataclasses import replace

import pytest

from autoengineering.utility.analysis import DependentAnalysisPlan, analyze
from autoengineering.utility.dependence import PairedDependenceEvidence, bind_summary
from autoengineering.utility.uncertainty import DependencePlan, BoundScenarioUncertaintySpec, scenario_uncertainty
from test_utility_analysis import fixture
from test_utility_contracts import H


def prepared(*, census=False):
    spec, old, scores = fixture((2., 2., 2.))
    policy = BoundScenarioUncertaintySpec("utility-scenario-uncertainty-v2", "task", "W", "minimize",
        ("low", "high"), "fixed_scenario_census" if census else "iid_paired_scenario_bootstrap",
        "fixed_design_cases" if census else "independent_scenario_sample", H, 500, .999, 17, spec.tasks[0].partition_digest)
    dependence = DependencePlan("utility-dependence-v1", (), (policy,))
    plan = DependentAnalysisPlan("utility-analysis-v2", old.contrasts, old.missing_policy, dependence.digest)
    spec = replace(spec, analysis_digest=plan.digest)
    by_cell = {cell.digest: cell for cell in spec.cells}
    evidence = []
    for route in scores:
        cell = by_cell[route.cell_digest]
        if cell.route_id != "multi":
            continue
        comparator = next(s for s in scores if by_cell[s.cell_digest].pair_key == cell.pair_key
                          and by_cell[s.cell_digest].route_id == "conventional")
        summary = scenario_uncertainty(policy, [8., 8.], [10., 10.], scenario_ids=policy.scenario_ids)
        evidence.append(bind_summary(policy, route, comparator, summary))
    return spec, plan, scores, dependence, tuple(evidence)


def evaluate(inputs):
    spec, plan, scores, dependence, evidence = inputs
    return analyze(spec, plan, scores, dependence=dependence, dependence_evidence=evidence)["contrasts"][0]


def test_complete_combined_evidence_supports_gain_and_preserves_separate_intervals():
    inputs = prepared()
    result = evaluate(inputs)
    assert result["verdict"] == "scientific_gain_supported"
    assert result["dependence_complete"] is True
    assert len(result["dependence_evidence"]) == 3
    assert result["interval"] == [2., 2.]
    spec, plan, scores, dependence, evidence = inputs
    assert DependencePlan.from_json(dependence.to_json()) == dependence
    assert DependentAnalysisPlan.from_json(plan.to_json()) == plan
    assert PairedDependenceEvidence.from_json(evidence[0].to_json()) == evidence[0]
    assert analyze(spec, plan, scores)["contrasts"][0]["verdict"] == "inconclusive"


def test_missing_wide_or_insufficient_dependence_cannot_support_gain():
    spec, plan, scores, dependence, evidence = prepared()
    for changed in (evidence[:-1], (replace(evidence[0], interval=(-1., 4.)), *evidence[1:]),
                    (replace(evidence[0], status="insufficient_data", interval=None), *evidence[1:])):
        assert evaluate((spec, plan, scores, dependence, changed))["verdict"] == "inconclusive"


@pytest.mark.parametrize("change,match", [
    ({"route_score_digest": "2"*64}, "exact successful"),
    ({"policy_digest": "2"*64}, "policy or units"),
    ({"gain": 4.}, "gain differs"),
    ({"status": "finite_scenario_summary", "interval": None}, "frozen scenario census"),
])
def test_altered_receipt_or_semantics_reject(change, match):
    spec, plan, scores, dependence, evidence = prepared()
    with pytest.raises(ValueError, match=match):
        evaluate((spec, plan, scores, dependence, (replace(evidence[0], **change), *evidence[1:])))


def test_duplicate_unpaired_and_insufficient_family_confidence_reject():
    spec, plan, scores, dependence, evidence = prepared()
    with pytest.raises(ValueError, match="duplicate paired"):
        evaluate((spec, plan, scores, dependence, (*evidence, evidence[0])))
    altered = replace(evidence[0], comparator_cell_digest=evidence[1].comparator_cell_digest)
    with pytest.raises(ValueError, match="repetition/scenario pair"):
        evaluate((spec, plan, scores, dependence, (altered, *evidence[1:])))
    lower = replace(dependence.scenarios[0], confidence=.95)
    changed = replace(dependence, scenarios=(lower,))
    changed_plan = replace(plan, dependence_policy_digest=changed.digest)
    changed_spec = replace(spec, analysis_digest=changed_plan.digest)
    with pytest.raises(ValueError, match="decision family"):
        evaluate((changed_spec, changed_plan, scores, changed,
                  tuple(replace(e, policy_digest=lower.digest) for e in evidence)))


def test_census_gain_is_limited_to_frozen_cases_without_population_interval():
    result = evaluate(prepared(census=True))
    assert result["verdict"] == "scientific_gain_supported"
    assert result["scientific_claim_scope"] == "frozen finite scenarios"
    assert all(item["interval"] is None for item in result["dependence_evidence"])


def test_changed_policy_rejects_and_v1_cannot_silently_gain_new_decision_rule():
    spec, plan, scores, dependence, evidence = prepared()
    with pytest.raises(ValueError, match="frozen analysis"):
        evaluate((spec, plan, scores, replace(dependence, scenarios=(replace(dependence.scenarios[0], seed=18),)), evidence))
    from autoengineering.utility.analysis import AnalysisPlan
    old = AnalysisPlan("utility-analysis-v1", plan.contrasts, plan.missing_policy, dependence.digest)
    with pytest.raises(ValueError, match="utility-analysis-v2"):
        evaluate((replace(spec, analysis_digest=old.digest), old, scores, dependence, evidence))


def test_prediction_policy_partition_and_units_are_bound_to_public_scores():
    import numpy as np
    from autoengineering.utility.uncertainty import prediction_uncertainty
    from test_utility_uncertainty import inputs
    spec, old, scores = fixture((2., 2., 2.))
    policy, support = inputs()
    policy = replace(policy, task_id="task", units="W", confidence=.999,
                     partition_digest=spec.tasks[0].partition_digest)
    dependence = DependencePlan("utility-dependence-v1", (policy,))
    contrast = replace(old.contrasts[0], outcome="rmse")
    plan = DependentAnalysisPlan("utility-analysis-v2", (contrast,), old.missing_policy, dependence.digest)
    spec = replace(spec, analysis_digest=plan.digest)
    scores = tuple(replace(s, outcome="rmse") for s in scores)
    by_cell = {cell.digest: cell for cell in spec.cells}
    evidence = []
    for route in scores:
        if by_cell[route.cell_digest].route_id != "multi":
            continue
        comparator = next(s for s in scores if by_cell[s.cell_digest].pair_key == by_cell[route.cell_digest].pair_key
                          and by_cell[s.cell_digest].route_id == "conventional")
        summary = prediction_uncertainty(policy, np.zeros(12), np.full(12, 8.), np.full(12, 10.), **support)
        evidence.append(bind_summary(policy, route, comparator, summary))
    assert evaluate((spec, plan, scores, dependence, tuple(evidence)))["verdict"] == "scientific_gain_supported"
    wrong = replace(policy, partition_digest="2"*64)
    changed = replace(dependence, tasks=(wrong,))
    plan = replace(plan, dependence_policy_digest=changed.digest)
    spec = replace(spec, analysis_digest=plan.digest)
    with pytest.raises(ValueError, match="partition differs"):
        evaluate((spec, plan, scores, changed, tuple(replace(e, policy_digest=wrong.digest) for e in evidence)))


def test_offline_reader_verifies_dependence_artifact_bytes_without_resampling(tmp_path, monkeypatch):
    from autoengineering.campaign.artifacts import put_bytes
    from autoengineering.campaign.serialization import canonical_json
    from autoengineering.campaign.store import EventStore
    from autoengineering.utility.analysis import analyze_receipts
    from autoengineering.utility import uncertainty
    spec, plan, scores, dependence, evidence = prepared()
    root = EventStore.create(tmp_path / "public").root
    score_refs, identities = [], {}
    for score in scores:
        document = score.to_dict()
        document.pop("score_digest")
        ref = put_bytes(root, canonical_json({"schema": "utility-public-score-v1",
            "suite_digest": spec.digest, "score": document}).encode(), name="score.json",
            media_type="application/json", producer="authored-test-fixture")
        identities[score.score_digest] = ref.sha256
        score_refs.append(ref)
    refs = tuple(put_bytes(root, replace(e, route_score_digest=identities[e.route_score_digest],
        comparator_score_digest=identities[e.comparator_score_digest]).to_json().encode(),
        name="dependence.json", media_type="application/json", producer="authored-test-fixture") for e in evidence)

    def forbidden(*args, **kwargs):
        raise AssertionError("offline reader must not invoke a custodian resampler")

    monkeypatch.setattr(uncertainty, "scenario_uncertainty", forbidden)
    monkeypatch.setattr(uncertainty, "prediction_uncertainty", forbidden)
    report = analyze_receipts(spec, plan, root, tuple(score_refs), dependence=dependence, dependence_references=refs)
    assert report["contrasts"][0]["verdict"] == "scientific_gain_supported"
    assert len(report["dependence_references"]) == 3
    (root / refs[0].path).write_text("tampered")
    with pytest.raises(ValueError):
        analyze_receipts(spec, plan, root, tuple(score_refs), dependence=dependence, dependence_references=refs)



def test_small_and_adverse_gains_do_not_become_equivalence_claims():
    spec, plan, scores, dependence, evidence = prepared()
    scores = tuple(replace(s, value=10.) for s in scores)
    evidence = tuple(replace(e, gain=0., interval=(0., 0.)) for e in evidence)
    result = evaluate((spec, plan, scores, dependence, evidence))
    assert result["verdict"] == "no_useful_gain_demonstrated"
    assert result["mean_gain"] == 0.


def test_legacy_analysis_serialization_keeps_exact_original_fields():
    from autoengineering.utility.analysis import AnalysisPlan
    spec, plan, scores = fixture()
    assert set(plan.to_dict()) == {"schema", "contrasts", "missing_policy", "dependence_policy_digest"}
    assert AnalysisPlan.from_json(plan.to_json()).digest == plan.digest



def test_scenario_interval_cannot_substitute_another_forcing_partition():
    spec, plan, scores, dependence, evidence = prepared()
    changed_policy = replace(dependence.scenarios[0], partition_digest="2"*64)
    changed = replace(dependence, scenarios=(changed_policy,))
    plan = replace(plan, dependence_policy_digest=changed.digest)
    spec = replace(spec, analysis_digest=plan.digest)
    with pytest.raises(ValueError, match="frozen partition identity"):
        evaluate((spec, plan, scores, changed,
                  tuple(replace(e, policy_digest=changed_policy.digest) for e in evidence)))
