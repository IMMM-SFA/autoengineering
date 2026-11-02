"""Append-only worker evidence and physical invocation reservations.

The commit is an immutable, hash-linked event. There is no mutable projection to
trust after interruption. This journal cannot write campaign events.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
import fcntl
from functools import wraps
import os
from pathlib import Path
import stat
import time
from typing import Callable, Literal
import uuid

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef, sha256
from autoengineering.campaign.serialization import Record, canonical_json, unique_json
from autoengineering.campaign.store import (
    StoreError,
    WriterBusy,
    checked_directory,
    durable_write,
    sync_directory,
)

from .permissions import validate_assignment, validate_task_route
from .records import (
    AgentRunSpec,
    CampaignAction,
    ReviewDisposition,
    ReviewFindings,
    RoleHandoff,
    RunStart,
    ScientificReceipt,
    TaskAssignment,
    WorkerInvocation,
    ImplementationPreparation,
    SourceDraft,
    HostConfigurationBinding,
)

PENDING = frozenset(("reserved", "running", "reconciliation_required"))
TERMINAL = frozenset(("completed", "invalid_output", "timeout", "cancelled", "host_failure"))


def serialized_operation(function):
    """Exclude competing external actions without holding the journal writer."""

    @wraps(function)
    def wrapped(self, *args, **kwargs):
        with self.store.operation():
            return function(self, *args, **kwargs)

    return wrapped


@dataclass(frozen=True)
class WorkerEvent(Record):
    schema_version: Literal["1.0"]
    sequence: int
    previous_hash: str | None
    run_digest: str
    record: (
        TaskAssignment
        | WorkerInvocation
        | CampaignAction
        | RunStart
        | ScientificReceipt
        | ReviewDisposition
        | ImplementationPreparation
        | HostConfigurationBinding
    )

    def _validate(self):
        if self.sequence < 1:
            raise ValueError("invalid journal sequence")
        sha256(self.run_digest)
        if self.previous_hash is not None:
            sha256(self.previous_hash)


@dataclass(frozen=True)
class WorkerProjection:
    events: tuple[WorkerEvent, ...]
    tasks: dict[str, TaskAssignment]
    invocations: dict[str, WorkerInvocation]
    actions: dict[str, CampaignAction]
    started_at: float | None
    science: tuple[ScientificReceipt, ...]
    dispositions: dict[str, ReviewDisposition]
    preparations: dict[str, ImplementationPreparation]
    host_configuration: HostConfigurationBinding | None = None

    @property
    def pending_preparations(self):
        return tuple(
            value
            for value in self.preparations.values()
            if value.state in ("captured", "checking", "reconciliation_required")
        )

    @property
    def pending(self) -> tuple[WorkerInvocation, ...]:
        return tuple(value for value in self.invocations.values() if value.state in PENDING)

    @property
    def repairs_used(self) -> int:
        return sum(invocation.attempt > 0 for invocation in self.invocations.values())


def invocation_artifacts(value: WorkerInvocation) -> tuple[ArtifactRef, ...]:
    return tuple(
        ref
        for ref in (
            value.prompt,
            value.process_receipt,
            value.raw_response,
            value.normalized_output,
            value.completion_receipt,
            value.parse_failure,
            value.final_response,
            value.stderr_response,
            value.recovery_receipt,
        )
        if ref is not None
    )


def preparation_artifacts(value: ImplementationPreparation):
    return tuple(
        ref
        for ref in (
            value.configuration,
            value.capture,
            value.interface,
            value.bundle,
            value.admission,
            value.fork,
        )
        if ref is not None
    )


class WorkerStore:
    def __init__(self, root: Path, *, fault: Callable[[str], None] | None = None):
        self.root = checked_directory(root)
        self.events_path = checked_directory(self.root / "events")
        self.spec = AgentRunSpec.from_file(confined_file(self.root, "run.json"))
        self.fault = fault or (lambda stage: None)
        self._locked = False

    @classmethod
    def create(cls, root: Path, spec: AgentRunSpec, *, clock=time.time, **kwargs):
        root = Path(root).absolute()
        if root.is_symlink() or (root.exists() and (not root.is_dir() or any(root.iterdir()))):
            raise StoreError("worker run requires an absent or empty directory")
        for part in (*reversed(root.parents), root):
            if part.is_symlink():
                raise StoreError("worker directory contains a symlink")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)
        for name in ("events", "artifacts", "control", "reports", "processes"):
            (root / name).mkdir(mode=0o700)
        durable_write(root / "run.json", spec.to_json().encode())
        sync_directory(root)
        store = cls(root, **kwargs)
        with store.writer():
            store.commit(RunStart("1.0", spec.id, clock()))
        return store

    def require_identity(self, spec: AgentRunSpec) -> None:
        if spec.digest != self.spec.digest:
            raise StoreError("worker run identity mismatch")

    @contextmanager
    def _advisory_lock(self, filename, label):
        descriptor = os.open(
            self.root / filename,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise StoreError(f"worker {label} lock must be a regular file")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise WriterBusy(f"another {label} owns the worker run") from error
            yield self
        finally:
            os.close(descriptor)

    @contextmanager
    def operation(self):
        """Lease one dispatch, reconciliation or scientific action across commits.

        Always acquire before the writer. OS descriptor ownership releases this
        lease on process death. A lease file alone does not prove a live owner.
        """
        with self._advisory_lock(".operation.lock", "operation"):
            yield self

    @contextmanager
    def writer(self):
        if self._locked:
            raise WriterBusy("worker writer is already held")
        with self._advisory_lock(".worker.lock", "writer"):
            self._locked = True
            try:
                yield self
            finally:
                self._locked = False

    def _reduce(self, events) -> WorkerProjection:
        tasks, invocations, actions = {}, {}, {}
        previous = None
        started_at = None
        science = []
        dispositions = {}
        preparations = {}
        host_configuration = None
        for sequence, event in enumerate(events, 1):
            if (event.sequence, event.previous_hash, event.run_digest) != (
                sequence,
                previous,
                self.spec.digest,
            ):
                raise StoreError("worker journal sequence, hash or identity mismatch")
            value = event.record
            if value.run_id != self.spec.id:
                raise StoreError("record belongs to a different worker run")
            if isinstance(value, RunStart):
                if sequence != 1:
                    raise StoreError("run start receipt must be the first event")
                started_at = value.created_at
            elif started_at is None:
                raise StoreError("worker run creation receipt is missing")
            elif isinstance(value, HostConfigurationBinding):
                if sequence != 2 or host_configuration is not None:
                    raise StoreError("host configuration must be bound before worker activity")
                capabilities = value.capabilities
                if (
                    capabilities.host,
                    capabilities.auth_mode,
                    capabilities.adapter_version,
                    capabilities.boundary_identity,
                ) != (
                    self.spec.host.kind,
                    self.spec.host.auth_mode,
                    self.spec.host.adapter_version,
                    self.spec.host.qualification_digest,
                ):
                    raise StoreError("host configuration differs from run selection")
                host_configuration = value
            elif isinstance(value, ImplementationPreparation):
                if value.recorded_at < started_at:
                    raise StoreError("preparation predates its worker run")
                invocation = invocations.get(value.invocation_id)
                if (
                    self.spec.execution_mode != "generated"
                    or invocation is None
                    or invocation.state != "completed"
                ):
                    raise StoreError("source preparation requires a completed generated handoff")
                handoff = RoleHandoff.from_json(
                    read_bytes(self.root, invocation.normalized_output).decode()
                )
                if (
                    not isinstance(handoff.output, SourceDraft)
                    or invocation.task_id != value.task_id
                    or handoff.output.candidate_id != value.candidate_id
                    or handoff.output.digest != value.draft_digest
                ):
                    raise StoreError("preparation differs from its implementer handoff")
                old = preparations.get(value.id)
                if old is None:
                    if value.state != "captured" or any(
                        getattr(value, field) is not None
                        for field in (
                            "interface",
                            "bundle",
                            "admission",
                            "registration_identity",
                            "fork",
                            "successor_identity",
                        )
                    ):
                        raise StoreError("source preparation must start with capture")
                    if any(v.invocation_id == value.invocation_id for v in preparations.values()):
                        raise StoreError("a handoff cannot replenish its source check allowance")
                else:
                    if value.recorded_at < old.recorded_at:
                        raise StoreError("preparation observation time moved backwards")
                    transitions = {
                        "captured": {"checking", "failed"},
                        "checking": {"checked", "failed", "reconciliation_required"},
                        "reconciliation_required": {"checked", "failed"},
                        "checked": {"registered"},
                        "registered": {"forked"},
                    }
                    if value.state not in transitions.get(old.state, set()):
                        raise StoreError("illegal source preparation transition")
                    for field in (
                        "schema_version",
                        "id",
                        "run_id",
                        "task_id",
                        "invocation_id",
                        "candidate_id",
                        "proposal_digest",
                        "draft_digest",
                        "workspace",
                        "configuration",
                        "capture",
                    ):
                        if getattr(old, field) != getattr(value, field):
                            raise StoreError("source preparation identity changed")
                    for field in (
                        "interface",
                        "bundle",
                        "admission",
                        "registration_identity",
                        "fork",
                        "successor_identity",
                    ):
                        if getattr(old, field) is not None and getattr(old, field) != getattr(
                            value, field
                        ):
                            raise StoreError("source preparation evidence changed")
                preparations[value.id] = value
            elif isinstance(value, ReviewDisposition):
                invocation = invocations.get(value.invocation_id)
                if (
                    invocation is None
                    or invocation.state != "completed"
                    or (tasks[invocation.task_id].role not in ("reviewer", "single_agent"))
                ):
                    raise StoreError("disposition requires a completed review")
                handoff = RoleHandoff.from_json(
                    read_bytes(self.root, invocation.normalized_output).decode()
                )
                if (
                    not isinstance(handoff.output, ReviewFindings)
                    or handoff.output.digest != value.review_digest
                ):
                    raise StoreError("disposition refers to different review evidence")
                if value.invocation_id in dispositions:
                    raise StoreError("review disposition is immutable")
                dispositions[value.invocation_id] = value
            elif isinstance(value, ScientificReceipt):
                if value.campaign_identity != self.spec.campaign_identity:
                    raise StoreError("scientific receipt belongs to a different campaign")
                if science and value.revision <= science[-1].revision:
                    raise StoreError("scientific receipt revision is immutable")
                if science and not {a.id for a in science[-1].attempts} <= {
                    a.id for a in value.attempts
                }:
                    raise StoreError("scientific receipt erased a physical attempt")
                science.append(value)
            elif isinstance(value, CampaignAction):
                old = actions.get(value.id)
                if old is None:
                    if value.state != "reserved":
                        raise StoreError("campaign action must begin with an intent")
                    if any(a.state == "reserved" for a in actions.values()):
                        raise StoreError("pending campaign action requires reconciliation")
                    if any(v.state in PENDING for v in invocations.values()):
                        raise StoreError("pending worker requires reconciliation")
                    if len(actions) >= 16 + self.spec.limits.max_tasks * 8:
                        raise StoreError("broker action allowance exhausted")
                    if value.invocation_id is not None and (
                        value.invocation_id not in invocations
                        or invocations[value.invocation_id].state != "completed"
                    ):
                        raise StoreError("campaign action requires a valid completed handoff")
                    if (
                        value.request is not None
                        and value.request.campaign_id != self.spec.campaign_id
                    ):
                        raise StoreError("campaign request belongs to a different campaign")
                else:
                    if old.state == "completed" or value.state != "completed":
                        raise StoreError("campaign action is immutable")
                    for field in ("id", "run_id", "kind", "invocation_id", "source", "request"):
                        if getattr(old, field) != getattr(value, field):
                            raise StoreError("campaign intent changed")
                actions[value.id] = value
            elif isinstance(value, TaskAssignment):
                validate_assignment(value)
                validate_task_route(value, self.spec)
                if value.id in tasks or len(tasks) >= self.spec.limits.max_tasks:
                    raise StoreError("duplicate task or task limit exhausted")
                if value.parent_task is not None and value.parent_task not in tasks:
                    raise StoreError("task parent does not exist")
                if value.repair_allowance > self.spec.limits.repairs_per_task:
                    raise StoreError("task expands repair allowance")
                tasks[value.id] = value
            else:
                if (
                    host_configuration is not None
                    and value.capabilities != host_configuration.capabilities
                ):
                    raise StoreError("invocation differs from bound host configuration")
                if value.task_id not in tasks:
                    raise StoreError("invocation task does not exist")
                if (value.policy_digest, value.requested_model) != (
                    self.spec.tool_policy_digest,
                    self.spec.host.requested_model,
                ):
                    raise StoreError("invocation policy/model mismatch")
                if (
                    value.capabilities.host,
                    value.capabilities.auth_mode,
                    value.capabilities.adapter_version,
                ) != (
                    self.spec.host.kind,
                    self.spec.host.auth_mode,
                    self.spec.host.adapter_version,
                ):
                    raise StoreError("invocation host identity mismatch")
                if (
                    self.spec.host.adapter_version in ("2.1", "3.0")
                    and value.capabilities.boundary_identity != self.spec.host.qualification_digest
                ):
                    raise StoreError("invocation native qualification pin mismatch")
                old = invocations.get(value.id)
                if old is None:
                    if any(a.state == "reserved" for a in actions.values()):
                        raise StoreError("pending campaign action requires reconciliation")
                    if any(item.state in PENDING for item in invocations.values()):
                        raise StoreError("pending invocation requires reconciliation")
                    if value.state != "reserved":
                        raise StoreError("invocation must begin with a reservation")
                    if len(invocations) >= self.spec.limits.max_invocations:
                        raise StoreError("physical invocation limit exhausted")
                    if (
                        not started_at
                        <= value.started_at
                        < started_at + self.spec.limits.elapsed_seconds
                    ):
                        raise StoreError("invocation is outside the frozen run duration")
                    prior = [v for v in invocations.values() if v.task_id == value.task_id]
                    if any(v.state == "completed" for v in prior):
                        raise StoreError("completed task cannot be dispatched again")
                    if value.attempt != len(prior):
                        raise StoreError("invocation attempt sequence mismatch")
                    repairs = sum(v.attempt > 0 for v in invocations.values())
                    if value.attempt and (
                        value.attempt > tasks[value.task_id].repair_allowance
                        or repairs >= self.spec.limits.max_repairs
                    ):
                        raise StoreError("repair allowance exhausted")
                    if value.prompt.size_bytes > self.spec.limits.transcript_bytes:
                        raise StoreError("prompt exceeds transcript allowance")
                else:
                    if old.state in TERMINAL:
                        raise StoreError("terminal invocation is immutable")
                    if value.state == "reserved" or (
                        old.state == "reconciliation_required" and value.state == "running"
                    ):
                        raise StoreError("illegal invocation transition")
                    for field in (
                        "schema_version",
                        "id",
                        "run_id",
                        "task_id",
                        "attempt",
                        "prompt",
                        "capabilities",
                        "requested_model",
                        "policy_digest",
                        "launch_nonce",
                        "started_at",
                    ):
                        if getattr(old, field) != getattr(value, field):
                            raise StoreError("invocation identity changed")
                    for field in (
                        "process_receipt",
                        "raw_response",
                        "normalized_output",
                        "completion_receipt",
                        "parse_failure",
                        "final_response",
                        "stderr_response",
                        "recovery_receipt",
                    ):
                        if getattr(old, field) is not None and (
                            getattr(old, field) != getattr(value, field)
                        ):
                            raise StoreError("invocation evidence changed")
                invocations[value.id] = value
                # Every physical transcript counts, even when its bytes match.
                refs = [
                    ref
                    for v in invocations.values()
                    for ref in (
                        v.prompt,
                        v.raw_response,
                        v.stderr_response,
                    )
                    if ref is not None
                ]
                if sum(ref.size_bytes for ref in refs) > self.spec.limits.transcript_bytes:
                    raise StoreError("run transcript allowance exhausted")
            previous = event.digest
        return WorkerProjection(
            tuple(events),
            tasks,
            invocations,
            actions,
            started_at,
            tuple(science),
            dispositions,
            preparations,
            host_configuration,
        )

    def replay(self) -> WorkerProjection:
        # run.json is part of every committed event identity, including read-only reports.
        if AgentRunSpec.from_file(confined_file(self.root, "run.json")) != self.spec:
            raise StoreError("worker run manifest changed")
        events = []
        for path in sorted(self.events_path.iterdir()):
            if path.name.startswith(".") and path.name.endswith(".tmp"):
                continue
            if path.name != f"{len(events) + 1:012d}.json":
                raise StoreError("unexpected worker event or sequence gap")
            safe = confined_file(self.root, f"events/{path.name}")
            if safe.stat().st_size > 1048576:
                raise StoreError("worker event exceeds size limit")
            raw = safe.read_text(encoding="utf-8")
            document = unique_json(raw)
            if not isinstance(document, dict) or set(document) != {"event", "sha256"}:
                raise StoreError("invalid worker event envelope")
            event = WorkerEvent.from_dict(document["event"])
            if document["sha256"] != event.digest or raw != canonical_json(document) + "\n":
                raise StoreError("worker event checksum/canonical form mismatch")
            if isinstance(event.record, WorkerInvocation):
                for reference in invocation_artifacts(event.record):
                    read_bytes(self.root, reference, max_bytes=self.spec.limits.transcript_bytes)
            elif isinstance(event.record, CampaignAction) and event.record.source is not None:
                read_bytes(self.root, event.record.source)
            elif isinstance(event.record, TaskAssignment):
                for grant in event.record.grants:
                    read_bytes(self.root, grant.artifact, max_bytes=grant.max_bytes)
            elif isinstance(event.record, ImplementationPreparation):
                for reference in preparation_artifacts(event.record):
                    read_bytes(self.root, reference)
            events.append(event)
        return self._reduce(events)

    def commit(
        self,
        record: TaskAssignment
        | WorkerInvocation
        | CampaignAction
        | RunStart
        | ScientificReceipt
        | ReviewDisposition
        | ImplementationPreparation
        | HostConfigurationBinding,
    ):
        if not self._locked:
            raise StoreError("worker commit requires writer lock")
        projection = self.replay()
        event = WorkerEvent(
            "1.0",
            len(projection.events) + 1,
            projection.events[-1].digest if projection.events else None,
            self.spec.digest,
            record,
        )
        self._reduce((*projection.events, event))
        if isinstance(record, WorkerInvocation):
            for reference in invocation_artifacts(record):
                read_bytes(self.root, reference, max_bytes=self.spec.limits.transcript_bytes)
        elif isinstance(record, CampaignAction) and record.source is not None:
            read_bytes(self.root, record.source)
        elif isinstance(record, TaskAssignment):
            for grant in record.grants:
                read_bytes(self.root, grant.artifact, max_bytes=grant.max_bytes)
        elif isinstance(record, ImplementationPreparation):
            for reference in preparation_artifacts(record):
                read_bytes(self.root, reference)
        self.fault("before_event_commit")
        durable_write(
            self.events_path / f"{event.sequence:012d}.json",
            (canonical_json({"event": event.to_dict(), "sha256": event.digest}) + "\n").encode(),
        )
        self.fault("after_event_commit")
        return record

    def put_private(self, data: bytes, *, name: str, media_type: str) -> ArtifactRef:
        if not self._locked:
            raise StoreError("worker artifacts require writer lock")
        if len(data) > self.spec.limits.transcript_bytes:
            raise StoreError("worker artifact exceeds transcript allowance")
        return put_bytes(
            self.root, data, name=name, media_type=media_type, producer="worker-broker"
        )

    def mark_unresolved(self) -> tuple[str, ...]:
        """Recovery never assumes a reserved or running host is dead."""
        if not self._locked:
            raise StoreError("worker recovery requires writer lock")
        pending = self.replay().pending
        for value in pending:
            if value.state != "reconciliation_required":
                self.commit(replace(value, state="reconciliation_required"))
        return tuple(value.id for value in pending)

    def request_cancel(self) -> str:
        """Independent inbox: queued intent, never a claim that a process stopped."""
        control = checked_directory(self.root / "control")
        nonce = uuid.uuid4().hex
        durable_write(control / f"cancel-{nonce}.json", b'{"intent":"cancel"}\n')
        return nonce
