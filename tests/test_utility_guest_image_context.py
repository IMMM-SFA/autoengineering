"""Authored payload copying only; no real packages, image builds or daemon calls."""

import hashlib
from pathlib import PurePosixPath
import shutil
import socket
import subprocess
import time
import zipfile

import pytest
import yaml

from autoengineering.campaign.serialization import canonical_json, digest
from examples.utility import guest_image, guest_image_context as module
from examples.utility.inference_environment import prepare_inputs
import test_utility_inference_environment as fixture


def prepared(tmp_path, monkeypatch):
    fixture.inputs(tmp_path)
    cache = tmp_path / "cache"
    cache.mkdir(mode=0o700)
    (cache / "archives").mkdir()
    (cache / "installer").mkdir()
    lock_path = tmp_path / "pixi.lock"
    lock = yaml.safe_load(lock_path.read_text())
    for package in lock["packages"]:
        if "conda" not in package:
            continue
        name = PurePosixPath(package["conda"]).name
        content = (name.encode() * 100)[:100]
        package["sha256"] = hashlib.sha256(content).hexdigest()
        package["size"] = len(content)
        (cache / "archives" / name).write_bytes(content)
    lock_path.write_text(yaml.safe_dump(lock))
    source = tmp_path / "source"
    source.mkdir()
    with zipfile.ZipFile(tmp_path / "autoengineering-0.2.0-py3-none-any.whl") as archive:
        for name in archive.namelist():
            if name.endswith(".py"):
                path = source / "src" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(archive.read(name))
    installer = b"AUTHORED-INSTALLER-BYTES-NOT-EXECUTABLE"
    profile = dict(
        guest_image.INSTALLER,
        sha256=hashlib.sha256(installer).hexdigest(),
        size_bytes=len(installer),
    )
    monkeypatch.setattr(guest_image, "INSTALLER", profile)
    (cache / "installer" / profile["filename"]).write_bytes(installer)
    environment = tmp_path / "environment"
    inputs = prepare_inputs(tmp_path, output=environment, **fixture.refs(tmp_path))
    plan_root = tmp_path / "plan"
    plan = guest_image.prepare(
        environment, expected_digest=inputs.digest, source_root=source, output=plan_root
    )
    return plan_root, plan, cache


def test_only_reviewed_existing_payloads_are_copied_and_verified(tmp_path, monkeypatch):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    (cache / "private-canary.txt").write_text("DO-NOT-COPY")

    def forbidden(*args, **kwargs):
        raise AssertionError("context materialization tried acquisition, execution or extraction")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    monkeypatch.setattr(module, "CHUNK", 7)
    output = tmp_path / "context"
    manifest = module.materialize(
        plan_root, cache, expected_plan_digest=digest(plan), output=output
    )
    assert module.verify(output, expected_digest=digest(manifest)) == manifest
    assert manifest["payload_bytes"] == sum(p["size_bytes"] for p in plan["payloads"])
    assert manifest["status"] == "materialized_inputs_only"
    assert not any(
        manifest[k] for k in ("build_authorized", "starts_authorized", "runtime_qualified")
    )
    assert not list(output.rglob("private-canary.txt"))
    # The fixture cache also holds pytest, outside the selected dependency closure.
    assert not list((output / "build").rglob("pytest-*"))
    assert (output / "build/Dockerfile").is_file()
    assert (output / "build/.dockerignore").is_file()
    assert all(p.stat().st_mode & 0o077 == 0 for p in output.rglob("*"))
    for item in plan["payloads"]:
        data = (output / "build" / item["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item["sha256"]
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="absent output"):
        module.materialize(plan_root, cache, expected_plan_digest=digest(plan), output=output)
    assert {
        p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()
    } == before


@pytest.mark.parametrize("problem", ["missing", "size", "digest", "symlink", "directory"])
def test_bad_cache_refuses_before_output_creation(tmp_path, monkeypatch, problem):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    item = next(p for p in plan["payloads"] if p["url"] is not None)
    path = cache / item["path"]
    original = path.read_bytes()
    if problem == "missing":
        path.unlink()
    elif problem == "size":
        path.write_bytes(original + b"X")
    elif problem == "digest":
        path.write_bytes(b"X" * len(original))
    else:
        path.unlink()
        if problem == "symlink":
            outside = tmp_path / "outside"
            outside.write_bytes(original)
            path.symlink_to(outside)
        else:
            path.mkdir()
    output = tmp_path / "context"
    with pytest.raises(ValueError):
        module.materialize(plan_root, cache, expected_plan_digest=digest(plan), output=output)
    assert not output.exists()


@pytest.mark.parametrize("stage", ["after_context_file", "before_context_manifest"])
def test_interrupted_copy_cannot_be_reused_as_a_fresh_attempt(tmp_path, monkeypatch, stage):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    output = tmp_path / "context"

    def fail(point):
        if point == stage:
            raise KeyboardInterrupt("authored copy interruption")

    with pytest.raises(KeyboardInterrupt):
        module.materialize(
            plan_root, cache, expected_plan_digest=digest(plan), output=output, fault=fail
        )
    assert output.exists() and not (output / "context.json").exists()
    with pytest.raises(ValueError):
        module.verify(output, expected_digest="a" * 64)
    with pytest.raises(ValueError, match="partial copies cannot resume"):
        module.materialize(plan_root, cache, expected_plan_digest=digest(plan), output=output)


def test_cache_mutation_between_validation_and_copy_leaves_uncommitted_output(
    tmp_path, monkeypatch
):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    output = tmp_path / "context"
    item = next(p for p in plan["payloads"] if p["url"] is not None)

    def change(stage):
        if stage == "context_inputs_verified":
            (cache / item["path"]).write_bytes(b"X" * item["size_bytes"])

    with pytest.raises(ValueError, match="digest/size"):
        module.materialize(
            plan_root, cache, expected_plan_digest=digest(plan), output=output, fault=change
        )
    assert not (output / "context.json").exists()


@pytest.mark.parametrize("problem", ["payload", "recipe", "proof", "extra", "empty_dir", "symlink"])
def test_changed_or_extra_context_bytes_cannot_verify(tmp_path, monkeypatch, problem):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    output = tmp_path / "context"
    manifest = module.materialize(
        plan_root, cache, expected_plan_digest=digest(plan), output=output
    )
    pin = digest(manifest)
    if problem == "payload":
        (output / "build" / plan["payloads"][0]["path"]).write_bytes(b"corrupt")
    elif problem == "recipe":
        (output / "build/Dockerfile").write_bytes(b"corrupt")
    elif problem == "proof":
        (output / "proof/plan.json").write_text("{}")
    elif problem == "extra":
        (output / "build/private-labels.json").write_text("PRIVATE-CANARY")
    elif problem == "empty_dir":
        (output / "build/unreviewed").mkdir()
    else:
        (output / "unreviewed").symlink_to(cache, target_is_directory=True)
    with pytest.raises(ValueError):
        module.verify(output, expected_digest=pin)


def test_saved_context_relocates_without_cache_sources_execution_or_clock(tmp_path, monkeypatch):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    output = tmp_path / "context"
    manifest = module.materialize(
        plan_root, cache, expected_plan_digest=digest(plan), output=output
    )
    relocated = tmp_path / "relocated"
    shutil.copytree(output, relocated)
    for path in (output, cache, plan_root, tmp_path / "source", tmp_path / "environment"):
        shutil.rmtree(path)

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "cold verification tried execution, acquisition, source probe or clock"
        )

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(guest_image, "_source_alignment", forbidden)
    assert module.verify(relocated, expected_digest=digest(manifest)) == manifest


def test_repinning_cannot_promote_materialization_to_authority(tmp_path, monkeypatch):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    output = tmp_path / "context"
    manifest = module.materialize(
        plan_root, cache, expected_plan_digest=digest(plan), output=output
    )
    manifest["build_authorized"] = True
    (output / "context.json").write_text(canonical_json(manifest))
    with pytest.raises(ValueError, match="nonexecuting materialization"):
        module.verify(output, expected_digest=digest(manifest))


@pytest.mark.parametrize("scope", ["cache", "plan"])
def test_output_cannot_overlap_inputs(tmp_path, monkeypatch, scope):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    output = (cache if scope == "cache" else plan_root) / "context"
    with pytest.raises(ValueError, match="overlaps"):
        module.materialize(plan_root, cache, expected_plan_digest=digest(plan), output=output)
    assert not output.exists()


@pytest.mark.parametrize("cap", ["MAX_TOTAL", "MAX_FILE"])
def test_copy_envelope_refuses_before_output_creation(tmp_path, monkeypatch, cap):
    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    monkeypatch.setattr(module, cap, 1)
    output = tmp_path / "context"
    with pytest.raises(ValueError, match="envelope"):
        module.materialize(plan_root, cache, expected_plan_digest=digest(plan), output=output)
    assert not output.exists()


def test_guarded_cold_reader_opens_only_relocated_saved_closure(tmp_path, monkeypatch):
    import os
    import sys
    from pathlib import Path

    plan_root, plan, cache = prepared(tmp_path, monkeypatch)
    output = tmp_path / "context"
    manifest = module.materialize(
        plan_root, cache, expected_plan_digest=digest(plan), output=output
    )
    pin = digest(manifest)
    relocated = tmp_path / "relocated"
    shutil.copytree(output, relocated)
    for path in (output, cache, plan_root, tmp_path / "source", tmp_path / "environment"):
        shutil.rmtree(path)

    def forbidden(*args, **kwargs):
        raise AssertionError("cold reader used execution, acquisition, clock or source probe")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(guest_image, "_source_alignment", forbidden)
    active = [True]

    def guard(event, args):
        if not active[0] or event != "open" or isinstance(args[0], int):
            return
        path = Path(args[0]).resolve()
        mode, flags = args[1:3]
        assert path.is_relative_to(relocated), "original/private or unrelated file read"
        assert mode is None or not any(c in mode for c in "wax+"), "write"
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND), (
            "write"
        )

    sys.addaudithook(guard)
    try:
        assert module.verify(relocated, expected_digest=pin) == manifest
    finally:
        active[0] = False
