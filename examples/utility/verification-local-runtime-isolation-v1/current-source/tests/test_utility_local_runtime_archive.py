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
LIFECYCLE = ROOT / "examples/utility/verification-local-runtime-lifecycle-v1"
ISOLATION = ROOT / "examples/utility/verification-local-runtime-isolation-v1"


def digest(root):
    return hashlib.sha256((root / "execution-files.json").read_bytes()).hexdigest()


@pytest.fixture
def archive(tmp_path):
    root = tmp_path / "relocated"
    root.mkdir()
    shutil.copytree(ARCHIVE / "executions", root / "executions")
    shutil.copyfile(ARCHIVE / "execution-files.json", root / "execution-files.json")
    return root


@pytest.fixture
def lifecycle(tmp_path):
    root = tmp_path / "relocated-lifecycle"
    root.mkdir()
    shutil.copytree(LIFECYCLE / "executions", root / "executions")
    shutil.copyfile(LIFECYCLE / "execution-files.json", root / "execution-files.json")
    return root


@pytest.fixture
def isolation(tmp_path):
    root = tmp_path / "relocated-isolation"
    root.mkdir()
    shutil.copytree(ISOLATION / "executions", root / "executions")
    shutil.copyfile(ISOLATION / "execution-files.json", root / "execution-files.json")
    return root


def test_isolation_reconstruction_without_socket_or_execution(isolation, monkeypatch):
    import socket
    import subprocess

    def denied(*args, **kwargs):
        pytest.fail("offline isolation reader attempted execution or Docker access")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    result = reader.verify(isolation, digest(isolation), modes=("isolation",))
    assert result["verified_files"] == 25
    assert result["private_scoring_qualified"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("mounted_public_canary_read", False),
        ("unmounted_host_canary_read", True),
        ("parent_traversal_canary_read", True),
        ("root_and_stage_write", True),
        ("loopback_positive_control", False),
        ("documentation_address_errno", 110),
    ],
)
def test_isolation_rehashed_changed_positive_or_negative_refuses(isolation, field, value):
    mutate(isolation, "isolation/isolation/stdout.bin", lambda v: v.update({field: value}))
    mutate(
        isolation, "isolation/isolation/result.json", lambda v: v["result"].update({field: value})
    )
    with pytest.raises(reader.Refused, match="isolation positive/negative"):
        reader.verify(isolation, digest(isolation), modes=("isolation",))


def test_missing_unrestricted_host_positive_control_refuses(isolation):
    mutate(
        isolation,
        "isolation/isolation/host-positive-control.json",
        lambda v: v.update(read_succeeded=False),
    )
    with pytest.raises(reader.Refused, match="host positive"):
        reader.verify(isolation, digest(isolation), modes=("isolation",))


def test_lifecycle_reconstruction_without_socket_or_execution(lifecycle, monkeypatch):
    import socket
    import subprocess

    def denied(*args, **kwargs):
        pytest.fail("offline lifecycle reader attempted execution or Docker access")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    result = reader.verify_lifecycle(lifecycle, digest(lifecycle))
    assert len(result["controls"]) == 4
    assert result["verified_files"] == 88
    assert result["live_container_absence_checked"] is False
    assert result["private_scoring_qualified"] is False


@pytest.mark.parametrize(
    "member,change",
    [
        ("owner-loss/owner-exit.json", lambda v: v.update(returncode=0)),
        ("owner-loss/owner-exit.json", lambda v: v.update(owner_pid=1)),
        ("deadline/hold/cleanup.json", lambda v: v.update(reason="owner_pipe_eof")),
        ("deadline/hold/cleanup-before.json", lambda v: v["State"].update(Running=False)),
        ("cancellation/hold/fault-reconciled.json", lambda v: v.update(start_retries=1)),
        (
            "cancellation/hold/fault-reconciled.json",
            lambda v: v.update(private_scoring_qualified=True),
        ),
        (
            "lost-start-ack/hold/fault-intent.json",
            lambda v: v.update(start_response_delivered_to_controller=True),
        ),
        ("owner-loss/hold/fault-witness.json", lambda v: v.update(nonce="0" * 32)),
    ],
)
def test_lifecycle_rehashed_corruption_is_refused(lifecycle, member, change):
    mutate(lifecycle, member, change)
    with pytest.raises(reader.Refused):
        reader.verify_lifecycle(lifecycle, digest(lifecycle))


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
