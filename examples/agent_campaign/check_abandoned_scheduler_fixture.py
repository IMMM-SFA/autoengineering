"""Recover an abandoned native call with no credential read or provider request.

Qualification is stubbed only inside this fixture. The actual fixed subscription
worker is held before its launch gate opens. Only this fixture's supervisor is
killed. The missing lease is never read, and no provider connection is attempted.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

from autoengineering.agents.hosts import brokered_host, command_upstream
from autoengineering.agents.hosts.brokered_host import BrokeredCodexHost
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
from autoengineering.agents.hosts.native_profile import VerifiedNativeProfile
from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.records import ArtifactGrant, HostSelection, TaskAssignment
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.store import WorkerStore
from autoengineering.agents.process import recover_watchdog_stop
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL
from examples.agent_campaign.run import prepare


def profile(root, executable):
    return VerifiedNativeProfile(
        root,
        "0" * 64,
        inspect_brokered_codex(executable),
        OFFLINE_MODEL,
        300,
        65536,
        65536,
        "1" * 64,
    )


def host(root):
    return BrokeredCodexHost(
        qualification_root=root,
        qualification_digest="0" * 64,
        credential_path=root / "no-credential/lease.json",
        lease_id="abandoned-fixture",
        model=OFFLINE_MODEL,
    )


def child(root, executable):
    _, specification = prepare(root / "run")
    specification = replace(
        specification,
        host=HostSelection(
            "codex",
            "subscription",
            OFFLINE_MODEL,
            "2.1",
            "0" * 64,
        ),
    )
    (root / "no-credential").mkdir(mode=0o700)
    store = WorkerStore.create(root / "run/worker", specification)
    with store.writer():
        summary = store.put_private(
            b'{"fixture":"public summary only"}', name="summary.json", media_type="application/json"
        )
    grant = ArtifactGrant(
        "1.0",
        specification.id,
        "investigate",
        "investigator",
        summary,
        "read",
        1024,
        "worker_summary",
    )
    task = TaskAssignment(
        "1.0",
        "investigate",
        specification.id,
        "investigator",
        None,
        0,
        "Propose a supplied intervention using only this fixture summary",
        (grant,),
        "role-handoff-1.0",
        ("propose", "stop"),
        time.time() + 30,
        0,
    )
    original = command_upstream.supervise_process

    def gated(*args, **kwargs):
        callback = kwargs["on_launch"]

        def block(identity):
            callback(identity)
            durable_write(root / "upstream-ready.json", b"{}")
            # Test instrumentation in the supervisor, before the fixed worker
            # can reach credential preflight or any connection code.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                time.sleep(0.02)
            raise TimeoutError("fixture observation expired")

        kwargs["on_launch"] = block
        return original(*args, **kwargs)

    with (
        patch.object(
            brokered_host, "verify_native_profile", return_value=profile(root, executable)
        ),
        patch.object(command_upstream, "supervise_process", side_effect=gated),
    ):
        SerialScheduler(store, host(root)).dispatch(task, campaign_revision=0)


def snapshot(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def wait_for(path, parent=None):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if path.exists():
            return unique_json(path.read_text())
        if parent is not None and parent.poll() is not None:
            raise ValueError("fixture ended before its owned gate was observed")
        time.sleep(0.01)
    raise ValueError("fixture observation deadline expired")


def exercise(root, executable):
    root = Path(root).absolute()
    checked_directory(root.parent)
    root.mkdir(mode=0o700)
    durable_write(root / "fixture-source.py", Path(__file__).read_bytes())
    print("Checking abandoned native scheduler recovery before credential preflight", flush=True)
    with (root / "supervisor.log").open("xb") as log:
        parent = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "examples.agent_campaign.check_abandoned_scheduler_fixture",
                "--child",
                "--output",
                str(root),
                "--executable",
                str(executable),
            ],
            stdout=log,
            stderr=log,
        )
        try:
            wait_for(root / "upstream-ready.json", parent)
            store = WorkerStore(root / "run/worker")
            pending = store.replay().pending[0]
            physical = store.root / "processes" / pending.id
            parent.kill()
            parent.wait(timeout=2)
            for directory in (physical / "transport/client", physical / "upstream/attempt/process"):
                wait_for(directory / "watchdog-result.json")
                assert recover_watchdog_stop(directory)["stopped"]
            assert not (physical / "upstream/attempt/provider-intent.json").exists()
            assert not (root / "no-credential/lease.json").exists()
            before = snapshot(physical)
            with patch.object(
                brokered_host, "verify_native_profile", return_value=profile(root, executable)
            ):
                scheduler = SerialScheduler(store, host(root))
                result = scheduler.recover_invocation(pending.id, campaign_revision=0)
                assert scheduler.recover_invocation(pending.id, campaign_revision=0) == result
            evidence = unique_json(read_bytes(store.root, result.recovery_receipt).decode())
            transport = unique_json((physical / "transport/transport.json").read_text())
            passed = (
                result.state == "host_failure"
                and result.elapsed_seconds is None
                and not result.usage
                and result.resolved_model is None
                and snapshot(physical) == before
                and not store.replay().pending
            )
            receipt = {
                "status": "passed" if passed else "failed",
                "qualification_stubbed": True,
                "host_qualified": False,
                "strict_native_policy": True,
                "executable": str(executable),
                "inventory": transport["inventory"],
                "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "source_identity": host_source_identity(),
                "worker_state": result.state,
                "elapsed_seconds": result.elapsed_seconds,
                "usage": "unknown",
                "native_invocations": len(store.replay().invocations),
                "provider_calls": 0,
                "real_credentials_used": False,
                "credential_preflight_run": False,
                "replay_unchanged": snapshot(physical) == before,
                "recovery_evidence": evidence,
            }
            durable_write(root / "receipt.json", canonical_json(receipt).encode())
            print(f"Abandoned native recovery: {receipt['status']}", flush=True)
            return receipt
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.child:
        child(args.output, args.executable)
        return 0
    return 0 if exercise(args.output, args.executable)["status"] == "passed" else 4


if __name__ == "__main__":
    raise SystemExit(main())
