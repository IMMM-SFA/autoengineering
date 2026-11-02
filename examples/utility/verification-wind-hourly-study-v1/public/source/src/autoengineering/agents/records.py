"""Versioned, immutable worker contracts. These records grant no scientific authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from autoengineering.campaign.records import (
    ArtifactRef,
    Request,
    Response,
    Scalar,
    identifier,
    relative_path,
    sha256,
    unique,
)
from autoengineering.campaign.serialization import Record

Role = Literal["orchestrator", "investigator", "implementer", "reviewer"]
Operation = Literal["assign", "propose", "configure", "review", "freeze", "stop"]
ROLES = ("orchestrator", "investigator", "implementer", "reviewer")
SINGLE_ROLE = "single_agent"
WorkerRole = Literal["orchestrator", "investigator", "implementer", "reviewer", "single_agent"]
MAX_ENVELOPE_BYTES = 65536


class AgentRecord(Record):
    """Bound worker-controlled envelopes before parsing or serializing them."""

    def __post_init__(self):
        super().__post_init__()
        if len(self.to_json().encode("utf-8")) > MAX_ENVELOPE_BYTES:
            raise ValueError("worker record exceeds 64 KiB")

    @classmethod
    def from_json(cls, text: str):
        if len(text.encode("utf-8")) > MAX_ENVELOPE_BYTES:
            raise ValueError("worker record exceeds 64 KiB")
        return super().from_json(text)


@dataclass(frozen=True)
class ResourceLimits(AgentRecord):
    max_invocations: int
    max_tasks: int
    max_repairs: int
    repairs_per_task: int
    elapsed_seconds: float
    worker_seconds: float
    transcript_bytes: int
    workspace_bytes: int
    observed_tokens: int | None = None

    def _validate(self):
        for value in (
            self.max_invocations,
            self.max_tasks,
            self.elapsed_seconds,
            self.worker_seconds,
            self.transcript_bytes,
            self.workspace_bytes,
        ):
            if value <= 0:
                raise ValueError("resource ceilings must be positive")
        if self.max_repairs < 0 or not 0 <= self.repairs_per_task <= 2:
            raise ValueError("invalid repair allowance")
        if self.worker_seconds > self.elapsed_seconds:
            raise ValueError("worker deadline exceeds run deadline")
        if self.observed_tokens is not None and self.observed_tokens <= 0:
            raise ValueError("observed token stop must be positive")


@dataclass(frozen=True)
class HostSelection(AgentRecord):
    kind: Literal["fake", "codex", "claude"]
    auth_mode: Literal["none", "subscription", "api"]
    requested_model: str
    adapter_version: Literal["1.0", "2.1", "3.0"]
    qualification_digest: str | None = None

    def to_dict(self):
        value = super().to_dict()
        if self.adapter_version == "1.0":
            value.pop("qualification_digest")
        return value

    @classmethod
    def from_dict(cls, value):
        if (
            isinstance(value, Mapping)
            and value.get("adapter_version") not in ("2.1", "3.0")
            and "qualification_digest" in value
        ):
            raise ValueError("qualification pin requires host adapter 2.1")
        return super().from_dict(value)

    def _validate(self):
        if self.adapter_version in ("2.1", "3.0"):
            if self.qualification_digest is None:
                raise ValueError(f"host adapter {self.adapter_version} requires a qualification pin")
            sha256(self.qualification_digest)
        elif self.qualification_digest is not None:
            raise ValueError("qualification pin requires host adapter 2.1")
        if self.kind == "fake" and self.adapter_version != "1.0":
            raise ValueError("fake host requires adapter version 1.0")
        if (self.kind == "fake") != (self.auth_mode == "none"):
            raise ValueError("host/authentication mode mismatch")
        if (self.kind == "claude") != (self.adapter_version == "3.0") or (
            (self.kind == "claude") != (self.auth_mode == "api")
        ):
            raise ValueError("Claude requires API authentication and adapter 3.0")


@dataclass(frozen=True)
class AgentRunSpec(AgentRecord):
    schema_version: Literal["1.0", "1.1"]
    id: str
    campaign_id: str
    campaign_identity: str
    host: HostSelection
    role_templates: Mapping[str, str]
    permitted_interventions: tuple[str, ...]
    tool_policy_digest: str
    limits: ResourceLimits
    source_identity: str
    environment_identity: str
    execution_mode: Literal["supplied", "generated"]
    workflow_route: Literal["four_role", "single_agent"] = "four_role"

    def to_dict(self):
        value = super().to_dict()
        if self.schema_version == "1.0":
            value.pop("workflow_route")
        return value

    @classmethod
    def from_dict(cls, value):
        if (
            isinstance(value, Mapping)
            and value.get("schema_version") == "1.0"
            and "workflow_route" in value
        ):
            raise ValueError("workflow route requires run schema 1.1")
        return super().from_dict(value)

    def _validate(self):
        identifier(self.id)
        identifier(self.campaign_id)
        for value in (
            self.campaign_identity,
            self.tool_policy_digest,
            self.source_identity,
            self.environment_identity,
        ):
            sha256(value)
        if (self.schema_version == "1.1") != (self.workflow_route == "single_agent"):
            raise ValueError("single-agent route requires explicit run schema 1.1")
        if self.workflow_route == "single_agent" and self.execution_mode != "supplied":
            raise ValueError("single-agent comparison supports supplied implementations only")
        expected_roles = (SINGLE_ROLE,) if self.workflow_route == "single_agent" else ROLES
        if set(self.role_templates) != set(expected_roles):
            raise ValueError("versioned role templates differ from the frozen workflow route")
        for value in self.role_templates.values():
            sha256(value)
        unique(self.permitted_interventions, "intervention")
        for value in self.permitted_interventions:
            identifier(value)

    @classmethod
    def from_file(cls, path: Path):
        """Run files use strict JSON, including duplicate-key rejection."""
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_ENVELOPE_BYTES + 1)
        if len(raw) > MAX_ENVELOPE_BYTES:
            raise ValueError("worker record exceeds 64 KiB")
        return cls.from_json(raw.decode("utf-8"))


@dataclass(frozen=True)
class ArtifactGrant(AgentRecord):
    schema_version: Literal["1.0", "1.1"]
    run_id: str
    task_id: str
    role: WorkerRole
    artifact: ArtifactRef
    operation: Literal["read"]
    max_bytes: int
    visibility: Literal["worker_summary", "public_source", "candidate_source"]

    def _validate(self):
        if (self.schema_version == "1.1") != (self.role == SINGLE_ROLE):
            raise ValueError("single-agent scope requires schema 1.1")
        identifier(self.run_id)
        identifier(self.task_id)
        if not 0 < self.max_bytes <= MAX_ENVELOPE_BYTES:
            raise ValueError("grant byte limit must be in 1..65536")
        if self.artifact.size_bytes > self.max_bytes:
            raise ValueError("artifact exceeds grant")


@dataclass(frozen=True)
class TaskAssignment(AgentRecord):
    schema_version: Literal["1.0", "1.1"]
    id: str
    run_id: str
    role: WorkerRole
    parent_task: str | None
    campaign_revision: int
    question: str
    grants: tuple[ArtifactGrant, ...]
    expected_schema: Literal["role-handoff-1.0", "role-handoff-1.1", "role-handoff-1.2"]
    allowed_operations: tuple[Operation, ...]
    deadline: float
    repair_allowance: int

    def _validate(self):
        if (self.schema_version == "1.1") != (self.role == SINGLE_ROLE):
            raise ValueError("single-agent scope requires schema 1.1")
        if (self.expected_schema == "role-handoff-1.2") != (self.role == SINGLE_ROLE):
            raise ValueError("single-agent task requires handoff schema 1.2")
        identifier(self.id)
        identifier(self.run_id)
        if self.parent_task is not None:
            identifier(self.parent_task)
            if self.parent_task == self.id:
                raise ValueError("task cannot parent itself")
        if self.campaign_revision < 0 or self.deadline <= 0:
            raise ValueError("invalid revision or deadline")
        if not 0 <= self.repair_allowance <= 2:
            raise ValueError("at most two task repairs are allowed")
        unique(self.allowed_operations, "operation")
        unique([grant.artifact.sha256 for grant in self.grants], "artifact grant")
        for grant in self.grants:
            if (grant.run_id, grant.task_id, grant.role) != (self.run_id, self.id, self.role):
                raise ValueError("artifact grant has a different task scope")


@dataclass(frozen=True)
class CandidateBrief(AgentRecord):
    candidate_id: str
    target: str
    implementation_id: str
    hypothesis: str
    expected_tradeoffs: str
    evidence_ids: tuple[str, ...]
    eligibility_gaps: tuple[str, ...]

    def _validate(self):
        for value in (self.candidate_id, self.target, self.implementation_id):
            identifier(value)
        unique(self.evidence_ids, "evidence")
        for value in self.evidence_ids:
            sha256(value)
        if not self.evidence_ids:
            raise ValueError("candidate brief needs supporting evidence")


@dataclass(frozen=True)
class SuppliedConfiguration(AgentRecord):
    candidate_id: str
    implementation_id: str
    parameters: Mapping[str, Scalar]
    evidence_ids: tuple[str, ...]

    def _validate(self):
        identifier(self.candidate_id)
        identifier(self.implementation_id)
        for value in self.evidence_ids:
            sha256(value)
        unique(self.evidence_ids, "evidence")


@dataclass(frozen=True)
class Finding(AgentRecord):
    id: str
    severity: Literal["blocking", "advisory", "information"]
    description: str
    supporting_checks: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def _validate(self):
        identifier(self.id)
        if not self.supporting_checks or not self.evidence_ids:
            raise ValueError("findings require checks and evidence")
        for value in self.evidence_ids:
            sha256(value)


@dataclass(frozen=True)
class ReviewFindings(AgentRecord):
    candidate_id: str
    evaluation_id: str
    evidence_ids: tuple[str, ...]
    findings: tuple[Finding, ...]
    missing_evidence: tuple[str, ...]
    recommendation: Literal["proceed", "repair", "stop"]

    def _validate(self):
        identifier(self.candidate_id)
        identifier(self.evaluation_id)
        if not self.evidence_ids:
            raise ValueError("review needs evaluation evidence")
        unique(self.evidence_ids, "evidence")
        unique([finding.id for finding in self.findings], "finding")
        for value in self.evidence_ids:
            sha256(value)
        if any(not set(f.evidence_ids) <= set(self.evidence_ids) for f in self.findings):
            raise ValueError("finding cites evidence outside review")
        if self.recommendation == "proceed" and (
            self.missing_evidence or any(f.severity == "blocking" for f in self.findings)
        ):
            raise ValueError("unresolved review cannot recommend proceeding")


@dataclass(frozen=True)
class NextStep(AgentRecord):
    action: Literal["assign", "freeze", "stop"]
    role: Role | None
    reason: str

    def _validate(self):
        if (self.action == "assign") != (self.role is not None):
            raise ValueError("only an assignment specifies a role")
        if self.role == "orchestrator":
            raise ValueError("orchestrator cannot assign itself")


@dataclass(frozen=True)
class ImplementationBundle(AgentRecord):
    base_snapshot: str
    patch: ArtifactRef
    sources: tuple[ArtifactRef, ...]
    allowed_files: tuple[str, ...]
    dependencies: tuple[str, ...]
    interface_results: tuple[ArtifactRef, ...]
    execution_boundary_receipt: ArtifactRef | None
    admitted_identity: str | None

    def _validate(self):
        sha256(self.base_snapshot)
        if not self.sources:
            raise ValueError("implementation bundle requires source bytes")
        unique(self.allowed_files, "allowed file")
        unique([source.path for source in self.sources], "source path")
        for value in self.allowed_files:
            relative_path(value)
        if not {source.path for source in self.sources} <= set(self.allowed_files):
            raise ValueError("implementation contains undeclared files")
        if self.admitted_identity is not None:
            sha256(self.admitted_identity)
            if self.execution_boundary_receipt is None or not self.interface_results:
                raise ValueError("admission requires boundary and interface receipts")


@dataclass(frozen=True)
class SourceDraft(AgentRecord):
    candidate_id: str
    base_snapshot: str
    files: Mapping[str, str]
    dependencies: tuple[str, ...]
    evidence_ids: tuple[str, ...]

    def _validate(self):
        identifier(self.candidate_id)
        sha256(self.base_snapshot)
        if set(self.files) != {"adapter.py"} or self.dependencies != ("python-stdlib", "math"):
            raise ValueError("source draft requires one adapter and fixed dependencies")
        if len(self.files["adapter.py"].encode()) > 65536:
            raise ValueError("source draft exceeds its byte allowance")
        if not self.evidence_ids:
            raise ValueError("source draft needs the granted preparation context")
        unique(self.evidence_ids, "evidence")
        for value in self.evidence_ids:
            sha256(value)


@dataclass(frozen=True)
class ImplementationPreparation(AgentRecord):
    schema_version: Literal["1.0"]
    id: str
    run_id: str
    task_id: str
    invocation_id: str
    candidate_id: str
    proposal_digest: str
    draft_digest: str
    workspace: str
    configuration: ArtifactRef
    capture: ArtifactRef
    state: Literal[
        "captured",
        "checking",
        "checked",
        "failed",
        "reconciliation_required",
        "registered",
        "forked",
    ]
    reason: str
    recorded_at: float = 0.0
    interface: ArtifactRef | None = None
    bundle: ArtifactRef | None = None
    admission: ArtifactRef | None = None
    registration_identity: str | None = None
    fork: ArtifactRef | None = None
    successor_identity: str | None = None

    def _validate(self):
        for value in (self.id, self.run_id, self.task_id, self.invocation_id, self.candidate_id):
            identifier(value)
        for value in (
            self.proposal_digest,
            self.draft_digest,
            self.registration_identity,
            self.successor_identity,
        ):
            if value is not None:
                sha256(value)
        if self.workspace != f"preparations/{self.id}/workspace":
            raise ValueError("preparation workspace differs from its reserved path")
        if not self.reason or len(self.reason) > 2048:
            raise ValueError("preparation requires a bounded reason")
        if self.recorded_at < 0:
            raise ValueError("preparation time cannot be negative")
        if self.state in ("checked", "registered", "forked") and (
            self.interface is None or self.bundle is None
        ):
            raise ValueError("checked preparation requires trusted interface and bundle evidence")
        if (self.registration_identity is None) != (self.admission is None):
            raise ValueError("registration requires an admission receipt")
        if self.state in ("registered", "forked") and self.admission is None:
            raise ValueError("registered preparation requires trusted admission")
        if (self.successor_identity is None) != (self.fork is None):
            raise ValueError("successor requires a fork receipt")
        if (self.state == "forked") != (self.fork is not None):
            raise ValueError("fork receipt requires the forked state")


@dataclass(frozen=True)
class RoleHandoff(AgentRecord):
    schema_version: Literal["1.0", "1.1", "1.2"]
    id: str
    task_id: str
    invocation_id: str
    role: WorkerRole
    campaign_revision: int
    status: Literal["complete", "incomplete", "unsupported"]
    output: (
        NextStep
        | CandidateBrief
        | SuppliedConfiguration
        | ImplementationBundle
        | ReviewFindings
        | SourceDraft
    )
    supporting_artifact_ids: tuple[str, ...]
    unresolved_issues: tuple[str, ...]
    proposed_next_action: Operation
    supersedes: str | None = None

    def _validate(self):
        if (self.schema_version == "1.2") != (self.role == SINGLE_ROLE):
            raise ValueError("single-agent handoff requires schema 1.2")
        for value in (self.id, self.task_id, self.invocation_id):
            identifier(value)
        if self.supersedes is not None:
            identifier(self.supersedes)
            if self.supersedes == self.id:
                raise ValueError("handoff cannot supersede itself")
        if self.campaign_revision < 0:
            raise ValueError("invalid campaign revision")
        expected = {
            "orchestrator": (NextStep,),
            "investigator": (CandidateBrief,),
            "implementer": (SuppliedConfiguration, ImplementationBundle, SourceDraft),
            "reviewer": (ReviewFindings,),
            SINGLE_ROLE: (NextStep, CandidateBrief, SuppliedConfiguration, ReviewFindings),
        }
        if not isinstance(self.output, expected[self.role]):
            raise ValueError("output does not match role schema")
        if (
            self.role == SINGLE_ROLE
            and isinstance(self.output, NextStep)
            and self.output.action == "assign"
        ):
            raise ValueError("single agent cannot delegate")
        if isinstance(self.output, SourceDraft) and self.schema_version != "1.1":
            raise ValueError("source drafts require role handoff version 1.1")
        for value in self.supporting_artifact_ids:
            sha256(value)
        unique(self.supporting_artifact_ids, "supporting artifact")
        if self.status == "complete" and self.unresolved_issues:
            raise ValueError("complete handoff cannot have unresolved issues")


@dataclass(frozen=True)
class HostCapabilities(AgentRecord):
    schema_version: Literal["1.0", "1.1"]
    host: Literal["fake", "codex", "claude"]
    adapter_version: Literal["1.0", "2.1", "3.0"]
    executable_version: str
    auth_mode: Literal["none", "subscription", "api"]
    structured_output: bool
    process_supervision: bool
    boundary_identity: str | None
    platform: str
    limitations: tuple[str, ...] = ()
    usage_basis: Literal["reported_message_fields_only"] | None = None

    def to_dict(self):
        value = super().to_dict()
        if self.schema_version == "1.0":
            value.pop("limitations")
            value.pop("usage_basis")
        return value

    @classmethod
    def from_dict(cls, value):
        if (
            isinstance(value, Mapping)
            and value.get("schema_version") == "1.0"
            and ("limitations" in value or "usage_basis" in value)
        ):
            raise ValueError("host limitations and usage basis require capability schema 1.1")
        return super().from_dict(value)

    def _validate(self):
        if self.adapter_version == "2.1" and (
            self.host != "codex"
            or not self.process_supervision
            or not self.structured_output
            or self.boundary_identity is None
        ):
            raise ValueError("adapter 2.1 requires qualified native capabilities")
        if (self.host == "fake") != (self.auth_mode == "none"):
            raise ValueError("capability authentication mismatch")
        if self.boundary_identity is not None:
            sha256(self.boundary_identity)
        if self.schema_version == "1.0" and (self.limitations or self.usage_basis is not None):
            raise ValueError("legacy capabilities cannot contain new accounting metadata")
        if self.host == "claude":
            if (
                self.schema_version != "1.1"
                or self.adapter_version != "3.0"
                or self.auth_mode != "api"
                or not self.structured_output
                or not self.process_supervision
                or self.boundary_identity is None
                or not self.limitations
                or self.usage_basis != "reported_message_fields_only"
            ):
                raise ValueError("Claude requires versioned qualified API capabilities")
            unique(self.limitations, "host limitation")
        elif (
            self.schema_version != "1.0" or self.adapter_version == "3.0" or self.auth_mode == "api"
        ):
            raise ValueError("capability version or authentication differs from host")


@dataclass(frozen=True)
class HostConfigurationBinding(AgentRecord):
    schema_version: Literal["1.0", "1.1"]
    run_id: str
    configuration_digest: str
    capabilities: HostCapabilities

    def _validate(self):
        identifier(self.run_id)
        sha256(self.configuration_digest)
        if self.schema_version == "1.1":
            if (
                self.capabilities.adapter_version != "3.0"
                or self.capabilities.schema_version != "1.1"
            ):
                raise ValueError("binding schema 1.1 requires Claude adapter 3.0")
        elif self.capabilities.adapter_version != "2.1":
            raise ValueError("host configuration binding requires adapter 2.1")


@dataclass(frozen=True)
class WorkerInvocation(AgentRecord):
    schema_version: Literal["1.0", "1.1", "1.2"]
    id: str
    run_id: str
    task_id: str
    attempt: int
    state: Literal[
        "reserved",
        "running",
        "completed",
        "invalid_output",
        "timeout",
        "cancelled",
        "host_failure",
        "reconciliation_required",
    ]
    prompt: ArtifactRef
    capabilities: HostCapabilities
    requested_model: str
    resolved_model: str | None
    policy_digest: str
    launch_nonce: str
    process_receipt: ArtifactRef | None
    raw_response: ArtifactRef | None
    normalized_output: ArtifactRef | None
    completion_receipt: ArtifactRef | None
    started_at: float
    elapsed_seconds: float | None
    usage: Mapping[str, int | None]
    parse_failure: ArtifactRef | None = None
    final_response: ArtifactRef | None = None
    stderr_response: ArtifactRef | None = None
    recovery_receipt: ArtifactRef | None = None

    def to_dict(self):
        value = super().to_dict()
        if self.schema_version != "1.2":
            value.pop("recovery_receipt")
        if self.schema_version == "1.0":
            value.pop("final_response")
            value.pop("stderr_response")
        return value

    @classmethod
    def from_dict(cls, value):
        if (
            isinstance(value, Mapping)
            and value.get("schema_version") in ("1.0", "1.1")
            and "recovery_receipt" in value
        ):
            raise ValueError("recovery receipt requires invocation version 1.2")
        if (
            isinstance(value, Mapping)
            and value.get("schema_version") == "1.0"
            and ({"final_response", "stderr_response"} & set(value))
        ):
            raise ValueError("invocation 1.0 cannot contain 1.1 transcript fields")
        return super().from_dict(value)

    def _validate(self):
        if self.schema_version != "1.2" and self.recovery_receipt is not None:
            raise ValueError("recovery receipt requires invocation version 1.2")
        if self.schema_version == "1.0" and (
            self.final_response is not None or self.stderr_response is not None
        ):
            raise ValueError("separate transcript channels require invocation version 1.1")
        for value in (self.id, self.run_id, self.task_id, self.launch_nonce):
            identifier(value)
        sha256(self.policy_digest)
        if self.attempt < 0 or self.started_at < 0:
            raise ValueError("invalid invocation attempt/time")
        if self.elapsed_seconds is not None and self.elapsed_seconds < 0:
            raise ValueError("invalid elapsed time")
        if any(value is not None and value < 0 for value in self.usage.values()):
            raise ValueError("usage cannot be negative")
        if self.state == "running" and self.process_receipt is None:
            raise ValueError("running invocation requires launch receipt")
        if self.state == "completed" and any(
            value is None
            for value in (
                self.raw_response,
                self.normalized_output,
                self.completion_receipt,
                self.elapsed_seconds,
            )
        ):
            raise ValueError("completed invocation requires output and completion receipts")


@dataclass(frozen=True)
class CampaignAction(AgentRecord):
    """Trusted broker intent and acknowledgment, never a worker tool envelope."""

    schema_version: Literal["1.0"]
    id: str
    run_id: str
    kind: Literal["stage_proposal", "stage_snapshot", "stage_diagnostic", "request"]
    state: Literal["reserved", "completed"]
    invocation_id: str | None
    source: ArtifactRef | None
    request: Request | None
    response: Response | None
    staged_id: str | None

    def _validate(self):
        identifier(self.id)
        identifier(self.run_id)
        if self.invocation_id is not None:
            identifier(self.invocation_id)
        if self.kind == "request":
            if self.request is None or self.source is not None or self.staged_id is not None:
                raise ValueError("request action requires only an exact campaign envelope")
            if self.response is not None and self.response.request_id != self.request.request_id:
                raise ValueError("campaign response identity differs from request")
            if (self.state == "completed") != (self.response is not None):
                raise ValueError("request completion requires its original response")
        else:
            if self.source is None or self.request is not None or self.response is not None:
                raise ValueError("staging action requires only a source artifact")
            if (self.state == "completed") != (self.staged_id is not None):
                raise ValueError("staging completion requires the admitted artifact identity")
            if self.staged_id is not None:
                sha256(self.staged_id)


@dataclass(frozen=True)
class RunStart(AgentRecord):
    schema_version: Literal["1.0"]
    run_id: str
    created_at: float

    def _validate(self):
        identifier(self.run_id)
        if self.created_at < 0:
            raise ValueError("run creation time cannot be negative")


@dataclass(frozen=True)
class ScientificAttempt(AgentRecord):
    id: str
    reservation_id: str
    state: Literal["reserved", "launched", "finished", "uncertain", "reconciled"]
    child_action_id: str | None
    measured_cost: float | None
    elapsed_seconds: float | None
    uncertain_cost: bool

    def _validate(self):
        identifier(self.id)
        identifier(self.reservation_id)
        if self.child_action_id is not None:
            parts = self.child_action_id.split(":")
            if len(parts) not in (1, 2):
                raise ValueError("scientific child action has an invalid composite identity")
            for part in parts:
                identifier(part)
        for value in (self.measured_cost, self.elapsed_seconds):
            if value is not None and value < 0:
                raise ValueError("scientific attempt cost cannot be negative")


@dataclass(frozen=True)
class ScientificReceipt(AgentRecord):
    """Allowlisted controller evidence for report reconstruction without science access."""

    schema_version: Literal["1.0"]
    run_id: str
    campaign_identity: str
    revision: int
    phase: str
    objective_metric: str
    objective_direction: Literal["minimize", "maximize"]
    outcome: str | None
    selected_id: str | None
    selected_configuration: Mapping[str, Scalar] | None
    objective_value: float | None
    confirmation: str
    execution_limit: int
    attempts: tuple[ScientificAttempt, ...]
    measured_cost: float
    cost_is_uncertain: bool
    data_exposure: Mapping[str, str]
    committed_capacity: int
    recorded_at: float

    def _validate(self):
        identifier(self.run_id)
        sha256(self.campaign_identity)
        if self.revision < 0 or self.execution_limit <= 0 or self.measured_cost < 0:
            raise ValueError("invalid scientific receipt accounting")
        if len(self.attempts) > self.execution_limit:
            raise ValueError("scientific attempts exceed frozen ceiling")
        if not len(self.attempts) <= self.committed_capacity <= self.execution_limit:
            raise ValueError("invalid committed scientific capacity")
        if self.recorded_at < 0:
            raise ValueError("invalid scientific receipt time")
        unique([attempt.id for attempt in self.attempts], "scientific attempt")
        if (self.selected_id is None) != (self.selected_configuration is None):
            raise ValueError("scientific selection and configuration must both be supplied")


@dataclass(frozen=True)
class ReviewDisposition(AgentRecord):
    """Explicit trusted-caller disposition. No worker operation creates this record."""

    schema_version: Literal["1.0"]
    run_id: str
    invocation_id: str
    review_digest: str
    reason: str
    decision: Literal["continue", "stop"]

    def _validate(self):
        identifier(self.run_id)
        identifier(self.invocation_id)
        sha256(self.review_digest)
