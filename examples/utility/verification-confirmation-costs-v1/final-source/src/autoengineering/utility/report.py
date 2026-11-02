"""Offline suite accounting with full assigned-cell denominators."""

from __future__ import annotations

from .controller import UtilityController
from .costs import join_batch_costs, join_confirmation_costs, reconcile


def accounting_report(store) -> dict:
    state = store.replay()
    controller = UtilityController(store)
    allocations = state["attempts"]
    records, blockers, cell_states = [], [], {}
    children = sorted({a.child_digest for a, _ in allocations.values() if a.phase == "selection"})
    for identity in children:
        try:
            child, bindings = controller._child(identity)
            records.extend(join_batch_costs(child, {b.case_id: b.cell_digest for b in bindings}))
        except (ValueError, OSError) as error:
            # Paths, payloads and exception text may expose private metadata.
            blockers.append({"child_digest": identity, "reason": type(error).__name__})
    for cell in store.spec.cells:
        attempts = [
            (a, status) for a, status in allocations.values() if a.cell_digest == cell.digest
        ]
        cell_states[cell.digest] = attempts[-1][1] if attempts else "not_attempted"
        for allocation, status in attempts:
            if status == "finished" and allocation.phase == "selection":
                try:
                    controller.verify_result(allocation.attempt_id)
                except (ValueError, OSError, KeyError):
                    blockers.append({"cell_digest": cell.digest, "reason": "invalid_child_result"})
    records.extend(join_confirmation_costs(store))
    costs = reconcile(tuple(records), tuple(r.receipt_id for r in records))
    from .scoring import read_receipt

    confirmations = [
        {
            "attempt_id": attempt,
            "receipt_digest": identity,
            "receipt": read_receipt(store.root, identity).to_dict(),
        }
        for attempt, identity in state["confirmation_scores"].items()
    ]
    confirmation_attempts = [
        (a, status) for a, status in allocations.values() if a.phase == "confirmation"
    ]
    pending = any(
        a.attempt_id not in state["confirmation_scores"] for a, _ in confirmation_attempts
    )
    confirmation_state = (
        "reconciliation_required"
        if pending
        else "scored_unanalyzed"
        if confirmations
        else "not_attempted"
    )
    return {
        "schema": "utility-accounting-v1",
        "suite_digest": store.spec.digest,
        "assigned_cells": len(store.spec.cells),
        "cells": cell_states,
        "confirmation_receipts": confirmations,
        "confirmation_state": confirmation_state,
        "role_permissions_reserved": [
            {"cell_digest": cell, "role": role, "calls": count}
            for (cell, role), count in sorted(state["role_counts"].items())
        ],
        "parent_reservations": [
            {"regime": regime, "resource": resource, "quantity": value}
            for (regime, resource), value in sorted(state["used"].items())
        ],
        "physical_receipt_costs": costs,
        "receipts": [r.to_dict() for r in records],
        "evidence_blockers": blockers,
        "complete_cost_evidence": False,
        "cost_limits": [
            "Task-level solver, training, human and preparation receipts remain required",
            "Reservations do not establish physical starts",
            "Per-attempt durations may overlap",
            "Confirmation callback durations include nested workers; worker starts remain unknown",
        ],
        "utility_verdict": "not_attempted",
    }


def render_markdown(document):
    """Render explicit evidence limits without converting unknowns into zeroes."""
    lines = [
        "# Utility accounting",
        "",
        f"Suite: `{document['suite_digest']}`",
        "",
        f"Assigned cells: {document['assigned_cells']}",
        "",
        "| Cell | State |",
        "| --- | --- |",
    ]
    lines.extend(f"| {cell} | {state} |" for cell, state in document["cells"].items())
    lines.extend(
        [
            "",
            "Cost evidence is incomplete.",
            "",
            "| Resource | Units | Known quantity |",
            "| --- | --- | --- |",
        ]
    )
    lines.extend(
        f"| {r['resource']} | {r['units']} | {r['quantity']} |"
        for r in document["physical_receipt_costs"]["known_totals"]
    )
    lines.extend(
        [
            "",
            f"Unknown receipt quantities: {len(document['physical_receipt_costs']['unknown'])}",
            f"Evidence blockers: {len(document['evidence_blockers'])}",
            "",
            "Utility verdict: not_attempted.",
            "",
        ]
    )
    return "\n".join(lines)
