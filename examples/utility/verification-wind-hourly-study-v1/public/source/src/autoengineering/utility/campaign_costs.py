"""Public campaign work reconstructed from committed state, without model imports."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from autoengineering.adapters.contracts import TrainingResult, TrainingArtifactBundle
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.state import ControllerState
from autoengineering.campaign.store import EventStore, StoreError
from .contracts import sha256
from .costs import CostRecord


@dataclass(frozen=True)
class _Campaign:
    root: Path
    state: ControllerState
    refs: tuple
    spec: CampaignSpec
    events: tuple


@dataclass(frozen=True)
class _Training:
    origin: str
    cell: str
    trained: bool
    records: tuple[CostRecord, ...]
    lifecycle: ArtifactRef


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
            return _Campaign(
                root,
                ControllerState.from_json(read_bytes(root, ref).decode()),
                refs,
                spec,
                projection.events,
            )
    raise StoreError("campaign cost lacks committed controller state")


def _quantities(campaign, reservation, observation, document):
    root, state, refs = campaign.root, campaign.state, campaign.refs
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


def _training(campaign, observation, document, cell):
    """Use only the event that committed this exact evaluation and its closure."""
    if not observation.stop_verified:
        if campaign.spec.training is not None:
            return (
                _training_record(digest(document), cell, "unverified_training_work", "count", None),
            ), None
        return (), None
    root, state = campaign.root, campaign.state
    attempt_id = document["attempt"]["id"]
    evaluation = next((e for e in state.evaluations if e.attempt_id == attempt_id), None)
    if evaluation is not None and evaluation.provenance.get("training_terminal_record"):
        return _terminal_training(campaign, evaluation, cell)
    identity = evaluation.provenance.get("lifecycle_record") if evaluation else None
    if identity is None:
        if campaign.spec.training is not None:
            return (
                _training_record(digest(document), cell, "unverified_training_work", "count", None),
            ), None
        return (), None
    lifecycle = next(
        (
            r
            for r in campaign.refs
            if r.sha256 == identity
            and r.producer == attempt_id
            and r.path.endswith("/lifecycle.json")
        ),
        None,
    )
    if lifecycle is None:
        raise StoreError("training evaluation lacks its committed lifecycle")
    metadata = unique_json(read_bytes(root, lifecycle, max_bytes=65536).decode())
    training = TrainingResult.from_dict(metadata["training"])
    if training.artifact is None:
        return (), None
    matches = []
    for event in campaign.events:
        if event.operation not in ("action_finished", "recovery"):
            continue
        lifecycle = next(
            (
                r
                for r in event.artifacts
                if r.sha256 == identity
                and r.producer == attempt_id
                and r.path.endswith("/lifecycle.json")
            ),
            None,
        )
        if lifecycle is None:
            continue
        state_ref = next(
            (r for r in event.artifacts if r.sha256 == event.response.result.get("state_id")), None
        )
        if state_ref is None:
            raise StoreError("training lifecycle lacks its original state commit")
        committed = ControllerState.from_json(read_bytes(root, state_ref).decode())
        if evaluation in committed.evaluations:
            matches.append((event, lifecycle))
            break
    if not matches:
        raise StoreError("training evaluation requires one original lifecycle commit")
    event, lifecycle = matches[0]
    text = training.artifact.metadata.get("training_bundle")
    if text is None:
        if training.artifact not in event.artifacts:
            raise StoreError("unprofiled training artifact is absent from its original commit")
        if training.status != "trained":
            return tuple(
                _training_record(lifecycle.sha256, cell, name, units, value)
                for name, units, value in (
                    ("unprofiled_frozen_fit_reuses", "count", 1.0),
                    ("unprofiled_training_preparation", "count", None),
                )
            ), None
        return tuple(
            _training_record(lifecycle.sha256, cell, name, units, value)
            for name, units, value in (
                ("unprofiled_training_results", "count", 1.0),
                ("unprofiled_training_work", "count", None),
                ("unprofiled_training_duration", "s", None),
            )
        ), None
    bundle_ref = ArtifactRef.from_json(text)
    if bundle_ref not in event.artifacts:
        raise StoreError("training bundle is absent from its original lifecycle commit")
    bundle = TrainingArtifactBundle.from_json(
        read_bytes(root, bundle_ref, max_bytes=65536).decode()
    )
    for ref in (bundle.primary, *bundle.companions):
        if ref not in event.artifacts:
            raise StoreError("training closure member is absent from its original lifecycle commit")
    by_name = {Path(r.path).name: r for r in bundle.companions}
    if set(by_name) != {"training-profile.json", "training-intent.json", "training-result.json"}:
        raise StoreError("campaign training cost profile is not supported")
    from .trained_selection import RoutingSelectionArtifacts, verify_routing_selection
    from .hydrology_training import (
        RoutingTrainingProfile,
        read_training_costs,
        routing_training_identity,
    )

    evidence = RoutingSelectionArtifacts(
        "utility-routing-selection-artifacts-v1",
        bundle.primary,
        by_name["training-profile.json"],
        by_name["training-intent.json"],
        by_name["training-result.json"],
        bundle_ref,
        lifecycle,
    )
    if evaluation.model_id == campaign.spec.baseline.model.digest:
        model = campaign.spec.baseline.model
    else:
        snapshots = [s for s in state.snapshots if s.digest == evaluation.model_id]
        if len(snapshots) != 1:
            raise StoreError("training evaluation has no committed model snapshot")
        model = snapshots[0].model
    bound = SimpleNamespace(
        model=model,
        configuration=evaluation.configuration,
        evaluation=evaluation,
        training=evidence,
    )
    verify_routing_selection(root, bound)
    profile = RoutingTrainingProfile.from_json(
        read_bytes(root, evidence.profile, max_bytes=4 * 1024 * 1024).decode()
    )
    seed = int(evaluation.provenance["execution_seed"])
    costs = read_training_costs(
        root,
        evidence.intent,
        evidence.result,
        identity=routing_training_identity(model, evaluation.configuration, seed, profile),
        profile=profile,
        seed=seed,
        cell_digest=cell,
    )
    return (), _Training(
        evidence.intent.sha256, cell, training.status == "trained", costs, lifecycle
    )


def _terminal_training(campaign, evaluation, cell):
    from autoengineering.campaign.training import FittingGrant, fitting_grant
    from .training_terminal import TerminalTrainingEvidence, terminal_training_costs

    identity = evaluation.provenance["training_terminal_record"]
    ref = next(
        (
            r
            for r in campaign.refs
            if r.sha256 == identity
            and r.producer == evaluation.attempt_id
            and r.path.endswith("/terminal-training.json")
        ),
        None,
    )
    if ref is None:
        raise StoreError("terminal training record is not committed")
    original = None
    for event in campaign.events:
        if (
            event.operation not in ("action_finished", "recovery", "cancelled_after_recovery")
            or ref not in event.artifacts
        ):
            continue
        state_ref = next(
            (r for r in event.artifacts if r.sha256 == event.response.result.get("state_id")), None
        )
        if (
            state_ref is not None
            and evaluation
            in ControllerState.from_json(read_bytes(campaign.root, state_ref).decode()).evaluations
        ):
            original = event
            break
    if original is None:
        raise StoreError("terminal training lacks its original evaluation commit")
    evidence = TerminalTrainingEvidence.from_json(
        read_bytes(campaign.root, ref, max_bytes=65536).decode()
    )
    if any(r not in original.artifacts for r in evidence.references()):
        raise StoreError("terminal training closure is absent from its original commit")
    grant = FittingGrant.from_json(
        read_bytes(campaign.root, evidence.grant, max_bytes=4 * 1024 * 1024).decode()
    )
    if evaluation.model_id == campaign.spec.baseline.model.digest:
        model = campaign.spec.baseline.model
    else:
        models = [s.model for s in campaign.state.snapshots if s.digest == evaluation.model_id]
        if len(models) != 1:
            raise StoreError("terminal training model is not committed")
        model = models[0]
    seed = int(evaluation.provenance["execution_seed"])
    attempt = next(
        (a for a in campaign.state.budget.attempts if a.id == evaluation.attempt_id), None
    )
    role = next((d.role for d in campaign.spec.data if d.id == evaluation.split_id), None)
    if attempt is None or role is None:
        raise StoreError("terminal training lacks its declared execution role or attempt")
    forcing = next(d.artifact for d in campaign.spec.data if d.role == "forcing")
    expected = fitting_grant(
        campaign.spec,
        model,
        grant.adapter_id,
        attempt.id,
        attempt.launch_nonce,
        seed,
        role,
        forcing,
        evaluation.configuration,
    )
    reserved = False
    for event in campaign.events:
        if event.operation != "action_reserved":
            continue
        state_ref = next(
            (r for r in event.artifacts if r.sha256 == event.response.result.get("state_id")), None
        )
        if state_ref is None:
            continue
        state = ControllerState.from_json(read_bytes(campaign.root, state_ref).decode())
        original_attempt = next((a for a in state.budget.attempts if a.id == attempt.id), None)
        if original_attempt is not None:
            reserved = (
                evidence.grant in event.artifacts
                and original_attempt.state == "launched"
                and original_attempt.launch_nonce == attempt.launch_nonce
            )
            break
    if grant != expected or not reserved:
        raise StoreError("terminal training grant differs from original reservation")
    records = terminal_training_costs(
        campaign.root, evidence, grant, model, evaluation.configuration, seed, cell
    )
    if records is None:
        return (
            _training_record(ref.sha256, cell, "unverified_training_work", "count", None),
        ), None
    return (), _Training(evidence.intent.sha256, cell, True, records, ref)


def _training_record(source, cell, name, units, value):
    return CostRecord(
        "campaign-training-" + digest({"source": source, "resource": name})[:48],
        source,
        "training",
        name,
        units,
        value,
        (cell,),
        (1.0,),
    )


def join_campaign_costs(batch, case_cells):
    """Read public attempt evidence only, with explicit unknown lifecycle work.

    Starts count owned outer workers, not nested model/solver/training operations.
    Lifecycle duration ends before cleanup and overlaps outer process duration.
    Profiled training uses its own explicit units. Unprofiled training and frozen
    fits lacking an in-cell verified origin retain unknown preparation work.
    """
    if set(case_cells) != {c.id for c in batch.spec.cases} or len(set(case_cells.values())) != len(
        case_cells
    ):
        raise ValueError("campaign cost mapping must cover unique child cases exactly")
    for cell in case_cells.values():
        sha256(cell)
    state, campaigns, records = batch.replay(), {}, []
    training_origins, reuses = {}, []
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
                quantities = _quantities(campaigns[key], reservation, observation, document)
                extra, link = _training(
                    campaigns[key], observation, document, case_cells[reservation.case_id]
                )
                records.extend(extra)
                if link is not None:
                    if link.trained:
                        if link.origin in training_origins:
                            raise StoreError(
                                "one training intent is claimed by multiple physical attempts"
                            )
                        training_origins[link.origin] = link.cell
                        records.extend(link.records)
                    else:
                        reuses.append(link)
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
    for link in reuses:
        records.append(
            _training_record(
                link.lifecycle.sha256, link.cell, "frozen_fit_inference_reuses", "count", 1.0
            )
        )
        origin = training_origins.get(link.origin)
        if origin != link.cell:
            name = (
                "unverified_training_preparation"
                if origin is None
                else "unallocated_shared_training"
            )
            records.append(_training_record(link.lifecycle.sha256, link.cell, name, "count", None))
    return tuple(records)
