"""Durable candidate guest owner intents and original observations.

This journal performs no daemon operation or input staging. An intent is a charged,
possibly executed transition, not a reusable launch permission. A future launcher
must dispatch once immediately after committing it under the same owner lock. This
module alone grants no execution authority or qualified runtime admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import EventStore, StoreError, checked_directory, durable_write
from .contracts import sha256
from .guest_observations import (
    _launch,
    configuration,
    project_lifecycle,
    project_observations,
    verify_created,
    verify_image,
    verify_started,
)
from .guest_receipts import GuestLaunchIntent
from .inference_execution import FrozenGuestInferenceJob

OPERATIONS = (
    "create_intent",
    "created",
    "start_intent",
    "started",
    "stopped",
    "cleanup_intent",
    "cleaned",
)


@dataclass(frozen=True)
class GuestOwnerManifest(Record):
    schema: Literal["utility-guest-owner-v1"]
    job: FrozenGuestInferenceJob
    launch: GuestLaunchIntent
    claim: ArtifactRef
    owner_scope: str

    def _validate(self):
        _launch(self.job, self.launch)
        sha256(self.owner_scope)
        if self.launch.claim_digest != self.claim.sha256:
            raise ValueError("guest owner claim differs from launch")


@dataclass(frozen=True)
class GuestOwnerEvent(Record):
    sequence: int
    previous: str | None
    owner_digest: str
    operation: Literal[
        "create_intent",
        "created",
        "start_intent",
        "started",
        "stopped",
        "cleanup_intent",
        "cleaned",
    ]
    observation: ArtifactRef | None
    input_package_digest: str | None = None
    daemon_creation: ArtifactRef | None = None
    dispatch: ArtifactRef | None = None

    def to_dict(self):
        value = super().to_dict()
        if self.input_package_digest is None:
            value.pop("input_package_digest")
        if self.daemon_creation is None:
            value.pop("daemon_creation")
        if self.dispatch is None:
            value.pop("dispatch")
        return value

    def _validate(self):
        if self.dispatch is not None and self.operation != "start_intent":
            raise ValueError("guest dispatch belongs only to the original start intent")
        if self.daemon_creation is not None and self.operation != "created":
            raise ValueError("daemon creation response belongs only to original creation")
        if self.input_package_digest is not None:
            sha256(self.input_package_digest)
            if self.operation != "start_intent":
                raise ValueError("guest inputs may bind only the original start intent")
        if self.sequence < 1:
            raise ValueError("guest owner sequence must be positive")
        sha256(self.owner_digest)
        if self.previous is not None:
            sha256(self.previous)
        if (self.operation in ("start_intent", "cleanup_intent")) != (self.observation is None):
            raise ValueError("guest owner observation does not match transition")


@dataclass(frozen=True)
class GuestOwnerProjection:
    events: tuple[GuestOwnerEvent, ...]
    phase: str
    create_uncertain: bool
    start_uncertain: bool
    observations: dict
    input_package_digest: str | None = None


class GuestOwnerJournal(EventStore):
    """One suite-bound owner, create-only commits and read-only recovery.

    Reopening cannot reissue an intent. Missing observations stay uncertain and
    their charge cannot be refunded here. A relocated copy supports replay only.
    """

    @classmethod
    def create(cls, root, job, launch, *, suite_root, claim, fault=None):
        suite_root = checked_directory(suite_root)
        _launch(job, launch)
        original = ArtifactRef.from_json(
            confined_file(suite_root, f"inference-claims/{job.grant.digest}.json").read_text()
        )
        if original != claim or launch.claim_digest != claim.sha256:
            raise StoreError("guest owner requires original suite claim")
        value = unique_json(read_bytes(suite_root, claim, max_bytes=65536).decode())
        if value != {
            "grant": job.grant.digest,
            "executor": job.executor_digest,
            "nonce": job.nonce,
            "job": job.digest,
            "scope": job.claim_scope(None),
        }:
            raise StoreError("guest owner claim binding differs")
        # The owner lease precedes initialization; interrupted initialization does
        # not release the grant or authorize a second owner directory.
        scope = digest(str(Path(root).absolute()))
        manifest = GuestOwnerManifest("utility-guest-owner-v1", job, launch, claim, scope)
        directory = suite_root / "inference-owners"
        directory.mkdir(mode=0o700, exist_ok=True)
        checked_directory(directory)
        try:
            durable_write(directory / f"{job.grant.digest}.json", manifest.to_json().encode())
        except FileExistsError:
            raise StoreError(
                "guest grant already has an owner; explicit recovery required"
            ) from None
        if fault:
            fault("after_owner_claim")
        base = EventStore.create(root)
        put_bytes(
            base.root,
            read_bytes(suite_root, claim),
            name=Path(claim.path).name,
            media_type="application/json",
            producer="guest-owner",
        )
        durable_write(base.root / "owner.json", manifest.to_json().encode())
        return cls(base.root, suite_root=suite_root, expected=manifest, fault=fault)

    def __init__(self, root, *, suite_root=None, expected=None, fault=None):
        super().__init__(root, fault=fault)
        path = confined_file(self.root, "owner.json")
        if path.stat().st_size > 4 * 1024 * 1024:
            raise StoreError("guest owner manifest exceeds limit")
        self.manifest = GuestOwnerManifest.from_json(path.read_text())
        if expected is not None and self.manifest != expected:
            raise StoreError("guest owner identity changed")
        self.suite_root = checked_directory(suite_root) if suite_root is not None else None

    def _binding(self):
        if self.suite_root is None or digest(str(self.root)) != self.manifest.owner_scope:
            raise StoreError("guest owner replay copy cannot write or dispatch")
        raw = confined_file(
            self.suite_root, f"inference-owners/{self.manifest.job.grant.digest}.json"
        ).read_text()
        if raw != self.manifest.to_json():
            raise StoreError("guest owner differs from original suite owner lease")
        original = ArtifactRef.from_json(
            confined_file(
                self.suite_root, f"inference-claims/{self.manifest.job.grant.digest}.json"
            ).read_text()
        )
        if original != self.manifest.claim:
            raise StoreError("guest owner original suite claim changed")
        read_bytes(self.suite_root, original, max_bytes=65536)

    def _validate_observations(self, observations):
        job, launch = self.manifest.job, self.manifest.launch
        if "create_intent" in observations:
            value = observations["create_intent"]
            if not isinstance(value, dict) or set(value) not in (
                {"image", "request"},
                {"image", "request", "daemon_preflight"},
            ):
                raise StoreError("guest owner create intent is malformed")
            if "daemon_preflight" in value:
                from .guest_daemon import verify_preflight_document

                ref = ArtifactRef.from_dict(value["daemon_preflight"])
                document = unique_json(
                    read_bytes(self.root, ref, max_bytes=2 * 1024 * 1024).decode()
                )
                verify_preflight_document(document, job, launch)
                if digest(document["image"]) != digest(value["image"]):
                    raise StoreError("guest owner image differs from original daemon preflight")
            verify_image(value["image"], job)
            if canonical_json(value["request"]) != canonical_json(configuration(job, launch)):
                raise StoreError("guest owner create request changed")
        if "created" in observations:
            verify_created(observations["created"], job, launch)
        if "started" in observations:
            verify_started(observations["started"], job, launch)
            if observations["started"]["Id"] != observations["created"]["Id"]:
                raise StoreError("guest owner start belongs to another container")
        if "stopped" in observations:
            stop = observations["stopped"]
            if not isinstance(stop, dict) or set(stop) != {"inspect", "elapsed_seconds", "reason"}:
                raise StoreError("guest owner stop evidence is malformed")
            project_lifecycle(
                job,
                launch,
                image=observations["create_intent"]["image"],
                created=observations["created"],
                started=observations["started"],
                stopped=stop["inspect"],
                elapsed_seconds=stop["elapsed_seconds"],
                reason=stop["reason"],
            )
        if "cleaned" in observations:
            self._project(observations)

    def _project(self, observations):
        stop = observations["stopped"]
        return project_observations(
            self.manifest.job,
            self.manifest.launch,
            image=observations["create_intent"]["image"],
            created=observations["created"],
            started=observations["started"],
            stopped=stop["inspect"],
            cleanup=observations["cleaned"],
            elapsed_seconds=stop["elapsed_seconds"],
            reason=stop["reason"],
        )

    def replay(self):
        job = self.manifest.job
        claim = unique_json(read_bytes(self.root, self.manifest.claim, max_bytes=65536).decode())
        if claim != {
            "grant": job.grant.digest,
            "executor": job.executor_digest,
            "nonce": job.nonce,
            "job": job.digest,
            "scope": job.claim_scope(None),
        }:
            raise StoreError("guest owner saved claim binding differs")
        events, observations, head = [], {}, None
        input_package_digest = None
        files = []
        for path in self.events_path.iterdir():
            if path.name.startswith(".") and path.name.endswith(".tmp"):
                continue
            if path.name not in {f"{n:012d}.json" for n in range(1, len(OPERATIONS) + 1)}:
                raise StoreError("unexpected guest owner event file")
            files.append(path)
        for sequence, path in enumerate(sorted(files), 1):
            if path.name != f"{sequence:012d}.json":
                raise StoreError("guest owner event sequence has a gap")
            path = confined_file(self.root, str(path.relative_to(self.root)))
            if path.stat().st_size > 65536:
                raise StoreError("guest owner event exceeds limit")
            raw = path.read_text()
            envelope = unique_json(raw)
            if not isinstance(envelope, dict) or set(envelope) != {"event", "sha256"}:
                raise StoreError("guest owner event envelope differs")
            event = GuestOwnerEvent.from_dict(envelope["event"])
            if (
                event.sequence != sequence
                or event.previous != head
                or event.owner_digest != self.manifest.digest
                or event.operation != OPERATIONS[sequence - 1]
                or envelope["sha256"] != event.digest
                or raw != canonical_json(envelope) + "\n"
            ):
                raise StoreError("guest owner event identity/order differs")
            if event.observation is not None:
                observations[event.operation] = unique_json(
                    read_bytes(self.root, event.observation, max_bytes=1024 * 1024).decode()
                )
            if event.daemon_creation is not None:
                from .guest_daemon import verify_creation_document

                document = unique_json(
                    read_bytes(self.root, event.daemon_creation, max_bytes=2 * 1024 * 1024).decode()
                )
                verify_creation_document(
                    document,
                    self.manifest,
                    events[0].digest,
                    container_id=observations["created"]["Id"],
                )
            if event.dispatch is not None:
                from .guest_dispatch import verify_dispatch_document

                document = unique_json(
                    read_bytes(self.root, event.dispatch, max_bytes=65536).decode()
                )
                verify_dispatch_document(self, document, observations["created"]["Id"])
            if event.input_package_digest is not None:
                from .guest_inputs import verify_guest_inputs

                manifest = self.manifest
                package = verify_guest_inputs(
                    self.root, manifest.job, manifest.launch, manifest.claim
                )
                if package.digest != event.input_package_digest:
                    raise StoreError("guest owner input package differs from original start intent")
                input_package_digest = package.digest
            events.append(event)
            head = event.digest
        self._validate_observations(observations)
        phase = events[-1].operation if events else "ready"
        return GuestOwnerProjection(
            tuple(events),
            phase,
            phase == "create_intent",
            phase == "start_intent",
            observations,
            input_package_digest,
        )

    def record(
        self,
        operation,
        observation=None,
        *,
        daemon_preflight=None,
        daemon_creation=None,
        dispatch=None,
    ):
        """Commit before external side effects; never repeat a consumed transition.

        The owner must retain the writer lock across intent and actual dispatch.
        This method does not execute the external operation or prove it occurred.
        """
        if not self._locked:
            raise StoreError("guest owner transition requires the writer lock")
        self._binding()
        cleanup = self.root / "control/creation-cleanup"
        if cleanup.exists() or cleanup.is_symlink():
            raise StoreError("creation cleanup already intended; journal advance forbidden")
        if operation == "start_intent" and any(
            (self.root / "control/guest-watchdog" / name).exists()
            or (self.root / "control/guest-watchdog" / name).is_symlink()
            for name in ("cleanup-window.json", "outcome.json")
        ):
            raise StoreError("watchdog cleanup already intended; start authority refused")
        current = self.replay()
        index = len(current.events)
        if index >= len(OPERATIONS) or operation != OPERATIONS[index]:
            raise StoreError("guest owner transition already consumed or out of order")
        if daemon_preflight is not None and operation != "create_intent":
            raise StoreError("daemon preflight belongs only to the original create intent")
        if operation == "create_intent":
            observation = {
                "image": observation,
                "request": configuration(self.manifest.job, self.manifest.launch),
            }
            if daemon_preflight is not None:
                observation["daemon_preflight"] = daemon_preflight.to_dict()
        if (operation in ("start_intent", "cleanup_intent")) != (observation is None):
            raise StoreError("guest owner transition observation differs")
        observations = dict(current.observations)
        if observation is not None:
            # Copy and canonicalize before committing any mutable caller data.
            raw = canonical_json(observation)
            if len(raw.encode()) > 1024 * 1024:
                raise StoreError("guest owner observation exceeds limit")
            observation = unique_json(raw)
            observations[operation] = observation
        self._validate_observations(observations)
        ref = None
        if observation is not None:
            ref = put_bytes(
                self.root,
                canonical_json(observation).encode(),
                name=operation + ".json",
                media_type="application/json",
                producer="guest-owner",
            )
        if daemon_creation is not None:
            from .guest_daemon import verify_creation_document

            if operation != "created":
                raise StoreError("daemon creation response belongs only to original creation")
            document = unique_json(
                read_bytes(self.root, daemon_creation, max_bytes=2 * 1024 * 1024).decode()
            )
            verify_creation_document(
                document, self.manifest, current.events[0].digest, container_id=observation["Id"]
            )
        if dispatch is not None:
            from .guest_dispatch import verify_dispatch_document

            if operation != "start_intent":
                raise StoreError("guest dispatch belongs only to original start intent")
            document = unique_json(read_bytes(self.root, dispatch, max_bytes=65536).decode())
            verify_dispatch_document(self, document, observations["created"]["Id"])
        input_package_digest = None
        input_intent = self.root / "input-intent.json"
        input_manifest = self.root / "input-package.json"
        if operation == "start_intent" and (
            input_intent.exists()
            or input_intent.is_symlink()
            or input_manifest.exists()
            or input_manifest.is_symlink()
        ):
            from .guest_inputs import verify_guest_inputs

            manifest = self.manifest
            input_package_digest = verify_guest_inputs(
                self.root, manifest.job, manifest.launch, manifest.claim
            ).digest
        event = GuestOwnerEvent(
            index + 1,
            current.events[-1].digest if index else None,
            self.manifest.digest,
            operation,
            ref,
            input_package_digest,
            daemon_creation,
            dispatch,
        )
        self.fault("before_" + operation)
        durable_write(
            self.events_path / f"{event.sequence:012d}.json",
            (canonical_json({"event": event.to_dict(), "sha256": event.digest}) + "\n").encode(),
        )
        self.fault("after_" + operation)
        return self.replay()

    def projections(self):
        """Recover original completed evidence without a daemon, model or new clock."""
        current = self.replay()
        if current.phase != "cleaned":
            raise StoreError("guest owner lifecycle is incomplete; replay cannot retry it")
        return self._project(current.observations)
