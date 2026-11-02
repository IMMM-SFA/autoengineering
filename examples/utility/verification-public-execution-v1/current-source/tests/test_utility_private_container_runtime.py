"""Runtime evidence checks using authored fixtures, without daemon execution."""

import copy
import json
from pathlib import Path

import pytest

from autoengineering.utility import private_container_runtime as module

H = "1" * 64


def runtime():
    return module.FixedScorerRuntime(Path("/private/tmp/owned-synthetic.sock"), server_sha256=H)


@pytest.mark.parametrize("bad", ["http://example.invalid", "relative.sock"])
def test_only_explicit_local_unix_paths_are_accepted(bad):
    with pytest.raises(module.Refused):
        module.API(bad)


def test_stage_binding_mismatch_refuses_before_daemon_mutation(tmp_path, monkeypatch):
    candidate = runtime()
    tmp_path.chmod(0o700)
    work = tmp_path / "workspace"
    work.mkdir(mode=0o700)
    (work / "job.json").write_bytes(b"{}")
    (work / "labels.json").write_bytes(b"{}")
    monkeypatch.setattr(
        module.API, "request", lambda *_a, **_k: pytest.fail("must not call daemon")
    )
    with pytest.raises(module.Refused, match="durable access intent"):
        candidate.run(tmp_path, api_version="1.53", job_sha256=H, labels_sha256=H)


def saved(tmp_path):
    candidate = runtime()
    folder = tmp_path / "container"
    stage = folder / "stage"
    stage.mkdir(parents=True)
    (stage / "job.json").write_bytes(b"{}")
    for name, raw in (
        ("private_score_worker.py", candidate.worker_bytes),
        ("private_container_worker.py", candidate.wrapper_bytes),
    ):
        (stage / name).write_bytes(raw)
    (folder / "runtime.py").write_bytes(candidate.runtime_bytes)
    job_sha = module.sha(b"{}")
    plan = {
        "mode": "score",
        "stage": str(stage),
        "container_id": "a" * 64,
        "nonce": "b" * 32,
        "runtime_identity": candidate.identity,
        "runtime_sha256": module.sha(candidate.runtime_bytes),
        "job_sha256": job_sha,
        "labels_sha256": H,
    }
    config = module.configuration(plan["nonce"], "score", stage)
    before = {
        "Id": plan["container_id"],
        "Image": module.IMAGE,
        "Name": "/ae-private-rmse-" + plan["nonce"],
        "Config": config,
        "HostConfig": copy.deepcopy(config["HostConfig"]),
        "Mounts": [
            {"Type": "bind", "Source": str(stage), "Destination": "/qualification", "RW": False}
        ],
        "State": {"Running": False, "Status": "created"},
        "RestartCount": 0,
    }
    final = copy.deepcopy(before)
    final["State"] = {"Running": False, "Status": "exited", "ExitCode": 0, "OOMKilled": False}
    capture = {
        "schema": "private-container-output-v1",
        "mode": "score",
        "output_limited": False,
        "child_exit_code": 0,
        "child_signal": None,
        "output_limit_bytes": 16384,
        "captured_bytes": 78,
        "private_scoring_qualified": False,
        "score": {
            "status": "success",
            "outcome": "rmse",
            "units": "W",
            "value": 1.0,
            "feasible": True,
        },
    }
    raw = module.encode(capture)
    (folder / "stdout.bin").write_bytes(raw)
    (folder / "stderr.bin").write_bytes(b"")
    bound = {"container_id": plan["container_id"], "nonce": plan["nonce"]}
    documents = {
        "plan.json": plan,
        "stage-hashes.json": {"job.json": job_sha, "labels.json": H},
        "before-start.json": before,
        "final-inspect.json": final,
        "cleanup.json": {**bound, "removed": True, "reason": "owner_pipe_eof"},
        "start-intent.json": bound,
        "watchdog-ready.json": bound,
        "result.json": {
            **bound,
            "runtime_identity": candidate.identity,
            "stdout_sha256": module.sha(raw),
            "result": capture,
        },
    }
    for name, value in documents.items():
        module.write(folder / name, value)
    return candidate, folder, job_sha


def test_offline_recovery_needs_no_labels_or_api(tmp_path, monkeypatch):
    candidate, folder, job_sha = saved(tmp_path)
    assert not (folder / "stage/labels.json").exists()
    monkeypatch.setattr(
        module.API, "request", lambda *_a, **_k: pytest.fail("offline recovery used API")
    )
    assert candidate.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)["value"] == 1.0


def test_public_metadata_needs_no_labels_or_api_and_retains_unknown_time(tmp_path, monkeypatch):
    candidate, folder, job_sha = saved(tmp_path)
    monkeypatch.setattr(
        module.API, "request", lambda *_a, **_k: pytest.fail("metadata queried daemon")
    )
    evidence = candidate.execution_evidence(tmp_path, job_sha256=job_sha, labels_sha256=H)
    assert evidence["container_starts"] == evidence["scoring_process_starts"] == 1
    assert evidence["lifecycle_seconds"] is None
    assert evidence["stop_receipt_digest"] == module.sha(
        (folder / "final-inspect.json").read_bytes()
    )
    assert not any("path" in k or "labels" in k for k in evidence)


@pytest.mark.parametrize(
    "field,value",
    [
        ("socket_path", "/different-owned-socket"),
        ("server_sha256", "2" * 64),
        ("wrapper_bytes", b"changed source"),
    ],
)
def test_changed_runtime_configuration_refuses_before_api(tmp_path, monkeypatch, field, value):
    candidate = runtime()
    setattr(candidate, field, value)
    monkeypatch.setattr(
        module.API, "request", lambda *_a, **_k: pytest.fail("changed runtime used API")
    )
    with pytest.raises(module.Refused, match="configuration changed"):
        candidate.preflight()


@pytest.mark.parametrize(
    "name,change",
    [
        ("final-inspect.json", lambda v: v["State"].update(Running=True)),
        ("final-inspect.json", lambda v: v.update(RestartCount=1)),
        ("cleanup.json", lambda v: v.update(removed=False)),
        ("start-intent.json", lambda v: v.update(nonce="0" * 32)),
        ("stage-hashes.json", lambda v: v.update({"labels.json": "0" * 64})),
        ("plan.json", lambda v: v.update(runtime_identity="0" * 64)),
    ],
)
def test_changed_saved_identity_or_incomplete_stop_refuses(tmp_path, name, change):
    candidate, folder, job_sha = saved(tmp_path)
    path = folder / name
    value = json.loads(path.read_bytes())
    change(value)
    path.write_text(json.dumps(value))
    with pytest.raises(module.Refused):
        candidate.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)


def test_changed_public_job_cannot_reuse_saved_score(tmp_path):
    candidate, folder, job_sha = saved(tmp_path)
    (folder / "stage/job.json").write_bytes(b'{"changed":true}')
    with pytest.raises(module.Refused, match="public job"):
        candidate.recover(tmp_path, job_sha256=job_sha, labels_sha256=H)
