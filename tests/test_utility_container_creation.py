"""Creation/cleanup fault fixtures. No daemon, label scorer or model is started."""

import copy

import pytest

from autoengineering.utility import private_container_runtime as module
from test_utility_private_container_runtime import runtime


def workspace(tmp_path):
    tmp_path.chmod(0o700)
    work = tmp_path / "workspace"
    work.mkdir(mode=0o700)
    for name in ("job.json", "labels.json"):
        (work / name).write_bytes(b"{}")
    return module.sha(b"{}")


class Daemon:
    def __init__(self, root, *, lost_ack=True, delayed=False):
        self.root = root
        self.lost_ack = lost_ack
        self.delayed = delayed
        self.value = None
        self.pending = None
        self.creates = 0
        self.deletes = 0
        self.starts = 0

    def request(self, api, method, path, value=None, **kwargs):
        if method == "POST" and path.startswith("/containers/create?name="):
            assert (self.root / "container/creation-pending.json").exists()
            self.creates += 1
            self.pending = {
                "Id": "a" * 64,
                "Image": module.IMAGE,
                "Name": "/" + path.split("name=")[1],
                "Config": copy.deepcopy(value),
                "State": {"Running": False, "Status": "created"},
            }
            if not self.delayed:
                self.value = self.pending
            if self.lost_ack:
                raise TimeoutError("authored lost create acknowledgement")
            return 201, module.encode({"Id": "a" * 64})
        if method == "GET" and path.startswith("/containers/") and path.endswith("/json"):
            if self.value is None:
                return 404, b"{}"
            return 200, module.encode(self.value)
        if method == "DELETE":
            assert path == "/containers/" + ("a" * 64) + "?force=true"
            self.deletes += 1
            self.value = None
            return 204, b""
        if method == "POST" and path.endswith("/start"):
            self.starts += 1
        pytest.fail("unexpected daemon operation: " + method + " " + path)


def install(monkeypatch, daemon):
    monkeypatch.setattr(module.API, "request", lambda api, *a, **kw: daemon.request(api, *a, **kw))


def test_lost_create_ack_removes_only_original_and_never_retries(tmp_path, monkeypatch):
    candidate = runtime()
    digest = workspace(tmp_path)
    daemon = Daemon(tmp_path)
    install(monkeypatch, daemon)
    with pytest.raises(TimeoutError):
        candidate.run(tmp_path, api_version="1.53", job_sha256=digest, labels_sha256=digest)
    assert daemon.value is None and daemon.creates == daemon.deletes == 1 and daemon.starts == 0
    observed = candidate.reconcile_creation(tmp_path, stop=True)
    assert observed["removed"] is True
    assert daemon.deletes == 1
    with pytest.raises(FileExistsError):
        candidate.run(tmp_path, api_version="1.53", job_sha256=digest, labels_sha256=digest)
    assert daemon.creates == 1


def test_missing_name_after_uncertain_create_remains_uncertain(tmp_path, monkeypatch):
    candidate = runtime()
    digest = workspace(tmp_path)
    daemon = Daemon(tmp_path, delayed=True)
    install(monkeypatch, daemon)
    with pytest.raises(TimeoutError):
        candidate.run(tmp_path, api_version="1.53", job_sha256=digest, labels_sha256=digest)
    first = candidate.reconcile_creation(tmp_path)
    assert first["state"] == "absent_at_observation" and first["creation_uncertain"] is True
    assert first["removed"] is False and "no_launch" not in first
    assert not (tmp_path / "container/cleanup.json").exists()
    # The same original request commits late. No replacement create was made.
    daemon.value = daemon.pending
    final = candidate.reconcile_creation(tmp_path, stop=True)
    assert final["removed"] is True and daemon.value is None
    assert daemon.creates == daemon.deletes == 1 and daemon.starts == 0


def test_pipe_failure_after_create_ack_cleans_original_before_start(tmp_path, monkeypatch):
    candidate = runtime()
    digest = workspace(tmp_path)
    daemon = Daemon(tmp_path, lost_ack=False)
    install(monkeypatch, daemon)
    monkeypatch.setattr(
        module.os, "pipe", lambda: (_ for _ in ()).throw(OSError("authored pipe failure"))
    )
    with pytest.raises(OSError):
        candidate.run(tmp_path, api_version="1.53", job_sha256=digest, labels_sha256=digest)
    assert daemon.value is None and daemon.deletes == daemon.creates == 1 and daemon.starts == 0


def test_foreign_ownership_never_allows_delete(tmp_path, monkeypatch):
    candidate = runtime()
    digest = workspace(tmp_path)
    daemon = Daemon(tmp_path, delayed=True)
    install(monkeypatch, daemon)
    with pytest.raises(TimeoutError):
        candidate.run(tmp_path, api_version="1.53", job_sha256=digest, labels_sha256=digest)
    daemon.value = daemon.pending
    daemon.value["Config"]["Labels"]["org.autoengineering.nonce"] = "c" * 32
    with pytest.raises(module.Refused):
        candidate.reconcile_creation(tmp_path, stop=True)
    assert daemon.deletes == daemon.starts == 0


def test_observe_without_stop_and_reconcile_without_label_reads(tmp_path, monkeypatch):
    candidate = runtime()
    digest = workspace(tmp_path)
    daemon = Daemon(tmp_path, delayed=True)
    install(monkeypatch, daemon)
    with pytest.raises(TimeoutError):
        candidate.run(tmp_path, api_version="1.53", job_sha256=digest, labels_sha256=digest)
    daemon.value = daemon.pending
    old_read = module.read_regular

    def metadata_only(path, limit):
        assert path.name not in ("labels.json", "job.json")
        return old_read(path, limit)

    monkeypatch.setattr(module, "read_regular", metadata_only)
    before = candidate.reconcile_creation(tmp_path)
    assert before["state"] == "observed" and before["removed"] is False
    assert daemon.deletes == 0
    after = candidate.reconcile_creation(tmp_path, stop=True)
    assert after["removed"] is True and daemon.deletes == 1


def test_failed_delete_can_retry_same_id_without_rewriting_first_snapshot(tmp_path, monkeypatch):
    candidate = runtime()
    digest = workspace(tmp_path)
    daemon = Daemon(tmp_path, delayed=True)
    install(monkeypatch, daemon)
    with pytest.raises(TimeoutError):
        candidate.run(tmp_path, api_version="1.53", job_sha256=digest, labels_sha256=digest)
    daemon.value = daemon.pending
    original = daemon.request
    failed = []

    def first_delete_fails(api, method, path, value=None, **kw):
        if method == "DELETE" and not failed:
            failed.append(True)
            return 500, b"{}"
        return original(api, method, path, value, **kw)

    monkeypatch.setattr(module.API, "request", first_delete_fails)
    with pytest.raises(module.Refused, match="removal is unverified"):
        candidate.reconcile_creation(tmp_path, stop=True)
    snapshot = tmp_path / "container/cleanup-before.json"
    saved = snapshot.read_bytes()
    result = candidate.reconcile_creation(tmp_path, stop=True)
    assert result["removed"] is True and daemon.value is None
    assert snapshot.read_bytes() == saved
    assert len(list((tmp_path / "container").glob("cleanup-before-*.json"))) == 1


def test_api_error_never_proves_absence(tmp_path, monkeypatch):
    candidate = runtime()
    digest = workspace(tmp_path)
    daemon = Daemon(tmp_path, delayed=True)
    install(monkeypatch, daemon)
    with pytest.raises(TimeoutError):
        candidate.run(tmp_path, api_version="1.53", job_sha256=digest, labels_sha256=digest)
    monkeypatch.setattr(module.API, "request", lambda *_a, **_kw: (500, b"{}"))
    with pytest.raises(module.Refused, match="observation is unverified"):
        candidate.reconcile_creation(tmp_path, stop=True)
    assert not (tmp_path / "container/cleanup.json").exists()
