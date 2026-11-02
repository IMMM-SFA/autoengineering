"""Trusted supplied-candidate broker over the existing scientific controller.

Workers receive approved scalar summaries. They never receive the controller,
its service, its store root, or a callable for arbitrary scientific operations.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import hashlib
from typing import TYPE_CHECKING

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import (
    CandidateProposal,
    CandidateSnapshot,
    CheckResult,
    Request,
)
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError

from .records import (
    ArtifactGrant,
    CampaignAction,
    NextStep,
    ReviewFindings,
    ReviewDisposition,
    RoleHandoff,
    ScientificAttempt,
    ScientificReceipt,
    SuppliedConfiguration,
    TaskAssignment,
)
from .scheduler import SerialScheduler
from .permissions import role_operations
from .records import SINGLE_ROLE
from .store import serialized_operation
from .deadline import ScientificDeadline

if TYPE_CHECKING:
    from autoengineering.campaign.controller import CampaignController

METRICS = ("rmse", "bias", "relative_bias", "correlation", "nse", "kge")


def action_id(kind: str, key: str) -> str:
    return f"{kind}-{digest(key)[:24]}"


class WorkflowStopped(StoreError):
    """A visible role or scientific stop, with its evidence retained."""


class CampaignBroker:
    workflow_route = "four_role"
    review_description = "independent review"

    def __init__(self, controller: CampaignController, scheduler: SerialScheduler):
        self.controller, self.scheduler, self.store = controller, scheduler, scheduler.store
        if self.store.spec.workflow_route != self.workflow_route:
            raise StoreError("broker differs from the frozen workflow route")
        identity = unique_json((controller.store.root / "identity.json").read_text())
        if (self.store.spec.campaign_id, self.store.spec.campaign_identity) != (
            controller.spec.name,
            identity["scientific_identity"],
        ):
            raise StoreError("worker and scientific campaign identities differ")
        allowed = {
            implementation
            for item in controller.spec.interventions
            for implementation in item.implementation_ids
        }
        if not set(self.store.spec.permitted_interventions) <= allowed:
            raise StoreError("worker run expands scientific interventions")
        self.catalogue = {
            (snapshot.proposal.target, snapshot.proposal.implementation_id): snapshot
            for snapshot in controller.supplied_snapshots()
            if snapshot.proposal.implementation_id in self.store.spec.permitted_interventions
        }

    def _resolve_action(self, action: CampaignAction) -> CampaignAction:
        """Caller holds the operation lease; external work holds no journal writer."""
        if action.state == "completed":
            return action
        if action.kind == "request":
            # Obtain an already committed response first, even after expiry.
            # This replay cannot start work and must retain the exact envelope.
            committed = action.request.request_id in self.controller.store.replay().responses
            guard = self._deadline(action.id)
            if committed:
                response = self.controller.service.handle(action.request)
            else:
                with guard:
                    response = self.controller.service.handle(action.request)
            with self.store.writer():
                completed = self.store.commit(replace(action, state="completed", response=response))
            if committed and guard.deadline <= self.scheduler.clock():
                guard.expire()
                guard._check_forwarding()
            return completed
        kinds = {
            "stage_proposal": CandidateProposal,
            "stage_snapshot": CandidateSnapshot,
            "stage_diagnostic": CheckResult,
        }
        raw = read_bytes(self.store.root, action.source)
        record = kinds[action.kind].from_json(raw.decode())
        # A lost stage acknowledgment can be reconciled by the exact committed
        # artifact. Do not call stage_record again and create another checkpoint.
        expected = hashlib.sha256((record.to_json() + "\n").encode()).hexdigest()
        for event in self.controller.store.replay().events:
            for ref in event.artifacts:
                if ref.sha256 == expected:
                    read_bytes(self.controller.store.root, ref)
                    with self.store.writer():
                        return self.store.commit(
                            replace(action, state="completed", staged_id=expected)
                        )
        staged = self.controller.stage_record(record, f"{action.kind}.json")
        if staged != expected:
            raise StoreError("scientific staging identity differs from submitted bytes")
        with self.store.writer():
            return self.store.commit(replace(action, state="completed", staged_id=staged))

    @serialized_operation
    def reconcile_actions(self):
        for action in self.store.replay().actions.values():
            if action.state == "reserved":
                action = self._resolve_action(action)
            if action.response is not None and action.response.status == "error":
                raise WorkflowStopped(f"campaign request failed: {action.response.error}")

    def cancel(self):
        """Queue both intents without either journal writer. Stops need separate receipts."""
        worker_intent = self.store.request_cancel()
        scientific_intent = self.controller.cancel(action_id("cancel", self.store.spec.id))
        return {
            "worker_intent": worker_intent,
            "scientific_intent": scientific_intent,
            "worker_stop": "queued",
            "scientific_stop": "queued",
        }

    def prepare_implementation(
        self, *, baseline, specification, qualification_root, qualification_digest
    ):
        """Trusted public fixtures; worker text supplies only the permitted source."""
        from .preparation import SourcePreparation

        return SourcePreparation(self, qualification_root, qualification_digest).prepare(
            baseline=baseline, specification=specification
        )

    def _deadline(self, action=None):
        return ScientificDeadline(
            self.store,
            clock=self.scheduler.clock,
            cancel_science=self.controller.cancel,
            action_id=action,
        )

    def _require_time(self):
        guard = self._deadline()
        if guard.deadline <= self.scheduler.clock():
            guard.expire()
            guard._check_forwarding()
            raise WorkflowStopped("worker run deadline exhausted; cancellation queued")
        if self.scheduler._cancelled():
            raise WorkflowStopped("worker cancellation queued")

    def dispose_review(self, invocation_id: str, *, reason: str, decision="continue"):
        """Trusted caller only: retain original findings and bind the explicit reason."""
        with self.store.writer():
            projection = self.store.replay()
            invocation = projection.invocations.get(invocation_id)
            if invocation is None:
                raise StoreError("review invocation is absent")
            handoff = self.scheduler.handoff(invocation)
            if not isinstance(handoff.output, ReviewFindings):
                raise StoreError("disposition requires review findings")
            science = self.controller.store.replay()
            if science.state != "evidence_ready" or handoff.campaign_revision != science.revision:
                raise StoreError("review disposition context is stale")
            disposition = ReviewDisposition(
                "1.0", self.store.spec.id, invocation_id, handoff.output.digest, reason, decision
            )
            return self.store.commit(disposition)

    @serialized_operation
    def stage(self, kind: str, key: str, record, *, invocation_id=None) -> str:
        identity = action_id(kind, key)
        with self.store.writer():
            previous = self.store.replay().actions.get(identity)
            if previous is None:
                self._require_time()
                source = self.store.put_private(
                    record.to_json().encode(), name="staging.json", media_type="application/json"
                )
                previous = self.store.commit(
                    CampaignAction(
                        "1.0",
                        identity,
                        self.store.spec.id,
                        kind,
                        "reserved",
                        invocation_id,
                        source,
                        None,
                        None,
                        None,
                    )
                )
            elif read_bytes(self.store.root, previous.source) != record.to_json().encode():
                raise StoreError("staged logical identity has different content")
        return self._resolve_action(previous).staged_id

    @serialized_operation
    def request(self, operation: str, payload=None, *, key: str, invocation_id=None):
        identity = action_id(operation, key)
        with self.store.writer():
            previous = self.store.replay().actions.get(identity)
            if previous is None:
                self._require_time()
                projection = self.controller.store.replay()
                request = Request(
                    "1.0",
                    self.controller.spec.name,
                    identity,
                    projection.revision,
                    operation,
                    payload or {},
                )
                previous = self.store.commit(
                    CampaignAction(
                        "1.0",
                        identity,
                        self.store.spec.id,
                        "request",
                        "reserved",
                        invocation_id,
                        None,
                        request,
                        None,
                        None,
                    )
                )
            elif (previous.request.operation, dict(previous.request.payload)) != (
                operation,
                dict(payload or {}),
            ):
                raise StoreError("logical campaign request has different content")
        response = self._resolve_action(previous).response
        if response.status == "error":
            raise WorkflowStopped(f"campaign request failed: {response.error}")
        return response

    def summary(self) -> dict:
        """Construct an allowlist projection. Never serialize/redact controller state."""
        projection = self.controller.store.replay()
        state = self.controller.state(projection)
        calibration = self.controller.spec.calibration
        studies = {link.study_id: link for link in state.studies}
        evaluations = []
        for evaluation in state.evaluations:
            if evaluation.split_id not in {
                data.id
                for data in self.controller.spec.data
                if data.role in ("comparison", "fitting")
            }:
                continue
            purpose = evaluation.provenance.get("purpose", "")
            study_id = purpose.removeprefix("calibrated:")
            study_id = (
                study_id if purpose.startswith("calibrated:") and study_id in studies else None
            )
            evaluations.append(
                {
                    "id": evaluation.id,
                    "model_id": evaluation.model_id,
                    "configuration": dict(evaluation.configuration),
                    "split_id": evaluation.split_id,
                    "purpose": "calibrated"
                    if purpose.startswith("calibrated:")
                    else purpose
                    if purpose in {"comparison", "fitting"}
                    else "other",
                    "calibration_study_id": study_id,
                    "status": evaluation.status,
                    "metrics": {
                        name: evaluation.metrics[name]
                        for name in METRICS
                        if name in evaluation.metrics
                    },
                    "checks": [
                        {
                            "name": check.name,
                            "status": check.status,
                            "required": check.required,
                            "version": check.version,
                            "value": check.value,
                            "threshold": check.threshold,
                        }
                        for check in evaluation.checks
                    ],
                }
            )
        return {
            "schema_version": "1.1",
            "campaign_id": self.controller.spec.name,
            "revision": projection.revision,
            "state": projection.state,
            "objective": {
                "metric": self.controller.spec.acceptance.primary_metric,
                "direction": self.controller.spec.acceptance.direction,
                "minimum_gain": self.controller.spec.acceptance.minimum_gain,
                "secondary_tolerances": dict(self.controller.spec.acceptance.secondary_tolerances),
            },
            "catalogue": [
                {
                    "target": target,
                    "implementation_id": implementation,
                    "parameters": dict(snapshot.fixed_parameters),
                    "parameter_role": "starting" if calibration else "fixed",
                }
                for (target, implementation), snapshot in self.catalogue.items()
            ],
            "interface": [
                {"name": port.name, "units": port.units, "dimensions": list(port.dimensions)}
                for port in self.controller.spec.baseline.model.outputs
            ],
            "evaluations": evaluations,
            "calibration": None
            if calibration is None
            else {
                "owner": "trusted_controller",
                "policy": calibration.run.policy,
                "seed": calibration.run.study.seed,
                "fitting_data_id": calibration.fitting_data_id,
                "objective": {
                    "metric": calibration.run.study.objective.outcome,
                    "direction": calibration.run.study.objective.direction,
                },
                "parameter_space": calibration.run.search_space.to_dict(),
            },
            "calibration_studies": [
                {
                    "study_id": link.study_id,
                    "candidate_id": link.candidate_id,
                    "seed": link.seed,
                    "run_spec_digest": link.run_spec_digest,
                    "committed_manifest_sha256": None
                    if link.committed_manifest is None
                    else link.committed_manifest.sha256,
                }
                for link in state.studies
            ],
            "input_interface": [
                {"name": port.name, "units": port.units, "dimensions": list(port.dimensions)}
                for port in self.controller.spec.baseline.model.inputs
            ],
            "data_exposure": [
                {"role": data.role, "prior_exposure": data.prior_exposure}
                for data in self.controller.spec.data
            ],
            "proposed_interventions": [
                {"target": p.target, "implementation_id": p.implementation_id}
                for p in state.proposals
            ],
            "outcome": state.outcome,
            "confirmation": state.confirmation,
            "confirmation_policy": self.controller.spec.confirmation.mode,
            "limitations": [
                "Approved summaries expose development feedback.",
                "Relative acceptance does not establish absolute predictive skill.",
            ],
        }

    def _registered_review_context(self, snapshot):
        if not snapshot.adapter_id.startswith("generated-"):
            return {}
        from autoengineering.adapters.registration import load_registration

        registration, refs = load_registration(
            self.controller.bundle, expected_identity=snapshot.adapter_id.removeprefix("generated-")
        )
        return {
            "registered_implementation": {
                "registration_identity": registration.digest,
                "capture_digest": registration.capture.digest,
                "source_digest": registration.capture.source_digest,
                "source_text": read_bytes(
                    self.controller.bundle, refs[1], max_bytes=65536
                ).decode(),
                "public_interface": registration.specification.to_dict(),
                "interface_receipt": registration.interface_receipt.to_dict(),
                "qualification_digest": registration.review.qualification_digest,
            }
        }

    def _record_science(self, projection, state):
        decision = state.decisions[-1] if state.decisions else None
        selected_id = decision.selected_id if decision else None
        selected = next((e for e in state.evaluations if e.id == selected_id), None)
        receipt = ScientificReceipt(
            "1.0",
            self.store.spec.id,
            self.store.spec.campaign_identity,
            projection.revision,
            projection.state,
            self.controller.spec.acceptance.primary_metric,
            self.controller.spec.acceptance.direction,
            state.outcome,
            selected_id,
            decision.selected_configuration if decision else None,
            selected.metrics.get(self.controller.spec.acceptance.primary_metric)
            if selected
            else None,
            state.confirmation,
            self.controller.spec.execution.max_executions,
            tuple(
                ScientificAttempt(
                    a.id,
                    a.reservation_id,
                    a.state,
                    a.child_action_id,
                    a.measured_cost,
                    a.elapsed_seconds,
                    a.uncertain_cost,
                )
                for a in state.budget.attempts
            ),
            state.budget.measured_cost,
            state.budget.cost_is_uncertain,
            {data.id: data.prior_exposure for data in self.controller.spec.data},
            state.budget.committed_capacity,
            self.scheduler.clock(),
        )
        with self.store.writer():
            previous = self.store.replay().science
            if previous and previous[-1].revision == receipt.revision:
                receipt = replace(receipt, recorded_at=previous[-1].recorded_at)
                if previous[-1] != receipt:
                    raise StoreError("scientific evidence changed without a campaign revision")
            else:
                self.store.commit(receipt)

    def _role(
        self,
        role: str,
        key: str,
        question: str,
        *,
        candidate_id=None,
        evaluation_id=None,
        context: dict | None = None,
        validate: Callable[[RoleHandoff], None] | None = None,
        expected_schema: str = "role-handoff-1.0",
    ):
        task_id = action_id(role, key)
        projection = self.store.replay()
        task = projection.tasks.get(task_id)
        if task is None:
            self._require_time()
            summary = self.summary()
            if context is not None:
                summary["submitted_handoff"] = context
            with self.store.writer():
                ref = self.store.put_private(
                    canonical_json(summary).encode(),
                    name="summary.json",
                    media_type="application/json",
                )
            scope_version = "1.1" if role == SINGLE_ROLE else "1.0"
            grant = ArtifactGrant(
                scope_version,
                self.store.spec.id,
                task_id,
                role,
                ref,
                "read",
                65536,
                "worker_summary",
            )
            task = TaskAssignment(
                scope_version,
                task_id,
                self.store.spec.id,
                role,
                None,
                summary["revision"],
                question,
                (grant,),
                expected_schema,
                tuple(sorted(role_operations(role))),
                self.scheduler.clock() + self.store.spec.limits.elapsed_seconds,
                self.store.spec.limits.repairs_per_task,
            )
        elif task.expected_schema != expected_schema:
            raise StoreError("persisted task has a different handoff schema")
        # Replay a previously completed role even if its own subsequent staging
        # checkpoint advanced science. Never create another host call for it.
        prior = [value for value in projection.invocations.values() if value.task_id == task.id]
        if prior and prior[-1].state == "completed":
            value = self.scheduler.handoff(prior[-1])
            if value.status != "complete" or value.proposed_next_action == "stop":
                raise WorkflowStopped(f"{role} stopped: {value.status}")
            if validate:
                validate(value)
            return value

        def check(value):
            if self.controller.store.replay().revision != task.campaign_revision:
                raise ValueError("scientific revision changed during worker invocation")
            if value.status != "complete" or value.proposed_next_action == "stop":
                # Preserve a valid worker stop; it is not malformed output.
                return
            if validate:
                validate(value)

        while True:
            pending = self.store.replay().pending
            if pending:
                if len(pending) != 1 or pending[0].task_id != task.id:
                    raise WorkflowStopped(
                        "pending worker does not match the current scientific stage"
                    )
                invocation = self.scheduler.recover_invocation(
                    pending[0].id,
                    campaign_revision=self.controller.store.replay().revision,
                    candidate_id=candidate_id,
                    evaluation_id=evaluation_id,
                    validator=check,
                )
            else:
                projection = self.store.replay()
                prior = [
                    value for value in projection.invocations.values() if value.task_id == task.id
                ]
                repairs = sum(value.attempt > 0 for value in projection.invocations.values())
                if prior and (
                    prior[-1].attempt >= task.repair_allowance
                    or repairs >= self.store.spec.limits.max_repairs
                ):
                    raise WorkflowStopped(f"{role} repair allowance exhausted")
                self._require_time()
                invocation = self.scheduler.dispatch(
                    task,
                    campaign_revision=self.controller.store.replay().revision,
                    candidate_id=candidate_id,
                    evaluation_id=evaluation_id,
                    validator=check,
                )
            if invocation.state == "invalid_output":
                continue  # dispatch enforces persistent task/run repair allowances
            if invocation.state != "completed":
                raise WorkflowStopped(f"{role} invocation ended as {invocation.state}")
            value = self.scheduler.handoff(invocation)
            if value.status != "complete" or value.proposed_next_action == "stop":
                raise WorkflowStopped(f"{role} stopped: {value.status}")
            return value

    def _coordinate(self, key: str, expected_role: str | None, *, may_freeze=False):
        def validate(value):
            output = value.output
            if not isinstance(output, NextStep):
                raise ValueError("orchestrator requires a next step")
            if output.action == "stop":
                return
            if output.action == "freeze":
                if not may_freeze:
                    raise ValueError("freeze is not legal before required role evidence")
            elif output.role != expected_role:
                raise ValueError("orchestrator assigned a role outside the current stage")

        return self._role(
            "orchestrator",
            key,
            f"Recommend {expected_role or 'freeze'} or stop for this stage.",
            validate=validate,
        )

    def _propose_or_freeze(self, slot, can_investigate, validate):
        next_step = self._coordinate(
            slot, "investigator" if can_investigate else None, may_freeze=True
        )
        if next_step.output.action == "freeze":
            return next_step
        if not can_investigate:
            raise WorkflowStopped("candidate allowance exhausted")
        return self._role(
            "investigator",
            slot,
            "Propose an untried supplied intervention.",
            validate=validate,
        )

    def advance(self):
        """Execute legal supplied transitions until terminal, paused, or a visible stop."""
        self.reconcile_actions()
        self.controller.recover()
        while True:
            projection = self.controller.store.replay()
            state = self.controller.state(projection)
            self._record_science(projection, state)
            if self.scheduler._cancelled():
                self.controller.cancel(action_id("cancel", self.store.spec.id))
                raise WorkflowStopped(
                    "worker cancellation queued; scientific stop requires reconciliation"
                )
            phase = projection.state
            if phase in ("completed", "reconciliation_required"):
                return projection
            self._require_time()
            key = f"revision-{projection.revision}"
            if phase == "created":
                response = self.request(
                    "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, key=key
                )
            elif phase == "baseline_ready":
                check = CheckResult(
                    "diagnosis",
                    "1",
                    "pass",
                    False,
                    "supplied_interventions",
                    None,
                    None,
                    "Evaluate only admitted supplied implementations",
                    (),
                )
                asset = self.stage("stage_diagnostic", "baseline", check)
                response = self.request("diagnostics", {"artifact_id": asset}, key="baseline")
            elif phase == "proposal_open":
                tried = {(p.target, p.implementation_id) for p in state.proposals}
                remaining = set(self.catalogue) - tried
                can_investigate = (
                    bool(remaining)
                    and len(state.proposals) < self.controller.spec.workflow.max_candidates
                )
                slot = f"proposal-{len(state.proposals)}"

                def validate(value):
                    brief = value.output
                    if (brief.target, brief.implementation_id) not in remaining:
                        raise ValueError("candidate is not an untried supplied intervention")
                    if brief.eligibility_gaps:
                        raise ValueError("candidate brief has unresolved eligibility gaps")
                    if any(p.id == brief.candidate_id for p in state.proposals):
                        raise ValueError("candidate identity was already proposed")

                result = self._propose_or_freeze(slot, can_investigate, validate)
                if isinstance(result.output, NextStep):
                    if result.output.action != "freeze":
                        raise WorkflowStopped("proposal stage requires a candidate or freeze")
                    if self.controller.spec.execution.diagnostics != "none" and not (
                        self.controller._diagnostics_complete(state)
                    ):
                        if not self.controller._run_diagnostics():
                            return self.controller.store.replay()
                    response = self.request("freeze", key=slot, invocation_id=result.invocation_id)
                else:
                    brief = result.output
                    proposal = CandidateProposal(
                        brief.candidate_id,
                        brief.target,
                        brief.implementation_id,
                        brief.hypothesis,
                        brief.evidence_ids,
                        brief.expected_tradeoffs,
                        None,
                        (),
                    )
                    asset = self.stage(
                        "stage_proposal", slot, proposal, invocation_id=result.invocation_id
                    )
                    response = self.request(
                        "propose",
                        {"proposal_id": asset},
                        key=slot,
                        invocation_id=result.invocation_id,
                    )
            elif phase == "candidate_pending":
                if self.store.spec.execution_mode == "generated":
                    return projection  # Trusted public fixtures are supplied to preparation separately.
                proposal = next(p for p in state.proposals if p.id == state.active_candidate)
                self._coordinate(f"implement-{proposal.id}", "implementer")
                template = self.catalogue[(proposal.target, proposal.implementation_id)]

                def validate(value):
                    configuration = value.output
                    if not isinstance(configuration, SuppliedConfiguration):
                        raise ValueError("supplied workflow requires a supplied configuration")
                    if configuration.implementation_id != proposal.implementation_id:
                        raise ValueError("implementer changed proposed implementation")
                    # The fixed pool has supplied configurations. New parameter
                    # search belongs to the existing controller's calibration.
                    if dict(configuration.parameters) != dict(template.fixed_parameters):
                        raise ValueError("configuration differs from the supplied candidate pool")

                result = self._role(
                    "implementer",
                    proposal.id,
                    "Configure the proposed supplied implementation.",
                    candidate_id=proposal.id,
                    context=proposal.to_dict(),
                    validate=validate,
                )
                snapshot = replace(template, proposal=proposal)
                asset = self.stage(
                    "stage_snapshot", proposal.id, snapshot, invocation_id=result.invocation_id
                )
                response = self.request(
                    "admit",
                    {"snapshot_id": asset},
                    key=proposal.id,
                    invocation_id=result.invocation_id,
                )
            elif phase in ("candidate_ready", "evaluating"):
                if state.phase == "diagnostics":
                    if not self.controller._run_diagnostics():
                        return self.controller.store.replay()
                    continue
                if state.phase == "confirmation":
                    response = self.request("confirm", key=key)
                else:
                    response = self.request(
                        "evaluate",
                        {
                            "candidate_id": state.active_candidate or "baseline",
                            "mode": state.active_mode
                            or ("calibrate" if self.controller.spec.calibration else "fixed"),
                        },
                        key=key,
                    )
            elif phase == "evidence_ready":
                proposal = next(p for p in state.proposals if p.id == state.active_candidate)
                snapshot = next(s for s in state.snapshots if s.proposal.id == proposal.id)
                evaluation = next(
                    e for e in reversed(state.evaluations) if e.model_id == snapshot.digest
                )
                self._coordinate(f"review-{evaluation.id}", "reviewer")

                def validate(value):
                    review = value.output
                    if not isinstance(review, ReviewFindings):
                        raise ValueError("review requires evidence-linked findings")
                    names = {check.name for check in evaluation.checks}
                    if any(not set(f.supporting_checks) <= names for f in review.findings):
                        raise ValueError("review cites checks absent from the evaluation")

                result = self._role(
                    "reviewer",
                    evaluation.id,
                    "Review the immutable candidate and evaluation evidence.",
                    candidate_id=proposal.id,
                    evaluation_id=evaluation.id,
                    context={
                        "proposal": proposal.to_dict(),
                        "snapshot_digest": snapshot.digest,
                        "evaluation_id": evaluation.id,
                        **self._registered_review_context(snapshot),
                    },
                    validate=validate,
                )
                review = result.output
                disposition = self.store.replay().dispositions.get(result.invocation_id)
                if (disposition is not None and disposition.decision == "stop") or (
                    disposition is None
                    and (
                        review.recommendation != "proceed"
                        or review.missing_evidence
                        or any(f.severity == "blocking" for f in review.findings)
                    )
                ):
                    raise WorkflowStopped(f"{self.review_description} has unresolved findings")
                response = self.request(
                    "review", key=evaluation.id, invocation_id=result.invocation_id
                )
            elif phase == "selection_frozen":
                response = self.request("confirm", key="selection")
            elif phase == "report_ready":
                response = self.request("report", key="final")
            else:
                raise WorkflowStopped(f"unsupported scientific phase: {phase}")
            if response.result.get("paused"):
                projection = self.controller.store.replay()
                self._record_science(projection, self.controller.state(projection))
                return self.controller.store.replay()


def workflow_broker(controller, scheduler):
    if scheduler.store.spec.workflow_route == "single_agent":
        from .single_agent import SingleAgentBroker

        return SingleAgentBroker(controller, scheduler)
    return CampaignBroker(controller, scheduler)
