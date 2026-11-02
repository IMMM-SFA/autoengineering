"""Authored resource controls; never allocate a GiB, fork or contact a daemon."""

import errno
import json
from types import SimpleNamespace

import pytest

from examples.utility import guest_resource_probe as probe

NONCE = "a" * 32


@pytest.fixture
def context(monkeypatch):
    metadata = {
        "/sys/fs/cgroup/memory.max": str(probe.MEMORY),
        "/sys/fs/cgroup/memory.swap.max": "0",
        "/sys/fs/cgroup/pids.max": "16",
        "/sys/fs/cgroup/cpu.max": "100000 100000",
        "/proc/self/status": "NoNewPrivs:\t1\nSeccomp:\t2\n"
        + "".join(
            name + ":\t0000000000000000\n"
            for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")
        ),
        "/proc/self/mounts": "overlay / overlay ro,relatime 0 0\n"
        "tmpfs /work tmpfs rw,noexec,nosuid,nodev,size=131072k 0 0\n",
        "/proc/net/dev": "header\nheader\n lo: 0 0 0 0 0 0\n",
    }
    monkeypatch.setattr(probe, "read", lambda path: metadata[path])
    monkeypatch.setattr(probe.platform, "system", lambda: "Linux")
    monkeypatch.setattr(probe.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(probe.platform, "python_implementation", lambda: "CPython")
    monkeypatch.setattr(probe.sys, "version_info", (3, 12, 13))
    monkeypatch.setattr(
        probe, "PYTHON_BUILD", probe.hashlib.sha256(probe.sys.version.encode()).hexdigest()
    )
    monkeypatch.setattr(probe.sys, "executable", "/opt/inference/bin/python")
    monkeypatch.setattr(probe.sys, "flags", SimpleNamespace(isolated=1, no_site=1))
    monkeypatch.setattr(probe.sys, "dont_write_bytecode", True)
    monkeypatch.setattr(probe.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(probe.os, "getegid", lambda: 1000)
    monkeypatch.setattr(
        probe.os,
        "stat",
        lambda *a, **kw: SimpleNamespace(st_mode=0o40700, st_uid=1000, st_gid=1000),
    )
    monkeypatch.setattr(
        probe.os, "statvfs", lambda path: SimpleNamespace(f_blocks=32768, f_frsize=4096)
    )
    return metadata


def test_context_matches_authored_policy(context):
    assert probe.context()["workspace_bytes"] == probe.WORKSPACE


@pytest.mark.parametrize(
    "path,value",
    [
        ("/sys/fs/cgroup/memory.max", "max"),
        ("/sys/fs/cgroup/memory.swap.max", "1073741824"),
        ("/sys/fs/cgroup/pids.max", "max"),
        ("/sys/fs/cgroup/cpu.max", "max 100000"),
        ("/proc/self/status", "NoNewPrivs: 0\nSeccomp: 0\n"),
        ("/proc/self/mounts", "overlay / overlay rw 0 0\n"),
        ("/proc/net/dev", "header\nheader\nlo: 0\neth0: 0\n"),
    ],
)
def test_context_refuses_missing_boundary(context, path, value):
    context[path] = value
    with pytest.raises(probe.Refused):
        probe.context()


@pytest.mark.parametrize("mode", probe.MODES)
def test_guard_precedes_every_resource_action(monkeypatch, mode, capsys):
    calls = []

    def refuse():
        raise probe.Refused("effective_limits")

    monkeypatch.setattr(probe, "context", refuse)
    monkeypatch.setattr(probe.signal, "alarm", lambda value: calls.append(("alarm", value)))
    for name in probe.MODES:
        monkeypatch.setattr(probe, name, lambda *a: pytest.fail("resource action before guard"))
    with pytest.raises(probe.Refused, match="effective_limits"):
        probe.run(
            mode,
            NONCE,
            "/private/ae-host-canary-" + NONCE if mode == "host_canary_denied" else None,
        )
    assert calls == [("alarm", 45)]
    assert not capsys.readouterr().out


def test_workspace_short_writes_and_enospc(monkeypatch):
    writes, removed, closed = [], [], []
    monkeypatch.setattr(probe.os, "open", lambda *a: 41)

    def write(fd, data):
        writes.append(len(data))
        if len(writes) == 3:
            raise OSError(errno.ENOSPC, "authored")
        return len(data) // 2

    monkeypatch.setattr(probe.os, "write", write)
    monkeypatch.setattr(probe.os, "close", closed.append)
    monkeypatch.setattr(probe.os, "unlink", removed.append)
    assert probe.workspace_limit(NONCE) == {"errno": "ENOSPC", "written_bytes": probe.CHUNK}
    assert closed == [41] and len(removed) == 1 and len(writes) == 3


def test_workspace_has_finite_write_bound(monkeypatch):
    calls = []
    monkeypatch.setattr(probe.os, "open", lambda *a: 41)
    monkeypatch.setattr(probe.os, "write", lambda fd, data: calls.append(len(data)) or len(data))
    monkeypatch.setattr(probe.os, "close", lambda fd: None)
    monkeypatch.setattr(probe.os, "unlink", lambda path: None)
    with pytest.raises(probe.Refused, match="workspace_cap_not_observed"):
        probe.workspace_limit(NONCE)
    assert sum(calls) == probe.WORKSPACE + probe.CHUNK


@pytest.mark.parametrize("number", [errno.EACCES, errno.EIO, errno.EDQUOT])
def test_workspace_rejects_other_failures(monkeypatch, number):
    monkeypatch.setattr(probe.os, "open", lambda *a: 41)
    monkeypatch.setattr(
        probe.os, "write", lambda *a: (_ for _ in ()).throw(OSError(number, "private"))
    )
    monkeypatch.setattr(probe.os, "close", lambda fd: None)
    monkeypatch.setattr(probe.os, "unlink", lambda path: None)
    with pytest.raises(probe.Refused, match="workspace_failure_not_limit"):
        probe.workspace_limit(NONCE)


@pytest.mark.parametrize(
    "number,passes", [(errno.EROFS, True), (errno.EACCES, False), (errno.EEXIST, False)]
)
def test_root_requires_filesystem_denial(monkeypatch, number, passes):
    monkeypatch.setattr(probe.os, "stat", lambda *a, **kw: SimpleNamespace(st_mode=0o41777))
    monkeypatch.setattr(
        probe.os, "open", lambda *a: (_ for _ in ()).throw(OSError(number, "private"))
    )
    if passes:
        assert probe.read_only_root(NONCE) == {"errno": "EROFS"}
    else:
        with pytest.raises(probe.Refused, match="root_failure_not_read_only"):
            probe.read_only_root(NONCE)


@pytest.mark.parametrize(
    "number,passes",
    [
        (errno.ENETUNREACH, True),
        (errno.EHOSTUNREACH, True),
        (errno.ECONNREFUSED, False),
        (None, False),
        (errno.ETIMEDOUT, False),
    ],
)
def test_network_rejects_refusal_or_timeout(monkeypatch, number, passes):
    calls = []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            calls.append("close")

        def settimeout(self, value):
            calls.append(value)

        def connect(self, target):
            calls.append(target)
            raise OSError(number, "private")

    monkeypatch.setattr(probe.socket, "socket", lambda *a: Connection())
    if passes:
        assert probe.network_denied(NONCE)["attempts"] == 1
    else:
        with pytest.raises(probe.Refused, match="network_failure_not_isolation"):
            probe.network_denied(NONCE)
    assert calls == [2, ("192.0.2.1", 9), "close"]


def test_canary_visible_closes_without_reading(monkeypatch):
    closed = []
    monkeypatch.setattr(probe.os, "open", lambda *a: 41)
    monkeypatch.setattr(probe.os, "read", lambda *a: pytest.fail("canary bytes read"))
    monkeypatch.setattr(probe.os, "close", closed.append)
    with pytest.raises(probe.Refused, match="host_canary_visible"):
        probe.host_canary_denied(NONCE, "/private/ae-host-canary-" + NONCE)
    assert closed == [41]


@pytest.mark.parametrize(
    "number,passes", [(errno.ENOENT, True), (errno.ENOTDIR, True), (errno.EACCES, False)]
)
def test_canary_requires_absence(monkeypatch, number, passes):
    monkeypatch.setattr(
        probe.os, "open", lambda *a: (_ for _ in ()).throw(OSError(number, "private"))
    )
    if passes:
        assert probe.host_canary_denied(NONCE, "/private/ae-host-canary-" + NONCE)["errno"]
    else:
        with pytest.raises(probe.Refused, match="canary_failure_not_absence"):
            probe.host_canary_denied(NONCE, "/private/ae-host-canary-" + NONCE)


def test_pid_limit_reaps_all_children(monkeypatch):
    calls, forks = [], iter([101, 102, OSError(errno.EAGAIN, "authored")])
    monkeypatch.setattr(probe.os, "pipe", lambda: (41, 42))

    def fork():
        value = next(forks)
        calls.append("fork")
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(probe.os, "fork", fork)
    monkeypatch.setattr(probe, "read", lambda path: "16")
    monkeypatch.setattr(probe.os, "close", lambda fd: calls.append(("close", fd)))
    monkeypatch.setattr(
        probe.os, "waitpid", lambda child, flags: calls.append(("wait", child)) or (child, 0)
    )
    assert probe.pid_limit(NONCE) == {"errno": "EAGAIN", "pids_current": 16, "children": 2}
    assert calls[-4:] == [("close", 42), ("close", 41), ("wait", 101), ("wait", 102)]


def test_pid_spawn_bound_on_missing_limit(monkeypatch):
    children = []
    monkeypatch.setattr(probe.os, "pipe", lambda: (41, 42))
    monkeypatch.setattr(
        probe.os, "fork", lambda: children.append(len(children) + 100) or children[-1]
    )
    monkeypatch.setattr(probe.os, "close", lambda fd: None)
    monkeypatch.setattr(probe.os, "waitpid", lambda child, flags: (child, 0))
    with pytest.raises(probe.Refused, match="pid_cap_not_observed"):
        probe.pid_limit(NONCE)
    assert len(children) == 20


def test_refusal_output_does_not_disclose_exception(monkeypatch, capsys):
    monkeypatch.setattr(probe.sys, "argv", ["probe", "read_only_root", NONCE])
    monkeypatch.setattr(probe, "run", lambda *a: (_ for _ in ()).throw(OSError("private path")))
    assert probe.main() == 2
    assert json.loads(capsys.readouterr().out) == {
        "schema": "utility-guest-resource-refusal-v1",
        "reason": "unverified_failure",
    }
