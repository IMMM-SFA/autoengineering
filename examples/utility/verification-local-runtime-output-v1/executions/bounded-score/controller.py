"""Bounded synthetic controls in the approved cached local ARM64 container.

No private inputs, remote daemon, image pulls or arbitrary images/commands are
accepted. A separate owner-pipe watchdog removes the exact owned container on
owner loss or deadline. Partial controls never admit a private scoring profile.
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
import signal
import socket
import stat
import struct
import subprocess
import sys
import time
import uuid

SOCKET = "/Users/cam/.orbstack/run/docker.sock"
IMAGE = "sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704"
PURPOSE = "utility-synthetic-runtime-v1"
BASE_MODES = ("preflight", "memory-small", "score", "memory-overrun")
MODES = (*BASE_MODES, "hold", "isolation", "output-small", "output-overrun", "bounded-score")
FAULTS = ("deadline", "cancellation", "owner-loss", "lost-start-ack")
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


class Connection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(SOCKET)


class API:
    def __init__(self, version=""):
        if version and not re.fullmatch(r"1\.[0-9]{1,3}", version):
            raise Refused("invalid local API version")
        self.prefix = "/v" + version if version else ""

    def request(self, method, path, value=None, *, limit=262144):
        connection = Connection("localhost", timeout=3)
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
        "Entrypoint": ["python3", "-I", "-S", "-B", "/qualification/probe.py"],
        "Cmd": [mode, "--nonce", nonce],
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
        or value["Name"] != "/ae-utility-qual-" + plan["nonce"]
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


def watchdog(plan_path, owner_fd):
    directory = plan_path.parent
    plan = json.loads(plan_path.read_bytes())
    if (
        plan["controller_sha256"] != sha(Path(__file__).read_bytes())
        or not stat.S_ISFIFO(os.fstat(owner_fd).st_mode)
        or Path(plan["stage"]) != directory / "stage"
    ):
        raise Refused("watchdog source or lease binding differs")
    api = API(plan["api_version"])
    value = api.inspect(plan["container_id"])
    if value is None:
        raise Refused("original created container is absent")
    verify_owned(value, plan)
    write(
        directory / "watchdog-ready.json",
        {"container_id": plan["container_id"], "nonce": plan["nonce"], "watchdog_pid": os.getpid()},
    )
    # Hold probes retain their own ten-second alarm. The shorter independent
    # deadline makes watchdog enforcement observable before that alarm fires.
    deadline = time.monotonic() + (5 if plan["mode"] == "hold" else 10)
    reason = "deadline"
    while time.monotonic() < deadline:
        ready, _, _ = select.select(
            [owner_fd], [], [], min(0.1, max(0, deadline - time.monotonic()))
        )
        if ready and not os.read(owner_fd, 1):
            reason = "owner_pipe_eof"
            break
    cleanup(api, plan, directory, reason)
    return 0


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


def lifecycle_fault(api, plan, directory, fault):
    """Inject one fixed fault only after the exact owned container proves it runs."""
    if fault not in FAULTS or plan["mode"] != "hold":
        raise Refused("invalid synthetic lifecycle fault")
    cid, nonce = plan["container_id"], plan["nonce"]
    deadline = time.monotonic() + 3
    while True:
        inspected = api.inspect(cid)
        if inspected is None:
            raise Refused("original control disappeared before fault injection")
        verify_owned(inspected, plan)
        if not inspected["State"]["Running"]:
            raise Refused("original control stopped before fault injection")
        status, raw = api.request("GET", f"/containers/{cid}/logs?stdout=1&stderr=1", limit=32768)
        if status != 200:
            raise Refused("hold witness is unavailable")
        out, err = logs(raw)
        if out:
            witness = json.loads(out)
            if (
                witness["nonce"] != nonce
                or witness["mode"] != "hold"
                or witness["status"] != "synthetic_hold_ready"
                or err
            ):
                raise Refused("hold witness differs")
            break
        if time.monotonic() >= deadline:
            raise Refused("hold did not become ready")
        time.sleep(0.02)
    write(directory / "fault-running-inspect.json", inspected)
    write(directory / "fault-witness.json", witness)
    write(
        directory / "fault-intent.json",
        {
            "container_id": cid,
            "nonce": nonce,
            "fault": fault,
            "owner_pid": os.getpid(),
            "start_response_delivered_to_controller": fault != "lost-start-ack",
            "fault_scope": "fixed synthetic fault; no private scoring or retry",
        },
    )
    if fault in ("cancellation", "owner-loss"):
        # Kill only this synthetic controller. No finally block can clean up;
        # the already armed independent watchdog must act on actual pipe EOF.
        os.kill(os.getpid(), signal.SIGTERM if fault == "cancellation" else signal.SIGKILL)
        raise Refused("synthetic owner termination did not occur")
    if fault == "lost-start-ack":
        # The transport received the daemon response, but the controller has no
        # acknowledgement. Reconcile the original ID and close its lease. Never
        # POST another start or create a replacement container.
        return
    while not (directory / "cleanup.json").exists():
        if time.monotonic() >= deadline + 12:
            raise Refused("independent deadline cleanup was not observed")
        time.sleep(0.05)


def run_case(root, api, version, mode, sources, fault=None):
    if (mode == "hold") != (fault in FAULTS):
        raise Refused("hold mode requires a fixed lifecycle fault")
    nonce = uuid.uuid4().hex
    directory = root / mode
    directory.mkdir(mode=0o700)
    stage = directory / "stage"
    stage.mkdir(mode=0o700)
    if mode == "isolation":
        if not str(root).startswith("/private/tmp/utility-runtime-isolation-"):
            raise Refused("isolation control needs its owned public-canary directory")
        public = json.dumps({"public_synthetic_canary": nonce}, sort_keys=True).encode() + b"\n"
        host_canary = root / "host-canary.json"
        with host_canary.open("xb") as stream:
            stream.write(public)
        if host_canary.read_bytes() != public:
            raise Refused("unrestricted host positive control failed")
        write(
            directory / "host-positive-control.json",
            {
                "nonce": nonce,
                "canary_sha256": sha(public),
                "read_succeeded": True,
            },
        )
        sources = {
            **sources,
            "public-canary.json": public,
            "isolation.json": encode(
                {
                    "host_canary_path": str(host_canary),
                    "host_canary_sha256": sha(public),
                }
            )
            + b"\n",
        }
    for name, raw in sources.items():
        (stage / name).write_bytes(raw)
        (stage / name).chmod(0o444)
    write(stage / "scope.json", {"schema": "utility-container-probe-scope-v1", "nonce": nonce})
    (stage / "scope.json").chmod(0o444)
    stage.chmod(0o555)
    config = configuration(nonce, mode, stage)
    write(directory / "create-intent.json", config)
    created = api.json(
        "POST", "/containers/create?name=ae-utility-qual-" + nonce, config, expected=201
    )
    cid = created["Id"]
    if not re.fullmatch(r"[0-9a-f]{64}", cid):
        raise Refused("create acknowledgement lacks an exact ID")
    plan = {
        "container_id": cid,
        "nonce": nonce,
        "mode": mode,
        "stage": str(stage),
        "api_version": version,
        "controller_sha256": sha((root / "controller.py").read_bytes()),
    }
    write(directory / "plan.json", plan)
    lease_read, lease_write = os.pipe()
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
                    str(root / "controller.py"),
                    "watchdog",
                    "--plan",
                    str(directory / "plan.json"),
                    "--owner-fd",
                    str(lease_read),
                ],
                pass_fds=(lease_read,),
                stdout=out,
                stderr=err,
                start_new_session=True,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
        os.close(lease_read)
        lease_read = None
        deadline = time.monotonic() + 5
        while not (directory / "watchdog-ready.json").exists():
            if child.poll() is not None or time.monotonic() >= deadline:
                raise Refused("watchdog did not arm before start")
            time.sleep(0.02)
        ready = json.loads((directory / "watchdog-ready.json").read_bytes())
        if ready["container_id"] != cid or ready["nonce"] != nonce:
            raise Refused("watchdog readiness belongs to another container")
        before = api.inspect(cid)
        verify_owned(before, plan)
        if before["State"]["Running"] or before["State"]["Status"] != "created":
            raise Refused("container already ran before start intent")
        write(directory / "before-start.json", before)
        write(directory / "start-intent.json", {"container_id": cid, "nonce": nonce})
        status, _ = api.request("POST", f"/containers/{cid}/start")
        if fault != "lost-start-ack" and status != 204:
            raise Refused("start acknowledgement is uncertain")
        if fault:
            lifecycle_fault(api, plan, directory, fault)
            record = {
                "mode": mode,
                "container_id": cid,
                "nonce": nonce,
                "fault": fault,
                "qualified": False,
            }
            write(directory / "fault-parent-result.json", record)
            return record
        deadline = time.monotonic() + 15
        while True:
            final = api.inspect(cid)
            if final is None:
                raise Refused("container removed before result reconciliation")
            verify_owned(final, plan)
            if not final["State"]["Running"]:
                break
            if time.monotonic() >= deadline:
                raise Refused("container did not stop within bound")
            time.sleep(0.05)
        write(directory / "final-inspect.json", final)
        status, raw = api.request("GET", f"/containers/{cid}/logs?stdout=1&stderr=1", limit=32768)
        if status != 200:
            raise Refused("original container output is unavailable")
        stdout, stderr = logs(raw)
        (directory / "stdout.bin").write_bytes(stdout)
        (directory / "stderr.bin").write_bytes(stderr)
        state = final["State"]
        if final["RestartCount"] != 0:
            raise Refused("owned container restarted; original execution is uncertain")
        if mode == "memory-overrun":
            passed = state["OOMKilled"] is True and state["ExitCode"] == 137
            result = None
        else:
            result = json.loads(stdout)
            passed = (
                state["ExitCode"] == 0
                and not state["OOMKilled"]
                and result["status"] == "synthetic_control_observed"
                and result["qualified"] is False
                and result["nonce"] == nonce
            )
            if mode == "score":
                passed = (
                    passed and result["synthetic_rmse"] == 1.0 and result["vector_length"] == 64
                )
            if mode == "isolation":
                passed = (
                    passed
                    and result["public_canary_sha256"] == sha(public)
                    and result["mounted_public_canary_read"] is True
                    and result["unmounted_host_canary_read"] is False
                    and result["parent_traversal_canary_read"] is False
                    and result["root_and_stage_write"] is False
                    and result["temporary_canary_read_write"] is True
                    and result["loopback_positive_control"] is True
                    and result["documentation_address_errno"] == 101
                )
            if mode in ("output-small", "output-overrun", "bounded-score"):
                capture = result["output_capture"]
                passed = (
                    passed
                    and capture["output_limit_bytes"] == OUTPUT
                    and capture["private_scoring_qualified"] is False
                )
                if mode == "bounded-score":
                    passed = (
                        passed
                        and capture["child_exit_code"] == 0
                        and capture["output_limited"] is False
                        and capture["score"]["value"] == 1.0
                    )
                else:
                    expected = (
                        (4096, None, 0, False)
                        if mode == "output-small"
                        else (16384, int(signal.SIGXFSZ), None, True)
                    )
                    passed = (
                        passed
                        and tuple(
                            capture[k]
                            for k in (
                                "captured_bytes",
                                "child_signal",
                                "child_exit_code",
                                "output_limited",
                            )
                        )
                        == expected
                    )
        record = {
            "mode": mode,
            "container_id": cid,
            "nonce": nonce,
            "passed": passed,
            "exit_code": state["ExitCode"],
            "oom_killed": state["OOMKilled"],
            "result": result,
        }
        write(directory / "result.json", record)
    finally:
        if lease_read is not None:
            os.close(lease_read)
        os.close(lease_write)
        if child is not None:
            child.wait(timeout=15)
        if not (directory / "cleanup.json").exists():
            cleanup(api, plan, directory, "parent_reconciliation")
        if api.inspect(cid) is not None:
            raise Refused("original container cleanup is unresolved")
    return record


def reconcile_lifecycle(root):
    """Inspect only the original ID after a fault; never create or start work."""
    directory = root / "hold"
    plan = json.loads((directory / "plan.json").read_bytes())
    intent = json.loads((directory / "fault-intent.json").read_bytes())
    if (
        plan["mode"] != "hold"
        or intent["fault"] not in FAULTS
        or plan["controller_sha256"] != sha((root / "controller.py").read_bytes())
    ):
        raise Refused("lifecycle source or mode binding differs")
    for name in ("fault-running-inspect.json", "cleanup-before.json"):
        value = json.loads((directory / name).read_bytes())
        verify_owned(value, plan)
        if value["State"]["Running"] is not True:
            raise Refused("fault did not exercise a running original container")
    expected_reason = "deadline" if intent["fault"] == "deadline" else "owner_pipe_eof"
    receipt = json.loads((directory / "cleanup.json").read_bytes())
    for bound in (intent, receipt):
        if bound["container_id"] != plan["container_id"] or bound["nonce"] != plan["nonce"]:
            raise Refused("lifecycle fault belongs to another original container")
    if receipt["reason"] != expected_reason or receipt["removed"] is not True:
        raise Refused("expected independent cleanup is unverified")
    if API(plan["api_version"]).inspect(plan["container_id"]) is not None:
        raise Refused("original container still exists")
    result = {
        "schema": "utility-synthetic-lifecycle-reconciliation-v1",
        "fault": intent["fault"],
        "container_id": plan["container_id"],
        "nonce": plan["nonce"],
        "removed": True,
        "live_absence_confirmed": True,
        "private_scoring_qualified": False,
        "start_retries": 0,
    }
    write(directory / "fault-reconciled.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--mode", choices=MODES)
    run.add_argument("--fault", choices=FAULTS)
    watch = sub.add_parser("watchdog")
    watch.add_argument("--plan", type=Path, required=True)
    watch.add_argument("--owner-fd", type=int, required=True)
    reconcile = sub.add_parser("reconcile-lifecycle")
    reconcile.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "watchdog":
        return watchdog(args.plan, args.owner_fd)
    if args.command == "reconcile-lifecycle":
        print(json.dumps(reconcile_lifecycle(args.output.absolute()), sort_keys=True))
        return 0
    if (args.mode == "hold") != (args.fault in FAULTS):
        raise Refused("hold mode and fixed fault must be selected together")
    root = args.output.absolute()
    if root.exists() or any(p.is_symlink() for p in (root, *root.parents)) or "," in str(root):
        raise Refused("qualification output must be fresh and confined")
    root.mkdir(mode=0o700, parents=True)
    controller = Path(__file__).read_bytes()
    (root / "controller.py").write_bytes(controller)
    (root / "controller.py").chmod(0o500)
    repository = Path(__file__).resolve().parents[1]
    sources = {
        "probe.py": (repository / "scripts/utility_container_probe.py").read_bytes(),
        "private_score_worker.py": (
            repository / "src/autoengineering/utility/private_score_worker.py"
        ).read_bytes(),
    }
    if args.mode in ("output-small", "output-overrun", "bounded-score"):
        sources["private_container_worker.py"] = (
            repository / "src/autoengineering/utility/private_container_worker.py"
        ).read_bytes()
    write(
        root / "sources.json",
        {"controller.py": sha(controller), **{k: sha(v) for k, v in sources.items()}},
    )
    bootstrap = API()
    version_data = bootstrap.json("GET", "/version")
    write(root / "engine-version.json", version_data)
    version = version_data["ApiVersion"]
    api = API(version)
    image = api.json("GET", "/images/" + IMAGE + "/json")
    write(root / "image.json", image)
    if image["Id"] != IMAGE or image["Os"] != "linux" or image["Architecture"] != "arm64":
        raise Refused("cached image differs from approved local candidate")
    results = []
    for mode in (args.mode,) if args.mode else BASE_MODES:
        print("Running synthetic control: " + mode, flush=True)
        result = run_case(root, api, version, mode, sources, args.fault)
        results.append(result)
        if args.fault or not result["passed"]:
            break
    summary = {
        "schema": "utility-local-container-controls-v1",
        "results": results,
        "all_requested_controls_passed": all(r.get("passed", False) for r in results),
        "private_scoring_qualified": False,
        "platform_scope": "local Linux ARM64 only",
        "private_data_reads": 0,
        "provider_calls": 0,
        "image_pulls": 0,
        "remaining": [
            "network/host-path negative controls",
            "timeout/cancellation/owner-loss tests",
            "lost acknowledgement and relocated offline verification",
            "task/data admission",
        ],
    }
    write(root / "summary.json", summary)
    print(
        json.dumps({k: v for k, v in summary.items() if k != "results"}, sort_keys=True), flush=True
    )
    return 0 if summary["all_requested_controls_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
