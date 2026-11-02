"""Public controller integration for pinned ledger-replayed Optuna."""

from dataclasses import replace

import pytest

pytest.importorskip("optuna")

from autoengineering.optimization import (
    BudgetSpec,
    ContinuousParameter,
    EvaluationResult,
    NoiseSpec,
    ObjectiveSpec,
    ObservationLedger,
    SearchSpace,
    StudySpec,
)
from autoengineering.optimization.controller import OptimizationStudy, StudyRecoveryError
from autoengineering.optimization.optuna_backend import OptunaBackend


def specification():
    return StudySpec(
        "optuna-recovery",
        ObjectiveSpec("score", "maximize"),
        (),
        BudgetSpec(8, "run", 8),
        NoiseSpec(),
        "system",
        17,
    )


def make(root, evaluator, **options):
    spec = specification()
    space = SearchSpace((ContinuousParameter("x", 0.0, 1.0),))
    return OptimizationStudy(
        spec,
        space,
        OptunaBackend(spec, space, **options),
        ObservationLedger(root / "observations.jsonl"),
        evaluator,
        root,
    )


def evaluate(action):
    return EvaluationResult.success(
        action.id, {"score": -((action.config["x"] - 0.3) ** 2)}, {}, 1.0, "run"
    )


def test_fresh_resume_equivalence(tmp_path):
    full = make(tmp_path / "full", evaluate)
    full.run()
    split = make(tmp_path / "split", evaluate)
    split.run(max_new_evaluations=3)
    split = make(tmp_path / "split", evaluate)
    split.run()
    assert split.ledger.entries() == full.ledger.entries()
    assert split.backend.recommend(split.ledger) == full.backend.recommend(full.ledger)


def test_committed_result_recovery_never_relaunches(tmp_path, monkeypatch):
    starts = []

    def evaluator(action):
        starts.append(action.id)
        return evaluate(action)

    study = make(tmp_path / "study", evaluator)
    (action,) = study.ask()
    result = evaluator(action)
    original = study._update_artifacts

    def crash(**kwargs):
        raise RuntimeError("crash after result and ledger commit")

    with monkeypatch.context() as patch:
        patch.setattr(study, "_update_artifacts", crash)
        with pytest.raises(RuntimeError, match="crash"):
            study.tell(action, result)
    study._update_artifacts = original
    if study._pending_lock is not None:
        study._pending_lock.__exit__(None, None, None)
        study._pending_lock = None
    reopened = make(tmp_path / "study", evaluator)
    assert len(reopened.ledger.entries()) == 1
    assert starts == [action.id]
    reopened.run(max_new_evaluations=1)
    assert len(starts) == len(set(starts)) == 2


def test_changed_sampler_options_reject_resume(tmp_path):
    study = make(tmp_path / "study", evaluate)
    study.run(max_new_evaluations=1)
    with pytest.raises(StudyRecoveryError, match="configuration differs"):
        make(tmp_path / "study", evaluate, min_initial=5)


def test_replay_rejects_changed_historical_configuration(tmp_path):
    study = make(tmp_path / "study", evaluate)
    study.run(max_new_evaluations=1)
    action, result = study.ledger.entries()[0]

    class Altered:
        def entries(self):
            return ((replace(action, config={"x": 0.999}), result),)

    with pytest.raises(ValueError, match="replay differs"):
        study.backend.suggest(Altered())


def test_campaign_supplied_candidate_calibration(tmp_path):
    from autoengineering.campaign.controller import CampaignController
    from test_campaign_studies import ROOT, calibrated_spec

    spec = calibrated_spec()
    spec = replace(
        spec,
        calibration=replace(
            spec.calibration,
            run=replace(spec.calibration.run, policy="optuna"),
        ),
    )
    path = tmp_path / "campaign.yaml"
    spec.to_yaml(path)
    controller = CampaignController.create(path, ROOT, tmp_path / "campaign", max_new_evaluations=2)
    controller.advance()
    controller = CampaignController.open(controller.store.root, max_new_evaluations=2)
    controller.advance()
    controller = CampaignController.open(controller.store.root, max_new_evaluations=1)
    assert controller.advance().state == "completed"
    state = controller.state()
    assert len(state.budget.attempts) == state.budget.confirmed_attempts == 5
    assert len(state.studies) == 1
    fitting = [e for e in state.evaluations if e.split_id == "fitting"]
    assert len(fitting) == 3
    selected = min(fitting, key=lambda e: e.metrics["rmse"])
    assert state.evaluations[-1].configuration == selected.configuration
    import json

    root = controller.store.root / state.studies[0].work_path / "optimizer-proposals"
    receipts = [json.loads(p.read_text()) for p in root.glob("*-synchronized.json")]
    assert len(receipts) == 3
    actual = {a.child_action_id: a.id for a in state.budget.attempts if a.child_action_id}
    for receipt in receipts:
        assert receipt["campaign_id"] == controller.spec.name
        assert receipt["study_id"] == state.studies[0].study_id
        assert receipt["attempt_ids"] == [actual[f"{receipt['study_id']}:{receipt['action_id']}"]]


@pytest.mark.parametrize("hook", ["prepare_suggestion", "record_suggestion"])
def test_crash_after_proposal_evidence_does_not_start_model(tmp_path, monkeypatch, hook):
    starts = []

    def evaluator(action):
        starts.append(action.id)
        return evaluate(action)

    root = tmp_path / "study"
    study = make(root, evaluator)
    original = getattr(study.backend, hook)

    def crash(*args):
        original(*args)
        raise RuntimeError("proposal boundary crash")

    with monkeypatch.context() as patch:
        patch.setattr(study.backend, hook, crash)
        with pytest.raises(RuntimeError, match="boundary crash"):
            study.run(max_new_evaluations=1)
    assert starts == []
    assert len(tuple((root / "optimizer-proposals").glob("*-intent.json"))) == 1
    reopened = make(root, evaluator)
    reopened.run(max_new_evaluations=1)
    assert starts == ["eval-000000"]


@pytest.mark.parametrize("part", ["intent", "proposal"])
def test_missing_pending_evidence_blocks_recovery(tmp_path, part):
    root = tmp_path / "study"
    study = make(root, evaluate)
    (action,) = study.ask()
    study._pending_lock.__exit__(None, None, None)
    study._pending_lock = None
    (root / "optimizer-proposals" / f"{action.id}-{part}.json").unlink()
    with pytest.raises(StudyRecoveryError, match="evidence missing"):
        make(root, evaluate)


@pytest.mark.parametrize("suffix", ["tell-intent", "synchronized"])
def test_tell_crash_replays_without_duplicate_model_start(tmp_path, monkeypatch, suffix):
    import json

    starts = []

    def evaluator(action):
        starts.append(action.id)
        return evaluate(action)

    root = tmp_path / "study"
    study = make(root, evaluator)
    (action,) = study.ask()
    result = evaluator(action)
    original = study.backend._evidence

    def crash(directory, name, document, *, create):
        original(directory, name, document, create=create)
        if name == f"{action.id}-{suffix}.json":
            raise RuntimeError("tell boundary crash")

    with monkeypatch.context() as patch:
        patch.setattr(study.backend, "_evidence", crash)
        with pytest.raises(RuntimeError, match="boundary crash"):
            study.tell(action, result)
    study._pending_lock.__exit__(None, None, None)
    study._pending_lock = None
    recovered = make(root, evaluator)
    assert starts == [action.id]
    receipt = json.loads(
        (root / "optimizer-proposals" / f"{action.id}-synchronized.json").read_text()
    )
    assert receipt["external_trial_id"] == "0"
    assert receipt["external_experiment_id"].startswith("optuna-")
    assert receipt["attempt_ids"] == [] and receipt["campaign_id"] is None
    recovered.run(max_new_evaluations=1)
    assert starts == ["eval-000000", "eval-000001"]


@pytest.mark.parametrize("damage", ["missing", "trial", "observation"])
def test_committed_synchronization_corruption_blocks_resume(tmp_path, damage):
    import json

    root = tmp_path / "study"
    study = make(root, evaluate)
    study.run(max_new_evaluations=1)
    path = root / "optimizer-proposals/eval-000000-synchronized.json"
    if damage == "missing":
        path.unlink()
    else:
        receipt = json.loads(path.read_text())
        receipt["external_trial_id" if damage == "trial" else "observation_digest"] = "wrong"
        path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="evidence (missing|differs)"):
        make(root, evaluate)


def test_replay_rejects_changed_historical_seed(tmp_path):
    study = make(tmp_path / "study", evaluate)
    study.run(max_new_evaluations=1)
    action, result = study.ledger.entries()[0]

    class Altered:
        def entries(self):
            return ((replace(action, seed=action.seed + 1), result),)

    with pytest.raises(ValueError, match="replay differs"):
        study.backend.suggest(Altered())


def test_minimize_infeasible_and_failed_trials_keep_empty_recommendation(tmp_path):
    from autoengineering.optimization import CategoricalParameter, ConstraintSpec

    spec = replace(
        specification(),
        objective=ObjectiveSpec("score", "minimize"),
        constraints=(ConstraintSpec("limit", "<=", 0.0),),
    )
    space = SearchSpace((CategoricalParameter("choice", ("a", "b")),))
    starts = []

    def evaluator(action):
        starts.append(action.id)
        if len(starts) == 1:
            return EvaluationResult.success(
                action.id, {"score": -999.0, "limit": 1.0}, {}, 1.0, "run"
            )
        return EvaluationResult.model_failure(action.id, "failed", cost=1.0, cost_unit="run")

    study = OptimizationStudy(
        spec,
        space,
        OptunaBackend(spec, space),
        ObservationLedger(tmp_path / "observations.jsonl"),
        evaluator,
        tmp_path,
    )
    study.run()
    assert len(starts) == 2 and study.stop_reason == "finite_space_exhausted"
    assert study.backend.recommend(study.ledger).action_id is None
    import json

    receipts = [
        json.loads(p.read_text())
        for p in (tmp_path / "optimizer-proposals").glob("*-synchronized.json")
    ]
    assert len(receipts) == 2 and all(r["projected_objective"] is None for r in receipts)


@pytest.mark.parametrize("installed", [None, "4.4.0"])
def test_missing_or_wrong_framework_rejects_before_dispatch(monkeypatch, installed):
    import autoengineering.optimization.optuna_backend as module

    original = module.version

    def version(name):
        if name == "optuna":
            if installed is None:
                raise module.PackageNotFoundError(name)
            return installed
        return original(name)

    monkeypatch.setattr(module, "version", version)
    with pytest.raises((ImportError, ValueError), match="requires"):
        OptunaBackend(specification(), SearchSpace((ContinuousParameter("x", 0.0, 1.0),)))


def test_standalone_display_name_is_not_used_as_receipt_identifier(tmp_path):
    import json

    spec = StudySpec(
        "a study / display name",
        ObjectiveSpec("score", "maximize"),
        (),
        BudgetSpec(1.0, "run", 1),
        NoiseSpec(),
        "system",
        17,
    )
    space = SearchSpace((ContinuousParameter("x", 0.0, 1.0),))
    starts = []

    def evaluate(action):
        starts.append(action.id)
        return EvaluationResult.success(action.id, {"score": action.config["x"]}, {}, 1.0, "run")

    study = OptimizationStudy(
        spec,
        space,
        OptunaBackend(spec, space),
        ObservationLedger(tmp_path / "observations.jsonl"),
        evaluate,
        tmp_path,
    )
    study.run()
    receipt = json.loads(
        (tmp_path / "optimizer-proposals/eval-000000-synchronized.json").read_text()
    )
    assert receipt["study_id"].startswith("study-")
    assert starts == ["eval-000000"]


@pytest.mark.parametrize("seed", [0, 2**32 - 1, 2**32, 2**63 - 1])
def test_large_study_seeds_have_explicit_deterministic_sampler_mapping(seed):
    import numpy as np

    spec = replace(specification(), seed=seed)
    space = SearchSpace((ContinuousParameter("x", 0.0, 1.0),))
    backend = OptunaBackend(spec, space)
    expected = (
        seed
        if seed <= 2**32 - 1
        else int(np.random.SeedSequence(seed).generate_state(1, dtype=np.uint32)[0])
    )
    assert backend.sampler_seed == expected
    constructor = backend.identity_dict()["constructor"]
    if seed <= 2**32 - 1:
        assert "seed_mapping" not in constructor
    else:
        assert constructor["seed_mapping"] == {
            "version": "numpy-seedsequence-u32-v1",
            "sampler_seed": expected,
        }
    first = backend._new_session().ask().suggest_float("x", 0.0, 1.0)
    assert OptunaBackend(spec, space)._new_session().ask().suggest_float("x", 0.0, 1.0) == first


def test_large_seed_resume_replays_exact_proposals_and_costs(tmp_path):
    spec = replace(specification(), seed=2**63 - 1)
    space = SearchSpace((ContinuousParameter("x", 0.0, 1.0),))
    starts = []

    def counted(action):
        starts.append(action.id)
        return evaluate(action)

    def large(root):
        return OptimizationStudy(
            spec,
            space,
            OptunaBackend(spec, space),
            ObservationLedger(root / "observations.jsonl"),
            counted,
            root,
        )

    full = large(tmp_path / "large-full")
    full.run()
    full_count = len(starts)
    split = large(tmp_path / "large-split")
    split.run(max_new_evaluations=3)
    split = large(tmp_path / "large-split")
    split.run()
    assert split.ledger.entries() == full.ledger.entries()
    assert len(starts) == 2 * full_count == 16
    split.run()
    assert len(starts) == 16
