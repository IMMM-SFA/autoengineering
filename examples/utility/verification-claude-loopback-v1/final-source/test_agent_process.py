"""Real owned process groups, launch gates, bounded output and stop receipts."""

import json
import os
import subprocess
import sys
import threading

import pytest

from autoengineering.agents.process import read_completion, supervise_process
from autoengineering.campaign.execution import (
    ProcessIdentity,
    identity_matches,
    live_members,
    stop_recovered,
)
from autoengineering.campaign.spec import ExecutionSpec


def run(
    tmp_path,
    code,
    *,
    on_launch=lambda receipt: None,
    cancelled=lambda: False,
    timeout=3,
    output_limit=4096,
    parent_watchdog=False,
):
    tmp_path.chmod(0o700)
    return supervise_process(
        (sys.executable, "-I", "-S", "-c", code),
        directory=tmp_path / "physical",
        cwd=tmp_path,
        environment={"PATH": "/usr/bin:/bin"},
        nonce="owned-nonce",
        stdin=b"bounded input",
        timeout_seconds=timeout,
        max_output_bytes=output_limit,
        on_launch=on_launch,
        cancelled=cancelled,
        parent_watchdog=parent_watchdog,
    )


def test_launch_gate_saves_ownership_before_start_and_raw_output(tmp_path):
    marker = tmp_path / "started"
    receipts = []

    def persist(receipt):
        assert not marker.exists()
        assert identity_matches(ProcessIdentity(**receipt))
        receipts.append(receipt)

    result = run(
        tmp_path,
        f"from pathlib import Path; import sys; Path({str(marker)!r}).touch(); "
        "print(sys.stdin.read()); print('diagnostic',file=sys.stderr)",
        on_launch=persist,
    )
    assert result.status == "completed" and result.stopped
    assert result.stdout == b"bounded input\n" and result.stderr == b"diagnostic\n"
    assert len(receipts) == 1 and marker.exists()
    assert not live_members(result.identity.pgid)
    assert read_completion(tmp_path / "physical")["stopped"] is True
    assert (tmp_path / "physical/stdout.bin").read_bytes() == result.stdout


def test_callback_fault_cannot_launch_executable(tmp_path):
    marker = tmp_path / "should-not-start"

    def fail(receipt):
        raise RuntimeError("launch acknowledgment lost")

    with pytest.raises(RuntimeError, match="acknowledgment"):
        run(tmp_path, f"from pathlib import Path; Path({str(marker)!r}).touch()", on_launch=fail)
    assert not marker.exists()
    receipt = read_completion(tmp_path / "physical")
    assert receipt["stopped"] is True
    assert not live_members(receipt["identity"]["pgid"])


@pytest.mark.parametrize("home,temporary", [(None, "/tmp"), ("/private/home", "/tmp"), ("", "")])
def test_claude_temporary_directory_cannot_add_an_independent_scope(tmp_path, home, temporary):
    environment = {"CLAUDE_CODE_TMPDIR": temporary}
    if home is not None:
        environment["HOME"] = home
    with pytest.raises(ValueError, match="temporary directory"):
        supervise_process(
            (sys.executable, "-c", "raise AssertionError('must not run')"),
            directory=tmp_path / "physical", cwd=tmp_path, environment=environment,
            nonce="invalid-temp", stdin=b"", timeout_seconds=1, max_output_bytes=1024,
            on_launch=lambda _: None,
        )
    assert not (tmp_path / "physical").exists()


@pytest.mark.parametrize(
    "code,expected",
    [
        ("import time; time.sleep(20)", "timeout"),
        ("import sys; print('partial'); sys.exit(7)", "host_failure"),
        (
            "import os,time; pid=os.fork(); time.sleep(20) if pid==0 else None",
            "descendant_survived",
        ),
    ],
)
def test_faults_stop_owned_group(tmp_path, code, expected):
    result = run(tmp_path, code, timeout=0.7)
    assert result.status == expected
    assert result.stopped and not live_members(result.identity.pgid)


def test_output_flood_is_bounded_across_both_streams(tmp_path):
    result = run(
        tmp_path,
        "import os;\nwhile True: os.write(1,b'x'*65536); os.write(2,b'y'*65536)",
        output_limit=1234,
    )
    assert result.status == "output_limit"
    assert result.truncated and result.stopped
    assert len(result.stdout) + len(result.stderr) == 1234
    assert not live_members(result.identity.pgid)


def test_cancel_is_independent_of_writer_and_has_verified_stop(tmp_path):
    cancel = threading.Event()
    timer = threading.Timer(0.3, cancel.set)
    timer.start()
    try:
        result = run(tmp_path, "import time; time.sleep(20)", cancelled=cancel.is_set)
    finally:
        timer.cancel()
        timer.join()
    assert result.status == "cancelled" and result.stopped
    assert not live_members(result.identity.pgid)


def test_duplicate_directory_and_ambient_credentials_are_rejected(tmp_path):
    assert run(tmp_path, "pass").status == "completed"
    with pytest.raises(FileExistsError):
        run(tmp_path, "raise AssertionError('must not launch')")
    with pytest.raises(ValueError, match="credential"):
        supervise_process(
            (sys.executable,),
            directory=tmp_path / "forbidden",
            cwd=tmp_path,
            environment={"OPENAI_API_KEY": "never-inherited"},
            nonce="nonce",
            stdin=b"",
            timeout_seconds=1,
            max_output_bytes=100,
            on_launch=lambda _: None,
        )
    assert not (tmp_path / "forbidden").exists()


def test_dead_supervisor_preserves_owned_process_for_explicit_reconciliation(tmp_path):
    tmp_path.chmod(0o700)
    source = """
from pathlib import Path
import sys
from autoengineering.agents.process import supervise_process
root=Path(sys.argv[1])
supervise_process((sys.executable,'-I','-S','-c','import time; time.sleep(20)'),
 directory=root/'physical',cwd=root,environment={'PATH':'/usr/bin:/bin'},nonce='orphan-nonce',
 stdin=b'',timeout_seconds=25,max_output_bytes=100,on_launch=lambda _:None)
"""
    process = subprocess.Popen([sys.executable, "-c", source, str(tmp_path)])
    import time

    gate = tmp_path / "physical/launch-gate.json"
    deadline = time.monotonic() + 5
    while not gate.exists() and process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.02)
    assert gate.exists()
    identity = ProcessIdentity(**json.loads((gate.parent / "process.json").read_text()))
    try:
        process.kill()
        process.wait(timeout=2)
        assert identity_matches(identity)
        assert not stop_recovered(
            ProcessIdentity(identity.pid, identity.pgid, "wrong-nonce", identity.started),
            ExecutionSpec(("test",), termination_grace_seconds=0.1, kill_wait_seconds=1),
        )
        assert identity_matches(identity)
        assert stop_recovered(
            identity, ExecutionSpec(("test",), termination_grace_seconds=0.1, kill_wait_seconds=1)
        )
        assert not live_members(identity.pgid)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=2)
        if identity_matches(identity):
            os.killpg(identity.pgid, 9)
