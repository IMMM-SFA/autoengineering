"""Confined, digest-verified artifact access without model imports."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat

from autoengineering.optimization import NpzReadLimits, read_verified_npz

from .records import ArtifactRef, relative_path

MAX_FILE_BYTES = 64 * 1024 * 1024


def confined_file(root: Path, relative: str) -> Path:
    relative_path(relative)
    root = Path(root).absolute()
    # Check every existing ancestor, including the supplied root's ancestors.
    target = root / relative
    for path in (*reversed(target.parents), target):
        if path.is_symlink():
            raise ValueError("artifact path contains a symlink")
    if not target.is_file() or not stat.S_ISREG(target.stat().st_mode):
        raise ValueError("artifact must be a regular file")
    return target


def read_bytes(root: Path, reference: ArtifactRef, *, max_bytes: int = MAX_FILE_BYTES) -> bytes:
    path = confined_file(root, reference.path)
    if reference.size_bytes > max_bytes:
        raise ValueError("artifact exceeds size limit")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != reference.size_bytes:
            raise ValueError("artifact type/size mismatch")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(max_bytes + 1)
    finally:
        os.close(descriptor)
    if len(data) != reference.size_bytes or hashlib.sha256(data).hexdigest() != reference.sha256:
        raise ValueError("artifact digest/size mismatch")
    return data


def reference(root: Path, relative: str, *, media_type: str, producer: str) -> ArtifactRef:
    path = confined_file(root, relative)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("artifact exceeds size limit")
    data = path.read_bytes()
    return ArtifactRef(
        relative, hashlib.sha256(data).hexdigest(), len(data), media_type, producer, {}
    )


def read_arrays(root: Path, artifact: ArtifactRef, *, limits: NpzReadLimits = NpzReadLimits()):
    read_bytes(root, artifact, max_bytes=limits.max_compressed_bytes)
    return read_verified_npz(confined_file(root, artifact.path), artifact.sha256, limits=limits)


def put_bytes(root: Path, data: bytes, *, name: str, media_type: str, producer: str) -> ArtifactRef:
    """Create a content-addressed immutable result, without overwriting existing bytes."""
    from .store import checked_directory, durable_write

    relative_path(name)
    if "/" in name:
        raise ValueError("artifact name must be a basename")
    root = checked_directory(root)
    content_hash = hashlib.sha256(data).hexdigest()
    directory = root / "artifacts" / content_hash
    if directory.is_symlink():
        raise ValueError("artifact directory cannot be a symlink")
    directory.mkdir(mode=0o700, exist_ok=True)
    checked_directory(directory)
    path = directory / name
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise ValueError("immutable artifact conflict")
    else:
        durable_write(path, data)
    return reference(root, str(path.relative_to(root)), media_type=media_type, producer=producer)


def commit_worker_lifecycle(
    root: Path, scratch: Path, raw: bytes, *, output_sha256: str, producer: str
) -> tuple[ArtifactRef, ...]:
    """Capture a completed worker's explicit training closure before parent commit.

    Normal completion and recovery share this path. Untrained metadata retains
    its original bytes. Content-addressed bundle references survive relocation.
    The caller commits every returned reference in the same authoritative event.
    """
    import math
    from dataclasses import replace
    from autoengineering.adapters.contracts import TrainingArtifactBundle, TrainingResult
    from .serialization import canonical_json, unique_json

    if len(raw) > 65536:
        raise ValueError("worker lifecycle metadata exceeds bound")
    metadata = unique_json(raw.decode())
    if not isinstance(metadata, dict) or set(metadata) != {
        "training",
        "elapsed_seconds",
        "output_sha256",
    }:
        raise ValueError("invalid worker lifecycle metadata")
    seconds = metadata["elapsed_seconds"]
    if (
        type(seconds) not in (int, float)
        or not math.isfinite(seconds)
        or seconds < 0
        or metadata["output_sha256"] != output_sha256
    ):
        raise ValueError("worker lifecycle duration or output differs")
    training = TrainingResult.from_dict(metadata["training"])
    retained = []

    def capture(ref, *, maximum=MAX_FILE_BYTES, portable=False):
        data = read_bytes(scratch, ref, max_bytes=maximum)
        saved = put_bytes(
            root, data, name=Path(ref.path).name, media_type=ref.media_type, producer=ref.producer
        )
        saved = replace(saved, metadata=ref.metadata)
        if portable and saved != ref:
            raise ValueError("training bundle reference is not portable")
        retained.append(saved)
        return saved

    if training.artifact is not None:
        primary = training.artifact
        bundle_text = primary.metadata.get("training_bundle")
        if bundle_text is not None:
            if not isinstance(bundle_text, str):
                raise ValueError("invalid training bundle reference")
            bundle_ref = ArtifactRef.from_json(bundle_text)
            bundle = TrainingArtifactBundle.from_json(
                read_bytes(scratch, bundle_ref, max_bytes=65536).decode()
            )
            original = replace(
                primary,
                metadata={k: v for k, v in primary.metadata.items() if k != "training_bundle"},
            )
            if (
                bundle.primary != original
                or sum(r.size_bytes for r in bundle.companions) > 4 * 1024 * 1024
            ):
                raise ValueError("training bundle primary or companion size differs")
            saved = capture(original, portable=True)
            for companion in bundle.companions:
                capture(companion, maximum=4 * 1024 * 1024, portable=True)
            capture(bundle_ref, maximum=65536, portable=True)
            saved = replace(saved, metadata=primary.metadata)
        else:
            saved = capture(primary)
        metadata = dict(
            metadata,
            schema_version="2.0",
            worker_training=training.to_dict(),
            training=replace(training, artifact=saved).to_dict(),
        )
        raw = canonical_json(metadata).encode()
    lifecycle = put_bytes(
        root, raw, name="lifecycle.json", media_type="application/json", producer=producer
    )
    return (lifecycle, *retained)
