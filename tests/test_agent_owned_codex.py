"""Version 2.1 native ownership, startup receipts and supervisor death."""

import json
import os
import socket
import subprocess
import sys
import time

import pytest

from autoengineering.agents.hosts.codex_brokered import (
    OWNED_VERSION,
    execute_brokered_codex,
    recover_brokered_transport,
)
from autoengineering.agents.process import recover_watchdog_stop
from autoengineering.campaign.execution import ProcessIdentity, identity_matches, live_members
from examples.agent_campaign.probe_external_codex import response_stream
from test_agent_brokered_codex import prepare, snapshot
from test_agent_process_watchdog import wait_for


@pytest.mark.parametrize(
    "mode,expected",
    [
        ("normal", "completed"),
        ("sleep", "timeout"),
        ("partial", "host_failure"),
        ("flood", "host_failure"),
    ],
)
def test_owned_native_profile_replays_with_verified_watchdog(tmp_path, mode, expected):
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream()

    result = execute_brokered_codex(
        **prepare(tmp_path, mode=mode, seconds=0.7 if mode == "sleep" else 3),
        upstream=upstream,
        owned_native=True,
    )
    assert result.host_result.status == expected and result.host_result.stop_verified
    assert json.loads((result.root / "transport.json").read_text())["version"] == OWNED_VERSION
    assert recover_watchdog_stop(result.root / "client")["stopped"]
    before = snapshot(result.root)
    assert recover_brokered_transport(result.root).host_result == result.host_result
    assert before == snapshot(result.root)
    assert len(calls) == (0 if mode == "sleep" else 1)


def test_owned_native_watchdog_cannot_be_downgraded_in_recovery(tmp_path):
    result = execute_brokered_codex(
        **prepare(tmp_path), upstream=lambda _: response_stream(), owned_native=True
    )
    manifest = result.root / "transport.json"
    value = json.loads(manifest.read_text())
    value["version"] = "codex-text-2.0"
    manifest.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="binding"):
        recover_brokered_transport(result.root)


@pytest.mark.parametrize("failure", ["trampoline", "startup", "launch_ack", "blocked_ack"])
def test_owned_native_startup_and_ack_faults_never_request_upstream(tmp_path, monkeypatch, failure):
    import autoengineering.agents.process as supervisor

    original = subprocess.Popen

    def popen(command, *args, **kwargs):
        if failure == "trampoline" and any(
            str(arg).endswith("process_worker.py") for arg in command
        ):
            raise OSError("authored trampoline startup failure")
        if failure == "startup" and any(
            str(arg).endswith("process_watchdog.py") for arg in command
        ):
            raise OSError("authored watchdog startup failure")
        return original(command, *args, **kwargs)

    def launched(_):
        if failure == "launch_ack":
            raise OSError("authored ownership ack loss")
        if failure == "blocked_ack":
            time.sleep(0.8)

    args = prepare(tmp_path, launched=launched, seconds=0.4 if failure == "blocked_ack" else 3)
    monkeypatch.setattr(supervisor.subprocess, "Popen", popen)
    if failure == "launch_ack":
        with pytest.raises(OSError, match="ack loss"):
            execute_brokered_codex(
                **args, owned_native=True, upstream=lambda _: pytest.fail("gated callback")
            )
        result = recover_brokered_transport(tmp_path / "transport")
    else:
        result = execute_brokered_codex(
            **args, owned_native=True, upstream=lambda _: pytest.fail("gated callback")
        )
    assert result.host_result.status == ("timeout" if failure == "blocked_ack" else "host_failure")
    assert result.host_result.stop_verified
    assert result.exchange_result.provider_requests_reserved == 0
    assert not (result.root / "client/launch-gate.json").exists()


@pytest.mark.parametrize("during_upstream", [False, True])
def test_owner_death_stops_native_and_active_upstream_without_fabricating_completion(
    tmp_path, during_upstream
):
    prepare(tmp_path, mode="normal" if during_upstream else "sleep")
    source = tmp_path / "authored-upstream.py"
    source.write_text(
        "from pathlib import Path\nimport sys,time\nPath(sys.argv[3]).touch()\ntime.sleep(20)\n"
    )
    launcher = r"""
from pathlib import Path
import sys,time
from autoengineering.agents.hosts.base import InvocationContext
from autoengineering.agents.hosts.codex_brokered import execute_brokered_codex,inspect_brokered_codex
from autoengineering.agents.hosts.command_upstream import CommandUpstream
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL
root=Path(sys.argv[1])
source=root/'authored-upstream.py'
callback=CommandUpstream(root/'upstream',command=(sys.executable,'-I','-S',str(source),'{request}','{response}',str(root/'upstream-started')),source_files=(source,),deadline_monotonic=time.monotonic()+20)
context=InvocationContext('owned-death','owned-death-nonce',root/'transport',20,65536,lambda _:None,lambda:False)
execute_brokered_codex(inspect_brokered_codex(root/'fake-codex'),model=OFFLINE_MODEL,schema=root/'workspace/schema.json',workspace=root/'workspace',home=root/'home',prompt=b'approved brokered prompt',context=context,upstream=callback,boundary_identity='0'*64,wrap_command=lambda command,_:command,owned_native=True)
"""
    parent = subprocess.Popen(
        [sys.executable, "-c", launcher, str(tmp_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    roots = [tmp_path / "transport/client"]
    identities = []
    try:
        wait_for(roots[0] / "launch-gate.json", parent)
        if during_upstream:
            roots.append(tmp_path / "upstream/process")
            wait_for(roots[1] / "launch-gate.json", parent)
        marker = tmp_path / ("upstream-started" if during_upstream else "native-started")
        deadline = time.monotonic() + 3
        while not marker.exists() and parent.poll() is None and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists()
        identities = [ProcessIdentity(**wait_for(root / "process.json")) for root in roots]
        parent.kill()
        parent.wait(timeout=2)
        endpoint = json.loads((tmp_path / "transport/endpoint/endpoint.json").read_text())
        with pytest.raises(OSError):
            socket.create_connection((endpoint["address"], endpoint["port"]), timeout=0.2)
        for root, identity in zip(roots, identities):
            assert wait_for(root / "watchdog-result.json")["stopped"]
            assert recover_watchdog_stop(root)["stopped"]
            assert not live_members(identity.pgid)
            assert not (root / "completion.json").exists()
        with pytest.raises(ValueError):
            recover_brokered_transport(tmp_path / "transport")
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=2)
        for identity in identities:
            if identity_matches(identity):
                os.killpg(identity.pgid, 9)
