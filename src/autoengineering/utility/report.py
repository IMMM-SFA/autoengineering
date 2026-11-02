"""Offline suite accounting with full assigned-cell denominators."""

from __future__ import annotations

from .controller import UtilityController
from .costs import join_batch_costs, join_confirmation_costs, reconcile
from .native_costs import join_native_costs
from .scenario_costs import join_scenario_costs
from .campaign_costs import join_campaign_costs


def accounting_report(store, *, cost_inputs=None) -> dict:
    state = store.replay()
    controller = UtilityController(store)
    allocations = state["attempts"]
    records, blockers, cell_states = [], [], {}
    children = sorted({a.child_digest for a, _ in allocations.values() if a.phase == "selection"})
    for identity in children:
        try:
            child, bindings = controller._child(identity)
            mapping = {b.case_id: b.cell_digest for b in bindings}
            records.extend(join_batch_costs(child, mapping))
            records.extend(join_native_costs(child, mapping))
            records.extend(join_scenario_costs(child, mapping))
            records.extend(join_campaign_costs(child, mapping))
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
    from .baseline_selection import allocate_selection_costs, selection_reference_costs
    records = allocate_selection_costs(store, records)
    records.extend(selection_reference_costs(store, state))
    records.extend(join_confirmation_costs(store))
    if cost_inputs is not None:
        from .load_costs import join_cost_inputs
        records.extend(join_cost_inputs(store, cost_inputs))
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
    document = {
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
            "Scoring starts require execution receipts; callback duration includes nested work",
            "Container lifecycle durations overlap callback durations; do not add them",
            "Provider token components overlap totals; do not sum distinct token resources",
            "Missing token fields and billed provider spend remain unknown",
        ],
        "utility_verdict": "not_attempted",
    }

    if cost_inputs is not None:
        if store.replay()["head"] != state["head"]:
            raise ValueError("suite changed during accounting reconstruction")
        document.update(schema="utility-accounting-v2", cost_inputs_digest=cost_inputs.digest,
                        source_head=state["head"])
        document["cost_limits"].extend([
            "Load work receipts are trusted application evidence, not OS execution proof",
            "Do not add load reservations or known-completed subsets to full totals",
            "Component linearization counts include Newton work and are not FLOPs",
        ])
    return document


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
            "Container lifecycle durations overlap callback durations. Do not add them.",
            "Provider token components overlap totals. Do not sum distinct token resources.",
            "Missing token fields and billed provider spend remain unknown.",
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
    if "cost_inputs_digest" in document:
        lines.extend(["Load reservations and known-completed subsets overlap full totals. Do not add them.",
                      "Component linearization counts include Newton work and are not FLOPs.", ""])
    return "\n".join(lines)
