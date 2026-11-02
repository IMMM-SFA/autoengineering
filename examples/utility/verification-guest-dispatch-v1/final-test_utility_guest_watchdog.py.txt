"""Original-CID cleanup on authored peers; no Docker or privacy qualification."""

from contextlib import contextmanager
from pathlib import Path
import socket
import tempfile
import threading

from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_receipts import GuestStdinPolicy

import subprocess
import sys

from copy import deepcopy
from dataclasses import replace
import time

import pytest

from autoengineering.campaign.store import durable_write
from autoengineering.utility import guest_watchdog as module
import test_utility_guest_daemon as fixture

metadata = fixture.metadata


def prepared(tmp_path, metadata, monkeypatch):
    owner, store, api, daemon = fixture.prepared(tmp_path, metadata, monkeypatch)
    fixture.create(owner, store, api)
    root = owner.root / "control" / "guest-watchdog"
    root.mkdir(mode=0o700)
    (root / "artifacts").mkdir(mode=0o700)
    m = owner.manifest
    now = time.monotonic()
    plan = module.GuestWatchdogPlan(
        "utility-guest-watchdog-plan-v1",
        m.digest,
        m.job.digest,
        m.launch.digest,
        fixture.H,
        m.job.nonce,
        123,
        str(store.root),
        api._socket_path,
        api.profile,
        now,
        now + 20,
    )
    durable_write(root / "plan.json", plan.to_json().encode())
    original = daemon.request

    def request(method, path, value=None, **kwargs):
        if method == "POST" and "/kill?" in path:
            daemon.calls.append((method, path, value))
            daemon.created["State"].update(
                Status="exited",
                Running=False,
                Pid=0,
                ExitCode=137,
            )
            if daemon.lost:
                raise OSError("authored lost kill response")
            return 204, b""
        if method == "DELETE":
            daemon.calls.append((method, path, value))
            daemon.exists = False
            if daemon.lost:
                raise OSError("authored lost delete response")
            return 204, b""
        return original(method, path, value, **kwargs)

    monkeypatch.setattr(api, "_request", request)
    return owner, store, api, daemon, root, plan


def running(daemon):
    daemon.created["State"].update(Status="running", Running=True, Pid=123)


@pytest.mark.parametrize("lost", [False, True])
def test_owned_cleanup_observes_stop_and_absence_even_with_lost_responses(
    tmp_path, metadata, monkeypatch, lost
):
    owner, store, api, daemon, root, plan = prepared(tmp_path, metadata, monkeypatch)
    running(daemon)
    daemon.lost = lost
    # Resource drift is adverse but cannot disable cleanup of the owned CID.
    daemon.created["HostConfig"]["Memory"] = 0
    before = store.replay()
    outcome = module.cleanup(owner, api, plan, root, "owner_lost")
    assert outcome.result == "absent"
    assert outcome.before and outcome.stopped and outcome.absence
    assert outcome.kill_intended and outcome.delete_intended
    assert module.read_outcome(root, owner, plan) == outcome
    calls = deepcopy(daemon.calls)
    assert module.cleanup(owner, api, plan, root, "deadline") == outcome
    assert daemon.calls == calls  # Original completed cleanup never repeats mutations.
    assert store.replay() == before
    mutations = [(m, p) for m, p, _ in calls if m in ("POST", "DELETE")]
    assert mutations[-2:] == [
        ("POST", f"/containers/{fixture.H}/kill?signal=SIGKILL"),
        ("DELETE", f"/containers/{fixture.H}?force=1&v=0"),
    ]


@pytest.mark.parametrize("problem", ["image", "labels", "id"])
def test_foreign_identity_never_authorizes_mutation(tmp_path, metadata, monkeypatch, problem):
    owner, _, api, daemon, root, plan = prepared(tmp_path, metadata, monkeypatch)
    running(daemon)
    if problem == "image":
        daemon.created["Image"] = "sha256:" + "2" * 64
    elif problem == "id":
        daemon.created["Id"] = "2" * 64
    else:
        daemon.created["Config"]["Labels"] = {}
    calls = len(daemon.calls)
    outcome = module.cleanup(owner, api, plan, root, "cancelled")
    assert outcome.result == "foreign_refused"
    assert not outcome.kill_intended and not outcome.delete_intended
    assert all(method == "GET" for method, _, _ in daemon.calls[calls:])
    assert module.read_outcome(root, owner, plan) == outcome


def test_existing_absence_is_not_fabricated_stop(tmp_path, metadata, monkeypatch):
    owner, _, api, daemon, root, plan = prepared(tmp_path, metadata, monkeypatch)
    daemon.exists = False
    outcome = module.cleanup(owner, api, plan, root, "deadline")
    assert outcome.result == "absent" and outcome.absence
    assert outcome.stopped is None and outcome.before is None
    assert not outcome.kill_intended and not outcome.delete_intended


def test_server_change_preserves_unverified_outcome(tmp_path, metadata, monkeypatch):
    owner, _, api, daemon, root, plan = prepared(tmp_path, metadata, monkeypatch)
    daemon.server["Version"] = "another-daemon"
    calls = len(daemon.calls)
    outcome = module.cleanup(owner, api, plan, root, "deadline")
    assert outcome.result == "unverified" and not outcome.absence
    assert len(daemon.calls) == calls + 1


def test_cold_outcome_checks_saved_bytes_without_clock_or_daemon(tmp_path, metadata, monkeypatch):
    owner, _, api, daemon, root, plan = prepared(tmp_path, metadata, monkeypatch)
    running(daemon)
    outcome = module.cleanup(owner, api, plan, root, "cancelled")

    def forbidden(*args, **kwargs):
        raise AssertionError("cold replay must not probe live resources")

    monkeypatch.setattr(api, "_request", forbidden)
    monkeypatch.setattr(module.time, "monotonic", forbidden)
    assert module.read_outcome(root, owner, plan) == outcome
    assert outcome.stopped
    path = root / outcome.stopped.path
    path.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        module.read_outcome(root, owner, plan)


def test_plan_rejects_nonfinite_or_expanded_deadline(tmp_path, metadata, monkeypatch):
    _, _, _, _, _, plan = prepared(tmp_path, metadata, monkeypatch)
    for end in (float("inf"), float("nan"), plan.armed_at + 61):
        with pytest.raises(ValueError):
            replace(plan, deadline=end)


# A real local Unix HTTP peer services the independent watchdog child. Every
# container state below is authored; no Docker endpoint or executable model exists.


@contextmanager
def native_peer():
    with tempfile.TemporaryDirectory(prefix="ae-guard-", dir="/tmp") as folder:
        endpoint = str(Path(folder) / "peer.sock")
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        listener.bind(endpoint)
        listener.listen(8)
        listener.settimeout(0.1)
        stop = threading.Event()
        peer = {"daemon": None, "errors": [], "calls": []}

        def serve():
            while not stop.is_set():
                try:
                    stream, _ = listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    with stream:
                        stream.settimeout(2)
                        raw = bytearray()
                        while b"\r\n\r\n" not in raw:
                            value = stream.recv(4096)
                            if not value or len(raw) > 65536:
                                raise AssertionError("authored request headers incomplete")
                            raw.extend(value)
                        header, body = bytes(raw).split(b"\r\n\r\n", 1)
                        lines = header.decode().split("\r\n")
                        method, path, _ = lines[0].split(" ")
                        fields = dict(line.split(": ", 1) for line in lines[1:])
                        size = int(fields.get("Content-Length", "0"))
                        assert 0 <= size <= 65536
                        while len(body) < size:
                            body += stream.recv(size - len(body))
                        assert len(body) == size
                        path = path.removeprefix("/v1.48")
                        peer["calls"].append((method, path))
                        daemon = peer["daemon"]
                        if method == "POST" and "/kill?" in path:
                            assert path == f"/containers/{fixture.H}/kill?signal=SIGKILL"
                            daemon.created["State"].update(
                                Status="exited", Running=False, Pid=0, ExitCode=137
                            )
                            status, output = 204, b""
                        elif method == "DELETE":
                            assert path == f"/containers/{fixture.H}?force=1&v=0"
                            daemon.exists = False
                            status, output = 204, b""
                        else:
                            value = unique_json(body.decode()) if body else None
                            status, output = daemon.request(method, path, value)
                        stream.sendall(
                            f"HTTP/1.1 {status} Authored\r\nContent-Length: {len(output)}\r\n"
                            "Connection: close\r\n\r\n".encode()
                            + output
                        )
                except BaseException as error:
                    peer["errors"].append(error)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            yield endpoint, peer
        finally:
            stop.set()
            listener.close()
            thread.join(timeout=3)
            assert not thread.is_alive()
            assert not peer["errors"], peer["errors"]


def native_prepared(tmp_path, metadata, endpoint, peer):
    api = GuestDaemonAPI(endpoint, api_version="1.48", server_digest=digest(fixture.SERVER))
    owner, store, source, drivers = fixture.input_fixture.prepared(
        tmp_path, metadata, policy=GuestStdinPolicy(), runtime_digest=api.identity
    )
    fixture.input_fixture.prepare(owner, store, source, drivers)
    peer["daemon"] = fixture.Daemon(owner)
    fixture.create(owner, store, api)
    return owner, store, api


@pytest.mark.parametrize("trigger", ["owner_lost", "cancelled", "deadline", "invalid_disarm"])
def test_real_watchdog_process_observes_pipe_and_deadline(tmp_path, metadata, trigger):
    with native_peer() as (endpoint, peer):
        owner, store, api = native_prepared(tmp_path, metadata, endpoint, peer)
        with store.writer(), owner.writer():
            handle = module.arm(owner, store, api, deadline=time.monotonic() + 3)
        try:
            ready = handle.check_live()
            assert ready.watchdog_pid == handle.process.pid
            assert handle.process.pid != module.os.getpid()
            running(peer["daemon"])
            if trigger == "owner_lost":
                handle.close_owner()
            elif trigger == "cancelled":
                handle.cancel()
            elif trigger == "invalid_disarm":
                with pytest.raises(ValueError, match="before original cleanup"):
                    handle.disarm()
                # Simulate a buggy owner bypassing the parent's API guard.
                module.os.write(handle._owner_fd, b"D")
                handle.close_owner()
            outcome = handle.outcome(timeout=15)
            assert outcome.reason == trigger and outcome.result == "absent"
            assert outcome.stopped and outcome.absence
            assert handle.process.returncode == 0
            assert (
                peer["calls"].count(("POST", f"/containers/{fixture.H}/kill?signal=SIGKILL")) == 1
            )
            assert peer["calls"].count(("DELETE", f"/containers/{fixture.H}?force=1&v=0")) == 1
            assert not any("/start" in path for _, path in peer["calls"])
            assert peer["daemon"].creates == 1
            with pytest.raises(ValueError, match="not live"):
                handle.check_live()
        finally:
            handle.close_owner()
            handle.process.wait(timeout=15)


def test_watchdog_survives_actual_owner_sigkill(tmp_path, metadata):
    with native_peer() as (endpoint, peer):
        owner, store, _ = native_prepared(tmp_path, metadata, endpoint, peer)
        helper_ready = tmp_path / "helper-ready.json"
        script = """
from pathlib import Path
import signal, sys, time
from autoengineering.campaign.serialization import digest
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_watchdog import arm
from autoengineering.utility.store import SuiteStore
suite = SuiteStore(Path(sys.argv[1]))
owner = GuestOwnerJournal(Path(sys.argv[2]), suite_root=suite.root)
server = {"ApiVersion":"1.48","Os":"linux","Arch":"amd64","Version":"authored"}
api = GuestDaemonAPI(sys.argv[3], api_version="1.48", server_digest=digest(server))
with suite.writer(), owner.writer():
    handle = arm(owner, suite, api, deadline=time.monotonic() + 10)
Path(sys.argv[4]).write_text(handle.check_live().to_json())
signal.pause()
"""
        helper = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-c",
                script,
                str(store.root),
                str(owner.root),
                endpoint,
                str(helper_ready),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        guard_root = owner.root / "control" / "guest-watchdog"
        try:
            end = time.monotonic() + 8
            while not helper_ready.exists() and helper.poll() is None and time.monotonic() < end:
                time.sleep(0.05)
            assert helper_ready.exists(), helper.poll()
            ready = module.GuestWatchdogReady.from_json(helper_ready.read_text())
            assert ready.watchdog_pid != helper.pid
            running(peer["daemon"])
            helper.kill()  # Kill only the exact child Popen created by this test.
            assert helper.wait(timeout=5) < 0
            end = time.monotonic() + 15
            while not (guard_root / "outcome.json").exists() and time.monotonic() < end:
                time.sleep(0.05)
            plan = module.GuestWatchdogPlan.from_json((guard_root / "plan.json").read_text())
            outcome = module.read_outcome(guard_root, owner, plan)
            assert outcome.reason == "owner_lost" and outcome.result == "absent"
            assert outcome.stopped and outcome.kill_intended and outcome.delete_intended
            # The orphan guard is not our child. Observe terminal status without
            # sending signals to a PID that might eventually be reused.
            end = time.monotonic() + 3
            while time.monotonic() < end:
                status = subprocess.run(
                    ["ps", "-p", str(ready.watchdog_pid), "-o", "stat="],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if status.returncode == 1 or status.stdout.strip().startswith("Z"):
                    break
                time.sleep(0.05)
            else:
                pytest.fail("original watchdog did not terminate after publishing cleanup")
        finally:
            if helper.poll() is None:
                helper.kill()
            helper.wait(timeout=5)
            helper.stderr.close()


def test_verified_parent_cleanup_can_disarm_without_watchdog_mutation(tmp_path, metadata):
    with native_peer() as (endpoint, peer):
        owner, store, api = native_prepared(tmp_path, metadata, endpoint, peer)
        with store.writer(), owner.writer():
            handle = module.arm(owner, store, api, deadline=time.monotonic() + 8)
        try:
            observations = fixture.observation_fixture.captures(
                owner.manifest.job, owner.manifest.launch
            )
            # Authored saved lifecycle only; no actual model or container start.
            with owner.writer():
                owner.record("start_intent")
                owner.record("started", observations["started"])
                owner.record(
                    "stopped",
                    {
                        "inspect": observations["stopped"],
                        "reason": None,
                        "elapsed_seconds": None,
                    },
                )
                owner.record("cleanup_intent")
                owner.record("cleaned", observations["cleanup"])
            peer["daemon"].exists = False
            handle.disarm()
            outcome = handle.outcome()
            assert outcome.result == "disarmed" and outcome.reason == "owner_done"
            assert outcome.parent_cleanup_head == owner.replay().events[-1].digest
            assert outcome.absence and not outcome.stopped
            assert not outcome.kill_intended and not outcome.delete_intended
            assert not any(method == "DELETE" or "/kill?" in path for method, path in peer["calls"])
        finally:
            handle.close_owner()
            handle.process.wait(timeout=15)


def test_unknown_creation_response_cannot_arm_new_guard(tmp_path, metadata, monkeypatch):
    owner, store, api, daemon = fixture.prepared(tmp_path, metadata, monkeypatch)
    daemon.lost = True
    with pytest.raises(ValueError):
        fixture.create(owner, store, api)
    fixture.reconcile(owner, store, api)
    assert owner.replay().events[1].daemon_creation is None
    with store.writer(), owner.writer(), pytest.raises(ValueError, match="reviewed original"):
        module.arm(owner, store, api, deadline=time.monotonic() + 5)
    assert not (owner.root / "control/guest-watchdog").exists()


def test_original_guard_cannot_be_replaced(tmp_path, metadata):
    with native_peer() as (endpoint, peer):
        owner, store, api = native_prepared(tmp_path, metadata, endpoint, peer)
        with store.writer(), owner.writer():
            handle = module.arm(owner, store, api, deadline=time.monotonic() + 8)
        try:
            before = (handle.root / "plan.json").read_bytes()
            with store.writer(), owner.writer(), pytest.raises(FileExistsError):
                module.arm(owner, store, api, deadline=time.monotonic() + 5)
            assert (handle.root / "plan.json").read_bytes() == before
            handle.cancel()
            assert handle.outcome().result == "absent"
        finally:
            handle.close_owner()
            handle.process.wait(timeout=15)


def test_expired_deadline_precedes_simultaneous_owner_pipe_eof(tmp_path, metadata, monkeypatch):
    owner, _, api, daemon, root, plan = prepared(tmp_path, metadata, monkeypatch)
    clock = [plan.armed_at]
    owner_read, owner_write = module.os.pipe()
    ready_read, ready_write = module.os.pipe()
    module.os.close(owner_write)

    def expire_when_readable(readers, writers, errors, timeout):
        assert readers == [owner_read]
        running(daemon)
        clock[0] = plan.deadline  # Scheduler resumes the read exactly at expiry.
        return [owner_read], [], []

    monkeypatch.setattr(module, "GuestDaemonAPI", lambda *args, **kwargs: api)
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(module.select, "select", expire_when_readable)
    try:
        outcome = module.watch(root, owner_read, ready_write)
        assert outcome.reason == "deadline" and outcome.result == "absent"
        assert outcome.kill_intended and outcome.delete_intended
        assert module.read_outcome(root, owner, plan) == outcome
    finally:
        module.os.close(owner_read)
        module.os.close(ready_read)
