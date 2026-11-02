"""One-use, suite-bound custody for supplied normalized annual wind drivers.

This trusted application helper acquires no weather and admits no task/runtime.
Advisory workers must not receive private roots or invoke its preparation path.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from itertools import islice
import os
from pathlib import Path
import stat
from typing import Literal

import numpy as np

from autoengineering.campaign.artifacts import confined_file, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.contracts import identifier, sha256
from autoengineering.utility.scoring import validate_grant
from examples.utility import wind_annual_scoring as kernel
from examples.utility.wind_annual import AnnualWindPlan

CLAIMS = "wind-annual-source-claims"
BINDINGS = "wind-annual-source-bindings"
ACCESSES = "wind-annual-source-accesses"


def source_identity():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True)
class AnnualWindBinding(Record):
    schema: Literal["utility-wind-annual-source-binding-v1"]
    task_id: str
    suite_digest: str
    plan: AnnualWindPlan
    payloads: tuple[ArtifactRef, ...]
    claim_digest: str
    source_code_digest: str
    kernel_code_digest: str
    task_admitted: Literal[False] = False
    private_boundary_qualified: Literal[False] = False

    def _validate(self):
        identifier(self.task_id)
        for value in (
            self.suite_digest,
            self.claim_digest,
            self.source_code_digest,
            self.kernel_code_digest,
        ):
            sha256(value)
        if len(self.payloads) != len(self.plan.sources):
            raise ValueError("annual wind binding has incomplete payload coverage")
        for source, payload in zip(self.plan.sources, self.payloads, strict=True):
            hours = len(kernel._axis(source.year))
            if (
                payload.path != f"year-{source.year}.f64le"
                or payload.size_bytes != 16 * hours
                or payload.media_type != "application/octet-stream"
                or payload.producer != "wind-annual-source"
                or payload.metadata
            ):
                raise ValueError("annual wind payload role or exact shape differs")


def _directory(root, name):
    path = root / name
    if path.is_symlink():
        raise ValueError("annual wind custody scope is a symlink")
    path.mkdir(mode=0o700, exist_ok=True)
    return checked_directory(path)


def _roots(store, public_root, private_root):
    public, private = checked_directory(public_root), checked_directory(private_root)
    roots = (store.root, public, private)
    if any(
        a.is_relative_to(b) or b.is_relative_to(a)
        for i, a in enumerate(roots)
        for b in roots[i + 1 :]
    ):
        raise ValueError("annual wind public, private and suite scopes must be separate")
    return public, private


def _scope(public, private):
    return digest({"public": str(public), "private": str(private)})


def _claim(store, task_id):
    path = reference(
        store.root,
        f"{CLAIMS}/{task_id}.json",
        media_type="application/json",
        producer="wind-annual-source",
    )
    return unique_json(read_bytes(store.root, path, max_bytes=65536).decode())


def prepare(store, task_id, plan, drivers, public_root, private_root):
    """Seal supplied data once before any suite activity; retain uncertain intents.

    Final store binding is published only after every private payload and the
    public metadata. A partial preparation cannot restart under a fresh path.
    Source rights and prior exposure are not established by hashing the input.
    """
    try:
        identifier(task_id)
        if (
            not isinstance(plan, AnnualWindPlan)
            or plan.model_digest != kernel.model_identity()
            or plan.interpretation_digest != digest(kernel.INTERPRETATION)
        ):
            raise ValueError("annual wind plan differs from the supplied kernel")
        public, private = _roots(store, public_root, private_root)
        drivers = tuple(islice(drivers, 9))
        if len(drivers) != len(plan.sources) or len(drivers) > 8:
            raise ValueError("annual wind preparation has incomplete declared years")
        for source, data in zip(plan.sources, drivers, strict=True):
            if (
                not isinstance(data, kernel.AnnualWindDrivers)
                or data.year != source.year
                or data.object_identity_digest != source.object_identity_digest
                or data.manifest_digest != source.point_manifest_digest
            ):
                raise ValueError("annual wind preparation differs from its source plan")
        with store.writer():
            state = store.replay()
            task = next(t for t in store.spec.tasks if t.task_id == task_id)
            if (
                state["frozen"] is not None
                or state["events"]
                or task.family != "wind"
                or task.partition_digest != plan.digest
            ):
                raise ValueError("annual wind preparation must precede selection on its exact task")
            if any(public.iterdir()) or any(private.iterdir()):
                raise ValueError("annual wind preparation roots must be empty")
            claim = {
                "schema": "utility-wind-annual-source-claim-v1",
                "task_id": task_id,
                "suite_digest": store.spec.digest,
                "plan_digest": plan.digest,
                "scope_digest": _scope(public, private),
                "source_code_digest": source_identity(),
                "kernel_code_digest": kernel.source_identity(),
                "automatic_retries": 0,
                "private_payload_writes_reserved": len(drivers),
                "scientific_starts": 0,
            }
            durable_write(
                _directory(store.root, CLAIMS) / (task_id + ".json"), canonical_json(claim).encode()
            )
            payloads = []
            for data in drivers:
                blob = data.speed_m_s.tobytes() + data.direction_deg.tobytes()
                name = f"year-{data.year}.f64le"
                durable_write(private / name, blob)
                payloads.append(
                    ArtifactRef(
                        name,
                        hashlib.sha256(blob).hexdigest(),
                        len(blob),
                        "application/octet-stream",
                        "wind-annual-source",
                        {},
                    )
                )
            binding = AnnualWindBinding(
                "utility-wind-annual-source-binding-v1",
                task_id,
                store.spec.digest,
                plan,
                tuple(payloads),
                digest(claim),
                source_identity(),
                kernel.source_identity(),
            )
            durable_write(public / "binding.json", binding.to_json().encode())
            durable_write(
                _directory(store.root, BINDINGS) / (task_id + ".json"), binding.to_json().encode()
            )
            return reference(
                store.root,
                f"{BINDINGS}/{task_id}.json",
                media_type="application/json",
                producer="wind-annual-source",
            )
    except Exception:
        pass
    raise ValueError("annual wind source preparation failed; preserve existing intents") from None


def read_binding(store, artifact):
    """Verify a caller-pinned binding and original claim without private payloads."""
    try:
        bound = AnnualWindBinding.from_json(
            read_bytes(store.root, artifact, max_bytes=65536).decode()
        )
        task = next(t for t in store.spec.tasks if t.task_id == bound.task_id)
        if (
            artifact.path != f"{BINDINGS}/{bound.task_id}.json"
            or artifact.media_type != "application/json"
            or task.family != "wind"
            or task.partition_digest != bound.plan.digest
            or bound.suite_digest != store.spec.digest
            or bound.claim_digest != digest(_claim(store, bound.task_id))
            or bound.source_code_digest != source_identity()
            or bound.kernel_code_digest != kernel.source_identity()
            or bound.plan.model_digest != kernel.model_identity()
            or bound.plan.interpretation_digest != digest(kernel.INTERPRETATION)
        ):
            raise ValueError("annual wind binding changed its task, source or claim")
        return bound
    except Exception:
        pass
    raise ValueError("annual wind source binding verification failed") from None


def scorer_identity(binding, scorer_code_digest):
    sha256(scorer_code_digest)
    return digest(
        {
            "schema": "utility-wind-annual-bound-scorer-v1",
            "binding_digest": binding.digest,
            "scorer_code_digest": scorer_code_digest,
        }
    )


def open_for_confirmation(
    store, grant, binding_artifact, public_root, private_root, *, scorer_code_digest
):
    """Open each bounded payload once after the full barrier and charged access.

    A durable per-grant intent precedes the first private byte. Partial reads
    remain consumed. This helper produces drivers, not scores or worker grants.
    """
    try:
        bound = read_binding(store, binding_artifact)
        state = store.replay()
        validate_grant(store, grant, state["frozen"])
        attempt = "confirmation-" + grant.cell_digest[:48]
        allocation, status = state["attempts"].get(attempt, (None, None))
        cell = next(c for c in store.spec.cells if c.digest == grant.cell_digest)
        if (
            grant.scorer_digest != scorer_identity(bound, scorer_code_digest)
            or grant.partition_digest != bound.plan.digest
            or cell.task_id != bound.task_id
            or status != "started"
            or allocation.child_digest != grant.digest
            or attempt not in state["confirmation_accesses"]
            or attempt in state["confirmation_scores"]
        ):
            raise ValueError("annual wind source requires original committed confirmation access")
        caps = {cap.name: cap for cap in grant.resources}
        for name, required in (
            ("private_wind_reads", len(bound.payloads)),
            ("private_wind_bytes", sum(p.size_bytes for p in bound.payloads)),
        ):
            cap = caps.get(name)
            if (
                cap is None
                or cap.units != "count"
                or cap.enforcement != "reservation"
                or cap.limit != required
            ):
                raise ValueError("annual wind private read counts/bytes were not reserved")
        public, private = _roots(store, public_root, private_root)
        if (
            _scope(public, private) != _claim(store, bound.task_id)["scope_digest"]
            or read_bytes(public, replace(binding_artifact, path="binding.json"), max_bytes=65536)
            != bound.to_json().encode()
        ):
            raise ValueError("annual wind source roots or public binding changed")
        access_root = _directory(store.root, ACCESSES)
        durable_write(
            access_root / (grant.digest + ".json"),
            canonical_json(
                {
                    "grant_digest": grant.digest,
                    "binding_digest": bound.digest,
                    "private_reads_reserved": len(bound.payloads),
                    "private_bytes_reserved": sum(p.size_bytes for p in bound.payloads),
                    "automatic_retries": 0,
                }
            ).encode(),
        )
        drivers = []
        for source, payload in zip(bound.plan.sources, bound.payloads, strict=True):
            path = confined_file(private, payload.path)
            info = path.stat()
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("annual wind payload is not owner-private")
            durable_write(
                access_root / f"{grant.digest}-{source.year}-start.json",
                canonical_json(
                    {
                        "grant_digest": grant.digest,
                        "source_digest": source.digest,
                        "payload_digest": payload.sha256,
                        "status": "started",
                        "private_bytes_reserved": payload.size_bytes,
                        "automatic_retries": 0,
                    }
                ).encode(),
            )
            blob = read_bytes(private, payload, max_bytes=140544)
            hours = len(kernel._axis(source.year))
            data = np.frombuffer(blob, dtype="<f8").reshape(2, hours)
            value = kernel.AnnualWindDrivers(
                source.year,
                source.object_identity_digest,
                kernel._axis(source.year),
                data[0],
                data[1],
            )
            if value.manifest_digest != source.point_manifest_digest:
                raise ValueError("annual wind private payload differs from point manifest")
            durable_write(
                access_root / f"{grant.digest}-{source.year}-complete.json",
                canonical_json(
                    {
                        "grant_digest": grant.digest,
                        "source_digest": source.digest,
                        "payload_digest": payload.sha256,
                        "status": "verified",
                        "completed_private_reads": 1,
                        "verified_private_bytes": payload.size_bytes,
                    }
                ).encode(),
            )
            drivers.append(value)
        durable_write(
            access_root / f"{grant.digest}-complete.json",
            canonical_json(
                {
                    "grant_digest": grant.digest,
                    "binding_digest": bound.digest,
                    "completed_private_reads": len(drivers),
                    "verified_private_bytes": sum(p.size_bytes for p in bound.payloads),
                    "automatic_retries": 0,
                }
            ).encode(),
        )
        return tuple(drivers)
    except Exception:
        pass
    raise ValueError("annual wind bound-source access failed; no automatic retry") from None
