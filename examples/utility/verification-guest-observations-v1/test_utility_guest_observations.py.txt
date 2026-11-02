"""Authored OCI captures test owner validation, not actual runtime enforcement."""

from copy import deepcopy
from dataclasses import replace
import json
import socket
import subprocess
import time

import pytest

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import digest
from autoengineering.utility import guest_observations as module
from autoengineering.utility import guest_receipts as receipts
import test_utility_guest_receipts as receipt_fixture

metadata = receipt_fixture.metadata
H = "1" * 64
ZERO = "0001-01-01T00:00:00Z"


def captures(job, launch):
    request = module.configuration(job, launch)
    config = {k: deepcopy(v) for k, v in request.items() if k != "HostConfig"}
    image = {
        "Id": job.guest.image_id,
        "Os": "linux",
        "Architecture": "amd64",
        "Config": {"Labels": deepcopy(config["Labels"]), "Env": ["LANG=C.UTF-8"]},
    }
    created = {
        "Id": H,
        "Image": job.guest.image_id,
        "Name": "/" + module.container_name(job),
        "Config": config,
        "HostConfig": deepcopy(request["HostConfig"]),
        "Mounts": [{"Type": "tmpfs", "Destination": "/work", "Source": "", "RW": True}],
        "RestartCount": 0,
        "State": {
            "Status": "created",
            "Running": False,
            "Pid": 0,
            "Paused": False,
            "Restarting": False,
            "Dead": False,
            "OOMKilled": False,
            "ExitCode": 0,
            "StartedAt": ZERO,
            "FinishedAt": ZERO,
        },
    }
    started = deepcopy(created)
    started["State"].update(
        Status="running", Running=True, Pid=42, StartedAt="2026-01-01T00:00:00Z"
    )
    stopped = deepcopy(started)
    stopped["State"].update(
        Status="exited", Running=False, Pid=0, FinishedAt="2026-01-01T00:00:02Z"
    )
    cleanup = {"container_id": H, "nonce": job.nonce, "removed": True, "observed_absent": True}
    return dict(image=image, created=created, started=started, stopped=stopped, cleanup=cleanup)


def setup(tmp_path, metadata, **kwargs):
    root, job, archive, ref, args, save = receipt_fixture.prepared(tmp_path, metadata, **kwargs)
    launch = receipts.GuestLaunchIntent.from_json(read_bytes(root, archive.launch).decode())
    return root, job, launch, archive, args, save


def test_fixed_request_has_no_host_input_or_execution_escape(tmp_path, metadata):
    _, job, launch, _, _, _ = setup(tmp_path, metadata)
    request = module.configuration(job, launch)
    assert request["User"] == "1000:1000"
    assert request["Entrypoint"] == [
        "/opt/inference/bin/python",
        "-I",
        "-m",
        "autoengineering.utility.inference_worker",
    ]
    assert request["Cmd"] == ["/work/job.json"]
    host = request["HostConfig"]
    assert host["NetworkMode"] == "none" and host["ReadonlyRootfs"] is True
    assert host["Memory"] == host["MemorySwap"] == 1073741824
    assert host["NanoCpus"] == 1000000000 and host["PidsLimit"] == 16
    assert host["CapDrop"] == ["ALL"] and host["Privileged"] is False
    assert host["Binds"] == host["Devices"] == host["DeviceRequests"] == []
    assert "noexec,nosuid,nodev" in host["Tmpfs"]["/work"]
    assert host["LogConfig"] == {"Type": "none", "Config": {}}


@pytest.mark.parametrize("terminal_start", [False, True])
def test_original_capture_chain_reaches_cold_archive_reader(
    tmp_path, metadata, monkeypatch, terminal_start
):
    root, job, launch, archive, args, save = setup(tmp_path, metadata)
    observations = captures(job, launch)
    if terminal_start:
        observations["started"] = deepcopy(observations["stopped"])

    def forbidden(*args, **kwargs):
        pytest.fail("projection must not execute, connect or sample a new clock")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    start, stop, cleanup = module.project_observations(job, launch, **observations)
    assert start.original_creation_digest == digest(observations["created"])
    assert start.original_start_digest == digest(observations["started"])
    assert stop.original_stop_digest == digest(observations["stopped"])
    assert stop.start_digest == start.digest and cleanup.stop_digest == stop.digest
    assert stop.elapsed_seconds is None
    archive = replace(
        archive,
        start=save(start, "observed-start.json"),
        stop=save(stop, "observed-stop.json"),
        cleanup=save(cleanup, "observed-cleanup.json"),
    )
    result = receipts.verify_guest_archive(
        root, save(archive, "observed-archive.json"), job.grant, **args
    )
    assert result.status == "success" and result.boundary == "unqualified-candidate"
    assert result.lifecycle_seconds is None
    (root / "authored-raw-observations.json").write_text(json.dumps(observations, indent=2))
    (root / "observation-projection-result.json").write_text(result.to_json())


@pytest.mark.parametrize(
    "path,value",
    [
        ("image.Id", "sha256:" + "2" * 64),
        ("image.Os", "darwin"),
        ("image.Architecture", "arm64"),
        ("image.Config.Labels", []),
        ("image.Config.Env", ["TOKEN=secret-canary"]),
        ("image.Config.Env", ["LANG=C.UTF-8", "LANG=C.UTF-8"]),
        ("image.Config.Volumes", {"/private": {}}),
        ("image.Config.OnBuild", ["RUN other"]),
        ("image.Config.Healthcheck", {"Test": ["CMD", "other"]}),
        ("created.Name", "/foreign"),
        ("started.Id", "2" * 64),
        ("stopped.Image", "sha256:" + "2" * 64),
        ("started.Config.Labels", None),
        ("started.Config.Labels.org.autoengineering.nonce", "b" * 32),
        ("started.Config.Entrypoint", ["/bin/sh"]),
        ("started.Config.Cmd", ["/other.json"]),
        ("started.Config.Env", ["PATH=/host"]),
        ("started.Config.Volumes", {"/host": {}}),
        ("started.Config.NetworkDisabled", False),
        ("started.Config.Tty", True),
        ("started.HostConfig.NetworkMode", "host"),
        ("started.HostConfig.ReadonlyRootfs", False),
        ("started.HostConfig.Memory", True),
        ("started.HostConfig.NanoCpus", 1),
        ("started.HostConfig.PidsLimit", 0),
        ("started.HostConfig.CapAdd", ["SYS_ADMIN"]),
        ("started.HostConfig.SecurityOpt", ["seccomp=unconfined"]),
        ("started.HostConfig.Privileged", True),
        ("started.HostConfig.Binds", ["/:/host"]),
        ("started.HostConfig.Devices", [{"PathOnHost": "/dev/mem"}]),
        ("started.HostConfig.PidMode", "host"),
        ("started.HostConfig.IpcMode", "host"),
        ("started.HostConfig.UsernsMode", "host"),
        ("started.HostConfig.Runtime", "other"),
        ("started.HostConfig.Sysctls", {"kernel.example": "1"}),
        ("started.HostConfig.StorageOpt", {"size": "2G"}),
        ("started.Mounts", [{"Type": "bind", "Destination": "/work", "RW": True}]),
        ("started.Mounts", [{"Type": "tmpfs", "Destination": "/work", "RW": 1}]),
        ("started.RestartCount", True),
        ("started.RestartCount", 1),
        ("created.State.Dead", True),
        ("created.State.ExitCode", True),
        ("created.State.StartedAt", "2026-01-01T00:00:00Z"),
        ("created.State.FinishedAt", "2026-01-01T00:00:00Z"),
        ("started.State.Status", "exited"),
        ("started.State.Running", False),
        ("started.State.Pid", 0),
        ("started.State.Dead", True),
        ("stopped.State.Status", "running"),
        ("stopped.State.Running", True),
        ("stopped.State.Pid", 1),
        ("stopped.State.ExitCode", False),
        ("stopped.State.OOMKilled", 1),
        ("stopped.State.Dead", True),
        ("stopped.State.StartedAt", "2026-01-01T00:00:01Z"),
        ("stopped.State.FinishedAt", "2025-01-01T00:00:00Z"),
        ("started.State.StartedAt", None),
        ("stopped.State.FinishedAt", None),
        ("started.State.OOMKilled", True),
        ("started.State.ExitCode", 1),
        ("started.State.FinishedAt", "2026-01-01T00:00:02Z"),
        ("cleanup.nonce", "b" * 32),
        ("cleanup.container_id", "2" * 64),
        ("cleanup.removed", False),
        ("cleanup.observed_absent", 1),
    ],
)
def test_changed_or_contradictory_original_capture_refuses(tmp_path, metadata, path, value):
    _, job, launch, _, _, _ = setup(tmp_path, metadata)
    observations = captures(job, launch)
    target = observations
    keys = path.split(".")
    # Label keys themselves contain dots.
    if "Labels" in keys:
        index = keys.index("Labels")
        keys = keys[: index + 1] + ([".".join(keys[index + 1 :])] if keys[index + 1 :] else [])
    for key in keys[:-1]:
        target = target[key]
    target[keys[-1]] = value
    with pytest.raises(ValueError):
        module.project_observations(job, launch, **observations)


@pytest.mark.parametrize(
    "reason,oom,dead,expected",
    [
        ("timeout", False, False, "timeout"),
        ("cancelled", False, False, "infrastructure_failure"),
        (None, True, False, "infrastructure_failure"),
        (None, False, True, "infrastructure_failure"),
    ],
)
def test_original_stop_failure_never_yields_a_vector(
    tmp_path, metadata, reason, oom, dead, expected
):
    root, job, launch, archive, args, save = setup(
        tmp_path, metadata, reason=reason, oom=oom, dead=dead, exit_code=137
    )
    observations = captures(job, launch)
    observations["stopped"]["State"].update(
        ExitCode=137, OOMKilled=oom, Dead=dead, Status="dead" if dead else "exited"
    )
    start, stop, cleanup = module.project_observations(job, launch, **observations, reason=reason)
    archive = replace(
        archive,
        start=save(start, "failed-start.json"),
        stop=save(stop, "failed-stop.json"),
        cleanup=save(cleanup, "failed-cleanup.json"),
    )
    result = receipts.verify_guest_archive(
        root, save(archive, "failed-observed-archive.json"), job.grant, **args
    )
    assert result.status == expected and result.result is None and archive.predictions is None
