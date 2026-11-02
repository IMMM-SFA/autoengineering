"""Offline candidate image recipes, with no acquisition or image execution."""

import hashlib
import io
import shutil
import socket
import subprocess
import time
import zipfile

import pytest

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest
from examples.utility import guest_image as module
from examples.utility.inference_environment import prepare_inputs
import test_utility_inference_environment as fixture


def prepared(tmp_path):
    _, arguments = fixture.inputs(tmp_path)
    wheel = tmp_path / "autoengineering-0.2.0-py3-none-any.whl"
    source = tmp_path / "source"
    source.mkdir(mode=0o755)
    with zipfile.ZipFile(io.BytesIO(wheel.read_bytes())) as archive:
        for name in archive.namelist():
            if name.endswith(".py"):
                target = source / "src" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
    environment = tmp_path / "environment"
    inputs = prepare_inputs(tmp_path, output=environment, **arguments)
    return environment, inputs, source


def test_recipe_is_offline_pinned_and_does_not_overwrite(tmp_path, monkeypatch):
    environment, inputs, source = prepared(tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("preparation performed acquisition, execution or extraction")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(zipfile.ZipFile, "extractall", forbidden)
    output = tmp_path / "image"
    plan = module.prepare(
        environment, expected_digest=inputs.digest, source_root=source, output=output
    )
    assert module.verify(output, expected_digest=digest(plan)) == plan
    assert plan["base"]["platform"] == "linux/amd64"
    assert plan["remote_payload_bytes"] == 800 + 6988090 + 45269741
    assert len(plan["payloads"]) == 10  # Eight fixture packages, installer and local wheel.
    assert all(
        plan[key] is False
        for key in (
            "acquisition_authorized",
            "build_authorized",
            "starts_authorized",
            "runtime_qualified",
        )
    )
    dockerfile = read_bytes(output, ArtifactRef.from_dict(plan["recipes"]["Dockerfile"])).decode()
    assert "@sha256:" in dockerfile and "--no-index --no-deps" in dockerfile
    assert "USER 1000:1000" in dockerfile and "ENTRYPOINT []" in dockerfile
    assert "apt-get" not in dockerfile and "curl" not in dockerfile
    explicit = read_bytes(output, ArtifactRef.from_dict(plan["recipes"]["explicit.txt"])).decode()
    assert explicit.startswith("@EXPLICIT\n") and explicit.count("#sha256:") == 8
    assert all(line.startswith("file:///build/") for line in explicit.splitlines()[1:])
    before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
    with pytest.raises(ValueError, match="absent output"):
        module.prepare(
            environment, expected_digest=inputs.digest, source_root=source, output=output
        )
    assert {
        p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()
    } == before


@pytest.mark.parametrize("change", ["changed", "missing", "extra", "symlink"])
def test_stale_or_unsafe_sources_refuse_before_output(tmp_path, change):
    environment, inputs, source = prepared(tmp_path)
    file = source / "src/autoengineering/utility/inference_worker.py"
    if change == "changed":
        file.write_bytes(b"changed source")
    elif change == "missing":
        file.unlink()
    elif change == "extra":
        (file.parent / "new_module.py").write_text("pass")
    else:
        original = file.read_bytes()
        file.unlink()
        destination = tmp_path / "outside.py"
        destination.write_bytes(original)
        file.symlink_to(destination)
    output = tmp_path / "image"
    with pytest.raises(ValueError):
        module.prepare(
            environment, expected_digest=inputs.digest, source_root=source, output=output
        )
    assert not output.exists()


@pytest.mark.parametrize("change", ["recipe", "wheel", "preparer", "plan"])
def test_modified_saved_package_refuses_cold_verification(tmp_path, change):
    environment, inputs, source = prepared(tmp_path)
    output = tmp_path / "image"
    plan = module.prepare(
        environment, expected_digest=inputs.digest, source_root=source, output=output
    )
    pin = digest(plan)
    ref = {"recipe": plan["recipes"]["Dockerfile"], "preparer": plan["preparer"]}.get(change)
    if ref:
        (output / ref["path"]).write_bytes(b"corrupt")
    elif change == "wheel":
        (output / "environment" / inputs.wheel.path).write_bytes(b"corrupt")
    else:
        (output / "plan.json").write_text("{}")
    with pytest.raises(ValueError):
        module.verify(output, expected_digest=pin)


def test_cold_relocated_plan_needs_only_saved_bytes(tmp_path, monkeypatch):
    environment, inputs, source = prepared(tmp_path)
    output = tmp_path / "image"
    plan = module.prepare(
        environment, expected_digest=inputs.digest, source_root=source, output=output
    )
    relocated = tmp_path / "relocated"
    shutil.copytree(output, relocated)
    shutil.rmtree(output)
    shutil.rmtree(environment)
    shutil.rmtree(source)

    def forbidden(*args, **kwargs):
        raise AssertionError("cold reader probed source, clock, network or execution")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(module, "_source_alignment", forbidden)
    assert module.verify(relocated, expected_digest=digest(plan)) == plan
    assert (
        hashlib.sha256((relocated / plan["preparer"]["path"]).read_bytes()).hexdigest()
        == plan["preparer"]["sha256"]
    )


def test_repinning_does_not_turn_recipe_into_authority(tmp_path):
    from autoengineering.campaign.serialization import canonical_json

    environment, inputs, source = prepared(tmp_path)
    output = tmp_path / "image"
    plan = module.prepare(
        environment, expected_digest=inputs.digest, source_root=source, output=output
    )
    plan["build_authorized"] = True
    (output / "plan.json").write_text(canonical_json(plan))
    with pytest.raises(ValueError, match="nonexecuting recipe"):
        module.verify(output, expected_digest=digest(plan))


def test_output_parent_symlink_is_refused_before_writing(tmp_path):
    environment, inputs, source = prepared(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        module.prepare(
            environment, expected_digest=inputs.digest, source_root=source, output=alias / "image"
        )
    assert not (tmp_path / "image").exists()
