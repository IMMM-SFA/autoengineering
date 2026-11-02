"""Fixture custody checks; no fitting, model run, daemon or guest starts."""

import pytest
import stat
import json
from pathlib import Path
import socket
import subprocess
from dataclasses import replace
from types import SimpleNamespace

from autoengineering.campaign.records import ArtifactRef

from examples.utility import guest_inference_smoke as module
from examples.utility import guest_resources
import test_utility_guest_inputs as input_fixture

metadata = input_fixture.metadata


@pytest.mark.parametrize("role", ["core", "model"])
@pytest.mark.parametrize("damage", ["missing", "digest", "size"])
def test_frozen_code_mismatch_refuses_without_driver_access(role, damage):
    path = "src/autoengineering/utility/report.py" if role == "core" else "examples/model.py"
    ref = ArtifactRef(path, "1" * 64, 20, "text/x-python", "fixture", {})
    installed = replace(ref, path=path.removeprefix("src/"))
    good = SimpleNamespace(wheel_python_sources=(installed,))
    model_sources = (ref,) if role == "model" else ()
    module.verify_fixture_code(good, (ref,), model_sources)
    if damage == "missing":
        refs = ()
    elif damage == "digest":
        refs = (replace(installed, sha256="2" * 64),)
    else:
        refs = (replace(installed, size_bytes=21),)
    with pytest.raises(ValueError, match="wheel code differs"):
        module.verify_fixture_code(
            SimpleNamespace(wheel_python_sources=refs), (ref,), model_sources
        )


def test_snapshot_copies_metadata_without_opening_arrays(tmp_path, monkeypatch):
    source = tmp_path / "original"
    source.mkdir(mode=0o700)
    (source / "suite.json").write_text("{}")
    (source / "private-labels.npz").write_bytes(b"authored canary; never read")
    original = module.raw

    def metadata(root, name):
        if name.endswith(".npz"):
            pytest.fail("snapshot read a label or fitting array")
        return original(root, name)

    monkeypatch.setattr(module, "raw", metadata)
    target = tmp_path / "copy"
    assert module.copy_json_tree(source, target) == 1
    assert (target / "suite.json").read_text() == "{}"
    assert not (target / "private-labels.npz").exists()


def test_snapshot_refuses_symlink_before_creating_output(tmp_path):
    source = tmp_path / "original"
    source.mkdir(mode=0o700)
    (source / "metadata.json").symlink_to(tmp_path / "outside.json")
    target = tmp_path / "copy"
    with pytest.raises(ValueError, match="symlink"):
        module.copy_json_tree(source, target)
    assert not target.exists()


def test_snapshot_total_envelope_refuses_before_output(tmp_path, monkeypatch):
    source = tmp_path / "original"
    source.mkdir(mode=0o700)
    (source / "metadata.json").write_text("{}")
    monkeypatch.setattr(module, "MAX_TOTAL", 1)
    target = tmp_path / "copy"
    with pytest.raises(ValueError, match="envelope"):
        module.copy_json_tree(source, target)
    assert not target.exists()


def test_nested_snapshot_preserves_private_modes_for_every_directory(tmp_path):
    source = tmp_path / "original"
    source.mkdir(mode=0o700)
    nested = source / "children" / "child" / "events"
    nested.mkdir(parents=True)
    (nested / "event.json").write_text("{}")
    target = tmp_path / "copy"
    assert module.copy_json_tree(source, target) == 1
    for path in target.rglob("*"):
        if path.is_dir():
            assert stat.S_IMODE(path.stat().st_mode) == 0o700


def test_preparation_reuses_frozen_state_without_new_process_or_label_copy(
    tmp_path, metadata, monkeypatch
):
    owner, _, source, drivers = input_fixture.prepared(tmp_path / "template", metadata)
    original = metadata[0]
    profile = json.loads(
        (
            Path(__file__).parents[1] / "examples/utility/prepared-guest-resources-v6/request.json"
        ).read_text()
    )["profile"]
    resources = tmp_path / "resource-proof"
    resources.mkdir(mode=0o700)
    module.save(
        resources,
        "request.json",
        {"profile": profile, "endpoint": {"authored": True}, "daemon": {}},
    )
    module.save(resources, "bindings.json", {"endpoint": "/authored/no-socket"})
    monkeypatch.setattr(module.guest_resource_reader, "read_completion", lambda *a, **kw: {})
    monkeypatch.setattr(module.build, "_endpoint", lambda path: {"authored": True})

    def forbidden(*args, **kwargs):
        pytest.fail("preparation started a process or contacted a socket")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    output = tmp_path / "prepared"
    environment = Path(__file__).parents[1] / "examples/utility/prepared-inference-environment-v6"
    request = module.prepare(
        owner.root,
        original.root,
        source,
        drivers,
        resources,
        environment,
        resource_digest="1" * 64,
        output=output,
    )
    assert request["guest"]["image_id"] == guest_resources.CURRENT_IMAGE
    assert request["grant"]["inference"]["forcing"]["prior_exposure"] == "exposed"
    assert request["fitting_starts_allowed"] == request["scoring_starts_allowed"] == 0
    assert not list((output / "suite").rglob("*.npz"))
    assert not list((output / "source").rglob("*.npz"))
    assert not (output / "drivers/private-labels.json").exists()
    assert not (output / "execution-intent.json").exists()
