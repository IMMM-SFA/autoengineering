"""Opt-in hard process ownership survives a dead or blocked supervisor."""

import hashlib
import json
import os
import signal
import subprocess
import sys
import time

import pytest

from autoengineering.agents import process_watchdog
from autoengineering.agents.process import (
    read_completion,
    recover_completed_process,
    recover_watchdog_stop,
    supervise_process,
)
from autoengineering.campaign.execution import ProcessIdentity, identity_matches, live_members
from test_agent_process import run


@pytest.mark.parametrize("concurrent_stop", [False, True])
def test_denied_stop_requires_observed_group_disappearance(tmp_path, monkeypatch, concurrent_stop):
    from autoengineering.agents import process as supervisor

    nonce = "denied-stop-race"
    target = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)", "--nonce", nonce],
        start_new_session=True,
    )
    killpg = os.killpg
    calls = []

    def denied(pgid, sig):
        assert pgid == target.pid
        calls.append(sig)
        if concurrent_stop:
            killpg(pgid, signal.SIGKILL)
            target.wait(timeout=2)
        raise PermissionError("simulated concurrent stop or denied signal")

    try:
        description = supervisor._process_description(target.pid)
        assert description is not None
        identity = ProcessIdentity(target.pid, target.pid, nonce, description[0])
        with monkeypatch.context() as scoped:
            scoped.setattr(supervisor.os, "killpg", denied)
            assert supervisor._stop_owned(target, identity, 0.05) is concurrent_stop
        assert len(calls) == 1
        assert bool(live_members(target.pid)) is not concurrent_stop
    finally:
        if target.poll() is None:
            killpg(target.pid, signal.SIGKILL)
        target.wait(timeout=2)


def wait_for(path, process=None, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return json.loads(path.read_text())
        if process is not None and process.poll() is not None:
            raise AssertionError("supervisor exited before receipt")
        time.sleep(0.02)
    raise AssertionError("receipt deadline expired")


@pytest.mark.parametrize(
    "code,expected",
    [
        ("print('done')", "completed"),
        ("import time; time.sleep(20)", "timeout"),
        (
            "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(20)",
            "timeout",
        ),
    ],
)
def test_opt_in_watchdog_verifies_stop_and_reaps(tmp_path, code, expected):
    result = run(tmp_path, code, parent_watchdog=True, timeout=0.8)
    assert result.status == expected and result.stopped
    assert not live_members(result.identity.pgid)
    root = tmp_path / "physical"
    ready = wait_for(root / "watchdog-ready.json")
    receipt = wait_for(root / "watchdog-result.json")
    assert receipt["stopped"] is True
    assert (
        receipt["job_sha256"]
        == hashlib.sha256((root / "watchdog-job.json").read_bytes()).hexdigest()
    )
    assert receipt["nonce"] == ready["nonce"]
    assert process_watchdog.describe(ready["pid"]) is None
    assert recover_completed_process(root, nonce="owned-nonce", max_output_bytes=4096) == result


def test_watchdog_launch_callback_failure_keeps_command_gated(tmp_path):
    marker = tmp_path / "forbidden"

    def fail(_):
        raise RuntimeError("lost ownership acknowledgment")

    with pytest.raises(RuntimeError, match="acknowledgment"):
        run(
            tmp_path,
            f"from pathlib import Path; Path({str(marker)!r}).touch()",
            parent_watchdog=True,
            on_launch=fail,
        )
    assert not marker.exists()
    assert read_completion(tmp_path / "physical")["stopped"]
    assert wait_for(tmp_path / "physical/watchdog-result.json")["stopped"]


@pytest.mark.parametrize("fork", [False, True])
def test_parent_death_stops_group_even_after_command_leaves_descendant(tmp_path, fork):
    tmp_path.chmod(0o700)
    marker = tmp_path / "started"
    code = (
        "import os,signal,time; from pathlib import Path; "
        + ("pid=os.fork(); " if fork else "")
        + "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        + f"Path({str(marker)!r}).touch(); "
        + ("time.sleep(20) if pid==0 else None" if fork else "time.sleep(20)")
    )
    source = """
from pathlib import Path
import sys
from autoengineering.agents.process import supervise_process
root=Path(sys.argv[1])
supervise_process((sys.executable,'-I','-S','-c',sys.argv[2]),
 directory=root/'physical',cwd=root,environment={'PATH':'/usr/bin:/bin'},nonce='watched-nonce',
 stdin=b'',timeout_seconds=20,max_output_bytes=100,on_launch=lambda _:None,parent_watchdog=True)
"""
    parent = subprocess.Popen([sys.executable, "-c", source, str(tmp_path), code])
    identity = None
    try:
        root = tmp_path / "physical"
        wait_for(root / "launch-gate.json", parent)
        identity = ProcessIdentity(**wait_for(root / "process.json"))
        deadline = time.monotonic() + 3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert marker.exists()
        parent.kill()
        parent.wait(timeout=2)
        receipt = wait_for(root / "watchdog-result.json")
        assert receipt["reason"] == "owner_lost" and receipt["stopped"]
        assert not live_members(identity.pgid)
        assert not (root / "completion.json").exists()
        before = {path.name: path.read_bytes() for path in root.iterdir()}
        assert recover_watchdog_stop(root) == receipt
        assert {path.name: path.read_bytes() for path in root.iterdir()} == before
        with pytest.raises(ValueError, match="binding"):
            changed = {**receipt, "job_sha256": "0" * 64}
            (root / "watchdog-result.json").write_text(json.dumps(changed))
            recover_watchdog_stop(root)
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=2)
        if identity is not None and identity_matches(identity):
            os.killpg(identity.pgid, 9)


def test_watchdog_deadline_applies_while_owner_callback_is_blocked(tmp_path):
    tmp_path.chmod(0o700)
    marker = tmp_path / "forbidden"
    result = supervise_process(
        (sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"),
        directory=tmp_path / "physical",
        cwd=tmp_path,
        environment={"PATH": "/usr/bin:/bin"},
        nonce="blocked-owner",
        stdin=b"",
        timeout_seconds=0.4,
        max_output_bytes=100,
        on_launch=lambda _: time.sleep(0.8),
        parent_watchdog=True,
    )
    assert result.status == "timeout" and result.stopped
    assert not marker.exists()
    receipt = wait_for(tmp_path / "physical/watchdog-result.json")
    assert receipt["reason"] == "timeout" and receipt["stopped"]


@pytest.mark.parametrize("field,value", [("nonce", "wrong-nonce"), ("started", "stale-start")])
def test_unverified_identity_never_signals_unrelated_group(tmp_path, field, value):
    # Give the real target a nonce-bearing command, then corrupt one binding.
    target = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(20)", "--nonce", "real-nonce"],
        start_new_session=True,
    )
    try:
        description = process_watchdog.describe(target.pid)
        identity = {
            "pid": target.pid,
            "pgid": target.pid,
            "nonce": "real-nonce",
            "started": description[0],
        }
        identity[field] = value
        job = {
            "target": identity,
            "owner_pid": os.getpid(),
            "owner_started": process_watchdog.describe(os.getpid())[0],
            "deadline_monotonic": time.monotonic() - 1,
            "grace_seconds": 0.1,
        }
        reason, stopped = process_watchdog.watch(
            job, lambda: pytest.fail("cannot become ready"), lambda: False
        )
        assert reason == "ownership_unverified" and stopped is False
        assert target.poll() is None
    finally:
        target.kill()
        target.wait(timeout=2)


def test_concurrent_owner_stop_is_reobserved_before_claiming_uncertainty(monkeypatch):
    identities = iter((True, False))
    listings = iter(((123,), (123,), ()))
    monkeypatch.setattr(process_watchdog, "matches", lambda _: next(identities))
    monkeypatch.setattr(process_watchdog, "members", lambda _: next(listings))
    monkeypatch.setattr(process_watchdog, "describe", lambda _: ("owner-start", "owner"))
    monkeypatch.setattr(process_watchdog.os, "killpg", lambda *_: pytest.fail("already stopped"))
    reason, stopped = process_watchdog.watch(
        {
            "target": {"pgid": 123},
            "owner_pid": 456,
            "owner_started": "owner-start",
            "deadline_monotonic": time.monotonic() - 1,
            "grace_seconds": 0.1,
        },
        lambda: None,
        lambda: False,
    )
    assert reason == "timeout" and stopped


def test_pipe_eof_stops_target_without_relying_on_owner_pid(tmp_path):
    target = subprocess.Popen(
        [sys.executable, "-I", "-S", "-c", "import time; time.sleep(20)", "--nonce", "pipe-target"],
        start_new_session=True,
    )
    read_fd, write_fd = os.pipe()
    watcher = None
    try:
        identity = {
            "pid": target.pid,
            "pgid": target.pid,
            "nonce": "pipe-target",
            "started": process_watchdog.describe(target.pid)[0],
        }
        job = {
            "nonce": "pipe-watcher",
            "target": identity,
            "owner_lease": "pipe-eof-v1",
            "owner_pid": -1,
            "owner_started": "intentionally unusable PID metadata",
            "deadline_monotonic": time.monotonic() + 20,
            "grace_seconds": 0.1,
        }
        path = tmp_path / "watchdog-job.json"
        path.write_text(json.dumps(job))
        watcher = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                process_watchdog.__file__,
                "--nonce",
                "pipe-watcher",
                "--job",
                str(path),
                "--owner-fd",
                str(read_fd),
            ],
            pass_fds=(read_fd,),
            start_new_session=True,
        )
        wait_for(tmp_path / "watchdog-ready.json", watcher)
        time.sleep(0.1)
        assert target.poll() is None  # Dead PID metadata cannot substitute for pipe EOF.
        os.close(write_fd)
        write_fd = None
        watcher.wait(timeout=3)
        receipt = wait_for(tmp_path / "watchdog-result.json")
        assert receipt["reason"] == "owner_lost" and receipt["stopped"]
        target.wait(timeout=2)
        assert not live_members(target.pid)
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if watcher is not None and watcher.poll() is None:
            watcher.kill()
            watcher.wait(timeout=2)
        if target.poll() is None:
            target.kill()
            target.wait(timeout=2)


def test_trampoline_loses_lease_before_watchdog_start_and_never_opens_gate(tmp_path):
    from autoengineering.agents import process_worker

    marker = tmp_path / "forbidden"
    job = {
        "command": [sys.executable, "-c", f"open({str(marker)!r},'w').close()"],
        "cwd": str(tmp_path),
        "environment": {},
        "keep_group_leader": True,
        "owner_lease": "pipe-eof-v1",
    }
    path = tmp_path / "job.json"
    path.write_text(json.dumps(job))
    read_fd, write_fd = os.pipe()
    worker = None
    try:
        worker = subprocess.Popen(
            [
                sys.executable,
                "-I",
                "-S",
                process_worker.__file__,
                "--nonce",
                "before-ready",
                "--job",
                str(path),
                "--owner-fd",
                str(read_fd),
            ],
            pass_fds=(read_fd,),
            start_new_session=True,
        )
        os.close(write_fd)
        write_fd = None
        assert worker.wait(timeout=1) == 125
        assert not marker.exists()
    finally:
        os.close(read_fd)
        if write_fd is not None:
            os.close(write_fd)
        if worker is not None and worker.poll() is None:
            worker.kill()
            worker.wait(timeout=2)


@pytest.mark.parametrize("failure", ["deadline", "spawn"])
def test_watchdog_startup_failure_is_gated_terminal_and_recoverable(tmp_path, monkeypatch, failure):
    import autoengineering.agents.process as supervisor

    launches = []
    real_popen = subprocess.Popen

    def popen(command, *args, **kwargs):
        if failure == "spawn" and any(
            str(value).endswith("process_watchdog.py") for value in command
        ):
            raise OSError("authored startup failure without sensitive diagnostics")
        return real_popen(command, *args, **kwargs)

    monkeypatch.setattr(supervisor.subprocess, "Popen", popen)
    marker = tmp_path / "forbidden"
    result = run(
        tmp_path,
        f"open({str(marker)!r},'w').close()",
        parent_watchdog=True,
        timeout=0.001 if failure == "deadline" else 3,
        on_launch=launches.append,
    )
    assert result.status == ("timeout" if failure == "deadline" else "host_failure")
    assert result.stopped and not marker.exists() and not launches
    root = tmp_path / "physical"
    assert not (root / "launch-gate.json").exists()
    assert recover_watchdog_stop(root)["stopped"]
    assert recover_completed_process(root, nonce="owned-nonce", max_output_bytes=4096) == result
    (root / "launch-gate.json").write_text('{"nonce":"owned-nonce"}')
    with pytest.raises(ValueError, match="aborted"):
        recover_watchdog_stop(root)


def test_cancel_after_ownership_acknowledgment_cannot_open_gate(tmp_path):
    cancelled = False

    def acknowledge(_):
        nonlocal cancelled
        cancelled = True

    marker = tmp_path / "forbidden"
    result = run(
        tmp_path,
        f"open({str(marker)!r},'w').close()",
        parent_watchdog=True,
        cancelled=lambda: cancelled,
        on_launch=acknowledge,
    )
    assert result.status == "cancelled" and result.stopped and not marker.exists()
    assert not (tmp_path / "physical/launch-gate.json").exists()
    assert (
        recover_completed_process(tmp_path / "physical", nonce="owned-nonce", max_output_bytes=4096)
        == result
    )
