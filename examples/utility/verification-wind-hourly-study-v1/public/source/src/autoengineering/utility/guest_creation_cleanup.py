"""Bounded cleanup of one original creation; never create/start or renew science.

Cancellation does not remove cleanup authority. Immutable CID/image/owner labels
are required before mutation. A missing name after an unknown CREATE response is
not final absence. Unknown outcomes retain charges and cannot become guest scores.
"""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, unique_json
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .contracts import sha256
from .guest_daemon import GuestDaemonProfile, _creation_ref, _creation_document
from .guest_observations import container_name, labels
from .guest_watchdog import _server, _stopped

SECONDS = 10.0


@dataclass(frozen=True)
class GuestCreationCleanupPlan(Record):
    schema: Literal["utility-guest-creation-cleanup-plan-v1"]
    owner_digest: str
    create_intent_digest: str
    runtime: GuestDaemonProfile
    nonce: str
    container_id: str | None
    creation_response: ArtifactRef | None
    began_at: float
    deadline: float

    def _validate(self):
        sha256(self.owner_digest)
        sha256(self.create_intent_digest)
        if self.container_id is not None:
            sha256(self.container_id)
        if len(self.nonce) != 32 or any(c not in "0123456789abcdef" for c in self.nonce):
            raise ValueError("creation cleanup requires original nonce")
        if not 0 < self.deadline - self.began_at <= SECONDS:
            raise ValueError("creation cleanup deadline exceeds its fixed allowance")


@dataclass(frozen=True)
class GuestCreationCleanupOutcome(Record):
    schema: Literal["utility-guest-creation-cleanup-outcome-v1"]
    plan_digest: str
    owner_digest: str
    container_id: str | None
    result: Literal["absent", "creation_unresolved", "foreign_refused", "unverified"]
    before: ArtifactRef | None
    stopped: ArtifactRef | None
    absence: ArtifactRef | None
    foreign: ArtifactRef | None
    kill_intended: bool
    delete_intended: bool
    elapsed_seconds: float | None

    def _validate(self):
        sha256(self.plan_digest)
        sha256(self.owner_digest)
        if self.container_id is not None:
            sha256(self.container_id)
        if self.result == "absent" and (self.container_id is None or self.absence is None):
            raise ValueError("creation cleanup absence requires exact original CID")
        if self.result == "creation_unresolved" and (
            self.container_id is not None or self.absence is None
        ):
            raise ValueError("unresolved creation must preserve named absence and unknown CID")
        if (self.foreign is not None) != (self.result == "foreign_refused"):
            raise ValueError("foreign refusal requires original conflicting observation")
        if self.result in ("foreign_refused", "unverified") and self.absence is not None:
            raise ValueError("unverified cleanup cannot invent absence")
        if self.elapsed_seconds is not None and self.elapsed_seconds < 0:
            raise ValueError("creation cleanup elapsed time must be nonnegative")


def _json(root, name, kind=None):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise StoreError("creation cleanup record exceeds bound")
    return kind.from_json(path.read_text()) if kind else unique_json(path.read_text())


def _response_cid(owner, ref, intent):
    if ref is None:
        return None
    value = _creation_document(owner, ref)
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "owner_digest", "create_intent_digest", "response"}
        or (
            value["schema"] != "utility-guest-daemon-create-response-v1"
            or value["owner_digest"] != owner.manifest.digest
            or value["create_intent_digest"] != intent
            or not isinstance(value["response"], dict)
        )
    ):
        raise StoreError("creation cleanup response differs from original intent")
    cid = value["response"].get("Id")
    sha256(cid)
    # Warnings remain in the original capture. They prohibit start but cannot
    # disable cleanup of an exactly identified, originally owned resource.
    return cid


def _bindings(owner, plan):
    m = owner.manifest
    state = owner.replay()
    if state.phase not in ("create_intent", "created") or (
        plan.owner_digest != m.digest
        or plan.create_intent_digest != state.events[0].digest
        or plan.nonce != m.job.nonce
        or plan.runtime.digest != m.launch.runtime_digest
    ):
        raise StoreError("creation cleanup differs from original unstarted owner")
    response = _response_cid(owner, plan.creation_response, plan.create_intent_digest)
    if response is not None and response != plan.container_id:
        raise StoreError("creation cleanup CID differs from original response")
    if state.phase == "created" and state.observations["created"]["Id"] != plan.container_id:
        raise StoreError("creation cleanup CID differs from original creation")
    return state


def _owned(raw, owner, cid, *, named=False):
    m = owner.manifest
    if (
        not isinstance(raw, dict)
        or raw.get("Id") != cid
        or raw.get("Image") != m.job.guest.image_id
    ):
        raise StoreError("creation cleanup refuses foreign CID/image")
    observed = raw.get("Config", {}).get("Labels")
    if not isinstance(observed, dict) or any(
        observed.get(k) != v for k, v in labels(m.job, m.launch).items()
    ):
        raise StoreError("creation cleanup refuses foreign owner labels")
    if named and raw.get("Name") != "/" + container_name(m.job):
        raise StoreError("creation cleanup original name differs")


def _save(root, name, value):
    return put_bytes(
        root,
        canonical_json(value).encode(),
        name=name,
        media_type="application/json",
        producer="guest-creation-cleanup",
    )


def _intent(root, name, plan, cid):
    value = {"plan_digest": plan.digest, "container_id": cid}
    path = root / name
    if path.exists() or path.is_symlink():
        if _json(root, name) != value:
            raise StoreError("creation cleanup mutation intent changed")
        return False
    durable_write(path, canonical_json(value).encode())
    return True


def _target(root, owner, plan):
    path = root / "target.json"
    if not path.exists() and not path.is_symlink():
        return plan.container_id, None
    value = _json(root, path.name)
    if (
        not isinstance(value, dict)
        or set(value) != {"plan_digest", "container_id", "observation"}
        or value["plan_digest"] != plan.digest
    ):
        raise StoreError("creation cleanup original target differs")
    cid = value["container_id"]
    sha256(cid)
    if plan.container_id is not None and cid != plan.container_id:
        raise StoreError("creation cleanup target changed original CID")
    ref = ArtifactRef.from_dict(value["observation"])
    raw = unique_json(read_bytes(root, ref, max_bytes=1024 * 1024).decode())
    _owned(raw, owner, cid, named=plan.container_id is None)
    return cid, ref


def _absence(root, plan, cid):
    return _save(
        root,
        "observed-absent.json",
        {
            "plan_digest": plan.digest,
            "container_id": cid,
            "nonce": plan.nonce,
            "observed_absent": True,
        },
    )


def _publish(root, owner, plan, cid, result, before, stopped, absence, foreign, *, elapsed):
    value = GuestCreationCleanupOutcome(
        "utility-guest-creation-cleanup-outcome-v1",
        plan.digest,
        owner.manifest.digest,
        cid,
        result,
        before,
        stopped,
        absence,
        foreign,
        (root / "kill-intent.json").is_file(),
        (root / "delete-intent.json").is_file(),
        elapsed,
    )
    owner.fault("before_creation_cleanup_outcome")
    durable_write(root / "outcome.json", value.to_json().encode())
    owner.fault("after_creation_cleanup_outcome")
    return value


def read_creation_cleanup(owner):
    """Cold original result validation; no clock, source/runtime probe or action."""
    root = checked_directory(owner.root / "control/creation-cleanup")
    plan = _json(root, "plan.json", GuestCreationCleanupPlan)
    _bindings(owner, plan)
    outcome = _json(root, "outcome.json", GuestCreationCleanupOutcome)
    cid, _ = _target(root, owner, plan)
    if (outcome.plan_digest, outcome.owner_digest, outcome.container_id) != (
        plan.digest,
        owner.manifest.digest,
        cid,
    ):
        raise StoreError("creation cleanup outcome differs from original plan/target")
    for ref in (outcome.before, outcome.stopped):
        if ref is not None:
            raw = unique_json(read_bytes(root, ref, max_bytes=1024 * 1024).decode())
            _owned(raw, owner, cid)
            if ref == outcome.stopped and not _stopped(raw):
                raise StoreError("creation cleanup terminal observation differs")
    if outcome.foreign is not None:
        raw = unique_json(read_bytes(root, outcome.foreign, max_bytes=1024 * 1024).decode())
        try:
            _owned(
                raw,
                owner,
                cid if cid is not None else raw.get("Id"),
                named=plan.container_id is None,
            )
        except (ValueError, AttributeError, TypeError):
            pass
        else:
            raise StoreError("creation cleanup foreign observation is owned")
    if outcome.absence is not None and unique_json(read_bytes(root, outcome.absence).decode()) != {
        "plan_digest": plan.digest,
        "container_id": cid,
        "nonce": plan.nonce,
        "observed_absent": True,
    }:
        raise StoreError("creation cleanup absence differs from original reference")
    for flag, name in (
        (outcome.kill_intended, "kill-intent.json"),
        (outcome.delete_intended, "delete-intent.json"),
    ):
        if flag != (root / name).is_file() or (root / name).is_symlink():
            raise StoreError("creation cleanup mutation intent missing or changed")
        if flag and _json(root, name) != {"plan_digest": plan.digest, "container_id": cid}:
            raise StoreError("creation cleanup mutation belongs to another original resource")
    return outcome


def cleanup_creation(owner, store, api):
    """Explicit cleanup/resumption within one original 10 s window; no retries."""
    if not owner._locked or not store._locked:
        raise StoreError("creation cleanup requires original suite/owner writers")
    owner._binding()
    m = owner.manifest
    if owner.suite_root != store.root or (m.job.source_digest, m.job.lock.sha256) != (
        store.spec.source_digest,
        store.spec.lock_digest,
    ):
        raise StoreError("creation cleanup original suite/source differs")
    root = owner.root / "control/creation-cleanup"
    if (root / "outcome.json").exists() or (root / "outcome.json").is_symlink():
        return read_creation_cleanup(owner)
    if (owner.root / "control/guest-watchdog").exists() or (
        owner.root / "control/guest-watchdog"
    ).is_symlink():
        raise StoreError("original watchdog owns cleanup; second cleanup authority refused")
    state = owner.replay()
    if state.phase not in ("create_intent", "created"):
        raise StoreError(
            "creation cleanup requires original consumed creation without start intent"
        )
    charged = store.replay()
    attempt = "confirmation-" + m.job.grant.cell_digest[:48]
    allocation = charged["attempts"].get(attempt)
    if (
        allocation is None
        or allocation[1] not in ("started", "finished")
        or attempt not in charged["confirmation_accesses"]
        or (allocation[0].phase, allocation[0].child_digest, allocation[0].resources)
        != ("confirmation", m.job.grant.digest, m.job.grant.resources)
    ):
        raise StoreError("creation cleanup lacks original charged access")
    if m.launch.runtime_digest != api.identity:
        raise StoreError("creation cleanup runtime differs from original launch")
    resumed = root.exists() or root.is_symlink()
    if resumed:
        checked_directory(root)
        plan = _json(root, "plan.json", GuestCreationCleanupPlan)
    else:
        now = time.monotonic()
        ref = state.events[1].daemon_creation if state.phase == "created" else None
        if ref is None:
            ref = _creation_ref(owner)
        cid = (
            state.observations["created"]["Id"]
            if state.phase == "created"
            else _response_cid(owner, ref, state.events[0].digest)
        )
        plan = GuestCreationCleanupPlan(
            "utility-guest-creation-cleanup-plan-v1",
            m.digest,
            state.events[0].digest,
            api.profile,
            m.job.nonce,
            cid,
            ref,
            now,
            now + SECONDS,
        )
        root.mkdir(mode=0o700)
        (root / "artifacts").mkdir(mode=0o700)
        durable_write(root / "plan.json", plan.to_json().encode())
        owner.fault("creation_cleanup_intended")
    _bindings(owner, plan)
    if plan.runtime != api.profile:
        raise StoreError("creation cleanup original API profile changed")
    cid, before = _target(root, owner, plan)
    stopped = absence = foreign = None
    result = "unverified"
    now = time.monotonic()
    if not plan.began_at <= now < plan.deadline:
        return _publish(root, owner, plan, cid, result, before, None, None, None, elapsed=None)
    try:
        _server(api, deadline=plan.deadline)
        raw = api.inspect(
            cid if cid is not None else m.job.nonce, named=cid is None, deadline=plan.deadline
        )
        if raw is None:
            absence = _absence(root, plan, cid)
            result = "absent" if cid is not None else "creation_unresolved"
        else:
            observed = raw.get("Id")
            sha256(observed)
            try:
                _owned(raw, owner, cid or observed, named=cid is None)
            except (ValueError, AttributeError, TypeError):
                foreign = _save(root, "foreign.json", raw)
                result = "foreign_refused"
            else:
                cid = observed
                if before is None:
                    before = _save(root, "cleanup-before.json", raw)
                    durable_write(
                        root / "target.json",
                        canonical_json(
                            {
                                "plan_digest": plan.digest,
                                "container_id": cid,
                                "observation": before.to_dict(),
                            }
                        ).encode(),
                    )
                if not _stopped(raw):
                    if _intent(root, "kill-intent.json", plan, cid):
                        owner.fault("before_creation_cleanup_kill")
                        try:
                            api._request(
                                "POST",
                                f"/containers/{cid}/kill?signal=SIGKILL",
                                deadline=plan.deadline,
                            )
                        except Exception:
                            pass
                        owner.fault("after_creation_cleanup_kill")
                    until = min(plan.deadline, time.monotonic() + 5)
                    while time.monotonic() < until:
                        raw = api.inspect(cid, deadline=plan.deadline)
                        if raw is None or _stopped(raw):
                            break
                        _owned(raw, owner, cid)
                        time.sleep(min(0.05, max(0, until - time.monotonic())))
                if raw is None:
                    absence = _absence(root, plan, cid)
                    result = "absent"
                else:
                    _owned(raw, owner, cid)
                    if _stopped(raw):
                        stopped = _save(root, "cleanup-stopped.json", raw)
                    if _intent(root, "delete-intent.json", plan, cid):
                        owner.fault("before_creation_cleanup_delete")
                        try:
                            api._request(
                                "DELETE", f"/containers/{cid}?force=1&v=0", deadline=plan.deadline
                            )
                        except Exception:
                            pass
                        owner.fault("after_creation_cleanup_delete")
                    remaining = api.inspect(cid, deadline=plan.deadline)
                    if remaining is None:
                        absence = _absence(root, plan, cid)
                        result = "absent"
                    else:
                        _owned(remaining, owner, cid)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception:
        # Fault hooks model owner loss as BaseException. API failure stays saved
        # uncertainty and never authorizes another mutation or scientific start.
        pass
    return _publish(
        root,
        owner,
        plan,
        cid,
        result,
        before,
        stopped,
        absence,
        foreign,
        elapsed=None if resumed else time.monotonic() - plan.began_at,
    )
