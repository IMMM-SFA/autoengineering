"""Durable authored lifecycle evidence, not a launcher or actual container test."""

from dataclasses import replace
import json
import shutil
import socket
import subprocess
import time
import sys

import pytest

from autoengineering.campaign.store import StoreError, WriterBusy
from autoengineering.utility.guest_owner import GuestOwnerJournal, OPERATIONS
import test_utility_guest_observations as observation_fixture

metadata = observation_fixture.metadata


def prepared(tmp_path, metadata, *, fault=None):
    suite, job, launch, archive, _, _ = observation_fixture.setup(tmp_path, metadata)
    owner = GuestOwnerJournal.create(
        tmp_path / "owner", job, launch, suite_root=suite, claim=archive.claim, fault=fault
    )
    captures = observation_fixture.captures(job, launch)
    payloads = (
        captures["image"],
        captures["created"],
        None,
        captures["started"],
        {"inspect": captures["stopped"], "reason": None, "elapsed_seconds": None},
        None,
        captures["cleanup"],
    )
    return owner, suite, payloads


def append(owner, payloads, begin=0, end=7):
    with owner.writer():
        for operation, value in zip(OPERATIONS[begin:end], payloads[begin:end], strict=True):
            owner.record(operation, value)


def test_original_lifecycle_recovery_relocates_without_execution(tmp_path, metadata, monkeypatch):
    owner, suite, payloads = prepared(tmp_path, metadata)
    assert owner.replay().phase == "ready"
    append(owner, payloads)
    expected = owner.projections()
    assert expected[1].elapsed_seconds is None
    assert expected[0].container_starts == 1
    copy = tmp_path / "relocated"
    shutil.copytree(owner.root, copy)

    def forbidden(*args, **kwargs):
        pytest.fail("owner replay cannot execute, connect or sample a new clock")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    reopened = GuestOwnerJournal(copy)
    assert reopened.projections() == expected
    assert len(reopened.replay().events) == 7
    with reopened.writer(), pytest.raises(StoreError, match="replay copy"):
        reopened.record("create_intent", payloads[0])
    # Even retaining the original suite does not let a relocated owner write.
    reopened = GuestOwnerJournal(copy, suite_root=suite)
    with reopened.writer(), pytest.raises(StoreError, match="replay copy"):
        reopened.record("create_intent", payloads[0])


@pytest.mark.parametrize("index", range(7))
@pytest.mark.parametrize("side", ["before", "after"])
def test_interruption_retains_original_transition_without_reissuing_it(
    tmp_path, metadata, index, side
):
    owner, suite, payloads = prepared(tmp_path, metadata)
    append(owner, payloads, end=index)

    def fail(stage):
        if stage == side + "_" + OPERATIONS[index]:
            raise RuntimeError("authored owner loss")

    owner.fault = fail
    with owner.writer(), pytest.raises(RuntimeError, match="owner loss"):
        owner.record(OPERATIONS[index], payloads[index])
    reopened = GuestOwnerJournal(owner.root, suite_root=suite)
    state = reopened.replay()
    committed = index + (side == "after")
    assert len(state.events) == committed
    assert state.phase == (OPERATIONS[committed - 1] if committed else "ready")
    assert state.create_uncertain == (state.phase == "create_intent")
    assert state.start_uncertain == (state.phase == "start_intent")
    assert len(reopened.replay().events) == committed
    if side == "after":
        with reopened.writer(), pytest.raises(StoreError, match="consumed or out of order"):
            reopened.record(OPERATIONS[index], payloads[index])
    if committed < 7:
        with pytest.raises(StoreError, match="incomplete"):
            reopened.projections()


def test_same_claim_cannot_create_another_owner_directory(tmp_path, metadata):
    owner, suite, _ = prepared(tmp_path, metadata)
    manifest = owner.manifest
    with pytest.raises(StoreError, match="already has an owner"):
        GuestOwnerJournal.create(
            tmp_path / "another",
            manifest.job,
            manifest.launch,
            suite_root=suite,
            claim=manifest.claim,
        )
    assert not (tmp_path / "another").exists()


def test_loss_after_owner_claim_does_not_release_it(tmp_path, metadata):
    suite, job, launch, archive, _, _ = observation_fixture.setup(tmp_path, metadata)

    def fail(stage):
        if stage == "after_owner_claim":
            raise RuntimeError("authored owner loss")

    with pytest.raises(RuntimeError):
        GuestOwnerJournal.create(
            tmp_path / "owner", job, launch, suite_root=suite, claim=archive.claim, fault=fail
        )
    with pytest.raises(StoreError, match="already has an owner"):
        GuestOwnerJournal.create(
            tmp_path / "another", job, launch, suite_root=suite, claim=archive.claim
        )
    assert not (tmp_path / "owner").exists()


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4, 5, 6, 7])
def test_no_intent_can_be_skipped_or_replayed(tmp_path, metadata, count):
    owner, _, payloads = prepared(tmp_path, metadata)
    append(owner, payloads, end=count)
    index = count - 1 if count else 1
    with owner.writer(), pytest.raises(StoreError, match="consumed or out of order"):
        owner.record(OPERATIONS[index], payloads[index])
    assert len(owner.replay().events) == count


def test_writer_is_required_and_concurrent_owner_is_refused(tmp_path, metadata):
    owner, suite, payloads = prepared(tmp_path, metadata)
    with pytest.raises(StoreError, match="writer lock"):
        owner.record("create_intent", payloads[0])
    another = GuestOwnerJournal(owner.root, suite_root=suite)
    with owner.writer(), pytest.raises(WriterBusy):
        with another.writer():
            pytest.fail("two writers")
    assert not owner.replay().events


@pytest.mark.parametrize(
    "problem", ["claim", "lease", "event", "observation", "sequence", "manifest"]
)
def test_missing_or_changed_original_evidence_refuses(tmp_path, metadata, problem):
    owner, suite, payloads = prepared(tmp_path, metadata)
    append(owner, payloads)
    if problem == "claim":
        path = owner.root / owner.manifest.claim.path
        path.write_bytes(path.read_bytes() + b" ")
    elif problem == "lease":
        path = suite / "inference-owners" / f"{owner.manifest.job.grant.digest}.json"
        path.write_text("{}")
        with owner.writer(), pytest.raises(StoreError, match="owner lease"):
            owner.record("create_intent", payloads[0])
        return
    elif problem == "event":
        path = owner.events_path / "000000000003.json"
        value = json.loads(path.read_text())
        value["event"]["previous"] = "2" * 64
        path.write_text(json.dumps(value))
    elif problem == "observation":
        ref = owner.replay().events[1].observation
        path = owner.root / ref.path
        path.write_bytes(path.read_bytes() + b" ")
    elif problem == "sequence":
        (owner.events_path / "000000000003.json").unlink()
    else:
        value = replace(owner.manifest, owner_scope="2" * 64)
        (owner.root / "owner.json").write_text(value.to_json())
        owner = GuestOwnerJournal(owner.root)
    with pytest.raises(ValueError):
        owner.replay()


@pytest.mark.parametrize("operation", ["created", "started", "stopped", "cleaned"])
def test_foreign_raw_observations_refuse_before_committing(tmp_path, metadata, operation):
    owner, _, payloads = prepared(tmp_path, metadata)
    index = OPERATIONS.index(operation)
    append(owner, payloads, end=index)
    value = json.loads(json.dumps(payloads[index]))
    if operation == "cleaned":
        value["nonce"] = "b" * 32
    elif operation == "stopped":
        value["inspect"]["Id"] = "2" * 64
    else:
        value["Id"] = "2" * 64
        if operation == "created":
            value["Name"] = "/foreign"
    with owner.writer(), pytest.raises(ValueError):
        owner.record(operation, value)
    assert len(owner.replay().events) == index


def test_mutable_caller_capture_cannot_change_committed_evidence(tmp_path, metadata):
    owner, _, payloads = prepared(tmp_path, metadata)
    append(owner, payloads, end=2)
    payloads[1]["State"]["Pid"] = 999
    assert owner.replay().observations["created"]["State"]["Pid"] == 0


def test_oversized_observation_cannot_commit_an_unreadable_event(tmp_path, metadata):
    owner, _, payloads = prepared(tmp_path, metadata)
    payloads[0]["extra"] = "x" * 1048576
    with owner.writer(), pytest.raises(StoreError, match="exceeds limit"):
        owner.record("create_intent", payloads[0])
    assert not owner.replay().events


def test_completed_owner_projects_into_existing_guest_archive(tmp_path, metadata):
    from autoengineering.campaign.artifacts import put_bytes
    from autoengineering.utility.guest_receipts import GuestInferenceArchive, verify_guest_archive

    owner, suite, payloads = prepared(tmp_path, metadata)
    append(owner, payloads)
    original = next(suite.glob("artifacts/*/guest-archive.json"))
    archive = GuestInferenceArchive.from_json(original.read_text())
    refs = []
    for value, name in zip(owner.projections(), ("start", "stop", "cleanup"), strict=True):
        refs.append(
            put_bytes(
                suite,
                value.to_json().encode(),
                name="owned-" + name + ".json",
                media_type="application/json",
                producer="authored-owner",
            )
        )
    archive = replace(archive, start=refs[0], stop=refs[1], cleanup=refs[2])
    ref = put_bytes(
        suite,
        archive.to_json().encode(),
        name="owned-archive.json",
        media_type="application/json",
        producer="authored-owner",
    )
    job, launch = owner.manifest.job, owner.manifest.launch
    result = verify_guest_archive(
        suite,
        ref,
        job.grant,
        source_digest=job.source_digest,
        lock_digest=job.lock.sha256,
        executor_digest=job.executor_digest,
        runtime_digest=launch.runtime_digest,
    )
    assert result.status == "success" and result.lifecycle_seconds is None
    assert result.boundary == "unqualified-candidate"


def test_cold_owner_replay_requires_only_public_saved_bytes(tmp_path, metadata):
    owner, _, payloads = prepared(tmp_path, metadata)
    append(owner, payloads)
    script = """
import importlib.abc,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:
   raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.utility.guest_owner import GuestOwnerJournal
import numpy,subprocess,socket,os,time
def forbidden(*args,**kwargs):raise AssertionError('execution/runtime/array access')
numpy.load=subprocess.Popen=socket.socket=time.monotonic=forbidden
root=Path(sys.argv[1]);allowed={p for p in root.rglob('*') if p.is_file()}
old=Path.open;old_os=os.open
def guarded(path,mode='r',*args,**kwargs):
 if path not in allowed or any(c in mode for c in 'wax+'):raise AssertionError('ungranted access')
 return old(path,mode,*args,**kwargs)
def guarded_os(path,flags,*args,**kwargs):
 if Path(path) not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):
  raise AssertionError('ungranted access')
 return old_os(path,flags,*args,**kwargs)
Path.open=guarded;os.open=guarded_os
owner=GuestOwnerJournal(root)
assert len(owner.replay().events)==7
start,stop,cleanup=owner.projections()
assert start.container_starts==1 and stop.elapsed_seconds is None and cleanup.removed
print(owner.manifest.digest)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(owner.root)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stdout.strip() == owner.manifest.digest
