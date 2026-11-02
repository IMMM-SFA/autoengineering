"""Public campaign work reconstructed from committed state, without model imports."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from autoengineering.adapters.contracts import TrainingResult
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.state import ControllerState
from autoengineering.campaign.store import EventStore, StoreError
from .contracts import sha256
from .costs import CostRecord


def _campaign(batch, case, document):
    # Original absolute roots remain metadata after relocation. Never open them.
    original = Path(document["scope"])
    matches = [
        i
        for i, part in enumerate(original.parts[:-1])
        if part == "cases" and original.parts[i + 1] == case
    ]
    if not original.is_absolute() or ".." in original.parts or len(matches) != 1:
        raise StoreError("campaign cost scope is outside its reserved case")
    root = batch.root.joinpath(*original.parts[matches[0] :])
    path = confined_file(root, "campaign.yaml")
    if path.stat().st_size > 4 * 1024 * 1024:
        raise StoreError("campaign cost specification exceeds bound")
    spec = CampaignSpec.from_yaml(path)
    if spec.digest != document["campaign"]:
        raise StoreError("campaign cost specification differs from observation")
    projection = EventStore(root).replay()
    refs = tuple(ref for event in projection.events for ref in event.artifacts)
    for event in reversed(projection.events):
        identity = event.response.result.get("state_id")
        if identity:
            ref = next((r for r in event.artifacts if r.sha256 == identity), None)
            if ref is None:
                raise StoreError("campaign cost lacks committed controller state")
            return root, ControllerState.from_json(read_bytes(root, ref).decode()), refs
    raise StoreError("campaign cost lacks committed controller state")


def _quantities(root, state, refs, reservation, observation, document):
    declared = document["attempt"]
    attempt = next((a for a in state.budget.attempts if a.id == declared["id"]), None)
    expected = (
        "science-"
        + digest(
            {
                "case": reservation.case_id,
                "campaign": document["campaign"],
                "attempt": declared["id"],
            }
        )[:32]
    )
    if (
        attempt is None
        or attempt.to_dict() != declared
        or attempt.receipt is None
        or reservation.id != expected
        or len(observation.evidence) != 1
        or document["stop_verified"] != observation.stop_verified
        or observation.elapsed_seconds != attempt.elapsed_seconds
    ):
        raise StoreError("campaign cost attempt differs from reserved observation")
    raw = read_bytes(root, attempt.receipt, max_bytes=65536)
    if hashlib.sha256(raw).hexdigest() != document["receipt_sha256"]:
        raise StoreError("campaign cost process receipt differs from observation")
    receipt = unique_json(raw.decode())
    identity = receipt.get("identity")
    starts = None
    if identity is not None:
        if (
            identity["nonce"] != attempt.launch_nonce
            or type(identity["pid"]) is not int
            or identity["pid"] <= 0
            or identity["pgid"] != identity["pid"]
        ):
            raise StoreError("campaign cost process identity differs from original attempt")
        starts = 1.0
    elif not (
        receipt.get("recovered") is True
        and receipt.get("nonce") == attempt.launch_nonce
        and receipt.get("attempt_id") == attempt.id
        and not observation.stop_verified
    ):
        raise StoreError("campaign cost lacks original process identity")
    if observation.stop_verified and (
        attempt.state not in ("finished", "reconciled")
        or attempt.uncertain_cost
        or receipt["stopped"] is not True
    ):
        raise StoreError("campaign cost stop differs from committed observation")
    evaluation = next((e for e in state.evaluations if e.attempt_id == attempt.id), None)
    if identity is None and (
        evaluation is None
        or not any(
            r.sha256 == receipt.get("output_sha256") and r in refs for r in evaluation.outputs
        )
    ):
        raise StoreError("legacy campaign recovery lacks committed output")
    status = evaluation.status if evaluation else receipt["status"]
    if document["evaluation_status"] != status or observation.status != (
        status if observation.stop_verified else "reconciliation_required"
    ):
        raise StoreError("campaign cost evaluation differs from observation")
    seconds = None
    lifecycle = evaluation.provenance.get("lifecycle_record") if evaluation else None
    if observation.stop_verified and lifecycle:
        ref = next(
            (
                r
                for r in refs
                if r.sha256 == lifecycle
                and r.producer == attempt.id
                and r.path.endswith("/lifecycle.json")
            ),
            None,
        )
        if ref is None:
            raise StoreError("campaign cost lifecycle is not committed for this attempt")
        metadata = unique_json(read_bytes(root, ref, max_bytes=65536).decode())
        seconds = metadata["elapsed_seconds"]
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise StoreError("campaign cost lifecycle duration is invalid")
        TrainingResult.from_dict(metadata["training"])
        outputs = [
            r
            for r in evaluation.outputs
            if r.media_type == "application/x-npz" and r.sha256 == metadata["output_sha256"]
        ]
        if len(outputs) != 1 or outputs[0] not in refs:
            raise StoreError("campaign cost lifecycle lacks its committed output")
    return (
        ("campaign_process_starts", "count", starts),
        ("campaign_model_lifecycle_duration", "s", seconds),
    )


def join_campaign_costs(batch, case_cells):
    """Read public attempt evidence only, with explicit unknown lifecycle work.

    Starts count owned outer workers, not nested model/solver/training operations.
    Lifecycle duration ends before cleanup and overlaps outer process duration.
    The training record's cost has no unit and cannot be projected as time/money.
    """
    if set(case_cells) != {c.id for c in batch.spec.cases} or len(set(case_cells.values())) != len(
        case_cells
    ):
        raise ValueError("campaign cost mapping must cover unique child cases exactly")
    for cell in case_cells.values():
        sha256(cell)
    state, campaigns, records = batch.replay(), {}, []
    for observation in state.observations.values():
        reservation = state.reservations[observation.reservation_id]
        if reservation.resource != "science":
            continue
        for ref in observation.evidence:
            if ref.media_type != "application/json":
                continue
            document = unique_json(read_bytes(batch.root, ref, max_bytes=65536).decode())
            if (
                not isinstance(document, dict)
                or document.get("kind") != "campaign_attempt_observation"
            ):
                continue
            try:
                key = reservation.case_id, document["scope"], document["campaign"]
                if key not in campaigns:
                    campaigns[key] = _campaign(batch, reservation.case_id, document)
                quantities = _quantities(*campaigns[key], reservation, observation, document)
            except (KeyError, TypeError) as error:
                raise StoreError("campaign cost evidence is malformed") from error
            source = digest(document)
            records.extend(
                CostRecord(
                    "campaign-cost-" + digest({"source": source, "resource": name})[:48],
                    source,
                    "selection",
                    name,
                    units,
                    quantity,
                    (case_cells[reservation.case_id],),
                    (1.0,),
                )
                for name, units, quantity in quantities
            )
    return tuple(records)
