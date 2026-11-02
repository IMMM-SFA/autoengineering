"""Local container boundary prototype with pinned images and owned watchdogs.

No image is pulled automatically. Only a local image with an official Python
repository digest is eligible for qualification. This module does not register
or admit generated scientific implementations.
"""

from __future__ import annotations

from collections.abc import Mapping, Callable
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import sys
import time
import tempfile
import uuid

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from .sandbox import BoundaryLimits


@dataclass(frozen=True)
class ContainerRuntime:
    image_id: str
    repository_digest: str
    architecture: str
    endpoint: str
    docker: str
    client_sha256: str | None = None
    server_fingerprint: str | None = None

    def __post_init__(self):
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.image_id):
            raise ValueError("container runtime requires an immutable image ID")
        if not re.fullmatch(
            r"(?:docker.io/library/)?python@sha256:[0-9a-f]{64}", self.repository_digest
        ):
            raise ValueError("container runtime must come from the official Python repository")
        if self.architecture not in ("arm64", "amd64") or not self.endpoint.startswith("unix:///"):
            raise ValueError(
                "only local Unix Docker endpoints and qualified CPU architectures are allowed"
            )
        if (self.client_sha256 is None) != (self.server_fingerprint is None):
            raise ValueError("container runtime fingerprint is incomplete")
        for value in (self.client_sha256, self.server_fingerprint):
            if value is not None and not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError("invalid container runtime fingerprint")


def discover_runtime(image: str, *, docker: str | None = None) -> ContainerRuntime:
    # Docker may be a multicall executable selected by argv[0]. Keep the
    # installed command name while checking its resolved target exists.
    executable = Path(docker or shutil.which("docker") or "/missing/docker").absolute()
    executable.resolve(strict=True)
    # Context discovery reads only its Unix endpoint, never registry credentials.
    context = subprocess.run(
        [str(executable), "context", "inspect", "--format", "{{.Endpoints.docker.Host}}"],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    ).stdout.strip()
    if not context.startswith("unix:///"):
        raise ValueError("remote Docker compute is not authorized by this boundary")
    with tempfile.TemporaryDirectory(prefix="ae-docker-config-") as temporary:
        command = [
            str(executable),
            "--host",
            context,
            "--config",
            temporary,
            "image",
            "inspect",
            "--format",
            '{"id":{{json .Id}},"digests":{{json .RepoDigests}},"os":{{json .Os}},"architecture":{{json .Architecture}}}',
            image,
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        if result.returncode:
            raise ValueError("approved local Python image is unavailable; no image was pulled")
        value = unique_json(result.stdout)
        if value["os"] != "linux":
            raise ValueError("generated container execution requires a Linux image")
        details = subprocess.run(
            [
                str(executable),
                "--host",
                context,
                "--config",
                temporary,
                "info",
                "--format",
                '{"version":{{json .ServerVersion}},"kernel":{{json .KernelVersion}},"os":{{json .OSType}},"architecture":{{json .Architecture}},"security":{{json .SecurityOptions}}}',
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        server_fingerprint = digest(unique_json(details.stdout))
    if value["os"] != "linux":
        raise ValueError("generated container execution requires a Linux image")
    sources = [
        item
        for item in value["digests"] or ()
        if re.fullmatch(r"(?:docker.io/library/)?python@sha256:[0-9a-f]{64}", item)
    ]
    if len(sources) != 1:
        raise ValueError("image has no unique official Python repository digest")
    return ContainerRuntime(
        value["id"],
        sources[0],
        value["architecture"],
        context,
        str(executable),
        hashlib.sha256(executable.read_bytes()).hexdigest(),
        server_fingerprint,
    )


@dataclass(frozen=True)
class ContainerResult:
    status: str
    container_id: str
    stdout: bytes
    stderr: bytes
    stopped: bool
    oom_killed: bool
    elapsed_seconds: float
    receipt_digest: str


class DockerBoundary:
    version = "local-docker-generated-1.0"

    def __init__(self, runtime: ContainerRuntime):
        self.runtime = runtime

    def _command(self, root: Path, *args):
        return [
            self.runtime.docker,
            "--host",
            self.runtime.endpoint,
            "--config",
            str(root / "docker-config"),
            *args,
        ]

    def run_qualified(self, sources, *, qualification_root, qualification_digest, **kwargs):
        """Execute only after verifying a caller-pinned qualification and current runtime.

        This executes code inside the qualified boundary. It grants no scientific
        admission. The trusted interface runner supplies the driver and inputs.
        """
        from .qualification import verify_qualification

        qualification = verify_qualification(
            qualification_root, expected_digest=qualification_digest
        )
        if qualification.runtime != self.runtime or self.runtime.client_sha256 is None:
            raise ValueError("execution requires a fingerprinted, qualified runtime")
        current = discover_runtime(self.runtime.image_id, docker=self.runtime.docker)
        if current != self.runtime:
            raise ValueError("container client, server or image changed since qualification")
        if kwargs.get("limits") != qualification.limits:
            raise ValueError("execution limits differ from the tested qualification")
        return self.run_probe(sources, **kwargs)

    def _metadata(self, root, *args, check=True):
        result = subprocess.run(
            self._command(root, *args),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=5,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        if (
            len(result.stdout) > 65536
            or len(result.stderr) > 65536
            or (check and result.returncode)
        ):
            raise ValueError("container metadata command failed")
        return result

    def _inspect(self, root, cid):
        result = self._metadata(root, "inspect", "--format", "{{json .}}", cid)
        return unique_json(result.stdout.decode())

    def _verify_policy(self, value, *, root, nonce, intent, export, limits):
        host = value["HostConfig"]
        config = value["Config"]
        if (
            value["Id"] != root.joinpath("container-id").read_text()
            or value["Image"] != self.runtime.image_id
        ):
            raise ValueError("container identity differs from reserved runtime")
        if (
            config["Labels"].get("autoengineering.nonce") != nonce
            or config["Labels"].get("autoengineering.intent") != intent
        ):
            raise ValueError("container ownership labels differ from intent")
        expected = {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "Memory": limits.memory_bytes,
            "MemorySwap": limits.memory_bytes,
            "NanoCpus": 1000000000,
            "PidsLimit": 8,
        }
        if any(host.get(key) != expected_value for key, expected_value in expected.items()):
            raise ValueError("container resource or isolation policy differs from request")
        if (
            host.get("CapAdd")
            or set(host.get("CapDrop") or ()) != {"ALL"}
            or "no-new-privileges" not in (host.get("SecurityOpt") or ())
        ):
            raise ValueError("container capabilities or privilege policy changed")
        if (
            config["User"] != "65534:65534"
            or config["WorkingDir"] != "/work"
            or config["Entrypoint"] != ["/usr/local/bin/python3.12"]
        ):
            raise ValueError("container execution identity or entrypoint changed")
        declaration = unique_json(confined_file(root, "intent.json").read_text())
        if digest(declaration) != intent or config["Cmd"] != [
            "-I",
            "-S",
            "-B",
            f"/work/{declaration['entrypoint']}",
        ]:
            raise ValueError("container command differs from the frozen intent")
        expected_limits = {
            "nofile": (32, 32),
            "cpu": (limits.cpu_seconds, limits.cpu_seconds),
            "fsize": (limits.output_bytes, limits.output_bytes),
        }
        if {
            value["Name"]: (value["Soft"], value["Hard"]) for value in host.get("Ulimits") or ()
        } != expected_limits:
            raise ValueError("container process limits differ from policy")
        if host.get("Tmpfs") != {"/dev/shm": "ro,nosuid,nodev,noexec,size=65536,mode=000"}:
            raise ValueError("container has an undeclared shared-memory workspace")
        if (
            host["LogConfig"]["Type"] != "none"
            or host.get("Binds")
            or host.get("PidMode")
            or host.get("IpcMode") == "host"
        ):
            raise ValueError("container has an undeclared host/control-plane channel")
        mounts = value["Mounts"]
        if (
            len(mounts) != 1
            or mounts[0]["Type"] != "bind"
            or mounts[0]["Destination"] != "/work"
            or mounts[0]["RW"]
            or Path(mounts[0]["Source"]).resolve() != export.resolve()
        ):
            raise ValueError("container mounts differ from the declared source workspace")

    def run_probe(
        self,
        sources: Mapping[str, bytes],
        *,
        entrypoint: str,
        payload: bytes,
        root: Path,
        limits: BoundaryLimits = BoundaryLimits(),
        wall_seconds: float = 5,
        on_launch: Callable[[dict], None] = lambda _: None,
        cancelled: Callable[[], bool] = lambda: False,
    ):
        """Run trusted qualification probes. No scientific admission is implied."""
        if (
            type(wall_seconds) not in (int, float)
            or not 0 < wall_seconds <= 60
            or type(payload) is not bytes
            or len(payload) > 65536
        ):
            raise ValueError("container input or deadline exceeds policy")
        if (
            not sources
            or len(sources) > 4
            or entrypoint not in sources
            or sum(len(b) for b in sources.values()) > 65536
        ):
            raise ValueError("container source envelope exceeds policy")
        if any(
            name not in ("adapter.py", "driver.py", "probe.py") or type(raw) is not bytes
            for name, raw in sources.items()
        ):
            raise ValueError("container source contains an undeclared file")
        root = Path(root).absolute()
        checked_directory(root.parent)
        root.mkdir(mode=0o700)
        (root / "docker-config").mkdir(mode=0o700)
        export = root / "export"
        export.mkdir(mode=0o700)
        manifest = {name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()}
        for name, raw in sources.items():
            durable_write(export / name, raw)
            (export / name).chmod(0o444)
        export.chmod(0o555)  # only this derived export is mounted, under a private parent
        nonce = uuid.uuid4().hex
        spec = {
            "version": self.version,
            "nonce": nonce,
            "image_id": self.runtime.image_id,
            "repository_digest": self.runtime.repository_digest,
            "sources": manifest,
            "entrypoint": entrypoint,
            "input_sha256": hashlib.sha256(payload).hexdigest(),
            "cpu_seconds": limits.cpu_seconds,
            "memory_bytes": limits.memory_bytes,
            "output_bytes": limits.output_bytes,
            "wall_seconds": wall_seconds,
        }
        intent = digest(spec)
        durable_write(root / "intent.json", canonical_json(spec).encode())
        durable_write(root / "stdin.bin", payload)
        result = self._metadata(
            root,
            "create",
            "--pull",
            "never",
            "--name",
            f"ae-generated-{nonce}",
            "--label",
            f"autoengineering.nonce={nonce}",
            "--label",
            f"autoengineering.intent={intent}",
            "--network",
            "none",
            "--read-only",
            "--tmpfs",
            "/dev/shm:ro,nosuid,nodev,noexec,size=65536,mode=000",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            str(limits.memory_bytes),
            "--memory-swap",
            str(limits.memory_bytes),
            "--cpus",
            "1",
            "--pids-limit",
            "8",
            "--ulimit",
            "nofile=32:32",
            "--ulimit",
            f"cpu={limits.cpu_seconds}:{limits.cpu_seconds}",
            "--ulimit",
            f"fsize={limits.output_bytes}:{limits.output_bytes}",
            "--log-driver",
            "none",
            "--user",
            "65534:65534",
            "--workdir",
            "/work",
            "--env",
            "PATH=/usr/local/bin:/usr/bin:/bin",
            "--env",
            "HOME=/nonexistent",
            "--mount",
            f"type=bind,source={export},target=/work,readonly",
            "--interactive",
            "--entrypoint",
            "/usr/local/bin/python3.12",
            self.runtime.image_id,
            "-I",
            "-S",
            "-B",
            f"/work/{entrypoint}",
        )
        cid = result.stdout.decode().strip()
        if not re.fullmatch("[0-9a-f]{64}", cid):
            raise ValueError(
                "container creation has no immutable ID; reconcile its labelled intent"
            )
        durable_write(root / "container-id", cid.encode())
        observed = self._inspect(root, cid)
        durable_write(
            root / "effective-policy.json",
            canonical_json(
                {
                    "id": observed["Id"],
                    "image": observed["Image"],
                    "mounts": observed["Mounts"],
                    "host": observed["HostConfig"],
                    "labels": observed["Config"]["Labels"],
                    "user": observed["Config"]["User"],
                    "command": observed["Config"]["Cmd"],
                    "config": observed["Config"],
                }
            ).encode(),
        )
        try:
            self._verify_policy(
                observed, root=root, nonce=nonce, intent=intent, export=export, limits=limits
            )
        except BaseException:
            labels = observed["Config"].get("Labels") or {}
            if (
                observed["Id"] == cid
                and labels.get("autoengineering.nonce") == nonce
                and labels.get("autoengineering.intent") == intent
                and not observed["State"]["Running"]
            ):
                self._metadata(root, "rm", cid)
            raise
        try:
            on_launch(
                {
                    "container_id": cid,
                    "nonce": nonce,
                    "intent_digest": intent,
                    "image_id": self.runtime.image_id,
                }
            )
        except BaseException:
            # Not started yet. Preserve the intent and remove only the owned,
            # inspected container created by this call.
            self._metadata(root, "rm", cid)
            raise
        began = time.monotonic()
        job = {
            "nonce": nonce,
            "container_id": cid,
            "intent_digest": intent,
            "docker": self.runtime.docker,
            "endpoint": self.runtime.endpoint,
            "config": str(root / "docker-config"),
            "deadline": began + wall_seconds,
        }
        durable_write(root / "watchdog-job.json", canonical_json(job).encode())
        with (root / "watchdog.log").open("xb") as log:
            watcher = subprocess.Popen(
                [
                    sys.executable,
                    "-I",
                    "-S",
                    str(Path(__file__).with_name("container_watchdog.py")),
                    "--job",
                    str(root / "watchdog-job.json"),
                    "--nonce",
                    nonce,
                ],
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
        ready = root / "watchdog-ready.json"
        deadline = time.monotonic() + 3
        while not ready.exists() and watcher.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if not ready.exists():
            raise ValueError("container watchdog is unavailable; container was not started")
        if unique_json(ready.read_text()).get("nonce") != nonce:
            raise ValueError("container watchdog readiness identity mismatch")
        # A source edit after snapshot cannot silently become the tested implementation.
        for name, expected in manifest.items():
            if hashlib.sha256(confined_file(export, name).read_bytes()).hexdigest() != expected:
                raise ValueError("container export bytes changed before execution")
        client = subprocess.Popen(
            self._command(root, "start", "--attach", "--interactive", cid),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        selector = selectors.DefaultSelector()
        buffers = {"stdout": bytearray(), "stderr": bytearray()}
        # Writes are bounded too; use nonblocking stdin to avoid a candidate that never reads.
        for name, stream in (("stdout", client.stdout), ("stderr", client.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        os.set_blocking(client.stdin.fileno(), False)
        selector.register(client.stdin, selectors.EVENT_WRITE, "stdin")
        offset = 0
        reason = None
        try:
            while selector.get_map() or client.poll() is None:
                if cancelled():
                    reason = "cancelled"
                elif time.monotonic() >= began + wall_seconds:
                    reason = "timeout"
                if reason:
                    self._queue_stop(root, reason)
                if reason and time.monotonic() > began + wall_seconds + 5:
                    break
                for key, _ in selector.select(0.02):
                    if key.data == "stdin":
                        if offset == len(payload):
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                            continue
                        try:
                            offset += os.write(key.fileobj.fileno(), payload[offset:])
                        except BrokenPipeError:
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                    else:
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        remaining = limits.output_bytes - sum(
                            len(value) for value in buffers.values()
                        )
                        buffers[key.data].extend(chunk[:remaining])
                        if len(chunk) > remaining:
                            reason = "output_limit"
                            self._queue_stop(root, reason)
                if watcher.poll() is not None and not (root / "watchdog-result.json").exists():
                    reason = "reconciliation_required"
                    break
            final = self._inspect(root, cid)
            if final["State"]["Running"]:
                self._queue_stop(root, "observer_failed")
                try:
                    watcher.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                final = self._inspect(root, cid)
            stopped = not final["State"]["Running"]
            if not stopped:
                reason = "reconciliation_required"
            elif reason is None:
                reason = "model_failure" if final["State"]["ExitCode"] else "success"
            result = {
                "status": reason,
                "container_id": cid,
                "nonce": nonce,
                "intent_digest": intent,
                "image_id": self.runtime.image_id,
                "stopped": stopped,
                "oom_killed": final["State"]["OOMKilled"],
                "exitcode": final["State"]["ExitCode"],
                "elapsed_seconds": time.monotonic() - began,
                "stdout_sha256": hashlib.sha256(buffers["stdout"]).hexdigest(),
                "stderr_sha256": hashlib.sha256(buffers["stderr"]).hexdigest(),
                "effective_policy_sha256": hashlib.sha256(
                    confined_file(root, "effective-policy.json").read_bytes()
                ).hexdigest(),
            }
            durable_write(root / "stdout.bin", bytes(buffers["stdout"]))
            durable_write(root / "stderr.bin", bytes(buffers["stderr"]))
            durable_write(root / "result.json", canonical_json(result).encode())
            if stopped:
                watcher.wait(timeout=5)
                self._metadata(root, "rm", cid)
            return ContainerResult(
                reason,
                cid,
                bytes(buffers["stdout"]),
                bytes(buffers["stderr"]),
                stopped,
                result["oom_killed"],
                result["elapsed_seconds"],
                digest(result),
            )
        finally:
            selector.close()
            for stream in (client.stdin, client.stdout, client.stderr):
                if not stream.closed:
                    stream.close()
            if client.poll() is None:
                client.kill()
                client.wait(timeout=2)

    def _queue_stop(self, root, reason):
        if not (root / "stop-container.json").exists():
            try:
                durable_write(
                    root / "stop-container.json", canonical_json({"reason": reason}).encode()
                )
            except FileExistsError:
                pass


def boundary_source_identity() -> str:
    """Explicit boundary closure. Role prompts and host adapters are not science inputs."""
    package = Path(__file__).resolve().parent.parent
    paths = (
        "agents/containers.py",
        "agents/container_watchdog.py",
        "agents/sandbox.py",
        "campaign/artifacts.py",
        "campaign/serialization.py",
        "campaign/store.py",
        "campaign/records.py",
    )
    return digest(
        {
            name: hashlib.sha256(confined_file(package, name).read_bytes()).hexdigest()
            for name in paths
        }
    )
