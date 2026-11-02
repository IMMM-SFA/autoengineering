"""Offline recovery requires the original complete creation and lifecycle chain."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from autoengineering.utility import private_container_runtime as module
from test_utility_private_container_runtime import H, saved


@pytest.mark.parametrize(
    "name,change",
    [
        ("creation-pending.json", lambda v: v.update(nonce="c" * 32)),
        ("creation-pending.json", lambda v: v.update(api_version="1.52")),
        ("create-intent.json", lambda v: v["HostConfig"].update(NetworkMode="host")),
        ("plan.json", lambda v: v.update(socket_path="/different.sock")),
        ("before-start.json", lambda v: v["State"].update(Status="exited")),
        ("before-start.json", lambda v: v["State"].update(Running=True)),
        ("before-start.json", lambda v: v["State"].update(Paused=True)),
        ("before-start.json", lambda v: v.update(RestartCount=1)),
        ("before-start.json", lambda v: v.update(RestartCount=False)),
        ("final-inspect.json", lambda v: v["State"].update(Status="created")),
        ("final-inspect.json", lambda v: v["State"].update(Running=0)),
        ("final-inspect.json", lambda v: v["State"].update(Paused=True)),
        ("final-inspect.json", lambda v: v["State"].update(ExitCode=False)),
        ("final-inspect.json", lambda v: v["State"].update(OOMKilled=0)),
        ("final-inspect.json", lambda v: v.update(RestartCount=False)),
        ("watchdog-ready.json", lambda v: v.update(watchdog_pid=False)),
        ("stage-hashes.json", lambda v: v.update({"private_score_worker.py": "0" * 64})),
        ("result.json", lambda v: v.update(lifecycle_seconds=-1)),
        ("result.json", lambda v: v.update(lifecycle_seconds=True)),
        ("result.json", lambda v: v.update(lifecycle_seconds=None)),
        ("result.json", lambda v: v["result"].update(child_exit_code=False)),
        ("result.json", lambda v: v.update(unapproved="private detail")),
        ("start-intent.json", lambda v: v.update(unapproved=True)),
        ("cleanup.json", lambda v: v.update(reason="unknown")),
    ],
)
def test_conflicting_chain_never_recovers_or_queries_daemon(tmp_path, monkeypatch, name, change):
    runtime, folder, job_sha = saved(tmp_path)
    path = folder / name
    value = json.loads(path.read_bytes())
    change(value)
    path.write_text(json.dumps(value))
    monkeypatch.setattr(module.API, "request", lambda *_a, **_k: pytest.fail("used daemon"))
    with pytest.raises(module.Refused):
        runtime.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)


@pytest.mark.parametrize("name", ["creation-pending.json", "create-intent.json"])
def test_missing_original_creation_evidence_is_not_a_completed_score(tmp_path, name):
    runtime, folder, job_sha = saved(tmp_path)
    (folder / name).unlink()
    with pytest.raises(module.Refused):
        runtime.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)


@pytest.mark.parametrize("relative", ["container", "container/stage"])
def test_recovery_rejects_symlinked_evidence_directories(tmp_path, relative):
    runtime, _, job_sha = saved(tmp_path)
    path = tmp_path / relative
    target = path.with_name(path.name + "-original")
    path.rename(target)
    path.symlink_to(target, target_is_directory=True)
    with pytest.raises(module.Refused):
        runtime.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)


def test_recovery_remains_relocatable_and_uses_no_private_arrays(tmp_path, monkeypatch):
    runtime, folder, job_sha = saved(tmp_path)
    relocated = tmp_path / "relocated"
    shutil.copytree(folder, relocated / "container")
    original_read = module.read_regular

    def read(path, limit):
        assert Path(path).is_relative_to(relocated)
        assert Path(path).name != "labels.json"
        return original_read(path, limit)

    monkeypatch.setattr(module, "read_regular", read)
    monkeypatch.setattr(module.API, "request", lambda *_a, **_k: pytest.fail("used daemon"))
    assert runtime.recover(relocated, job_sha256=job_sha, labels_sha256=H)["value"] == 1.0
