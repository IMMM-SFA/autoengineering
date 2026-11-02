"""Public OptimizationStudy bridge with campaign-owned physical attempt evidence."""

from __future__ import annotations

from dataclasses import replace

from autoengineering.optimization import (
    EvaluationResult,
    EvaluationStatus,
    ObservationLedger,
    OptimizationStudy,
)
from autoengineering.optimization.command import build_backend

from .acceptance import eligible
from .artifacts import put_bytes
from .budget import BudgetExhausted
from .records import StudyLink
from .serialization import digest
from .service import CampaignError


def campaign_evaluator(
    controller, *, model_id, model, adapter_id, parameters, reservation_id, study_id
):
    """Construct the trusted fitting evaluator declared by CampaignSpec calibration."""

    def evaluate(action):
        evaluation = controller._physical(
            model_id,
            model,
            adapter_id,
            dict(parameters, **dict(action.config)),
            "fitting",
            reservation_id,
            action_id=f"{study_id}:{action.id}",
            seed=action.seed,
        )
        if evaluation is None:
            raise RuntimeError("invocation allowance must be checked before asking for an action")
        return child_result(evaluation, action, controller.spec)

    return evaluate


def child_result(evaluation, action, spec):
    if evaluation.status == "success" and eligible(evaluation, spec.acceptance):
        outcomes = {name: value for name, value in evaluation.metrics.items() if value is not None}
        return EvaluationResult.success(
            action.id,
            outcomes,
            {},
            1.0,
            spec.calibration.run.study.budget.cost_unit,
            evaluator_seconds=evaluation.elapsed_seconds,
        )
    status = evaluation.status if evaluation.status != "success" else "scientific_infeasible"
    return EvaluationResult(
        action.id,
        EvaluationStatus(status),
        cost=0.0 if evaluation.provenance.get("cost_uncertain") == "true" else 1.0,
        cost_unit=spec.calibration.run.study.budget.cost_unit,
        evaluator_seconds=evaluation.elapsed_seconds,
        message="See campaign scientific checks",
    )


def run_child(controller, request, model_id, model, adapter_id, parameters):
    spec = controller.spec
    if spec.calibration is None:
        raise CampaignError("schema_error")
    state = controller.state()
    if state.budget.unresolved_attempts:
        raise CampaignError("reconciliation_required")
    candidate_id = request.payload["candidate_id"]
    run = spec.calibration.run
    identity = digest(
        {
            "candidate": model_id,
            "adapter": adapter_id,
            "fixed_parameters": dict(parameters),
            "run": run.to_dict(),
            "fitting": controller._data("fitting").to_dict(),
            "forcing": controller._data("forcing").to_dict(),
            "campaign": spec.digest,
        }
    )
    study_id = f"study-{identity[:32]}"
    link = next((item for item in state.studies if item.study_id == study_id), None)
    reservation_id = study_id
    if link is None:
        # Supplied defaults and the final comparison are distinct physical calls.
        default_present = (
            model == spec.baseline.model and dict(parameters) == dict(spec.baseline.parameters)
        ) or any(
            item.model_id == model_id
            and item.split_id == controller._data("comparison").id
            and dict(item.configuration) == dict(parameters)
            for item in state.evaluations
        )
        capacity = run.study.budget.max_evaluations + 1 + int(not default_present)
        try:
            budget = state.budget.reserve(reservation_id, capacity)
        except BudgetExhausted:
            return controller._transition("completed", replace(state, outcome="budget_exhausted"))
        link = StudyLink(
            study_id,
            candidate_id,
            (controller._data("forcing").artifact, controller._data("fitting").artifact),
            run.sha256,
            run.study.seed,
            f"children/{study_id}",
            None,
            predecessor_id=state.studies[-1].study_id if state.studies else None,
        )
        state = replace(
            state,
            budget=budget,
            studies=(*state.studies, link),
            active_mode="calibrate",
            active_reservation=reservation_id,
        )
        controller._checkpoint("evaluating", state, "study_linked")
        if not default_present:
            controller._physical(
                model_id,
                model,
                adapter_id,
                parameters,
                "comparison",
                reservation_id,
                purpose=f"default:{study_id}",
            )
            if controller.store.replay().state != "evaluating":
                return controller._transition(controller.store.replay().state, controller.state())
    directory = controller.store.root / link.work_path
    directory.mkdir(mode=0o700, exist_ok=True)
    from .store import checked_directory

    checked_directory(directory)

    evaluate = campaign_evaluator(
        controller,
        model_id=model_id,
        model=model,
        adapter_id=adapter_id,
        parameters=parameters,
        reservation_id=reservation_id,
        study_id=study_id,
    )

    def resolve(action):
        current = controller.state()
        attempt = next(
            (
                item
                for item in current.budget.attempts
                if item.child_action_id == f"{study_id}:{action.id}"
            ),
            None,
        )
        if attempt is None or attempt.state != "finished":
            return None
        evaluation = next(
            (item for item in current.evaluations if item.attempt_id == attempt.id), None
        )
        return child_result(evaluation, action, spec) if evaluation else None

    def result_links(action):
        attempts = tuple(
            item.id for item in controller.state().budget.attempts
            if item.child_action_id == f"{study_id}:{action.id}"
        )
        return {"campaign_id": spec.name, "study_id": study_id, "attempt_ids": attempts}

    study = OptimizationStudy(
        run.study,
        run.search_space,
        build_backend(run),
        ObservationLedger(directory / "observations.jsonl"),
        evaluate,
        directory,
        target_value=run.target_value,
        input_artifact_hashes={"campaign": spec.digest, "child": identity},
        pending_result_resolver=resolve,
        result_link_resolver=result_links,
    )
    while controller.remaining is None or controller.remaining > 0:
        study.run_result(max_new_evaluations=1)
        state = controller.state()
        if controller.store.replay().state != "evaluating" or study.stop_reason is not None:
            break
    manifest = put_bytes(
        controller.store.root,
        (directory / "manifest.json").read_bytes(),
        name="child-manifest.json",
        media_type="application/json",
        producer=study_id,
    )
    state = controller.state()
    link = replace(link, committed_manifest=manifest)
    state = replace(
        state, studies=tuple(link if item.study_id == study_id else item for item in state.studies)
    )
    controller._checkpoint(controller.store.replay().state, state, "study_observed", (manifest,))
    if controller.store.replay().state != "evaluating":
        return controller._transition(controller.store.replay().state, state)
    if study.stop_reason is None or controller.remaining == 0:
        return controller._transition("evaluating", state, {"paused": True, "study_id": study_id})
    recommendation = study.recommend()
    if recommendation.action_id is None or not recommendation.feasible:
        state = replace(
            state,
            budget=state.budget.release(reservation_id),
            active_mode=None,
            active_reservation=None,
        )
        return controller._transition(
            "evidence_ready", state, {"study_id": study_id, "no_fitting_selection": True}
        )
    # Selection uses only fitting records. A fresh comparison call evaluates that frozen configuration.
    evaluation = next(
        (
            item
            for item in state.evaluations
            if item.provenance.get("purpose") == f"calibrated:{study_id}"
        ),
        None,
    )
    if evaluation is None:
        evaluation = controller._physical(
            model_id,
            model,
            adapter_id,
            dict(parameters, **dict(recommendation.config)),
            "comparison",
            reservation_id,
            purpose=f"calibrated:{study_id}",
        )
    state = controller.state()
    if controller.store.replay().state != "evaluating":
        return controller._transition(controller.store.replay().state, state)
    state = replace(
        state,
        budget=state.budget.release(reservation_id),
        active_mode=None,
        active_reservation=None,
    )
    return controller._transition(
        "evidence_ready",
        state,
        {
            "study_id": study_id,
            "evaluation_id": evaluation.id,
            "selected_action_id": recommendation.action_id,
        },
    )
