"""Reports are regenerated exclusively from committed records, without model execution."""

from __future__ import annotations

import hashlib

from .spec import CampaignSpec
from .state import ControllerState


def render_report(spec: CampaignSpec, state: ControllerState, *, artifact_prefix: str = "") -> str:
    budget = state.budget
    lines = [
        f"# Campaign {spec.name}",
        "",
        spec.scientific_scope,
        "",
        f"Scientific specification: `{spec.digest}`",
        "",
        f"Outcome: `{state.outcome or 'pending'}`.",
        f"Confirmation: `{state.confirmation}`.",
        "",
        f"Physical attempts: {len(budget.attempts)}. Confirmed: {budget.confirmed_attempts}. "
        f"Unresolved: {budget.unresolved_attempts}.",
        f"Reserved or consumed capacity: {budget.committed_capacity}/{budget.max_executions}.",
        f"Measured cost: {budget.measured_cost:.6g}. Cost uncertainty: {budget.cost_is_uncertain}.",
        f"Charged active time: {budget.charged_seconds:.6g} seconds.",
        "",
        "## Evaluations",
        "",
        "| Evaluation | Split | Execution | RMSE | Checks |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in state.evaluations:
        rmse = item.metrics.get("rmse")
        checks = ", ".join(f"{check.name}: {check.status}" for check in item.checks)
        lines.append(
            f"| {item.id} | {item.split_id} | {item.status} | {rmse if rmse is not None else 'unavailable'} | {checks} |"
        )
    lines.extend(["", "## Decisions", ""])
    for decision in state.decisions:
        lines.extend(
            [
                f"- Comparator `{decision.comparator_id}`: `{decision.outcome}`. "
                f"Selection: `{decision.selected_id}`."
            ]
        )
        lines.extend(f"  - {reason}" for reason in decision.reasons)
    lines.extend(["", "## Admission", ""])
    admitted = {item.proposal.id for item in state.snapshots}
    for proposal in state.proposals:
        lines.append(
            f"- `{proposal.id}`: {'admitted' if proposal.id in admitted else 'rejected or pending'}."
        )
    if state.evaluations:
        state_hash = hashlib.sha256((state.to_json() + "\n").encode()).hexdigest()
        lines.extend(
            [
                "",
                f"[Immutable evaluation and check records]({artifact_prefix}artifacts/{state_hash}/state.json).",
                "",
            ]
        )
    lines.extend(["", "## Immutable output evidence", ""])
    for item in state.evaluations:
        for ref in item.outputs:
            lines.append(
                f"- [{item.id}: output]({artifact_prefix}{ref.path}), SHA-256 `{ref.sha256}`."
            )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "This experimental local workflow evaluates supplied trusted implementations. Process separation "
            "provides lifecycle control and is not a security sandbox. Token ceilings, production agent roles, "
            "new host integrations, automatic model training, and general scientific improvement remain deferred.",
            "",
            "Exposed development data do not establish independent confirmation. Unknown costs and "
            "unavailable checks remain explicit. This report requires no private observation reads or network access.",
            "",
        ]
    )
    return "\n".join(lines)
