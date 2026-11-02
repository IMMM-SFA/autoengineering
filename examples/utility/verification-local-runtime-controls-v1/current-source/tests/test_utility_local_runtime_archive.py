"""Relocated raw evidence verification must neither execute nor contact Docker."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    spec = importlib.util.spec_from_file_location(
        "runtime_archive", ROOT / "scripts/verify_utility_local_runtime_archive.py"
    )
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
finally:
    sys.path.pop(0)

ARCHIVE = ROOT / "examples/utility/verification-local-runtime-controls-v1"


def digest(root):
    return hashlib.sha256((root / "execution-files.json").read_bytes()).hexdigest()


@pytest.fixture
def archive(tmp_path):
    root = tmp_path / "relocated"
    root.mkdir()
    shutil.copytree(ARCHIVE / "executions", root / "executions")
    shutil.copyfile(ARCHIVE / "execution-files.json", root / "execution-files.json")
    return root


def mutate(root, member, change):
    path = root / "executions" / member
    value = json.loads(path.read_bytes())
    change(value)
    path.write_text(json.dumps(value))
    manifest_path = root / "execution-files.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest[member] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def test_relocated_evidence_without_any_execution_or_socket(archive, monkeypatch):
    import socket
    import subprocess

    def denied(*args, **kwargs):
        pytest.fail("offline reader attempted a socket or process start")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    result = reader.verify(archive, digest(archive))
    assert len(result["controls"]) == 4
    assert result["private_scoring_qualified"] is False
    assert result["live_container_absence_checked"] is False


def test_manifest_requires_separately_retained_digest(archive):
    with pytest.raises(reader.Refused, match="manifest digest"):
        reader.verify(archive, "0" * 64)


@pytest.mark.parametrize(
    "member,change",
    [
        ("score/score/cleanup.json", lambda v: v.update(container_id="a" * 64)),
        ("score/score/cleanup.json", lambda v: v.update(removed=False)),
        ("score/score/plan.json", lambda v: v.update(controller_sha256="0" * 64)),
        ("score/score/final-inspect.json", lambda v: v.update(RestartCount=1)),
        ("score/score/final-inspect.json", lambda v: v["State"].update(Running=True)),
        ("score/score/final-inspect.json", lambda v: v["HostConfig"].update(NetworkMode="host")),
        (
            "memory-overrun/memory-overrun/final-inspect.json",
            lambda v: v["State"].update(OOMKilled=False),
        ),
        ("score/score/result.json", lambda v: v["result"].update(qualified=True)),
    ],
)
def test_rehashed_corrupt_evidence_is_not_accepted(archive, member, change):
    mutate(archive, member, change)
    with pytest.raises(reader.Refused):
        reader.verify(archive, digest(archive))


def test_changed_archived_code_is_only_hashed(archive):
    path = archive / "executions/score/controller.py"
    path.chmod(0o600)
    path.write_text("raise RuntimeError('must never execute archived code')")
    with pytest.raises(reader.Refused, match="member digest"):
        reader.verify(archive, digest(archive))


@pytest.mark.parametrize("kind", ["symlink", "fifo", "oversized"])
def test_nonregular_or_unbounded_members_refused(archive, kind):
    import os

    path = archive / "executions/score/controller.py"
    path.unlink()
    if kind == "symlink":
        path.symlink_to(ROOT / "scripts/qualify_utility_local_runtime.py")
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.write_bytes(b"x" * (reader.LIMIT + 1))
    with pytest.raises((reader.Refused, OSError)):
        reader.verify(archive, digest(archive))
