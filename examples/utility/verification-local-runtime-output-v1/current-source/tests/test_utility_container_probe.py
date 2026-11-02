"""Authored preflight fixtures do not attest a real Linux/container boundary."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "private_probe", ROOT / "scripts/utility_container_probe.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def context(tmp_path):
    cgroup, proc = tmp_path / "cgroup", tmp_path / "proc"
    cgroup.mkdir()
    (proc / "self").mkdir(parents=True)
    (proc / "net").mkdir()
    for name, value in {
        "memory.max": "67108864",
        "memory.swap.max": "0",
        "pids.max": "16",
        "cpu.max": "100000 100000",
    }.items():
        (cgroup / name).write_text(value + "\n")
    (proc / "self/status").write_text(
        "NoNewPrivs:\t1\nCapInh:\t0000000000000000\nCapPrm:\t0000000000000000\n"
        "CapEff:\t0000000000000000\nCapBnd:\t0000000000000000\nCapAmb:\t0000000000000000\n"
    )
    (proc / "self/mounts").write_text(
        "overlay / overlay ro,nosuid 0 0\ntmpfs /tmp tmpfs rw,nosuid,nodev,noexec,size=4096k 0 0\n"
    )
    (proc / "net/dev").write_text("header\nheader\n lo: 0 0 0 0\n")
    return cgroup, proc


def inspect(cgroup, proc):
    return probe.inspect_context(cgroup, proc, platform_name="linux", identity=(65534, 65534))


def test_explicit_limits_are_observed_without_claiming_qualification(tmp_path):
    observed = inspect(*context(tmp_path))
    assert observed["effective_limits"]["memory.max"] == "67108864"
    assert observed["network_interfaces"] == ["lo"]
    assert "qualified" not in observed


@pytest.mark.parametrize(
    "name,value",
    [
        ("memory.max", "max"),
        ("memory.max", "134217728"),
        ("memory.swap.max", "67108864"),
        ("pids.max", "max"),
        ("pids.max", "32"),
        ("cpu.max", "max 100000"),
        ("cpu.max", "200000 100000"),
    ],
)
def test_loosened_or_unbounded_kernel_limits_refuse(tmp_path, name, value):
    cgroup, proc = context(tmp_path)
    (cgroup / name).write_text(value)
    with pytest.raises(probe.Refused):
        inspect(cgroup, proc)


@pytest.mark.parametrize(
    "target,text",
    [
        ("self/status", "NoNewPrivs: 0\nCapEff: 0000000000000000\n"),
        ("self/status", "NoNewPrivs: 1\nCapEff: 0000000000000001\n"),
        ("self/mounts", "overlay / overlay rw 0 0\ntmpfs /tmp tmpfs rw 0 0\n"),
        (
            "self/mounts",
            "overlay / overlay ro 0 0\ntmpfs /tmp tmpfs rw,nosuid,nodev,size=4096k 0 0\n",
        ),
        ("net/dev", "header\nheader\n lo: 0\n eth0: 0\n"),
    ],
)
def test_unsafe_process_mount_or_network_context_refuses(tmp_path, target, text):
    cgroup, proc = context(tmp_path)
    (proc / target).write_text(text)
    with pytest.raises(probe.Refused):
        inspect(cgroup, proc)


def test_wrong_platform_or_identity_refuses_before_files(tmp_path):
    with pytest.raises(probe.Refused):
        probe.inspect_context(tmp_path, tmp_path, platform_name="darwin", identity=(65534, 65534))
    with pytest.raises(probe.Refused):
        probe.inspect_context(tmp_path, tmp_path, platform_name="linux", identity=(0, 0))


@pytest.mark.parametrize("field", ["CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"])
def test_any_remaining_capability_refuses(tmp_path, field):
    cgroup, proc = context(tmp_path)
    path = proc / "self/status"
    path.write_text(
        path.read_text().replace(field + ":\t0000000000000000", field + ":\t0000000000000001")
    )
    with pytest.raises(probe.Refused):
        inspect(cgroup, proc)


def test_scope_and_worker_must_match_original_bytes(tmp_path):
    nonce = "a" * 32
    (tmp_path / "scope.json").write_text(
        json.dumps(
            {"schema": "utility-container-probe-scope-v1", "nonce": nonce},
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    worker = (ROOT / "src/autoengineering/utility/private_score_worker.py").read_bytes()
    (tmp_path / "private_score_worker.py").write_bytes(worker)
    assert probe.verify_stage(tmp_path, nonce) == worker
    with pytest.raises(probe.Refused):
        probe.verify_stage(tmp_path, "b" * 32)
    (tmp_path / "private_score_worker.py").write_bytes(worker + b"\n")
    with pytest.raises(probe.Refused):
        probe.verify_stage(tmp_path, nonce)


def test_fixed_score_uses_only_internally_authored_synthetic_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(probe.tempfile, "tempdir", str(tmp_path))
    worker = (ROOT / "src/autoengineering/utility/private_score_worker.py").read_bytes()
    assert probe.synthetic_score(worker) == {"vector_length": 64, "synthetic_rmse": 1.0}
    assert not list(tmp_path.iterdir())


def test_symlink_and_nonregular_input_refuse_without_opening(tmp_path):
    import os

    target = tmp_path / "target"
    target.write_text("owned canary")
    link = tmp_path / "link"
    link.symlink_to(target)
    with pytest.raises(probe.Refused):
        probe._read(link)
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    with pytest.raises(probe.Refused):
        probe._read(fifo)


def test_oversized_input_refuses_at_bound(tmp_path):
    path = tmp_path / "owned"
    path.write_bytes(b"a" * 1025)
    with pytest.raises(probe.Refused):
        probe._read(path, limit=1024)


def test_refusal_prevents_any_allocation_or_scoring(monkeypatch, capsys):
    monkeypatch.setattr(probe, "inspect_context", lambda: (_ for _ in ()).throw(probe.Refused()))
    monkeypatch.setattr(probe, "allocate", lambda *_: pytest.fail("guard allowed allocation"))
    monkeypatch.setattr(probe, "synthetic_score", lambda *_: pytest.fail("guard allowed scoring"))
    assert probe.main(["memory-overrun", "--nonce", "a" * 32]) == 2
    assert json.loads(capsys.readouterr().out)["qualified"] is False


@pytest.mark.parametrize(
    "host_path",
    [
        "/public-unowned/host-canary.json",
        "/private/tmp/utility-runtime-isolation-owned/../host-canary.json",
        "/private/tmp/utility-runtime-isolation-owned/another-file.json",
    ],
)
def test_isolation_rejects_arbitrary_probe_paths_before_network(tmp_path, monkeypatch, host_path):
    (tmp_path / "isolation.json").write_text(json.dumps({"host_canary_path": host_path}))
    monkeypatch.setattr(probe.socket, "socket", lambda *_: pytest.fail("must not open socket"))
    with pytest.raises(probe.Refused):
        probe.isolation_checks(tmp_path, "a" * 32)


def test_isolation_canary_must_match_own_nonce_before_host_read(tmp_path, monkeypatch):
    (tmp_path / "isolation.json").write_text(
        json.dumps(
            {
                "host_canary_path": "/private/tmp/utility-runtime-isolation-owned/host-canary.json",
                "host_canary_sha256": "0" * 64,
            }
        )
    )
    (tmp_path / "public-canary.json").write_text("wrong public canary")
    monkeypatch.setattr(probe.socket, "socket", lambda *_: pytest.fail("must not open socket"))
    with pytest.raises(probe.Refused):
        probe.isolation_checks(tmp_path, "a" * 32)
