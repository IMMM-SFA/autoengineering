"""Candidate guest inference facade; no default scorer or runtime admission.

One original initialization owns the grant. Metadata reconciliation can finish
that initialization but cannot dispatch science. Recovery consumes only saved
observations/public archives. Synchronous filesystem I/O remains a qualification
limit; absolute checks prevent a late daemon launch after it returns.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import stat
import time
from typing import Literal
from uuid import uuid4

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import EventStore, StoreError, checked_directory, durable_write
from .contracts import sha256
from .guest_archive import archive_guest_dispatch, publisher_identity
from .guest_attach import GuestAttachCancelled, GuestAttachTimeout
from .guest_daemon import GuestCreationController
from .guest_dispatch import GuestDispatchController, reconcile_dispatch
from .guest_inputs import prepare_guest_inputs
from .guest_owner import GuestOwnerJournal, GuestOwnerManifest
from .guest_receipts import GuestLaunchIntent, GuestStdinPolicy, verify_guest_archive
from .inference_execution import FrozenRoutingExecutor, FrozenGuestInferenceJob
from .inference_guest import guest_executor_identity
from .scoring import CompositeConfirmationGrant, validate_grant

DIRECTORIES = ("events", "artifacts", "children", "attempts", "control", "reports")


@dataclass(frozen=True)
class GuestExecutorRegistration(Record):
    schema: Literal["utility-guest-executor-registration-v1"]
    executor_digest: str
    source_digest: str
    lock_digest: str
    guest_digest: str
    environment_digest: str
    runtime_digest: str
    publisher_digest: str
    policy_digest: str
    implementation_digest: str
    boundary: Literal["unqualified-candidate"] = "unqualified-candidate"

    def _validate(self):
        for name, value in self.to_dict().items():
            if name.endswith("_digest"):
                sha256(value)


@dataclass(frozen=True)
class GuestExecutorInitialization(Record):
    schema: Literal["utility-guest-executor-initialization-v1"]
    suite_digest: str
    registration: GuestExecutorRegistration
    owner: GuestOwnerManifest
    began_at: float
    deadline: float

    def _validate(self):
        sha256(self.suite_digest)
        job, launch = self.owner.job, self.owner.launch
        r = self.registration
        if (
            (
                r.executor_digest,
                r.source_digest,
                r.lock_digest,
                r.guest_digest,
                r.environment_digest,
            )
            != (
                job.executor_digest,
                job.source_digest,
                job.lock.sha256,
                job.guest.digest,
                job.environment.sha256,
            )
            or r.runtime_digest != launch.runtime_digest
            or r.policy_digest != launch.policy.digest
            or not 0 < self.deadline - self.began_at <= job.grant.inference.timeout_seconds
        ):
            raise ValueError("guest initialization differs from original registration/deadline")


def _exact(root, relative, raw, *, limit=4 * 1024 * 1024):
    path = root / relative
    if path.exists() or path.is_symlink():
        file = confined_file(root, relative)
        if file.stat().st_size > limit or file.read_bytes() != raw:
            raise StoreError("guest initialization original metadata differs")
    else:
        durable_write(path, raw)


def _claim_body(job):
    return canonical_json(
        {
            "grant": job.grant.digest,
            "executor": job.executor_digest,
            "nonce": job.nonce,
            "job": job.digest,
            "scope": job.claim_scope(None),
        }
    ).encode()


class GuestRoutingExecutor(FrozenRoutingExecutor):
    """Fixed supplied worker through the original charged two-stage grant."""

    def __init__(
        self,
        store,
        source_root,
        driver_root,
        work_root,
        *,
        sources,
        lock,
        guest,
        environment,
        api,
        publisher_digest,
    ):
        super().__init__(store, source_root, driver_root, work_root, sources=sources, lock=lock)
        self.guest, self.environment, self.api = guest, environment, api
        self.identity = guest_executor_identity(store.spec.source_digest, lock.sha256, guest)
        sha256(publisher_digest)
        self.publisher_digest = publisher_digest
        guest.validate_environment(
            unique_json(read_bytes(store.root, environment, max_bytes=4 * 1024 * 1024).decode())
        )
        self.registration = self._registration()
        self._recovery_only = False

    @classmethod
    def for_recovery(cls, store, grant, work_root):
        """Open original metadata without live code/driver/API construction.

        This object cannot execute. Public completion needs no original work
        directory. Private reconciliation still enforces its original scope.
        """
        if not isinstance(grant, CompositeConfirmationGrant):
            raise StoreError("guest recovery requires original composite grant")
        path = confined_file(store.root, f"guest-executor-inits/{grant.digest}.json")
        if path.stat().st_size > 4 * 1024 * 1024:
            raise StoreError("guest initialization exceeds bound")
        value = GuestExecutorInitialization.from_json(path.read_text())
        if (
            value.suite_digest != store.spec.digest
            or value.owner.job.grant != grant
            or (value.registration.source_digest, value.registration.lock_digest)
            != (store.spec.source_digest, store.spec.lock_digest)
        ):
            raise StoreError("guest recovery registration differs from original suite/grant")
        instance = cls.__new__(cls)
        instance.store = store
        instance.source_root = instance.driver_root = instance.api = None
        instance.work_root = Path(work_root).absolute()
        instance.sources = value.owner.job.sources
        instance.lock = value.owner.job.lock
        instance.guest = value.owner.job.guest
        instance.environment = value.owner.job.environment
        instance.identity = value.registration.executor_digest
        instance.publisher_digest = value.registration.publisher_digest
        instance.registration = value.registration
        instance._recovery_only = True
        instance._charged(grant, recovery=True)
        return instance

    def _registration(self):
        return GuestExecutorRegistration(
            "utility-guest-executor-registration-v1",
            self.identity,
            self.store.spec.source_digest,
            self.lock.sha256,
            self.guest.digest,
            self.environment.sha256,
            self.api.identity,
            self.publisher_digest,
            GuestStdinPolicy().digest,
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        )

    def _paths(self, grant):
        directory = self.store.root / "guest-executor-inits"
        return directory / (grant.digest + ".json"), directory / (grant.digest + ".complete.json")

    def _charged(self, grant, *, recovery):
        if not isinstance(grant, CompositeConfirmationGrant):
            raise StoreError("guest executor requires the original composite grant")
        state = self.store.replay()
        if state["cancelled"] and not recovery:
            raise StoreError("cancelled suite cannot start guest inference")
        validate_grant(self.store, grant, state["frozen"])
        attempt = "confirmation-" + grant.cell_digest[:48]
        allocation = state["attempts"].get(attempt)
        if (
            allocation is None
            or allocation[1] not in ("started", "finished")
            or attempt not in state["confirmation_accesses"]
        ):
            raise StoreError("guest executor lacks original charged access")
        event = allocation[0]
        if (event.phase, event.child_digest, event.resources) != (
            "confirmation",
            grant.digest,
            grant.resources,
        ):
            raise StoreError("guest executor differs from original charged grant")

    def _read_initialization(self, grant):
        path, _ = self._paths(grant)
        raw = confined_file(self.store.root, str(path.relative_to(self.store.root)))
        if raw.stat().st_size > 4 * 1024 * 1024:
            raise StoreError("guest initialization exceeds bound")
        value = GuestExecutorInitialization.from_json(raw.read_text())
        if (
            value.suite_digest != self.store.spec.digest
            or value.registration != self.registration
            or value.owner.job.grant != grant
            or value.owner.owner_scope != digest(str(self.work_root / grant.digest))
        ):
            raise StoreError("guest initialization differs from original grant/owner/registration")
        return value

    def reconcile_initialization(self, grant):
        """Finish matching original metadata only; no drivers, APIs or new clocks."""
        if not self.store._locked:
            raise StoreError("guest initialization requires original suite writer")
        self._charged(grant, recovery=True)
        value = self._read_initialization(grant)
        m = value.owner
        root = self.work_root / grant.digest
        checked_directory(self.work_root)
        _, marker = self._paths(grant)
        completion = canonical_json(
            {"initialization_digest": value.digest, "owner_digest": m.digest}
        ).encode()
        if marker.exists() or marker.is_symlink():
            _exact(self.store.root, str(marker.relative_to(self.store.root)), completion)
            owner = GuestOwnerJournal(
                root, suite_root=self.store.root, expected=m, fault=self.store.fault
            )
            owner._binding()
            return owner
        if read_bytes(self.store.root, m.claim, max_bytes=65536) != _claim_body(m.job):
            raise StoreError("guest initialization original claim differs")
        for directory, name, raw in (
            ("inference-claims", grant.digest + ".json", m.claim.to_json().encode()),
            ("inference-owners", grant.digest + ".json", m.to_json().encode()),
        ):
            folder = self.store.root / directory
            folder.mkdir(mode=0o700, exist_ok=True)
            checked_directory(folder)
            _exact(self.store.root, str((folder / name).relative_to(self.store.root)), raw)
            self.store.fault("guest_executor_" + directory + "_published")
        if not root.exists():
            root.mkdir(mode=0o700)
        checked_directory(root)
        if (root / "owner.json").exists() or (root / "owner.json").is_symlink():
            owner = GuestOwnerJournal(
                root, suite_root=self.store.root, expected=m, fault=self.store.fault
            )
            with owner.writer():
                if owner.replay().phase != "ready" or any(
                    (root / name).exists() or (root / name).is_symlink()
                    for name in ("input-intent.json", "input-package.json")
                ):
                    raise StoreError("guest owner advanced without original initialization marker")
                _exact(self.store.root, str(marker.relative_to(self.store.root)), completion)
            return owner
        # Only known empty initialization directories and original claim bytes may
        # be completed. Unknown files/events are not erased or reset to ready.
        allowed = {root / name for name in DIRECTORIES}
        claim_path = root / m.claim.path
        for path in root.rglob("*"):
            if path.is_symlink():
                raise StoreError("guest partial initialization contains a symlink")
            if path.is_dir():
                checked_directory(path)
                if path not in allowed and path not in claim_path.parents:
                    raise StoreError("guest partial initialization contains an unknown directory")
            elif path == root / ".campaign.lock":
                metadata = path.stat()
                if (
                    not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_uid != root.stat().st_uid
                    or stat.S_IMODE(metadata.st_mode) & 0o077
                    or metadata.st_size != 0
                ):
                    raise StoreError("guest partial initialization contains an invalid lock")
            elif path != claim_path:
                raise StoreError("guest partial initialization contains unverified files/events")
        for name in DIRECTORIES:
            (root / name).mkdir(mode=0o700, exist_ok=True)
            checked_directory(root / name)
        base = EventStore(root)
        with base.writer():
            saved = put_bytes(
                root,
                read_bytes(self.store.root, m.claim),
                name=Path(m.claim.path).name,
                media_type="application/json",
                producer="guest-owner",
            )
            if saved.sha256 != m.claim.sha256:
                raise StoreError("guest initialized claim differs")
            self.store.fault("guest_executor_owner_claim_copied")
            _exact(root, "owner.json", m.to_json().encode())
            self.store.fault("guest_executor_owner_manifest_saved")
            _exact(self.store.root, str(marker.relative_to(self.store.root)), completion)
        owner = GuestOwnerJournal(
            root, suite_root=self.store.root, expected=m, fault=self.store.fault
        )
        owner._binding()
        return owner

    def _archive_arguments(self):
        return dict(
            source_digest=self.registration.source_digest,
            lock_digest=self.registration.lock_digest,
            executor_digest=self.identity,
            runtime_digest=self.registration.runtime_digest,
            publisher_digest=self.registration.publisher_digest,
        )

    def archive(self, grant):
        """Read the original public pointer; no private workspace or runtime probe."""
        self._charged(grant, recovery=True)
        path = confined_file(self.store.root, f"guest-inference-archives/{grant.digest}.json")
        if path.stat().st_size > 65536:
            raise StoreError("guest inference archive pointer exceeds bound")
        ref = ArtifactRef.from_json(path.read_text())
        verify_guest_archive(self.store.root, ref, grant, **self._archive_arguments())
        return ref

    def recover(self, grant):
        """Recover saved proof only. An incomplete stage never dispatches again."""
        path = self.store.root / "guest-inference-archives" / (grant.digest + ".json")
        if path.exists() or path.is_symlink():
            ref = self.archive(grant)
            return verify_guest_archive(self.store.root, ref, grant, **self._archive_arguments())
        if not self.store._locked:
            raise StoreError("guest recovery requires original suite writer")
        owner = self.reconcile_initialization(grant)
        with owner.writer():
            if not (owner.root / "control/guest-dispatch").is_dir():
                raise StoreError("guest preparation/creation incomplete; new dispatch forbidden")
            result = reconcile_dispatch(owner)
            if result.journal_phase != "cleaned":
                raise StoreError("original guest lifecycle incomplete; new dispatch forbidden")
            ref = archive_guest_dispatch(owner, self.store, publisher_digest=self.publisher_digest)
        return verify_guest_archive(self.store.root, ref, grant, **self._archive_arguments())

    def cleanup_creation(self, grant):
        """Explicit original-resource cleanup, independent of cancellation."""
        if self.api is None:
            raise StoreError(
                "creation cleanup requires the original live API, not recovery-only mode"
            )
        if not self.store._locked:
            raise StoreError("creation cleanup requires original suite writer")
        from .guest_creation_cleanup import cleanup_creation

        owner = self.reconcile_initialization(grant)
        with owner.writer():
            return cleanup_creation(owner, self.store, self.api)

    def cleanup_watchdog_startup(self, grant):
        """Resolve original interrupted arming without a new worker or dispatch."""
        if self.api is None or not self.store._locked:
            raise StoreError("watchdog startup cleanup requires original API and suite writer")
        from .guest_watchdog import reconcile_startup_cleanup

        owner = self.reconcile_initialization(grant)
        with owner.writer():
            return reconcile_startup_cleanup(owner, self.store, self.api)

    def execute(self, grant, *, cancelled=None):
        if self._recovery_only:
            raise StoreError("recovery-only guest executor cannot dispatch")
        if not self.store._locked:
            raise StoreError("guest execution requires original suite writer")
        if not isinstance(grant, CompositeConfirmationGrant):
            raise StoreError("guest executor requires composite grant")
        path, marker = self._paths(grant)
        if path.exists() or path.is_symlink() or marker.exists() or marker.is_symlink():
            raise StoreError(
                "guest attempt already intended; explicit saved-evidence recovery only"
            )
        for name in ("inference-claims", "inference-owners"):
            directory = self.store.root / name
            if directory.exists() or directory.is_symlink():
                checked_directory(directory)
                existing = directory / (grant.digest + ".json")
                if existing.exists() or existing.is_symlink():
                    raise StoreError("guest grant already claimed; new initialization forbidden")
        began = time.monotonic()
        deadline = began + grant.inference.timeout_seconds
        events = tuple(sorted(p.name for p in self.store.events_path.iterdir()))
        is_cancelled = False

        def cancellation():
            nonlocal events, is_cancelled
            value = False if cancelled is None else cancelled()
            if type(value) is not bool:
                raise StoreError("guest executor cancellation state is invalid")
            current = tuple(sorted(p.name for p in self.store.events_path.iterdir()))
            if current != events:
                is_cancelled = self.store.replay()["cancelled"]
                events = current
            return value or is_cancelled

        def check():
            if cancellation():
                raise GuestAttachCancelled("guest executor cancelled")
            if time.monotonic() >= deadline:
                raise GuestAttachTimeout("guest executor original deadline expired")

        check()
        self._charged(grant, recovery=False)
        self._preflight(grant)
        if (
            self.registration != self._registration()
            or self.publisher_digest != publisher_identity()
        ):
            raise StoreError("guest executor/publisher registration changed")
        self.api._identity()
        self.guest.validate_environment(
            unique_json(
                read_bytes(self.store.root, self.environment, max_bytes=4 * 1024 * 1024).decode()
            )
        )
        check()
        root = self.work_root / grant.digest
        if root.exists() or root.is_symlink():
            raise StoreError("guest original work directory already exists")
        original = grant.inference.forcing.artifact
        staged = ArtifactRef(
            f"artifacts/{original.sha256}/drivers.npz",
            original.sha256,
            original.size_bytes,
            "application/x-npz",
            "inference",
            {},
        )
        job = FrozenGuestInferenceJob(
            "utility-frozen-inference-job-v2",
            grant,
            self.identity,
            self.store.spec.source_digest,
            self.sources,
            self.lock,
            uuid4().hex,
            staged,
            self.guest,
            self.environment,
        )
        claim = put_bytes(
            self.store.root,
            _claim_body(job),
            name="inference-claim.json",
            media_type="application/json",
            producer="trusted-inference",
        )
        launch = GuestLaunchIntent(
            "utility-guest-launch-intent-v1",
            job.digest,
            grant.digest,
            self.identity,
            self.registration.runtime_digest,
            claim.sha256,
            job.nonce,
            self.guest.image_id,
            grant.inference.timeout_seconds,
            GuestStdinPolicy(),
        )
        initialization = GuestExecutorInitialization(
            "utility-guest-executor-initialization-v1",
            self.store.spec.digest,
            self.registration,
            GuestOwnerManifest("utility-guest-owner-v1", job, launch, claim, digest(str(root))),
            began,
            deadline,
        )
        path.parent.mkdir(mode=0o700, exist_ok=True)
        checked_directory(path.parent)
        durable_write(path, initialization.to_json().encode())
        self.store.fault("guest_executor_init_intended")
        owner = self.reconcile_initialization(grant)
        self.store.fault("guest_executor_owner_ready")
        with owner.writer():
            check()
            prepare_guest_inputs(owner, self.store, self.source_root, self.driver_root, check=check)
            self.store.fault("guest_executor_inputs_ready")
            check()
            try:
                GuestCreationController(self.api).create(
                    owner, self.store, deadline=deadline, cancelled=cancellation
                )
                self.store.fault("guest_executor_created")
                check()
                GuestDispatchController(self.api).run(
                    owner, self.store, deadline=deadline, cancelled=cancellation
                )
                self.store.fault("guest_executor_dispatched")
                ref = archive_guest_dispatch(
                    owner, self.store, publisher_digest=self.publisher_digest
                )
            except BaseException:
                # Resolve only original cleanup authority. A live watchdog lease
                # refuses takeover. Preserve the original error and all charges.
                try:
                    if owner.replay().phase in ("create_intent", "created"):
                        if (owner.root / "control/guest-watchdog").exists():
                            from .guest_watchdog import reconcile_startup_cleanup

                            reconcile_startup_cleanup(owner, self.store, self.api)
                        else:
                            from .guest_creation_cleanup import cleanup_creation

                            cleanup_creation(owner, self.store, self.api)
                except BaseException:
                    pass
                raise
        return verify_guest_archive(self.store.root, ref, grant, **self._archive_arguments())
