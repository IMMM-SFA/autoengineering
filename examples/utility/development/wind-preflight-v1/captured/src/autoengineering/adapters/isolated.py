"""Standalone registry adapter for one reviewed, fixed Python component.

The campaign controller does not activate this backend yet. A caller must not
infer container stop from an outer process exit or from cleanup alone.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import threading
import uuid

import numpy as np

from autoengineering.agents.containers import DockerBoundary, ContainerResult
from autoengineering.agents.interface import decode_output
from autoengineering.agents.qualification import verify_qualification, VerifiedQualification
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory

from .contracts import AdapterRegistration, PrepareContext, TrainingResult, validate_arrays
from .registration import (
    FILES,
    load_registration,
    extract_archive,
    verify_evidence,
    SourceRegistration,
    validate_model,
)


@dataclass
class IsolatedHandle:
    context: PrepareContext
    root: Path
    registration: SourceRegistration
    qualification: VerifiedQualification
    sources: Mapping[str, bytes]
    closed: bool = False
    used: bool = False


class IsolatedAdapter:
    """No candidate import, training, dependency installation or parameter search."""

    def __init__(self, root: Path, identity: str):
        self.root, self.identity = checked_directory(root), identity
        self._active: IsolatedHandle | None = None
        self._cancel = threading.Event()
        self.last_execution: Path | None = None
        self.last_result: ContainerResult | None = None
        self.launch_observer = None

    def prepare(self, context: PrepareContext) -> IsolatedHandle:
        if self._active is not None:
            raise ValueError("registered adapter already has an active lifecycle")
        self.last_execution = None
        self.last_result = None
        registration, refs = load_registration(self.root, expected_identity=self.identity)
        model = context.model
        validate_model(registration, refs, model, context.parameters)
        scratch = checked_directory(Path(context.scratch_path))
        root = scratch / f"isolated-{uuid.uuid4().hex}"
        root.mkdir(mode=0o700)
        extract_archive(read_bytes(self.root, refs[3]), root / "evidence")
        verify_evidence(root / "evidence", registration)
        qualification = verify_qualification(
            root / "evidence/qualification",
            expected_digest=registration.review.qualification_digest,
        )
        sources = {
            "adapter.py": read_bytes(self.root, refs[1], max_bytes=65536),
            "driver.py": read_bytes(self.root, refs[2], max_bytes=65536),
        }
        handle = IsolatedHandle(context, root, registration, qualification, sources)
        self._active = handle
        self._cancel.clear()
        return handle

    def validate(self, handle: IsolatedHandle) -> None:
        if handle is not self._active or handle.closed:
            raise ValueError("registered adapter handle is absent or closed")

    def train(
        self, handle: IsolatedHandle, fitting_data: Mapping[str, np.ndarray]
    ) -> TrainingResult:
        self.validate(handle)
        if fitting_data:
            raise ValueError("registered fixed adapters do not train")
        return TrainingResult("not_applicable", None, None)

    def run(
        self, handle: IsolatedHandle, forcing: Mapping[str, np.ndarray]
    ) -> dict[str, np.ndarray]:
        self.validate(handle)
        if handle.used:
            raise ValueError("registered adapter requires a fresh lifecycle for another execution")
        inputs = validate_arrays(
            forcing, handle.context.model.inputs, handle.registration.specification.inputs
        )
        payload = canonical_json(
            {
                "schema_version": "1.0",
                "inputs": {name: value.tolist() for name, value in inputs.items()},
            }
        ).encode()
        handle.used = True
        execution = handle.root / "execution"
        self.last_execution = execution
        boundary = DockerBoundary(handle.qualification.runtime)
        try:
            result = boundary.run_qualified(
                handle.sources,
                qualification_root=handle.root / "evidence/qualification",
                qualification_digest=handle.registration.review.qualification_digest,
                entrypoint="driver.py",
                payload=payload,
                root=execution,
                limits=handle.qualification.limits,
                wall_seconds=5,
                cancelled=self._cancel.is_set,
                on_launch=lambda receipt: (
                    self.launch_observer(execution, receipt) if self.launch_observer else None
                ),
            )
        except BaseException:
            if execution.is_dir():
                boundary._queue_stop(execution, "owner_failed")
            raise
        self.last_result = result
        if not result.stopped or result.status != "success":
            raise ValueError(
                f"isolated execution ended as {result.status}; inspect its stop receipt"
            )
        values = decode_output(result.stdout, handle.registration.specification.outputs)
        return {name: np.asarray(value) for name, value in values.items()}

    def inspect(self, handle, outputs):
        self.validate(handle)
        return {}

    def request_cancel(self):
        self._cancel.set()

    def cleanup(self, handle: IsolatedHandle | None) -> None:
        if handle is not None:
            self._cancel.set()
            handle.closed = True
            if self._active is handle:
                self._active = None
        # Keep extracted evidence and all physical receipts for reconciliation.


def registration_entry(root: Path, *, expected_identity: str) -> AdapterRegistration:
    """Application-only registration. A worker cannot supply this factory."""
    registration, _ = load_registration(root, expected_identity=expected_identity)
    return AdapterRegistration(
        registration.adapter_id, "1.0", lambda: IsolatedAdapter(root, expected_identity), FILES
    )
