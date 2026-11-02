"""Suite-wide immutable selection sealing, without private-label access."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes, reference, put_bytes
from autoengineering.campaign.records import (
    ArtifactRef,
    ModelSnapshot,
    EvaluationRecord,
    CandidateSnapshot,
    Scalar,
)
from autoengineering.campaign.serialization import Record, unique_json, canonical_json
from autoengineering.campaign.store import StoreError
from .contracts import identifier, sha256


@dataclass(frozen=True)
class SelectedState(Record):
    schema: Literal["utility-selected-state-v1"]
    model: ModelSnapshot
    configuration: Mapping[str, Scalar]
    evaluation: EvaluationRecord
    candidate: CandidateSnapshot | None = None

    def _validate(self):
        if not self.evaluation.eligible or dict(self.evaluation.configuration) != dict(
            self.configuration
        ):
            raise ValueError("selected state needs eligible evidence for its exact configuration")
        if self.candidate is None:
            expected = self.model.digest
        else:
            if self.candidate.model != self.model:
                raise ValueError("selected candidate differs from frozen model")
            expected = self.candidate.digest
        if self.evaluation.model_id != expected:
            raise ValueError("selected evaluation belongs to a different scientific model")


@dataclass(frozen=True)
class SelectedArtifactBinding(Record):
    schema: Literal["utility-selected-artifact-binding-v1"]
    kind: Literal["model", "selected_state"]
    artifact: ArtifactRef

    def _validate(self):
        if not 65536 < self.artifact.size_bytes <= 64 * 1024 * 1024:
            raise ValueError("selected artifact binding requires a bounded large payload")
        if self.artifact.media_type != "application/json":
            raise ValueError("selected artifact binding requires JSON")


def selected_artifact_evidence(batch, artifact, document, kind):
    """Retain legacy small receipts; bind larger suite artifacts by exact identity."""
    raw = canonical_json(document).encode()
    if len(raw) != artifact.size_bytes or hashlib.sha256(raw).hexdigest() != artifact.sha256:
        raise StoreError("selected artifact differs from supplied evidence payload")
    if artifact.size_bytes <= 65536:
        return batch.evidence(document)
    return batch.evidence(
        SelectedArtifactBinding("utility-selected-artifact-binding-v1", kind, artifact).to_dict()
    )


def has_selected_artifact_evidence(child, evidence, artifact, kind, *, allow_bindings):
    if artifact.sha256 in {ref.sha256 for ref in evidence}:
        return True
    if not allow_bindings:
        return False
    for ref in evidence:
        if ref.media_type != "application/json":
            continue
        document = unique_json(read_bytes(child.root, ref, max_bytes=65536).decode())
        if (
            isinstance(document, dict)
            and document.get("schema") == "utility-selected-artifact-binding-v1"
        ):
            binding = SelectedArtifactBinding.from_dict(document)
            if binding.kind == kind and binding.artifact == artifact:
                return True
    return False


@dataclass(frozen=True)
class SelectedCell(Record):
    cell_digest: str
    status: Literal["selected", "no_eligible_model", "insufficient_data", "failed", "not_attempted"]
    attempt_id: str | None
    child_result_digest: str | None
    model: ArtifactRef | None
    reason: str
    selected_state: ArtifactRef | None = None

    def _validate(self):
        sha256(self.cell_digest)
        if self.attempt_id is not None:
            identifier(self.attempt_id)
        if self.child_result_digest is not None:
            sha256(self.child_result_digest)
        if (self.attempt_id is None) != (self.child_result_digest is None):
            raise ValueError("child attempt and result must be present together")
        if (self.status == "selected") != (self.model is not None):
            raise ValueError("selected cells require a model; other statuses cannot select one")
        if (self.status == "selected") != (self.selected_state is not None):
            raise ValueError("selected cells require immutable parameter/evaluation state")
        if self.status == "selected" and self.attempt_id is None:
            raise ValueError("selection needs authoritative child evidence")
        if self.status == "not_attempted" and self.attempt_id is not None:
            raise ValueError("attempted work cannot be relabeled not_attempted")


@dataclass(frozen=True)
class SelectionManifest(Record):
    schema: Literal["utility-selection-v1", "utility-selection-v2"]
    suite_digest: str
    protocol_digest: str
    cells: tuple[SelectedCell, ...]

    def _validate(self):
        sha256(self.suite_digest)
        sha256(self.protocol_digest)
        if self.schema == "utility-selection-v1" and any(
            c.status == "selected" for c in self.cells
        ):
            raise ValueError("selected parameter states require selection schema v2")
        if not self.cells or len({c.cell_digest for c in self.cells}) != len(self.cells):
            raise ValueError("selection cells must be nonempty and unique")


def read_manifest(root, identity):
    sha256(identity)
    path = f"artifacts/{identity}/selection.json"
    ref = reference(root, path, media_type="application/json", producer="selection-reader")
    if ref.sha256 != identity:
        raise StoreError("selection manifest content changed")
    return SelectionManifest.from_json(read_bytes(root, ref).decode())


def validate_manifest(store, manifest, attempts, events):
    """Validate a barrier using authoritative prefix state, without recursive replay."""
    from .controller import UtilityController

    if (manifest.suite_digest, manifest.protocol_digest) != (
        store.spec.digest,
        store.spec.protocol_digest,
    ):
        raise StoreError("selection suite or protocol identity differs")
    if tuple(c.cell_digest for c in manifest.cells) != tuple(c.digest for c in store.spec.cells):
        raise StoreError("selection barrier must cover the complete ordered matrix")
    cells = {c.digest: c for c in store.spec.cells}
    tasks = {t.task_id: t for t in store.spec.tasks}
    for selection in manifest.cells:
        assigned = [
            (allocation, state)
            for allocation, state in attempts.values()
            if allocation.cell_digest == selection.cell_digest
        ]
        if not assigned:
            if selection.status != "not_attempted":
                raise StoreError("unattempted cell needs explicit not_attempted outcome")
            continue
        if selection.attempt_id is None:
            raise StoreError("attempted cell requires pinned terminal child evidence")
        allocation, state = attempts.get(selection.attempt_id, (None, None))
        if state != "finished" or allocation.cell_digest != selection.cell_digest:
            raise StoreError("selection child is not a finished assigned attempt")
        finishes = [
            e for e in events if e.operation == "finish" and e.attempt_id == selection.attempt_id
        ]
        if len(finishes) != 1 or finishes[0].result_digest != selection.child_result_digest:
            raise StoreError("selection differs from committed child result")
        child, bindings = UtilityController(store)._child(allocation.child_digest)
        binding = next(b for b in bindings if b.cell_digest == selection.cell_digest)
        path = f"artifacts/{selection.child_result_digest}/child-result.json"
        ref = reference(store.root, path, media_type="application/json", producer="reader")
        if ref.sha256 != selection.child_result_digest:
            raise StoreError("saved child result changed")
        result = unique_json(read_bytes(store.root, ref).decode())
        read_bytes(child.root, ArtifactRef.from_dict(result["manifest"]))
        actual = child.replay().finished[binding.case_id]
        if result["case_result"] != actual.to_dict():
            raise StoreError("selection child evidence changed")
        for evidence in actual.evidence:
            read_bytes(child.root, evidence)
        if selection.model is not None:
            if actual.status != "passed":
                raise StoreError("failed child cannot provide a selected model")
            if not has_selected_artifact_evidence(
                child,
                actual.evidence,
                selection.model,
                "model",
                allow_bindings=manifest.schema == "utility-selection-v2",
            ):
                raise StoreError("selected snapshot is absent from authoritative child evidence")
            model = ModelSnapshot.from_json(read_bytes(store.root, selection.model).decode())
            if not has_selected_artifact_evidence(
                child,
                actual.evidence,
                selection.selected_state,
                "selected_state",
                allow_bindings=manifest.schema == "utility-selection-v2",
            ):
                raise StoreError("selected state is absent from authoritative child evidence")
            bound = SelectedState.from_json(
                read_bytes(store.root, selection.selected_state).decode()
            )
            if bound.model != model:
                raise StoreError("selected state differs from immutable model")
            task = tasks[cells[selection.cell_digest].task_id]
            if model.digest not in task.candidate_digests:
                raise StoreError("selected model is outside the frozen candidate pool")
            for source in model.source_bundle:
                read_bytes(store.root, source)


def freeze(store, manifest: SelectionManifest):
    """Commit the complete barrier once. No scorer, provider or data loader is invoked."""
    with store.writer():
        state = store.replay()
        if state["frozen"] is not None:
            saved = read_manifest(store.root, state["frozen"])
            if saved != manifest:
                raise StoreError("selection is already frozen with different content")
            return state["frozen"]
        validate_manifest(store, manifest, state["attempts"], state["events"])
        ref = put_bytes(
            store.root,
            (manifest.to_json() + "\n").encode(),
            name="selection.json",
            media_type="application/json",
            producer="utility-selection",
        )
        store.fault("before_selection_freeze")
        store.append(
            request_id="suite-selection-freeze",
            operation="freeze",
            cell_digest=store.spec.cells[0].digest,
            attempt_id="suite-selection-freeze",
            child_digest=store.spec.digest,
            result_digest=ref.sha256,
        )
        store.fault("after_selection_freeze")
        return ref.sha256
