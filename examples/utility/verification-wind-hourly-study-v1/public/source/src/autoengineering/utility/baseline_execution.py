"""Frozen deterministic baseline confirmation reuse above existing score journals.

The designated source is executed by ConfirmationService. Followers never get a
new scoring reservation. Successful source receipts are allocated only through
the predeclared groups. No scientific runner or second ledger is introduced.
"""

from __future__ import annotations

from autoengineering.campaign.serialization import digest
from .baselines import SharedBaseline
from .confirmation import read_selected_state, read_manifest


def validate_source_selection(store, cell_digest, manifest, scorer_digest):
    policy = store.spec.baseline_reuse
    if policy is None:
        return
    group = next((g for g in policy.groups if cell_digest in g.cell_digests), None)
    if group is None:
        return
    if cell_digest != group.source_cell_digest:
        raise ValueError("frozen baseline follower cannot dispatch scoring work")
    if scorer_digest != group.scorer_digest:
        raise ValueError("baseline scorer differs from the frozen reference profile")
    selected = {c.cell_digest: c for c in manifest.cells}
    allocation = SharedBaseline("0" * 64, group.cell_digests, group.allocation)
    allocation.validate(store.spec)
    allocation.validate_selections(selected)
    source = selected[group.source_cell_digest]
    if source.model.sha256 != group.model_digest:
        raise ValueError("selected baseline differs from the frozen reference model")
    state = read_selected_state(store.root, source.selected_state)
    if digest(state.to_dict()["configuration"]) != group.configuration_digest:
        raise ValueError("selected baseline parameters differ from frozen defaults")


def frozen_baseline_allocations(store, state=None):
    """Reconstruct declared allocations from successful original public receipts."""
    policy = store.spec.baseline_reuse
    if policy is None:
        return ()
    state = state if state is not None else store.replay()
    if state["frozen"] is None:
        return ()
    from .scoring import read_receipt, _read, ConfirmationGrant

    manifest = read_manifest(store.root, state["frozen"])
    result = []
    for group in policy.groups:
        matches = [
            state["confirmation_scores"].get(attempt)
            for attempt, (allocation, _) in state["attempts"].items()
            if allocation.phase == "confirmation"
            and allocation.cell_digest == group.source_cell_digest
        ]
        identities = [identity for identity in matches if identity is not None]
        if not identities:
            continue
        if len(identities) != 1:
            raise ValueError("baseline reference requires one original score")
        receipt = read_receipt(store.root, identities[0])
        if receipt.score.status != "success" or receipt.score.feasible is not True:
            continue
        source_attempt = next(
            attempt
            for attempt, (allocation, _) in state["attempts"].items()
            if allocation.phase == "confirmation"
            and allocation.cell_digest == group.source_cell_digest
        )
        grant = _read(
            store.root,
            state["confirmation_accesses"][source_attempt],
            "confirmation-grant.json",
            ConfirmationGrant,
        )
        validate_source_selection(store, group.source_cell_digest, manifest, grant.scorer_digest)
        result.append(SharedBaseline(identities[0], group.cell_digests, group.allocation))
    return tuple(result)


def resolve_baseline_allocations(store, state, requested=()):
    if store.spec.baseline_reuse is None:
        return tuple(requested)
    frozen = frozen_baseline_allocations(store, state)
    if requested and tuple(requested) != frozen:
        raise ValueError("requested baseline allocation differs from frozen execution policy")
    return frozen
