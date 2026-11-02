"""Durable shared allowances for a serial, explicitly selected execution batch.

Reservations are permanent charges, not evidence that a process actually ran.
Only trusted runners provide physical observations. This module never launches
work, reads credentials, chooses a model or grants execution authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import stat
import time
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef, identifier, sha256, unique
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError, WriterBusy, checked_directory, durable_write

from .identity import host_environment_identity, host_source_identity
from .records import AgentRecord, HostCapabilities, HostSelection, ResourceLimits


@dataclass(frozen=True)
class BatchCase(AgentRecord):
    id: str
    kind: Literal["text", "roles", "timeout", "cancel", "owner_loss", "malformed", "comparison"]
    configuration_digest: str
    host_invocations: int
    scientific_starts: int

    def _validate(self):
        identifier(self.id)
        sha256(self.configuration_digest)
        if self.host_invocations < 0 or self.scientific_starts < 0:
            raise ValueError("case allowances must be nonnegative")
        if self.host_invocations + self.scientific_starts == 0:
            raise ValueError("case requires a physical allowance")


@dataclass(frozen=True)
class BatchSpec(AgentRecord):
    schema_version: Literal["1.0"]
    id: str
    source_identity: str
    environment_identity: str
    host: HostSelection
    capabilities: HostCapabilities
    host_configuration_digest: str
    limits: ResourceLimits
    scientific_starts: int
    cases: tuple[BatchCase, ...]

    @classmethod
    def from_file(cls, filename):
        with Path(filename).open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("batch specification exceeds 64 KiB")
        return cls.from_json(raw.decode())

    def _validate(self):
        identifier(self.id)
        for value in (
            self.source_identity,
            self.environment_identity,
            self.host_configuration_digest,
        ):
            sha256(value)
        if (
            self.capabilities.host,
            self.capabilities.auth_mode,
            self.capabilities.adapter_version,
            self.capabilities.boundary_identity if self.host.adapter_version == "2.1" else None,
        ) != (
            self.host.kind,
            self.host.auth_mode,
            self.host.adapter_version,
            self.host.qualification_digest,
        ):
            raise ValueError("batch capability differs from selected host")
        unique([case.id for case in self.cases], "batch case")
        if (
            not 1 <= len(self.cases) <= 32
            or self.scientific_starts < 0
            or sum(case.host_invocations for case in self.cases) > self.limits.max_invocations
            or sum(case.scientific_starts for case in self.cases) > self.scientific_starts
        ):
            raise ValueError("batch cases exceed the frozen aggregate allowance")


@dataclass(frozen=True)
class CaseStarted(AgentRecord):
    case_id: str
    configuration_digest: str
    recorded_at: float

    def _validate(self):
        identifier(self.case_id)
        sha256(self.configuration_digest)


@dataclass(frozen=True)
class PhysicalReservation(AgentRecord):
    id: str
    case_id: str
    resource: Literal["host", "science"]
    invocation_digest: str
    task_id: str | None
    recorded_at: float
    timeout_seconds: float
    prompt_bytes: int
    output_limit: int
    workspace_bytes: int

    def _validate(self):
        identifier(self.id)
        identifier(self.case_id)
        sha256(self.invocation_digest)
        if self.timeout_seconds <= 0 or any(
            v < 0 for v in (self.prompt_bytes, self.output_limit, self.workspace_bytes)
        ):
            raise ValueError("invalid batch reservation bounds")
        if self.resource == "host":
            if self.task_id is None or self.output_limit == 0:
                raise ValueError("host reservation needs a task and output allowance")
            identifier(self.task_id)
        elif self.task_id is not None or any(
            (self.prompt_bytes, self.output_limit, self.workspace_bytes)
        ):
            raise ValueError("scientific reservation cannot claim host resources")

    @property
    def transcript_ceiling(self):
        # The worker journal retains prompt, raw combined capture and final text.
        return self.prompt_bytes + 2 * self.output_limit


@dataclass(frozen=True)
class PhysicalObservation(AgentRecord):
    reservation_id: str
    status: Literal[
        "completed",
        "invalid_output",
        "timeout",
        "cancelled",
        "host_failure",
        "reconciliation_required",
        "success",
        "scientific_infeasible",
        "model_failure",
        "infrastructure_failure",
        "not_launched",
    ]
    stop_verified: bool
    transcript_bytes: int | None
    usage: Mapping[str, int | None]
    resolved_model: str | None
    request_intent: Literal["present", "absent", "unknown", "not_applicable"]
    elapsed_seconds: float | None
    evidence: tuple[ArtifactRef, ...]

    def _validate(self):
        identifier(self.reservation_id)
        if not self.evidence or len(self.evidence) > 16:
            raise ValueError("physical observation needs bounded evidence")
        if self.transcript_bytes is not None and self.transcript_bytes < 0:
            raise ValueError("invalid observed transcript size")
        if self.elapsed_seconds is not None and self.elapsed_seconds < 0:
            raise ValueError("invalid observed duration")
        if any(value is not None and value < 0 for value in self.usage.values()):
            raise ValueError("invalid observed usage")
        if not self.stop_verified and self.status != "reconciliation_required":
            raise ValueError("unverified physical work must remain pending")
        if self.status == "reconciliation_required" and self.stop_verified:
            raise ValueError("pending physical work cannot claim a verified stop")


@dataclass(frozen=True)
class CaseFinished(AgentRecord):
    case_id: str
    status: Literal["passed", "failed"]
    evidence: tuple[ArtifactRef, ...]

    def _validate(self):
        identifier(self.case_id)
        if not 1 <= len(self.evidence) <= 16:
            raise ValueError("case result needs bounded evidence")


@dataclass(frozen=True)
class BatchEvent(AgentRecord):
    schema_version: Literal["1.0"]
    sequence: int
    previous_hash: str | None
    batch_digest: str
    record: CaseStarted | PhysicalReservation | PhysicalObservation | CaseFinished

    def _validate(self):
        if self.sequence < 1:
            raise ValueError("invalid batch sequence")
        sha256(self.batch_digest)
        if self.previous_hash is not None:
            sha256(self.previous_hash)


@dataclass(frozen=True)
class BatchProjection:
    events: tuple[BatchEvent, ...]
    active_case: str | None
    reservations: Mapping[str, PhysicalReservation]
    observations: Mapping[str, PhysicalObservation]
    finished: Mapping[str, CaseFinished]

    @property
    def pending(self):
        return tuple(
            value
            for key, value in self.reservations.items()
            if key not in self.observations or not self.observations[key].stop_verified
        )

    @property
    def charged_transcript_bytes(self):
        return sum(
            self.observations[key].transcript_bytes
            if key in self.observations and self.observations[key].transcript_bytes is not None
            else value.transcript_ceiling
            for key, value in self.reservations.items()
            if value.resource == "host"
        )


class BatchStore:
    def __init__(self, root: Path, *, expected_digest=None, clock=time.time, fault=lambda _: None):
        self.root = checked_directory(root)
        self.events = checked_directory(self.root / "events")
        self.clock, self.fault = clock, fault
        self._writing = False
        manifest = self._json("batch.json")
        if set(manifest) != {"specification", "created_at"}:
            raise StoreError("invalid batch manifest")
        self.spec = BatchSpec.from_dict(manifest["specification"])
        created = manifest["created_at"]
        if type(created) not in (float, int) or not 0 <= created < float("inf"):
            raise StoreError("invalid batch creation time")
        self.created_at = created
        self._manifest = canonical_json(manifest)
        self.digest = digest(manifest)
        if expected_digest is not None:
            sha256(expected_digest)
            if self.digest != expected_digest:
                raise StoreError("batch manifest differs from trusted pin")
        self._trusted_pin = expected_digest

    @classmethod
    def create(cls, root, spec, *, clock=time.time, **kwargs):
        if (
            spec.source_identity != host_source_identity()
            or spec.environment_identity != host_environment_identity()
        ):
            raise StoreError("batch source or environment identity mismatch")
        root = Path(root).absolute()
        checked_directory(root.parent)
        root.mkdir(mode=0o700)
        for name in ("events", "artifacts", "cases"):
            (root / name).mkdir(mode=0o700)
        manifest = {"specification": spec.to_dict(), "created_at": clock()}
        durable_write(
            root / "batch.json",
            canonical_json(manifest).encode(),
        )
        return cls(root, expected_digest=digest(manifest), clock=clock, **kwargs)

    def _json(self, name):
        path = confined_file(self.root, name)
        with path.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise StoreError("batch record exceeds 64 KiB")
        return unique_json(raw.decode())

    @contextmanager
    def _lock(self, name):
        descriptor = os.open(
            self.root / name, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise StoreError("batch lock must be a regular file")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise WriterBusy("another operation owns the batch") from None
            yield
        finally:
            os.close(descriptor)

    @contextmanager
    def operation(self):
        """Held across physical work, independently of the short writer lock."""
        with self._lock(".operation.lock"):
            yield self

    @contextmanager
    def writer(self):
        if self._writing:
            raise WriterBusy("batch writer is already held")
        with self._lock(".writer.lock"):
            self._writing = True
            try:
                yield self
            finally:
                self._writing = False

    def _reduce(self, events):
        active, previous = None, None
        reservations, observations, finished = {}, {}, {}
        cases = {case.id: case for case in self.spec.cases}
        for sequence, event in enumerate(events, 1):
            if (event.sequence, event.previous_hash, event.batch_digest) != (
                sequence,
                previous,
                self.digest,
            ):
                raise StoreError("batch journal sequence, hash or identity mismatch")
            value = event.record
            if isinstance(value, CaseStarted):
                if active is not None or any(v.status == "failed" for v in finished.values()):
                    raise StoreError("unfinished or failed case blocks the batch")
                expected = self.spec.cases[len(finished)] if len(finished) < len(cases) else None
                if expected is None or (value.case_id, value.configuration_digest) != (
                    expected.id,
                    expected.configuration_digest,
                ):
                    raise StoreError("batch case differs from frozen order or configuration")
                if (
                    not self.created_at
                    <= value.recorded_at
                    < self.created_at + self.spec.limits.elapsed_seconds
                ):
                    raise StoreError("batch deadline exhausted")
                active = value.case_id
            elif isinstance(value, PhysicalReservation):
                if value.case_id != active or value.id in reservations:
                    raise StoreError("reservation scope mismatch or duplicate physical start")
                if any(
                    r.invocation_digest == value.invocation_digest for r in reservations.values()
                ):
                    raise StoreError("physical identity was already reserved")
                projection = BatchProjection(tuple(), active, reservations, observations, finished)
                if projection.pending:
                    raise StoreError("pending physical work requires reconciliation")
                case = cases[active]
                same = [r for r in reservations.values() if r.resource == value.resource]
                case_limit = (
                    case.host_invocations if value.resource == "host" else case.scientific_starts
                )
                total_limit = (
                    self.spec.limits.max_invocations
                    if value.resource == "host"
                    else self.spec.scientific_starts
                )
                if len(same) >= total_limit or sum(r.case_id == active for r in same) >= case_limit:
                    raise StoreError("physical batch allowance exhausted")
                if (
                    not self.created_at
                    <= value.recorded_at
                    < self.created_at + self.spec.limits.elapsed_seconds
                    or value.timeout_seconds
                    > self.created_at + self.spec.limits.elapsed_seconds - value.recorded_at
                ):
                    raise StoreError("physical reservation exceeds batch deadline")
                if value.resource == "host":
                    limits = self.spec.limits
                    keys = [(r.case_id, r.task_id) for r in same]
                    key = (active, value.task_id)
                    repairs = len(keys) - len(set(keys))
                    if (key not in keys and len(set(keys)) >= limits.max_tasks) or (
                        key in keys
                        and (
                            keys.count(key) >= limits.repairs_per_task + 1
                            or repairs >= limits.max_repairs
                        )
                    ):
                        raise StoreError("batch task or repair allowance exhausted")
                    if (
                        value.timeout_seconds > limits.worker_seconds
                        or value.output_limit > 65536
                        or value.workspace_bytes > limits.workspace_bytes
                    ):
                        raise StoreError("host reservation exceeds batch worker bounds")
                    if (
                        projection.charged_transcript_bytes + value.transcript_ceiling
                        > limits.transcript_bytes
                    ):
                        raise StoreError("batch transcript allowance exhausted")
                reservations[value.id] = value
            elif isinstance(value, PhysicalObservation):
                reservation = reservations.get(value.reservation_id)
                if reservation is None or reservation.case_id != active:
                    raise StoreError("observation has no active physical reservation")
                old = observations.get(value.reservation_id)
                if old is not None and old.stop_verified:
                    raise StoreError("terminal physical observation is immutable")
                if old is not None and (
                    any(
                        old.usage.get(key) is not None and old.usage[key] != value.usage.get(key)
                        for key in old.usage
                    )
                    or (
                        old.resolved_model is not None
                        and old.resolved_model != value.resolved_model
                    )
                    or (old.request_intent == "present" and value.request_intent != "present")
                ):
                    raise StoreError("physical reconciliation erased known evidence")
                if reservation.resource == "host":
                    if (
                        value.status
                        in (
                            "success",
                            "scientific_infeasible",
                            "model_failure",
                            "infrastructure_failure",
                        )
                        or value.request_intent == "not_applicable"
                    ):
                        raise StoreError("host observation has scientific fields")
                    if (
                        value.transcript_bytes is not None
                        and not reservation.prompt_bytes
                        <= value.transcript_bytes
                        <= reservation.transcript_ceiling
                    ):
                        raise StoreError("observed transcript exceeds reservation bounds")
                elif (
                    value.transcript_bytes != 0
                    or value.usage
                    or value.resolved_model is not None
                    or value.request_intent != "not_applicable"
                    or value.status in ("completed", "invalid_output", "host_failure")
                ):
                    raise StoreError("scientific observation has host fields")
                for ref in value.evidence:
                    read_bytes(self.root, ref, max_bytes=65536)
                observations[value.reservation_id] = value
            else:
                projection = BatchProjection(tuple(), active, reservations, observations, finished)
                if value.case_id != active or projection.pending:
                    raise StoreError("case has unresolved physical work")
                for ref in value.evidence:
                    read_bytes(self.root, ref, max_bytes=65536)
                finished[active] = value
                active = None
            previous = event.digest
        return BatchProjection(tuple(events), active, reservations, observations, finished)

    def replay(self):
        if canonical_json(self._json("batch.json")) != self._manifest:
            raise StoreError("batch manifest changed")
        events = []
        for path in sorted(self.events.iterdir()):
            if path.name.startswith(".") and path.name.endswith(".tmp"):
                continue
            if path.name != f"{len(events) + 1:012d}.json":
                raise StoreError("unexpected batch event or sequence gap")
            raw = self._json(f"events/{path.name}")
            if set(raw) != {"event", "sha256"}:
                raise StoreError("invalid batch event envelope")
            event = BatchEvent.from_dict(raw["event"])
            if event.digest != raw["sha256"]:
                raise StoreError("batch event checksum mismatch")
            events.append(event)
        return self._reduce(events)

    def commit(self, record):
        if not self._writing:
            raise StoreError("batch commit requires writer lock")
        if self._trusted_pin != self.digest:
            raise StoreError("batch mutation requires a caller-pinned manifest")
        if (
            self.spec.source_identity != host_source_identity()
            or self.spec.environment_identity != host_environment_identity()
        ):
            raise StoreError("batch source or environment identity changed")
        projection = self.replay()
        if isinstance(record, (CaseStarted, PhysicalReservation)):
            now = self.clock()
            prior_times = [
                getattr(e.record, "recorded_at", self.created_at) for e in projection.events
            ]
            if (
                type(now) not in (float, int)
                or not max([self.created_at, *prior_times])
                <= now
                < self.created_at + self.spec.limits.elapsed_seconds
                or not max([self.created_at, *prior_times]) <= record.recorded_at <= now
                or (
                    isinstance(record, PhysicalReservation)
                    and now + record.timeout_seconds
                    > self.created_at + self.spec.limits.elapsed_seconds
                )
            ):
                raise StoreError("batch clock or deadline prohibits a new reservation")
        event = BatchEvent(
            "1.0",
            len(projection.events) + 1,
            projection.events[-1].digest if projection.events else None,
            self.digest,
            record,
        )
        self._reduce((*projection.events, event))
        self.fault("before_event_commit")
        durable_write(
            self.events / f"{event.sequence:012d}.json",
            canonical_json({"event": event.to_dict(), "sha256": event.digest}).encode(),
        )
        self.fault("after_event_commit")
        return record

    def evidence(self, document):
        raw = canonical_json(document).encode()
        if len(raw) > 65536:
            raise StoreError("batch evidence exceeds 64 KiB")
        return put_bytes(
            self.root,
            raw,
            name="receipt.json",
            media_type="application/json",
            producer="trusted-batch-observer",
        )

    def start_case(self, case_id, configuration_digest):
        with self.operation(), self.writer():
            projection = self.replay()
            if projection.active_case == case_id:
                case = next(c for c in self.spec.cases if c.id == case_id)
                if case.configuration_digest != configuration_digest:
                    raise StoreError("active case configuration changed")
                return
            self.commit(CaseStarted(case_id, configuration_digest, self.clock()))

    def reserve(self, reservation):
        with self.writer():
            # Never return an earlier reservation as permission to launch again.
            return self.commit(reservation)

    def execute(self, reservation, perform, observe):
        """Call a trusted bounded implementation once, after durable reservation.

        Any exception leaves a pending charge. Reconciliation is a separate
        observation, never a second invocation of perform. The observer supplies
        evidence from the actual owned process or underlying journal.
        """
        with self.operation():
            self.reserve(reservation)
            now = self.clock()
            if (
                type(now) not in (float, int)
                or not reservation.recorded_at <= now
                or now + reservation.timeout_seconds
                > self.created_at + self.spec.limits.elapsed_seconds
            ):
                raise StoreError("batch deadline changed before physical launch; charge retained")
            result = perform(reservation)
            observation = observe(reservation, result)
            if observation.reservation_id != reservation.id:
                raise StoreError("observer returned a foreign physical reservation")
            self.observe(observation)
            return result

    def finish_case(self, case_id, status, evidence):
        with self.operation(), self.writer():
            expected = CaseFinished(case_id, status, evidence)
            old = self.replay().finished.get(case_id)
            if old == expected:
                return old
            return self.commit(expected)

    def observe(self, observation):
        """Idempotently append trusted proof. Never launch, retry or release a charge."""
        with self.writer():
            old = self.replay().observations.get(observation.reservation_id)
            if old == observation:
                return old
            return self.commit(observation)

    def report(self):
        value = self.replay()
        hosts = [r for r in value.reservations.values() if r.resource == "host"]
        return {
            "batch_id": self.spec.id,
            "batch_digest": self.digest,
            "specification_digest": self.spec.digest,
            "created_at": self.created_at,
            "deadline_at": self.created_at + self.spec.limits.elapsed_seconds,
            "status": "reconciliation_required"
            if value.pending
            else "failed"
            if any(v.status == "failed" for v in value.finished.values())
            else "completed"
            if len(value.finished) == len(self.spec.cases)
            else "active"
            if value.active_case
            else "ready",
            "active_case": value.active_case,
            "host_reservations_charged": len(hosts),
            "scientific_reservations_charged": sum(
                r.resource == "science" for r in value.reservations.values()
            ),
            "transcript_bytes_charged": value.charged_transcript_bytes,
            "pending_reservations": [r.id for r in value.pending],
            "host_invocations_with_unknown_usage": sum(
                r.id not in value.observations
                or not value.observations[r.id].usage
                or any(v is None for v in value.observations[r.id].usage.values())
                for r in hosts
            ),
            "request_intents_present": sum(
                o.request_intent == "present" for o in value.observations.values()
            ),
            "request_intents_unknown": sum(
                r.id not in value.observations
                or value.observations[r.id].request_intent == "unknown"
                for r in hosts
            ),
            "case_results": {key: result.status for key, result in value.finished.items()},
            "execution_authority": "not_granted_by_batch_manifest",
            "host": self.spec.host.to_dict(),
            "limits": self.spec.limits.to_dict(),
            "scientific_start_limit": self.spec.scientific_starts,
            "cases": [case.to_dict() for case in self.spec.cases],
            "reservations": [r.to_dict() for r in value.reservations.values()],
            "observations": [o.to_dict() for o in value.observations.values()],
        }
