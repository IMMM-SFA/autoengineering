"""Offline consistency checks of running-container fault evidence."""

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
        "running_archive_reader", ROOT / "scripts/verify_utility_running_archive.py"
    )
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
finally:
    sys.path.pop(0)
ARCHIVE = ROOT / "examples/utility/verification-container-running-v1"


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


def test_running_archive_relocates_without_daemon_or_process(archive, monkeypatch):
    import socket
    import subprocess

    def denied(*_a, **_k):
        pytest.fail("offline reader attempted network or execution")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(reader.policy.API, "request", denied)
    result = reader.verify(archive, digest(archive))
    assert result["verified_files"] == 90 and result["container_starts"] == 4
    assert result["scoring_child_starts"] is None
    assert result["accepted_scientific_results"] == 0
    assert result["private_scoring_qualified"] is False


@pytest.mark.parametrize(
    "member,change",
    [
        ("cancel/control-result.json", lambda v: v.update(owner_exit=0)),
        ("owner-loss/running-fault-intent.json", lambda v: v.update(owner_pid=1)),
        (
            "lost-start-ack/running-fault-intent.json",
            lambda v: v.update(transport_start_status=500),
        ),
        ("deadline/container/cleanup.json", lambda v: v.update(reason="owner_pipe_eof")),
        ("cancel/container/cleanup-before.json", lambda v: v["State"].update(Running=False)),
        ("cancel/paused-running.json", lambda v: v["State"].update(Paused=False)),
        ("owner-loss/control-result.json", lambda v: v.update(replacement_attempts=1)),
        ("lost-start-ack/control-result.json", lambda v: v.update(scoring_child_starts=1)),
        ("deadline/control-result.json", lambda v: v.update(accepted_scientific_result=True)),
    ],
)
def test_rehashed_false_interruption_claims_are_rejected(archive, member, change):
    mutate(archive, member, change)
    with pytest.raises(ValueError):
        reader.verify(archive, digest(archive))


def test_running_manifest_requires_retained_digest(archive):
    with pytest.raises(ValueError, match="manifest digest differs"):
        reader.verify(archive, "0" * 64)


@pytest.fixture
def timeout_archive(tmp_path):
    root = tmp_path / "timeout-relocated"
    source = ARCHIVE / "execution-timeout"
    shutil.copytree(source / "executions", root / "executions")
    shutil.copyfile(source / "execution-files.json", root / "execution-files.json")
    return root


def test_execution_timeout_relocates_without_daemon_or_process(timeout_archive, monkeypatch):
    import socket
    import subprocess

    def denied(*_a, **_k):
        pytest.fail("timeout reader attempted network or execution")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(reader.policy.API, "request", denied)
    result = reader.verify(timeout_archive, digest(timeout_archive), execution_timeout_only=True)
    assert result["verified_files"] == 23
    assert result["container_starts"] == 1
    assert result["controls"][0]["cleanup_reason"] == "owner_pipe_eof"
    assert result["scoring_child_starts"] is None
    assert result["accepted_scientific_results"] == 0


@pytest.mark.parametrize(
    "member,change",
    [
        ("container/cleanup.json", lambda v: v.update(reason="deadline")),
        ("expected-controller-refusal.json", lambda v: v.update(type="TimeoutError")),
        ("control-result.json", lambda v: v.update(accepted_scientific_result=True)),
    ],
)
def test_execution_timeout_false_claims_are_rejected(timeout_archive, member, change):
    mutate(timeout_archive, "runtime-timeout/" + member, change)
    with pytest.raises(ValueError):
        reader.verify(timeout_archive, digest(timeout_archive), execution_timeout_only=True)
