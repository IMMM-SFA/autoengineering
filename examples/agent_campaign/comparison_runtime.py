"""Serial matched workflow on frozen synthetic inputs.

This driver currently exercises authored responses only. It cannot dispatch a
provider or execute measured Leaf River data. Live dispatch and native worker
interruption still require implementation and separate authorization.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore, CaseStarted
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.agents.broker import CampaignBroker, WorkflowStopped
from autoengineering.agents.hosts.scripted import scripted_host
from autoengineering.agents.records import AgentRecord, AgentRunSpec, CandidateBrief
from autoengineering.agents.report import evidence_report
from autoengineering.agents.scheduler import SerialScheduler, validate_run_spec
from autoengineering.agents.single_agent import SingleAgentBroker
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.identity import scientific_identity, verify_runtime_sources
from autoengineering.campaign.records import ArtifactRef, sha256, unique
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.store import StoreError, checked_directory, durable_write

from .prepare_leafriver import LIVE_LIMITS, ROUTES, TEMPLATE_SHA256
from .comparison_status import CURRENT_VERSION, read_json as _json, reconstruct_report as report

VERSION = CURRENT_VERSION
CANDIDATES = ("pet-hamon-v1", "pet-hargreaves-v1")
DRIVER_FILES = (
    "comparison.py",
    "comparison_runtime.py",
    "comparison_status.py",
    "synthetic_comparison.py",
    "prepare_leafriver.py",
)
PROTOCOL = {
    "version": VERSION,
    "routes": list(ROUTES),
    "candidate_order": list(CANDIDATES),
    "canonical_candidate_ids": True,
    "early_freeze": "reject while untried candidates remain; a worker may stop",
    "static_admission_checks_per_route": 2,
    "negative_control": {
        "field": "model.outputs[0].units",
        "value": "invalid-unit",
        "reason": "candidate topology/interface differs",
    },
    "live_host_invocations": 0,
    "scientific_starts_per_route": 38,
    "aggregate_scientific_starts": 114,
    "synthetic_npz_limits": {
        "max_compressed_bytes": 65536,
        "max_members": 5,
        "max_member_bytes": 4096,
        "max_total_bytes": 32768,
    },
    "native_worker_interruption": "not_attempted",
    "live_comparison": "not_implemented",
}
PROTOCOL_DIGEST = digest(PROTOCOL)


class FrozenPool:
    """The same ordered candidate identities over both existing broker routes."""

    def summary(self):
        proposed = self.controller.state().proposals
        return {
            **super().summary(),
            "comparison_policy": {
                "version": VERSION,
                "candidate_order": list(CANDIDATES),
                "canonical_candidate_ids": True,
                "proposed_candidate_ids": [p.id for p in proposed],
                "next_proposal_candidate_id": CANDIDATES[len(proposed)]
                if len(proposed) < len(CANDIDATES)
                else None,
                "baseline_counts_as_proposal": False,
            },
        }

    def _propose_or_freeze(self, slot, can_investigate, validate):
        proposed = self.controller.state().proposals
        expected = CANDIDATES[len(proposed)] if can_investigate else None

        def check(value):
            validate(value)
            if (
                not isinstance(value.output, CandidateBrief)
                or value.output.candidate_id != expected
                or value.output.candidate_id
                != f"{value.output.target}-{value.output.implementation_id}"
            ):
                raise ValueError(f"matched candidate identity/order differs: expected {expected}")

        if self.workflow_route == "single_agent":
            from autoengineering.agents.records import NextStep

            def single_check(value):
                if isinstance(value.output, NextStep):
                    if value.output.action == "stop":
                        return
                    if value.output.action != "freeze" or can_investigate:
                        raise ValueError("matched pool must be exhausted before freeze")
                else:
                    check(value)

            return CampaignBroker._role(
                self,
                "single_agent",
                f"investigator:{slot}",
                "Propose comparison_policy.next_proposal_candidate_id, or stop. Baseline evaluation does not consume a proposal. Freeze only after the pool is exhausted.",
                expected_schema="role-handoff-1.2",
                candidate_id=expected,
                validate=single_check,
            )

        # An orchestrator's freeze bypasses the investigator validator, so the
        # four-role route checks it in _role too.
        return super()._propose_or_freeze(slot, can_investigate, check)

    def _role(self, role, key, question, *, validate=None, **kwargs):
        from autoengineering.agents.records import NextStep

        if role == "investigator":
            count = len(self.controller.state().proposals)
            kwargs["candidate_id"] = CANDIDATES[count] if count < len(CANDIDATES) else None

        def check(value):
            if isinstance(value.output, NextStep) and value.output.action == "freeze":
                if len(self.controller.state().proposals) < len(CANDIDATES):
                    raise ValueError("matched pool must be exhausted before freeze")
            if validate is not None:
                validate(value)

        return super()._role(role, key, question, validate=check, **kwargs)


class MatchedFourRoleBroker(FrozenPool, CampaignBroker):
    pass


class MatchedSingleAgentBroker(FrozenPool, SingleAgentBroker):
    pass


@dataclass(frozen=True)
class ComparisonCase(AgentRecord):
    id: Literal["scripted", "single_agent", "four_role"]
    scientific: ArtifactRef
    worker: AgentRunSpec

    def _validate(self):
        if self.scientific.path != f"scientific/{self.id}.yaml":
            raise ValueError("comparison scientific path differs")
        route = "single_agent" if self.id == "single_agent" else "four_role"
        if self.worker.workflow_route != route or self.worker.limits != LIVE_LIMITS:
            raise ValueError("comparison worker route or limits differ")
        if self.worker.host.kind != "fake" or self.worker.execution_mode != "supplied":
            raise ValueError("synthetic driver requires an authored supplied-only host")

    @property
    def configuration_digest(self):
        return digest({"protocol": PROTOCOL_DIGEST, "case": self.to_dict()})


def batch_cases(cases):
    return tuple(BatchCase(c.id, "comparison", c.configuration_digest, 0, 38) for c in cases)


@dataclass(frozen=True)
class ComparisonPreparation(AgentRecord):
    schema_version: Literal["synthetic-matched-comparison-1.1"]
    protocol_digest: str
    runtime_root: str
    parent_leaf: ArtifactRef
    template: ArtifactRef
    original_system: ArtifactRef
    driver_sources: tuple[ArtifactRef, ...]
    cases: tuple[ComparisonCase, ...]
    inputs: tuple[ArtifactRef, ...]
    batch: BatchSpec

    def _validate(self):
        if (
            self.protocol_digest != PROTOCOL_DIGEST
            or self.template.sha256 != TEMPLATE_SHA256
            or self.template.path != "original-template.yaml"
            or self.parent_leaf.path != "parent-leaf-preparation.json"
            or self.original_system.path != "original-system.yaml"
            or tuple(c.id for c in self.cases) != ROUTES
            or tuple(r.path for r in self.driver_sources)
            != tuple(f"driver/{n}" for n in DRIVER_FILES)
            or not Path(self.runtime_root).is_absolute()
            or not 1 <= len(self.inputs) <= 256
            or sum(r.size_bytes for r in self.inputs) > 67108864
            or self.batch.cases != batch_cases(self.cases)
            or self.batch.scientific_starts != 114
            or self.batch.host.kind != "fake"
        ):
            raise ValueError("synthetic comparison differs from fixed protocol")
        unique([r.path for r in self.inputs], "comparison input")
        if any(not r.path.startswith("captured_source/") for r in self.inputs):
            raise ValueError("comparison input outside captured source")
        for case in self.cases:
            if (
                case.worker.source_identity != self.batch.source_identity
                or case.worker.environment_identity != self.batch.environment_identity
                or case.worker.host != self.batch.host
            ):
                raise ValueError("comparison worker/batch identity differs")


def load(root, *, expected_digest, allow_runtime=False):
    sha256(expected_digest)
    root = checked_directory(root)
    document = _json(root, "comparison.json")
    if digest(document) != expected_digest:
        raise ValueError("comparison preparation differs from trusted pin")
    plan = ComparisonPreparation.from_dict(document)
    runtime = Path(plan.runtime_root)
    checked_directory(runtime.parent)
    if (
        runtime.is_symlink()
        or (runtime.exists() and not allow_runtime)
        or runtime.resolve().is_relative_to(root)
        or root.is_relative_to(runtime.resolve())
    ):
        raise ValueError("comparison runtime must be absent and separate from preparation")
    for ref in (
        plan.parent_leaf,
        plan.template,
        plan.original_system,
        *plan.driver_sources,
        *plan.inputs,
    ):
        read_bytes(root, ref, max_bytes=4194304)
    from .prepare_leafriver import LeafPreparation

    parent = LeafPreparation.from_json(read_bytes(root, plan.parent_leaf).decode())
    if parent.template.sha256 != plan.template.sha256:
        raise ValueError("comparison parent/template binding differs")
    for name, ref in zip(DRIVER_FILES, plan.driver_sources):
        if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != ref.sha256:
            raise ValueError("comparison driver source changed")
    specs = []
    for case in plan.cases:
        validate_run_spec(case.worker)
        read_bytes(root, case.scientific, max_bytes=1048576)
        spec = CampaignSpec.from_yaml(confined_file(root, case.scientific.path))
        verify_runtime_sources(spec)
        if (case.worker.campaign_id, case.worker.campaign_identity) != (
            spec.name,
            scientific_identity(spec, root / "captured_source"),
        ):
            raise ValueError("comparison scientific/worker identity differs")
        specs.append(spec)
    from .synthetic_comparison import verify

    verify(root, plan, specs)
    return plan


def _probe(controller, batch, case_root):
    (case_root / "artifacts").mkdir(mode=0o700, exist_ok=True)
    path = case_root / "invalid-interface.json"
    template = next(controller.supplied_snapshots())
    bad = replace(
        template,
        model=replace(
            template.model,
            outputs=(
                replace(template.model.outputs[0], units="invalid-unit"),
                *template.model.outputs[1:],
            ),
        ),
    )
    if path.exists():
        receipt = _json(case_root, path.name)
        ref = ArtifactRef.from_dict(receipt["invalid_snapshot"])
        raw = read_bytes(case_root, ref, max_bytes=1048576)
        expected = {
            "kind": "trusted_static_interface_control",
            "mutation": PROTOCOL["negative_control"],
            "invalid_snapshot": ref.to_dict(),
            "reason": PROTOCOL["negative_control"]["reason"],
            "valid_control_passed": True,
            "scientific_starts": 0,
            "host_calls": 0,
            "worker_feedback": "none",
            "campaign_events_before_and_after": 0,
        }
        if raw != bad.to_json().encode() or canonical_json(receipt) != canonical_json(expected):
            raise StoreError("saved invalid-candidate control changed")
        return receipt
    if controller.store.replay().events or controller.state().budget.attempts:
        raise StoreError("missing invalid-candidate control after campaign activity")
    controller._validate_snapshot(template)
    source = put_bytes(
        case_root,
        bad.to_json().encode(),
        name="invalid-snapshot.json",
        media_type="application/json",
        producer="trusted-comparison-control",
    )
    reason = None
    try:
        controller._validate_snapshot(bad)
    except ValueError as error:
        reason = str(error)
    if reason != PROTOCOL["negative_control"]["reason"]:
        raise StoreError("invalid candidate failed for an unintended reason or was accepted")
    receipt = {
        "kind": "trusted_static_interface_control",
        "mutation": PROTOCOL["negative_control"],
        "invalid_snapshot": source.to_dict(),
        "reason": reason,
        "valid_control_passed": True,
        "scientific_starts": 0,
        "host_calls": 0,
        "worker_feedback": "none",
        "campaign_events_before_and_after": 0,
    }
    if controller.store.replay().events or controller.state().budget.attempts:
        raise StoreError("static control performed scientific work")
    durable_write(path, canonical_json(receipt).encode())
    return receipt


class Runtime:
    def __init__(self, preparation, expected_digest, batch):
        self.preparation = checked_directory(preparation)
        self.pin = expected_digest
        self.plan = load(self.preparation, expected_digest=expected_digest, allow_runtime=True)
        self.batch = batch
        if (
            batch.root != Path(self.plan.runtime_root)
            or batch.spec != self.plan.batch
            or _json(batch.root, "origin.json")
            != {
                "version": VERSION,
                "preparation_digest": expected_digest,
                "batch_digest": batch.digest,
            }
        ):
            raise StoreError("comparison runtime origin differs")

    @classmethod
    def create(cls, preparation, *, expected_digest):
        plan = load(preparation, expected_digest=expected_digest)
        batch = BatchStore.create(plan.runtime_root, plan.batch)
        durable_write(
            batch.root / "origin.json",
            canonical_json(
                {
                    "version": VERSION,
                    "preparation_digest": expected_digest,
                    "batch_digest": batch.digest,
                }
            ).encode(),
        )
        return cls(preparation, expected_digest, batch)

    @classmethod
    def open(cls, preparation, *, expected_digest, runtime_digest):
        plan = load(preparation, expected_digest=expected_digest, allow_runtime=True)
        return cls(
            preparation,
            expected_digest,
            BatchStore(plan.runtime_root, expected_digest=runtime_digest),
        )

    def _case(self, case, *, max_new_evaluations=None, host=None):
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
                self.preparation / "captured_source",
                root / "campaign",
                batch=self.batch,
                case_id=case.id,
                max_new_evaluations=max_new_evaluations,
            )
        control = _probe(controller, self.batch, root)
        if (root / "worker").exists():
            worker = WorkerStore(root / "worker")
            worker.require_identity(case.worker)
        else:
            worker = WorkerStore.create(root / "worker", case.worker)
        from autoengineering.agents.hosts.fake import FakeHost

        host = host or scripted_host(case.worker.workflow_route)
        if not isinstance(host, FakeHost):
            raise StoreError("synthetic comparison cannot use a real host")
        broker_class = (
            MatchedSingleAgentBroker if case.id == "single_agent" else MatchedFourRoleBroker
        )
        broker = broker_class(controller, SerialScheduler(worker, host))
        stopped = None
        try:
            broker.advance()
        except WorkflowStopped as error:
            stopped = str(error)
        evidence = evidence_report(worker)
        state = controller.state()
        if (
            evidence["pending_invocations"]
            or evidence["pending_campaign_actions"]
            or state.budget.cost_is_uncertain
            or self.batch.replay().pending
        ):
            return None
        if controller.store.replay().state != "completed" and stopped is None:
            return None
        worker_report = put_bytes(
            self.batch.root,
            canonical_json(evidence).encode(),
            name="worker-report.json",
            media_type="application/json",
            producer="comparison-reporter",
        )
        observed = tuple(p.id for p in state.proposals)
        passed = (
            stopped is None
            and evidence["status"] == "completed"
            and observed == CANDIDATES
            and len(state.budget.attempts) <= 38
            and control["valid_control_passed"]
        )
        comparisons = [
            e.to_dict() for e in state.evaluations if e.split_id in ("comparison", "diagnostic")
        ]
        calls = worker.replay().invocations
        starts = [
            e.record.recorded_at
            for e in self.batch.replay().events
            if isinstance(e.record, CaseStarted) and e.record.case_id == case.id
        ]
        return {
            "case": case.id,
            "passed": passed,
            "workflow_stop": stopped,
            "kind": "authored_synthetic_dry_run",
            "candidate_order": list(observed),
            "logical_host_calls": len(worker.replay().invocations),
            "handoff_states": {
                s: sum(c.state == s for c in calls.values())
                for s in sorted({c.state for c in calls.values()})
            },
            "repairs_used": worker.replay().repairs_used,
            "case_elapsed_seconds": self.batch.clock() - starts[-1],
            "trusted_review_dispositions": [
                d.to_dict() for d in worker.replay().dispositions.values()
            ],
            "physical_provider_calls": 0,
            "scientific_starts": len(state.budget.attempts),
            "confirmation": state.confirmation,
            "scientific_outcome": state.outcome,
            "scientific_evidence": evidence["scientific_evidence"],
            "comparison_and_diagnostic_evaluations": comparisons,
            "invalid_candidate_control": control,
            "worker_report": worker_report.to_dict(),
            "worker_head": worker.replay().events[-1].digest,
            "scientific_head": controller.store.replay().events[-1].digest,
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
                proof = self.batch.evidence(receipt)
                self.batch.finish_case(
                    case.id, "passed" if receipt["passed"] else "failed", (proof,)
                )
                completed += 1
        return report(self.batch, self.pin)
