"""Fitting-only calibration through the public study API and durable result recovery."""

from dataclasses import replace

from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.spec import CalibrationSpec
from autoengineering.optimization import (
    BudgetSpec,
    ContinuousParameter,
    NoiseSpec,
    ObjectiveSpec,
    OptimizationRunSpec,
    SearchSpace,
    StudySpec,
)
from examples.campaign_contracts.build_fixture import ROOT, fixture


def calibrated_spec():
    spec = fixture()
    run = OptimizationRunSpec(
        StudySpec(
            "scalar-fitting",
            ObjectiveSpec("rmse", "minimize"),
            (),
            BudgetSpec(3, "calls", 3),
            NoiseSpec(),
            "system",
            17,
        ),
        SearchSpace((ContinuousParameter("multiplier", 0, 2),)),
        "sobol",
        {},
        "autoengineering.campaign.studies:campaign_evaluator",
    )
    return replace(
        spec,
        calibration=CalibrationSpec(run, "fitting"),
        workflow=replace(spec.workflow, max_candidates=1),
    )


def test_study_resume_preserves_fitting_selection_and_counts(tmp_path):
    spec = calibrated_spec()
    path = tmp_path / "input.yaml"
    spec.to_yaml(path)
    controller = CampaignController.create(path, ROOT, tmp_path / "campaign", max_new_evaluations=2)
    assert controller.advance().state == "evaluating"
    assert len(controller.state().budget.attempts) == 2
    controller = CampaignController.open(controller.store.root, max_new_evaluations=2)
    assert controller.advance().state == "evaluating"
    assert len(controller.state().budget.attempts) == 4
    controller = CampaignController.open(controller.store.root, max_new_evaluations=1)
    assert controller.advance().state == "completed"
    state = controller.state()
    assert len(state.budget.attempts) == 5
    assert state.budget.confirmed_attempts == 5
    assert len(state.studies) == 1
    assert state.studies[0].committed_manifest is not None
    fitting = [item for item in state.evaluations if item.split_id == "fitting"]
    comparison = [item for item in state.evaluations if item.split_id == "comparison"]
    assert len(fitting) == 3
    assert len(comparison) == 2
    selected = min(fitting, key=lambda item: item.metrics["rmse"])
    assert comparison[-1].configuration == selected.configuration
    # Uninterrupted search has identical fitting metrics/configurations and scientific outcome.
    other = CampaignController.create(path, ROOT, tmp_path / "uninterrupted")
    assert other.advance().state == "completed"
    other_fits = [item for item in other.state().evaluations if item.split_id == "fitting"]
    assert [(item.configuration, item.metrics) for item in fitting] == [
        (item.configuration, item.metrics) for item in other_fits
    ]
    assert state.outcome == other.state().outcome


def test_public_pending_result_resolver_preserves_verified_result(tmp_path):
    from autoengineering.optimization import (
        EvaluationResult,
        ObservationLedger,
        OptimizationStudy,
        SobolBackend,
    )

    run = calibrated_spec().calibration.run
    path = tmp_path / "child"
    study = OptimizationStudy(
        run.study,
        run.search_space,
        SobolBackend(run.study, run.search_space),
        ObservationLedger(path / "observations.jsonl"),
        lambda action: None,
        path,
    )
    action = study.ask()[0]
    # Release the live instance's lock by completing the process, not by editing pending state.
    # This fixture uses a subprocess for a genuine abandoned public ask.
    study.tell(action, EvaluationResult.success(action.id, {"rmse": 1.0}, {}, 1.0, "calls"))

    import subprocess
    import sys
    from autoengineering.campaign.serialization import canonical_json

    job = tmp_path / "run.json"
    job.write_text(canonical_json(run.to_dict()))
    code = """
import json, os, sys
from pathlib import Path
from autoengineering.optimization import OptimizationRunSpec, OptimizationStudy, ObservationLedger, SobolBackend
run = OptimizationRunSpec.from_dict(json.loads(Path(sys.argv[1]).read_text()))
p = Path(sys.argv[2])
s = OptimizationStudy(run.study, run.search_space, SobolBackend(run.study, run.search_space), ObservationLedger(p/'observations.jsonl'), lambda a: None, p)
a = s.ask()[0]
Path(sys.argv[3]).write_text(json.dumps(a.to_dict()))
os._exit(0)
"""
    action_path = tmp_path / "action.json"
    subprocess.run([sys.executable, "-c", code, str(job), str(path), str(action_path)], check=True)
    from autoengineering.optimization import EvaluationAction

    pending = EvaluationAction.from_dict(__import__("json").loads(action_path.read_text()))
    saved = EvaluationResult.success(pending.id, {"rmse": 0.25}, {}, 1.0, "calls")
    resumed = OptimizationStudy(
        run.study,
        run.search_space,
        SobolBackend(run.study, run.search_space),
        ObservationLedger(path / "observations.jsonl"),
        lambda action: None,
        path,
        pending_result_resolver=lambda action: saved if action == pending else None,
    )
    assert resumed.ledger.entries()[-1] == (pending, saved)
    assert resumed.recommend().action_id == pending.id
    assert len(resumed.ledger.entries()) == 2
