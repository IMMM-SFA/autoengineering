"""Stopped-attempt training evidence without a successful model lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, unique_json
from .hydrology_training import (
    RoutingTrainingProfile,
    TrainingWork,
    read_training_costs,
    routing_training_identity,
)


@dataclass(frozen=True)
class TerminalTrainingEvidence(Record):
    schema: Literal["utility-terminal-training-v1"]
    attempt_id: str
    nonce: str
    disposition: Literal["captured", "invalid"]
    grant: ArtifactRef
    profile: ArtifactRef
    intent: ArtifactRef | None
    result: ArtifactRef | None
    fit: ArtifactRef | None

    def references(self):
        return tuple(
            r
            for r in (self.grant, self.profile, self.intent, self.result, self.fit)
            if r is not None
        )


def terminal_training_costs(root, evidence, grant, model, parameters, seed, cell):
    """Original-event authority is supplied by the parent campaign reader."""
    if evidence.disposition != "captured":
        raise ValueError("terminal training evidence is invalid")
    if (
        evidence.attempt_id != grant.attempt_id
        or evidence.nonce != grant.nonce
        or grant.model_digest != model.digest
        or grant.seed != seed
    ):
        raise ValueError("terminal training evidence belongs to another execution")
    profile = RoutingTrainingProfile.from_json(
        read_bytes(root, evidence.profile, max_bytes=4 * 1024 * 1024).decode()
    )
    clock = grant.data.ports[0].time
    if (
        clock.dates != profile.fitting_dates
        or clock.scoring_mask != profile.valid_mask
        or model.implementations.get("training") != profile.digest
    ):
        raise ValueError("terminal training profile differs from original fitting permission")
    if evidence.intent is None:
        if evidence.result is not None or evidence.fit is not None:
            raise ValueError("terminal training work lacks its original intent")
        return None
    if evidence.result is not None:
        work = TrainingWork.from_json(read_bytes(root, evidence.result, max_bytes=65536).decode())
        if work.trained_artifact != evidence.fit:
            raise ValueError("terminal training fit differs from its result")
    elif evidence.fit is not None:
        raise ValueError("terminal training fit lacks its work receipt")
    return read_training_costs(
        root,
        evidence.intent,
        evidence.result,
        identity=routing_training_identity(model, parameters, seed, profile),
        profile=profile,
        seed=seed,
        cell_digest=cell,
    )


def capture_terminal_training(root, spec, job_path, job, context):
    """Call only after verifying the original worker has stopped. Never load labels."""
    from autoengineering.campaign.training import verify_fitting_grant

    if job["adapter_id"] != "hydrology-learned-routing-v1":
        return ()
    grant = verify_fitting_grant(job_path, job, context)
    if grant is None:
        return ()
    grant_ref = ArtifactRef.from_dict(job["fitting_grant"])
    declared = next(r for r in spec.provenance.sources if r.path == "routing-runtime.json")
    runtime = unique_json(read_bytes(root / "bundle", declared, max_bytes=4 * 1024 * 1024).decode())
    profile = RoutingTrainingProfile.from_dict(runtime["training_profile"])
    profile_ref = put_bytes(
        root,
        profile.to_json().encode(),
        name="training-profile.json",
        media_type="application/json",
        producer=grant.attempt_id,
    )
    refs = [grant_ref, profile_ref]
    captured = {"intent": None, "result": None, "fit": None}
    disposition = "captured"
    try:
        scratch = Path(context.scratch_path)
        for key in ("intent", "result"):
            name = f"training-{key}.json"
            path = scratch / name
            if not path.exists() and not path.is_symlink():
                continue
            if confined_file(scratch, name).stat().st_size > 65536:
                raise ValueError("terminal training receipt exceeds bound")
            source = reference(
                scratch, name, media_type="application/json", producer=grant.attempt_id
            )
            ref = put_bytes(
                root,
                read_bytes(scratch, source, max_bytes=65536),
                name=name,
                media_type="application/json",
                producer=grant.attempt_id,
            )
            captured[key] = ref
            refs.append(ref)
        if captured["result"] is not None:
            work = TrainingWork.from_json(
                read_bytes(root, captured["result"], max_bytes=65536).decode()
            )
            if work.trained_artifact is not None:
                original = work.trained_artifact
                saved = put_bytes(
                    root,
                    read_bytes(scratch, original, max_bytes=65536),
                    name=Path(original.path).name,
                    media_type=original.media_type,
                    producer=original.producer,
                )
                saved = replace(saved, metadata=original.metadata)
                if saved != original:
                    raise ValueError("terminal training fit is not portable")
                captured["fit"] = saved
                refs.append(saved)
        evidence = TerminalTrainingEvidence(
            "utility-terminal-training-v1",
            grant.attempt_id,
            grant.nonce,
            disposition,
            grant_ref,
            profile_ref,
            **captured,
        )
        terminal_training_costs(
            root, evidence, grant, context.model, context.parameters, context.seed, "0" * 64
        )
    except (ValueError, OSError, KeyError, TypeError):
        disposition = "invalid"
    evidence = TerminalTrainingEvidence(
        "utility-terminal-training-v1",
        grant.attempt_id,
        grant.nonce,
        disposition,
        grant_ref,
        profile_ref,
        **captured,
    )
    ref = put_bytes(
        root,
        evidence.to_json().encode(),
        name="terminal-training.json",
        media_type="application/json",
        producer=grant.attempt_id,
    )
    return (ref, *refs)
