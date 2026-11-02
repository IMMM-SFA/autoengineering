"""Read-only worker evidence reconstruction without a host or scientific controller."""

from __future__ import annotations

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.serialization import unique_json
from autoengineering.campaign.store import StoreError

from .records import ReviewFindings, RoleHandoff
from .store import WorkerStore
from .deadline import read_deadline_notices


def evidence_report(store: WorkerStore) -> dict:
    projection = store.replay()
    notices = read_deadline_notices(
        store, started_at=projection.started_at, action_ids=set(projection.actions)
    )
    cancelled = []
    for path in sorted((store.root / "control").glob("cancel-*.json")):
        path = confined_file(store.root, f"control/{path.name}")
        if path.stat().st_size > 65536 or unique_json(path.read_text()) != {"intent": "cancel"}:
            raise StoreError("invalid worker cancellation intent")
        cancelled.append(path.name)
    invocations, findings = [], []
    observed = 0
    unknown = 0
    for invocation in projection.invocations.values():
        total = invocation.usage.get("total_tokens")
        if total is None:
            inputs, outputs = (
                invocation.usage.get(name) for name in ("input_tokens", "output_tokens")
            )
            total = inputs + outputs if inputs is not None and outputs is not None else None
        if total is None:
            unknown += 1
        else:
            observed += total
        invocations.append(invocation.to_dict())
        if invocation.normalized_output is not None:
            handoff = RoleHandoff.from_json(
                read_bytes(store.root, invocation.normalized_output).decode()
            )
            if isinstance(handoff.output, ReviewFindings):
                findings.append({"invocation_id": invocation.id, **handoff.output.to_dict()})
    actions = [value.to_dict() for value in projection.actions.values()]
    pending_science = [a.id for a in projection.actions.values() if a.state == "reserved"]
    errors = [
        a.response.error
        for a in projection.actions.values()
        if a.response is not None and a.response.status == "error"
    ]
    blocked = [
        review
        for review in findings
        if (
            review["invocation_id"] not in projection.dispositions
            or projection.dispositions[review["invocation_id"]].decision != "continue"
        )
        and (
            review["recommendation"] != "proceed"
            or review["missing_evidence"]
            or any(f["severity"] == "blocking" for f in review["findings"])
        )
    ]
    science = projection.science[-1] if projection.science else None
    science_event = next(
        (
            f"events/{event.sequence:012d}.json"
            for event in reversed(projection.events)
            if event.record is science
        ),
        None,
    )
    final = next(
        (
            a
            for a in reversed(tuple(projection.actions.values()))
            if a.request is not None
            and a.request.operation == "report"
            and a.response is not None
            and a.response.status == "ok"
        ),
        None,
    )
    if (
        projection.pending
        or projection.pending_preparations
        or pending_science
        or any(n["failures"] and not n["forwarding_resolved"] for n in notices)
    ):
        status = "reconciliation_required"
    elif cancelled:
        status = "cancel_queued"
    elif (
        errors
        or blocked
        or any(d.decision == "stop" for d in projection.dispositions.values())
        or any(p.state == "failed" for p in projection.preparations.values())
    ):
        status = "stopped"
    elif final:
        status = "completed"
    elif any(p.state == "forked" for p in projection.preparations.values()):
        status = "successor_created"
    elif any(p.state in ("checked", "registered") for p in projection.preparations.values()):
        status = "awaiting_trusted_admission"
    elif (
        store.spec.execution_mode == "generated"
        and science
        and science.phase == "candidate_pending"
    ):
        status = "awaiting_source_preparation"
    else:
        status = "idle"
    reserved_checks = {}
    for event in projection.events:
        value = event.record
        if getattr(value, "state", None) == "checking" and hasattr(value, "configuration"):
            configuration = unique_json(read_bytes(store.root, value.configuration).decode())
            ceiling = configuration.get("maximum_container_starts")
            if type(ceiling) is not int or not 1 <= ceiling <= 4:
                raise StoreError("invalid interface reservation")
            reserved_checks[value.id] = ceiling
    observed_times = [value.recorded_at for value in projection.preparations.values()]
    if science is not None:
        observed_times.append(science.recorded_at)
    return {
        "schema_version": "1.0",
        "run_id": store.spec.id,
        "workflow_route": store.spec.workflow_route,
        "review_context": "self_review"
        if store.spec.workflow_route == "single_agent"
        else "independent_role",
        "run_digest": store.spec.digest,
        "campaign_id": store.spec.campaign_id,
        "campaign_identity": store.spec.campaign_identity,
        "status": status,
        "created_at": projection.started_at,
        "deadline_notices": notices,
        "host": store.spec.host.to_dict(),
        "host_configuration": (
            projection.host_configuration.to_dict() if projection.host_configuration else None
        ),
        "source_identity": store.spec.source_identity,
        "environment_identity": store.spec.environment_identity,
        "limits": store.spec.limits.to_dict(),
        "roles_ran": sorted(
            {
                v.role
                for v in projection.tasks.values()
                if any(i.task_id == v.id for i in projection.invocations.values())
            }
        ),
        "tasks": [
            {
                "id": task.id,
                "role": task.role,
                "campaign_revision": task.campaign_revision,
                "allowed_operations": list(task.allowed_operations),
                "grants": [
                    {
                        "artifact_id": g.artifact.sha256,
                        "visibility": g.visibility,
                        "max_bytes": g.max_bytes,
                    }
                    for g in task.grants
                ],
            }
            for task in projection.tasks.values()
        ],
        "invocations": invocations,
        "campaign_actions": actions,
        "review_findings": findings,
        "review_dispositions": [value.to_dict() for value in projection.dispositions.values()],
        "source_preparations": [value.to_dict() for value in projection.preparations.values()],
        "allowances": {
            "invocations_used": len(projection.invocations),
            "invocations_remaining": store.spec.limits.max_invocations
            - len(projection.invocations),
            "tasks_used": len(projection.tasks),
            "repairs_used": projection.repairs_used,
            "observed_tokens": observed,
            "invocations_with_unknown_usage": unknown,
            "subscription_dollar_cost": None,
            "interface_starts_reserved": sum(reserved_checks.values()),
        },
        "worker_stop": "reconciliation_required"
        if projection.pending or projection.pending_preparations
        else ("queued" if cancelled else "not_requested"),
        "scientific_stop": "unknown" if cancelled or pending_science else "not_requested",
        "pending_invocations": [v.id for v in projection.pending],
        "pending_campaign_actions": pending_science,
        "pending_source_preparations": [value.id for value in projection.pending_preparations],
        "campaign_outcome": final.response.result.get("outcome")
        if final
        else (science.outcome if science else None),
        "scientific_evidence": science.to_dict() if science else None,
        "scientific_receipt_event": science_event,
        "physical_work": {
            "attempts": len(science.attempts),
            "unresolved_attempts": sum(
                a.state in ("reserved", "launched", "uncertain") for a in science.attempts
            ),
            "measured_cost": science.measured_cost,
            "cost_is_uncertain": science.cost_is_uncertain,
            "execution_limit": science.execution_limit,
            "available_execution_capacity": science.execution_limit - science.committed_capacity,
        }
        if science
        else None,
        "wall_seconds_observed": max(0, max(observed_times) - projection.started_at)
        if observed_times and projection.started_at is not None
        else None,
        "scientific_report_id": final.response.result.get("report_id") if final else None,
        "confirmation": science.confirmation
        if science
        else next(
            (
                a.response.result.get("confirmation")
                for a in reversed(tuple(projection.actions.values()))
                if a.request is not None
                and a.request.operation == "confirm"
                and a.response is not None
            ),
            None,
        ),
        "limitations": [
            "Worker evidence is reconstructed without reading the scientific campaign.",
            "Raw transcripts remain private and are distinct from normalized handoffs.",
            "Unknown usage remains unknown. Observed-token stops are not in-flight ceilings.",
            "Scripted fake-host runs do not establish model utility or independent confirmation.",
        ],
    }


def render_report(report: dict) -> str:
    lines = [
        "# Agent workflow evidence",
        "",
        f"Run: `{report['run_id']}`",
        f"Status: `{report['status']}`",
        f"Workflow route: `{report['workflow_route']}`",
        f"Review context: `{report['review_context']}`",
        f"Campaign outcome: `{report['campaign_outcome']}`",
        f"Confirmation: `{report['confirmation']}`",
        "",
        "## Invocations",
        "",
        "| Invocation | Role | State | Requested model | Resolved model | Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    roles = {task["id"]: task["role"] for task in report["tasks"]}
    for value in report["invocations"]:
        refs = []
        for name in (
            "prompt",
            "raw_response",
            "final_response",
            "stderr_response",
            "recovery_receipt",
            "normalized_output",
            "parse_failure",
            "completion_receipt",
        ):
            ref = value.get(name)
            if ref is not None:
                refs.append(f"[{name}]({ref['path']})")
        lines.append(
            f"| {value['id']} | {roles[value['task_id']]} | {value['state']} | "
            f"{value['requested_model']} | {value['resolved_model']} | {', '.join(refs)} |"
        )
    lines += [
        "",
        "## Limits and evidence",
        "",
        f"Physical host invocations: {report['allowances']['invocations_used']}",
        f"Repairs: {report['allowances']['repairs_used']}",
        f"Invocations with unknown usage: {report['allowances']['invocations_with_unknown_usage']}",
        "",
        *report["limitations"],
        "",
    ]
    science = report["scientific_evidence"]
    if report["source_preparations"]:
        lines += ["## Source preparation", ""]
        for value in report["source_preparations"]:
            lines += [
                f"{value['id']}: {value['state']} ({value['reason']})",
                f"Registration: `{value['registration_identity']}`",
                f"Successor identity: `{value['successor_identity']}`",
                "",
            ]
    if report["deadline_notices"]:
        lines += ["## Worker deadline", ""]
        for notice in report["deadline_notices"]:
            lines += [
                f"[Cancellation forwarding receipt]({notice['path']})",
                f"Forwarding failures: `{notice['failures']}`",
                "Queued cancellation does not prove that scientific work stopped.",
                "",
            ]
    if science is not None:
        lines += [
            "## Scientific evidence",
            "",
            f"[Controller receipt]({report['scientific_receipt_event']})",
            f"Selected evaluation: `{science['selected_id']}`",
            f"Objective: `{science['objective_metric']}` = `{science['objective_value']}`",
            f"Physical attempts: {len(science['attempts'])}",
            f"Cost uncertain: `{science['cost_is_uncertain']}`",
            "",
        ]
    return "\n".join(lines)
