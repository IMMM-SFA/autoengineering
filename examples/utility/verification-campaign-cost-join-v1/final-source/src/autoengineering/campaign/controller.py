"""Local campaign broker: immutable identity, durable launches and scientific decisions."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
import hashlib
import io
from pathlib import Path
import sys
import uuid

import numpy as np
import yaml

from autoengineering.adapters.contracts import PrepareContext, validate_arrays

from .acceptance import CheckContext, DEFAULT_CHECKS, decide, metrics
from .artifacts import confined_file, put_bytes, read_arrays, read_bytes, reference
from .budget import BudgetAccount, BudgetExhausted
from .execution import cancellation_intent, pending_cancellations, supervise
from .identity import scientific_identity, verify_dependencies, verify_runtime_sources
from .records import (
    ArtifactRef,
    AttemptRecord,
    CampaignEvent,
    CandidateProposal,
    CandidateSnapshot,
    EvaluationRecord,
    CheckResult,
    Request,
    Response,
)
from .runtime import registry, validate_policy
from .serialization import canonical_json, digest
from .service import CampaignError, CampaignService, Transition
from .spec import CampaignSpec
from .state import ControllerState
from .store import EventStore, Projection, durable_write, checked_directory


class CampaignController:
    """One trusted broker. No external caller supplies code, import names or label paths."""

    def __init__(
        self, store: EventStore, spec: CampaignSpec, *, max_new_evaluations: int | None = None
    ):
        if max_new_evaluations is not None and (
            type(max_new_evaluations) is not int or max_new_evaluations < 0
        ):
            raise ValueError("invocation allowance must be a nonnegative integer")
        self.store, self.spec = store, spec
        self.bundle = store.root / "bundle"
        self.remaining = max_new_evaluations
        self.service = CampaignService(
            store,
            spec,
            allow_scientific=True,
            cancel_handler=self._queue_cancel,
            report_reader=self._read_report,
            handlers={
                name: getattr(self, f"_{name}")
                for name in (
                    "diagnostics",
                    "propose",
                    "admit",
                    "evaluate",
                    "review",
                    "freeze",
                    "confirm",
                    "report",
                )
            },
        )

    @classmethod
    def create(cls, specification: Path, source_root: Path, workdir: Path, **kwargs):
        specification = Path(specification)
        spec = (
            CampaignSpec.from_json(specification.read_text(encoding="utf-8"))
            if specification.suffix.lower() == ".json"
            else CampaignSpec.from_yaml(specification)
        )
        validate_policy(spec)
        identity = scientific_identity(spec, source_root)
        verify_runtime_sources(spec)
        adapters = registry(spec=spec, root=source_root)
        for adapter_id in spec.execution.adapter_ids:
            adapters.validate(adapter_id, spec.baseline.model, source_root)
        # Validation and dependency checks finish before creating any work directory.
        refs = (
            spec.baseline.system,
            spec.provenance.environment_lock,
            *spec.provenance.sources,
            *(data.artifact for data in spec.data),
        )
        copied = {ref.path: read_bytes(source_root, ref) for ref in refs}
        store = EventStore.create(workdir)
        (store.root / "bundle").mkdir(mode=0o700)
        for path, content in copied.items():
            target = store.root / "bundle" / path
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            durable_write(target, content)
        durable_write(
            store.root / "campaign.yaml", yaml.safe_dump(spec.to_dict(), sort_keys=False).encode()
        )
        durable_write(
            store.root / "identity.json",
            canonical_json(
                {
                    "scientific_identity": identity,
                    "spec_digest": spec.digest,
                    "source_root": str(Path(source_root).absolute()),
                    "source_manifest": verify_dependencies(spec, source_root),
                }
            ).encode(),
        )
        return cls(store, spec, **kwargs)

    @classmethod
    def open(cls, workdir: Path, *, inspect_only: bool = False, **kwargs):
        store = EventStore(workdir)
        spec = CampaignSpec.from_yaml(confined_file(store.root, "campaign.yaml"))
        identity = json.loads(confined_file(store.root, "identity.json").read_text())
        if spec.digest != identity["spec_digest"]:
            raise CampaignError("identity_mismatch")
        # Read-only inspection remains possible if original code or data are unavailable.
        if not inspect_only:
            validate_policy(spec)
            try:
                verify_runtime_sources(spec)
                for adapter_id in spec.execution.adapter_ids:
                    registry(spec=spec, root=store.root / "bundle").validate(
                        adapter_id, spec.baseline.model, store.root / "bundle"
                    )
                current = scientific_identity(spec, Path(identity["source_root"]))
                bundled = scientific_identity(spec, store.root / "bundle")
            except (ValueError, OSError) as error:
                raise CampaignError("identity_mismatch") from error
            if current != bundled or current != identity["scientific_identity"]:
                raise CampaignError("identity_mismatch")
        store.replay()
        return cls(store, spec, **kwargs)

    def state(self, projection: Projection | None = None) -> ControllerState:
        projection = projection or self.store.replay()
        for event in reversed(projection.events):
            state_id = event.response.result.get("state_id")
            if state_id:
                ref = next((ref for ref in event.artifacts if ref.sha256 == state_id), None)
                if ref is None:
                    raise ValueError("committed controller state is missing")
                return ControllerState.from_json(read_bytes(self.store.root, ref).decode())
        settings = self.spec.execution
        return ControllerState(
            BudgetAccount(
                settings.max_executions,
                settings.active_deadline_seconds,
                settings.timeout_seconds
                + settings.termination_grace_seconds
                + settings.kill_wait_seconds,
            )
        )

    def _transition(self, target, state, result=None, artifacts=()):
        if target == "completed" and state.confirmation == "pending":
            state = replace(state, confirmation="confirmation_not_attempted")
        ref = put_bytes(
            self.store.root,
            (state.to_json() + "\n").encode(),
            name="state.json",
            media_type="application/json",
            producer="controller",
        )
        return Transition(target, dict(result or {}, state_id=ref.sha256), (*artifacts, ref))

    def _checkpoint(self, target, state, operation, artifacts=(), result=None):
        """Internal transitions share the active writer lock; IDs cannot collide with tools."""
        projection = self.store.replay()
        transition = self._transition(target, state, result, artifacts)
        request_id = f"internal-{uuid.uuid4().hex}"
        response = Response(
            request_id,
            "ok",
            projection.revision + 1,
            transition.result,
            None,
            tuple(ref.sha256 for ref in transition.artifacts),
        )
        self.store.commit(
            CampaignEvent(
                response.revision,
                digest({"internal": request_id}),
                projection.head_hash,
                "controller",
                operation,
                projection.state,
                target,
                response,
                transition.artifacts,
            )
        )
        return self.store.replay()

    def stage_record(self, record, name="record.json") -> str:
        """Broker-only artifact admission. Worker tools receive only the returned digest."""
        with self.store.writer():
            projection = self.store.replay()
            ref = put_bytes(
                self.store.root,
                (record.to_json() + "\n").encode(),
                name=name,
                media_type="application/json",
                producer="trusted-author",
            )
            self._checkpoint(projection.state, self.state(projection), "stage", (ref,))
            return ref.sha256

    def _asset(self, artifact_id: str, record_type=None):
        for event in reversed(self.store.replay().events):
            for ref in event.artifacts:
                if ref.sha256 == artifact_id:
                    if record_type:
                        return record_type.from_json(read_bytes(self.store.root, ref).decode())
                    return ref
        raise CampaignError("schema_error")

    def _diagnostics(self, request, projection):
        self._asset(request.payload["artifact_id"])
        return self._transition(
            "proposal_open",
            self.state(projection),
            {"diagnostic_id": request.payload["artifact_id"]},
        )

    def _propose(self, request, projection):
        state = self.state(projection)
        proposal = self._asset(request.payload["proposal_id"], CandidateProposal)
        if len(state.proposals) >= self.spec.workflow.max_candidates:
            raise CampaignError("budget_exhausted")
        if any(item.id == proposal.id for item in state.proposals):
            raise CampaignError("schema_error")
        allowed = next(
            (item for item in self.spec.interventions if item.target == proposal.target), None
        )
        if allowed is None or proposal.implementation_id not in allowed.implementation_ids:
            raise CampaignError("schema_error")
        return self._transition(
            "candidate_pending",
            replace(state, proposals=(*state.proposals, proposal), active_candidate=proposal.id),
            {"candidate_id": proposal.id},
        )

    def _validate_snapshot(self, snapshot):
        baseline = self.spec.baseline.model
        allowed = next(
            item for item in self.spec.interventions if item.target == snapshot.proposal.target
        )
        if snapshot.adapter_id not in self.spec.execution.adapter_ids:
            raise ValueError("unadmitted adapter")
        if (
            snapshot.model.graph_digest != baseline.graph_digest
            or snapshot.model.inputs != baseline.inputs
            or snapshot.model.outputs != baseline.outputs
        ):
            raise ValueError("candidate topology/interface differs")
        expected = dict(
            baseline.implementations,
            **{snapshot.proposal.target: snapshot.proposal.implementation_id},
        )
        if dict(snapshot.model.implementations) != expected:
            raise ValueError("candidate changes an undeclared component")
        declared = {ref.path: ref for ref in self.spec.provenance.sources}
        if any(declared.get(ref.path) != ref for ref in snapshot.model.source_bundle):
            raise ValueError("candidate has undeclared source dependencies")
        registry(spec=self.spec, root=self.bundle).validate(
            snapshot.adapter_id, snapshot.model, self.bundle
        )
        if snapshot.adapter_id.startswith("generated-"):
            from autoengineering.adapters.registration import load_registration, validate_model

            registration, refs = load_registration(
                self.bundle, expected_identity=snapshot.adapter_id.removeprefix("generated-")
            )
            validate_model(registration, refs, snapshot.model, snapshot.fixed_parameters)
        for name, value in snapshot.fixed_parameters.items():
            if name in allowed.parameter_bounds:
                low, high = allowed.parameter_bounds[name]
                if type(value) not in (int, float) or not low <= value <= high:
                    raise ValueError("candidate parameter is outside allowed bounds")
            elif name == "pet" and snapshot.adapter_id == "hydrology":
                if f"{value}-v1" != snapshot.proposal.implementation_id:
                    raise ValueError("PET configuration and implementation identity differ")
            elif name == "family" and snapshot.adapter_id == "routing":
                if f"{value}-v1" != snapshot.proposal.implementation_id:
                    raise ValueError("routing configuration and implementation identity differ")
            elif name == "method" and snapshot.adapter_id == "solar-pvlib":
                if {"faiman": "faiman-v1", "sapm_module": "sapm-v1"}.get(value) != (
                    snapshot.proposal.implementation_id
                ):
                    raise ValueError("solar thermal method and implementation identity differ")
            elif self.spec.baseline.parameters.get(name) != value:
                raise ValueError("candidate changes an undeclared parameter")
        if set(snapshot.fixed_parameters) != set(self.spec.baseline.parameters):
            raise ValueError("candidate parameter interface differs")
        expected_space = (
            self.spec.calibration.run.search_space.to_dict() if self.spec.calibration else []
        )
        if snapshot.parameter_space_digest != digest(expected_space):
            raise ValueError("candidate parameter space identity differs")

    def _admit(self, request, projection):
        state = self.state(projection)
        snapshot = self._asset(request.payload["snapshot_id"], CandidateSnapshot)
        if (
            snapshot.proposal != state.proposals[-1]
            or snapshot.proposal.id != state.active_candidate
        ):
            raise CampaignError("schema_error")
        try:
            self._validate_snapshot(snapshot)
        except (ValueError, OSError):
            return self._transition(
                "proposal_open",
                replace(state, active_candidate=None),
                {"admitted": False, "reason": "interface_or_source_rejected"},
            )
        return self._transition(
            "candidate_ready",
            replace(state, snapshots=(*state.snapshots, snapshot)),
            {"admitted": True, "candidate_id": snapshot.proposal.id},
        )

    def _data(self, role):
        matches = [data for data in self.spec.data if data.role == role]
        if len(matches) != 1:
            raise ValueError(f"expected one {role} data contract")
        return matches[0]

    def _arrays(self, data):
        if data.artifact.media_type == "application/json":
            return {
                key: np.asarray(value)
                for key, value in json.loads(read_bytes(self.bundle, data.artifact)).items()
            }
        return read_arrays(self.bundle, data.artifact)

    def _data_availability(self):
        """Availability/alignment is checked before a costly model start, without filling gaps."""
        forcing = self._data("forcing")
        try:
            validate_arrays(self._arrays(forcing), self.spec.baseline.model.inputs, forcing.ports)
        except (ValueError, TypeError, KeyError):
            return "invalid_task"
        for role in ("comparison", "fitting") if self.spec.calibration else ("comparison",):
            data = self._data(role)
            try:
                validate_arrays(self._arrays(data), data.ports, data.ports)
                if any(
                    port.time is not None and not any(port.time.scoring_mask) for port in data.ports
                ):
                    return "insufficient_data"
            except (ValueError, TypeError, KeyError):
                return "insufficient_data"
        return None

    def _score(
        self,
        model_id,
        configuration,
        status,
        outputs,
        attempt_id,
        elapsed,
        output_refs,
        role,
        forcing_override=None,
    ):
        data = self._data(role) if role != "diagnostic" else None
        forcing = (
            forcing_override
            if forcing_override is not None
            else self._arrays(self._data("forcing"))
        )
        checks = tuple(
            DEFAULT_CHECKS.evaluate(check, CheckContext(outputs, forcing, configuration))
            for check in self.spec.acceptance.checks
        )
        values = {}
        if status == "success" and data is not None:
            try:
                observations = self._arrays(data)["prediction"]
            except (KeyError, ValueError):
                observations = np.asarray([])
            predicted = np.asarray(outputs["prediction"])
            if predicted.ndim:
                full_dates = self.spec.baseline.model.outputs[0].time.dates
                dates = data.ports[0].time.dates
                indexes = {value: index for index, value in enumerate(full_dates)}
                predicted = predicted[[indexes[value] for value in dates]]
            if data.ports[0].time is not None:
                mask = np.asarray(data.ports[0].time.scoring_mask)
                observations, predicted = observations[mask], predicted[mask]
            values = metrics(np.atleast_1d(observations), np.atleast_1d(predicted))
        return EvaluationRecord(
            f"evaluation-{attempt_id}-{role}",
            model_id,
            configuration,
            status,
            values,
            checks,
            output_refs,
            data.id if data else "diagnostic",
            attempt_id,
            elapsed,
            {"campaign_spec": self.spec.digest, "acceptance": self.spec.acceptance.digest},
        )

    def _physical(self, model_id, model, adapter_id, parameters, role, reservation_id, **kwargs):
        try:
            return self._physical_attempt(
                model_id, model, adapter_id, parameters, role, reservation_id, **kwargs
            )
        except Exception:
            state = self.state()
            unresolved = [
                item
                for item in state.budget.attempts
                if item.state not in ("finished", "reconciled")
            ]
            if not unresolved:
                raise
            attempt = unresolved[-1]
            state = replace(
                state,
                budget=state.budget.resolve(
                    replace(attempt, state="uncertain", uncertain_cost=True)
                ),
                resume_state="evaluating",
            )
            self._checkpoint("reconciliation_required", state, "supervision_failed")
            return EvaluationRecord(
                f"unresolved-{attempt.id}",
                model_id,
                parameters,
                "infrastructure_failure",
                {},
                (),
                (),
                role,
                attempt.id,
                0.0,
                {"cost_uncertain": "true", "reason": "supervisor_or_result_failure"},
            )

    def _physical_attempt(
        self,
        model_id,
        model,
        adapter_id,
        parameters,
        role,
        reservation_id,
        *,
        action_id=None,
        purpose=None,
        forcing_override=None,
        causal_reference=None,
        seed=None,
    ):
        state = self.state()
        if self.remaining is not None and self.remaining < 1:
            return None
        if pending_cancellations(self.store.root, self.spec.name):
            raise CampaignError("invalid_transition")
        identity = json.loads(confined_file(self.store.root, "identity.json").read_text())
        verify_dependencies(self.spec, Path(identity["source_root"]))
        verify_runtime_sources(self.spec)
        registry(spec=self.spec, root=self.bundle).validate(adapter_id, model, self.bundle)
        attempt_id = f"attempt-{len(state.budget.attempts) + 1:06d}"
        nonce = uuid.uuid4().hex
        attempt = AttemptRecord(
            attempt_id, reservation_id, "launched", action_id, nonce, None, None, True, None
        )
        budget = state.budget.start(attempt)
        state = replace(state, budget=budget)
        self._checkpoint(
            "evaluating", state, "action_reserved", (forcing_override,) if forcing_override else ()
        )
        if self.remaining is not None:
            self.remaining -= 1
        jobs = self.store.root / "jobs"
        jobs.mkdir(mode=0o700, exist_ok=True)
        checked_directory(jobs)
        output_path = jobs / f"{attempt_id}.npz"
        scratch = jobs
        if adapter_id.startswith("generated-"):
            from .container_execution import scratch_path

            scratch = scratch_path(self.store.root, attempt_id, nonce)
            scratch.mkdir(mode=0o700)
        context = PrepareContext(
            model, parameters, self.spec.seed if seed is None else seed, str(scratch), ()
        )
        job = {
            "context": context.to_dict(),
            "adapter_id": adapter_id,
            "bundle_root": str(self.bundle),
            "forcing": (forcing_override or self._data("forcing").artifact).to_dict(),
            "forcing_root": str(self.store.root if forcing_override else self.bundle),
            "output_path": str(output_path),
            "model_id": model_id,
            "role": role,
            "purpose": purpose or role,
            "nonce": nonce,
            "causal_reference": causal_reference.to_dict() if causal_reference else None,
        }
        if adapter_id.startswith("generated-"):
            job["attempt_id"] = attempt_id
        job_path = jobs / f"{attempt_id}.json"
        durable_write(job_path, canonical_json(job).encode())
        result = supervise(
            (sys.executable, "-m", "autoengineering.campaign.model_worker", str(job_path)),
            root=self.store.root,
            attempt_id=attempt_id,
            campaign_id=self.spec.name,
            settings=self.spec.execution,
            cwd=Path.cwd(),
            launch_nonce=nonce,
            invocation_remaining_seconds=self.spec.execution.active_deadline_seconds
            - state.budget.charged_seconds
            + state.budget.timeout_reservation_seconds,
        )
        output_refs, outputs = (), {}
        lifecycle_ref = None
        status = result.status
        if status == "success":
            try:
                metadata_path = output_path.with_suffix(".metadata.json")
                metadata = json.loads(metadata_path.read_text())
                content = output_path.read_bytes()
                if hashlib.sha256(content).hexdigest() != metadata["output_sha256"]:
                    raise ValueError("worker output digest mismatch")
                lifecycle_ref = put_bytes(
                    self.store.root,
                    metadata_path.read_bytes(),
                    name="lifecycle.json",
                    media_type="application/json",
                    producer=attempt_id,
                )
                ref = put_bytes(
                    self.store.root,
                    content,
                    name="outputs.npz",
                    media_type="application/x-npz",
                    producer=attempt_id,
                )
                outputs = read_arrays(self.store.root, ref)
                output_refs = (ref,)
            except (ValueError, KeyError, OSError):
                status = "infrastructure_failure"
        receipt = reference(
            self.store.root,
            f"attempts/{attempt_id}/supervisor-result.json",
            media_type="application/json",
            producer="supervisor",
        )
        certain = result.stopped and (result.receipt_valid or result.stop_reason is not None)
        inner_receipt = None
        if adapter_id.startswith("generated-"):
            try:
                if not certain:
                    raise ValueError("native owner stop remains unresolved")
                proof, inner_receipt = self._isolated_proof(
                    attempt, job=job, stop=True, outputs=outputs if status == "success" else None
                )
                certain = proof.stopped
                if not certain:
                    status = "infrastructure_failure"
            except (ValueError, OSError, TypeError, KeyError):
                certain, status = False, "infrastructure_failure"
        attempt = replace(
            attempt,
            state="finished" if certain else "uncertain",
            measured_cost=1.0 if certain else None,
            elapsed_seconds=result.elapsed_seconds,
            uncertain_cost=not certain,
            receipt=receipt,
        )
        state = self.state()
        state = replace(state, budget=state.budget.resolve(attempt))
        evaluation = self._score(
            model_id,
            parameters,
            status,
            outputs,
            attempt_id,
            result.elapsed_seconds,
            output_refs,
            role,
            read_arrays(self.store.root, forcing_override) if forcing_override else None,
        )
        if causal_reference and status == "success":
            evaluation = self._causal_check(evaluation, outputs, causal_reference)
        provenance = dict(
            evaluation.provenance, purpose=purpose or role, execution_seed=str(context.seed)
        )
        if lifecycle_ref:
            provenance["lifecycle_record"] = lifecycle_ref.sha256
        if inner_receipt:
            provenance["isolated_execution_record"] = inner_receipt.sha256
        if not certain:
            provenance["cost_uncertain"] = "true"
        evaluation = replace(evaluation, provenance=provenance)
        state = replace(state, evaluations=(*state.evaluations, evaluation))
        target = "evaluating" if certain else "reconciliation_required"
        if result.stop_reason == "timeout" and certain:
            target, state = "completed", replace(state, outcome="failed_execution")
        if result.stop_reason == "cancelled" and certain:
            target, state = "completed", replace(state, outcome="cancelled")
        self._checkpoint(
            target,
            state,
            "action_finished",
            (
                *output_refs,
                receipt,
                *((lifecycle_ref,) if lifecycle_ref else ()),
                *((inner_receipt,) if inner_receipt else ()),
            ),
        )
        return evaluation

    def _isolated_proof(self, attempt, *, job=None, stop=False, outputs=None):
        """Verify the native owner is gone before inspecting or stopping inner work."""
        from .container_execution import reconcile_attempt
        from .execution import ProcessIdentity, live_members

        folder = self.store.root / "attempts" / attempt.id
        identity = ProcessIdentity(**json.loads(confined_file(folder, "process.json").read_text()))
        if identity.nonce != attempt.launch_nonce or live_members(identity.pgid):
            raise ValueError("native owner stop remains unresolved")
        if job is None:
            job = json.loads(confined_file(self.store.root, f"jobs/{attempt.id}.json").read_text())
        if job.get("adapter_id") not in self.spec.execution.adapter_ids:
            raise ValueError("isolated adapter is outside the frozen catalogue")
        proof = reconcile_attempt(
            self.store.root, job, attempt_id=attempt.id, nonce=attempt.launch_nonce, stop=stop
        )
        if outputs is not None:
            if not proof.stopped:
                raise ValueError("isolated container stop remains unresolved")
            recovered = proof.outputs(PrepareContext.from_dict(job["context"]).model.outputs)
            if set(outputs) != set(recovered) or any(
                not np.array_equal(outputs[name], value) for name, value in recovered.items()
            ):
                raise ValueError("native outputs differ from the isolated execution result")
        record = asdict(proof)
        if record["physical"] is not None:
            raw = record["physical"].pop("stdout")
            record["physical"]["stdout_sha256"] = (
                hashlib.sha256(raw).hexdigest() if raw is not None else None
            )
        receipt = put_bytes(
            self.store.root,
            canonical_json(
                {"attempt_id": attempt.id, "nonce": attempt.launch_nonce, **record}
            ).encode(),
            name="isolated-recovery.json",
            media_type="application/json",
            producer="controller",
        )
        return proof, receipt

    def _evaluate(self, request, projection):
        state = self.state(projection)
        if pending_cancellations(self.store.root, self.spec.name):
            if state.budget.unresolved_attempts:
                return self._transition("reconciliation_required", state)
            return self._transition("completed", replace(state, outcome="cancelled"))
        candidate_id, mode = request.payload["candidate_id"], request.payload["mode"]
        if projection.state == "created":
            issue = self._data_availability()
            if issue:
                return self._transition(
                    "completed", replace(state, outcome=issue), {"data_status": issue}
                )
        if state.active_mode is not None and mode != state.active_mode:
            raise CampaignError("invalid_transition")
        if candidate_id == "baseline" and state.baseline is None:
            if candidate_id != "baseline" or mode != "fixed":
                raise CampaignError("schema_error")
            model, parameters, adapter_id = (
                self.spec.baseline.model,
                self.spec.baseline.parameters,
                self.spec.baseline.adapter_id,
            )
            model_id = model.digest
        else:
            if candidate_id != state.active_candidate:
                raise CampaignError("schema_error")
            snapshot = next(item for item in state.snapshots if item.proposal.id == candidate_id)
            model, parameters, adapter_id = (
                snapshot.model,
                snapshot.fixed_parameters,
                snapshot.adapter_id,
            )
            model_id = snapshot.digest
        if mode == "calibrate" and self.spec.calibration is None:
            raise CampaignError("schema_error")
        if self.remaining == 0:
            return self._transition(projection.state, state, {"paused": True})
        if mode == "calibrate":
            from .studies import run_child

            return run_child(self, request, model_id, model, adapter_id, parameters)
        reservation_id = f"fixed-{candidate_id}"
        try:
            budget = (
                state.budget
                if any(item.id == reservation_id for item in state.budget.reservations)
                else state.budget.reserve(reservation_id, 1, invocation_remaining=self.remaining)
            )
        except BudgetExhausted:
            return self._transition("completed", replace(state, outcome="budget_exhausted"))
        state = replace(
            state, budget=budget, active_reservation=reservation_id, active_mode="fixed"
        )
        self._checkpoint("evaluating", state, "reserved")
        prior_attempts = {
            item.id for item in state.budget.attempts if item.reservation_id == reservation_id
        }
        evaluation = next(
            (item for item in state.evaluations if item.attempt_id in prior_attempts), None
        )
        if evaluation is None:
            evaluation = self._physical(
                model_id, model, adapter_id, parameters, "comparison", reservation_id
            )
        state = self.state()
        target = self.store.replay().state
        if target == "reconciliation_required" or state.outcome:
            return self._transition(target, state)
        state = replace(
            state,
            budget=state.budget.release(reservation_id),
            active_reservation=None,
            active_mode=None,
        )
        if candidate_id == "baseline":
            state = replace(state, baseline=evaluation)
            target = "baseline_ready"
        else:
            target = "evidence_ready"
        return self._transition(target, state, {"evaluation_id": evaluation.id})

    def _review(self, request, projection):
        state = self.state(projection)
        if projection.state == "reconciliation_required":
            return self._reconcile(request, state)
        wanted = request.payload.get("evaluation_id")
        if wanted:
            candidate = next((item for item in state.evaluations if item.id == wanted), None)
            if candidate is None or candidate.split_id != self._data("comparison").id:
                raise CampaignError("schema_error")
            new_decisions = (decide(state.baseline, (candidate,), self.spec.acceptance),)
        else:
            snapshot = next(
                item for item in state.snapshots if item.proposal.id == state.active_candidate
            )
            comparisons = [
                item
                for item in state.evaluations
                if item.model_id == snapshot.digest and item.split_id == self._data("comparison").id
            ]
            new_decisions = []
            for candidate in comparisons:
                comparator = state.baseline
                if candidate.provenance.get("purpose", "").startswith("calibrated:"):
                    earlier = [
                        item
                        for item in state.evaluations
                        if item.model_id != snapshot.digest
                        and item.provenance.get("purpose", "").startswith("calibrated:")
                        and item.split_id == self._data("comparison").id
                    ]
                    if earlier:
                        comparator = earlier[-1]
                new_decisions.append(decide(comparator, (candidate,), self.spec.acceptance))
            if not new_decisions:
                new_decisions = [decide(state.baseline, (), self.spec.acceptance)]
        state = replace(state, decisions=(*state.decisions, *new_decisions), active_candidate=None)
        last = new_decisions[-1]
        return self._transition(
            "proposal_open", state, {"outcome": last.outcome, "selected_id": last.selected_id}
        )

    def _freeze(self, request, projection):
        state = self.state(projection)
        comparisons = tuple(
            item
            for item in state.evaluations
            if item.split_id == self._data("comparison").id and item.id != state.baseline.id
        )
        decision = decide(state.baseline, comparisons, self.spec.acceptance)
        outcome = decision.outcome
        if not state.proposals and decision.selected_id is not None:
            outcome = "no_suitable_intervention"
        if all(item.status != "success" for item in (state.baseline, *comparisons)):
            outcome = "failed_execution"
        elif all(
            item.metrics.get(self.spec.acceptance.primary_metric) is None
            for item in (state.baseline, *comparisons)
        ):
            outcome = "insufficient_data"
        state = replace(
            state,
            frozen_id=decision.selected_id,
            outcome=outcome,
            decisions=(*state.decisions, decision),
        )
        return self._transition(
            "selection_frozen", state, {"outcome": outcome, "selected_id": decision.selected_id}
        )

    def _confirm(self, request, projection):
        state = self.state(projection)
        if state.outcome is None or (
            projection.state != "selection_frozen" and state.phase != "confirmation"
        ):
            raise CampaignError("invalid_transition")
        if pending_cancellations(self.store.root, self.spec.name):
            if state.budget.unresolved_attempts:
                return self._transition("reconciliation_required", state)
            return self._transition("completed", replace(state, outcome="cancelled"))
        if self.spec.confirmation.mode == "disabled":
            return self._transition(
                "report_ready",
                replace(state, confirmation="confirmation_not_attempted"),
                {"confirmation": "confirmation_not_attempted"},
            )
        if self.spec.confirmation.protocol != "eligibility-v1":
            raise CampaignError("schema_error")
        # Synthetic confirmation evaluates the frozen choice once. It can never reopen selection.
        if state.confirmation != "pending":
            raise CampaignError("invalid_transition")
        if state.frozen_id is None:
            return self._transition("report_ready", replace(state, confirmation="unavailable"))
        selected = next(item for item in state.evaluations if item.id == state.frozen_id)
        snapshot = next(
            (item for item in state.snapshots if item.digest == selected.model_id), None
        )
        model = snapshot.model if snapshot else self.spec.baseline.model
        adapter = snapshot.adapter_id if snapshot else self.spec.baseline.adapter_id
        reservation_id = "confirmation"
        if self.remaining == 0:
            return self._transition("selection_frozen", state, {"paused": True})
        budget = (
            state.budget
            if any(item.id == reservation_id for item in state.budget.reservations)
            else state.budget.reserve(reservation_id, 1, invocation_remaining=self.remaining)
        )
        self._checkpoint(
            "evaluating",
            replace(state, budget=budget, phase="confirmation"),
            "confirmation_reserved",
        )
        evaluation = next(
            (item for item in state.evaluations if item.split_id == self._data("confirmation").id),
            None,
        )
        if evaluation is None:
            evaluation = self._physical(
                selected.model_id,
                model,
                adapter,
                selected.configuration,
                "confirmation",
                reservation_id,
            )
        state = self.state()
        if self.store.replay().state != "evaluating":
            return self._transition(self.store.replay().state, state)
        from .acceptance import eligible

        status = "pass" if eligible(evaluation, self.spec.acceptance) else "fail"
        state = replace(
            state, budget=state.budget.release(reservation_id), confirmation=status, phase="model"
        )
        return self._transition("report_ready", state, {"confirmation": status})

    def _report(self, request, projection):
        from .report import render_report

        state = self.state(projection)
        ref = put_bytes(
            self.store.root,
            render_report(self.spec, state, artifact_prefix="../../").encode(),
            name="report.md",
            media_type="text/markdown",
            producer="reporter",
        )
        return self._transition(
            "completed", state, {"report_id": ref.sha256, "outcome": state.outcome}, (ref,)
        )

    def _reconcile(self, request, state):
        from .execution import ProcessIdentity, identity_matches, live_members, stop_recovered

        wanted = request.payload.get("reconcile_attempt_id")
        attempt = next((item for item in state.budget.attempts if item.id == wanted), None)
        if attempt is None or attempt.state != "uncertain":
            raise CampaignError("schema_error")
        path = self.store.root / "attempts" / attempt.id / "process.json"
        if path.exists():
            identity = ProcessIdentity(**json.loads(path.read_text()))
            if identity.nonce != attempt.launch_nonce:
                raise CampaignError("reconciliation_required")
            if live_members(identity.pgid):
                if not identity_matches(identity) or not stop_recovered(
                    identity, self.spec.execution
                ):
                    raise CampaignError("reconciliation_required")
        elif (self.store.root / "attempts" / attempt.id / "launch-intent.json").exists():
            # No PID receipt means that this process cannot prove which group to stop.
            raise CampaignError("reconciliation_required")
        inner_receipt = None
        try:
            job_path = self.store.root / "jobs" / f"{attempt.id}.json"
            if not job_path.exists() and any(
                name.startswith("generated-") for name in self.spec.execution.adapter_ids
            ):
                raise ValueError("isolated attempt job is missing")
            if job_path.exists():
                job = json.loads(confined_file(job_path.parent, job_path.name).read_text())
                if job["adapter_id"].startswith("generated-"):
                    proof, inner_receipt = self._isolated_proof(attempt, job=job, stop=True)
                    if not proof.stopped:
                        raise ValueError("isolated container stop remains unresolved")
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise CampaignError("reconciliation_required") from error
        resolved = replace(attempt, state="reconciled", uncertain_cost=True)
        state = replace(state, budget=state.budget.resolve(resolved))
        target = state.resume_state or "evaluating"
        if any(item.state not in ("finished", "reconciled") for item in state.budget.attempts):
            target = "reconciliation_required"
        else:
            state = replace(state, resume_state=None)
            if pending_cancellations(self.store.root, self.spec.name):
                target, state = "completed", replace(state, outcome="cancelled")
            elif attempt.child_action_id is None:
                # A fixed/diagnostic evaluation has no optimizer action to retire.
                # A lost result cannot be silently retried under the same allowance.
                if state.phase == "confirmation":
                    target, state = (
                        "report_ready",
                        replace(state, confirmation="unavailable", phase="model"),
                    )
                else:
                    target, state = "completed", replace(state, outcome="failed_execution")
        return self._transition(
            target,
            state,
            {
                "reconciled_attempt_id": attempt.id,
                "cost_note": "Physical allowance retained; unknown cost is not zero",
            },
            artifacts=(inner_receipt,) if inner_receipt else (),
        )

    def request(self, operation, payload=None, *, request_id=None):
        projection = self.store.replay()
        request = Request(
            "1.0",
            self.spec.name,
            request_id or f"request-{uuid.uuid4().hex}",
            projection.revision,
            operation,
            payload or {},
        )
        return self.service.handle(request)

    def _read_report(self, request, projection):
        from .report import render_report

        return Response(
            request.request_id,
            "ok",
            projection.revision,
            {"report": render_report(self.spec, self.state(projection))},
            None,
            (),
        )

    def _queue_cancel(self, request, projection):
        path = self.store.root / "control" / f"cancel-{request.request_id}.json"
        if path.is_file() and not path.is_symlink():
            previous = json.loads(path.read_text())
            if previous.get("request_digest") == request.digest:
                return Response.from_dict(previous["response"])
            return Response(
                request.request_id, "error", projection.revision, {}, "request_conflict", ()
            )
        if request.expected_revision != projection.revision:
            return self.service._side_rejection(request, "stale_revision", projection.revision)
        if (
            len(tuple((self.store.root / "control").glob("cancel-*.json")))
            >= self.spec.workflow.max_transport_requests
        ):
            return Response(
                request.request_id, "error", projection.revision, {}, "budget_exhausted", ()
            )
        intent = cancellation_intent(
            self.store.root,
            request.request_id,
            campaign_id=self.spec.name,
            envelope=request,
            revision=projection.revision,
        )
        return Response.from_dict(intent["response"])

    def cancel(self, request_id):
        from .records import identifier

        identifier(request_id)
        control = self.store.root / "control"
        if (
            not (control / f"cancel-{request_id}.json").exists()
            and len(tuple(control.glob("cancel-*.json")))
            >= self.spec.workflow.max_transport_requests
        ):
            raise CampaignError("budget_exhausted")
        return cancellation_intent(self.store.root, request_id, campaign_id=self.spec.name)

    def supplied_snapshots(self):
        """Deterministic author-supplied queue, not model or literature discovery."""
        for intervention in self.spec.interventions:
            for implementation in intervention.implementation_ids:
                if (
                    implementation == self.spec.baseline.model.implementations[intervention.target]
                    and self.spec.calibration is None
                ):
                    continue
                proposal = CandidateProposal(
                    f"{intervention.target}-{implementation}",
                    intervention.target,
                    implementation,
                    "Evaluate the supplied implementation and frozen parameter space",
                    (),
                    "Measure the declared comparison",
                    None,
                    (),
                )
                parameters = dict(self.spec.baseline.parameters)
                if self.spec.baseline.adapter_id == "hydrology":
                    parameters["pet"] = implementation.removesuffix("-v1")
                elif self.spec.baseline.adapter_id == "solar-pvlib":
                    parameters["method"] = {"faiman-v1": "faiman", "sapm-v1": "sapm_module"}[
                        implementation
                    ]
                elif self.spec.baseline.adapter_id == "routing":
                    from examples.campaign_contracts.routing import PARAMETERS

                    parameters = dict(PARAMETERS[implementation.removesuffix("-v1")])
                elif (
                    self.spec.baseline.adapter_id == "linear"
                    and implementation
                    != self.spec.baseline.model.implementations[intervention.target]
                ):
                    parameters["multiplier"] = 1.5
                model = replace(
                    self.spec.baseline.model,
                    implementations=dict(
                        self.spec.baseline.model.implementations,
                        **{intervention.target: implementation},
                    ),
                )
                space = (
                    self.spec.calibration.run.search_space.to_dict()
                    if self.spec.calibration
                    else []
                )
                yield CandidateSnapshot(
                    proposal,
                    model,
                    implementation
                    if implementation.startswith("generated-")
                    else self.spec.baseline.adapter_id,
                    digest(space),
                    parameters,
                )

    def advance(self):
        """Run the scripted local workflow until terminal, paused, or reconciliation is needed."""
        self.recover()
        while True:
            projection = self.store.replay()
            state = self.state(projection)
            if projection.state in ("completed", "reconciliation_required"):
                return projection
            if pending_cancellations(self.store.root, self.spec.name):
                with self.store.writer():
                    self._checkpoint("completed", replace(state, outcome="cancelled"), "cancelled")
                return self.store.replay()
            if projection.state == "created":
                operation, payload = "evaluate", {"candidate_id": "baseline", "mode": "fixed"}
            elif projection.state == "baseline_ready":
                from .records import CheckResult

                diagnostic = CheckResult(
                    "diagnosis",
                    "1",
                    "pass",
                    False,
                    self.spec.scientific_scope,
                    None,
                    None,
                    "Evaluate only the declared supplied interventions",
                    (),
                )
                asset = self.stage_record(diagnostic, "diagnostic.json")
                operation, payload = "diagnostics", {"artifact_id": asset}
            elif projection.state == "proposal_open":
                supplied = next(
                    (
                        snapshot
                        for snapshot in self.supplied_snapshots()
                        if snapshot.proposal.id not in {item.id for item in state.proposals}
                    ),
                    None,
                )
                if supplied is None or len(state.proposals) >= self.spec.workflow.max_candidates:
                    if self.spec.execution.diagnostics != "none" and not self._diagnostics_complete(
                        state
                    ):
                        if not self._run_diagnostics():
                            return self.store.replay()
                        continue
                    operation, payload = "freeze", {}
                else:
                    proposal_id = self.stage_record(supplied.proposal, "proposal.json")
                    operation, payload = "propose", {"proposal_id": proposal_id}
            elif projection.state == "candidate_pending":
                supplied = next(
                    item
                    for item in self.supplied_snapshots()
                    if item.proposal.id == state.active_candidate
                )
                asset = self.stage_record(supplied, "snapshot.json")
                operation, payload = "admit", {"snapshot_id": asset}
            elif projection.state == "evaluating" and state.phase == "diagnostics":
                if not self._run_diagnostics():
                    return self.store.replay()
                continue
            elif projection.state == "evaluating" and state.phase == "confirmation":
                operation, payload = "confirm", {}
            elif projection.state in ("candidate_ready", "evaluating"):
                operation, payload = (
                    "evaluate",
                    {
                        "candidate_id": state.active_candidate or "baseline",
                        "mode": state.active_mode
                        or ("calibrate" if self.spec.calibration else "fixed"),
                    },
                )
            elif projection.state == "evidence_ready":
                operation, payload = "review", {}
            elif projection.state == "selection_frozen":
                operation, payload = "confirm", {}
            elif projection.state == "report_ready":
                operation, payload = "report", {}
            else:
                raise ValueError("unsupported campaign workflow state")
            response = self.request(operation, payload)
            if response.status == "error":
                raise CampaignError(response.error)
            if response.result.get("paused"):
                return self.store.replay()

    def _recover_finished(self, attempt):
        """Recover only a hash-verified completed worker result after its process group is gone."""
        from .execution import ProcessIdentity, live_members

        folder = self.store.root / "attempts" / attempt.id
        try:
            identity = ProcessIdentity(
                **json.loads(confined_file(folder, "process.json").read_text())
            )
            if (
                identity.nonce != attempt.launch_nonce
                or type(identity.pid) is not int
                or identity.pid <= 0
                or type(identity.pgid) is not int
                or identity.pgid != identity.pid
                or live_members(identity.pgid)
            ):
                return None
            start = json.loads(confined_file(folder, "action-start.json").read_text())
            finish = json.loads(confined_file(folder, "action-finish.json").read_text())
            if (
                start["nonce"] != finish["nonce"]
                or finish["nonce"] != attempt.launch_nonce
                or finish["returncode"] != 0
                or finish["monotonic"] < start["monotonic"]
            ):
                return None
            job = json.loads(confined_file(self.store.root, f"jobs/{attempt.id}.json").read_text())
            if job["nonce"] != attempt.launch_nonce:
                return None
            output_path = confined_file(self.store.root, f"jobs/{attempt.id}.npz")
            metadata = json.loads(
                confined_file(self.store.root, f"jobs/{attempt.id}.metadata.json").read_text()
            )
            if output_path.stat().st_size > 64 * 1024 * 1024:
                return None
            content = output_path.read_bytes()
            if hashlib.sha256(content).hexdigest() != metadata["output_sha256"]:
                return None
            lifecycle_ref = put_bytes(
                self.store.root,
                canonical_json(metadata).encode(),
                name="lifecycle.json",
                media_type="application/json",
                producer=attempt.id,
            )
            ref = put_bytes(
                self.store.root,
                content,
                name="outputs.npz",
                media_type="application/x-npz",
                producer=attempt.id,
            )
            outputs = read_arrays(self.store.root, ref)
            context = PrepareContext.from_dict(job["context"])
            inner_receipt = None
            if job["adapter_id"].startswith("generated-"):
                proof, inner_receipt = self._isolated_proof(attempt, job=job, outputs=outputs)
                if not proof.stopped:
                    return None
            elapsed = finish["monotonic"] - start["monotonic"]
            accounted_seconds = None
            supervisor_path = folder / "supervisor-result.json"
            if supervisor_path.exists():
                supervisor = json.loads(confined_file(folder, "supervisor-result.json").read_text())
                if (
                    supervisor["identity"]["nonce"] != attempt.launch_nonce
                    or not supervisor["stopped"]
                ):
                    return None
                accounted_seconds = max(elapsed, float(supervisor["elapsed_seconds"]))
            evaluation = self._score(
                job["model_id"],
                context.parameters,
                "success",
                outputs,
                attempt.id,
                elapsed,
                (ref,),
                job["role"],
                read_arrays(self.store.root, ArtifactRef.from_dict(job["forcing"]))
                if job["role"] == "diagnostic"
                else None,
            )
            if job.get("causal_reference"):
                evaluation = self._causal_check(
                    evaluation, outputs, ArtifactRef.from_dict(job["causal_reference"])
                )
            evaluation = replace(
                evaluation,
                provenance=dict(
                    evaluation.provenance,
                    purpose=job["purpose"],
                    execution_seed=str(context.seed),
                    lifecycle_record=lifecycle_ref.sha256,
                    **(
                        {"isolated_execution_record": inner_receipt.sha256} if inner_receipt else {}
                    ),
                ),
            )
            receipt = put_bytes(
                self.store.root,
                canonical_json(
                    {
                        "schema": "campaign-recovery-receipt-v2",
                        "attempt_id": attempt.id,
                        "nonce": attempt.launch_nonce,
                        "identity": identity.to_dict(),
                        "stopped": True,
                        "status": "success",
                        "output_sha256": ref.sha256,
                        "recovered": True,
                        **(
                            {"isolated_execution_record": inner_receipt.to_dict()}
                            if inner_receipt
                            else {}
                        ),
                    }
                ).encode(),
                name="recovery-receipt.json",
                media_type="application/json",
                producer="controller",
            )
            return (
                replace(
                    attempt,
                    state="finished",
                    measured_cost=1.0,
                    elapsed_seconds=accounted_seconds,
                    uncertain_cost=False,
                    receipt=receipt,
                ),
                evaluation,
                (ref, receipt, lifecycle_ref, *((inner_receipt,) if inner_receipt else ())),
            )
        except (ValueError, KeyError, TypeError, OSError):
            return None

    def recover(self):
        """No scientific launch or child recovery until all physical attempts are classified."""
        with self.store.writer():
            projection = self.store.replay()
            state = self.state(projection)
            if projection.state == "completed":
                self.store.refresh_projection()
                return
            unresolved = [
                item
                for item in state.budget.attempts
                if item.state not in ("finished", "reconciled")
            ]
            if unresolved and pending_cancellations(self.store.root, self.spec.name):
                stopped, stop_receipts = self._stop_unresolved(unresolved)
                if stopped:
                    # Stopping work does not turn uncertain cost into a measured zero.
                    self._checkpoint(
                        "completed",
                        replace(state, outcome="cancelled"),
                        "cancelled_after_recovery",
                        stop_receipts,
                    )
                    return
            artifacts = []
            for attempt in unresolved:
                recovered = self._recover_finished(attempt)
                if recovered:
                    resolved, evaluation, refs = recovered
                    state = replace(
                        state,
                        budget=state.budget.resolve(resolved),
                        evaluations=(*state.evaluations, evaluation),
                    )
                    artifacts.extend(refs)
                else:
                    state = replace(
                        state,
                        budget=state.budget.resolve(
                            replace(attempt, state="uncertain", uncertain_cost=True)
                        ),
                    )
            uncertain = state.budget.unresolved_attempts > 0
            target = (
                "reconciliation_required" if uncertain else (state.resume_state or projection.state)
            )
            if uncertain:
                state = replace(state, resume_state=state.resume_state or projection.state)
            elif target == "reconciliation_required":
                target = "evaluating"
            if state != self.state(projection) or target != projection.state:
                self._checkpoint(target, state, "recovery", tuple(artifacts))
            self.store.quarantine_temporaries()
            self.store.refresh_projection()

    def _causal_check(self, evaluation, outputs, source_ref):
        original = read_arrays(self.store.root, source_ref)["prediction"]
        dates = self._data("comparison").ports[0].time.dates
        full_dates = self.spec.baseline.model.outputs[0].time.dates
        cutoff = full_dates.index(dates[0])
        difference = float(np.max(abs(outputs["prediction"][:cutoff] - original[:cutoff])))
        result = CheckResult(
            "causal_prefix",
            "1",
            "pass" if difference <= 1e-12 else "fail",
            True,
            "future forcing cannot alter earlier simulated discharge",
            difference,
            1e-12,
            "Prefix before the first comparison date",
            (source_ref,),
        )
        return replace(evaluation, checks=(*evaluation.checks, result))

    def _diagnostic_sources(self, state):
        return tuple(
            item
            for item in state.evaluations
            if item.split_id == self._data("comparison").id
            and item.provenance.get("purpose", "").startswith("calibrated:")
        )

    def _diagnostics_complete(self, state):
        completed = {
            item.provenance.get("purpose")
            for item in state.evaluations
            if item.split_id == "diagnostic"
        }
        return all(f"causal:{item.id}" in completed for item in self._diagnostic_sources(state))

    def _run_diagnostics(self):
        with self.store.writer():
            state = self.state()
            completed = {
                item.provenance.get("purpose")
                for item in state.evaluations
                if item.split_id == "diagnostic"
            }
            missing = [
                item
                for item in self._diagnostic_sources(state)
                if f"causal:{item.id}" not in completed
            ]
            if self.remaining is not None and self.remaining < len(missing):
                return False
            reservation_id = "causality"
            try:
                budget = (
                    state.budget
                    if any(item.id == reservation_id for item in state.budget.reservations)
                    else state.budget.reserve(
                        reservation_id, len(missing), invocation_remaining=self.remaining
                    )
                )
            except BudgetExhausted:
                self._checkpoint(
                    "completed",
                    replace(state, outcome="budget_exhausted"),
                    "diagnostic_budget_exhausted",
                )
                return False
            self._checkpoint(
                "evaluating",
                replace(state, budget=budget, phase="diagnostics"),
                "diagnostics_reserved",
            )
            for original in missing:
                source = next(item for item in state.snapshots if item.digest == original.model_id)
                forcing = {
                    name: value.copy()
                    for name, value in self._arrays(self._data("forcing")).items()
                }
                if "precip_mm" not in forcing:
                    raise ValueError("causality profile requires hydrology precipitation")
                full_dates = self.spec.baseline.model.outputs[0].time.dates
                cutoff = full_dates.index(self._data("comparison").ports[0].time.dates[0])
                forcing["precip_mm"][cutoff:] += 100.0
                buffer = io.BytesIO()
                np.savez(buffer, **forcing)
                forcing_ref = put_bytes(
                    self.store.root,
                    buffer.getvalue(),
                    name="causal-forcing.npz",
                    media_type="application/x-npz",
                    producer="declared-causality-protocol",
                )
                evaluation = self._physical(
                    original.model_id,
                    source.model,
                    source.adapter_id,
                    original.configuration,
                    "diagnostic",
                    reservation_id,
                    forcing_override=forcing_ref,
                    causal_reference=original.outputs[0],
                    purpose=f"causal:{original.id}",
                )
                if self.store.replay().state != "evaluating":
                    return False
                if evaluation.status != "success" or any(
                    check.required and check.status != "pass" for check in evaluation.checks
                ):
                    self._checkpoint(
                        "completed",
                        replace(self.state(), outcome="failed_execution"),
                        "causality_failed",
                    )
                    return False
            state = self.state()
            self._checkpoint(
                "proposal_open",
                replace(state, budget=state.budget.release(reservation_id), phase="model"),
                "diagnostics_finished",
            )
            return True

    def _stop_unresolved(self, attempts):
        from .execution import ProcessIdentity, identity_matches, live_members, stop_recovered

        receipts = []
        for attempt in attempts:
            folder = self.store.root / "attempts" / attempt.id
            path = folder / "process.json"
            if not path.exists():
                if (folder / "launch-intent.json").exists():
                    return False, tuple(receipts)
                continue
            try:
                identity = ProcessIdentity(
                    **json.loads(confined_file(folder, "process.json").read_text())
                )
                if identity.nonce != attempt.launch_nonce:
                    return False, tuple(receipts)
                if live_members(identity.pgid) and (
                    not identity_matches(identity)
                    or not stop_recovered(identity, self.spec.execution)
                ):
                    return False, tuple(receipts)
                job_path = self.store.root / "jobs" / f"{attempt.id}.json"
                if not job_path.exists():
                    if any(
                        name.startswith("generated-") for name in self.spec.execution.adapter_ids
                    ):
                        return False, tuple(receipts)
                    continue
                job = json.loads(confined_file(job_path.parent, job_path.name).read_text())
                if job["adapter_id"].startswith("generated-"):
                    proof, receipt = self._isolated_proof(attempt, job=job, stop=True)
                    receipts.append(receipt)
                    if not proof.stopped:
                        return False, tuple(receipts)
            except (OSError, ValueError, TypeError, KeyError):
                return False, tuple(receipts)
        return True, tuple(receipts)
