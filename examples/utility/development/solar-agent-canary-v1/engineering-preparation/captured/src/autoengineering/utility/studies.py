"""Engineering calibration through the existing durable OptimizationStudy.

The caller owns the trusted batch scientific executor. This bridge never creates
an adapter, launches a process or replaces a child scientific journal.
"""
from __future__ import annotations

from dataclasses import dataclass

from autoengineering.campaign.acceptance import eligible
from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, unique_json, digest
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from autoengineering.optimization import (
    EvaluationResult, EvaluationStatus, ObservationLedger, OptimizationRunSpec, OptimizationStudy,
)
from autoengineering.optimization.command import build_backend
from .contracts import identifier, sha256
from .outcomes import EngineeringAcceptance, EngineeringEvaluation, engineering_decision


class EngineeringReconciliationRequired(BaseException):
    """Stop pending optimization without converting uncertain work to zero cost."""


@dataclass(frozen=True)
class EngineeringStudySpec(Record):
    run: OptimizationRunSpec
    rules: EngineeringAcceptance
    scenario_ids: tuple[str, ...]
    source_identity: str

    def _validate(self):
        sha256(self.source_identity)
        if not self.scenario_ids or len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ValueError("engineering study needs unique ordered scenarios")
        for name in self.scenario_ids:
            identifier(name)
        study = self.run.study
        if (study.noise.mode != "deterministic" or study.backend != "system"
                or self.run.evaluator_factory != "autoengineering.utility.studies:engineering_evaluator"):
            raise ValueError("unsupported engineering calibration profile")
        if study.objective.outcome != self.rules.primary_metric or study.objective.direction != self.rules.direction:
            raise ValueError("engineering calibration objective differs from scientific rules")
        if study.budget.cost_unit != "physical_executions" or study.budget.max_evaluations is None:
            raise ValueError("engineering calibration needs explicit physical budgets")
        if self.run.max_new_evaluations is not None:
            raise ValueError("invocation limits cannot change immutable calibration")
        if study.constraints:
            raise ValueError("engineering feasibility must use registered scenario checks")


class EngineeringStudy:
    def __init__(self, profile, batch, case_id, evaluate, *, fault=lambda _: None, resume_scenarios=False):
        self.profile, self.batch, self.case_id = profile, batch, case_id
        self.perform, self.fault = evaluate, fault
        if type(resume_scenarios) is not bool:
            raise ValueError("scenario resume must be explicitly boolean")
        self.resume_scenarios = resume_scenarios
        if resume_scenarios:
            from .engineering_process import SupervisedEngineeringExecutor
            if not isinstance(evaluate, SupervisedEngineeringExecutor):
                raise StoreError("scenario resume requires the registered supervised executor")
        from .engineering_process import SupervisedEngineeringExecutor
        if isinstance(evaluate, SupervisedEngineeringExecutor) and (
                evaluate.spec.study != profile or evaluate.batch.root != batch.root or evaluate.case_id != case_id):
            raise StoreError("engineering executor differs from original study or batch")
        if batch._trusted_pin != batch.digest:
            raise StoreError("engineering study requires a caller-pinned batch")
        case = next((case for case in batch.spec.cases if case.id == case_id), None)
        ceiling = profile.run.study.budget.max_evaluations * len(profile.scenario_ids)
        if case is None or case.scientific_starts < ceiling:
            raise StoreError("batch case cannot cover the complete calibration reserve")
        if batch.replay().active_case != case_id:
            raise StoreError("engineering calibration requires its active assigned case")
        parent = batch.root / "cases" / case_id
        checked_directory(parent)
        studies = parent / "utility-studies"
        if studies.is_symlink():
            raise StoreError("study directory cannot be a symlink")
        studies.mkdir(mode=0o700, exist_ok=True)
        checked_directory(studies)
        directory = studies / profile.digest
        directory.mkdir(mode=0o700, exist_ok=True)
        self.directory = checked_directory(directory)
        manifest = self.directory / "engineering.json"
        if manifest.exists():
            path = confined_file(self.directory, manifest.name)
            if path.read_text() != profile.to_json() + "\n":
                raise StoreError("engineering study identity changed")
        else:
            durable_write(manifest, (profile.to_json() + "\n").encode())
        run = profile.run
        inputs = {"engineering_profile": profile.digest, "batch": batch.digest}
        if isinstance(evaluate, SupervisedEngineeringExecutor):
            inputs["supervised_execution_binding"] = evaluate.binding_digest
        self.study = OptimizationStudy(
            run.study, run.search_space, build_backend(run),
            ObservationLedger(directory / "observations.jsonl"), engineering_evaluator(self), directory,
            input_artifact_hashes=inputs,
            pending_result_resolver=self._resolve, target_value=run.target_value)

    def _path(self, action, suffix):
        identifier(action.id)
        return self.directory / f"{action.id}-{suffix}.json"

    def _resolve(self, action):
        path = self._path(action, "result")
        if not path.exists():
            if self._path(action, "intent").exists():
                intent = unique_json(confined_file(self.directory, self._path(action, "intent").name).read_text())
                if intent != {"action_digest": digest(action.to_dict()), "profile": self.profile.digest}:
                    raise StoreError("engineering dispatch intent identity differs")
                from .engineering_process import SupervisedEngineeringExecutor
                if isinstance(self.perform, SupervisedEngineeringExecutor):
                    try:
                        value = (self.perform(action) if self.resume_scenarios else self.perform.recover_completed(action))
                        return self._save_result(action, value, self.perform.reservations(action))
                    except Exception:
                        raise EngineeringReconciliationRequired("engineering scenarios require original evidence reconciliation") from None
                raise EngineeringReconciliationRequired("engineering dispatch has no verified saved result")
            return None  # Existing controller records recovery failure, never calls the evaluator again.
        document = unique_json(confined_file(self.directory, path.name).read_text())
        if set(document) != {"action_digest", "result", "evidence", "reservations"} or document["action_digest"] != digest(action.to_dict()):
            raise StoreError("engineering result action identity changed")
        ref = ArtifactRef.from_dict(document["evidence"])
        value = EngineeringEvaluation.from_json(read_bytes(self.batch.root, ref).decode())
        engineering_decision(value, (), self.profile.rules)
        self._check_value(action, value)
        state = self.batch.replay()
        reservations = [state.reservations[key] for key in document["reservations"]]
        self._check_physical(action, value, state, reservations)
        result = EvaluationResult.from_dict(document["result"])
        if result.to_dict() != self._result(action, value, len(reservations)).to_dict():
            raise StoreError("saved engineering result differs from physical/scientific evidence")
        return result

    def _evaluate(self, action):
        try:
            return self._dispatch(action)
        except Exception:
            raise EngineeringReconciliationRequired("engineering dispatch requires evidence reconciliation") from None

    def _dispatch(self, action):
        if self.batch.replay().pending:
            raise StoreError("unresolved physical work blocks engineering calibration")
        intent = self._path(action, "intent")
        if intent.exists():
            raise StoreError("engineering action already dispatched; reconciliation required")
        before = self.batch.replay()
        durable_write(intent, canonical_json({"action_digest": digest(action.to_dict()),
                      "profile": self.profile.digest}).encode())
        value = self.perform(action)
        if not isinstance(value, EngineeringEvaluation):
            raise StoreError("engineering executor returned no scientific record")
        self._check_value(action, value)
        after = self.batch.replay()
        new = [r for key, r in after.reservations.items() if key not in before.reservations]
        return self._save_result(action, value, new)

    def _save_result(self, action, value, reservations):
        self._check_value(action, value)
        self._check_physical(action, value, self.batch.replay(), reservations)
        ref = put_bytes(self.batch.root, value.to_json().encode(), name="engineering-evaluation.json",
                        media_type="application/json", producer="utility-engineering")
        result = self._result(action, value, len(reservations))
        document = {"action_digest": digest(action.to_dict()), "result": result.to_dict(), "evidence": ref.to_dict(),
                    "reservations": [r.id for r in reservations]}
        durable_write(self._path(action, "result"), (canonical_json(document) + "\n").encode())
        self.fault("engineering_result_saved")
        return result

    def _check_value(self, action, value):
        if tuple(s.scenario_id for s in value.scenarios) != self.profile.scenario_ids:
            raise StoreError("engineering executor changed scenario order")
        if dict(value.evaluation.configuration) != dict(action.config):
            raise StoreError("engineering configuration differs from pending action")
        engineering_decision(value, (), self.profile.rules)

    def _check_physical(self, action, value, state, reservations):
        if len(reservations) != len(self.profile.scenario_ids) or len({r.id for r in reservations}) != len(reservations):
            raise StoreError("engineering work differs from physical profile")
        for reservation, scenario in zip(reservations, self.profile.scenario_ids):
            from .engineering_process import SupervisedEngineeringExecutor, engineering_invocation_identity
            expected = (engineering_invocation_identity(self.perform.spec, action, scenario, self.case_id)
                        if isinstance(self.perform, SupervisedEngineeringExecutor) else
                        digest({"action": action.to_dict(), "scenario": scenario, "profile": self.profile.digest}))
            if (reservation.resource != "science" or reservation.case_id != self.case_id
                    or reservation.invocation_digest != expected):
                raise StoreError("engineering physical identity differs")
            observation = state.observations.get(reservation.id)
            if observation is None or not observation.stop_verified:
                raise StoreError("engineering physical execution remains uncertain")
            if value.evaluation.status == "success" and observation.status != "success":
                raise StoreError("failed physical work cannot become scientific success")
            for ref in observation.evidence:
                read_bytes(self.batch.root, ref)

    def _result(self, action, value, cost):
        status = value.evaluation.status
        if status == "success" and eligible(value.evaluation, self.profile.rules):
            return EvaluationResult.success(action.id, dict(value.evaluation.metrics), {}, cost,
                                             "physical_executions", evaluator_seconds=value.evaluation.elapsed_seconds)
        return EvaluationResult(action.id, EvaluationStatus(
            status if status != "success" else "scientific_infeasible"),
            cost=cost, cost_unit="physical_executions", evaluator_seconds=value.evaluation.elapsed_seconds,
            message="See pinned engineering evidence")

    def run(self, *, max_new_evaluations=None):
        # The optimizer owns its study lock. Each physical callback owns the
        # existing batch operation lock; nesting that lock would reject dispatch.
        try:
            return self.study.run(max_new_evaluations=max_new_evaluations)
        except EngineeringReconciliationRequired:
            self.study.release_pending_writer()
            raise


def engineering_evaluator(bridge: EngineeringStudy):
    """Resolve the registered engineering callback without importing model code."""
    return bridge._evaluate
