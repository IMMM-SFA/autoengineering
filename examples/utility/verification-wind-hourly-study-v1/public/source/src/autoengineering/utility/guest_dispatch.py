"""Candidate single-start stdin dispatch and saved-only lifecycle reconciliation.

No default executor activates this path. Authored peers do not qualify an actual
container runtime, isolation or scientific utility. Recovery never reconnects,
starts, creates, executes a model or renews the original deadline.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .contracts import sha256
from .guest_attach import GuestAttachCancelled, GuestAttachTimeout, attach
from .guest_bootstrap import (
    GuestBootstrapCapture,
    capture_response,
    encode_request,
    read_capture,
)
from .guest_daemon import _access
from .guest_inputs import verify_guest_inputs
from .guest_observations import verify_created, verify_started
from .guest_watchdog import (
    CLEANUP_SECONDS,
    GuestWatchdogPlan,
    GuestWatchdogReady,
    GuestWatchdogOutcome,
    arm,
    read_outcome,
)


@dataclass(frozen=True)
class GuestDispatchPlan(Record):
    schema: Literal["utility-guest-dispatch-plan-v1"]
    owner_digest: str
    container_id: str
    package_digest: str
    watchdog: GuestWatchdogPlan
    ready: GuestWatchdogReady

    def _validate(self):
        for value in (self.owner_digest, self.container_id, self.package_digest):
            sha256(value)
        if (
            self.watchdog.owner_digest != self.owner_digest
            or self.watchdog.container_id != self.container_id
            or self.ready.owner_digest != self.owner_digest
            or self.ready.container_id != self.container_id
            or self.ready.plan_digest != self.watchdog.digest
        ):
            raise ValueError("guest dispatch differs from original watchdog readiness")


@dataclass(frozen=True)
class GuestDispatchCompletion(Record):
    schema: Literal["utility-guest-dispatch-completion-v1"]
    plan_digest: str
    owner_digest: str
    journal_head: str
    journal_phase: str
    transport_status: Literal["complete", "missing", "unverified"]
    start_response: ArtifactRef | None
    capture: GuestBootstrapCapture | None
    watchdog: GuestWatchdogOutcome
    boundary: Literal["unqualified-candidate"] = "unqualified-candidate"

    def _validate(self):
        for value in (self.plan_digest, self.owner_digest, self.journal_head):
            sha256(value)
        if self.watchdog.owner_digest != self.owner_digest:
            raise ValueError("guest completion differs from original owner")
        if self.transport_status == "complete" and (
            self.capture is None or self.start_response is None or self.journal_phase != "cleaned"
        ):
            raise ValueError("guest completed transport lacks original evidence")


def _json(root, name, kind=None, limit=65536):
    path = confined_file(root, name)
    if path.stat().st_size > limit:
        raise StoreError("guest dispatch record exceeds bound")
    raw = path.read_text()
    return kind.from_json(raw) if kind else unique_json(raw)


def _root(owner):
    return checked_directory(owner.root / "control/guest-dispatch")


def _plan(owner):
    plan = _json(_root(owner), "plan.json", GuestDispatchPlan)
    m = owner.manifest
    package = verify_guest_inputs(owner.root, m.job, m.launch, m.claim)
    if (
        plan.owner_digest != m.digest
        or plan.package_digest != package.digest
        or plan.watchdog.job_digest != m.job.digest
        or plan.watchdog.launch_digest != m.launch.digest
        or plan.watchdog.runtime.digest != m.launch.runtime_digest
        or plan.watchdog.nonce != m.job.nonce
    ):
        raise StoreError("guest dispatch plan differs from original job/inputs/runtime")
    guard = owner.root / "control/guest-watchdog"
    if (
        _json(guard, "plan.json", GuestWatchdogPlan) != plan.watchdog
        or _json(guard, "ready.json", GuestWatchdogReady) != plan.ready
    ):
        raise StoreError("guest dispatch original watchdog evidence changed")
    return plan, package


def verify_dispatch_document(owner, document, container_id):
    """Pure original start-intent evidence validation, including legacy replay."""
    if not isinstance(document, dict) or set(document) != {"plan", "attached"}:
        raise StoreError("guest dispatch start binding is malformed")
    plan, _ = _plan(owner)
    if (
        document
        != {
            "plan": plan.to_dict(),
            "attached": {"plan_digest": plan.digest, "upgraded": True},
        }
        or plan.container_id != container_id
    ):
        raise StoreError("guest start binding differs from original attached stream")
    if _json(_root(owner), "attached.json") != document["attached"]:
        raise StoreError("guest start lacks original completed attach receipt")
    return plan


def _start_response(owner, plan, state):
    root = _root(owner)
    path = root / "start-response.json"
    if not path.exists() and not path.is_symlink():
        return None, False
    ref = _json(root, path.name, ArtifactRef)
    doc = unique_json(read_bytes(owner.root, ref, max_bytes=65536).decode())
    if (
        not isinstance(doc, dict)
        or set(doc)
        != {
            "plan_digest",
            "start_intent_digest",
            "status",
            "body_digest",
            "body_size",
        }
        or (
            doc["plan_digest"] != plan.digest
            or len(state.events) < 3
            or doc["start_intent_digest"] != state.events[2].digest
            or type(doc["status"]) is not int
            or not 100 <= doc["status"] <= 599
            or type(doc["body_size"]) is not int
            or not 0 <= doc["body_size"] <= 1024 * 1024
        )
    ):
        raise StoreError("guest original start response differs from original intent")
    sha256(doc["body_digest"])
    # A digest is retained for a bounded rejected body without exposing its text.
    return ref, doc["status"] == 204 and doc["body_size"] == 0 and (
        doc["body_digest"] == hashlib.sha256(b"").hexdigest()
    )


def _completion(owner):
    plan, package = _plan(owner)
    state = owner.replay()
    guard = owner.root / "control/guest-watchdog"
    outcome = read_outcome(guard, owner, plan.watchdog)
    response, acknowledged = _start_response(owner, plan, state)
    capture = None
    path = owner.root / "bootstrap-capture.json"
    if path.exists() or path.is_symlink():
        capture = read_capture(owner.root, owner.manifest.job, owner.manifest.launch, package)
    status = "missing" if capture is None else "unverified"
    if capture is not None and acknowledged and state.phase == "cleaned":
        stop = state.observations["stopped"]
        raw = stop["inspect"]["State"]
        if (
            stop["reason"] is None
            and raw["ExitCode"] == 0
            and not raw["OOMKilled"]
            and not raw["Dead"]
            and outcome.result == "absent"
            and outcome.reason in ("owner_finished", "owner_lost")
        ):
            status = "complete"
    return GuestDispatchCompletion(
        "utility-guest-dispatch-completion-v1",
        plan.digest,
        owner.manifest.digest,
        state.events[-1].digest,
        state.phase,
        status,
        response,
        capture,
        outcome,
    )


def read_completion(owner):
    """Cold verification of original completed evidence, without dispatch or writes."""
    saved = _json(_root(owner), "completion.json", GuestDispatchCompletion)
    if saved != _completion(owner):
        raise StoreError("guest dispatch completion differs from original saved evidence")
    return saved


def reconcile_dispatch(owner):
    """Append only derivable lifecycle events from the original watchdog evidence."""
    if not owner._locked:
        raise StoreError("guest dispatch reconciliation requires original owner writer")
    owner._binding()
    root = _root(owner)
    if (root / "completion.json").exists():
        return read_completion(owner)
    plan, _ = _plan(owner)
    outcome = read_outcome(owner.root / "control/guest-watchdog", owner, plan.watchdog)
    state = owner.replay()
    # Missing start intent cannot be recreated after a crash. No new START or
    # attachment is permitted, even when cleanup confirms an unstarted resource.
    if state.phase == "start_intent":
        if state.events[2].dispatch is None:
            raise StoreError("guest dispatch recovery lacks original bound start intent")
        for ref in (outcome.before, outcome.stopped):
            if ref is None:
                continue
            raw = unique_json(read_bytes(owner.root / "control/guest-watchdog", ref).decode())
            try:
                verify_started(raw, owner.manifest.job, owner.manifest.launch)
            except ValueError:
                continue
            state = owner.record("started", raw)
            break
    if state.phase == "started" and outcome.stopped is not None:
        raw = unique_json(
            read_bytes(owner.root / "control/guest-watchdog", outcome.stopped).decode()
        )
        reason = {"deadline": "timeout", "cancelled": "cancelled"}.get(outcome.reason)
        # Journal validation checks ownership, unchanged start and all OCI limits.
        state = owner.record("stopped", {"inspect": raw, "elapsed_seconds": None, "reason": reason})
    if state.phase in ("stopped", "cleanup_intent") and outcome.result == "absent":
        if outcome.stopped is None:
            # Absence cannot fill in a missing terminal observation.
            return _completion(owner)
        raw = unique_json(
            read_bytes(owner.root / "control/guest-watchdog", outcome.stopped).decode()
        )
        if digest(raw) != digest(state.observations["stopped"]["inspect"]):
            raise StoreError("guest cleanup contradicts original terminal observation")
        if state.phase == "stopped":
            state = owner.record("cleanup_intent")
        state = owner.record(
            "cleaned",
            {
                "container_id": plan.container_id,
                "nonce": owner.manifest.job.nonce,
                "removed": True,
                "observed_absent": True,
            },
        )
    completion = _completion(owner)
    if state.phase == "cleaned":
        owner.fault("before_dispatch_completion")
        durable_write(root / "completion.json", completion.to_json().encode())
        owner.fault("after_dispatch_completion")
    return completion


class GuestDispatchController:
    """Single attached dispatch, armed before START; no automatic science retry."""

    def __init__(self, api):
        self.api = api

    def run(self, owner, store, *, deadline, cancelled=None):
        package = _access(owner, store)
        state = owner.replay()
        m = owner.manifest
        if state.phase != "created" or m.launch.runtime_digest != self.api.identity:
            raise StoreError("guest dispatch requires original unstarted creation/runtime")
        root = owner.root / "control/guest-dispatch"
        root.mkdir(mode=0o700)  # Consumed even if arming/attachment later fails.
        guard = session = None
        try:
            guard = arm(owner, store, self.api, deadline=deadline)
            plan = GuestDispatchPlan(
                "utility-guest-dispatch-plan-v1",
                m.digest,
                state.observations["created"]["Id"],
                package.digest,
                guard.plan,
                guard.check_live(),
            )
            durable_write(root / "plan.json", plan.to_json().encode())

            # Suite events are append-only under the retained writer. Revalidate
            # new event files rather than replaying the complete ledger for every
            # short read/write. The external callback is still polled each time.
            def event_names():
                return tuple(sorted(path.name for path in store.events_path.iterdir()))

            cancellation_events = event_names()
            suite_cancelled = False

            def check_cancelled():
                nonlocal cancellation_events, suite_cancelled
                value = False if cancelled is None else cancelled()
                if type(value) is not bool:
                    raise StoreError("guest dispatch cancellation state is invalid")
                current_events = event_names()
                if current_events != cancellation_events:
                    suite_cancelled = store.replay()["cancelled"]
                    cancellation_events = current_events
                return value or suite_cancelled

            def check():
                guard.check_live()
                if check_cancelled():
                    raise GuestAttachCancelled("guest dispatch cancelled")
                if time.monotonic() >= deadline:
                    raise GuestAttachTimeout("guest dispatch original deadline expired")

            check()
            # The immutable plan is attach intent. No attach or stdin transfer is
            # repeated after interruption, even when no model was observed.
            owner.fault("before_guest_attach")
            session = attach(
                self.api._socket_path,
                self.api.profile.api_version,
                plan.container_id,
                deadline=deadline,
                cancelled=check_cancelled,
            )
            owner.fault("after_guest_attach")
            attached = {"plan_digest": plan.digest, "upgraded": True}
            durable_write(root / "attached.json", canonical_json(attached).encode())
            document = {"plan": plan.to_dict(), "attached": attached}
            verify_dispatch_document(owner, document, plan.container_id)
            ref = put_bytes(
                owner.root,
                canonical_json(document).encode(),
                name="dispatch-binding.json",
                media_type="application/json",
                producer="guest-dispatch",
            )
            check()
            original = self.api.inspect(
                plan.container_id, deadline=deadline, cancelled=check_cancelled
            )
            verify_created(original, m.job, m.launch)
            owner.record("start_intent", dispatch=ref)
            owner.fault("before_daemon_start")
            check()
            observed_start = time.monotonic()
            status, raw = self.api._request(
                "POST",
                f"/containers/{plan.container_id}/start",
                deadline=deadline,
                cancelled=check_cancelled,
            )
            owner.fault("after_daemon_start")
            response = {
                "plan_digest": plan.digest,
                "start_intent_digest": owner.replay().events[2].digest,
                "status": status,
                "body_digest": hashlib.sha256(raw).hexdigest(),
                "body_size": len(raw),
            }
            response_ref = put_bytes(
                owner.root,
                canonical_json(response).encode(),
                name="start-response-record.json",
                media_type="application/json",
                producer="guest-dispatch",
            )
            durable_write(root / "start-response.json", response_ref.to_json().encode())
            owner.fault("start_response_saved")
            if not _start_response(owner, plan, owner.replay())[1]:
                raise StoreError("guest original start acknowledgement is unverified")
            original = self.api.inspect(
                plan.container_id, deadline=deadline, cancelled=check_cancelled
            )
            owner.record("started", original)
            check()
            owner.fault("before_guest_input")
            session.send_once(
                encode_request(owner),
                job_digest=m.job.digest,
                launch_digest=m.launch.digest,
                package_digest=package.digest,
            )
            owner.fault("after_guest_input")
            capture_response(owner.root, session, m.job, m.launch, package)
            owner.fault("guest_capture_saved")
            while True:
                check()
                original = self.api.inspect(
                    plan.container_id, deadline=deadline, cancelled=check_cancelled
                )
                state = verify_started(original, m.job, m.launch)
                if not state["Running"]:
                    break
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
            # This surviving owner measures its dispatch-to-stop interval.
            # Recovery preserves unknown time if this original record is absent.
            owner.record(
                "stopped",
                {
                    "inspect": original,
                    "elapsed_seconds": time.monotonic() - observed_start,
                    "reason": None,
                },
            )
            owner.record("cleanup_intent")
            check()
            guard.finish()
            guard.outcome(timeout=CLEANUP_SECONDS + 2)
            return reconcile_dispatch(owner)
        except BaseException as error:
            if guard is not None:
                try:
                    if isinstance(error, GuestAttachCancelled):
                        guard.cancel()
                except Exception:
                    pass
            raise
        finally:
            if session is not None:
                session.close()
            if guard is not None:
                guard.close_owner()
                # Preserve the original dispatch error. The independent guard
                # retains any unverified cleanup for explicit reconciliation.
                try:
                    guard.outcome(timeout=CLEANUP_SECONDS + 2)
                except Exception:
                    pass
