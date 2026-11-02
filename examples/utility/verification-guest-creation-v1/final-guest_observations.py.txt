"""Fixed guest OCI request and saved-observation validation; no API operations.

These checks can support a future owner-side launcher. No caller receives image,
data or execution admission from constructing or projecting these documents.
"""

from __future__ import annotations

from .guest_receipts import (
    GuestLaunchIntent,
    GuestContainerStart,
    GuestContainerStop,
    GuestContainerCleanup,
    _timestamp,
)
from .inference_execution import FrozenGuestInferenceJob
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import StoreError

PURPOSE = "utility-frozen-routing-guest-candidate-v1"
BASE_ENV = (
    ("PATH", "/opt/inference/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"),
    ("LANG", "C.UTF-8"),
)


def _same(first, second):
    return canonical_json(first) == canonical_json(second)


def _environment(values):
    if not isinstance(values, list):
        raise StoreError("guest environment must be a complete explicit list")
    result = {}
    for value in values:
        if not isinstance(value, str) or "=" not in value:
            raise StoreError("guest environment entry is invalid")
        name, content = value.split("=", 1)
        if name in result:
            raise StoreError("guest environment has duplicate keys")
        result[name] = content
    return result


def _launch(job, launch):
    if not isinstance(job, FrozenGuestInferenceJob) or not isinstance(launch, GuestLaunchIntent):
        raise StoreError("guest observation requires the versioned job and launch intent")
    if (
        launch.job_digest,
        launch.grant_digest,
        launch.executor_digest,
        launch.nonce,
        launch.image_id,
        launch.timeout_seconds,
        launch.policy.inference_limits_digest,
    ) != (
        job.digest,
        job.grant.digest,
        job.executor_digest,
        job.nonce,
        job.guest.image_id,
        job.grant.inference.timeout_seconds,
        job.guest.limits_digest,
    ):
        raise StoreError("guest launch identity differs from job/grant/profile")


def labels(job, launch):
    _launch(job, launch)
    return {
        "org.autoengineering.purpose": PURPOSE,
        "org.autoengineering.nonce": job.nonce,
        "org.autoengineering.job": job.digest,
        "org.autoengineering.grant": job.grant.digest,
        "org.autoengineering.executor": job.executor_digest,
        "org.autoengineering.runtime": launch.runtime_digest,
        "org.autoengineering.launch": launch.digest,
        "org.autoengineering.environment": job.guest.environment_inputs_digest,
        "org.autoengineering.wheel": job.guest.wheel_digest,
    }


def container_name(job):
    return "ae-frozen-routing-" + job.nonce


def configuration(job, launch):
    """Return a fixed candidate create request, never a caller-supplied command."""
    _launch(job, launch)
    p = launch.policy
    return {
        "Image": launch.image_id,
        "User": p.user,
        "WorkingDir": p.workspace,
        "Entrypoint": list(p.command[:-1]),
        "Cmd": [p.command[-1]],
        "Env": [f"{k}={v}" for k, v in (*BASE_ENV, *p.environment)],
        "NetworkDisabled": True,
        "AttachStdout": True,
        "AttachStderr": True,
        "AttachStdin": p.stdin,
        "OpenStdin": p.stdin,
        "StdinOnce": p.stdin,
        "Tty": False,
        "Labels": labels(job, launch),
        "Volumes": {},
        "Healthcheck": {"Test": ["NONE"]},
        "StopSignal": "SIGTERM",
        "StopTimeout": 5,
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Memory": p.memory_bytes,
            "MemorySwap": p.memory_swap_bytes,
            "NanoCpus": p.nano_cpus,
            "PidsLimit": p.pids,
            "CapDrop": ["ALL"],
            "CapAdd": [],
            "SecurityOpt": ["no-new-privileges"],
            "Privileged": False,
            "CgroupnsMode": "private",
            "IpcMode": "private",
            "PidMode": "",
            "Binds": [],
            "Mounts": [],
            "VolumesFrom": [],
            "Devices": [],
            "DeviceRequests": [],
            "PublishAllPorts": False,
            "PortBindings": {},
            "AutoRemove": False,
            "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
            "Tmpfs": {
                p.workspace: (
                    f"rw,noexec,nosuid,nodev,size={p.workspace_bytes},mode=0700,uid=1000,gid=1000"
                )
            },
            "LogConfig": {"Type": "none", "Config": {}},
        },
    }


def verify_image(value, job):
    """Validate saved image metadata, without looking up or acquiring an image."""
    if not isinstance(value, dict) or (
        value.get("Id"),
        value.get("Os"),
        value.get("Architecture"),
    ) != (job.guest.image_id, "linux", "amd64"):
        raise StoreError("guest image identity/platform differs")
    config = value.get("Config")
    if not isinstance(config, dict):
        raise StoreError("guest image configuration is absent")
    required = {
        "org.autoengineering.purpose": PURPOSE,
        "org.autoengineering.environment": job.guest.environment_inputs_digest,
        "org.autoengineering.wheel": job.guest.wheel_digest,
    }
    image_labels = config.get("Labels")
    if not isinstance(image_labels, dict) or any(
        image_labels.get(k) != v for k, v in required.items()
    ):
        raise StoreError("guest image environment/source provenance differs")
    allowed = dict((*BASE_ENV, *job_policy_environment()))
    if any(allowed.get(k) != v for k, v in _environment(config.get("Env", [])).items()):
        raise StoreError("guest image contains an unapproved environment")
    if config.get("Volumes") not in (None, {}) or config.get("OnBuild") not in (None, []):
        raise StoreError("guest image contains inherited volume/build actions")
    if config.get("Healthcheck") not in (None, {"Test": ["NONE"]}):
        raise StoreError("guest image contains an unapproved health process")


def job_policy_environment():
    from .guest_receipts import ENVIRONMENT

    return ENVIRONMENT


def verify_owned(value, job, launch):
    """Check actual inspect structure against the fixed request and owner nonce."""
    expected = configuration(job, launch)
    if (
        not isinstance(value, dict)
        or value.get("Image") != job.guest.image_id
        or value.get("Name") != "/" + container_name(job)
    ):
        raise StoreError("guest container identity differs")
    from .contracts import sha256

    sha256(value.get("Id", ""))
    config, host = value.get("Config"), value.get("HostConfig")
    if not isinstance(config, dict) or not isinstance(host, dict):
        raise StoreError("guest container configuration is absent")
    for key in (
        "Image",
        "User",
        "WorkingDir",
        "Entrypoint",
        "Cmd",
        "NetworkDisabled",
        "AttachStdout",
        "AttachStderr",
        "AttachStdin",
        "OpenStdin",
        "StdinOnce",
        "Tty",
        "StopSignal",
        "StopTimeout",
        "Healthcheck",
    ):
        if not _same(config.get(key), expected[key]):
            raise StoreError("guest container command/environment differs")
    if _environment(config.get("Env")) != _environment(expected["Env"]):
        raise StoreError("guest container environment differs")
    owner_labels = config.get("Labels")
    if not isinstance(owner_labels, dict) or any(
        owner_labels.get(k) != v for k, v in expected["Labels"].items()
    ):
        raise StoreError("guest container owner binding differs")
    if config.get("Volumes") not in (None, {}):
        raise StoreError("guest container has inherited volumes")
    for key, wanted in expected["HostConfig"].items():
        observed = host.get(key)
        if key == "SecurityOpt" and observed == ["no-new-privileges:true"]:
            continue
        if key in {"Binds", "Mounts", "VolumesFrom", "Devices", "DeviceRequests", "CapAdd"}:
            if observed is None and wanted == []:
                continue
        if key == "PortBindings" and observed is None and wanted == {}:
            continue
        if not _same(observed, wanted):
            raise StoreError("guest container isolation/resource projection differs")
    for key in (
        "DeviceCgroupRules",
        "GroupAdd",
        "Links",
        "ExtraHosts",
        "Dns",
        "DnsOptions",
        "DnsSearch",
        "Ulimits",
    ):
        if host.get(key) not in (None, []):
            raise StoreError("guest container has unapproved host/network access")
    if (
        host.get("UsernsMode", "")
        or host.get("UTSMode", "")
        or host.get("Runtime", "runc") != "runc"
    ):
        raise StoreError("guest container namespace/runtime differs")
    for key in ("Sysctls", "StorageOpt"):
        if host.get(key) not in (None, {}):
            raise StoreError("guest container has unapproved kernel/storage settings")
    for key in ("CgroupParent", "ContainerIDFile", "Isolation"):
        if host.get(key) not in (None, ""):
            raise StoreError("guest container has unapproved host settings")
    mounts = value.get("Mounts")
    if not isinstance(mounts, list) or len(mounts) > 1:
        raise StoreError("guest container workspace mount is unverified")
    # HostConfig.Tmpfs is authoritative for the map-based request above. Moby
    # keeps that map separate from its ordinary mount-point collection. Legacy
    # authored projections may additionally describe the same single tmpfs.
    if mounts:
        mount = mounts[0]
        if not isinstance(mount, dict) or not _same(
            (mount.get("Type"), mount.get("Destination"), mount.get("RW")),
            ("tmpfs", "/work", True),
        ):
            raise StoreError("guest container has an unapproved mount")
        if mount.get("Source") not in (None, ""):
            raise StoreError("guest workspace exposes a host source")
    if type(value.get("RestartCount")) is not int or value["RestartCount"] != 0:
        raise StoreError("guest execution restart history differs")
    state = value.get("State")
    if (
        not isinstance(state, dict)
        or state.get("Paused") is not False
        or state.get("Restarting") is not False
    ):
        raise StoreError("guest container is paused/restarting or unobserved")
    return state


def verify_created(value, job, launch):
    """Require original, unstarted creation before an owner may intend a start."""
    before = verify_owned(value, job, launch)
    if (
        before.get("Status") != "created"
        or before.get("Running") is not False
        or type(before.get("Pid")) is not int
        or before["Pid"] != 0
        or before.get("Dead") is not False
        or before.get("OOMKilled") is not False
        or type(before.get("ExitCode")) is not int
        or before["ExitCode"] != 0
    ):
        raise StoreError("guest creation is not an original unstarted observation")
    if any(
        before.get(key) not in (None, "", "0001-01-01T00:00:00Z")
        for key in ("StartedAt", "FinishedAt")
    ):
        raise StoreError("guest creation already has a start")
    return before


def verify_started(value, job, launch):
    """Accept an original running snapshot or an already terminal fast worker."""
    first = verify_owned(value, job, launch)
    if (
        first.get("Status") not in ("running", "exited", "dead")
        or type(first.get("Running")) is not bool
        or (first["Status"] == "running") != first["Running"]
        or type(first.get("Dead")) is not bool
        or (first["Status"] == "dead") != first["Dead"]
        or type(first.get("Pid")) is not int
        or (first["Running"] and first["Pid"] <= 0)
        or (not first["Running"] and first["Pid"] != 0)
    ):
        raise StoreError("guest original start is unverified")
    if first["Status"] == "running" and (
        first.get("OOMKilled") is not False
        or type(first.get("ExitCode")) is not int
        or first["ExitCode"] != 0
        or first.get("FinishedAt") not in (None, "", "0001-01-01T00:00:00Z")
    ):
        raise StoreError("guest running snapshot contains terminal state")
    if not isinstance(first.get("StartedAt"), str):
        raise StoreError("guest lifecycle timestamp is missing or malformed")
    _timestamp(first["StartedAt"])
    return first


def project_lifecycle(
    job, launch, *, image, created, started, stopped, elapsed_seconds=None, reason=None
):
    """Validate original saved observations before producing public projections.

    Digests describe canonical saved JSON, not an independent attestation or new
    daemon observation. The caller remains responsible for authentic collection.
    """
    verify_image(image, job)
    verify_created(created, job, launch)
    first = verify_started(started, job, launch)
    final = verify_owned(stopped, job, launch)
    if started["Id"] != created["Id"] or stopped["Id"] != created["Id"]:
        raise StoreError("guest observations belong to different containers")
    if (
        final.get("Status") not in ("exited", "dead")
        or final.get("Running") is not False
        or type(final.get("Pid")) is not int
        or final["Pid"] != 0
    ):
        raise StoreError("guest original stop is unverified")
    if (
        type(final.get("ExitCode")) is not int
        or type(final.get("OOMKilled")) is not bool
        or type(final.get("Dead")) is not bool
    ):
        raise StoreError("guest terminal state types differ")
    if (final["Status"] == "dead") != final["Dead"]:
        raise StoreError("guest terminal dead state is inconsistent")
    for state, keys in ((first, ("StartedAt",)), (final, ("StartedAt", "FinishedAt"))):
        for key in keys:
            if not isinstance(state.get(key), str):
                raise StoreError("guest lifecycle timestamp is missing or malformed")
            _timestamp(state[key])
    if first["Status"] != "running" and not _same(first, final):
        raise StoreError("guest terminal start observation changed before final capture")
    if first.get("StartedAt") != final.get("StartedAt"):
        raise StoreError("guest lifecycle changed original start")
    start = GuestContainerStart(
        "utility-guest-container-start-v1",
        launch.digest,
        created["Id"],
        job.nonce,
        job.guest.image_id,
        launch.policy.digest,
        first["StartedAt"],
        digest(created),
        digest(started),
        1,
    )
    stop = GuestContainerStop(
        "utility-guest-container-stop-v1",
        start.digest,
        created["Id"],
        job.nonce,
        first["StartedAt"],
        final["FinishedAt"],
        False,
        0,
        final["ExitCode"],
        final["OOMKilled"],
        final["Dead"],
        reason,
        elapsed_seconds,
        digest(stopped),
    )
    return start, stop


def project_observations(
    job, launch, *, image, created, started, stopped, cleanup, elapsed_seconds=None, reason=None
):
    """Project a complete original lifecycle, including matching removal evidence."""
    start, stop = project_lifecycle(
        job,
        launch,
        image=image,
        created=created,
        started=started,
        stopped=stopped,
        elapsed_seconds=elapsed_seconds,
        reason=reason,
    )
    if (
        not isinstance(cleanup, dict)
        or set(cleanup) != {"container_id", "nonce", "removed", "observed_absent"}
        or (cleanup["container_id"], cleanup["nonce"]) != (created["Id"], job.nonce)
        or cleanup["removed"] is not True
        or cleanup["observed_absent"] is not True
    ):
        raise StoreError("guest original cleanup is unverified")
    removed = GuestContainerCleanup(
        "utility-guest-container-cleanup-v1",
        stop.digest,
        created["Id"],
        job.nonce,
        True,
        True,
        digest(cleanup),
    )
    return start, stop, removed
