"""Explicit local Unix-socket candidate runtime for the fixed private scorer.

No image pull, remote endpoint, generated code, registry activation or scientific
admission is provided. The caller owns data admission and confirmation grants.
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import select
import socket
import stat
import struct
import subprocess
import sys
import time
import uuid

IMAGE = "sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704"
PURPOSE = "utility-private-rmse-container-candidate-v1"
MODES = ("score",)
MEMORY = 67108864
OUTPUT = 16384


class Refused(ValueError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def write(path, value):
    with path.open("xb") as stream:
        stream.write(encode(value) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_regular(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise Refused("runtime evidence must be a bounded regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise Refused("runtime evidence exceeds its bound")
        return raw
    finally:
        os.close(fd)


class Connection(http.client.HTTPConnection):
    def __init__(self, socket_path, **kwargs):
        super().__init__("localhost", **kwargs)
        self.socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


class API:
    def __init__(self, socket_path, version=""):
        if not Path(socket_path).is_absolute() or "\x00" in str(socket_path):
            raise Refused("runtime requires an explicit local Unix socket")
        self.socket_path = str(socket_path)
        if version and not re.fullmatch(r"1\.[0-9]{1,3}", version):
            raise Refused("invalid local API version")
        self.prefix = "/v" + version if version else ""

    def request(self, method, path, value=None, *, limit=262144):
        connection = Connection(self.socket_path, timeout=3)
        try:
            connection.request(
                method,
                self.prefix + path,
                body=encode(value) if value else None,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise Refused("local API response exceeds bound")
            return response.status, raw
        finally:
            connection.close()

    def json(self, method, path, value=None, *, expected=200):
        status, raw = self.request(method, path, value)
        if status != expected:
            raise Refused("local API request did not complete")
        return json.loads(raw)

    def inspect(self, cid):
        if not re.fullmatch(r"[0-9a-f]{64}", cid):
            raise Refused("invalid owned container ID")
        status, raw = self.request("GET", f"/containers/{cid}/json")
        if status == 404:
            return None
        if status != 200:
            raise Refused("container absence is unverified")
        return json.loads(raw)


def configuration(nonce, mode, stage):
    if not re.fullmatch(r"[0-9a-f]{32}", nonce) or mode not in MODES:
        raise Refused("invalid synthetic control")
    return {
        "Image": IMAGE,
        "User": "65534:65534",
        "WorkingDir": "/qualification",
        "Entrypoint": ["python3", "-I", "-S", "-B", "/qualification/private_container_worker.py"],
        "Cmd": ["score"],
        "AttachStdout": True,
        "AttachStderr": True,
        "Labels": {"org.autoengineering.purpose": PURPOSE, "org.autoengineering.nonce": nonce},
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges"],
            "Memory": MEMORY,
            "MemorySwap": MEMORY,
            "NanoCpus": 1000000000,
            "PidsLimit": 16,
            "CgroupnsMode": "private",
            "IpcMode": "none",
            "Privileged": False,
            "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
            "Mounts": [
                {"Type": "bind", "Source": str(stage), "Target": "/qualification", "ReadOnly": True}
            ],
            "Tmpfs": {"/tmp": "rw,noexec,nosuid,nodev,size=4m"},
            "LogConfig": {"Type": "json-file", "Config": {"max-size": "16k", "max-file": "1"}},
        },
    }


def verify_identity(value, plan):
    expected = configuration(plan["nonce"], plan["mode"], Path(plan["stage"]))
    if (
        value["Id"] != plan["container_id"]
        or value["Image"] != IMAGE
        or value["Name"] != "/ae-private-rmse-" + plan["nonce"]
    ):
        raise Refused("container identity differs")
    config = value["Config"]
    if any(config.get("Labels", {}).get(k) != v for k, v in expected["Labels"].items()):
        raise Refused("container owner binding differs")


def verify_owned(value, plan):
    verify_identity(value, plan)
    expected = configuration(plan["nonce"], plan["mode"], Path(plan["stage"]))
    config, host = value["Config"], value["HostConfig"]
    for key in ("User", "WorkingDir", "Entrypoint", "Cmd", "Image"):
        if config[key] != expected[key]:
            raise Refused("container command differs")
    if any(config.get("Labels", {}).get(k) != v for k, v in expected["Labels"].items()):
        raise Refused("container owner binding differs")
    for key in (
        "NetworkMode",
        "ReadonlyRootfs",
        "Memory",
        "MemorySwap",
        "NanoCpus",
        "PidsLimit",
        "CgroupnsMode",
        "IpcMode",
        "Privileged",
        "CapDrop",
        "SecurityOpt",
        "Tmpfs",
        "LogConfig",
        "RestartPolicy",
    ):
        if host[key] != expected["HostConfig"][key]:
            raise Refused("container resource or isolation settings differ")
    if host.get("PidMode", "") or host.get("Devices") or host.get("Binds"):
        raise Refused("container has unapproved host access")
    mounts = value["Mounts"]
    binds = [m for m in mounts if m["Type"] == "bind"]
    extras = [m for m in mounts if m["Type"] != "bind"]
    if len(binds) != 1 or any(
        binds[0].get(k) != v
        for k, v in {
            "Type": "bind",
            "Source": plan["stage"],
            "Destination": "/qualification",
            "RW": False,
        }.items()
    ):
        raise Refused("container mounts differ")
    if extras and (
        len(extras) != 1
        or extras[0].get("Type") != "tmpfs"
        or extras[0].get("Destination") != "/tmp"
        or extras[0].get("RW") is not True
    ):
        raise Refused("container has an unapproved extra mount")


def cleanup(api, plan, directory, reason):
    before = api.inspect(plan["container_id"])
    if before is not None:
        # A resource-setting mismatch must prevent start, not prevent cleanup of
        # the exact container we own. Never remove an unrelated container.
        verify_identity(before, plan)
        write(directory / "cleanup-before.json", before)
        status, _ = api.request("DELETE", f"/containers/{plan['container_id']}?force=true")
        if status not in (204, 404):
            raise Refused("owned container removal is unverified")
    if api.inspect(plan["container_id"]) is not None:
        raise Refused("owned container still exists")
    write(
        directory / "cleanup.json",
        {
            "container_id": plan["container_id"],
            "nonce": plan["nonce"],
            "reason": reason,
            "removed": True,
        },
    )


def logs(raw):
    output = {1: bytearray(), 2: bytearray()}
    while raw:
        if len(raw) < 8:
            raise Refused("truncated container output frame")
        stream, reserved, size = raw[0], raw[1:4], struct.unpack(">I", raw[4:8])[0]
        if stream not in output or reserved != b"\0\0\0" or len(raw) < size + 8:
            raise Refused("invalid container output frame")
        output[stream].extend(raw[8 : 8 + size])
        raw = raw[8 + size :]
    if sum(map(len, output.values())) > OUTPUT:
        raise Refused("container output exceeds bound")
    return bytes(output[1]), bytes(output[2])


def watchdog(plan_path, owner_fd):
    directory = plan_path.parent
    plan = json.loads(plan_path.read_bytes())
    if (
        plan["runtime_sha256"] != sha(Path(__file__).read_bytes())
        or not stat.S_ISFIFO(os.fstat(owner_fd).st_mode)
        or Path(plan["stage"]) != directory / "stage"
    ):
        raise Refused("watchdog source or owner binding differs")
    api = API(plan["socket_path"], plan["api_version"])
    value = api.inspect(plan["container_id"])
    if value is None:
        raise Refused("original created container is absent")
    verify_owned(value, plan)
    write(
        directory / "watchdog-ready.json",
        {
            "container_id": plan["container_id"],
            "nonce": plan["nonce"],
            "watchdog_pid": os.getpid(),
        },
    )
    deadline = time.monotonic() + 10
    reason = "deadline"
    while time.monotonic() < deadline:
        ready, _, _ = select.select(
            [owner_fd], [], [], min(0.1, max(0, deadline - time.monotonic()))
        )
        if ready and not os.read(owner_fd, 1):
            reason = "owner_pipe_eof"
            break
    cleanup(api, plan, directory, reason)


class FixedScorerRuntime:
    """Candidate API boundary. No constructor or offline recovery opens labels."""

    def __init__(self, socket_path: Path, *, server_sha256: str):
        self.socket_path = str(socket_path)
        API(self.socket_path)  # Validate configuration without opening a socket.
        if not re.fullmatch(r"[0-9a-f]{64}", server_sha256):
            raise Refused("runtime needs an explicit server fingerprint")
        self.server_sha256 = server_sha256
        self.runtime_bytes = Path(__file__).read_bytes()
        self.wrapper_bytes = Path(__file__).with_name("private_container_worker.py").read_bytes()
        self.worker_bytes = Path(__file__).with_name("private_score_worker.py").read_bytes()
        self.identity = sha(
            encode(
                {
                    "profile": PURPOSE,
                    "socket": self.socket_path,
                    "server": server_sha256,
                    "image": IMAGE,
                    "runtime": sha(self.runtime_bytes),
                    "wrapper": sha(self.wrapper_bytes),
                    "worker": sha(self.worker_bytes),
                    "memory": MEMORY,
                    "output": OUTPUT,
                    "watchdog_seconds": 10,
                }
            )
        )

    def preflight(self):
        """Read daemon/image metadata before any private-byte access."""
        value = API(self.socket_path).json("GET", "/version")
        if sha(encode(value)) != self.server_sha256:
            raise Refused("local daemon differs from registered runtime")
        api = API(self.socket_path, value["ApiVersion"])
        image = api.json("GET", "/images/" + IMAGE + "/json")
        if image["Id"] != IMAGE or image["Os"] != "linux" or image["Architecture"] != "arm64":
            raise Refused("cached pinned local ARM64 image is unavailable")
        return value["ApiVersion"]

    def run(self, root: Path, *, api_version: str, job_sha256: str, labels_sha256: str):
        """Run one already-staged private attempt. Existing execution is never reused."""
        if (
            not root.is_absolute()
            or any(p.is_symlink() for p in (root, *root.parents))
            or root.stat().st_uid != os.geteuid()
            or stat.S_IMODE(root.stat().st_mode) & 0o077
        ):
            raise Refused("private runtime root must be owned and private")
        directory = root / "container"
        directory.mkdir(mode=0o700)
        stage = directory / "stage"
        stage.mkdir(mode=0o700)
        for name in ("job.json", "labels.json"):
            source = root / "workspace" / name
            # All reads happen after the scorer's durable access intent. The
            # derived private stage is never a grant to an agent/model worker.
            (stage / name).write_bytes(read_regular(source, 1048576))
        for name, raw in (
            ("private_score_worker.py", self.worker_bytes),
            ("private_container_worker.py", self.wrapper_bytes),
        ):
            (stage / name).write_bytes(raw)
        for path in stage.iterdir():
            path.chmod(0o444)
        stage.chmod(0o555)
        source_hashes = {p.name: sha(read_regular(p, 1048576)) for p in stage.iterdir()}
        if source_hashes["job.json"] != job_sha256 or source_hashes["labels.json"] != labels_sha256:
            raise Refused("staged scoring inputs differ from the durable access intent")
        write(directory / "stage-hashes.json", source_hashes)
        (directory / "runtime.py").write_bytes(self.runtime_bytes)
        (directory / "runtime.py").chmod(0o500)
        nonce = uuid.uuid4().hex
        config = configuration(nonce, "score", stage)
        api = API(self.socket_path, api_version)
        write(directory / "create-intent.json", config)
        created = api.json(
            "POST", "/containers/create?name=ae-private-rmse-" + nonce, config, expected=201
        )
        cid = created["Id"]
        if not re.fullmatch(r"[0-9a-f]{64}", cid):
            raise Refused("create acknowledgement lacks an exact original ID")
        plan = {
            "container_id": cid,
            "nonce": nonce,
            "mode": "score",
            "stage": str(stage),
            "api_version": api_version,
            "socket_path": self.socket_path,
            "runtime_sha256": sha(self.runtime_bytes),
            "runtime_identity": self.identity,
            "job_sha256": job_sha256,
            "labels_sha256": labels_sha256,
        }
        write(directory / "plan.json", plan)
        read_fd, write_fd = os.pipe()
        child = None
        try:
            with (
                (directory / "watchdog.stdout").open("xb") as out,
                (directory / "watchdog.stderr").open("xb") as err,
            ):
                child = subprocess.Popen(
                    [
                        sys.executable,
                        "-I",
                        "-S",
                        "-B",
                        str(directory / "runtime.py"),
                        "--plan",
                        str(directory / "plan.json"),
                        "--owner-fd",
                        str(read_fd),
                    ],
                    pass_fds=(read_fd,),
                    stdout=out,
                    stderr=err,
                    start_new_session=True,
                    env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
                )
            os.close(read_fd)
            read_fd = None
            deadline = time.monotonic() + 5
            while not (directory / "watchdog-ready.json").exists():
                if child.poll() is not None or time.monotonic() >= deadline:
                    raise Refused("watchdog did not arm before start")
                time.sleep(0.02)
            ready = json.loads(read_regular(directory / "watchdog-ready.json", 1024))
            if ready["container_id"] != cid or ready["nonce"] != nonce:
                raise Refused("watchdog readiness belongs to another original container")
            before = api.inspect(cid)
            verify_owned(before, plan)
            if before["State"]["Running"] or before["State"]["Status"] != "created":
                raise Refused("original container already ran")
            write(directory / "before-start.json", before)
            if any(
                sha(read_regular(stage / name, 1048576)) != value
                for name, value in source_hashes.items()
            ):
                raise Refused("private stage changed before start")
            write(directory / "start-intent.json", {"container_id": cid, "nonce": nonce})
            status, _ = api.request("POST", f"/containers/{cid}/start")
            if status != 204:
                raise Refused("start acknowledgement is uncertain; no retry")
            deadline = time.monotonic() + 8
            while True:
                final = api.inspect(cid)
                if final is None:
                    raise Refused("original container disappeared before result reconciliation")
                verify_owned(final, plan)
                if not final["State"]["Running"]:
                    break
                if time.monotonic() >= deadline:
                    raise Refused("fixed scorer exceeded its deadline")
                time.sleep(0.05)
            write(directory / "final-inspect.json", final)
            state = final["State"]
            if state["ExitCode"] != 0 or state["OOMKilled"] or final["RestartCount"] != 0:
                raise Refused("original scorer did not complete successfully")
            status, raw = api.request(
                "GET", f"/containers/{cid}/logs?stdout=1&stderr=1", limit=32768
            )
            if status != 200:
                raise Refused("original scorer output is unavailable")
            stdout, stderr = logs(raw)
            (directory / "stdout.bin").write_bytes(stdout)
            (directory / "stderr.bin").write_bytes(stderr)
            result = json.loads(stdout)
            if (
                stderr
                or result["schema"] != "private-container-output-v1"
                or result["mode"] != "score"
                or result["output_limit_bytes"] != OUTPUT
                or result["output_limited"] is not False
                or result["child_exit_code"] != 0
                or result["child_signal"] is not None
                or not 0 < result["captured_bytes"] < OUTPUT
            ):
                raise Refused("scorer output is failed, malformed or limited")
            write(
                directory / "result.json",
                {
                    "container_id": cid,
                    "nonce": nonce,
                    "runtime_identity": self.identity,
                    "stdout_sha256": sha(stdout),
                    "result": result,
                },
            )
        finally:
            if read_fd is not None:
                os.close(read_fd)
            os.close(write_fd)
            if child is not None:
                child.wait(timeout=15)
            if not (directory / "cleanup.json").exists():
                cleanup(api, plan, directory, "parent_reconciliation")
            if api.inspect(cid) is not None:
                raise Refused("original scorer cleanup is unresolved")
        return self.recover(root, job_sha256=job_sha256, labels_sha256=labels_sha256)

    def recover(self, root: Path, *, job_sha256: str, labels_sha256: str):
        """Offline completed-result recovery. No API, labels, create or start."""
        directory = root / "container"

        def document(name):
            path = directory / name
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 262144:
                raise Refused("saved runtime evidence is unavailable")
            return json.loads(path.read_bytes())

        plan = document("plan.json")
        if plan["runtime_identity"] != self.identity or plan["runtime_sha256"] != sha(
            self.runtime_bytes
        ):
            raise Refused("saved runtime binding differs")
        sources = document("stage-hashes.json")
        if (
            sources["job.json"] != job_sha256
            or sources["labels.json"] != labels_sha256
            or plan["job_sha256"] != job_sha256
            or plan["labels_sha256"] != labels_sha256
            or sha(read_regular(directory / "stage/job.json", 1048576)) != job_sha256
        ):
            raise Refused("saved public job or private input identity differs")
        if read_regular(directory / "runtime.py", 65536) != self.runtime_bytes:
            raise Refused("saved runtime source differs")
        for name, expected in (
            ("private_container_worker.py", self.wrapper_bytes),
            ("private_score_worker.py", self.worker_bytes),
        ):
            if read_regular(directory / "stage" / name, 65536) != expected:
                raise Refused("saved fixed scorer source differs")
        for name in ("before-start.json", "final-inspect.json"):
            verify_owned(document(name), plan)
        final = document("final-inspect.json")
        if (
            final["State"]["Running"]
            or final["State"]["ExitCode"] != 0
            or final["State"]["OOMKilled"]
            or final["RestartCount"] != 0
        ):
            raise Refused("saved original scorer did not stop successfully")
        receipt, result = document("cleanup.json"), document("result.json")
        for bound in (
            receipt,
            result,
            document("start-intent.json"),
            document("watchdog-ready.json"),
        ):
            if bound["container_id"] != plan["container_id"] or bound["nonce"] != plan["nonce"]:
                raise Refused("saved receipt belongs to another original container")
        if receipt["removed"] is not True or result["runtime_identity"] != self.identity:
            raise Refused("saved original cleanup is unresolved")
        stdout = directory / "stdout.bin"
        if stdout.is_symlink() or not stdout.is_file() or stdout.stat().st_size > OUTPUT:
            raise Refused("saved bounded output is unavailable")
        raw = stdout.read_bytes()
        captured = json.loads(raw)
        if read_regular(directory / "stderr.bin", OUTPUT) != b"":
            raise Refused("saved scorer stderr differs")
        if sha(raw) != result["stdout_sha256"] or captured != result["result"]:
            raise Refused("saved output identity differs")
        if (
            captured["schema"] != "private-container-output-v1"
            or captured["mode"] != "score"
            or captured["private_scoring_qualified"] is not False
            or captured["output_limited"] is not False
            or captured["child_exit_code"] != 0
            or captured["child_signal"] is not None
            or captured["output_limit_bytes"] != OUTPUT
            or not 0 < captured["captured_bytes"] < OUTPUT
        ):
            raise Refused("saved child result was not bounded and successful")
        return captured["score"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--owner-fd", type=int, required=True)
    arguments = parser.parse_args()
    watchdog(arguments.plan, arguments.owner_fd)
