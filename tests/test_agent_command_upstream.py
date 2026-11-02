"""Authored local upstream commands, bounded stop and immutable saved recovery."""

import json
import sys
import time

import pytest

from autoengineering.agents.hosts.command_upstream import (
    CommandUpstream,
    UpstreamProcessError,
    inspect_command_stop,
    recover_command_upstream,
)
from autoengineering.agents.process import read_completion, recover_watchdog_stop
from autoengineering.campaign.execution import live_members


def callback(tmp_path, code, *, timeout=3, cancelled=lambda: False, fault=lambda _: None):
    tmp_path.chmod(0o700)
    source = tmp_path / "authored.py"
    source.write_text("from pathlib import Path\nimport sys\n" + code)
    return CommandUpstream(
        tmp_path / "attempt",
        command=(sys.executable, "-I", "-S", str(source), "{request}", "{response}"),
        source_files=(source,),
        deadline_monotonic=time.monotonic() + timeout,
        cancelled=cancelled,
        fault=fault,
    )


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize("lost_ack", [False, True])
def test_large_request_success_and_lost_ack_recover_without_new_work(tmp_path, lost_ack):
    def fault(stage):
        if lost_ack:
            assert stage == "before_outcome_commit"
            raise RuntimeError("lost final acknowledgment")

    upstream = callback(
        tmp_path, "Path(sys.argv[2]).write_bytes(Path(sys.argv[1]).read_bytes())", fault=fault
    )
    request = b"x" * 200000  # Beyond the supervisor's deliberately small stdin allowance.
    if lost_ack:
        with pytest.raises(RuntimeError, match="acknowledgment"):
            upstream(request)
    else:
        assert upstream(request) == request
    before = snapshot(upstream.directory)
    assert recover_command_upstream(upstream.directory) == request
    assert snapshot(upstream.directory) == before
    with pytest.raises(FileExistsError):
        upstream(request)
    assert snapshot(upstream.directory) == before


@pytest.mark.parametrize(
    "code,expected",
    [
        ("import time\ntime.sleep(20)", "timeout"),
        ("Path(sys.argv[2]).write_bytes(b'partial')\nsys.exit(7)", "host_failure"),
        ("import os\nwhile True: os.write(1,b'x'*65536)", "output_limit"),
        ("Path(sys.argv[2]).write_bytes(b'x'*524289)", "invalid_response"),
        ("pass", "invalid_response"),
    ],
)
def test_failed_or_unbounded_work_never_delivers_partial_bytes(tmp_path, code, expected):
    upstream = callback(tmp_path, code, timeout=0.8)
    with pytest.raises(UpstreamProcessError) as caught:
        upstream(b"approved")
    assert caught.value.status == expected
    root = upstream.directory
    completion = read_completion(root / "process")
    assert completion["stopped"]
    assert not live_members(completion["identity"]["pgid"])
    assert recover_watchdog_stop(root / "process")["stopped"]
    with pytest.raises(UpstreamProcessError):
        recover_command_upstream(root)
    with pytest.raises(FileExistsError):
        upstream(b"approved")


def test_cancelled_and_expired_callbacks_do_not_start_command(tmp_path):
    upstream = callback(tmp_path, "raise AssertionError('must not start')", cancelled=lambda: True)
    with pytest.raises(UpstreamProcessError, match="cancelled"):
        upstream(b"approved")
    assert not (upstream.directory / "process/process.json").exists()
    other = tmp_path / "expired"
    other.mkdir(mode=0o700)
    expired = callback(other, "raise AssertionError('must not start')", timeout=-1)
    with pytest.raises(UpstreamProcessError, match="timeout"):
        expired(b"approved")
    assert not (expired.directory / "process").exists()


def test_declared_source_change_cannot_launch_or_recover(tmp_path):
    upstream = callback(tmp_path, "Path(sys.argv[2]).write_bytes(b'complete')")
    source = tmp_path / "authored.py"
    source.write_text("raise AssertionError('changed')")
    with pytest.raises(ValueError, match="source changed"):
        upstream(b"approved")
    assert not (upstream.directory / "process").exists()


@pytest.mark.parametrize("tamper", ["response", "request", "acceptance", "source"])
def test_recovery_checks_response_request_deadline_and_sources(tmp_path, tamper):
    upstream = callback(tmp_path, "Path(sys.argv[2]).write_bytes(b'complete')")
    assert upstream(b"approved") == b"complete"
    root = upstream.directory
    if tamper in {"response", "request"}:
        (root / f"{tamper}.bin").write_bytes(b"changed")
    elif tamper == "source":
        (tmp_path / "authored.py").write_text("pass")
    else:
        ref = json.loads((root / "response.json").read_text())
        ref["metadata"]["accepted_monotonic"] = time.monotonic() + 100
        (root / "response.json").write_text(json.dumps(ref))
    with pytest.raises(ValueError):
        recover_command_upstream(root)


def test_symlink_response_is_rejected(tmp_path):
    upstream = callback(
        tmp_path, "Path(sys.argv[2]).unlink()\nPath(sys.argv[2]).symlink_to(sys.argv[1])"
    )
    with pytest.raises(UpstreamProcessError, match="invalid_response"):
        upstream(b"not a response")


def test_executable_and_declared_script_symlinks_cannot_retarget_launch(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "source.py"
    source.write_text(
        "from pathlib import Path\nimport sys\nPath(sys.argv[2]).write_bytes(b'bound')"
    )
    executable = tmp_path / "interpreter"
    executable.symlink_to(sys.executable)
    script = tmp_path / "script.py"
    script.symlink_to(source)
    upstream = CommandUpstream(
        tmp_path / "attempt",
        command=(str(executable), "-I", "-S", str(script), "{request}", "{response}"),
        source_files=(script,),
        deadline_monotonic=time.monotonic() + 3,
    )
    executable.unlink()
    executable.symlink_to("/bin/false")
    script.unlink()
    script.symlink_to(tmp_path / "missing.py")
    assert upstream(b"approved") == b"bound"
    assert recover_command_upstream(upstream.directory) == b"bound"


def test_fresh_stop_proof_preserves_uncertain_original_completion(tmp_path):
    upstream = callback(tmp_path, "Path(sys.argv[2]).write_bytes(b'complete')")
    assert upstream(b"approved") == b"complete"
    path = upstream.directory / "process/completion.json"
    completion = json.loads(path.read_text())
    # Simulate a supervisor unable to observe the stop before its return.
    # The independently recorded watchdog proof remains untouched.
    completion.update(status="reconciliation_required", stopped=False, returncode=None)
    path.write_text(json.dumps(completion))
    before = snapshot(upstream.directory)
    proof = inspect_command_stop(upstream.directory)
    assert proof["state"] == "verified_stopped" and proof["bindings"]
    assert snapshot(upstream.directory) == before
    with pytest.raises(ValueError, match="stop remains unverified"):
        recover_command_upstream(upstream.directory)
    assert snapshot(upstream.directory) == before


@pytest.mark.parametrize("tamper", ["nonce", "job", "source", "watchdog"])
def test_stop_audit_rejects_foreign_or_unverified_ownership(tmp_path, tamper):
    upstream = callback(tmp_path, "Path(sys.argv[2]).write_bytes(b'complete')")
    assert upstream(b"approved") == b"complete"
    root = upstream.directory
    if tamper == "source":
        (tmp_path / "authored.py").write_text("pass")
    elif tamper == "watchdog":
        (root / "process/watchdog-result.json").unlink()
    else:
        path = root / ("process/process.json" if tamper == "nonce" else "process/job.json")
        value = json.loads(path.read_text())
        value["nonce" if tamper == "nonce" else "cwd"] = "foreign"
        path.write_text(json.dumps(value))
    before = snapshot(root)
    assert inspect_command_stop(root) == {"state": "unresolved"}
    assert snapshot(root) == before


def test_stop_audit_distinguishes_no_launch_from_incomplete_process(tmp_path):
    root = tmp_path / "attempt"
    assert inspect_command_stop(root) == {"state": "not_launched"}
    root.mkdir(mode=0o700)
    assert inspect_command_stop(root) == {"state": "not_launched"}
    (root / "process").mkdir(mode=0o700)
    assert inspect_command_stop(root) == {"state": "unresolved"}
