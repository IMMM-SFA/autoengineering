"""Fixed, bounded diagnostic worker for the candidate inference image.

Run only under the separately owned container controller. This stdlib worker
neither starts containers nor establishes lifecycle or private-data admission.
It refuses before resource actions unless the observed guest policy matches.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import socket
import stat
import sys

MEMORY = 1073741824
WORKSPACE = 134217728
CHUNK = 1048576
PYTHON_BUILD = "b045b35133aee229f091997de805d765ccda1c386ba6b0802f6534008f759cca"
MODES = (
    "memory_limit",
    "pid_limit",
    "workspace_limit",
    "read_only_root",
    "network_denied",
    "host_canary_denied",
)


class Refused(ValueError):
    """Report a fixed reason without paths, private bytes or raw exceptions."""


def read(path, limit=65536):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise Refused("metadata_type_or_size")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
    finally:
        os.close(descriptor)
    if len(raw) > limit:
        raise Refused("metadata_size")
    return raw.decode("ascii")


def context():
    """Observe exact limits before any allocation, fork, write or connection."""
    if (
        platform.system() != "Linux"
        or platform.machine() != "x86_64"
        or platform.python_implementation() != "CPython"
        or sys.version_info[:3] != (3, 12, 13)
        or hashlib.sha256(sys.version.encode()).hexdigest() != PYTHON_BUILD
        or sys.executable != "/opt/inference/bin/python"
        or not sys.flags.isolated
        or not sys.flags.no_site
        or not sys.dont_write_bytecode
        or (os.geteuid(), os.getegid()) != (1000, 1000)
    ):
        raise Refused("interpreter_or_user")
    limits = {
        name: read("/sys/fs/cgroup/" + name).strip()
        for name in ("memory.max", "memory.swap.max", "pids.max", "cpu.max")
    }
    if limits != {
        "memory.max": str(MEMORY),
        "memory.swap.max": "0",
        "pids.max": "16",
        "cpu.max": "100000 100000",
    }:
        raise Refused("effective_limits")
    status = {}
    for line in read("/proc/self/status").splitlines():
        name, separator, value = line.partition(":")
        if not separator or name in status:
            raise Refused("process_status")
        status[name] = value.strip()
    if (
        status.get("NoNewPrivs") != "1"
        or status.get("Seccomp") != "2"
        or any(
            status.get(name) != "0000000000000000"
            for name in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb")
        )
    ):
        raise Refused("process_privileges")
    mounts = {}
    for line in read("/proc/self/mounts").splitlines():
        parts = line.split()
        if len(parts) != 6:
            raise Refused("mount_metadata")
        if parts[1] in ("/", "/work"):
            if parts[1] in mounts:
                raise Refused("duplicate_mount")
            mounts[parts[1]] = (parts[2], set(parts[3].split(",")))
    if "/" not in mounts or "ro" not in mounts["/"][1] or "rw" in mounts["/"][1]:
        raise Refused("root_mount")
    if (
        "/work" not in mounts
        or mounts["/work"][0] != "tmpfs"
        or not {"rw", "noexec", "nosuid", "nodev", "size=131072k"} <= mounts["/work"][1]
    ):
        raise Refused("workspace_mount")
    work = os.stat("/work", follow_symlinks=False)
    if (
        not stat.S_ISDIR(work.st_mode)
        or stat.S_IMODE(work.st_mode) != 0o700
        or (work.st_uid, work.st_gid) != (1000, 1000)
    ):
        raise Refused("workspace_permissions")
    if os.statvfs("/work").f_blocks * os.statvfs("/work").f_frsize != WORKSPACE:
        raise Refused("workspace_capacity")
    devices = read("/proc/net/dev").splitlines()[2:]
    if {line.split(":", 1)[0].strip() for line in devices if line.strip()} != {"lo"}:
        raise Refused("network_interfaces")
    return {
        "effective_limits": limits,
        "workspace_bytes": WORKSPACE,
        "root_read_only": True,
        "network_interfaces": ["lo"],
        "uid": 1000,
        "gid": 1000,
        "seccomp": 2,
        "capabilities": "none",
    }


def memory_limit(nonce):
    # Hold and touch at most 1 GiB + 64 MiB. Only a daemon OOMKilled observation
    # plus exit 137 can qualify this control. Missing output is never sufficient.
    held = []
    for _ in range(17):
        block = bytearray(64 * CHUNK)
        for offset in range(0, len(block), 4096):
            block[offset] = 1
        held.append(block)
    raise Refused("memory_cap_not_observed")


def pid_limit(nonce):
    children = []
    reader, writer = os.pipe()
    try:
        for _ in range(20):
            try:
                child = os.fork()
            except OSError as error:
                if error.errno != errno.EAGAIN:
                    raise Refused("pid_failure_not_limit") from None
                current = read("/sys/fs/cgroup/pids.current").strip()
                if current != "16" or not children:
                    raise Refused("pid_limit_not_observed")
                return {"errno": "EAGAIN", "pids_current": 16, "children": len(children)}
            if child == 0:
                os.close(writer)
                try:
                    os.read(reader, 1)
                finally:
                    os._exit(0)
            children.append(child)
        raise Refused("pid_cap_not_observed")
    finally:
        os.close(writer)
        os.close(reader)
        for child in children:
            while True:
                try:
                    waited, status = os.waitpid(child, 0)
                    if waited != child or status != 0:
                        raise Refused("child_cleanup")
                    break
                except InterruptedError:
                    continue


def workspace_limit(nonce):
    path = "/work/resource-" + nonce
    written = 0
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        block = b"\x00" * CHUNK
        while written <= WORKSPACE:
            try:
                count = os.write(descriptor, block[: min(CHUNK, WORKSPACE + CHUNK - written)])
            except OSError as error:
                if error.errno != errno.ENOSPC or written == 0:
                    raise Refused("workspace_failure_not_limit") from None
                return {"errno": "ENOSPC", "written_bytes": written}
            if not 0 < count <= CHUNK:
                raise Refused("workspace_write_count")
            written += count
        raise Refused("workspace_cap_not_observed")
    finally:
        os.close(descriptor)
        os.unlink(path)


def read_only_root(nonce):
    # A world-writable directory avoids accepting UID permission denial as proof.
    info = os.stat("/var/tmp", follow_symlinks=False)
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) & 0o777 != 0o777:
        raise Refused("root_probe_directory")
    path = "/var/tmp/ae-resource-" + nonce
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError as error:
        if error.errno != errno.EROFS:
            raise Refused("root_failure_not_read_only") from None
        return {"errno": "EROFS"}
    else:
        os.close(descriptor)
        os.unlink(path)
        raise Refused("root_write_succeeded")


def network_denied(nonce):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(2)
        try:
            connection.connect(("192.0.2.1", 9))
        except OSError as error:
            if error.errno not in (errno.ENETUNREACH, errno.EHOSTUNREACH):
                raise Refused("network_failure_not_isolation") from None
            return {"errno": errno.errorcode[error.errno], "attempts": 1}
    raise Refused("network_connect_succeeded")


def host_canary_denied(nonce, canary):
    # The controller authors this fresh host file. No byte is read, even if the
    # boundary fails. The path is metadata; it must never appear in output.
    if (
        not isinstance(canary, str)
        or not canary.startswith("/")
        or "\x00" in canary
        or (Path(canary).name != "ae-host-canary-" + nonce)
        or ".." in Path(canary).parts
    ):
        raise Refused("canary_metadata")
    try:
        descriptor = os.open(canary, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        if error.errno not in (errno.ENOENT, errno.ENOTDIR):
            raise Refused("canary_failure_not_absence") from None
        return {"errno": errno.errorcode[error.errno]}
    else:
        os.close(descriptor)
        raise Refused("host_canary_visible")


def emit(value):
    print(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False), flush=True)


def run(mode, nonce, canary=None):
    if (
        mode not in MODES
        or not re.fullmatch(r"[0-9a-f]{32}", nonce)
        or ((mode == "host_canary_denied") != (canary is not None))
    ):
        raise Refused("arguments")
    signal.alarm(45)
    observed = context()
    emit(
        {
            "schema": "utility-guest-resource-ready-v1",
            "mode": mode,
            "nonce": nonce,
            "observed": observed,
        }
    )
    result = (
        host_canary_denied(nonce, canary)
        if mode == "host_canary_denied"
        else globals()[mode](nonce)
    )
    emit(
        {
            "schema": "utility-guest-resource-result-v1",
            "mode": mode,
            "nonce": nonce,
            "result": result,
        }
    )
    signal.alarm(0)


def main():
    try:
        if len(sys.argv) not in (3, 4):
            raise Refused("arguments")
        run(*sys.argv[1:])
    except Refused as error:
        emit({"schema": "utility-guest-resource-refusal-v1", "reason": str(error)})
        return 2
    except Exception:
        emit({"schema": "utility-guest-resource-refusal-v1", "reason": "unverified_failure"})
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
