"""Public broker workflow, physical starts, immutable resume and read-only inspection."""

from dataclasses import replace
from unittest.mock import patch

import pytest

from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.service import CampaignError
from examples.campaign_contracts.build_fixture import ROOT, fixture


def create(tmp_path, *, limit=None, spec=None):
    specification = tmp_path / "input.yaml"
    (spec or fixture()).to_yaml(specification)
    return CampaignController.create(
        specification, ROOT, tmp_path / "campaign", max_new_evaluations=limit
    )


def test_fixed_workflow_finishes_and_status_has_no_model_or_observation_access(tmp_path):
    controller = create(tmp_path)
    assert controller.advance().state == "completed"
    state = controller.state()
    assert len(state.budget.attempts) == 2
    assert state.budget.confirmed_attempts == 2
    assert state.outcome == "accepted_candidate"
    assert state.confirmation == "confirmation_not_attempted"
    assert state.baseline.metrics["rmse"] == 1
    assert state.evaluations[-1].metrics["rmse"] == 0
    assert state.decisions[-1].selected_configuration == {"multiplier": 1.5}
    before = {str(p): p.read_bytes() for p in controller.store.root.rglob("*") if p.is_file()}
    from autoengineering.campaign.report import render_report

    with patch.object(
        CampaignController, "_arrays", side_effect=AssertionError("private labels accessed")
    ):
        read = CampaignController.open(controller.store.root, inspect_only=True)
        assert read.request("state").result["state"] == "completed"
        assert "confirmation_not_attempted" in render_report(read.spec, read.state())
    after = {str(p): p.read_bytes() for p in controller.store.root.rglob("*") if p.is_file()}
    assert before == after


def test_bounded_resume_matches_uninterrupted_without_extra_starts(tmp_path):
    controller = create(tmp_path, limit=0)
    assert controller.advance().state == "created"
    assert not controller.state().budget.attempts
    controller = CampaignController.open(controller.store.root, max_new_evaluations=1)
    assert controller.advance().state == "candidate_ready"
    assert len(controller.state().budget.attempts) == 1
    controller = CampaignController.open(controller.store.root, max_new_evaluations=1)
    assert controller.advance().state == "completed"
    assert len(controller.state().budget.attempts) == 2
    assert controller.state().outcome == "accepted_candidate"


def test_invalid_identity_refuses_resume_without_modifying_campaign(tmp_path):
    controller = create(tmp_path, limit=0)
    path = controller.store.root / "bundle" / controller.spec.data[0].artifact.path
    path.write_text("changed forcing")
    before = {str(p): p.read_bytes() for p in controller.store.root.rglob("*") if p.is_file()}
    with pytest.raises(CampaignError, match="identity_mismatch"):
        CampaignController.open(controller.store.root)
    after = {str(p): p.read_bytes() for p in controller.store.root.rglob("*") if p.is_file()}
    assert before == after


def test_idle_cancellation_and_execution_budget_are_explicit(tmp_path):
    controller = create(tmp_path, limit=0)
    controller.cancel("stop-1")
    assert controller.advance().state == "completed"
    assert controller.state().outcome == "cancelled"
    assert not controller.state().budget.attempts
    other = tmp_path / "budget"
    other.mkdir()
    spec = fixture()
    spec = replace(spec, execution=replace(spec.execution, max_executions=1))
    controller = create(other, spec=spec)
    assert controller.advance().state == "completed"
    assert controller.state().outcome == "budget_exhausted"
    assert len(controller.state().budget.attempts) == 1


def test_synthetic_confirmation_is_once_and_freeze_cannot_reopen_selection(tmp_path):
    from autoengineering.campaign.spec import ConfirmationSpec

    spec = fixture()
    confirmation = replace(
        spec.data[-1], id="confirmation", role="confirmation", prior_exposure="unexposed"
    )
    spec = replace(
        spec,
        data=(*spec.data, confirmation),
        confirmation=ConfirmationSpec("once", "confirmation", "eligibility-v1"),
    )
    controller = create(tmp_path, spec=spec, limit=2)
    assert controller.advance().state == "selection_frozen"
    selected = controller.state().frozen_id
    controller = CampaignController.open(controller.store.root, max_new_evaluations=1)
    assert controller.advance().state == "completed"
    assert controller.state().confirmation == "pass"
    assert len(controller.state().budget.attempts) == 3
    assert controller.state().frozen_id == selected
    assert controller.request("confirm").error == "invalid_transition"
    assert controller.request("propose", {"proposal_id": "new"}).error == "invalid_transition"
    assert len(controller.state().budget.attempts) == 3


def test_failed_confirmation_does_not_reopen_selection(tmp_path, monkeypatch):
    from autoengineering.campaign.spec import ConfirmationSpec
    from autoengineering.campaign.acceptance import DEFAULT_CHECKS

    spec = fixture()
    data = replace(
        spec.data[-1], id="confirmation", role="confirmation", prior_exposure="unexposed"
    )
    spec = replace(
        spec,
        data=(*spec.data, data),
        confirmation=ConfirmationSpec("once", "confirmation", "eligibility-v1"),
    )
    controller = create(tmp_path, spec=spec, limit=2)
    assert controller.advance().state == "selection_frozen"
    selected = controller.state().frozen_id
    evaluate = DEFAULT_CHECKS.evaluate
    monkeypatch.setattr(
        DEFAULT_CHECKS, "evaluate", lambda *args: replace(evaluate(*args), status="fail")
    )
    controller = CampaignController.open(controller.store.root, max_new_evaluations=1)
    assert controller.advance().state == "completed"
    assert controller.state().confirmation == "fail"
    assert controller.state().frozen_id == selected
    assert (
        controller.request("evaluate", {"candidate_id": "baseline", "mode": "fixed"}).error
        == "invalid_transition"
    )
    assert len(controller.state().budget.attempts) == 3


@pytest.mark.parametrize(
    "outcome", ["retain_baseline", "no_eligible_model", "no_suitable_intervention"]
)
def test_valid_negative_outcomes_are_complete_campaigns(tmp_path, outcome):
    spec = fixture()
    if outcome == "retain_baseline":
        spec = replace(spec, acceptance=replace(spec.acceptance, minimum_gain=2.0))
    elif outcome == "no_eligible_model":
        checks = tuple(replace(check, version="not-installed") for check in spec.acceptance.checks)
        spec = replace(spec, acceptance=replace(spec.acceptance, checks=checks))
    else:
        spec = replace(
            spec, interventions=(replace(spec.interventions[0], implementation_ids=("linear-v1",)),)
        )
    controller = create(tmp_path, spec=spec)
    assert controller.advance().state == "completed"
    assert controller.state().outcome == outcome
    if outcome == "no_eligible_model":
        assert controller.state().frozen_id is None
        assert controller.state().decisions[-1].selected_configuration is None


def test_insufficient_observations_finish_before_model_launch(tmp_path):
    from autoengineering.campaign.artifacts import reference

    spec = fixture()
    source = tmp_path / "source"
    source.mkdir()
    for ref in (
        *spec.provenance.sources,
        spec.baseline.system,
        spec.provenance.environment_lock,
        *(data.artifact for data in spec.data),
    ):
        target = source / ref.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / ref.path).read_bytes())
    (source / "missing-observations.json").write_text('{"prediction":null}')
    missing = replace(
        spec.data[-1],
        artifact=reference(
            source, "missing-observations.json", media_type="application/json", producer="test"
        ),
    )
    spec = replace(spec, data=(*spec.data[:-1], missing))
    path = tmp_path / "input.yaml"
    spec.to_yaml(path)
    controller = CampaignController.create(path, source, tmp_path / "campaign")
    assert controller.advance().state == "completed"
    assert controller.state().outcome == "insufficient_data"
    assert not controller.state().budget.attempts
    assert not list((controller.store.root / "attempts").iterdir())


@pytest.mark.parametrize(
    "changed",
    ["examples/campaign_contracts/fixture_model.py", "src/autoengineering/campaign/acceptance.py"],
)
def test_declared_bundle_must_match_executing_adapter_and_engine(tmp_path, changed):
    from autoengineering.campaign.artifacts import reference

    spec = fixture()
    source = tmp_path / "shadow"
    source.mkdir()
    refs = (
        *spec.provenance.sources,
        spec.baseline.system,
        spec.provenance.environment_lock,
        *(data.artifact for data in spec.data),
    )
    for ref in refs:
        path = source / ref.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / ref.path).read_bytes())
    path = source / changed
    path.write_text(path.read_text() + "\n# A different declared implementation version.\n")
    old = next(ref for ref in spec.provenance.sources if ref.path == changed)
    altered = reference(source, changed, media_type=old.media_type, producer=old.producer)
    sources = tuple(altered if ref.path == changed else ref for ref in spec.provenance.sources)
    model = replace(spec.baseline.model, source_bundle=sources)
    spec = replace(
        spec,
        baseline=replace(spec.baseline, model=model),
        provenance=replace(spec.provenance, sources=sources),
    )
    specification = tmp_path / "declared.yaml"
    spec.to_yaml(specification)
    with pytest.raises(ValueError):
        CampaignController.create(specification, source, tmp_path / "must-not-create")
    assert not (tmp_path / "must-not-create").exists()
