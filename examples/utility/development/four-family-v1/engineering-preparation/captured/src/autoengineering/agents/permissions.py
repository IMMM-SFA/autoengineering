"""Deny-by-default role policy and exact artifact grants.

Only trusted callers construct grants. Worker output never creates a capability.
Artifact IDs inside a returned document do not grant access to another document.
"""

from __future__ import annotations

from pathlib import Path

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import digest

from .records import (
    CandidateBrief,
    ImplementationBundle,
    NextStep,
    ReviewFindings,
    RoleHandoff,
    SuppliedConfiguration,
    TaskAssignment,
    SourceDraft,
    SINGLE_ROLE,
)

ROLE_OPERATIONS = {
    "orchestrator": frozenset(("assign", "freeze", "stop")),
    "investigator": frozenset(("propose", "stop")),
    "implementer": frozenset(("configure", "stop")),
    "reviewer": frozenset(("review", "stop")),
}
POLICY_DIGEST = digest({role: sorted(ops) for role, ops in ROLE_OPERATIONS.items()})

SINGLE_OPERATIONS = frozenset(("propose", "configure", "review", "freeze", "stop"))
SINGLE_POLICY_DIGEST = digest({SINGLE_ROLE: sorted(SINGLE_OPERATIONS)})


def policy_digest(route):
    if route == "four_role":
        return POLICY_DIGEST
    if route == "single_agent":
        return SINGLE_POLICY_DIGEST
    raise ValueError("unsupported workflow route")


def role_operations(role):
    return SINGLE_OPERATIONS if role == SINGLE_ROLE else ROLE_OPERATIONS[role]


def validate_task_route(task, spec):
    if (task.role == SINGLE_ROLE) != (spec.workflow_route == "single_agent"):
        raise ValueError("task role differs from the frozen workflow route")


def validate_assignment(task: TaskAssignment) -> None:
    if not set(task.allowed_operations) <= role_operations(task.role):
        raise ValueError("assignment grants a forbidden role operation")
    if task.role != "implementer" and any(
        grant.visibility == "candidate_source" for grant in task.grants
    ):
        raise ValueError("candidate workspace access is restricted to implementer")


def read_granted(
    root: Path,
    task: TaskAssignment,
    artifact_id: str,
    *,
    run_id: str,
    role: str,
) -> bytes:
    validate_assignment(task)
    if (run_id, role) != (task.run_id, task.role):
        raise PermissionError("artifact scope differs from caller")
    grants = [grant for grant in task.grants if grant.artifact.sha256 == artifact_id]
    if len(grants) != 1:
        raise PermissionError("artifact was not granted to this task")
    grant = grants[0]
    return read_bytes(root, grant.artifact, max_bytes=grant.max_bytes)


def validate_handoff(
    handoff: RoleHandoff,
    task: TaskAssignment,
    *,
    invocation_id: str,
    campaign_revision: int,
    permitted_implementations: tuple[str, ...],
    candidate_id: str | None = None,
    evaluation_id: str | None = None,
    generated: bool = False,
) -> None:
    """Validate context and citations before any scientific staging or request."""
    validate_assignment(task)
    if (handoff.task_id, handoff.invocation_id, handoff.role) != (
        task.id,
        invocation_id,
        task.role,
    ):
        raise ValueError("handoff task, invocation or role mismatch")
    if handoff.campaign_revision != task.campaign_revision or (
        handoff.campaign_revision != campaign_revision
    ):
        raise ValueError("stale handoff campaign revision")
    if task.expected_schema != f"role-handoff-{handoff.schema_version}":
        raise ValueError("handoff version differs from the assigned schema")
    if handoff.proposed_next_action not in task.allowed_operations:
        raise ValueError("handoff requests a forbidden operation")
    granted = {grant.artifact.sha256 for grant in task.grants}
    if not set(handoff.supporting_artifact_ids) <= granted:
        raise ValueError("handoff cites ungranted evidence")
    output = handoff.output
    if task.role == SINGLE_ROLE:
        action = {
            CandidateBrief: "propose",
            SuppliedConfiguration: "configure",
            ReviewFindings: "review",
            NextStep: handoff.output.action if isinstance(handoff.output, NextStep) else None,
        }.get(type(output))
        if action != handoff.proposed_next_action:
            raise ValueError("single-agent action differs from its typed output")
    if isinstance(output, (CandidateBrief, SuppliedConfiguration)):
        if output.implementation_id not in permitted_implementations:
            raise ValueError("implementation is outside the allowed catalogue")
    if isinstance(output, (CandidateBrief, SuppliedConfiguration, ReviewFindings, SourceDraft)):
        if not set(output.evidence_ids) <= granted:
            raise ValueError("role output cites ungranted evidence")
        if not set(output.evidence_ids) <= set(handoff.supporting_artifact_ids):
            raise ValueError("role evidence is absent from handoff support")
        if candidate_id is not None and output.candidate_id != candidate_id:
            raise ValueError("handoff candidate mismatch")
    if isinstance(output, ReviewFindings) and output.evaluation_id != evaluation_id:
        raise ValueError("handoff evaluation mismatch")
    if isinstance(output, ImplementationBundle):
        if not generated:
            raise ValueError("generated implementations are disabled")
        if output.admitted_identity is not None:
            raise ValueError("worker cannot self-admit an implementation")
    if isinstance(output, SourceDraft) and not generated:
        raise ValueError("source drafts require explicit generated mode")
    if isinstance(output, NextStep) and output.action != handoff.proposed_next_action:
        raise ValueError("orchestrator action differs from handoff")
