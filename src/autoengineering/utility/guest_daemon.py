"""Candidate local daemon preflight and durable, unstarted guest creation.

Creation never starts a container. Start/attach dispatch must wait for an
independent owner-loss/deadline watchdog. No default service activates this API.
Canonical saved projections are producer evidence, not OS/runtime qualification.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import socket
import sys
from typing import Literal

from autoengineering.campaign.artifacts import put_bytes, read_bytes, confined_file
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError, durable_write
from .contracts import sha256
from .guest_attach import GuestAttachSession
from .guest_inputs import verify_guest_inputs
from .guest_observations import configuration, container_name, verify_created, verify_image
from .guest_receipts import GuestStdinPolicy
from .scoring import validate_grant

MAX_JSON = 1024 * 1024
MAX_CHUNKS = 4096
SOURCES = (
    "guest_attach.py",
    "guest_bootstrap.py",
    "guest_daemon.py",
    "guest_inputs.py",
    "guest_observations.py",
    "guest_owner.py",
    "guest_receipts.py",
)


class GuestDaemonError(StoreError):
    """An API outcome is unverified; no new scientific attempt is authorized."""


def _endpoint(path):
    text = str(path)
    if not Path(text).is_absolute() or "\x00" in text or ".." in Path(text).parts:
        raise GuestDaemonError("guest daemon requires an explicit local Unix endpoint")
    return text


def _version(value):
    if not isinstance(value, str) or not re.fullmatch(r"1\.[0-9]{1,3}", value):
        raise GuestDaemonError("guest daemon API version is invalid")
    if int(value.split(".")[1]) < 41:
        raise GuestDaemonError("guest daemon requires API 1.41 or later")


@dataclass(frozen=True)
class GuestDaemonProfile(Record):
    schema: Literal["utility-guest-daemon-creation-profile-v1"]
    endpoint_digest: str
    api_version: str
    server_digest: str
    implementation: tuple[tuple[str, str], ...]
    engine_source_digest: str
    owner_python_digest: str

    def _validate(self):
        sha256(self.endpoint_digest)
        sha256(self.engine_source_digest)
        sha256(self.owner_python_digest)
        sha256(self.server_digest)
        _version(self.api_version)
        if tuple(name for name, _ in self.implementation) != SOURCES:
            raise ValueError("guest daemon source closure differs")
        for _, value in self.implementation:
            sha256(value)


def _line(io, limit):
    value = bytearray()
    while not value.endswith(b"\r\n"):
        if len(value) >= limit:
            raise GuestDaemonError("guest daemon HTTP chunk header exceeds bound")
        value.extend(io._exact(1))
    return bytes(value[:-2])


def _body(io, status, fields):
    if "content-encoding" in fields:
        raise GuestDaemonError("guest daemon encoded response is unsupported")
    length, encoding = fields.get("content-length"), fields.get("transfer-encoding")
    if length is not None and encoding is not None:
        raise GuestDaemonError("guest daemon response framing is ambiguous")
    if status == 204:
        if length not in (None, "0") or encoding is not None or io._wire:
            raise GuestDaemonError("guest daemon empty response contains data")
        return b""
    if encoding == "chunked":
        raw = bytearray()
        for _ in range(MAX_CHUNKS):
            line = _line(io, 128)
            if not re.fullmatch(rb"[0-9a-fA-F]{1,8}", line):
                raise GuestDaemonError("guest daemon chunk framing is invalid")
            size = int(line, 16)
            if len(raw) + size > MAX_JSON:
                raise GuestDaemonError("guest daemon JSON exceeds bound")
            if size == 0:
                if io._exact(2) != b"\r\n" or io._wire:
                    raise GuestDaemonError("guest daemon trailers or excess data are unsupported")
                return bytes(raw)
            raw.extend(io._exact(size))
            if io._exact(2) != b"\r\n":
                raise GuestDaemonError("guest daemon chunk terminator differs")
        raise GuestDaemonError("guest daemon chunk count exceeds bound")
    if encoding is not None or length is None or not re.fullmatch(r"[0-9]{1,10}", length):
        raise GuestDaemonError("guest daemon response lacks bounded HTTP framing")
    size = int(length)
    if size > MAX_JSON:
        raise GuestDaemonError("guest daemon JSON exceeds bound")
    raw = io._exact(size)
    if io._wire:
        raise GuestDaemonError("guest daemon response has excess prefetched data")
    return raw


class GuestDaemonAPI:
    """Fixed Unix JSON operations. Constructor opens no socket; requests never retry."""

    def __init__(self, socket_path, *, api_version, server_digest):
        self._socket_path = _endpoint(socket_path)
        _version(api_version)
        sha256(server_digest)
        self.profile = self._profile(api_version, server_digest)

    def _profile(self, version, server):
        return GuestDaemonProfile(
            "utility-guest-daemon-creation-profile-v1",
            digest(self._socket_path),
            version,
            server,
            tuple(
                (name, hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest())
                for name in SOURCES
            ),
            digest(
                [
                    (
                        str(path.relative_to(Path(__file__).parents[1])),
                        hashlib.sha256(path.read_bytes()).hexdigest(),
                    )
                    for path in sorted(Path(__file__).parents[1].rglob("*.py"))
                ]
            ),
            hashlib.sha256(sys.version.encode()).hexdigest(),
        )

    @property
    def identity(self):
        return self.profile.digest

    def _identity(self):
        if self._profile(self.profile.api_version, self.profile.server_digest) != self.profile:
            raise GuestDaemonError("guest daemon implementation or endpoint changed")

    def _request(self, method, path, value=None, *, deadline, cancelled=None):
        self._identity()
        # All paths below are fixed or assembled from validated immutable IDs.
        raw = b"" if value is None else canonical_json(value).encode()
        if len(raw) > MAX_JSON:
            raise GuestDaemonError("guest daemon request exceeds bound")
        request = (
            f"{method} /v{self.profile.api_version}{path} HTTP/1.1\r\n"
            "Host: localhost\r\nConnection: close\r\nContent-Type: application/json\r\n"
            f"Content-Length: {len(raw)}\r\n\r\n"
        ).encode("ascii") + raw
        stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        io = None
        try:
            io = GuestAttachSession(stream, deadline=deadline, cancelled=cancelled)
            io._check()
            try:
                stream.connect(self._socket_path)
            except OSError:
                io._check()
                raise GuestDaemonError("guest daemon connection outcome is unverified") from None
            io._send(request)
            status, fields = io._headers()
            return status, _body(io, status, fields)
        finally:
            if io is None:
                stream.close()
            else:
                io.close()

    def _json(self, method, path, value=None, *, expected=200, deadline, cancelled=None):
        status, raw = self._request(method, path, value, deadline=deadline, cancelled=cancelled)
        if status != expected:
            raise GuestDaemonError("guest daemon request outcome is unverified")
        try:
            result = unique_json(raw.decode())
        except (ValueError, UnicodeError, RecursionError):
            raise GuestDaemonError("guest daemon JSON projection is malformed") from None
        if not isinstance(result, dict):
            raise GuestDaemonError("guest daemon projection must be a mapping")
        return result

    def preflight(self, job, *, deadline, cancelled=None):
        self._identity()
        server = self._json("GET", "/version", deadline=deadline, cancelled=cancelled)
        if (
            digest(server) != self.profile.server_digest
            or server.get("ApiVersion") != self.profile.api_version
            or server.get("Os") != "linux"
        ):
            raise GuestDaemonError("guest daemon differs from pinned server/version")
        image = self._json(
            "GET", f"/images/{job.guest.image_id}/json", deadline=deadline, cancelled=cancelled
        )
        verify_image(image, job)
        return server, image

    def inspect(self, reference, *, named=False, deadline, cancelled=None):
        if named:
            if not isinstance(reference, str) or not re.fullmatch(r"[0-9a-f]{32}", reference):
                raise GuestDaemonError("guest daemon original name nonce differs")
            target = "ae-frozen-routing-" + reference
        else:
            sha256(reference)
            target = reference
        status, raw = self._request(
            "GET", f"/containers/{target}/json", deadline=deadline, cancelled=cancelled
        )
        if status == 404:
            return None
        if status != 200:
            raise GuestDaemonError("guest daemon container observation is unverified")
        try:
            value = unique_json(raw.decode())
        except (ValueError, UnicodeError, RecursionError):
            raise GuestDaemonError("guest daemon container projection is malformed") from None
        if not isinstance(value, dict):
            raise GuestDaemonError("guest daemon container projection must be a mapping")
        return value

    def _create(self, job, launch, *, deadline, cancelled=None):
        result = self._json(
            "POST",
            f"/containers/create?name={container_name(job)}&platform=linux%2Famd64",
            configuration(job, launch),
            expected=201,
            deadline=deadline,
            cancelled=cancelled,
        )
        return result


def verify_preflight_document(document, job, launch):
    """Validate original canonical producer projections, without daemon/source probes."""
    if not isinstance(document, dict) or set(document) != {
        "schema",
        "job",
        "launch",
        "profile",
        "server",
        "image",
        "named_absent",
    }:
        raise GuestDaemonError("guest daemon preflight projection is malformed")
    profile = GuestDaemonProfile.from_dict(document["profile"])
    if (
        document["schema"] != "utility-guest-daemon-preflight-v1"
        or document["job"] != job.digest
        or document["launch"] != launch.digest
        or profile.digest != launch.runtime_digest
        or document["named_absent"] is not True
        or not isinstance(document["server"], dict)
        or digest(document["server"]) != profile.server_digest
        or document["server"].get("ApiVersion") != profile.api_version
        or document["server"].get("Os") != "linux"
    ):
        raise GuestDaemonError("guest daemon preflight differs from original launch")
    verify_image(document["image"], job)
    return profile


def verify_creation_document(document, manifest, intent_digest, *, container_id=None):
    """Keep known response warnings distinct from a genuinely missing response."""
    if (
        not isinstance(document, dict)
        or set(document) != {"schema", "owner_digest", "create_intent_digest", "response"}
        or document["schema"] != "utility-guest-daemon-create-response-v1"
    ):
        raise GuestDaemonError("guest original create response projection is malformed")
    if (document["owner_digest"], document["create_intent_digest"]) != (
        manifest.digest,
        intent_digest,
    ):
        raise GuestDaemonError("guest original create response belongs to another intent")
    result = document["response"]
    if not isinstance(result, dict):
        raise GuestDaemonError("guest original create response must be a mapping")
    cid = result.get("Id", "")
    sha256(cid)
    if container_id is not None and cid != container_id:
        raise GuestDaemonError("guest create response belongs to another container")
    if result.get("Warnings") not in (None, []):
        raise GuestDaemonError("guest daemon created with unresolved warnings; do not start")
    return cid


def _creation_ref(owner):
    path = owner.root / "daemon-create-response.json"
    if path.is_symlink():
        raise GuestDaemonError("guest original create response pointer is invalid")
    if not path.exists():
        return None
    path = confined_file(owner.root, path.name)
    if path.stat().st_size > 65536:
        raise GuestDaemonError("guest original create response pointer exceeds bound")
    return ArtifactRef.from_json(path.read_text())


def _creation_document(owner, ref):
    return unique_json(read_bytes(owner.root, ref, max_bytes=2 * MAX_JSON).decode())


def _access(owner, store):
    if not owner._locked or not store._locked:
        raise GuestDaemonError("guest creation requires original suite and owner writers")
    owner._binding()
    job = owner.manifest.job
    if owner.suite_root != store.root or (job.source_digest, job.lock.sha256) != (
        store.spec.source_digest,
        store.spec.lock_digest,
    ):
        raise GuestDaemonError("guest creation differs from original suite scope")
    if not isinstance(owner.manifest.launch.policy, GuestStdinPolicy):
        raise GuestDaemonError("guest creation requires the fixed stdin policy")
    state = store.replay()
    if state["cancelled"]:
        raise GuestDaemonError("cancelled suite cannot create a guest")
    grant = job.grant
    validate_grant(store, grant, state["frozen"])
    attempt = "confirmation-" + grant.cell_digest[:48]
    allocation = state["attempts"].get(attempt)
    if (
        allocation is None
        or allocation[1] != "started"
        or attempt not in state["confirmation_accesses"]
    ):
        raise GuestDaemonError("guest creation lacks original charged access")
    event = allocation[0]
    if (event.phase, event.child_digest, event.resources) != (
        "confirmation",
        grant.digest,
        grant.resources,
    ):
        raise GuestDaemonError("guest creation differs from charged grant")
    m = owner.manifest
    return verify_guest_inputs(owner.root, job, m.launch, m.claim)


class GuestCreationController:
    """Wire preflight and one creation to the original owner journal.

    There is deliberately no start operation until the independent watchdog is
    implemented and qualified. Recovery observes an original creation only.
    """

    def __init__(self, api):
        self.api = api

    def create(self, owner, store, *, deadline, cancelled=None):
        cleanup = owner.root / "control/creation-cleanup"
        if cleanup.exists() or cleanup.is_symlink():
            raise GuestDaemonError("creation cleanup already intended; creation advance forbidden")
        _access(owner, store)
        m = owner.manifest
        if m.launch.runtime_digest != self.api.identity or owner.replay().phase != "ready":
            raise GuestDaemonError("guest creation identity changed or intent already consumed")
        server, image = self.api.preflight(m.job, deadline=deadline, cancelled=cancelled)
        if (
            self.api.inspect(m.job.nonce, named=True, deadline=deadline, cancelled=cancelled)
            is not None
        ):
            raise GuestDaemonError("guest original name already exists without creation intent")
        document = {
            "schema": "utility-guest-daemon-preflight-v1",
            "job": m.job.digest,
            "launch": m.launch.digest,
            "profile": self.api.profile.to_dict(),
            "server": server,
            "image": image,
            "named_absent": True,
        }
        verify_preflight_document(document, m.job, m.launch)
        ref = put_bytes(
            owner.root,
            canonical_json(document).encode(),
            name="daemon-preflight.json",
            media_type="application/json",
            producer="guest-daemon-owner",
        )
        owner.fault("daemon_preflight_saved")
        owner.record("create_intent", image, daemon_preflight=ref)
        owner.fault("before_daemon_create")
        result = self.api._create(m.job, m.launch, deadline=deadline, cancelled=cancelled)
        owner.fault("after_daemon_create")
        intent = owner.replay().events[0]
        capture = {
            "schema": "utility-guest-daemon-create-response-v1",
            "owner_digest": m.digest,
            "create_intent_digest": intent.digest,
            "response": result,
        }
        response_ref = put_bytes(
            owner.root,
            canonical_json(capture).encode(),
            name="daemon-create-response-record.json",
            media_type="application/json",
            producer="guest-daemon-owner",
        )
        durable_write(owner.root / "daemon-create-response.json", response_ref.to_json().encode())
        owner.fault("daemon_create_response_saved")
        cid = verify_creation_document(capture, m, intent.digest)
        created = self.api.inspect(cid, deadline=deadline, cancelled=cancelled)
        if created is None or created.get("Id") != cid:
            raise GuestDaemonError("guest original creation remains unobserved")
        owner.record("created", created, daemon_creation=response_ref)
        return cid

    def reconcile_creation(self, owner, store, *, deadline, cancelled=None):
        cleanup = owner.root / "control/creation-cleanup"
        if cleanup.exists() or cleanup.is_symlink():
            raise GuestDaemonError("creation cleanup already intended; creation advance forbidden")
        _access(owner, store)
        m = owner.manifest
        state = owner.replay()
        if m.launch.runtime_digest != self.api.identity or state.phase != "create_intent":
            raise GuestDaemonError("guest reconcile requires the original unresolved create intent")
        original = state.observations["create_intent"]
        if "daemon_preflight" not in original:
            raise GuestDaemonError("guest creation lacks original daemon preflight")
        response_ref = _creation_ref(owner)
        document = None if response_ref is None else _creation_document(owner, response_ref)
        if document is not None:
            verify_creation_document(document, m, state.events[0].digest)
        self.api.preflight(m.job, deadline=deadline, cancelled=cancelled)
        created = self.api.inspect(m.job.nonce, named=True, deadline=deadline, cancelled=cancelled)
        if created is None:
            raise GuestDaemonError("guest creation absence does not authorize another create")
        verify_created(created, m.job, m.launch)
        if document is not None:
            verify_creation_document(
                document, m, state.events[0].digest, container_id=created["Id"]
            )
        owner.record("created", created, daemon_creation=response_ref)
        return created["Id"]
