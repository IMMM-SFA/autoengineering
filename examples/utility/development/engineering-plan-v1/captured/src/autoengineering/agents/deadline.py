"""Foreground scientific cancellation at the immutable worker-run deadline.

The timer forwards intents through independent inboxes. It does not signal a
scientific process or certify its stop. If this supervisor dies, existing
scientific ownership and recovery rules still apply.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import threading
from typing import Literal
import uuid

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.records import identifier, sha256, unique
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.store import StoreError, durable_write

from .records import AgentRecord
from .store import WorkerStore


def deadline_cancel_id(run_id: str) -> str:
    return f"deadline-{digest(run_id)[:24]}"


class DeadlineForwardingError(StoreError):
    """A stop was requested, but forwarding or its evidence remains incomplete."""


@dataclass(frozen=True)
class DeadlineNotice(AgentRecord):
    schema_version: Literal["1.0"]
    id: str
    run_id: str
    run_digest: str
    deadline_at: float
    recorded_at: float
    action_id: str | None
    worker_intent_id: str | None
    scientific_intent_id: str | None
    failures: tuple[Literal["worker_cancel_failed", "scientific_cancel_failed"], ...]
    reconciles: tuple[str, ...] = ()

    def _validate(self):
        for value in (self.id, self.run_id, self.action_id, self.worker_intent_id):
            if value is not None:
                identifier(value)
        sha256(self.run_digest)
        if self.deadline_at < 0 or self.recorded_at < 0:
            raise ValueError("deadline notice times must be nonnegative")
        unique(self.failures, "deadline forwarding failure")
        unique(self.reconciles, "deadline forwarding resolution")
        for value in self.reconciles:
            identifier(value)
        if self.failures and self.reconciles:
            raise ValueError("failed deadline forwarding cannot resolve earlier failures")
        if (self.worker_intent_id is None) != ("worker_cancel_failed" in self.failures):
            raise ValueError("deadline worker forwarding outcome is inconsistent")
        if (self.scientific_intent_id is None) != ("scientific_cancel_failed" in self.failures):
            raise ValueError("deadline scientific forwarding outcome is inconsistent")
        if self.scientific_intent_id not in (None, deadline_cancel_id(self.run_id)):
            raise ValueError("deadline cancellation identity differs from the worker run")


def read_deadline_notices(
    store: WorkerStore, *, started_at: float, action_ids: set[str]
) -> list[dict]:
    """Read notices without importing a controller or consulting process state."""
    values = []
    for path in sorted((store.root / "control").glob("deadline-*.json")):
        path = confined_file(store.root, f"control/{path.name}")
        if path.stat().st_size > 65536:
            raise StoreError("deadline notice exceeds its byte ceiling")
        notice = DeadlineNotice.from_json(path.read_text())
        if (
            (notice.run_id, notice.run_digest) != (store.spec.id, store.spec.digest)
            or path.name != f"deadline-{notice.id}.json"
            or notice.deadline_at != started_at + store.spec.limits.elapsed_seconds
            or (notice.action_id is not None and notice.action_id not in action_ids)
        ):
            raise StoreError("deadline notice has a different worker identity or limit")
        if notice.worker_intent_id is not None:
            intent = confined_file(store.root, f"control/cancel-{notice.worker_intent_id}.json")
            if intent.stat().st_size > 65536 or unique_json(intent.read_text()) != {
                "intent": "cancel"
            }:
                raise StoreError("deadline notice has no valid worker cancellation intent")
        values.append({**notice.to_dict(), "path": f"control/{path.name}"})
    by_id = {notice["id"]: notice for notice in values}
    resolved = set()
    for notice in values:
        for previous_id in notice["reconciles"]:
            previous = by_id.get(previous_id)
            if (
                previous is None
                or not previous["failures"]
                or previous["action_id"] != notice["action_id"]
            ):
                raise StoreError("deadline resolution refers to different or missing failures")
            resolved.add(previous_id)
    for notice in values:
        notice["forwarding_resolved"] = notice["id"] in resolved
    return values


class ScientificDeadline:
    """Join the timer before committing a response or allowing another action."""

    def __init__(
        self,
        store: WorkerStore,
        *,
        clock: Callable[[], float],
        cancel_science: Callable[[str], dict],
        action_id: str | None = None,
    ):
        self.store, self.clock = store, clock
        self.cancel_science, self.action_id = cancel_science, action_id
        started = store.replay().started_at
        if started is None:
            raise StoreError("worker run creation receipt is missing")
        self.deadline = started + store.spec.limits.elapsed_seconds
        self.notice = None
        self.failure = None
        self.timer = None

    def expire(self):
        """Attempt both forwards even if one fails. Persist only bounded outcome codes."""
        worker, science, failures = None, None, []
        try:
            worker = self.store.request_cancel()
        except Exception:
            failures.append("worker_cancel_failed")
        try:
            requested = deadline_cancel_id(self.store.spec.id)
            result = self.cancel_science(requested)
            if (
                result.get("request_id") != requested
                or result.get("campaign_id") != self.store.spec.campaign_id
                or result.get("operation") != "cancel"
            ):
                raise ValueError("scientific cancellation acknowledgment differs from intent")
            science = requested
        except Exception:
            failures.append("scientific_cancel_failed")
        try:
            projection = self.store.replay()
            previous = read_deadline_notices(
                self.store, started_at=projection.started_at, action_ids=set(projection.actions)
            )
            self.notice = DeadlineNotice(
                "1.0",
                uuid.uuid4().hex,
                self.store.spec.id,
                self.store.spec.digest,
                self.deadline,
                self.clock(),
                self.action_id,
                worker,
                science,
                tuple(failures),
                tuple(
                    n["id"] for n in previous if n["failures"] and n["action_id"] == self.action_id
                )
                if not failures
                else (),
            )
            durable_write(
                self.store.root / "control" / f"deadline-{self.notice.id}.json",
                (self.notice.to_json() + "\n").encode(),
            )
        except Exception as error:
            self.failure = error

    def __enter__(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            # Exact-envelope reconciliation is still allowed. Queue cancellation
            # before calling the service, so it cannot start new scientific work.
            self.expire()
            self._check_forwarding()
        else:
            self.timer = threading.Timer(remaining, self.expire)
            self.timer.daemon = True
            self.timer.start()
        return self

    def _check_forwarding(self):
        if self.failure is not None:
            raise DeadlineForwardingError(
                "deadline forwarding receipt unavailable; reconciliation required"
            )
        if self.notice is not None and self.notice.failures:
            raise DeadlineForwardingError(
                "deadline cancellation forwarding failed; reconciliation required"
            )

    def __exit__(self, kind, value, traceback):
        if self.timer is not None:
            self.timer.cancel()
            self.timer.join()
        if kind is None:
            self._check_forwarding()
