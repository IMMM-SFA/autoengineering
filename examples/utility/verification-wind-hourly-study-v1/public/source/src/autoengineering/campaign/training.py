"""Explicit fitting grants for trusted daily-prefix supervised execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from autoengineering.adapters.contracts import validate_arrays
from .artifacts import read_arrays, read_bytes
from .records import ArtifactRef, DataContract
from .serialization import Record, digest
from .spec import CampaignSpec
from .state import ControllerState
from .store import EventStore


@dataclass(frozen=True)
class FittingGrant(Record):
    schema: Literal["campaign-fitting-grant-v1"]
    campaign_digest: str
    model_digest: str
    adapter_id: str
    attempt_id: str
    nonce: str
    seed: int
    configuration_digest: str
    data: DataContract
    forcing: ArtifactRef


def fitting_grant(spec, model, adapter_id, attempt_id, nonce, seed, role, forcing, parameters):
    policy = spec.training
    if policy is None or adapter_id not in policy.adapter_ids:
        return None
    if role not in ("comparison", "fitting") or forcing != next(
        d.artifact for d in spec.data if d.role == "forcing"
    ):
        raise ValueError("training is not permitted for this execution role or forcing")
    if model.inputs != spec.baseline.model.inputs or model.outputs != spec.baseline.model.outputs:
        raise ValueError("training model interface differs from its declared fitting policy")
    data = next(d for d in spec.data if d.id == policy.fitting_data_id)
    return FittingGrant(
        "campaign-fitting-grant-v1",
        spec.digest,
        model.digest,
        adapter_id,
        attempt_id,
        nonce,
        seed,
        digest(dict(parameters)),
        data,
        forcing,
    )


def verify_fitting_grant(job_path, job, context):
    """Verify immutable permission without opening forcing or labels."""
    spec = CampaignSpec.from_yaml(job_path.parent.parent / "campaign.yaml")
    expected = fitting_grant(
        spec,
        context.model,
        job["adapter_id"],
        job.get("attempt_id"),
        job["nonce"],
        context.seed,
        job["role"],
        ArtifactRef.from_dict(job["forcing"]),
        context.parameters,
    )
    ref = job.get("fitting_grant")
    if expected is None:
        if ref is not None or context.permitted_data_ids:
            raise ValueError("worker has fitting access without a declared training policy")
        return None
    if ref is None or context.permitted_data_ids != (expected.data.id,):
        raise ValueError("worker fitting grant or permitted data IDs differ from policy")
    campaign_root = job_path.parent.parent
    scratch = campaign_root / "jobs" / f"{expected.attempt_id}-{expected.nonce}"
    if str(scratch) != context.scratch_path:
        raise ValueError("worker training scratch differs from its original attempt")
    ref = ArtifactRef.from_dict(ref)
    grant = FittingGrant.from_json(
        read_bytes(campaign_root, ref, max_bytes=4 * 1024 * 1024).decode()
    )
    if grant != expected:
        raise ValueError("worker fitting grant differs from original execution identity")
    committed = False
    for event in EventStore(campaign_root).replay().events:
        if event.operation != "action_reserved" or ref not in event.artifacts:
            continue
        state_ref = next(
            (r for r in event.artifacts if r.sha256 == event.response.result.get("state_id")), None
        )
        if state_ref is None:
            continue
        state = ControllerState.from_json(read_bytes(campaign_root, state_ref).decode())
        committed = any(
            a.id == grant.attempt_id and a.launch_nonce == grant.nonce and a.state == "launched"
            for a in state.budget.attempts
        )
        if committed:
            break
    if not committed:
        raise ValueError("worker fitting grant lacks its original attempt reservation")
    return grant


def worker_fitting_data(job_path, job, context, root, forcing):
    """Open only granted fitting labels after verifying the original reservation."""
    grant = verify_fitting_grant(job_path, job, context)
    if grant is None:
        return None
    data = grant.data
    observed = validate_arrays(read_arrays(root, data.artifact), data.ports, data.ports)
    n = len(data.ports[0].time.dates)
    payload = {name: np.array(value[:n], copy=True) for name, value in forcing.items()}
    payload["mask"] = np.asarray(data.ports[0].time.scoring_mask, dtype=bool)
    payload["labels"] = np.where(payload["mask"], observed["prediction"], 0.0)
    return payload
