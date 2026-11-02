"""Exclusive physical receipts and explicit allocation without invented zero costs."""

from __future__ import annotations

from dataclasses import dataclass

from autoengineering.campaign.serialization import Record
from .contracts import identifier, sha256


PROVIDER_TOKEN_FIELDS = (
    "input_tokens",
    "uncached_input_tokens",
    "cached_input_tokens",
    "cache_creation_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)


@dataclass(frozen=True)
class CostRecord(Record):
    receipt_id: str
    source_digest: str
    category: str
    resource: str
    units: str
    quantity: float | None
    cell_digests: tuple[str, ...]
    allocation: tuple[float, ...]

    def _validate(self):
        identifier(self.receipt_id)
        sha256(self.source_digest)
        identifier(self.category)
        identifier(self.resource)
        if self.units not in ("count", "s", "USD", "CPU-s", "GPU-s", "byte", "token"):
            raise ValueError("unknown cost units")
        if self.quantity is not None and self.quantity < 0:
            raise ValueError("cost must be nonnegative or explicitly unknown")
        if not self.cell_digests or len(set(self.cell_digests)) != len(self.cell_digests):
            raise ValueError("cost needs unique assigned cells")
        for value in self.cell_digests:
            sha256(value)
        if len(self.allocation) != len(self.cell_digests):
            raise ValueError("allocation must match assigned cells")
        if any(v < 0 for v in self.allocation) or abs(sum(self.allocation) - 1) > 1e-12:
            raise ValueError("exclusive allocation fractions must sum to one")


def reconcile(records: tuple[CostRecord, ...], expected_receipts: tuple[str, ...]) -> dict:
    """Reject duplicate charging; retain missing and unknown evidence in totals."""
    if len(set(expected_receipts)) != len(expected_receipts):
        raise ValueError("duplicate expected receipt")
    ids = [r.receipt_id for r in records]
    sources = [(r.source_digest, r.resource, r.units) for r in records]
    if len(set(ids)) != len(ids) or len(set(sources)) != len(sources):
        raise ValueError("duplicate physical receipt")
    if set(ids) - set(expected_receipts):
        raise ValueError("unassigned physical receipt")
    totals = {}
    unknown = []
    for record in records:
        key = (record.resource, record.units)
        if record.quantity is None:
            unknown.append(record.receipt_id)
        else:
            totals[key] = totals.get(key, 0.0) + record.quantity
    missing = sorted(set(expected_receipts) - set(ids))
    return {
        "complete": not missing and not unknown,
        "missing": missing,
        "unknown": sorted(unknown),
        "known_totals": [
            {"resource": r, "units": u, "quantity": q} for (r, u), q in sorted(totals.items())
        ],
    }


def join_batch_costs(child, case_cells: dict[str, str]) -> tuple[CostRecord, ...]:
    """Read pinned batch evidence without converting permission into execution.

    Durations describe individual physical receipts and may overlap. They are
    separate host/science quantities, not an inclusive wall-time measurement.
    Actual starts, solver work, training, money and human effort require additional
    task/provider receipts. Unknown quantities remain unknown here.
    """
    from autoengineering.campaign.artifacts import read_bytes
    from autoengineering.campaign.serialization import digest

    if set(case_cells) != {c.id for c in child.spec.cases}:
        raise ValueError("cost mapping must cover exactly the child cases")
    if len(set(case_cells.values())) != len(case_cells):
        raise ValueError("cost mapping assigns a cell twice")
    for cell in case_cells.values():
        sha256(cell)
    state = child.replay()
    records = []
    for reservation in state.reservations.values():
        observation = state.observations.get(reservation.id)
        if observation is not None:
            for ref in observation.evidence:
                read_bytes(child.root, ref)
        source = digest(
            {
                "batch": child.digest,
                "reservation": reservation.to_dict(),
                "observation": observation.to_dict() if observation else None,
            }
        )
        resource = reservation.resource
        metrics = [
            (f"{resource}_reservations", "count", 1),
            (f"{resource}_duration", "s", observation.elapsed_seconds if observation else None),
            (
                f"{resource}_starts",
                "count",
                0 if observation and observation.status == "not_launched" else None,
            ),
        ]
        if resource == "host":
            metrics.append(("provider_spend", "USD", None))
            # Copy normalized observation fields. Components can overlap totals.
            # Missing categories are not zero and are not derived by subtraction.
            for field in PROVIDER_TOKEN_FIELDS:
                metrics.append(
                    (
                        "provider_" + field,
                        "token",
                        observation.usage.get(field) if observation else None,
                    )
                )
        for name, units, quantity in metrics:
            receipt_id = (
                "cost-"
                + digest({"batch": child.digest, "reservation": reservation.id, "metric": name})[
                    :48
                ]
            )
            records.append(
                CostRecord(
                    receipt_id,
                    source,
                    "selection",
                    name,
                    units,
                    quantity,
                    (case_cells[reservation.case_id],),
                    (1.0,),
                )
            )
    for finished in state.finished.values():
        for ref in finished.evidence:
            read_bytes(child.root, ref)
    return tuple(records)


def join_confirmation_costs(store) -> tuple[CostRecord, ...]:
    """Export public confirmation evidence, without private reads or scorer calls.

    Callback duration includes preparation and any nested worker. It must not be
    added to overlapping worker durations. A completed callback does not prove a
    particular number of OS worker/model starts. Legacy scores retain unknown time.
    """
    from autoengineering.campaign.serialization import digest
    from .scoring import read_receipt

    state = store.replay()
    from .baseline_execution import frozen_baseline_allocations

    shared_by_score = {a.score_digest: a for a in frozen_baseline_allocations(store, state)}
    records = []
    for allocation, _ in state["attempts"].values():
        if allocation.phase != "confirmation":
            continue
        attempt = allocation.attempt_id
        access = state["confirmation_accesses"].get(attempt)
        score_id = state["confirmation_scores"].get(attempt)
        receipt = read_receipt(store.root, score_id) if score_id else None
        shared = shared_by_score.get(score_id)
        measured = receipt.measurement if receipt else None
        composite = receipt.composite if receipt else None
        execution = (
            composite.inner_execution if composite else receipt.execution if receipt else None
        )
        inference_proof = None
        inference_status = None
        transition = None
        if composite is not None or access is not None:
            from .scoring import CompositeConfirmationGrant, ConfirmationGrant, _read

            grant = _read(store.root, access, "confirmation-grant.json", ConfirmationGrant)
            if isinstance(grant, CompositeConfirmationGrant):
                from .composite_scoring import read_stage_transition

                path = store.root / "composite-transitions" / f"{grant.digest}.json"
                if path.exists() or path.is_symlink():
                    transition, (_, inferred, _, inference_proof) = read_stage_transition(
                        store, grant
                    )
                    inference_status = inferred.status
        source_fields = {
            "suite": store.spec.digest,
            "allocation": allocation.to_dict(),
            "access": access,
            "score": score_id,
        }
        if transition is not None:
            source_fields["inference_transition"] = transition.digest
        source = digest(source_fields)
        metrics = (
            ("confirmation_reservations", "count", 1),
            ("confirmation_access_intents", "count", int(access is not None)),
            ("confirmation_scores_committed", "count", int(score_id is not None)),
            ("confirmation_callbacks_completed", "count", 1 if measured else None),
            ("confirmation_callback_duration", "s", measured.elapsed_seconds if measured else None),
            (
                "confirmation_scoring_starts",
                "count",
                execution.scoring_process_starts
                if execution
                else 0
                if composite or (inference_status is not None and inference_status != "success")
                else None,
            ),
        )
        if receipt is not None and receipt.recovery is not None:
            metrics += (("confirmation_recoveries_committed", "count", 1),)
        from .execution_receipts import GuestCompositeScorerRegistration

        guest_inference = transition is not None and isinstance(
            transition.registration, GuestCompositeScorerRegistration
        )
        if guest_inference:
            inferred_count = inference_proof["container_starts"]
            scoring_count = (
                execution.container_starts
                if execution
                else (0 if inference_status != "success" else None)
            )
            inferred_seconds = inference_proof["elapsed_seconds"]
            scoring_seconds = (
                execution.lifecycle_seconds
                if execution
                else (0 if inference_status != "success" else None)
            )
            metrics += (
                ("confirmation_inference_container_starts", "count", inferred_count),
                ("confirmation_scoring_container_starts", "count", scoring_count),
                (
                    "confirmation_container_starts",
                    "count",
                    None if scoring_count is None else inferred_count + scoring_count,
                ),
                (
                    "confirmation_container_lifecycle_duration",
                    "s",
                    None
                    if inferred_seconds is None or scoring_seconds is None
                    else inferred_seconds + scoring_seconds,
                ),
            )
        elif execution is not None:
            metrics += (
                ("confirmation_container_starts", "count", execution.container_starts),
                ("confirmation_container_lifecycle_duration", "s", execution.lifecycle_seconds),
            )
        if inference_proof is not None:
            metrics += (
                ("confirmation_inference_starts", "count", 1),
                (
                    "confirmation_inference_lifecycle_duration",
                    "s",
                    inference_proof["elapsed_seconds"],
                ),
            )
        for name, units, quantity in metrics:
            identity = (
                "cost-"
                + digest({"suite": store.spec.digest, "attempt": attempt, "metric": name})[:48]
            )
            records.append(
                CostRecord(
                    identity,
                    source,
                    "confirmation",
                    name,
                    units,
                    quantity,
                    shared.cell_digests if shared else (allocation.cell_digest,),
                    shared.allocation if shared else (1.0,),
                )
            )
    return tuple(records)
