"""Synthetic-only controls for a future container qualification, not admission.

The CLI never starts Docker or accepts private input paths. Its real guard must
pass before scoring or allocating. The caller must separately bind the image,
mounts, container identity and daemon lifecycle. No output grants qualification.
"""

from __future__ import annotations

import argparse
import contextlib
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import sys
import tempfile

WORKER_SHA256 = "6cd9d35cd7f0ce64c4ade853fb151566bae526f54628ac59beaef704a27d187d"
MEMORY_BYTES = 64 * 1024 * 1024
ALLOCATION_BYTES = 8 * 1024 * 1024
MODES = ("preflight", "memory-small", "memory-overrun", "score", "hold", "isolation")


class Refused(ValueError):
    """Do not expose raw paths, values or exception details in probe output."""


def _read(path, limit=16384):
    if path.is_symlink() or not path.is_file():
        raise Refused()
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise Refused()
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
    finally:
        os.close(descriptor)
    if len(raw) > limit:
        raise Refused()
    return raw


def _mounts(text):
    mounts = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 4:
            raise Refused()
        if fields[1] in ("/", "/tmp"):
            if fields[1] in mounts:
                raise Refused()
            mounts[fields[1]] = fields[2], set(fields[3].split(","))
    return mounts


def inspect_context(
    cgroup=Path("/sys/fs/cgroup"), proc=Path("/proc"), *, platform_name=None, identity=None
):
    """Return observations, not an attestation; path overrides are for unit tests."""
    if (platform_name or sys.platform) != "linux":
        raise Refused()
    uid, gid = identity if identity is not None else (os.geteuid(), os.getegid())
    if (uid, gid) != (65534, 65534):
        raise Refused()
    values = {
        name: _read(cgroup / name).decode().strip()
        for name in ("memory.max", "memory.swap.max", "pids.max", "cpu.max")
    }
    if values != {
        "memory.max": str(MEMORY_BYTES),
        "memory.swap.max": "0",
        "pids.max": "16",
        "cpu.max": "100000 100000",
    }:
        raise Refused()
    status = {}
    for line in _read(proc / "self/status").decode().splitlines():
        name, sep, value = line.partition(":")
        if sep:
            if name in status:
                raise Refused()
            status[name] = value.strip()
    capability_fields = ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")
    if status.get("NoNewPrivs") != "1" or any(
        status.get(name) != "0000000000000000" for name in capability_fields
    ):
        raise Refused()
    mounts = _mounts(_read(proc / "self/mounts").decode())
    if "/" not in mounts or "ro" not in mounts["/"][1] or "rw" in mounts["/"][1]:
        raise Refused()
    if "/tmp" not in mounts or mounts["/tmp"][0] != "tmpfs":
        raise Refused()
    options = mounts["/tmp"][1]
    if not {"rw", "noexec", "nosuid", "nodev", "size=4096k"} <= options:
        raise Refused()
    devices = _read(proc / "net/dev").decode().splitlines()[2:]
    if {line.split(":", 1)[0].strip() for line in devices if line.strip()} != {"lo"}:
        raise Refused()
    return {
        "platform": "linux",
        "uid": uid,
        "gid": gid,
        "effective_limits": values,
        "root_read_only": True,
        "temporary_filesystem_bytes": 4194304,
        "network_interfaces": ["lo"],
        "no_new_privileges": True,
        "effective_capabilities": "none",
    }


def verify_stage(stage, nonce):
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise Refused()
    scope = _read(stage / "scope.json", limit=1024)
    expected = (
        json.dumps(
            {"schema": "utility-container-probe-scope-v1", "nonce": nonce},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + b"\n"
    )
    if scope != expected:
        raise Refused()
    # Execute the same bytes that were hashed, not a later path lookup.
    worker = _read(stage / "private_score_worker.py", limit=65536)
    if hashlib.sha256(worker).hexdigest() != WORKER_SHA256:
        raise Refused()
    return worker


def synthetic_score(worker):
    """Create all input bytes internally; never read caller-supplied labels."""
    if hashlib.sha256(worker).hexdigest() != WORKER_SHA256:
        raise Refused()
    with tempfile.TemporaryDirectory(prefix="ae-synthetic-") as name:
        root = Path(name)
        (root / "job.json").write_text(
            json.dumps(
                {"outcome": "rmse", "units": "1", "prediction": [float(i) for i in range(64)]},
                allow_nan=False,
            )
        )
        (root / "labels.json").write_text(
            json.dumps(
                {"labels": [float(i + 1) for i in range(64)], "mask": [True] * 64}, allow_nan=False
            )
        )
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(
                compile(worker, "pinned-synthetic-worker", "exec"),
                {"__name__": "__main__", "__file__": str(root / "private_score_worker.py")},
            )
        expected = {
            "status": "success",
            "outcome": "rmse",
            "units": "1",
            "value": 1.0,
            "feasible": True,
        }
        if json.loads(output.getvalue()) != expected:
            raise Refused()
    return {"vector_length": 64, "synthetic_rmse": 1.0}


def allocate(size):
    data = bytearray(size)
    for offset in range(0, size, 4096):
        data[offset] = 1  # Touch pages; a virtual allocation alone proves no memory enforcement.
    return len(data)


def isolation_checks(stage, nonce):
    """Exercise only public canaries and a documentation-only network address."""
    metadata = json.loads(_read(stage / "isolation.json", limit=2048))
    host_path = Path(metadata["host_canary_path"])
    if (
        host_path.name != "host-canary.json"
        or not str(host_path).startswith("/private/tmp/utility-runtime-isolation-")
        or ".." in host_path.parts
    ):
        raise Refused()
    expected = json.dumps({"public_synthetic_canary": nonce}, sort_keys=True).encode() + b"\n"
    public = _read(stage / "public-canary.json", limit=1024)
    if public != expected or hashlib.sha256(public).hexdigest() != metadata["host_canary_sha256"]:
        raise Refused()
    # The host controller proved this same public file exists outside the mount.
    # No real home, credential, label or arbitrary caller path is probed.
    for path in (host_path, stage / ".." / "host-canary.json"):
        try:
            with path.open("rb") as stream:
                stream.read(1)
        except OSError as exc:
            if exc.errno not in (errno.ENOENT, errno.EACCES):
                raise Refused() from None
        else:
            raise Refused()
    for path in (stage / "unexpected-write", Path("/unexpected-write")):
        try:
            with path.open("xb") as stream:
                stream.write(b"public canary")
        except OSError as exc:
            if exc.errno not in (errno.EROFS, errno.EACCES):
                raise Refused() from None
        else:
            path.unlink()
            raise Refused()
    with tempfile.TemporaryDirectory(prefix="ae-public-canary-") as name:
        writable = Path(name) / "canary"
        writable.write_bytes(expected)
        if _read(writable) != expected:
            raise Refused()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.settimeout(0.25)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(0.25)
            client.connect(server.getsockname())
            peer, _ = server.accept()
            with peer:
                peer.settimeout(0.25)
                peer.sendall(nonce.encode())
                if client.recv(64) != nonce.encode():
                    raise Refused()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as outbound:
        outbound.settimeout(0.25)
        try:
            outbound.connect(("192.0.2.1", 9))
        except OSError as exc:
            if exc.errno != errno.ENETUNREACH:
                raise Refused() from None
        else:
            raise Refused()
    return {
        "public_canary_sha256": hashlib.sha256(public).hexdigest(),
        "mounted_public_canary_read": True,
        "unmounted_host_canary_read": False,
        "parent_traversal_canary_read": False,
        "root_and_stage_write": False,
        "temporary_canary_read_write": True,
        "loopback_positive_control": True,
        "documentation_address_errno": errno.ENETUNREACH,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=MODES)
    parser.add_argument("--nonce", required=True)
    args = parser.parse_args(argv)
    armed = False
    previous_handler = None
    try:
        observed = inspect_context()
        worker = verify_stage(Path("/qualification"), args.nonce)
        previous_handler = signal.signal(signal.SIGALRM, lambda *_: os._exit(124))
        signal.alarm(10)
        armed = True
        result = {
            "schema": "utility-container-probe-result-v1",
            "nonce": args.nonce,
            "mode": args.mode,
            "qualified": False,
            "observed_context": observed,
        }
        if args.mode == "hold":
            result["status"] = "synthetic_hold_ready"
            print(json.dumps(result, allow_nan=False, sort_keys=True), flush=True)
            while True:
                signal.pause()
        elif args.mode == "isolation":
            result.update(isolation_checks(Path("/qualification"), args.nonce))
        elif args.mode == "score":
            result.update(synthetic_score(worker))
        elif args.mode == "memory-small":
            result["allocation_bytes"] = allocate(ALLOCATION_BYTES)
        elif args.mode == "memory-overrun":
            allocate(2 * MEMORY_BYTES)
            result["status"] = "overrun_survived"
            print(json.dumps(result, allow_nan=False, sort_keys=True), flush=True)
            return 3
        result["status"] = "synthetic_control_observed"
        print(json.dumps(result, allow_nan=False, sort_keys=True), flush=True)
        return 0
    except Exception:
        print(
            '{"schema":"utility-container-probe-result-v1","status":"refused","qualified":false}',
            flush=True,
        )
        return 2
    finally:
        if armed:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous_handler)


if __name__ == "__main__":
    raise SystemExit(main())
