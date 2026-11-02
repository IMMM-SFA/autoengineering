"""Reconcile one source-bound container without launching another execution.

The caller supplies trusted source and input bytes and must stop the outer owner
before requesting a stop here. An absent container proves no output or cost.
Daemon errors, changed ownership and incomplete launch records remain unresolved.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.campaign.store import checked_directory

from .containers import DockerBoundary, discover_runtime
from .qualification import verify_qualification


def _raw(root: Path, name: str, ceiling: int = 65536) -> bytes:
    path = confined_file(root, name)
    if path.stat().st_size > ceiling:
        raise ValueError("container recovery artifact exceeds its byte ceiling")
    value = path.read_bytes()
    if len(value) > ceiling:
        raise ValueError("container recovery artifact exceeds its byte ceiling")
    return value


def _record(root: Path, name: str):
    return unique_json(_raw(root, name).decode())


@dataclass(frozen=True)
class ContainerRecovery:
    container_id: str
    nonce: str
    intent_digest: str
    stopped: bool
    removed: bool
    stop_requested: bool
    result_digest: str | None
    result_status: str | None
    stdout: bytes | None


def reconcile_container(
    root: Path,
    *,
    qualification_root: Path,
    qualification_digest: str,
    sources: Mapping[str, bytes],
    payload: bytes,
    entrypoint: str = "driver.py",
    wall_seconds: float = 5,
    stop: bool = False,
) -> ContainerRecovery:
    """Inspect an exact owned container, optionally stopping it after owner exit.

    Invalid or unavailable evidence raises rather than claiming a stopped state.
    This function never starts, creates, restarts or replaces a container. It
    leaves results untouched and does not infer budget settlement from absence.
    """
    root = checked_directory(root)
    if type(stop) is not bool or type(payload) is not bytes or len(payload) > 65536:
        raise ValueError("invalid container recovery request")
    if (
        not sources
        or len(sources) > 4
        or entrypoint not in sources
        or any(
            name not in ("adapter.py", "driver.py", "probe.py") or type(raw) is not bytes
            for name, raw in sources.items()
        )
        or sum(map(len, sources.values())) > 65536
        or type(wall_seconds) not in (int, float)
        or not 0 < wall_seconds <= 60
    ):
        raise ValueError("invalid container recovery source or deadline")
    qualification = verify_qualification(qualification_root, expected_digest=qualification_digest)
    runtime, limits = qualification.runtime, qualification.limits
    if runtime.client_sha256 is None or runtime.server_fingerprint is None:
        raise ValueError("container recovery requires a fingerprinted runtime")
    declaration = _record(root, "intent.json")
    nonce = declaration.get("nonce")
    if type(nonce) is not str or not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ValueError("container recovery nonce is invalid")
    expected = {
        "version": DockerBoundary.version,
        "nonce": nonce,
        "image_id": runtime.image_id,
        "repository_digest": runtime.repository_digest,
        "sources": {name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()},
        "entrypoint": entrypoint,
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "cpu_seconds": limits.cpu_seconds,
        "memory_bytes": limits.memory_bytes,
        "output_bytes": limits.output_bytes,
        "wall_seconds": wall_seconds,
    }
    if declaration != expected or _raw(root, "stdin.bin") != payload:
        raise ValueError("container recovery intent differs from trusted execution")
    for name, raw in sources.items():
        if _raw(root, f"export/{name}") != raw:
            raise ValueError("container recovery source differs from trusted execution")
    if set(path.name for path in (root / "export").iterdir()) != set(sources):
        raise ValueError("container recovery export has undeclared sources")
    checked_directory(root / "docker-config")
    cid = _raw(root, "container-id", 64).decode()
    if not re.fullmatch(r"[0-9a-f]{64}", cid):
        raise ValueError("container recovery requires an immutable container ID")
    intent = digest(declaration)
    boundary = DockerBoundary(runtime)
    policy_raw = _raw(root, "effective-policy.json")
    policy = unique_json(policy_raw.decode())
    archived = {
        "Id": policy["id"],
        "Image": policy["image"],
        "HostConfig": policy["host"],
        "Config": policy["config"],
        "Mounts": policy["mounts"],
    }

    def check_policy(value):
        boundary._verify_policy(
            value, root=root, nonce=nonce, intent=intent, export=root / "export", limits=limits
        )
        if value["HostConfig"].get("RestartPolicy", {}).get("Name", "no") not in ("", "no"):
            raise ValueError("container recovery cannot accept automatic restart")

    check_policy(archived)
    result_digest = result_status = stdout = None
    if (root / "result.json").exists():
        result = _record(root, "result.json")
        elapsed = result.get("elapsed_seconds")
        if (
            result.get("container_id") != cid
            or result.get("nonce") != nonce
            or result.get("intent_digest") != intent
            or result.get("image_id") != runtime.image_id
            or type(result.get("stopped")) is not bool
            or type(result.get("exitcode")) is not int
            or type(result.get("oom_killed")) is not bool
            or type(elapsed) not in (int, float)
            or not math.isfinite(elapsed)
            or elapsed < 0
            or result.get("status")
            not in (
                "success",
                "model_failure",
                "timeout",
                "cancelled",
                "output_limit",
                "reconciliation_required",
            )
            or (result["stopped"] is False and result["status"] != "reconciliation_required")
            or (result["status"] == "success" and (result["exitcode"] or result["oom_killed"]))
            or result.get("effective_policy_sha256") != hashlib.sha256(policy_raw).hexdigest()
        ):
            raise ValueError("container recovery result is incomplete or inconsistent")
        stdout = _raw(root, "stdout.bin", limits.output_bytes)
        stderr = _raw(root, "stderr.bin", limits.output_bytes)
        if len(stdout) + len(stderr) > limits.output_bytes:
            raise ValueError("container recovery output exceeds its combined byte ceiling")
        if hashlib.sha256(stdout).hexdigest() != result.get("stdout_sha256") or hashlib.sha256(
            stderr
        ).hexdigest() != result.get("stderr_sha256"):
            raise ValueError("container recovery raw output differs from result")
        if result["stopped"] and result["status"] != "reconciliation_required":
            result_digest, result_status = digest(result), result["status"]
        else:
            # A saved uncertain outcome is not a completed numerical result.
            # It must not prevent an exact owned stop or be rewritten afterward.
            stdout = None

    # Refresh before *any* daemon command. A saved receipt cannot authorize a
    # signal to a changed client, daemon, image or ownership identity.
    if discover_runtime(runtime.image_id, docker=runtime.docker) != runtime:
        raise ValueError("container recovery runtime differs from qualification")

    def inspect():
        response = boundary._metadata(root, "inspect", "--format", "{{json .}}", cid, check=False)
        if response.returncode:
            # Match the complete C-locale Docker diagnostic for this exact ID.
            # Socket/permission/daemon errors must never count as absence.
            absent = {
                f"Error: No such object: {cid}",
                f"error: no such object: {cid}",
                f"Error response from daemon: No such container: {cid}",
            }
            if (
                response.returncode == 1
                and not response.stdout.strip()
                and (response.stderr.decode().strip() in absent)
            ):
                return None
            raise ValueError("container recovery inspection is unresolved")
        value = unique_json(response.stdout.decode())
        check_policy(value)
        state = value["State"]
        if type(state.get("Running")) is not bool or state.get("Status") not in (
            "created",
            "running",
            "paused",
            "restarting",
            "removing",
            "exited",
            "dead",
        ):
            raise ValueError("container recovery state is unresolved")
        return value

    current = inspect()
    if (
        result_digest
        and current is not None
        and (
            current["State"]["Running"] is not False
            or current["State"]["Status"] not in ("exited", "dead")
        )
    ):
        raise ValueError("saved stopped result contradicts current container state")
    requested = False
    if (
        stop
        and current is not None
        and current["State"]["Status"] in ("created", "running", "paused", "restarting")
    ):
        # Recheck exact ownership immediately before mutation. A created
        # container is removed so a late owner cannot start it after this call.
        current = inspect()
        if current is not None and current["State"]["Status"] in (
            "created",
            "running",
            "paused",
            "restarting",
        ):
            verb = "rm" if current["State"]["Status"] == "created" else "kill"
            boundary._metadata(root, verb, cid, check=False)
            requested = True
            current = inspect()
    stopped = current is None or (
        current["State"]["Running"] is False and current["State"]["Status"] in ("exited", "dead")
    )
    if result_digest and not stopped:
        raise ValueError("saved stopped result contradicts current container state")
    return ContainerRecovery(
        cid,
        nonce,
        intent,
        stopped,
        current is None,
        requested,
        result_digest,
        result_status,
        stdout,
    )
