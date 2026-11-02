"""Public projections of original candidate guest dispatch, without driver capsules.

The original bounded owner reader verifies private execution records before export.
Public readers verify hashes and producer projections, not OS enforcement. Raw OCI
observations and private dispatch plans remain opaque commitments. No default
confirmation service or runtime admission is activated by these archives.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .contracts import sha256
from .guest_bootstrap import GuestBootstrapResponse, MAX_RESULT_HEADER, RESPONSE_MAGIC, _frame
from .guest_dispatch import GuestDispatchCompletion, read_completion
from .guest_owner import GuestOwnerEvent, GuestOwnerManifest, OPERATIONS
from .guest_receipts import (
    GuestDispatchInferenceArchive,
    GuestResultCapture,
    verify_guest_archive,
)
from .inference_execution import FrozenInferenceResult


@dataclass(frozen=True)
class GuestDispatchEvidence(Record):
    """Original public-safe records; unexported observation refs are commitments."""

    schema: Literal["utility-published-guest-dispatch-v1"]
    publisher_digest: str
    owner_scope: str
    package_digest: str
    completion: GuestDispatchCompletion
    events: tuple[GuestOwnerEvent, ...]

    def _validate(self):
        for value in (self.publisher_digest, self.owner_scope, self.package_digest):
            sha256(value)
        c = self.completion
        if (
            len(self.events) != len(OPERATIONS)
            or c.journal_phase != "cleaned"
            or c.watchdog.result != "absent"
            or c.watchdog.absence is None
            or c.watchdog.stopped is None
        ):
            raise ValueError("guest export needs original completed lifecycle and absence")
        head = None
        for sequence, event in enumerate(self.events, 1):
            if (
                event.sequence != sequence
                or event.operation != OPERATIONS[sequence - 1]
                or event.previous != head
                or event.owner_digest != c.owner_digest
            ):
                raise ValueError("guest export original journal chain differs")
            head = event.digest
        if head != c.journal_head:
            raise ValueError("guest export completion differs from original journal head")
        start = self.events[2]
        if start.dispatch is None or start.input_package_digest != self.package_digest:
            raise ValueError("guest export lacks original bound dispatch/input intent")
        if (c.capture is None) != (c.transport_status == "missing"):
            raise ValueError("guest export capture state differs from original completion")


def publisher_identity():
    """Pin the actual exporter implementation before publication; never used cold."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _json(root, ref, kind=None, maximum=65536):
    raw = read_bytes(root, ref, max_bytes=maximum).decode()
    return kind.from_json(raw) if kind else unique_json(raw)


def verify_published_dispatch(
    root,
    archive,
    job,
    launch,
    start,
    stop,
    cleanup,
    capture,
    *,
    publisher_digest,
):
    """Validate explicit producer pins and public projections, without private reads."""
    if publisher_digest is None:
        raise StoreError("guest dispatch archives require an explicit publisher pin")
    sha256(publisher_digest)
    proof = _json(root, archive.dispatch, GuestDispatchEvidence)
    c = proof.completion
    owner = GuestOwnerManifest(
        "utility-guest-owner-v1",
        job,
        launch,
        archive.claim,
        proof.owner_scope,
    )
    if (
        proof.publisher_digest != publisher_digest
        or c.owner_digest != owner.digest
        or c.watchdog.container_id != start.container_id
        or c.watchdog.stopped.sha256 != stop.original_stop_digest
        or proof.events[1].observation.sha256 != start.original_creation_digest
        or proof.events[3].observation.sha256 != start.original_start_digest
        or proof.events[6].observation.sha256 != cleanup.original_cleanup_digest
    ):
        raise StoreError("guest published dispatch differs from original lifecycle/producer")
    raw_cleanup = {
        "container_id": start.container_id,
        "nonce": job.nonce,
        "removed": True,
        "observed_absent": True,
    }
    if digest(raw_cleanup) != cleanup.original_cleanup_digest:
        raise StoreError("guest published cleanup differs from its original commitment")
    if _json(root, c.watchdog.absence) != {
        "plan_digest": c.watchdog.plan_digest,
        "container_id": start.container_id,
        "nonce": job.nonce,
        "observed_absent": True,
    }:
        raise StoreError("guest published absence belongs to another watchdog/container")
    acknowledged = False
    if c.start_response is not None:
        response = _json(root, c.start_response)
        if (
            not isinstance(response, dict)
            or set(response)
            != {
                "plan_digest",
                "start_intent_digest",
                "status",
                "body_digest",
                "body_size",
            }
            or (
                response["plan_digest"] != c.plan_digest
                or response["start_intent_digest"] != proof.events[2].digest
                or type(response["status"]) is not int
                or not 100 <= response["status"] <= 599
                or type(response["body_size"]) is not int
                or not 0 <= response["body_size"] <= 1024 * 1024
            )
        ):
            raise StoreError("guest published start response differs from original intent")
        sha256(response["body_digest"])
        acknowledged = (
            response["status"] == 204
            and response["body_size"] == 0
            and response["body_digest"] == hashlib.sha256(b"").hexdigest()
        )
    if c.capture is None:
        if capture.state != "missing":
            raise StoreError("guest archive invents a captured original result")
    elif (
        c.capture.job_digest != job.digest
        or c.capture.launch_digest != launch.digest
        or c.capture.package_digest != proof.package_digest
        or capture.state != "complete"
        or capture.worker_result != c.capture.worker_result
    ):
        raise StoreError("guest published capture differs from original job/input/result")
    if c.transport_status == "complete" and (
        not acknowledged
        or c.watchdog.reason not in ("owner_finished", "owner_lost")
        or stop.reason is not None
        or stop.exit_code != 0
        or stop.oom_killed
        or stop.dead
        or capture.state != "complete"
    ):
        raise StoreError("guest published completion contradicts transport/stop evidence")
    return c


def verify_published_capture(root, capture, job, launch):
    """Reconstruct the complete original stdio digest using public output bytes."""
    result = _json(root, capture.worker_result, FrozenInferenceResult)
    refs = tuple(ref for ref in (result.outputs, result.predictions) if ref is not None)
    response = GuestBootstrapResponse(
        "utility-guest-bootstrap-response-v1",
        job.digest,
        launch.digest,
        capture.package_digest,
        result,
        refs,
    )
    code = hashlib.sha256(_frame(RESPONSE_MAGIC, response, MAX_RESULT_HEADER))
    for ref in refs:
        code.update(read_bytes(root, ref, max_bytes=64 * 1024 * 1024))
    if code.hexdigest() != capture.response_digest:
        raise StoreError("guest published stdio capture differs from original bytes")


def archive_guest_dispatch(owner, store, *, publisher_digest):
    """Publish only saved original projections and permitted outputs, manifest last."""
    if not owner._locked or not store._locked:
        raise StoreError("guest archive requires original suite and owner writers")
    owner._binding()
    m = owner.manifest
    job = m.job
    if (
        owner.suite_root != store.root
        or (job.source_digest, job.lock.sha256)
        != (
            store.spec.source_digest,
            store.spec.lock_digest,
        )
        or owner.root.is_relative_to(store.root)
        or store.root.is_relative_to(owner.root)
    ):
        raise StoreError("guest archive owner/public/source scopes differ or overlap")
    sha256(publisher_digest)
    arguments = dict(
        source_digest=job.source_digest,
        lock_digest=job.lock.sha256,
        executor_digest=job.executor_digest,
        runtime_digest=m.launch.runtime_digest,
        publisher_digest=publisher_digest,
    )
    directory = store.root / "guest-inference-archives"
    path = directory / (job.grant.digest + ".json")
    if path.exists() or path.is_symlink():
        pointer = confined_file(store.root, str(path.relative_to(store.root)))
        if pointer.stat().st_size > 65536:
            raise StoreError("guest archive pointer exceeds bound")
        from autoengineering.campaign.records import ArtifactRef

        ref = ArtifactRef.from_json(pointer.read_text())
        verify_guest_archive(store.root, ref, job.grant, **arguments)
        original = _json(store.root, ref, GuestDispatchInferenceArchive)
        if (
            _json(store.root, original.job, maximum=4 * 1024 * 1024) != job.to_dict()
            or original.claim != m.claim
        ):
            raise StoreError("guest archive pointer differs from original owned job")
        return ref
    if publisher_identity() != publisher_digest:
        raise StoreError("guest publisher implementation changed before publication")
    completion = read_completion(owner)
    state = owner.replay()
    if state.phase != "cleaned":
        raise StoreError("guest archive cannot invent missing start/stop/cleanup proof")
    start, stop, cleanup = owner.projections()
    proof = GuestDispatchEvidence(
        "utility-published-guest-dispatch-v1",
        publisher_digest,
        m.owner_scope,
        state.input_package_digest,
        completion,
        state.events,
    )
    if completion.watchdog.stopped.sha256 != stop.original_stop_digest:
        raise StoreError("guest archive watchdog contradicts original stop")
    # Original public claim/environment must already exist, rather than falling
    # back to original sources, drivers, private directories or a new package.
    if read_bytes(store.root, m.claim) != read_bytes(owner.root, m.claim):
        raise StoreError("guest archive differs from original public claim")
    read_bytes(store.root, job.environment, max_bytes=4 * 1024 * 1024)
    intent_path = owner.root / "control/guest-dispatch/archive-intent.json"
    intent = {
        "owner_digest": m.digest,
        "completion_digest": completion.digest,
        "publisher_digest": publisher_digest,
        "suite_digest": store.spec.digest,
    }
    if intent_path.exists() or intent_path.is_symlink():
        old = confined_file(owner.root, str(intent_path.relative_to(owner.root)))
        if old.stat().st_size > 65536 or unique_json(old.read_text()) != intent:
            raise StoreError("guest archive original publication intent differs")
    else:
        owner.fault("before_guest_archive_intent")
        durable_write(intent_path, canonical_json(intent).encode())
        owner.fault("after_guest_archive_intent")

    def save(record, name):
        return put_bytes(
            store.root,
            record.to_json().encode(),
            name=name,
            media_type="application/json",
            producer="guest-dispatch-archive",
        )

    def copy(ref, maximum=64 * 1024 * 1024, *, origin=None):
        saved = put_bytes(
            store.root,
            read_bytes(owner.root if origin is None else origin, ref, max_bytes=maximum),
            name=Path(ref.path).name,
            media_type=ref.media_type,
            producer=ref.producer,
        )
        if saved != ref:
            raise StoreError("guest archive cannot change original result references")
        return saved

    result = None
    captured = completion.capture
    worker = copy(captured.worker_result, 65536) if captured is not None else None
    capture = GuestResultCapture(
        "utility-guest-result-capture-v1",
        job.digest,
        job.nonce,
        "missing" if captured is None else "complete",
        worker,
        None if worker is None else worker.sha256,
    )
    if captured is not None:
        result = _json(owner.root, captured.worker_result, FrozenInferenceResult)
    outputs = predictions = None
    if completion.transport_status == "complete" and result is not None:
        outputs = copy(result.outputs) if result.outputs is not None else None
        predictions = copy(result.predictions, 1048576) if result.predictions is not None else None
    owner.fault("guest_archive_outputs_saved")
    if completion.start_response is not None:
        copy(completion.start_response, 65536)
    copy(completion.watchdog.absence, 65536, origin=owner.root / "control/guest-watchdog")
    owner.fault("guest_archive_projection_saved")
    binding = {
        "grant": job.grant.digest,
        "executor": job.executor_digest,
        "nonce": job.nonce,
        "job": job.digest,
    }
    original_intent = put_bytes(
        store.root,
        canonical_json(binding).encode(),
        name="guest-intent.json",
        media_type="application/json",
        producer="guest-dispatch-archive",
    )
    archive = GuestDispatchInferenceArchive(
        "utility-guest-inference-archive-v2",
        save(job, "guest-job.json"),
        original_intent,
        m.claim,
        save(m.launch, "guest-launch.json"),
        save(start, "guest-start.json"),
        save(stop, "guest-stop.json"),
        save(cleanup, "guest-cleanup.json"),
        save(capture, "guest-capture.json"),
        outputs,
        predictions,
        save(proof, "guest-dispatch-evidence.json"),
    )
    ref = save(archive, "guest-inference-archive-v2.json")
    verify_guest_archive(store.root, ref, job.grant, **arguments)
    directory.mkdir(mode=0o700, exist_ok=True)
    checked_directory(directory)
    owner.fault("before_guest_archive_publish")
    durable_write(path, ref.to_json().encode())
    owner.fault("after_guest_archive_publish")
    return ref
