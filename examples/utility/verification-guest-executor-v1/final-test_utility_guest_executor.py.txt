"""Guest facade on authored Unix peers, with no actual guest model or admission."""

from contextlib import contextmanager
from dataclasses import replace
from datetime import date
import io
from pathlib import Path
import shutil
import tempfile
import time

import numpy as np
import pytest

from autoengineering.campaign.artifacts import put_bytes, read_arrays, reference
from autoengineering.utility import guest_executor as module
from autoengineering.utility.guest_archive import publisher_identity
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_owner import GuestOwnerJournal
from autoengineering.utility.store import SuiteStore
import test_utility_guest_dispatch as fixture

metadata = fixture.metadata


@contextmanager
def prepared(tmp_path, metadata, *, authorize=True):
    original, grant, plan, environment, profile, _ = metadata
    source = original.root.parent / "source"
    store_root = tmp_path / "suite"
    shutil.copytree(original.root, store_root)
    store = SuiteStore(store_root)
    drivers = tmp_path / "drivers"
    drivers.mkdir(mode=0o700)
    (drivers / "reserved").mkdir(mode=0o700)
    arrays = read_arrays(
        source, reference(source, "forcing.npz", media_type="application/x-npz", producer="author")
    )
    arrays = {name: np.r_[value, np.full(20, value[-1])] for name, value in arrays.items()}
    arrays["day_of_year"] = np.array(
        [
            date.fromisoformat(day).timetuple().tm_yday
            for day in grant.inference.forcing.ports[0].time.dates
        ]
    )
    content = io.BytesIO()
    np.savez(content, **arrays)
    (drivers / "reserved/drivers.npz").write_bytes(content.getvalue())
    (drivers / "private-labels.json").write_text("AUTHORED-PRIVATE-CANARY")
    forcing = reference(
        drivers, "reserved/drivers.npz", media_type="application/x-npz", producer="author"
    )
    grant = replace(
        grant,
        inference=replace(
            grant.inference, forcing=replace(grant.inference.forcing, artifact=forcing)
        ),
    )
    envref = put_bytes(
        store.root,
        environment.to_json().encode(),
        name="environment.json",
        media_type="application/json",
        producer="authored-metadata",
    )
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    with tempfile.TemporaryDirectory(prefix="ae-facade-", dir="/tmp") as folder:
        endpoint = str(Path(folder) / "peer.sock")
        peer = fixture.Peer(endpoint)
        try:
            api = GuestDaemonAPI(
                endpoint,
                api_version="1.48",
                server_digest=fixture.digest(fixture.daemon_fixture.SERVER),
            )
            executor = module.GuestRoutingExecutor(
                store,
                source,
                drivers,
                work,
                sources=plan.source_inventory,
                lock=plan.lock,
                guest=profile,
                environment=envref,
                api=api,
                publisher_digest=publisher_identity(),
            )
            if authorize:
                attempt = "confirmation-" + grant.cell_digest[:48]
                arguments = dict(
                    cell_digest=grant.cell_digest,
                    attempt_id=attempt,
                    child_digest=grant.digest,
                    phase="confirmation",
                )
                with store.writer():
                    store.append(
                        request_id="authored-reserve",
                        operation="reserve",
                        resources=grant.resources,
                        **arguments,
                    )
                    store.append(request_id="authored-start", operation="start", **arguments)
                    ref = put_bytes(
                        store.root,
                        grant.to_json().encode(),
                        name="confirmation-grant.json",
                        media_type="application/json",
                        producer="author",
                    )
                    store.append(
                        request_id="authored-access",
                        operation="confirmation_access",
                        result_digest=ref.sha256,
                        **arguments,
                    )

            def configure(stage):
                if stage == "guest_executor_inputs_ready":
                    owner = GuestOwnerJournal(work / grant.digest, suite_root=store.root)
                    peer.daemon = fixture.daemon_fixture.Daemon(owner)
                    peer.packet = fixture.module.encode_request(owner)
                    peer.response, _ = fixture.bootstrap_fixture.response(tmp_path, owner)

            store.fault = configure
            yield executor, grant, peer, configure
        finally:
            peer.close()


def execute(executor, grant, **kwargs):
    with executor.store.writer():
        return executor.execute(grant, **kwargs)


def test_facade_owns_prepare_create_dispatch_export_and_cold_recovery(
    tmp_path, metadata, monkeypatch
):
    with prepared(tmp_path, metadata) as (executor, grant, peer, _):
        before = executor.store.replay()
        result = execute(executor, grant)
        assert result.status == "success" and result.boundary == "unqualified-candidate"
        assert peer.daemon.creates == peer.starts == peer.inputs == 1
        assert b"AUTHORED-PRIVATE-CANARY" not in peer.packet
        assert executor.store.replay() == before
        init = executor._read_initialization(grant)
        assert init.owner.job.nonce == result.nonce
        assert init.owner.launch.runtime_digest == executor.registration.runtime_digest
        calls = tuple(peer.calls)
        with pytest.raises(ValueError, match="already intended"):
            execute(executor, grant)
        assert tuple(peer.calls) == calls
        archive = executor.archive(grant)
        for root in (executor.work_root, executor.driver_root):
            shutil.rmtree(root)

        def forbidden(*args, **kwargs):
            raise AssertionError("public recovery cannot execute or probe original runtime/source")

        monkeypatch.setattr(executor, "_preflight", forbidden)
        monkeypatch.setattr(executor, "_registration", forbidden)
        monkeypatch.setattr(executor.api, "_identity", forbidden)
        monkeypatch.setattr(executor.api, "_request", forbidden)
        monkeypatch.setattr(module, "publisher_identity", forbidden)
        monkeypatch.setattr(module.time, "monotonic", forbidden)
        assert executor.recover(grant) == result and executor.archive(grant) == archive
        assert tuple(peer.calls) == calls
        monkeypatch.undo()


@pytest.mark.parametrize(
    "point",
    [
        "guest_executor_init_intended",
        "guest_executor_inference-claims_published",
        "guest_executor_inference-owners_published",
        "guest_executor_owner_claim_copied",
        "guest_executor_owner_manifest_saved",
        "guest_executor_owner_ready",
    ],
)
def test_initialization_loss_can_reconcile_metadata_but_never_dispatch(
    tmp_path, metadata, monkeypatch, point
):
    with prepared(tmp_path, metadata) as (executor, grant, peer, configure):
        before = executor.store.replay()

        def interrupt(stage):
            configure(stage)
            if stage == point:
                raise RuntimeError("authored initialization interruption")

        executor.store.fault = interrupt
        with pytest.raises(RuntimeError):
            execute(executor, grant)
        original = executor._read_initialization(grant)
        executor.store.fault = lambda stage: None

        def forbidden(*args, **kwargs):
            raise AssertionError("metadata recovery cannot read drivers/source, clock or daemon")

        monkeypatch.setattr(executor.api, "_request", forbidden)
        monkeypatch.setattr(executor, "_preflight", forbidden)
        monkeypatch.setattr(executor, "_registration", forbidden)
        monkeypatch.setattr(module, "publisher_identity", forbidden)
        monkeypatch.setattr(module.time, "monotonic", forbidden)
        with executor.store.writer():
            owner = executor.reconcile_initialization(grant)
        assert owner.manifest == original.owner and owner.replay().phase == "ready"
        assert not (owner.root / "input-intent.json").exists()
        assert executor.store.replay() == before and not peer.calls
        with executor.store.writer(), pytest.raises(ValueError, match="incomplete"):
            executor.recover(grant)
        with pytest.raises(ValueError, match="already intended"):
            execute(executor, grant)
        monkeypatch.undo()


def test_no_access_reservation_means_no_init_claim_or_daemon(tmp_path, metadata):
    with prepared(tmp_path, metadata, authorize=False) as (executor, grant, peer, _):
        with pytest.raises(ValueError, match="charged access"):
            execute(executor, grant)
        assert not (executor.store.root / "guest-executor-inits").exists()
        assert not peer.calls and not list(executor.work_root.iterdir())


@pytest.mark.parametrize(
    "point,expected",
    [
        ("guest_executor_dispatched", "success"),
        ("guest_capture_saved", "success"),
        ("after_daemon_start", "infrastructure_failure"),
    ],
)
def test_saved_dispatch_recovers_without_original_source_or_driver_reads(
    tmp_path, metadata, monkeypatch, point, expected
):
    with prepared(tmp_path, metadata) as (executor, grant, peer, configure):
        before = executor.store.replay()

        def interrupt(stage):
            configure(stage)
            if stage == point:
                raise RuntimeError("authored post-dispatch loss")

        executor.store.fault = interrupt
        with pytest.raises(RuntimeError):
            execute(executor, grant)
        calls = tuple(peer.calls)
        executor.store.fault = lambda stage: None
        shutil.rmtree(executor.driver_root)

        def forbidden(*args, **kwargs):
            raise AssertionError("saved recovery cannot launch, inspect runtime or refit")

        monkeypatch.setattr(executor, "_preflight", forbidden)
        monkeypatch.setattr(executor, "_registration", forbidden)
        monkeypatch.setattr(executor.api, "_request", forbidden)
        monkeypatch.setattr(module.time, "monotonic", forbidden)
        with executor.store.writer():
            recovered = executor.recover(grant)
        assert recovered.status == expected and tuple(peer.calls) == calls
        assert peer.starts == 1 and executor.store.replay() == before
        if point != "guest_executor_dispatched":
            assert recovered.lifecycle_seconds is None
        assert executor.recover(grant) == recovered
        monkeypatch.undo()


def test_cancellation_after_input_intent_precedes_reserved_driver_read(
    tmp_path, metadata, monkeypatch
):
    from autoengineering.utility import guest_inputs

    with prepared(tmp_path, metadata) as (executor, grant, peer, configure):
        cancelled = False
        driver_reads = 0
        original = guest_inputs.read_bytes

        def observe(stage):
            nonlocal cancelled
            configure(stage)
            if stage == "guest_inputs_intended":
                cancelled = True

        def guard(root, ref, **kwargs):
            nonlocal driver_reads
            if root == executor.driver_root:
                driver_reads += 1
                raise AssertionError("cancelled intent must not read reserved drivers")
            return original(root, ref, **kwargs)

        executor.store.fault = observe
        monkeypatch.setattr(guest_inputs, "read_bytes", guard)
        with pytest.raises(ValueError, match="cancelled"):
            execute(executor, grant, cancelled=lambda: cancelled)
        owner = GuestOwnerJournal(executor.work_root / grant.digest, suite_root=executor.store.root)
        assert (owner.root / "input-intent.json").exists()
        assert not (owner.root / "input-package.json").exists()
        assert driver_reads == 0 and not peer.calls
        with executor.store.writer(), pytest.raises(ValueError, match="incomplete"):
            executor.recover(grant)


def test_preparation_cannot_reset_deadline_before_daemon_creation(tmp_path, metadata, monkeypatch):
    with prepared(tmp_path, metadata) as (executor, grant, peer, configure):
        original_clock = time.monotonic

        def expire(stage):
            configure(stage)
            if stage == "guest_executor_inputs_ready":
                deadline = executor._read_initialization(grant).deadline
                monkeypatch.setattr(module.time, "monotonic", lambda: deadline + 1)

        executor.store.fault = expire
        with pytest.raises(ValueError, match="deadline"):
            execute(executor, grant)
        assert not peer.calls
        owner = GuestOwnerJournal(executor.work_root / grant.digest, suite_root=executor.store.root)
        assert owner.replay().phase == "ready" and (owner.root / "input-package.json").exists()
        monkeypatch.setattr(module.time, "monotonic", original_clock)


@pytest.mark.parametrize("problem", ["publisher", "runtime"])
def test_changed_registration_refuses_before_claim_or_driver_access(tmp_path, metadata, problem):
    with prepared(tmp_path, metadata) as (executor, grant, peer, _):
        if problem == "publisher":
            executor.publisher_digest = "2" * 64
        else:
            executor.api.profile = replace(executor.api.profile, server_digest="2" * 64)
        with pytest.raises(ValueError, match="registration changed"):
            execute(executor, grant)
        assert not (executor.store.root / "guest-executor-inits").exists()
        assert not (executor.store.root / "inference-claims").exists()
        assert not peer.calls


def test_second_workspace_cannot_replace_original_initialization(tmp_path, metadata):
    with prepared(tmp_path, metadata) as (executor, grant, peer, _):

        def interrupt(stage):
            if stage == "guest_executor_init_intended":
                raise RuntimeError("authored original intent")

        executor.store.fault = interrupt
        with pytest.raises(RuntimeError):
            execute(executor, grant)
        other = tmp_path / "other-work"
        other.mkdir(mode=0o700)
        second = module.GuestRoutingExecutor(
            executor.store,
            executor.source_root,
            executor.driver_root,
            other,
            sources=executor.sources,
            lock=executor.lock,
            guest=executor.guest,
            environment=executor.environment,
            api=executor.api,
            publisher_digest=executor.publisher_digest,
        )
        with pytest.raises(ValueError, match="already intended"):
            execute(second, grant)
        with executor.store.writer(), pytest.raises(ValueError, match="original grant/owner"):
            second.reconcile_initialization(grant)
        assert not list(other.iterdir()) and not peer.calls


def test_unknown_partial_files_and_missing_completed_owner_are_not_reset(tmp_path, metadata):
    with prepared(tmp_path, metadata) as (executor, grant, peer, _):

        def interrupt(stage):
            if stage == "guest_executor_inference-owners_published":
                raise RuntimeError("authored partial initialization")

        executor.store.fault = interrupt
        with pytest.raises(RuntimeError):
            execute(executor, grant)
        root = executor.work_root / grant.digest
        root.mkdir(mode=0o700)
        foreign = root / "unknown.bin"
        foreign.write_text("AUTHORED-PRIVATE-CANARY")
        executor.store.fault = lambda stage: None
        with executor.store.writer(), pytest.raises(ValueError, match="unverified files") as error:
            executor.reconcile_initialization(grant)
        assert "AUTHORED-PRIVATE-CANARY" not in str(error.value) and foreign.exists()
        foreign.unlink()  # Only this test's explicitly authored foreign fixture.
        with executor.store.writer():
            owner = executor.reconcile_initialization(grant)
        (owner.root / "owner.json").unlink()  # Simulate loss after durable completion marker.
        with executor.store.writer(), pytest.raises(ValueError):
            executor.reconcile_initialization(grant)
        assert not (root / "owner.json").exists() and not peer.calls


def test_fresh_recovery_only_facade_needs_no_driver_source_api_or_clock(tmp_path, metadata):
    import subprocess
    import sys

    with prepared(tmp_path, metadata) as (executor, grant, peer, _):
        result = execute(executor, grant)
        calls = tuple(peer.calls)
        shutil.rmtree(executor.work_root)
        shutil.rmtree(executor.driver_root)
        script = """
import importlib.abc,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:
   raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
import os,socket,subprocess,time,numpy
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.guest_receipts import VerifiedGuestExecution
from autoengineering.utility.store import SuiteStore
from autoengineering.utility.scoring import ConfirmationGrant
from autoengineering.utility import guest_executor,guest_archive
root=Path(sys.argv[1]);grant=ConfirmationGrant.from_json(sys.argv[2])
expected=VerifiedGuestExecution.from_json(sys.argv[4])
def forbidden(*args,**kwargs):raise AssertionError('execution, source probe, array load or clock')
subprocess.Popen=socket.socket=numpy.load=time.monotonic=time.time=forbidden
guest_executor.publisher_identity=guest_archive.publisher_identity=forbidden
def saved(event,args):
 if event!='open' or isinstance(args[0],int):return
 path=Path(args[0]).resolve();mode,flags=args[1:3]
 if not path.is_relative_to(root):raise AssertionError('ungranted read')
 writing=mode is not None and any(c in mode for c in 'wax+')
 writing=writing or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
 if writing:raise AssertionError('write')
store=SuiteStore(root)
store.replay()  # Initialize public metadata-reader code before the strict read barrier.
sys.addaudithook(saved)
store=SuiteStore(root)
executor=GuestRoutingExecutor.for_recovery(store,grant,Path(sys.argv[3]))
assert executor.source_root is executor.driver_root is executor.api is None
assert executor.recover(grant)==expected
try:executor.execute(grant)
except ValueError as error:assert 'recovery-only' in str(error)
else:raise AssertionError('recovery facade executed')
print('Fresh recovery facade agrees from original public metadata only.')
"""
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                script,
                str(executor.store.root),
                grant.to_json(),
                str(executor.work_root),
                result.to_json(),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert completed.returncode == 0, completed.stderr
        assert "Fresh recovery facade agrees" in completed.stdout
        assert tuple(peer.calls) == calls
