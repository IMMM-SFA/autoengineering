"""Human scope coverage, original time records and frozen effort decisions."""
from dataclasses import replace

import pytest

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.store import EventStore
from autoengineering.utility.analysis import EffortAnalysisPlan, EffortCriterion, analyze, read_analysis_plan
from autoengineering.utility.effort import (
    EffortScope, EffortPlan, HumanTimeSource, HumanTimeLog, EffortClosure, EffortInputs,
    read_effort, analyze_effort,
)
from test_utility_dependence import prepared
from test_utility_contracts import H


def put(root, record, name="effort.json"):
    return put_bytes(root, record.to_json().encode(), name=name,
                     media_type="application/json", producer="authored-human-log-fixture")


def fixture(tmp_path, *, multi_seconds=10., comparator_seconds=30.):
    spec, old, scores, dependence, evidence = prepared()
    # Scientific equality, rather than scientific improvement, for noninferiority.
    scores = tuple(replace(s, value=10.) for s in scores)
    evidence = tuple(replace(e, gain=0., interval=(0., 0.)) for e in evidence)
    cells = tuple(c.digest for c in spec.cells)
    scopes = (EffortScope("common", "preparation", "common_setup", cells, (1/len(cells),)*len(cells)),
              *(EffortScope("work-"+str(i), "selection", "route_work", (cell,), (1.,)) for i, cell in enumerate(cells)))
    policy = EffortPlan("utility-effort-policy-v1", scopes, ("timer",), 10, "first_use")
    plan = EffortAnalysisPlan("utility-analysis-v3", old.contrasts, old.missing_policy, dependence.digest,
        effort_policy_digest=policy.digest, effort_criteria=(EffortCriterion("task", "multi", "conventional", .05, 10.),))
    spec = replace(spec, analysis_digest=plan.digest)
    root = EventStore.create(tmp_path / "public").root
    closures, logs = [], []
    start = 1000.
    for index, scope in enumerate(scopes):
        seconds = 120. if index == 0 else (multi_seconds if spec.cells[index-1].route_id == "multi" else comparator_seconds)
        source = HumanTimeSource("utility-human-time-source-v1", "log-"+str(index), H, "setup" if index == 0 else "review",
                                 "timer", start, start+seconds)
        source_ref = put(root, source)
        log = HumanTimeLog(**(source.to_dict() | {"schema": "utility-human-time-v1",
            "scope_id": scope.scope_id, "evidence": source_ref}))
        log_ref = put(root, log)
        logs.append((log, log_ref))
        closure = EffortClosure("utility-effort-closure-v1", scope.scope_id, "closed", (log_ref,), source_ref)
        closures.append(put(root, closure))
        start += seconds
    inputs = EffortInputs("utility-effort-inputs-v1", put(root, policy), tuple(closures))
    scientific = analyze(spec, plan, scores, dependence=dependence, dependence_evidence=evidence)
    return spec, plan, root, inputs, scientific, logs


def test_scoped_totals_share_setup_once_and_report_amortization_separately(tmp_path):
    spec, plan, root, inputs, scientific, logs = fixture(tmp_path)
    effort = read_effort(spec, root, inputs, policy_digest=plan.effort_policy_digest)
    assert effort["declared_scopes_complete"] is True
    assert effort["source_log_count"] == 7
    assert sum(v["first_use_seconds"] for v in effort["cells"].values()) == 240.
    assert sum(v["amortized_seconds"] for v in effort["cells"].values()) == 132.
    assert effort["complete_physical_cost_evidence"] is False
    result = analyze_effort(spec, plan, scientific, effort)["contrasts"][0]
    assert result["verdict"] == "no_useful_gain_demonstrated"
    assert result["efficiency_verdict"] == "efficiency_gain_supported"
    assert result["efficiency_basis"] == "declared_logged_human_effort"
    assert result["effort"]["mean_seconds_saved"] == 20.
    assert result["effort"]["interval"] == [20., 20.]
    assert read_analysis_plan(plan.to_json()) == plan
    assert EffortInputs.from_json(inputs.to_json()) == inputs


def test_missing_scope_and_unknown_time_do_not_become_zero(tmp_path):
    spec, plan, root, inputs, scientific, logs = fixture(tmp_path)
    missing = read_effort(spec, root, replace(inputs, closures=inputs.closures[:-1]), policy_digest=plan.effort_policy_digest)
    assert not missing["declared_scopes_complete"] and missing["missing_scopes"]
    assert any(v["first_use_seconds"] is None for v in missing["cells"].values())
    assert analyze_effort(spec, plan, scientific, missing)["contrasts"][0]["efficiency_verdict"] == "inconclusive"
    source = HumanTimeSource("utility-human-time-source-v1", "log-0", H, "setup", "unknown", None, None)
    log = HumanTimeLog(**(source.to_dict() | {"schema":"utility-human-time-v1", "scope_id":"common", "evidence":put(root, source)}))
    closure = EffortClosure("utility-effort-closure-v1", "common", "closed", (put(root, log),), log.evidence)
    changed = replace(inputs, closures=(put(root, closure), *inputs.closures[1:]))
    unknown = read_effort(spec, root, changed, policy_digest=plan.effort_policy_digest)
    assert all(v["first_use_seconds"] is None for v in unknown["cells"].values())
    assert all(v["unknown_logs"] == 1 for v in unknown["cells"].values())


def test_tampered_original_and_overlapping_actor_time_reject(tmp_path):
    spec, plan, root, inputs, scientific, logs = fixture(tmp_path)
    log, _ = logs[1]
    altered = replace(log, started_at=1000., ended_at=1010.)
    closure = EffortClosure("utility-effort-closure-v1", log.scope_id, "closed", (put(root, altered),), log.evidence)
    changed = replace(inputs, closures=(inputs.closures[0], put(root, closure), *inputs.closures[2:]))
    with pytest.raises(ValueError, match="original source"):
        read_effort(spec, root, changed, policy_digest=plan.effort_policy_digest)
    source = HumanTimeSource("utility-human-time-source-v1", log.log_id, H, log.activity, "timer", 1000., 1010.)
    altered = replace(altered, evidence=put(root, source))
    closure = replace(closure, logs=(put(root, altered),), evidence=altered.evidence)
    with pytest.raises(ValueError, match="overlap"):
        read_effort(spec, root, replace(changed, closures=(inputs.closures[0], put(root, closure), *inputs.closures[2:])),
                    policy_digest=plan.effort_policy_digest)


def test_absent_closure_cannot_assert_zero_and_policy_cannot_change(tmp_path):
    spec, plan, root, inputs, scientific, logs = fixture(tmp_path)
    with pytest.raises(ValueError, match="explicit logs"):
        EffortClosure("utility-effort-closure-v1", "common", "closed", (), logs[0][0].evidence)
    with pytest.raises(ValueError, match="frozen analysis"):
        read_effort(spec, root, inputs, policy_digest="2"*64)
    with pytest.raises(ValueError, match="exactly the frozen contrasts"):
        replace(plan, effort_criteria=())
    policy = EffortPlan.from_json((root / inputs.policy.path).read_text())
    with pytest.raises(ValueError, match="exactly all assigned"):
        read_effort(spec, root, replace(inputs, policy=put(root, replace(policy, scopes=policy.scopes[1:2]))),
                    policy_digest=replace(policy, scopes=policy.scopes[1:2]).digest)


def test_scientific_degradation_and_missing_dependence_block_efficiency_claim(tmp_path):
    spec, plan, root, inputs, scientific, logs = fixture(tmp_path)
    effort = read_effort(spec, root, inputs, policy_digest=plan.effort_policy_digest)
    for change in ({"interval": [-1., 0.]}, {"dependence_complete": False}, {"valid_pairs": 2}):
        import copy
        altered = copy.deepcopy(scientific)
        altered["contrasts"][0].update(change)
        assert analyze_effort(spec, plan, altered, effort)["contrasts"][0]["efficiency_verdict"] == "inconclusive"


def test_duplicate_source_and_forbidden_self_reported_method_reject(tmp_path):
    spec, plan, root, inputs, scientific, logs = fixture(tmp_path)
    closure = EffortClosure.from_json((root / inputs.closures[0].path).read_text())
    with pytest.raises(ValueError, match="duplicate effort log"):
        replace(closure, logs=(logs[0][1], logs[0][1]))
    original = logs[0][0]
    source = HumanTimeSource("utility-human-time-source-v1", original.log_id, H, original.activity,
                             "self_reported", original.started_at, original.ended_at)
    log = replace(original, method="self_reported", evidence=put(root, source))
    updated = replace(closure, logs=(put(root, log),), evidence=log.evidence)
    with pytest.raises(ValueError, match="not admitted"):
        read_effort(spec, root, replace(inputs, closures=(put(root, updated), *inputs.closures[1:])),
                    policy_digest=plan.effort_policy_digest)



def test_report_and_cli_reconstruct_effort_without_confirmation_or_model_calls(tmp_path):
    from click.testing import CliRunner
    from autoengineering.cli import cli
    from autoengineering.utility.analysis import ContrastSpec
    from autoengineering.utility.reporting import EffortReportSpec, ReportSpec, comparative_report, export_report, verify_export
    from autoengineering.utility.uncertainty import BoundScenarioUncertaintySpec, DependencePlan
    from test_utility_contracts import suite
    from test_utility_confirmation import selected_suite
    cells = tuple(c.digest for c in suite().cells)
    policy = EffortPlan("utility-effort-policy-v1",
        (EffortScope("common", "preparation", "common_setup", cells, (.5, .5)),), ("timer",), 2, "first_use")
    dependence = DependencePlan("utility-dependence-v1", (), (
        BoundScenarioUncertaintySpec("utility-scenario-uncertainty-v2", "task", "W", "minimize", ("low", "high"),
            "fixed_scenario_census", "fixed_design_cases", H, 500, .999, 17, H),))
    contrast = ContrastSpec("task", "multi", "conventional", "power", "W", "minimize", .1, 1., .95,
                           "paired_student_t", 500, 17, "single_prespecified")
    plan = EffortAnalysisPlan("utility-analysis-v3", (contrast,), "complete_pairs_and_full_denominators", dependence.digest,
        effort_policy_digest=policy.digest, effort_criteria=(EffortCriterion("task", "multi", "conventional", .05, 10.),))
    store, _, _ = selected_suite(tmp_path, analysis_plan=plan)
    source = HumanTimeSource("utility-human-time-source-v1", "setup", H, "setup", "timer", 1000., 1040.)
    log = HumanTimeLog(**(source.to_dict() | {"schema":"utility-human-time-v1", "scope_id":"common",
                                            "evidence":put(store.root, source)}))
    closure = EffortClosure("utility-effort-closure-v1", "common", "closed", (put(store.root, log),), log.evidence)
    inputs = EffortInputs("utility-effort-inputs-v1", put(store.root, policy), (put(store.root, closure),))
    request = EffortReportSpec("utility-report-inputs-v2", store.spec.digest, put(store.root, plan), put(store.root, dependence), (),
                              effort=put(store.root, inputs))
    assert ReportSpec.from_json(request.to_json()) == request
    document = comparative_report(store, request)
    assert document["accounting"]["human_effort"]["declared_scopes_complete"]
    assert not document["complete_cost_evidence"]
    assert document["analysis"]["contrasts"][0]["efficiency_verdict"] == "inconclusive"
    destination = tmp_path / "export"
    manifest = export_report(store, request, destination)
    assert len(manifest["files"]) == 13
    assert verify_export(store, request, destination)["status"] == "verified_reconstruction"
    import importlib.util
    if importlib.util.find_spec("matplotlib") is not None:
        from autoengineering.utility.figures import export_figures
        figures = tmp_path / "figures"
        export_figures(store, request, figures)
        assert verify_export(store, request, figures, rerender_figures=True)["image_rendering"] == "reconstructed"
    path = tmp_path / "report-inputs.json"
    path.write_text(request.to_json())
    result = CliRunner().invoke(cli, ["utility", "verify", str(store.root), "--inputs", str(path),
                                    "--export-directory", str(destination)])
    assert result.exit_code == 0, result.output


def test_altering_measurement_method_or_amortization_changes_frozen_policy(tmp_path):
    spec, plan, root, inputs, scientific, logs = fixture(tmp_path)
    policy = EffortPlan.from_json((root / inputs.policy.path).read_text())
    for altered in (replace(policy, amortization_horizon=100), replace(policy, allowed_methods=("self_reported",))):
        with pytest.raises(ValueError, match="frozen analysis"):
            read_effort(spec, root, replace(inputs, policy=put(root, altered)), policy_digest=plan.effort_policy_digest)



@pytest.mark.parametrize("multi,comparator", [(40., 30.), (0., 0.)])
def test_no_effort_reduction_and_explicit_zero_logs_are_not_positive_results(tmp_path, multi, comparator):
    spec, plan, root, inputs, scientific, logs = fixture(tmp_path, multi_seconds=multi, comparator_seconds=comparator)
    effort = read_effort(spec, root, inputs, policy_digest=plan.effort_policy_digest)
    assert effort["declared_scopes_complete"] is True
    result = analyze_effort(spec, plan, scientific, effort)["contrasts"][0]
    assert result["efficiency_verdict"] == "no_useful_gain_demonstrated"
    assert result["effort"]["mean_seconds_saved"] == comparator-multi


def test_effort_policy_reserves_a_third_nominal_uncertainty_allowance(tmp_path):
    spec, old, scores, dependence, evidence = prepared()
    policy = replace(dependence.scenarios[0], confidence=.992)
    dependence = replace(dependence, scenarios=(policy,))
    plan = EffortAnalysisPlan("utility-analysis-v3", old.contrasts, old.missing_policy, dependence.digest,
        effort_policy_digest=H, effort_criteria=(EffortCriterion("task", "multi", "conventional", .05, 10.),))
    spec = replace(spec, analysis_digest=plan.digest)
    with pytest.raises(ValueError, match="decision family"):
        analyze(spec, plan, scores, dependence=dependence,
                dependence_evidence=tuple(replace(e, policy_digest=policy.digest) for e in evidence))
