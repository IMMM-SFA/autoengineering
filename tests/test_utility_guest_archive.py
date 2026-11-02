"""Dispatch-bound public guest evidence; no actual container or data admission."""

from dataclasses import replace
import shutil
import socket
import subprocess
import time

import numpy as np
import pytest

from autoengineering.campaign.artifacts import put_bytes, read_bytes
from autoengineering.utility import guest_archive as module
from autoengineering.utility.guest_receipts import (
    GuestInferenceArchive,
    GuestDispatchInferenceArchive,
    verify_guest_archive,
)
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.guest_dispatch import reconcile_dispatch
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.scoring import ConfirmationService
import test_utility_guest_dispatch as fixture

metadata = fixture.metadata


def arguments(owner):
    m = owner.manifest
    return dict(
        source_digest=m.job.source_digest,
        lock_digest=m.job.lock.sha256,
        executor_digest=m.job.executor_digest,
        runtime_digest=m.launch.runtime_digest,
        publisher_digest=module.publisher_identity(),
    )


def publish(owner, store, *, pin=None):
    with store.writer(), owner.writer():
        return module.archive_guest_dispatch(
            owner, store, publisher_digest=pin or module.publisher_identity()
        )


@pytest.fixture(scope="module")
def published(tmp_path_factory, metadata):
    path = tmp_path_factory.mktemp("authored-published-guest")
    with fixture.prepared(path, metadata) as (owner, store, api, peer):
        fixture.run(owner, store, api)
        before = {p.relative_to(store.root) for p in store.root.rglob("*") if p.is_file()}
        state = store.replay()
        ref = publish(owner, store)
        after = {p.relative_to(store.root) for p in store.root.rglob("*") if p.is_file()}
        assert store.replay() == state
        return owner, store, ref, arguments(owner), after - before, tuple(peer.calls)


def test_public_export_preserves_original_outputs_without_private_capsule(published, monkeypatch):
    owner, store, ref, args, added, _ = published
    grant = owner.manifest.job.grant
    archive = GuestInferenceArchive.from_json(read_bytes(store.root, ref).decode())
    assert isinstance(archive, GuestDispatchInferenceArchive)
    from types import MappingProxyType

    assert GuestInferenceArchive.from_dict(MappingProxyType(archive.to_dict())) == archive
    result = verify_guest_archive(store.root, ref, grant, **args)
    assert result.status == "success" and result.boundary == "unqualified-candidate"
    assert result.container_starts == 1 and result.lifecycle_seconds > 0
    proof = module.GuestDispatchEvidence.from_json(
        read_bytes(store.root, archive.dispatch).decode()
    )
    assert proof.completion == module.read_completion(owner)
    assert result.result.predictions == archive.predictions
    for path in added:
        assert path.name not in {
            "drivers.npz",
            "guest-inputs.tar",
            "input-package.json",
            "plan.json",
            "owner.json",
            "cleanup-before.json",
            "cleanup-stopped.json",
            "private-labels.json",
        }
        raw = (store.root / path).read_bytes()
        assert b"AUTHORED-PRIVATE-CANARY" not in raw
        for private in (owner.root, store.root.parent / "drivers"):
            assert str(private).encode() not in raw

    def forbidden(*args, **kwargs):
        raise AssertionError("saved publication cannot rerun or probe source/runtime")

    monkeypatch.setattr(module, "publisher_identity", forbidden)
    monkeypatch.setattr(np, "load", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    assert publish(owner, store, pin=args["publisher_digest"]) == ref
    assert verify_guest_archive(store.root, ref, grant, **args) == result


@pytest.mark.parametrize(
    "pin", ["publisher_digest", "source_digest", "lock_digest", "executor_digest", "runtime_digest"]
)
def test_wrong_explicit_pins_cannot_verify_guest_dispatch(published, pin):
    owner, store, ref, args, _, _ = published
    with pytest.raises(ValueError):
        verify_guest_archive(store.root, ref, owner.manifest.job.grant, **(args | {pin: "2" * 64}))
    if pin == "publisher_digest":
        unpinned = {k: v for k, v in args.items() if k != pin}
        with pytest.raises(ValueError, match="explicit publisher"):
            verify_guest_archive(store.root, ref, owner.manifest.job.grant, **unpinned)


def test_public_archive_relocates_without_owner_capsule_or_execution(
    tmp_path, published, monkeypatch
):
    owner, store, ref, args, _, _ = published
    destination = tmp_path / "public-copy"
    shutil.copytree(store.root, destination)
    expected = verify_guest_archive(destination, ref, owner.manifest.job.grant, **args)

    def forbidden(*args, **kwargs):
        raise AssertionError(
            "cold public verification must not execute, load arrays or sample time"
        )

    monkeypatch.setattr(module, "read_completion", forbidden)
    monkeypatch.setattr(module, "publisher_identity", forbidden)
    monkeypatch.setattr(np, "load", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    assert verify_guest_archive(destination, ref, owner.manifest.job.grant, **args) == expected


def test_late_cancellation_with_complete_capture_cannot_become_score_input(tmp_path, metadata):
    with fixture.prepared(tmp_path, metadata) as (owner, store, api, peer):
        stopped = False

        def observe(stage):
            nonlocal stopped
            if stage == "after_stopped":
                stopped = True

        owner.fault = observe
        with pytest.raises(ValueError):
            fixture.run(owner, store, api, cancelled=lambda: stopped)
        owner = GuestOwnerJournal(owner.root, suite_root=store.root)
        with owner.writer():
            original = reconcile_dispatch(owner)
        assert original.capture and original.transport_status == "unverified"
        assert owner.replay().observations["stopped"]["reason"] is None
        ref = publish(owner, store)
        args = arguments(owner)
        result = verify_guest_archive(store.root, ref, owner.manifest.job.grant, **args)
        assert result.status == "infrastructure_failure" and result.result is None
        archive = GuestInferenceArchive.from_json(read_bytes(store.root, ref).decode())
        assert archive.outputs is None and archive.predictions is None
        proof = module.GuestDispatchEvidence.from_json(
            read_bytes(store.root, archive.dispatch).decode()
        )
        assert proof.completion.capture and proof.completion.watchdog.reason == "cancelled"
        # A rewritten producer projection cannot upgrade this captured cancellation.
        forged = replace(proof, completion=replace(proof.completion, transport_status="complete"))
        proof_ref = put_bytes(
            store.root,
            forged.to_json().encode(),
            name="forged-proof.json",
            media_type="application/json",
            producer="authored-forgery",
        )
        forged_archive = replace(archive, dispatch=proof_ref)
        forged_ref = put_bytes(
            store.root,
            forged_archive.to_json().encode(),
            name="forged-archive.json",
            media_type="application/json",
            producer="authored-forgery",
        )
        with pytest.raises(ValueError):
            verify_guest_archive(store.root, forged_ref, owner.manifest.job.grant, **args)
        assert peer.starts == 1


def test_default_confirmation_service_does_not_admit_published_candidate(published):
    owner, store, _, _, _, _ = published
    grant = owner.manifest.job.grant
    outcome = OutcomeSpec("engineering-outcome-v1", "rmse", "mm/day", "minimize", "mean", "1" * 64)
    before = store.replay()

    def forbidden(*args):
        raise AssertionError("candidate archive cannot authorize private scoring")

    service = ConfirmationService(
        store, forbidden, scorer_digest=grant.scorer_digest, outcome_contract=outcome
    )
    with pytest.raises(ValueError, match="vector-only"):
        service.confirm(grant)
    with pytest.raises(ValueError, match="vector-only"):
        service.recover(grant)
    assert store.replay() == before


@pytest.mark.parametrize(
    "point",
    [
        "before_guest_archive_intent",
        "after_guest_archive_intent",
        "guest_archive_outputs_saved",
        "guest_archive_projection_saved",
        "before_guest_archive_publish",
        "after_guest_archive_publish",
    ],
)
def test_publication_interruption_reuses_saved_evidence_without_new_start(
    tmp_path, metadata, point
):
    with fixture.prepared(tmp_path, metadata) as (owner, store, api, peer):
        fixture.run(owner, store, api)
        args = arguments(owner)
        state = store.replay()
        calls = tuple(peer.calls)

        def fail(stage):
            if stage == point:
                raise RuntimeError("authored publication loss")

        owner.fault = fail
        with pytest.raises(RuntimeError, match="authored publication loss"):
            publish(owner, store, pin=args["publisher_digest"])
        reopened = GuestOwnerJournal(owner.root, suite_root=store.root)
        ref = publish(reopened, store, pin=args["publisher_digest"])
        result = verify_guest_archive(store.root, ref, reopened.manifest.job.grant, **args)
        assert result.status == "success" and peer.starts == peer.inputs == 1
        assert publish(reopened, store, pin=args["publisher_digest"]) == ref
        assert tuple(peer.calls) == calls and store.replay() == state


@pytest.mark.parametrize(
    "field",
    [
        "publisher",
        "stop",
        "journal",
        "capture",
        "input",
        "cancel",
        "status",
        "response",
    ],
)
def test_tampered_public_projection_cannot_reclassify_original_execution(
    tmp_path, published, field
):
    owner, store, ref, args, _, _ = published
    root = tmp_path / "public"
    shutil.copytree(store.root, root)
    archive = GuestInferenceArchive.from_json(read_bytes(root, ref).decode())
    doc = module.unique_json(read_bytes(root, archive.dispatch).decode())
    if field == "publisher":
        doc["publisher_digest"] = "2" * 64
    elif field == "stop":
        doc["completion"]["watchdog"]["stopped"]["sha256"] = "2" * 64
    elif field == "journal":
        doc["events"][1]["observation"]["sha256"] = "2" * 64
    elif field == "capture":
        doc["completion"]["capture"]["response_digest"] = "2" * 64
    elif field == "input":
        doc["package_digest"] = "2" * 64
    elif field == "cancel":
        doc["completion"]["watchdog"]["reason"] = "cancelled"
    elif field == "status":
        doc["completion"]["transport_status"] = "unverified"
    else:
        doc["completion"]["start_response"]["sha256"] = "2" * 64
    proof = put_bytes(
        root,
        module.canonical_json(doc).encode(),
        name="forged-proof.json",
        media_type="application/json",
        producer="authored-forgery",
    )
    forged = replace(archive, dispatch=proof)
    alternate = put_bytes(
        root,
        forged.to_json().encode(),
        name="forged-archive.json",
        media_type="application/json",
        producer="authored-forgery",
    )
    with pytest.raises(ValueError):
        verify_guest_archive(root, alternate, owner.manifest.job.grant, **args)


def test_unobserved_start_remains_charged_without_exported_started_receipt(tmp_path, metadata):
    with fixture.prepared(tmp_path, metadata) as (owner, store, api, peer):
        before = store.replay()

        def fail(stage):
            if stage == "after_start_intent":
                raise RuntimeError("authored uncertain start")

        owner.fault = fail
        with pytest.raises(RuntimeError):
            fixture.run(owner, store, api)
        reopened = GuestOwnerJournal(owner.root, suite_root=store.root)
        with reopened.writer():
            incomplete = reconcile_dispatch(reopened)
        assert incomplete.journal_phase == "start_intent" and peer.starts == 0
        with pytest.raises(ValueError):
            publish(reopened, store)
        assert store.replay() == before
        assert not (store.root / "guest-inference-archives").exists()


def test_legacy_local_archive_reader_cannot_accept_guest_dispatch(published):
    from autoengineering.utility.inference_evidence import verify_inference_archive

    owner, store, ref, args, _, _ = published
    with pytest.raises(ValueError):
        verify_inference_archive(
            store.root,
            ref,
            owner.manifest.job.grant,
            args["executor_digest"],
            args["source_digest"],
            args["lock_digest"],
        )


@pytest.mark.parametrize(
    "status", ["scientific_infeasible", "model_failure", "infrastructure_failure"]
)
def test_original_worker_failure_status_is_not_replaced_by_transport_success(
    tmp_path, metadata, status
):
    with fixture.prepared(tmp_path, metadata) as (owner, store, api, peer):
        adverse = tmp_path / "adverse"
        adverse.mkdir(mode=0o700)
        peer.response, original = fixture.bootstrap_fixture.response(adverse, owner, status=status)
        dispatched = fixture.run(owner, store, api)
        assert dispatched.transport_status == "complete"
        ref = publish(owner, store)
        result = verify_guest_archive(store.root, ref, owner.manifest.job.grant, **arguments(owner))
        assert result.status == status and result.result == original
        archive = GuestInferenceArchive.from_json(read_bytes(store.root, ref).decode())
        assert archive.predictions is None and peer.starts == peer.inputs == 1


@pytest.mark.parametrize(
    "problem,expected",
    [
        ("lost_start", "infrastructure_failure"),
        ("truncated", "infrastructure_failure"),
        ("idle", "timeout"),
    ],
)
def test_failed_or_timed_out_dispatch_exports_no_scoring_outputs(
    tmp_path, metadata, problem, expected
):
    with fixture.prepared(tmp_path, metadata) as (owner, store, api, peer):
        peer.problem = problem
        with pytest.raises(ValueError):
            fixture.run(owner, store, api)
        owner = GuestOwnerJournal(owner.root, suite_root=store.root)
        with owner.writer():
            completion = reconcile_dispatch(owner)
        calls = tuple(peer.calls)
        assert completion.journal_phase == "cleaned"
        ref = publish(owner, store)
        result = verify_guest_archive(store.root, ref, owner.manifest.job.grant, **arguments(owner))
        archive = GuestInferenceArchive.from_json(read_bytes(store.root, ref).decode())
        assert result.status == expected and result.result is None
        assert result.lifecycle_seconds is None
        assert archive.outputs is None and archive.predictions is None
        assert tuple(peer.calls) == calls and peer.starts == 1
