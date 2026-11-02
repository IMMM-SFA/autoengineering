"""Abandoned adapter recovery with actual owned groups and no credential read.

The native executable/qualifier/wrapper are synthetic test fixtures. The fixed
subscription command is held behind its launch gate and never reaches preflight.
"""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import autoengineering

from autoengineering.agents.hosts import brokered_host as module
from autoengineering.agents.hosts import abandoned
from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.brokered_host import BrokeredCodexHost
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
from autoengineering.agents.hosts.native_profile import VerifiedNativeProfile
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import read_bytes
from test_agent_brokered_codex import snapshot
from test_agent_process_watchdog import wait_for
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL

PARENT = r"""
from pathlib import Path
import sys,time,pytest
from test_agent_brokered_host import worker
from autoengineering.agents.hosts import command_upstream
from autoengineering.campaign.store import durable_write
root=Path(sys.argv[1])
patch=pytest.MonkeyPatch()
scheduler,task,_,_=worker(root,patch)
patch.delattr(scheduler.host,'_upstream')
original=command_upstream.supervise_process
def gated(*args,**kwargs):
    callback=kwargs['on_launch']
    def block(identity):
        callback(identity)
        durable_write(root/'upstream-ready',b'{}')
        while True: time.sleep(.02)
    kwargs['on_launch']=block
    return original(*args,**kwargs)
patch.setattr(command_upstream,'supervise_process',gated)
scheduler.dispatch(task,campaign_revision=3)
"""


def reopened(root, monkeypatch):
    profile = VerifiedNativeProfile(
        root,
        "0" * 64,
        inspect_brokered_codex(root / "fake-codex"),
        OFFLINE_MODEL,
        300,
        65536,
        65536,
        "1" * 64,
    )
    monkeypatch.setattr(module, "verify_native_profile", lambda *a, **k: profile)
    host = BrokeredCodexHost(
        qualification_root=root,
        qualification_digest="0" * 64,
        credential_path=root / "never-open-auth.json",
        lease_id="unit-lease",
        model=OFFLINE_MODEL,
    )
    return SerialScheduler(WorkerStore(root / "worker"), host, clock=lambda: 101)


@pytest.mark.parametrize(
    "corruption", [None, "request", "policy", "native_job", "owner", "process", "completion"]
)
def test_owner_death_reconciles_as_unknown_failure_without_relaunch(
    tmp_path, monkeypatch, corruption
):
    tmp_path.chmod(0o700)
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        (
            str(Path(__file__).parent),
            str(Path(autoengineering.__file__).resolve().parent.parent),
            str(Path(__file__).parents[1]),
        )
    )
    with (tmp_path / "parent.log").open("xb") as log:
        parent = subprocess.Popen(
            [sys.executable, "-c", PARENT, str(tmp_path)], env=environment, stdout=log, stderr=log
        )
        try:
            wait_for(tmp_path / "upstream-ready", parent, timeout=10)
            scheduler = reopened(tmp_path, monkeypatch)
            pending = scheduler.store.replay().pending[0]
            physical = scheduler.store.root / "processes" / pending.id
            # Ownership is not guessed, and no process is signalled on recovery.
            with pytest.raises(ValueError):
                scheduler.recover_invocation(pending.id, campaign_revision=3)
            assert parent.poll() is None and scheduler.store.replay().pending
            parent.kill()
            parent.wait(timeout=2)
            for directory in (physical / "transport/client", physical / "upstream/attempt/process"):
                assert wait_for(directory / "watchdog-result.json")["stopped"]
                assert not (directory / "completion.json").exists()
            assert not (physical / "upstream/attempt/provider-intent.json").exists()
            assert not (tmp_path / "never-open-auth.json").exists()
            if corruption is not None:
                if corruption == "request":
                    path = physical / "upstream/attempt/request.bin"
                    path.write_bytes(b"changed")
                else:
                    relative = {
                        "policy": "upstream/policy.json",
                        "native_job": "transport/client/job.json",
                        "owner": "transport/client/watchdog-job.json",
                        "process": "transport/client/process.json",
                        "completion": "transport/client/completion.json",
                    }[corruption]
                    path = physical / relative
                    value = json.loads(path.read_text()) if path.exists() else {}
                    if corruption == "policy":
                        value["lease_id"] = "foreign"
                    elif corruption == "owner":
                        value["owner_started"] = "changed"
                    elif corruption == "process":
                        value["nonce"] = "foreign"
                    else:
                        value["extra"] = True
                    path.write_text(json.dumps(value))
                with pytest.raises(ValueError):
                    scheduler.recover_invocation(pending.id, campaign_revision=3)
                assert scheduler.store.replay().pending
                return
            before = snapshot(physical)
            result = scheduler.recover_invocation(pending.id, campaign_revision=3)
            assert result.state == "host_failure"
            assert (
                result.elapsed_seconds is None
                and not result.usage
                and result.resolved_model is None
            )
            assert result.normalized_output is None
            evidence = json.loads(read_bytes(scheduler.store.root, result.recovery_receipt))
            assert evidence["kind"] == "abandoned_brokered_transport"
            assert evidence["usage"] == "unknown" and evidence["raw_result_recovered"] is False
            assert snapshot(physical) == before
            assert not scheduler.store.replay().pending
            assert scheduler.recover_invocation(pending.id, campaign_revision=3) == result
            assert snapshot(physical) == before
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=2)


def test_unknown_elapsed_is_not_zero_and_cannot_be_success():
    assert HostResult("host_failure", "", None, {}, None).elapsed_seconds is None
    with pytest.raises(ValueError, match="duration"):
        HostResult("completed", "{}", None, {}, None)


def test_failed_process_observation_never_proves_owner_death(monkeypatch):
    def fail(*a, **k):
        raise subprocess.CalledProcessError(1, "ps")

    monkeypatch.setattr(abandoned.subprocess, "run", fail)
    with pytest.raises(ValueError, match="unavailable"):
        abandoned._owner_absent(123, "Mon Oct 26 13:00:00 2026")
