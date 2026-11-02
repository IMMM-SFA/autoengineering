"""Bind exact generated-source bytes before selection to the existing scorer identity.

The source policy remains the task's prospective partition identity. A caller-pinned
binding additionally fixes the actual public manifest and private payload hashes.
This supplied trusted path does not admit protected execution or any real task.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.contracts import identifier, sha256
from autoengineering.utility.scoring import validate_grant
from examples.utility import engineering_scenarios as source

DIRECTORY = "engineering-source-bindings"
ACCESS_DIRECTORY = "engineering-source-accesses"


def implementation_identity():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True)
class SourceBinding(Record):
    schema: Literal["utility-engineering-source-binding-v1"]
    task_id: str
    suite_digest: str
    partition_policy_digest: str
    public_manifest_digest: str
    private_record_digest: str
    seed_commitment: str
    source_claim_digest: str
    generation_digest: str
    preparer_source_digest: str
    binding_source_digest: str
    task_admitted: Literal[False] = False
    private_boundary_qualified: Literal[False] = False

    def _validate(self):
        identifier(self.task_id)
        for name in (
            "suite_digest",
            "partition_policy_digest",
            "public_manifest_digest",
            "private_record_digest",
            "seed_commitment",
            "source_claim_digest",
            "generation_digest",
            "preparer_source_digest",
            "binding_source_digest",
        ):
            sha256(getattr(self, name))


def _task(store, binding):
    task = next(t for t in store.spec.tasks if t.task_id == binding.task_id)
    if (
        task.family != "engineering"
        or store.spec.digest != binding.suite_digest
        or task.partition_digest != binding.partition_policy_digest
    ):
        raise ValueError("engineering source binding differs from the immutable task")
    claim = source._read(checked_directory(store.root / source.CLAIMS), binding.task_id + ".json")
    if digest(claim) != binding.source_claim_digest:
        raise ValueError("engineering source binding differs from the original generation claim")
    return task


def seal(store, public_root, *, expected_manifest_digest):
    """Seal actual bytes once, before any selection event, without private reads."""
    try:
        metadata = source.read_public(
            public_root, expected_manifest_digest=expected_manifest_digest
        )
        policy = source.ScenarioPolicy.from_dict(metadata["policy"])
        binding = SourceBinding(
            "utility-engineering-source-binding-v1",
            policy.task_id,
            metadata["suite_digest"],
            policy.digest,
            expected_manifest_digest,
            metadata["private_record_digest"],
            metadata["seed_commitment"],
            metadata["claim_digest"],
            metadata["generation_digest"],
            policy.sampler_source_sha256,
            implementation_identity(),
        )
        if binding.preparer_source_digest != source.source_identity():
            raise ValueError("engineering source preparer changed")
        with store.writer():
            _task(store, binding)
            state = store.replay()
            if state["frozen"] is not None or state["events"]:
                raise ValueError("engineering source binding must precede all selection activity")
            root = store.root / DIRECTORY
            if root.is_symlink():
                raise ValueError("engineering source binding scope is a symlink")
            root.mkdir(mode=0o700, exist_ok=True)
            checked_directory(root)
            path = root / (binding.task_id + ".json")
            if path.exists() or path.is_symlink():
                saved = read_binding(
                    store,
                    reference(
                        store.root,
                        str(path.relative_to(store.root)),
                        media_type="application/json",
                        producer="engineering-source",
                    ),
                )
                if saved != binding:
                    raise ValueError("engineering source binding already sealed differently")
            else:
                durable_write(path, binding.to_json().encode())
            return reference(
                store.root,
                str(path.relative_to(store.root)),
                media_type="application/json",
                producer="engineering-source",
            )
    except Exception:
        pass
    raise ValueError("engineering source sealing failed") from None


def read_binding(store, artifact: ArtifactRef):
    """Read exactly a caller-pinned source-binding artifact, never refresh its hash."""
    try:
        binding = SourceBinding.from_json(
            read_bytes(store.root, artifact, max_bytes=65536).decode()
        )
        if (
            artifact.path != f"{DIRECTORY}/{binding.task_id}.json"
            or artifact.media_type != "application/json"
        ):
            raise ValueError("engineering source binding artifact role differs")
        _task(store, binding)
        return binding
    except Exception:
        pass
    raise ValueError("engineering source binding verification failed") from None


def scorer_identity(binding, scorer_code_digest):
    """Use the existing grant field to bind code plus the exact sealed source."""
    if not isinstance(binding, SourceBinding):
        raise ValueError("engineering source binding required")
    sha256(scorer_code_digest)
    return digest(
        {
            "schema": "utility-engineering-bound-scorer-v1",
            "scorer_code_digest": scorer_code_digest,
            "source_binding_digest": binding.digest,
        }
    )


def open_for_confirmation(
    store, grant, binding_artifact, public_root, private_root, *, scorer_code_digest
):
    """Check the unchanged grant/barrier and source binding before opening private data.

    This is a trusted application callback, not a scorer registration or OS grant.
    A qualified coupled-model scorer must still evaluate all physical checks and
    report its own resource evidence. No model or score is produced here.
    """
    try:
        binding = read_binding(store, binding_artifact)
        if (
            grant.scorer_digest != scorer_identity(binding, scorer_code_digest)
            or grant.partition_digest != binding.partition_policy_digest
            or binding.binding_source_digest != implementation_identity()
            or binding.preparer_source_digest != source.source_identity()
        ):
            raise ValueError("engineering confirmation code or source identity differs")
        state = store.replay()
        validate_grant(store, grant, state["frozen"])
        attempt = "confirmation-" + grant.cell_digest[:48]
        allocation, status = state["attempts"].get(attempt, (None, None))
        if (
            status != "started"
            or allocation.child_digest != grant.digest
            or attempt not in state["confirmation_accesses"]
            or attempt in state["confirmation_scores"]
        ):
            raise ValueError("engineering source requires its active committed confirmation access")
        cell = next(c for c in store.spec.cells if c.digest == grant.cell_digest)
        if cell.task_id != binding.task_id:
            raise ValueError("engineering source binding belongs to another task")
        metadata = source.read_public(
            public_root, expected_manifest_digest=binding.public_manifest_digest
        )
        if (
            metadata["private_record_digest"] != binding.private_record_digest
            or metadata["seed_commitment"] != binding.seed_commitment
        ):
            raise ValueError("engineering source contents differ from sealed binding")
        access_root = store.root / ACCESS_DIRECTORY
        if access_root.is_symlink():
            raise ValueError("engineering source-access scope is a symlink")
        access_root.mkdir(mode=0o700, exist_ok=True)
        checked_directory(access_root)
        claim = {
            "schema": "utility-engineering-bound-source-access-v1",
            "grant_digest": grant.digest,
            "source_binding_digest": binding.digest,
            "public_manifest_digest": binding.public_manifest_digest,
            "private_record_digest": binding.private_record_digest,
            "source_reads_reserved": 1,
            "automatic_retry_allowed": False,
            "task_admitted": False,
        }
        durable_write(access_root / (grant.digest + ".json"), source.canonical_json(claim).encode())
        return source.read_private(
            store,
            public_root,
            private_root,
            expected_manifest_digest=binding.public_manifest_digest,
            expected_selection_digest=grant.selection_digest,
        )
    except Exception:
        pass
    raise ValueError("engineering bound-source access failed") from None
