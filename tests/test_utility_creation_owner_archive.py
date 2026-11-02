"""Relocated owner-control evidence checks; no process/daemon execution."""

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
        "creation_owner_reader", ROOT / "scripts/verify_utility_creation_owner_archive.py"
    )
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
finally:
    sys.path.pop(0)
ARCHIVE = ROOT / "examples/utility/verification-container-creation-owner-v1"


@pytest.fixture
def archive(tmp_path):
    root = tmp_path / "relocated"
    root.mkdir()
    shutil.copytree(ARCHIVE / "executions", root / "executions")
    shutil.copyfile(ARCHIVE / "execution-files.json", root / "execution-files.json")
    return root


def digest(root):
    return hashlib.sha256((root / "execution-files.json").read_bytes()).hexdigest()


def mutate(root, member, change):
    path = root / "executions" / member
    value = json.loads(path.read_bytes())
    change(value)
    path.write_text(json.dumps(value))
    manifest_path = root / "execution-files.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest[member] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def test_relocated_verification_with_execution_and_socket_forbidden(archive, monkeypatch):
    import socket
    import subprocess

    def denied(*_a, **_k):
        pytest.fail("offline reader attempted execution or socket")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(reader.policy.API, "request", denied)
    result = reader.verify(archive, digest(archive))
    assert len(result["controls"]) == 6 and result["verified_files"] == 120
    assert result["container_starts"] == result["scoring_starts"] == 0
    assert result["private_scoring_qualified"] is False
    assert result["live_absence_checked_now"] is False


@pytest.mark.parametrize(
    "member,change",
    [
        ("before-ack-owner-loss/control-result.json", lambda v: v.update(owner_exit=0)),
        ("before-pipe-cancel/owner-termination-intent.json", lambda v: v.update(pid=1)),
        (
            "before-ack-cancel/container/creation-pending.json",
            lambda v: v.update(runtime_identity="0" * 64),
        ),
        (
            "before-pipe-owner-loss/container/cleanup.json",
            lambda v: v.update(container_id="0" * 64),
        ),
        ("before-ack-owner-loss/container/cleanup.json", lambda v: v.update(removed=False)),
        ("after-arm-cancel/container/watchdog-ready.json", lambda v: v.update(nonce="0" * 32)),
        (
            "after-arm-owner-loss/container/cleanup.json",
            lambda v: v.update(reason="parent_reconciliation"),
        ),
        (
            "after-arm-owner-loss/container/cleanup-before.json",
            lambda v: v["State"].update(Status="exited"),
        ),
    ],
)
def test_rehashed_corrupt_owner_evidence_is_refused(archive, member, change):
    mutate(archive, member, change)
    with pytest.raises(ValueError):
        reader.verify(archive, digest(archive))


def test_manifest_needs_separately_retained_digest(archive):
    with pytest.raises(ValueError, match="manifest digest differs"):
        reader.verify(archive, "0" * 64)


def test_archived_code_is_hashed_and_never_executed(archive):
    path = archive / "executions/before-ack-cancel/container/runtime.py"
    path.chmod(0o600)
    path.write_text("raise AssertionError('archived code must never execute')")
    with pytest.raises(ValueError, match="member digest differs"):
        reader.verify(archive, digest(archive))


def test_job_or_label_member_is_refused_before_open(archive, monkeypatch):
    path = archive / "execution-files.json"
    manifest = json.loads(path.read_bytes())
    manifest["before-ack-cancel/container/stage/labels.json"] = "0" * 64
    path.write_text(json.dumps(manifest))
    original = reader.read

    def metadata_only(root, relative):
        if Path(relative).name == "labels.json":
            pytest.fail("reader opened label member")
        return original(root, relative)

    monkeypatch.setattr(reader, "read", metadata_only)
    with pytest.raises(ValueError, match="metadata only"):
        reader.verify(archive, digest(archive))
