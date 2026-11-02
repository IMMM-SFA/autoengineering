"""Materialize verified preexisting image inputs, without acquisition or execution.

The build directory contains only reviewed recipe files and exact hash-bound
payloads. A separate proof directory supports cold verification after relocation.
A materialized context does not authorize a build or qualify a runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import stat

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, sync_directory
from examples.utility import guest_image
from examples.utility.inference_environment import verify_inputs

MAX_FILE = 512 * 1024**2
MAX_TOTAL = 8 * 1024**3
CHUNK = 1024**2


def _ref(path, sha256, size):
    return ArtifactRef(path, sha256, size, "application/octet-stream", "guest-image-context", {})


def _stream(root, ref, destination=None):
    """Bounded regular-file verification, optionally copying through the same stream."""
    if ref.size_bytes > MAX_FILE:
        raise ValueError("image context file exceeds its copy envelope")
    path = confined_file(root, ref.path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    output = None
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size != ref.size_bytes:
            raise ValueError("image context input type/size mismatch")
        if destination is not None:
            checked_directory(destination.parent)
            output = destination.open("xb")
            os.fchmod(output.fileno(), 0o600)
        sha = hashlib.sha256()
        remaining = ref.size_bytes
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            while remaining:
                content = stream.read(min(CHUNK, remaining))
                if not content:
                    raise ValueError("image context input truncated during copy")
                remaining -= len(content)
                sha.update(content)
                if output is not None:
                    output.write(content)
            if stream.read(1) or sha.hexdigest() != ref.sha256:
                raise ValueError("image context input digest/size mismatch")
        if output is not None:
            output.flush()
            os.fsync(output.fileno())
    finally:
        if output is not None:
            output.close()
        os.close(descriptor)
    if destination is not None:
        sync_directory(destination.parent)


def _proof_files(plan, inputs):
    paths = [
        "plan.json",
        "environment/manifest.json",
        "environment/review.json",
        "environment/" + inputs.lock.path,
        "environment/" + inputs.wheel.path,
        plan["preparer"]["path"],
    ]
    paths.extend(ref["path"] for ref in plan["recipes"].values())
    return tuple(sorted(set(paths)))


def _payload_sources(plan_root, cache, plan, inputs):
    result = {}
    for item in plan["payloads"]:
        if item["url"] is None:
            source_root, source_path = plan_root / "environment", inputs.wheel.path
        else:
            source_root, source_path = cache, item["path"]
        result["build/" + item["path"]] = (
            source_root,
            _ref(source_path, item["sha256"], item["size_bytes"]),
        )
    return result


def _manifest(plan, refs, materializer):
    return {
        "schema": "utility-guest-image-context-v1",
        "image_plan_digest": digest(plan),
        "files": {name: ref.to_dict() for name, ref in sorted(refs.items())},
        "materializer": materializer.to_dict(),
        "copied_file_bytes": sum(ref.size_bytes for ref in refs.values()),
        "payload_bytes": sum(p["size_bytes"] for p in plan["payloads"]),
        "status": "materialized_inputs_only",
        "build_authorized": False,
        "starts_authorized": False,
        "runtime_qualified": False,
    }


def materialize(plan_root, cache, *, expected_plan_digest, output, fault=None):
    """Copy only existing pinned bytes; failures leave an unreusable partial output."""
    plan_root = checked_directory(plan_root)
    cache = guest_image._public_directory(cache)
    plan = guest_image.verify(plan_root, expected_digest=expected_plan_digest)
    inputs = verify_inputs(
        plan_root / "environment", expected_digest=plan["environment_inputs_digest"]
    )
    output = Path(output).absolute()
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in (plan_root, cache)):
        raise ValueError("image context output overlaps its input scope")
    if output.exists() or output.is_symlink():
        raise ValueError("image context requires an absent output; partial copies cannot resume")
    guest_image._public_directory(output.parent)
    sources = _payload_sources(plan_root, cache, plan, inputs)
    for name, value in plan["recipes"].items():
        ref = ArtifactRef.from_dict(value)
        sources["build/" + name] = (plan_root, ref)
    for name in _proof_files(plan, inputs):
        path = confined_file(plan_root, name)
        limit = 8 * 1024**2
        if path.stat().st_size > limit:
            raise ValueError("image context proof exceeds its metadata envelope")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ValueError("image context proof grew beyond its envelope")
        sources["proof/" + name] = (
            plan_root,
            _ref(name, hashlib.sha256(data).hexdigest(), len(data)),
        )
    if len(sources) > 2048 or sum(ref.size_bytes for _, ref in sources.values()) > MAX_TOTAL:
        raise ValueError("image context exceeds its total copy envelope")
    # Validate every input before creating the output, then validate again while copying.
    for source_root, ref in sources.values():
        _stream(source_root, ref)
    fault = fault or (lambda stage: None)
    fault("context_inputs_verified")
    output.mkdir(mode=0o700)
    refs = {}
    for name, (source_root, ref) in sorted(sources.items()):
        fault("before_context_file")
        parent = output
        for part in Path(name).parts[:-1]:
            parent = parent / part
            parent.mkdir(mode=0o700, exist_ok=True)
            checked_directory(parent)
        _stream(source_root, ref, output / name)
        refs[name] = _ref(name, ref.sha256, ref.size_bytes)
        fault("after_context_file")
    guest_image.verify(output / "proof", expected_digest=expected_plan_digest)
    (output / "artifacts").mkdir(mode=0o700)
    materializer = put_bytes(
        output,
        Path(__file__).read_bytes(),
        name="guest_image_context.py",
        media_type="text/x-python",
        producer="guest-image-context",
    )
    manifest = _manifest(plan, refs, materializer)
    fault("before_context_manifest")
    durable_write(output / "context.json", canonical_json(manifest).encode())
    fault("after_context_manifest")
    return manifest


def verify(root, *, expected_digest):
    """Read exactly the saved closure; no cache, source probe, clock or new action."""
    root = checked_directory(root)
    path = confined_file(root, "context.json")
    if path.stat().st_size > 1024**2:
        raise ValueError("image context manifest exceeds its envelope")
    manifest = unique_json(path.read_text())
    if digest(manifest) != expected_digest:
        raise ValueError("image context differs from its explicit pin")
    plan = guest_image.verify(root / "proof", expected_digest=manifest["image_plan_digest"])
    inputs = verify_inputs(
        root / "proof/environment", expected_digest=plan["environment_inputs_digest"]
    )
    refs = {name: ArtifactRef.from_dict(value) for name, value in manifest["files"].items()}
    expected = {"build/" + p["path"] for p in plan["payloads"]}
    expected.update("build/" + name for name in plan["recipes"])
    expected.update("proof/" + name for name in _proof_files(plan, inputs))
    if set(refs) != expected or len(refs) > 2048:
        raise ValueError("image context file set differs from its pinned closure")
    if sum(ref.size_bytes for ref in refs.values()) > MAX_TOTAL:
        raise ValueError("image context exceeds total byte envelope")
    for name, ref in refs.items():
        if ref != _ref(name, ref.sha256, ref.size_bytes):
            raise ValueError("image context file reference changed path/type/producer")
        _stream(root, ref)
    for name, value in plan["recipes"].items():
        expected_ref = ArtifactRef.from_dict(value)
        observed = refs["build/" + name]
        if (observed.sha256, observed.size_bytes) != (expected_ref.sha256, expected_ref.size_bytes):
            raise ValueError("image context recipe differs from its pinned plan")
    for item in plan["payloads"]:
        ref = refs["build/" + item["path"]]
        if (ref.sha256, ref.size_bytes) != (item["sha256"], item["size_bytes"]):
            raise ValueError("image context payload differs from its pinned plan")
    materializer = ArtifactRef.from_dict(manifest["materializer"])
    read_bytes(root, materializer, max_bytes=1024**2)
    allowed = expected | {materializer.path, "context.json"}
    actual = set()
    expected_dirs = {
        str(parent) for name in allowed for parent in Path(name).parents if str(parent) != "."
    }
    for count, item in enumerate(root.rglob("*"), start=1):
        if count > 4096:
            raise ValueError("image context contains excessive directory entries")
        relative = str(item.relative_to(root))
        if item.is_symlink():
            raise ValueError("image context contains a symlink")
        if item.is_dir():
            if relative not in expected_dirs:
                raise ValueError("image context contains an unreviewed directory")
        elif item.is_file():
            actual.add(relative)
        else:
            raise ValueError("image context contains a nonregular entry")
    if actual != allowed:
        raise ValueError("image context contains unreviewed or missing files")
    if canonical_json(manifest) != canonical_json(_manifest(plan, refs, materializer)):
        raise ValueError("image context differs from its nonexecuting materialization")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("materialize")
    create.add_argument("plan", type=Path)
    create.add_argument("cache", type=Path)
    create.add_argument("output", type=Path)
    create.add_argument("--expected-plan-digest", required=True)
    check = commands.add_parser("verify")
    check.add_argument("context", type=Path)
    check.add_argument("--expected-digest", required=True)
    args = parser.parse_args()
    if args.command == "materialize":
        result = materialize(
            args.plan,
            args.cache,
            expected_plan_digest=args.expected_plan_digest,
            output=args.output,
        )
    else:
        result = verify(args.context, expected_digest=args.expected_digest)
    print(canonical_json({"context_digest": digest(result), "status": result["status"]}))


if __name__ == "__main__":
    main()
