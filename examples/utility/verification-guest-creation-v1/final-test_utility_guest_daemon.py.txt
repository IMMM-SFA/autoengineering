"""Authored daemon projections and owned Unix HTTP, not actual Docker execution."""

from copy import deepcopy
from dataclasses import replace
import shutil
import time

import pytest

from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.utility import guest_daemon as module
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_receipts import GuestStdinPolicy
import test_utility_guest_inputs as input_fixture
import test_utility_guest_observations as observation_fixture
import test_utility_guest_attach as wire_fixture

metadata = input_fixture.metadata
H = "1" * 64
SERVER = {"ApiVersion": "1.48", "Os": "linux", "Arch": "amd64", "Version": "authored"}


class Daemon:
    def __init__(self, owner):
        captures = observation_fixture.captures(owner.manifest.job, owner.manifest.launch)
        self.owner = owner
        self.image, self.created = captures["image"], captures["created"]
        self.created["Mounts"] = []
        for name in ("Binds", "Mounts", "VolumesFrom", "Devices", "DeviceRequests", "CapAdd"):
            self.created["HostConfig"][name] = None
        self.created["HostConfig"]["PortBindings"] = None
        self.server = deepcopy(SERVER)
        self.exists = False
        self.lost = False
        self.warnings = []
        self.calls = []
        self.creates = 0

    def request(self, method, path, value=None, **kwargs):
        self.calls.append((method, path, value))
        if path == "/version":
            return 200, canonical_json(self.server).encode()
        if path.startswith("/images/"):
            return 200, canonical_json(self.image).encode()
        if method == "POST":
            assert path.startswith("/containers/create?name=ae-frozen-routing-")
            assert self.owner.replay().phase == "create_intent"
            assert "daemon_preflight" in self.owner.replay().observations["create_intent"]
            self.creates += 1
            self.exists = True
            if self.lost:
                raise module.GuestDaemonError("authored lost creation response")
            return 201, canonical_json({"Id": H, "Warnings": self.warnings}).encode()
        assert method == "GET" and path.startswith("/containers/")
        return (200, canonical_json(self.created).encode()) if self.exists else (404, b"")


def prepared(tmp_path, metadata, monkeypatch, *, authorize=True):
    api = module.GuestDaemonAPI(
        "/authored-daemon.sock", api_version="1.48", server_digest=digest(SERVER)
    )
    owner, store, source, drivers = input_fixture.prepared(
        tmp_path,
        metadata,
        authorize=authorize,
        policy=GuestStdinPolicy(),
        runtime_digest=api.identity,
    )
    if authorize:
        input_fixture.prepare(owner, store, source, drivers)
    daemon = Daemon(owner)
    monkeypatch.setattr(api, "_request", daemon.request)
    return owner, store, api, daemon


def create(owner, store, api):
    with store.writer(), owner.writer():
        return module.GuestCreationController(api).create(
            owner, store, deadline=time.monotonic() + 5
        )


def reconcile(owner, store, api):
    with store.writer(), owner.writer():
        return module.GuestCreationController(api).reconcile_creation(
            owner, store, deadline=time.monotonic() + 5
        )


def test_creation_binds_original_preflight_and_never_starts(tmp_path, metadata, monkeypatch):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    assert create(owner, store, api) == H
    state = owner.replay()
    assert state.phase == "created" and daemon.creates == 1
    assert state.events[1].daemon_creation is not None
    assert len([c for c in daemon.calls if c[0] == "POST"]) == 1
    ref = state.observations["create_intent"]["daemon_preflight"]
    assert ref["sha256"]
    assert state.observations["created"]["Mounts"] == []
    assert state.observations["created"]["State"]["Pid"] == 0
    assert not hasattr(module.GuestCreationController(api), "start")
    before = list(daemon.calls)
    with pytest.raises(ValueError, match="already consumed"):
        create(owner, store, api)
    assert daemon.calls == before
    with pytest.raises(ValueError, match="unresolved create intent"):
        reconcile(owner, store, api)
    assert daemon.creates == 1


@pytest.mark.parametrize(
    "point",
    [
        "daemon_preflight_saved",
        "before_create_intent",
        "after_create_intent",
        "before_daemon_create",
        "after_daemon_create",
        "daemon_create_response_saved",
        "before_created",
        "after_created",
    ],
)
def test_faults_retain_original_charge_and_never_reissue_uncertain_create(
    tmp_path, metadata, monkeypatch, point
):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    before = store.replay()

    def fail(stage):
        if stage == point:
            raise RuntimeError("authored owner loss")

    owner.fault = fail
    with pytest.raises(RuntimeError):
        create(owner, store, api)
    owner = GuestOwnerJournal(owner.root, suite_root=store.root)
    state = owner.replay()
    count = daemon.creates
    if state.phase == "ready":
        assert count == 0
        assert create(owner, store, api) == H
        assert daemon.creates == 1
    elif state.phase == "create_intent":
        with pytest.raises(ValueError, match="already consumed"):
            create(owner, store, api)
        if daemon.exists:
            assert reconcile(owner, store, api) == H
            assert owner.replay().phase == "created"
        else:
            with pytest.raises(ValueError, match="absence does not authorize"):
                reconcile(owner, store, api)
        assert daemon.creates == count
    else:
        assert state.phase == "created" and count == 1
    assert store.replay() == before


def test_lost_creation_response_recovers_original_nonce_without_another_post(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    daemon.lost = True
    with pytest.raises(ValueError, match="lost creation response"):
        create(owner, store, api)
    assert owner.replay().create_uncertain
    assert reconcile(owner, store, api) == H and daemon.creates == 1
    assert owner.replay().events[1].daemon_creation is None


@pytest.mark.parametrize("problem", ["server", "image", "name", "runtime", "access", "source"])
def test_bad_preflight_refuses_before_create_intent(tmp_path, metadata, monkeypatch, problem):
    owner, store, api, daemon = prepared(
        tmp_path, metadata, monkeypatch, authorize=problem != "access"
    )
    if problem == "server":
        daemon.server["Version"] = "changed"
    elif problem == "image":
        daemon.image["Architecture"] = "arm64"
    elif problem == "name":
        daemon.exists = True
    elif problem == "runtime":
        api.profile = replace(api.profile, server_digest="2" * 64)
    elif problem == "source":
        old = api._profile
        monkeypatch.setattr(
            api, "_profile", lambda *args: replace(old(*args), engine_source_digest="2" * 64)
        )
    with pytest.raises(ValueError):
        create(owner, store, api)
    assert owner.replay().phase == "ready" and daemon.creates == 0


@pytest.mark.parametrize("problem", ["warnings", "foreign_created", "running_created"])
def test_post_creation_failure_stays_uncertain_without_new_create(
    tmp_path, metadata, monkeypatch, problem
):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    if problem == "warnings":
        daemon.warnings = ["authored unsupported resource"]
    elif problem == "foreign_created":
        daemon.created["Name"] = "/foreign"
    else:
        daemon.created["State"].update(Status="running", Running=True, Pid=42)
    with pytest.raises(ValueError):
        create(owner, store, api)
    assert owner.replay().phase == "create_intent" and daemon.creates == 1
    with pytest.raises(ValueError, match="already consumed"):
        create(owner, store, api)
    assert daemon.creates == 1
    if problem == "warnings":
        calls = list(daemon.calls)
        with pytest.raises(ValueError, match="unresolved warnings"):
            reconcile(owner, store, api)
        assert daemon.calls == calls


def test_preflight_and_original_observations_relocate_without_live_api(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    create(owner, store, api)
    copied = tmp_path / "copy"
    shutil.copytree(owner.root, copied)
    shutil.rmtree(store.root)
    monkeypatch.setattr(api, "_request", lambda *_a, **_k: pytest.fail("live API"))
    monkeypatch.setattr(module.socket, "socket", lambda *_a, **_k: pytest.fail("new socket"))
    assert GuestOwnerJournal(copied).replay().phase == "created"


def test_missing_original_preflight_cannot_be_substituted_by_live_metadata(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    daemon.lost = True
    with pytest.raises(ValueError):
        create(owner, store, api)
    ref = owner.replay().observations["create_intent"]["daemon_preflight"]
    (owner.root / ref["path"]).unlink()
    calls = list(daemon.calls)
    with pytest.raises(ValueError):
        reconcile(owner, store, api)
    assert daemon.calls == calls and daemon.creates == 1


def test_both_writers_are_required_before_any_api_call(tmp_path, metadata, monkeypatch):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    controller = module.GuestCreationController(api)
    with pytest.raises(ValueError, match="writers"):
        controller.create(owner, store, deadline=time.monotonic() + 5)
    with store.writer(), pytest.raises(ValueError, match="writers"):
        controller.create(owner, store, deadline=time.monotonic() + 5)
    assert daemon.calls == []


@pytest.mark.parametrize("kind", ["length", "chunked"])
def test_native_unix_http_json_reader(kind):
    requests = []

    def serve(connection):
        raw = bytearray()
        while not raw.endswith(b"\r\n\r\n"):
            raw.extend(connection.recv(1))
        requests.append(bytes(raw))
        payload = canonical_json(SERVER).encode()
        if kind == "length":
            header = f"HTTP/1.1 200 OK\r\nContent-Length: {len(payload)}\r\n\r\n".encode()
            connection.sendall(header + payload)
        else:
            connection.sendall(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n")
            for start in range(0, len(payload), 7):
                part = payload[start : start + 7]
                connection.sendall(f"{len(part):x}\r\n".encode() + part + b"\r\n")
            connection.sendall(b"0\r\n\r\n")

    with wire_fixture.unix_server(serve) as endpoint:
        api = module.GuestDaemonAPI(endpoint, api_version="1.48", server_digest=digest(SERVER))
        result = api._json("GET", "/version", deadline=time.monotonic() + 3)
    assert result == SERVER
    assert requests[0].startswith(b"GET /v1.48/version HTTP/1.1\r\n")
    assert b"Connection: close" in requests[0]


@pytest.mark.parametrize(
    "raw",
    [
        b"HTTP/1.1 200 OK\r\nContent-Length: 100000000\r\n\r\n",
        b"HTTP/1.1 200 OK\r\nContent-Length: 1\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n",
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: gzip\r\n\r\n",
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n10000000\r\n",
        b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n0\r\nHidden: value\r\n\r\n",
        b"HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nshort",
        b"HTTP/1.1 200 OK\r\n\r\n{}",
    ],
)
def test_ambiguous_unbounded_or_truncated_json_http_refuses(monkeypatch, raw):
    wire = wire_fixture.Wire(raw)
    monkeypatch.setattr(module.socket, "socket", lambda *_: wire)
    api = module.GuestDaemonAPI("/authored.sock", api_version="1.48", server_digest=digest(SERVER))
    with pytest.raises(ValueError):
        api._json("GET", "/version", deadline=time.monotonic() + 3)
    assert wire.closed


@pytest.mark.parametrize("mounts", [[], [{"Type": "tmpfs", "Destination": "/work", "RW": True}]])
def test_map_tmpfs_and_legacy_projection_both_require_exact_configuration(
    tmp_path, metadata, monkeypatch, mounts
):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    daemon.created["Mounts"] = mounts
    assert create(owner, store, api) == H


def test_empty_mount_projection_cannot_hide_a_host_bind(tmp_path, metadata, monkeypatch):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    daemon.created["HostConfig"]["Binds"] = ["/:/host"]
    with pytest.raises(ValueError):
        create(owner, store, api)
    assert owner.replay().phase == "create_intent"


def test_known_creation_capture_is_required_and_hash_checked_on_replay(
    tmp_path, metadata, monkeypatch
):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    create(owner, store, api)
    ref = owner.replay().events[1].daemon_creation
    assert ref is not None
    path = owner.root / ref.path
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        owner.replay()


def test_json_header_trickle_cannot_renew_original_deadline(monkeypatch):
    clock = wire_fixture.Clock(step=0.01)
    monkeypatch.setattr(wire_fixture.module, "_now", clock)
    payload = canonical_json(SERVER).encode()
    wire = wire_fixture.Wire(
        f"HTTP/1.1 200 OK\r\nContent-Length: {len(payload)}\r\n\r\n".encode() + payload,
        chunk=1,
    )
    monkeypatch.setattr(module.socket, "socket", lambda *_: wire)
    api = module.GuestDaemonAPI("/authored.sock", api_version="1.48", server_digest=digest(SERVER))
    with pytest.raises(wire_fixture.module.GuestAttachTimeout):
        api._json("GET", "/version", deadline=1)
    assert clock.value >= 1 and wire.closed


def test_source_and_endpoint_profiles_are_opaque_pins_not_private_paths():
    api = module.GuestDaemonAPI(
        "/authored-private-directory/daemon.sock", api_version="1.48", server_digest=digest(SERVER)
    )
    assert "/authored-private-directory" not in api.profile.to_json()
    assert api.profile.endpoint_digest == digest("/authored-private-directory/daemon.sock")
    assert len(api.profile.engine_source_digest) == len(api.profile.owner_python_digest) == 64


def test_cancelled_suite_refuses_before_any_daemon_request(tmp_path, metadata, monkeypatch):
    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    grant = owner.manifest.job.grant
    with store.writer():
        store.append(
            request_id="authored-cancel-before-create",
            operation="cancel",
            cell_digest=grant.cell_digest,
            attempt_id="confirmation-" + grant.cell_digest[:48],
            child_digest=grant.digest,
            phase="confirmation",
        )
    with pytest.raises(ValueError, match="cancelled"):
        create(owner, store, api)
    assert daemon.calls == [] and owner.replay().phase == "ready"


def test_cold_original_creation_reader_uses_only_saved_projections(tmp_path, metadata, monkeypatch):
    import subprocess
    import sys

    owner, store, api, daemon = prepared(tmp_path, metadata, monkeypatch)
    create(owner, store, api)
    script = """
import importlib.abc,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:
   raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.utility.guest_owner import GuestOwnerJournal
import numpy,subprocess,socket,os,time
def forbidden(*args,**kwargs):raise AssertionError('execution/runtime/array access')
numpy.load=subprocess.Popen=socket.socket=time.monotonic=forbidden
root=Path(sys.argv[1]);allowed={p for p in root.rglob('*') if p.is_file()}
old=Path.open;old_os=os.open
def guarded(path,mode='r',*args,**kwargs):
 if path not in allowed or any(c in mode for c in 'wax+'):raise AssertionError('ungranted access')
 return old(path,mode,*args,**kwargs)
def guarded_os(path,flags,*args,**kwargs):
 if Path(path) not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):
  raise AssertionError('ungranted access')
 return old_os(path,flags,*args,**kwargs)
Path.open=guarded;os.open=guarded_os
owner=GuestOwnerJournal(root);state=owner.replay()
assert state.phase=='created' and state.events[1].daemon_creation is not None
assert state.observations['created']['State']['Pid']==0
print(owner.manifest.digest)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(owner.root)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stdout.strip() == owner.manifest.digest


def test_native_unix_create_serializes_only_fixed_metadata(tmp_path, metadata):
    received = []

    def serve(connection):
        header = bytearray()
        while not header.endswith(b"\r\n\r\n"):
            part = connection.recv(1)
            assert part
            header.extend(part)
        length = next(
            int(line.split(b":", 1)[1])
            for line in header.split(b"\r\n")
            if line.lower().startswith(b"content-length:")
        )
        payload = bytearray()
        while len(payload) < length:
            part = connection.recv(length - len(payload))
            assert part
            payload.extend(part)
        received.append((bytes(header), module.unique_json(payload.decode())))
        raw = canonical_json({"Id": H, "Warnings": []}).encode()
        connection.sendall(
            f"HTTP/1.1 201 Created\r\nContent-Length: {len(raw)}\r\n\r\n".encode() + raw
        )

    with wire_fixture.unix_server(serve) as endpoint:
        api = module.GuestDaemonAPI(endpoint, api_version="1.48", server_digest=digest(SERVER))
        owner, store, source, drivers = input_fixture.prepared(
            tmp_path, metadata, policy=GuestStdinPolicy(), runtime_digest=api.identity
        )
        m = owner.manifest
        result = api._create(m.job, m.launch, deadline=time.monotonic() + 3)
    assert result == {"Id": H, "Warnings": []}
    header, body = received[0]
    assert header.startswith(b"POST /v1.48/containers/create?name=ae-frozen-routing-")
    assert b"platform=linux%2Famd64" in header
    assert body == module.configuration(m.job, m.launch)
    assert "prediction" not in canonical_json(
        body
    ) and "AUTHORED-PRIVATE-CANARY" not in canonical_json(body)
    assert owner.replay().phase == "ready"  # Low-level authored HTTP test, not owner dispatch.
