"""Serial conformance cases over a caller-pinned preparation and shared ledger.

Calling this API is execution, separate from preparation or live authorization.
Unsupported cases stop as incomplete. There is no fallback or uncharged retry.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import threading
import time
import uuid

from autoengineering.campaign.artifacts import confined_file, read_bytes, put_bytes
from autoengineering.campaign.records import ArtifactRef, identifier
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import StoreError, checked_directory, durable_write

from .batch import BatchStore
from .batch_native import BatchCodexHost
from .batch_science import BatchCampaignController
from .broker import CampaignBroker, WorkflowStopped
from .command import _bind_host_configuration
from .conformance import IMPLEMENTED_CASES, MALFORMED_LIMITS, load_conformance
from .hosts.base import InvocationContext
from .hosts.command_upstream import recover_command_upstream
from .hosts.command_upstream import inspect_command_stop
from .hosts.subscription import verify_subscription_attempt
from .hosts.subscription_worker import HOST, PORT, ROUTE
from .records import TaskAssignment
from .report import evidence_report
from .scheduler import SerialScheduler
from .store import WorkerStore

MALFORMED_OUTPUT = {"conformance_probe": "deliberately_invalid_handoff"}
MALFORMED_QUESTION = (
    "This is a bounded schema rejection probe. On the initial call (repair is null), "
    "return a transport object whose handoff_json contains exactly "
    '{"conformance_probe":"deliberately_invalid_handoff"}. '
    "This deliberately fails the inner role schema. On the one repair call, return a valid "
    "complete role-handoff-1.0 for this task and invocation, with NextStep stop, role null, "
    "no citations or unresolved issues, and proposed_next_action stop. Do not request tools."
)


TEXT_PROMPT = (
    'Return one transport object whose handoff_json contains exactly {"ack":"conformance"}.'
)


def _json(root, name):
    path = confined_file(root, name)
    with path.open("rb") as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise StoreError("conformance runtime metadata exceeds limit")
    return unique_json(raw.decode())


class MalformedProbeHost(BatchCodexHost):
    """Ask for the invalid probe without also demanding a valid role handoff.

    Only the initial conformance probe changes its instructions. The scheduler's
    parser, grants, journals and one-repair limit remain the ordinary worker path.
    The actual provider must still return the exact invalid payload for the case
    to exercise rejection. No output bytes are injected or rewritten.
    """

    def prepare_prompt(self, task, prompt):
        if (
            self.case_id != "malformed"
            or task.id != "malformed-probe"
            or task.run_id != "conformance-malformed"
            or task.role != "orchestrator"
            or task.grants
            or task.allowed_operations != ("stop",)
        ):
            raise StoreError("malformed probe host requires its fixed diagnostic task")
        context = unique_json(prompt[prompt.index('{"approved_evidence"') :])
        if context["task"] != task.to_dict() or context["approved_evidence"]:
            raise StoreError("malformed probe prompt differs from its fixed task")
        if context["repair"] is None:
            context["output_contract"] = {
                "version": "initial-malformed-probe-1.0",
                "expected_inner": MALFORMED_OUTPUT,
            }
            prompt = (
                "Trusted initial schema-rejection diagnostic. Return exactly "
                "output_contract.expected_inner inside the transport handoff_json string. "
                "This is intentionally not a role handoff: the ordinary parser must reject "
                "it before any scientific action. Do not correct it into a valid handoff. "
                "The single repair call will receive the ordinary role contract. "
                "Do not request tools.\n" + canonical_json(context)
            )
        return super().prepare_prompt(task, prompt)


class ConformanceRuntime:
    def __init__(self, preparation, pin, configuration, batch):
        self.preparation = checked_directory(preparation)
        self.preparation_digest = pin
        self.plan = load_conformance(
            self.preparation, expected_digest=pin, configuration=configuration, allow_runtime=True
        )
        if self.plan.schema_version != "host-conformance-preparation-1.0":
            raise StoreError("Claude conformance execution handlers are not implemented")
        self.configuration, self.batch = configuration, batch
        if str(batch.root) != self.plan.runtime_root or batch.spec != self.plan.batch:
            raise StoreError("conformance runtime differs from original preparation")
        expected = {
            "version": "conformance-runtime-1.0",
            "preparation_digest": pin,
            "batch_digest": batch.digest,
        }
        if _json(batch.root, "origin.json") != expected:
            raise StoreError("conformance runtime origin changed or is incomplete")

    @classmethod
    def create(cls, preparation, *, expected_digest, configuration):
        plan = load_conformance(
            preparation, expected_digest=expected_digest, configuration=configuration
        )
        if plan.schema_version != "host-conformance-preparation-1.0":
            raise StoreError("Claude conformance execution handlers are not implemented")
        batch = BatchStore.create(plan.runtime_root, plan.batch)
        durable_write(
            batch.root / "origin.json",
            canonical_json(
                {
                    "version": "conformance-runtime-1.0",
                    "preparation_digest": expected_digest,
                    "batch_digest": batch.digest,
                }
            ).encode(),
        )
        return cls(preparation, expected_digest, configuration, batch)

    @classmethod
    def open(cls, preparation, *, expected_digest, configuration, runtime_digest):
        plan = load_conformance(
            preparation,
            expected_digest=expected_digest,
            configuration=configuration,
            allow_runtime=True,
        )
        if plan.schema_version != "host-conformance-preparation-1.0":
            raise StoreError("Claude conformance execution handlers are not implemented")
        batch = BatchStore(plan.runtime_root, expected_digest=runtime_digest)
        return cls(preparation, expected_digest, configuration, batch)

    def _provider_evidence(self, scope):
        """Verify saved fixed-worker proof. Never open a credential or make a request."""
        try:
            policy, manifest = verify_subscription_attempt(scope / "upstream")
            if (policy["model"], policy["lease_id"], policy["credential_path"]) != (
                self.plan.worker.host.requested_model,
                self.configuration.lease_id,
                str(self.configuration.credential_path),
            ):
                raise ValueError("provider scope mismatch")
            attempt = scope / "upstream/attempt"
            response = recover_command_upstream(attempt)
            result = _json(attempt, "provider-result.json")
            intent = _json(attempt, "provider-intent.json")
            valid = (
                result["status"] == "response_received"
                and result["http_status"] == 200
                and result["request_may_have_been_sent"] is True
                and result["scope"] == str(scope / "upstream")
                and (intent["host"], intent["port"], intent["path"], intent["automatic_retries"])
                == (HOST, PORT, ROUTE, 0)
                and intent["lease_id"] == self.configuration.lease_id
                and intent["request_sha256"] == policy["request_sha256"]
                and intent["scope"] == result["scope"]
            )
            return {
                "verified": valid,
                "evidence": self.batch.evidence(
                    {
                        "kind": "fixed_worker_response_metadata",
                        "policy": policy,
                        "command_manifest": manifest,
                        "provider_result": result,
                        "provider_intent": intent,
                        "command_completion": _json(attempt / "process", "completion.json"),
                        "response_sha256": hashlib.sha256(response).hexdigest(),
                    }
                ).to_dict(),
                "response_sha256": hashlib.sha256(response).hexdigest(),
                "metadata_hashes": {
                    name: hashlib.sha256(confined_file(attempt, name).read_bytes()).hexdigest()
                    for name in ("provider-result.json", "provider-intent.json")
                },
            }
        except (ValueError, OSError, KeyError, TypeError):
            return {"verified": False, "reason": "fixed_worker_response_proof_unavailable"}

    def _request_evidence(self, scope, *, require_stop=True):
        """A fixed-worker intent proves possible dispatch, not provider acceptance."""
        try:
            policy, manifest = verify_subscription_attempt(scope / "upstream")
            intent = _json(scope / "upstream/attempt", "provider-intent.json")
            valid = (
                (policy["model"], policy["lease_id"], policy["credential_path"])
                == (
                    self.plan.worker.host.requested_model,
                    self.configuration.lease_id,
                    str(self.configuration.credential_path),
                )
                and (intent["host"], intent["port"], intent["path"], intent["automatic_retries"])
                == (HOST, PORT, ROUTE, 0)
                and intent["lease_id"] == policy["lease_id"]
                and intent["request_sha256"] == policy["request_sha256"]
                and intent["scope"] == str(scope / "upstream")
            )
            stopped = inspect_command_stop(scope / "upstream/attempt") if require_stop else None
            if require_stop:
                valid = valid and stopped["state"] == "verified_stopped"
            return {
                "verified": valid,
                "evidence": self.batch.evidence(
                    {
                        "kind": "fixed_worker_request_metadata",
                        "policy": policy,
                        "command_manifest": manifest,
                        "provider_intent": intent,
                        "stop_audit": stopped,
                    }
                ).to_dict()
                if require_stop
                else None,
                "request_may_have_been_sent": True,
                "intent_sha256": hashlib.sha256(
                    confined_file(scope / "upstream/attempt", "provider-intent.json").read_bytes()
                ).hexdigest(),
            }
        except (ValueError, OSError, KeyError, TypeError):
            return {"verified": False, "request_may_have_been_sent": None}

    def _direct(self, case, prompt, *, host=None):
        root = self.batch.root / "cases" / case
        root.mkdir(mode=0o700, exist_ok=True)
        host = host or BatchCodexHost(self.configuration, self.batch, case)
        task = TaskAssignment(
            "1.0",
            case + "-probe",
            self.plan.worker.id,
            "investigator",
            None,
            0,
            prompt,
            (),
            "role-handoff-1.0",
            (),
            self.batch.created_at + self.plan.batch.limits.elapsed_seconds,
            0,
        )
        framed = host.prepare_prompt(task, prompt)
        path = root / "invocation.json"
        saved = path.exists() or path.is_symlink()
        seconds = 1.0 if case == "timeout" else 30
        if not saved:
            durable_write(
                path,
                canonical_json(
                    {
                        "task": task.to_dict(),
                        "prompt": framed,
                        "invocation_id": case + "-call",
                        "nonce": uuid.uuid4().hex,
                        "timeout_seconds": seconds,
                        "output_limit": 65536,
                    }
                ).encode(),
            )
        metadata = _json(root, "invocation.json")
        if (
            set(metadata)
            != {"task", "prompt", "invocation_id", "nonce", "timeout_seconds", "output_limit"}
            or TaskAssignment.from_dict(metadata["task"]) != task
            or metadata["prompt"] != framed
            or metadata["invocation_id"] != case + "-call"
            or type(metadata["timeout_seconds"]) not in (float, int)
            or metadata["timeout_seconds"] != seconds
            or type(metadata["output_limit"]) is not int
            or metadata["output_limit"] != 65536
        ):
            raise StoreError("direct conformance invocation changed")
        identifier(metadata["nonce"])
        cancel, closed = threading.Event(), threading.Event()
        scope = root / metadata["invocation_id"]

        def monitor():
            deadline = time.monotonic() + seconds
            while not closed.wait(0.01) and time.monotonic() < deadline:
                if self._request_evidence(scope, require_stop=False)["verified"]:
                    durable_write(
                        root / "cancel-trigger.json",
                        canonical_json(
                            {
                                "nonce": metadata["nonce"],
                                "phase": "fixed_worker_request_intent",
                                "request_may_have_been_sent": True,
                            }
                        ).encode(),
                    )
                    cancel.set()
                    return

        thread = (
            threading.Thread(target=monitor, name="conformance-cancel", daemon=True)
            if case == "cancel" and not saved
            else None
        )
        context = InvocationContext(
            metadata["invocation_id"],
            metadata["nonce"],
            root / metadata["invocation_id"],
            seconds,
            65536,
            lambda receipt: durable_write(
                root / "native-ownership.json", canonical_json(receipt).encode()
            ),
            cancel.is_set,
        )
        if thread is not None:
            thread.start()
        try:
            result = (
                host.recover_supervised(task, framed, context)
                if saved
                else host.invoke_supervised(task, framed, context)
            )
        finally:
            closed.set()
            if thread is not None:
                thread.join(timeout=1)
                if thread.is_alive():
                    raise StoreError("conformance cancellation monitor stop remains unverified")
        return result, context.directory

    def text(self):
        result, scope = self._direct("text", TEXT_PROMPT)
        provider = self._provider_evidence(scope)
        try:
            content = unique_json(result.raw_output)
        except (ValueError, TypeError):
            content = None
        passed = (
            result.status == "completed"
            and result.stop_verified
            and content == {"ack": "conformance"}
            and result.resolved_model is not None
            and provider["verified"]
        )
        return {
            "passed": passed,
            "kind": "text",
            "host_status": result.status,
            "stop_verified": result.stop_verified,
            "requested_model": self.plan.worker.host.requested_model,
            "resolved_model": result.resolved_model,
            "usage": dict(result.usage),
            "provider": provider,
            "content_matches": content == {"ack": "conformance"},
            "transcripts": self._capture_transcripts(result),
        }

    def _capture_transcripts(self, result):
        if result.elapsed_seconds is None:
            return []
        items = [
            ("native-capture.bin", result.raw_transcript),
            ("native-stderr.bin", result.stderr),
        ]
        return [
            put_bytes(
                self.batch.root,
                raw,
                name=name,
                media_type="application/octet-stream",
                producer="conformance-native-capture",
            ).to_dict()
            for name, raw in items
            if raw is not None
        ]

    def timeout(self):
        result, scope = self._direct("timeout", TEXT_PROMPT)
        request = self._request_evidence(scope)
        return {
            "kind": "timeout",
            "passed": result.status == "timeout" and result.stop_verified and request["verified"],
            "host_status": result.status,
            "stop_verified": result.stop_verified,
            "intended_phase_exercised": request["verified"],
            "request": request,
            "resolved_model": result.resolved_model,
            "usage": dict(result.usage),
            "remote_computation_stopped": "unknown",
            "transcripts": self._capture_transcripts(result),
        }

    def cancel(self):
        result, scope = self._direct("cancel", TEXT_PROMPT)
        request = self._request_evidence(scope)
        trigger_path = scope.parent / "cancel-trigger.json"
        trigger = _json(scope.parent, trigger_path.name) if trigger_path.exists() else None
        metadata = _json(scope.parent, "invocation.json")
        valid_trigger = trigger == {
            "nonce": metadata["nonce"],
            "phase": "fixed_worker_request_intent",
            "request_may_have_been_sent": True,
        }
        return {
            "kind": "cancel",
            "passed": result.status == "cancelled"
            and result.stop_verified
            and request["verified"]
            and valid_trigger,
            "host_status": result.status,
            "stop_verified": result.stop_verified,
            "cancel_intent_recorded": valid_trigger,
            "cancel_trigger": trigger,
            "intended_phase_exercised": request["verified"],
            "request": request,
            "resolved_model": result.resolved_model,
            "usage": dict(result.usage),
            "remote_computation_stopped": "unknown",
            "transcripts": self._capture_transcripts(result),
        }

    def roles(self):
        root = self.batch.root / "cases/roles"
        root.mkdir(mode=0o700, exist_ok=True)
        if (root / "campaign").exists():
            controller = BatchCampaignController.open(
                root / "campaign", batch=self.batch, case_id="roles", max_new_evaluations=2
            )
            controller.reconcile_batch()
        else:
            controller = BatchCampaignController.create(
                self.preparation / self.plan.scientific_specification.path,
                self.preparation / "captured_source",
                root / "campaign",
                batch=self.batch,
                case_id="roles",
                max_new_evaluations=2,
            )
        if (root / "worker").exists():
            worker = WorkerStore(root / "worker")
            worker.require_identity(self.plan.worker)
        else:
            worker = WorkerStore.create(root / "worker", self.plan.worker)
        host = BatchCodexHost(self.configuration, self.batch, "roles")
        _bind_host_configuration(worker, host, self.configuration)
        broker = CampaignBroker(controller, SerialScheduler(worker, host))
        stopped = None
        try:
            broker.advance()
        except WorkflowStopped:
            stopped = "worker_workflow_stopped"
        report = evidence_report(worker)
        clients = list(worker.replay().invocations.values())
        provider = {
            c.id: self._provider_evidence(worker.root / "processes" / c.id) for c in clients
        }
        scientific = report["scientific_evidence"] or {}
        passed = (
            stopped is None
            and report["status"] == "completed"
            and len(clients) == 7
            and set(report["roles_ran"])
            == {"orchestrator", "investigator", "implementer", "reviewer"}
            and report["physical_work"]["attempts"] == 2
            and not report["physical_work"]["cost_is_uncertain"]
            and report["campaign_outcome"] == "accepted_candidate"
            and scientific.get("selected_configuration") == {"multiplier": 1.5}
            and scientific.get("objective_value") == 0
            and all(c.state == "completed" and c.resolved_model is not None for c in clients)
            and all(value["verified"] for value in provider.values())
        )
        return {
            "passed": passed,
            "kind": "roles",
            "worker_status": report["status"],
            "stop": stopped,
            "roles": report["roles_ran"],
            "host_invocations": len(clients),
            "scientific_attempts": report["physical_work"]["attempts"],
            "campaign_outcome": report["campaign_outcome"],
            "scientific_evidence": scientific,
            "providers": provider,
            "worker_run_digest": worker.spec.digest,
            "worker_head": worker.replay().events[-1].digest,
            "scientific_head": controller.store.replay().events[-1].digest,
            "reconciliation_required": bool(
                report["pending_invocations"]
                or report["pending_campaign_actions"]
                or report["physical_work"]["cost_is_uncertain"]
            ),
        }

    def owner_loss(self):
        from .conformance_owner import run_owner_loss

        return run_owner_loss(self)

    def malformed(self):
        """Reject a specific invalid inner payload, then allow exactly one typed repair."""
        root = self.batch.root / "cases/malformed"
        root.mkdir(mode=0o700, exist_ok=True)
        spec = replace(self.plan.worker, id="conformance-malformed", limits=MALFORMED_LIMITS)
        worker = (
            WorkerStore(root / "worker")
            if (root / "worker").exists()
            else WorkerStore.create(root / "worker", spec)
        )
        worker.require_identity(spec)
        host = MalformedProbeHost(self.configuration, self.batch, "malformed")
        _bind_host_configuration(worker, host, self.configuration)
        scheduler = SerialScheduler(worker, host)
        task = TaskAssignment(
            "1.0",
            "malformed-probe",
            spec.id,
            "orchestrator",
            None,
            0,
            MALFORMED_QUESTION,
            (),
            "role-handoff-1.0",
            ("stop",),
            self.batch.created_at + self.plan.batch.limits.elapsed_seconds,
            1,
        )
        projection = worker.replay()
        for call in tuple(projection.pending):
            scheduler.recover_invocation(call.id, campaign_revision=0)
        if not worker.replay().invocations:
            scheduler.dispatch(task, campaign_revision=0)

        def first_rejected(call):
            if (
                call.state != "invalid_output"
                or call.parse_failure is None
                or call.normalized_output is not None
                or call.final_response is None
                or call.completion_receipt is None
            ):
                return False
            try:
                completion = unique_json(read_bytes(worker.root, call.completion_receipt).decode())
                return (
                    completion["status"] == "completed"
                    and completion["stop_verified"] is True
                    and unique_json(read_bytes(worker.root, call.final_response).decode())
                    == MALFORMED_OUTPUT
                )
            except (ValueError, KeyError, TypeError):
                return False

        clients = list(worker.replay().invocations.values())
        first = clients[0]
        providers = {
            call.id: self._provider_evidence(worker.root / "processes" / call.id)
            for call in clients
        }
        rejected = first_rejected(first)
        # No repair for transport failure, a different rejection or missing provider proof.
        if (
            len(clients) == 1
            and rejected
            and providers[first.id]["verified"]
            and first.resolved_model is not None
        ):
            scheduler.dispatch(task, campaign_revision=0)
            clients = list(worker.replay().invocations.values())
            for call in clients[1:]:
                providers[call.id] = self._provider_evidence(worker.root / "processes" / call.id)
        projection = worker.replay()
        repaired = (
            len(clients) == 2
            and clients[1].state == "completed"
            and clients[1].attempt == 1
            and scheduler.handoff(clients[1]).status == "complete"
            and scheduler.handoff(clients[1]).proposed_next_action == "stop"
        )
        science_starts = sum(
            r.resource == "science" and r.case_id == "malformed"
            for r in self.batch.replay().reservations.values()
        )
        no_science = not projection.actions and not projection.science and science_starts == 0
        evidence_report(worker)
        return {
            "kind": "malformed",
            "passed": rejected
            and repaired
            and no_science
            and projection.tasks == {task.id: task}
            and projection.repairs_used == 1
            and all(value["verified"] for value in providers.values())
            and all(call.resolved_model is not None for call in clients),
            "intended_rejection_exercised": rejected,
            "repair_validated": repaired,
            "host_invocations": len(clients),
            "repairs_used": projection.repairs_used,
            "invocation_states": {call.id: call.state for call in clients},
            "scientific_actions": len(projection.actions),
            "scientific_starts": science_starts,
            "providers": providers,
            "worker_run_digest": spec.digest,
            "worker_head": projection.events[-1].digest,
            "reconciliation_required": bool(projection.pending),
        }

    def advance(self, *, max_new_cases=None):
        """Run the supported prefix. Missing cases remain incomplete, never passed."""
        with self.batch._lock(".conformance.lock"):
            if max_new_cases is not None and (type(max_new_cases) is not int or max_new_cases < 0):
                raise ValueError("case invocation allowance must be nonnegative")
            finished_here = 0
            while True:
                projection = self.batch.replay()
                if any(case.status == "failed" for case in projection.finished.values()):
                    return self.report()
                if len(projection.finished) == len(self.plan.batch.cases):
                    return self.report()
                if max_new_cases is not None and finished_here >= max_new_cases:
                    return self.report()
                case = self.plan.batch.cases[len(projection.finished)]
                if case.id not in IMPLEMENTED_CASES:
                    return self.report()
                self.batch.start_case(case.id, case.configuration_digest)
                verdict = getattr(self, case.id)()
                if self.batch.replay().pending or verdict.get("reconciliation_required"):
                    return self.report()
                provider_proofs = [
                    verdict.get("provider"),
                    verdict.get("request"),
                    verdict.get("ownership"),
                    *verdict.get("providers", {}).values(),
                ]
                evidence = [self.batch.evidence(verdict)]
                evidence.extend(
                    ArtifactRef.from_dict(value["evidence"])
                    for value in provider_proofs
                    if value and value.get("evidence")
                )
                evidence.extend(
                    ArtifactRef.from_dict(ref)
                    for ref in (*verdict.get("transcripts", []), *verdict.get("captures", []))
                )
                self.batch.finish_case(
                    case.id,
                    "passed" if verdict["passed"] else "failed",
                    tuple(evidence),
                )
                finished_here += 1

    def report(self):
        from .conformance_report import reconstruct_report

        return reconstruct_report(self.batch, self.preparation_digest)
