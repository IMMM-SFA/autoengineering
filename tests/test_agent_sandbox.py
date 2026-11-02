"""Actual OS privacy probes, separated from unqualified generated execution."""

import json
import socket
import sys

import pytest

from autoengineering.agents.process import supervise_process
from autoengineering.agents.sandbox import BoundaryLimits, MacOSBoundary

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS boundary prototype only")


def test_deny_default_blocks_private_reads_writes_network_fork_and_symlink_escape(tmp_path):
    tmp_path.chmod(0o700)
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    private = tmp_path / "private-labels"
    private.write_bytes(b"evaluator-owned-canary")
    (workspace / "escape").symlink_to(private)
    boundary = MacOSBoundary()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    source = f"""
import json,os,socket,errno
results={{}}
for name,path,mode in [('private_read',{str(private)!r},'rb'),('private_write',{str(private)!r},'wb'),
                       ('workspace_write',{str(workspace / "changed")!r},'wb'),
                       ('symlink_escape',{str(workspace / "escape")!r},'rb')]:
 try:
  with open(path,mode) as stream:
   stream.write(b'changed') if 'w' in mode else stream.read()
  results[name]='allowed'
 except PermissionError:
  results[name]='denied'
try:
 os.listdir({str(boundary.site_packages)!r})
 results['site_packages']='allowed'
except PermissionError:
 results['site_packages']='denied'
try:
 s=socket.socket();s.settimeout(1);s.connect(('127.0.0.1',{port}));s.close()
 results['network']='allowed'
except PermissionError:
 results['network']='denied'
try:
 pid=os.fork()
 if pid==0: os._exit(0)
 os.waitpid(pid,0)
 results['fork']='allowed'
except PermissionError:
 results['fork']='denied'
print(json.dumps(results))
"""
    (workspace / "probe.py").write_text(source)
    # This is a trusted OS probe, not generated candidate admission. The
    # separate memory wrapper is deliberately not bypassed for any candidate.
    command = (
        "/usr/bin/sandbox-exec",
        "-p",
        boundary.profile(workspace),
        str(boundary.python),
        "-I",
        "-S",
        "-B",
        str(workspace / "probe.py"),
    )
    try:
        result = supervise_process(
            command,
            directory=tmp_path / "physical",
            cwd=workspace,
            environment={"PATH": "/usr/bin:/bin"},
            nonce="privacy-probe",
            stdin=b"",
            timeout_seconds=4,
            max_output_bytes=65536,
            on_launch=lambda _: None,
        )
    finally:
        listener.close()
    assert result.status == "completed", result.stderr.decode(errors="replace")
    assert json.loads(result.stdout) == {
        key: "denied"
        for key in (
            "private_read",
            "private_write",
            "workspace_write",
            "symlink_escape",
            "site_packages",
            "network",
            "fork",
        )
    }
    assert private.read_bytes() == b"evaluator-owned-canary"
    assert not (workspace / "changed").exists()


def test_memory_wrapper_fails_closed_before_candidate_if_limit_unavailable(tmp_path):
    tmp_path.chmod(0o700)
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    (workspace / "candidate.py").write_text('print("candidate-executed")\n')
    boundary = MacOSBoundary()
    limits = BoundaryLimits()
    result = supervise_process(
        boundary.command(workspace, "candidate.py", limits),
        directory=tmp_path / "physical",
        cwd=workspace,
        environment={"PATH": "/usr/bin:/bin"},
        nonce="resource-probe",
        stdin=b"",
        timeout_seconds=4,
        max_output_bytes=65536,
        on_launch=lambda _: None,
    )
    if result.status != "completed":
        assert b"candidate-executed" not in result.stdout
        assert b"resource.setrlimit" in result.stderr
        assert b"current limit exceeds maximum limit" in result.stderr
    else:
        # Success establishes startup only. A successful allocation-limit probe
        # remains mandatory before a trusted registration can qualify this OS.
        assert result.stdout == b"candidate-executed\n"
    assert result.stopped


def test_boundary_limits_reject_boolean_or_unsupported_ceilings():
    with pytest.raises(ValueError):
        BoundaryLimits(cpu_seconds=True)
    with pytest.raises(ValueError):
        BoundaryLimits(memory_bytes=2 * 1024 * 1024 * 1024)
