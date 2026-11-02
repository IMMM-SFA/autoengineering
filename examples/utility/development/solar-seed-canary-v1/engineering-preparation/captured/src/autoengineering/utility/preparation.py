"""Reviewable suite preparation using trusted registrations, without dispatch."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from autoengineering.adapters.contracts import AdapterRegistry
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef, ModelSnapshot
from autoengineering.campaign.serialization import Record, digest, unique_json
from .contracts import UtilitySuiteSpec, identifier, sha256
from .exposure import ExposureRecord, PartitionManifest, admit_partition


@dataclass(frozen=True)
class TaskPreparation(Record):
    task_id: str
    adapter_id: str
    dossier: ArtifactRef
    candidates: tuple[ModelSnapshot, ...]
    partition: PartitionManifest
    exposure: ExposureRecord
    qualification: ArtifactRef
    outcome_contract: ArtifactRef

    def _validate(self):
        identifier(self.task_id)
        identifier(self.adapter_id)
        if not self.candidates or len({m.digest for m in self.candidates}) != len(self.candidates):
            raise ValueError("preparation needs an ordered unique candidate pool")


@dataclass(frozen=True)
class PreparationResult(Record):
    schema: Literal["utility-preparation-v1"]
    suite_digest: str
    status: Literal["ready_for_review", "blocked"]
    blockers: tuple[str, ...]
    cells: tuple[str, ...]
    batch_sizes: tuple[int, ...]
    inputs_digest: str
    starts_authorized: Literal[False] = False

    def _validate(self):
        sha256(self.suite_digest)
        sha256(self.inputs_digest)
        if (self.status == "blocked") != bool(self.blockers):
            raise ValueError("preparation status must reflect blockers")


def prepare_suite(spec: UtilitySuiteSpec, tasks: tuple[TaskPreparation, ...], *,
                  source_root: Path, adapters: AdapterRegistry,
                  capabilities: Mapping[str, tuple[str, ...]],
                  register: tuple[ExposureRecord, ...],
                  lock: ArtifactRef | None = None,
                  source_inventory: tuple[ArtifactRef, ...] = ()) -> PreparationResult:
    """Verify source/custody and existing adapter admission without creating a model.

    Capability profiles and AdapterRegistry are application-owned. A reviewed
    qualification artifact is required but its scientific conclusions remain a
    review responsibility. This function grants no execution authority.
    """
    blockers = []
    if lock is None or not source_inventory:
        blockers.append("suite:missing_source_or_lock_closure")
    else:
        try:
            read_bytes(source_root, lock)
            if lock.sha256 != spec.lock_digest:
                raise ValueError("lock identity differs")
            for ref in source_inventory:
                read_bytes(source_root, ref)
            if digest([ref.to_dict() for ref in source_inventory]) != spec.source_digest:
                raise ValueError("source inventory differs")
        except (ValueError, OSError):
            blockers.append("suite:source_or_lock_identity_invalid")
    if len({task.task_id for task in tasks}) != len(tasks):
        raise ValueError("duplicate task preparation")
    declared = {task.task_id: task for task in spec.tasks}
    if set(t.task_id for t in tasks) - declared.keys():
        raise ValueError("preparation references unknown task")
    for missing in sorted(declared.keys() - {t.task_id for t in tasks}):
        blockers.append(f"{missing}:missing_preparation")
    families = {task.family for task in spec.tasks}
    if not {"hydrology", "solar", "engineering"} <= families or not families & {"wind", "hybrid"}:
        blockers.append("suite:incomplete_real_task_families")
    for prepared in tasks:
        task = declared[prepared.task_id]
        try:
            dossier = unique_json(read_bytes(source_root, prepared.dossier).decode())
            if digest(dossier) != task.dossier_digest:
                raise ValueError("dossier identity differs")
            if not isinstance(dossier, dict) or dossier.get("status") != "admitted":
                blockers.append(f"{task.task_id}:dossier_not_admitted")
            outcome = unique_json(read_bytes(source_root, prepared.outcome_contract).decode())
            if digest(outcome) != task.outcome_digest:
                raise ValueError("outcome identity differs")
            # Qualification is a pinned review artifact, never executable input.
            read_bytes(source_root, prepared.qualification)
            if tuple(m.digest for m in prepared.candidates) != task.candidate_digests:
                raise ValueError("candidate order or model identity differs")
            if prepared.partition.digest != task.partition_digest:
                raise ValueError("partition identity differs")
            admit_partition(prepared.partition, prepared.exposure, register, spec.exposure_digest)
            supported = capabilities.get(prepared.adapter_id, ())
            if not set(task.required_capabilities) <= set(supported):
                blockers.append(f"{task.task_id}:unsupported_capability")
            for model in prepared.candidates:
                adapters.validate(prepared.adapter_id, model, source_root)
        except (OSError, ValueError, TypeError):
            # Do not publish raw payloads, private paths or data in error messages.
            blockers.append(f"{task.task_id}:identity_source_or_custody_invalid")
    document = {"tasks": [task.to_dict() for task in tasks],
                "register": [record.to_dict() for record in register],
                "lock": lock.to_dict() if lock else None,
                "source_inventory": [ref.to_dict() for ref in source_inventory],
                "capabilities": {key: list(value) for key, value in capabilities.items()}}
    return PreparationResult("utility-preparation-v1", spec.digest,
                             "blocked" if blockers else "ready_for_review", tuple(blockers),
                             tuple(cell.digest for cell in spec.cells),
                             tuple(len(batch) for batch in spec.child_batches()), digest(document))
