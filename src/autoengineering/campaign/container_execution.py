"""Trusted binding between one campaign attempt and its isolated container.

No registry activation is provided here. Callers must first stop the native
owner before requesting inner stop. Missing launch evidence remains unresolved.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import numpy as np

from autoengineering.adapters.contracts import PrepareContext, validate_arrays
from autoengineering.adapters.registration import load_registration, validate_model
from autoengineering.agents.container_recovery import reconcile_container, ContainerRecovery
from autoengineering.agents.interface import decode_output

from .artifacts import confined_file, read_arrays, read_bytes
from .records import ArtifactRef, identifier
from .serialization import canonical_json, digest, unique_json
from .store import checked_directory, durable_write


def is_isolated(adapter_id: str) -> bool:
    return (
        isinstance(adapter_id, str)
        and re.fullmatch(r"generated-[0-9a-f]{64}", adapter_id) is not None
    )


def scratch_path(root: Path, attempt_id: str, nonce: str) -> Path:
    identifier(attempt_id)
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ValueError("isolated attempt requires a launch nonce")
    return Path(root).absolute() / "jobs" / f"{attempt_id}-{nonce}-scratch"


def _context(root: Path, job, attempt_id: str, nonce: str):
    root = checked_directory(root)
    if (
        job.get("attempt_id") != attempt_id
        or job.get("nonce") != nonce
        or not is_isolated(job.get("adapter_id"))
        or job.get("bundle_root") != str(root / "bundle")
        or job.get("output_path") != str(root / "jobs" / f"{attempt_id}.npz")
    ):
        raise ValueError("isolated job differs from the reserved attempt")
    context = PrepareContext.from_dict(job["context"])
    scratch = scratch_path(root, attempt_id, nonce)
    if context.scratch_path != str(scratch):
        raise ValueError("isolated scratch differs from the reserved attempt")
    registration, refs = load_registration(
        root / "bundle", expected_identity=job["adapter_id"].removeprefix("generated-")
    )
    validate_model(registration, refs, context.model, context.parameters)
    return context, registration, scratch


def forcing(root: Path, job):
    """Read only an immutable forcing reference under the campaign or its bundle."""
    forcing_root = Path(job["forcing_root"])
    if forcing_root not in (root, root / "bundle"):
        raise ValueError("isolated forcing root is outside the campaign")
    ref = ArtifactRef.from_dict(job["forcing"])
    if ref.media_type == "application/json":
        return {
            name: np.asarray(value)
            for name, value in unique_json(read_bytes(forcing_root, ref).decode()).items()
        }
    return read_arrays(forcing_root, ref)


def launch_observer(root: Path, job, *, attempt_id: str, nonce: str):
    """Create a trusted callback that commits ownership before Docker can start."""
    root = checked_directory(root)
    _, registration, scratch = _context(root, job, attempt_id, nonce)
    folder = checked_directory(root / "attempts" / attempt_id)

    def observe(execution: Path, receipt):
        execution = Path(execution).absolute()
        if (
            execution.name != "execution"
            or execution.parent.parent != scratch
            or not re.fullmatch(r"isolated-[0-9a-f]{32}", execution.parent.name)
            or set(receipt) != {"container_id", "nonce", "intent_digest", "image_id"}
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["container_id"])
            or not re.fullmatch(r"[0-9a-f]{32}", receipt["nonce"])
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["intent_digest"])
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", receipt["image_id"])
        ):
            raise ValueError("container launch receipt differs from its reserved workspace")
        checked_directory(execution)
        binding = {
            "schema_version": "1.0",
            "attempt_id": attempt_id,
            "attempt_nonce": nonce,
            "registration_identity": registration.digest,
            "execution_path": str(execution.relative_to(root)),
            **receipt,
        }
        durable_write(folder / "container-launch.json", canonical_json(binding).encode())

    return observe


@dataclass(frozen=True)
class IsolatedAttemptRecovery:
    stopped: bool
    no_launch: bool
    execution_path: str | None
    physical: ContainerRecovery | None
    binding_digest: str | None = None

    def outputs(self, ports):
        if (
            self.binding_digest is None
            or self.physical is None
            or self.physical.result_status != "success"
        ):
            raise ValueError("isolated attempt has no recovered successful result")
        return {
            name: np.asarray(value)
            for name, value in decode_output(self.physical.stdout, ports).items()
        }


def reconcile_attempt(root: Path, job, *, attempt_id: str, nonce: str, stop: bool = False):
    """Reconcile one reserved scratch directory, without launching or charging it."""
    root = checked_directory(root)
    context, registration, scratch = _context(root, job, attempt_id, nonce)
    binding_path = root / "attempts" / attempt_id / "container-launch.json"
    if binding_path.is_symlink() or scratch.is_symlink():
        raise ValueError("isolated attempt contains a symlink")
    binding = None
    if binding_path.exists():
        binding = unique_json(confined_file(binding_path.parent, binding_path.name).read_text())
        if (
            binding.get("schema_version") != "1.0"
            or binding.get("attempt_id") != attempt_id
            or binding.get("attempt_nonce") != nonce
            or binding.get("registration_identity") != registration.digest
            or set(binding)
            != {
                "schema_version",
                "attempt_id",
                "attempt_nonce",
                "registration_identity",
                "execution_path",
                "container_id",
                "nonce",
                "intent_digest",
                "image_id",
            }
        ):
            raise ValueError("container launch binding differs from the reserved attempt")
    # The native owner must already be stopped: no directory here then proves
    # it did not reach Docker creation. Incomplete creation evidence is not
    # treated as no launch, because create may have succeeded before its ack.
    if not scratch.exists():
        if binding is not None:
            raise ValueError("container launch workspace disappeared")
        return IsolatedAttemptRecovery(True, True, None, None)
    checked_directory(scratch)
    children = list(scratch.iterdir())
    if not children:
        if binding is not None:
            raise ValueError("container launch workspace disappeared")
        return IsolatedAttemptRecovery(True, True, None, None)
    if len(children) != 1 or not re.fullmatch(r"isolated-[0-9a-f]{32}", children[0].name):
        raise ValueError("isolated attempt has an ambiguous workspace")
    handle = checked_directory(children[0])
    execution = handle / "execution"
    if execution.is_symlink():
        raise ValueError("isolated execution contains a symlink")
    if not execution.exists():
        if binding is not None:
            raise ValueError("container launch execution disappeared")
        return IsolatedAttemptRecovery(True, True, None, None)
    relative = str(execution.relative_to(root))
    if binding is not None and binding.get("execution_path") != relative:
        raise ValueError("container launch path differs from its binding")
    if binding is not None:
        declaration = unique_json(confined_file(execution, "intent.json").read_text())
        owned = {
            "container_id": confined_file(execution, "container-id").read_text(),
            "nonce": declaration["nonce"],
            "intent_digest": digest(declaration),
            "image_id": declaration["image_id"],
        }
        if any(binding[name] != value for name, value in owned.items()):
            raise ValueError("container identity differs from its durable launch binding")
    inputs = validate_arrays(
        forcing(root, job), context.model.inputs, registration.specification.inputs
    )
    payload = canonical_json(
        {
            "schema_version": "1.0",
            "inputs": {name: value.tolist() for name, value in inputs.items()},
        }
    ).encode()
    sources = {
        name: read_bytes(
            root / "bundle",
            next(ref for ref in context.model.source_bundle if ref.path == f"generated/{name}"),
            max_bytes=65536,
        )
        for name in ("adapter.py", "driver.py")
    }
    physical = reconcile_container(
        execution,
        qualification_root=handle / "evidence/qualification",
        qualification_digest=registration.review.qualification_digest,
        sources=sources,
        payload=payload,
        stop=stop,
    )
    if binding is not None and any(
        binding.get(name) != value
        for name, value in {
            "container_id": physical.container_id,
            "nonce": physical.nonce,
            "intent_digest": physical.intent_digest,
            "image_id": unique_json(confined_file(execution, "intent.json").read_text())[
                "image_id"
            ],
        }.items()
    ):
        raise ValueError("container identity differs from its durable launch binding")
    return IsolatedAttemptRecovery(
        physical.stopped,
        False,
        relative,
        physical,
        digest(binding) if binding is not None else None,
    )
