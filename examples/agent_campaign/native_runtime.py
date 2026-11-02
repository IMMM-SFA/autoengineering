"""Run the frozen native comparison after caller-pinned provider conformance.

Calling this API executes work. Preparation and a passing prerequisite do not
grant user authorization for model requests or measured-data execution.
"""

from __future__ import annotations

from pathlib import Path

from autoengineering.agents.batch import BatchStore, CaseStarted
from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.agents.broker import WorkflowStopped
from autoengineering.agents.command import _bind_host_configuration
from autoengineering.agents.hosts.scripted import scripted_host
from autoengineering.agents.report import evidence_report
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError, checked_directory, durable_write

from .comparison_runtime import CANDIDATES, MatchedFourRoleBroker, MatchedSingleAgentBroker, _probe
from .comparison_status import read_json
from .native_comparison import VERSION as PREPARATION_VERSION, load, verify_conformance_prerequisite
from .native_evidence import capture_provider
from .native_interruption import run_interruption
from .native_status import VERSION, read_report


class NativePoolPolicy:
    def summary(self):
        value = super().summary()
        return {
            **value,
            "comparison_policy": {**value["comparison_policy"], "version": PREPARATION_VERSION},
        }


class NativeFourRoleBroker(NativePoolPolicy, MatchedFourRoleBroker):
    pass


class NativeSingleAgentBroker(NativePoolPolicy, MatchedSingleAgentBroker):
    pass


class NativeRuntime:
    def __init__(self, preparation, pin, configuration, batch, conformance_digest):
        self.preparation = checked_directory(preparation)
        self.pin, self.configuration = pin, configuration
        self.plan = load(
            self.preparation, expected_digest=pin, configuration=configuration, allow_runtime=True
        )
        self.batch, self.conformance_digest = batch, conformance_digest
        proof = verify_conformance_prerequisite(
            self.preparation,
            expected_digest=pin,
            configuration=configuration,
            runtime_digest=conformance_digest,
            allow_runtime=True,
        )
        if (
            batch.root != Path(self.plan.runtime_root)
            or batch.spec != self.plan.batch
            or read_json(batch.root, "origin.json")
            != {
                "version": VERSION,
                "preparation_digest": pin,
                "batch_digest": batch.digest,
                "conformance_runtime_digest": conformance_digest,
                "conformance_prerequisite": proof,
            }
        ):
            raise StoreError("native comparison runtime/prerequisite origin differs")

    @classmethod
    def create(cls, preparation, *, expected_digest, configuration, conformance_runtime_digest):
        # All source, scope and real-conformance verification precedes BatchStore.create.
        plan = load(preparation, expected_digest=expected_digest, configuration=configuration)
        proof = verify_conformance_prerequisite(
            preparation,
            expected_digest=expected_digest,
            configuration=configuration,
            runtime_digest=conformance_runtime_digest,
        )
        batch = BatchStore.create(plan.runtime_root, plan.batch)
        durable_write(
            batch.root / "origin.json",
            canonical_json(
                {
                    "version": VERSION,
                    "preparation_digest": expected_digest,
                    "batch_digest": batch.digest,
                    "conformance_runtime_digest": conformance_runtime_digest,
                    "conformance_prerequisite": proof,
                }
            ).encode(),
        )
        return cls(preparation, expected_digest, configuration, batch, conformance_runtime_digest)

    @classmethod
    def open(
        cls,
        preparation,
        *,
        expected_digest,
        configuration,
        runtime_digest,
        conformance_runtime_digest,
    ):
        plan = load(
            preparation,
            expected_digest=expected_digest,
            configuration=configuration,
            allow_runtime=True,
        )
        return cls(
            preparation,
            expected_digest,
            configuration,
            BatchStore(plan.runtime_root, expected_digest=runtime_digest),
            conformance_runtime_digest,
        )

    def _worker(self, case):
        root = self.batch.root / "cases" / case.id
        root.mkdir(mode=0o700, exist_ok=True)
        if (root / "worker").exists():
            worker = WorkerStore(root / "worker")
            worker.require_identity(case.worker)
        else:
            worker = WorkerStore.create(root / "worker", case.worker)
        if case.id != "scripted":
            _bind_host_configuration(
                worker, BatchCodexHost(self.configuration, self.batch, case.id), self.configuration
            )
        return worker

    def _case(self, case, *, max_new_evaluations=None):
        root = self.batch.root / "cases" / case.id
        root.mkdir(mode=0o700, exist_ok=True)
        if (root / "campaign").exists():
            controller = BatchCampaignController.open(
                root / "campaign",
                batch=self.batch,
                case_id=case.id,
                max_new_evaluations=max_new_evaluations,
            )
            controller.reconcile_batch()
        else:
            controller = BatchCampaignController.create(
                self.preparation / case.scientific.path,
                self.preparation / "leaf/captured_source",
                root / "campaign",
                batch=self.batch,
                case_id=case.id,
                max_new_evaluations=max_new_evaluations,
            )
        control = _probe(controller, self.batch, root)
        worker = self._worker(case)
        interruption = {"kind": "scripted_no_native_worker", "passed": True}
        if case.id != "scripted":
            interruption = run_interruption(self, case, worker)
            if interruption["reconciliation_required"]:
                return None
            if interruption["passed"] is not True:
                raise StoreError("intended matched interruption did not pass")
        host = (
            scripted_host(case.worker.workflow_route)
            if case.id == "scripted"
            else BatchCodexHost(self.configuration, self.batch, case.id)
        )
        broker_type = NativeSingleAgentBroker if case.id == "single_agent" else NativeFourRoleBroker
        broker = broker_type(controller, SerialScheduler(worker, host))
        stopped = None
        try:
            broker.advance()
        except WorkflowStopped as error:
            stopped = str(error)
        worker_report = evidence_report(worker)
        state = controller.state()
        if (
            worker_report["pending_invocations"]
            or worker_report["pending_campaign_actions"]
            or state.budget.cost_is_uncertain
            or self.batch.replay().pending
        ):
            return None
        if controller.store.replay().state != "completed" and stopped is None:
            return None
        calls = worker.replay().invocations
        providers = (
            {}
            if case.id == "scripted"
            else {
                c.id: capture_provider(self.batch, worker, c, self.configuration)
                for c in calls.values()
                if c.id != interruption["call_id"]
            }
        )
        observed = tuple(p.id for p in state.proposals)
        passed = (
            stopped is None
            and worker_report["status"] == "completed"
            and observed == CANDIDATES
            and len(state.budget.attempts) <= 38
            and control["valid_control_passed"]
            and interruption["passed"]
            and all(p["verified"] is True for p in providers.values())
            and (case.id == "scripted" or bool(providers))
        )
        saved_report = put_bytes(
            self.batch.root,
            canonical_json(worker_report).encode(),
            name="worker-report.json",
            media_type="application/json",
            producer="native-comparison-reporter",
        )
        starts = [
            e.record.recorded_at
            for e in self.batch.replay().events
            if isinstance(e.record, CaseStarted) and e.record.case_id == case.id
        ]
        physical = [
            r
            for r in self.batch.replay().reservations.values()
            if r.resource == "host" and r.case_id == case.id
        ]
        observations = self.batch.replay().observations
        intents = [observations[r.id].request_intent for r in physical]
        return {
            "case": case.id,
            "passed": bool(passed),
            "workflow_stop": stopped,
            "kind": "native_matched_leaf_river_development",
            "candidate_order": list(observed),
            "logical_host_calls": len(calls),
            "physical_provider_calls": None if "unknown" in intents else intents.count("present"),
            "verified_provider_responses": sum(p["verified"] is True for p in providers.values()),
            "physical_host_calls": len(physical),
            "handoff_states": {
                s: sum(c.state == s for c in calls.values())
                for s in sorted({c.state for c in calls.values()})
            },
            "repairs_used": worker.replay().repairs_used,
            "case_elapsed_seconds": self.batch.clock() - starts[-1],
            "trusted_review_dispositions": [
                d.to_dict() for d in worker.replay().dispositions.values()
            ],
            "scientific_starts": len(state.budget.attempts),
            "confirmation": state.confirmation,
            "scientific_outcome": state.outcome,
            "scientific_evidence": worker_report["scientific_evidence"],
            "comparison_and_diagnostic_evaluations": [
                e.to_dict() for e in state.evaluations if e.split_id in ("comparison", "diagnostic")
            ],
            "invalid_candidate_control": control,
            "worker_report": saved_report.to_dict(),
            "worker_head": worker.replay().events[-1].digest,
            "scientific_head": controller.store.replay().events[-1].digest,
            "interruption": interruption,
            "provider_proofs": providers,
        }

    def advance(self, *, max_new_cases=3, max_new_evaluations=None):
        if type(max_new_cases) is not int or not 1 <= max_new_cases <= 3:
            raise ValueError("case cap must be in 1..3")
        if max_new_evaluations is not None and (
            type(max_new_evaluations) is not int or max_new_evaluations < 1
        ):
            raise ValueError("evaluation pause must be positive")
        with self.batch._lock(".comparison-operation.lock"):
            completed = 0
            for case in self.plan.cases:
                projection = self.batch.replay()
                if any(r.status == "failed" for r in projection.finished.values()):
                    break
                if case.id in projection.finished:
                    continue
                if completed == max_new_cases:
                    break
                self.batch.start_case(case.id, case.configuration_digest)
                receipt = self._case(case, max_new_evaluations=max_new_evaluations)
                if receipt is None:
                    break
                self.batch.finish_case(
                    case.id,
                    "passed" if receipt["passed"] else "failed",
                    (self.batch.evidence(receipt),),
                )
                completed += 1
        return read_report(self.batch.root, expected_digest=self.batch.digest)
