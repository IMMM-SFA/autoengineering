"""Single-writer suite journal with permanent parent reservations.

Child journals remain authoritative for execution. This journal allocates permission
and pins child identities; it never copies or edits scientific observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import Record, canonical_json, unique_json
from autoengineering.campaign.store import EventStore, StoreError, durable_write
from .contracts import ResourceCap, UtilitySuiteSpec, identifier, sha256


@dataclass(frozen=True)
class SuiteEvent(Record):
    sequence: int
    previous: str | None
    suite_digest: str
    request_id: str
    operation: Literal["reserve", "start", "finish", "cancel", "freeze", "role_reserve", "confirmation_access", "confirmation_score", "mechanical_step"]
    cell_digest: str
    attempt_id: str
    child_digest: str
    phase: Literal["selection", "confirmation"]
    resources: tuple[ResourceCap, ...]
    result_digest: str | None

    def _validate(self):
        if self.sequence < 1:
            raise ValueError("invalid sequence")
        for value in (self.suite_digest, self.cell_digest, self.child_digest):
            sha256(value)
        for value in (self.previous, self.result_digest):
            if value is not None:
                sha256(value)
        identifier(self.request_id)
        identifier(self.attempt_id)
        if self.operation in ("finish", "freeze", "role_reserve", "confirmation_access", "confirmation_score", "mechanical_step") and self.result_digest is None:
            raise ValueError("finish requires pinned child result evidence")
        if self.operation not in ("finish", "freeze", "role_reserve", "confirmation_access", "confirmation_score", "mechanical_step") and self.result_digest is not None:
            raise ValueError("result only belongs to finish")


class SuiteStore(EventStore):
    """Manifest-last initialization and immutable journal commits.

    A started attempt without a result remains uncertain after owner loss. It
    cannot be retried automatically or have its reserved allowance refunded.
    """

    @classmethod
    def create(cls, root, spec: UtilitySuiteSpec, **kwargs):
        base = EventStore.create(root)
        durable_write(base.root / "suite.json", (spec.to_json() + "\n").encode())
        return cls(base.root, expected=spec, **kwargs)

    def __init__(self, root, *, expected=None, fault=None):
        super().__init__(root, fault=fault)
        path = confined_file(self.root, "suite.json")
        if path.stat().st_size > 16 * 1024 * 1024:
            raise StoreError("oversized suite manifest")
        self.spec = UtilitySuiteSpec.from_json(path.read_text())
        if expected is not None and self.spec.digest != expected.digest:
            raise StoreError("suite identity changed; resume rejected")

    def _reduce(self, events):
        cells = {c.digest: c for c in self.spec.cells}
        budgets = {b.regime: b for b in self.spec.budgets}
        attempts, requests, used = {}, {}, {}
        role_counts, role_invocations = {}, set()
        phase_used, accesses, scores = {}, {}, {}
        mechanical_steps = {}
        cancelled, head, frozen = False, None, None
        for seq, event in enumerate(events, 1):
            if (event.sequence != seq or event.previous != head
                    or event.suite_digest != self.spec.digest):
                raise StoreError("suite event chain mismatch")
            if event.request_id in requests:
                raise StoreError("duplicate request")
            if event.cell_digest not in cells:
                raise StoreError("unknown cell")
            key = event.attempt_id
            if event.operation == "reserve":
                if cancelled or key in attempts:
                    raise StoreError("reservation unavailable")
                if (event.phase == "selection") != (frozen is None):
                    raise StoreError("reservation conflicts with selection barrier")
                if event.phase == "confirmation":
                    from .confirmation import read_manifest
                    manifest = read_manifest(self.root, frozen)
                    if not any(c.cell_digest == event.cell_digest and c.status == "selected"
                               for c in manifest.cells):
                        raise StoreError("confirmation requires an immutable selected model")
                    if any(a.cell_digest == event.cell_digest and a.phase == "confirmation"
                           for a, _ in attempts.values()):
                        raise StoreError("confirmation cell already has a charged attempt")
                if any(a.cell_digest == event.cell_digest and state != "finished"
                       for a, state in attempts.values()):
                    raise StoreError("cell has unresolved work")
                budget = budgets[cells[event.cell_digest].regime]
                caps = {c.name: c for c in budget.caps}
                reserve = {c.name: c.limit for c in budget.confirmation_reserve}
                if not event.resources or len({r.name for r in event.resources}) != len(
                        event.resources):
                    raise StoreError("reservation resources must be unique and nonempty")
                for resource in event.resources:
                    cap = caps.get(resource.name)
                    if (cap is None or resource.units != cap.units
                            or resource.enforcement != "reservation"
                            or cap.enforcement != "reservation"):
                        raise StoreError("unknown resource or incompatible enforcement")
                    counter = (budget.regime, resource.name)
                    value = used.get(counter, 0) + resource.limit
                    phase_counter = (budget.regime, event.phase, resource.name)
                    phase_value = phase_used.get(phase_counter, 0) + resource.limit
                    phase_cap = (cap.limit - reserve.get(resource.name, 0) if event.phase == "selection"
                                 else reserve.get(resource.name, 0))
                    if value > cap.limit or phase_value > phase_cap:
                        raise StoreError("parent phase budget exhausted")
                    used[counter] = value
                    phase_used[phase_counter] = phase_value
                attempts[key] = (event, "reserved")
            elif event.operation == "mechanical_step":
                if cancelled or frozen is not None:
                    raise StoreError("suite is closed to mechanical work")
                from .mechanical import validate_mechanical
                validate_mechanical(self, event, attempts, mechanical_steps)
            elif event.operation in ("confirmation_access", "confirmation_score"):
                allocation, state = attempts.get(key, (None, None))
                if (state != "started" or allocation.phase != "confirmation"
                        or event.phase != "confirmation" or event.resources
                        or (allocation.cell_digest, allocation.child_digest) != (event.cell_digest, event.child_digest)):
                    raise StoreError("confirmation receipt requires an active bound attempt")
                if event.operation == "confirmation_access":
                    if key in accesses:
                        raise StoreError("confirmation access already committed")
                    from .scoring import validate_access
                    validate_access(self, event, frozen, allocation)
                    accesses[key] = event.result_digest
                else:
                    if key not in accesses or key in scores:
                        raise StoreError("confirmation score lacks a unique access intent")
                    from .scoring import validate_score
                    validate_score(self, event, accesses[key], frozen)
                    scores[key] = event.result_digest
            elif event.operation == "role_reserve":
                if cancelled or frozen is not None:
                    raise StoreError("suite is closed to role dispatch")
                from .role_host import validate_claim
                validate_claim(self, event, attempts, role_counts, role_invocations)
            elif event.operation == "freeze":
                if frozen is not None or event.resources or event.phase != "selection":
                    raise StoreError("invalid selection freeze")
                if any(status != "finished" for _, status in attempts.values()):
                    raise StoreError("unresolved selection work blocks freeze")
                from .confirmation import read_manifest, validate_manifest
                manifest = read_manifest(self.root, event.result_digest)
                validate_manifest(self, manifest, attempts, tuple(events[:seq-1]))
                frozen = event.result_digest
            elif event.operation == "cancel":
                if event.resources:
                    raise StoreError("cancellation cannot change resources")
                cancelled = True
            else:
                if key not in attempts or event.resources:
                    raise StoreError("transition needs existing attempt and no new allowance")
                allocation, state = attempts[key]
                if any(getattr(allocation, name) != getattr(event, name) for name in (
                        "cell_digest", "child_digest", "phase")):
                    raise StoreError("attempt child binding changed")
                target = {"start": ("reserved", "started"), "finish": ("started", "finished")}
                before, after = target[event.operation]
                if state != before or ((cancelled or (frozen is not None and event.phase == "selection"))
                                       and event.operation == "start"):
                    raise StoreError("invalid attempt transition")
                if event.operation == "finish" and event.phase == "confirmation" and (
                        key not in scores or scores[key] != event.result_digest):
                    raise StoreError("confirmation acknowledgement requires its saved score")
                attempts[key] = (allocation, after)
            requests[event.request_id] = event
            head = event.digest
        return {"attempts": attempts, "requests": requests, "used": used,
                "confirmation_accesses": accesses, "confirmation_scores": scores,
                "mechanical_steps": mechanical_steps, "phase_used": phase_used, "role_counts": role_counts, "role_invocations": role_invocations,
                "cancelled": cancelled, "frozen": frozen, "head": head, "events": tuple(events)}

    def replay(self):
        manifest = confined_file(self.root, "suite.json")
        if manifest.stat().st_size > 16 * 1024 * 1024:
            raise StoreError("oversized suite manifest")
        if UtilitySuiteSpec.from_json(manifest.read_text()).digest != self.spec.digest:
            raise StoreError("suite manifest changed after opening")
        files = []
        for path in self.events_path.iterdir():
            if path.name.startswith(".") and path.name.endswith(".tmp"):
                continue
            files.append(path)
        events = []
        for sequence, path in enumerate(sorted(files), 1):
            if path.name != f"{sequence:012d}.json":
                raise StoreError("unexpected event or sequence gap")
            path = confined_file(self.root, f"events/{path.name}")
            if path.stat().st_size > 1048576:
                raise StoreError("oversized suite event")
            document = unique_json(path.read_text())
            if not isinstance(document, dict) or set(document) != {"event", "sha256"}:
                raise StoreError("invalid suite event envelope")
            event = SuiteEvent.from_dict(document["event"])
            if event.digest != document["sha256"]:
                raise StoreError("suite event digest mismatch")
            events.append(event)
        return self._reduce(events)

    def append(self, *, request_id, operation, cell_digest, attempt_id, child_digest,
               resources=(), result_digest=None, phase="selection"):
        if not self._locked:
            raise StoreError("suite mutation requires writer lock")
        state = self.replay()
        previous = state["requests"].get(request_id)
        event = SuiteEvent(len(state["events"]) + 1, state["head"], self.spec.digest,
                           request_id, operation, cell_digest, attempt_id, child_digest,
                           phase, resources, result_digest)
        if previous is not None:
            payload = event.to_dict()
            payload.update(sequence=previous.sequence, previous=previous.previous)
            if SuiteEvent.from_dict(payload) != previous:
                raise StoreError("request ID reused with changed payload")
            return previous
        self._reduce((*state["events"], event))
        self.fault("before_suite_commit")
        data = canonical_json({"event": event.to_dict(), "sha256": event.digest}) + "\n"
        durable_write(self.events_path / f"{event.sequence:012d}.json", data.encode())
        self.fault("after_suite_commit")
        return event
