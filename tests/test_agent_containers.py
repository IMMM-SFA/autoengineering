"""Container policy checks and owned-watchdog faults without image downloads."""

from copy import deepcopy
import json
import subprocess
import sys
import time

import pytest

from autoengineering.agents.containers import ContainerRuntime, DockerBoundary, discover_runtime
from autoengineering.agents.sandbox import BoundaryLimits
from autoengineering.campaign.serialization import digest

CID = "c" * 64


def runtime(docker="/usr/local/bin/docker"):
    return ContainerRuntime(
        "sha256:" + "a" * 64,
        "python@sha256:" + "b" * 64,
        "arm64",
        "unix:///private/tmp/test-docker.sock",
        docker,
    )


def policy(tmp_path):
    tmp_path.chmod(0o700)
    (tmp_path / "container-id").write_text(CID)
    declaration = {"entrypoint": "probe.py"}
    (tmp_path / "intent.json").write_text(json.dumps(declaration))
    export = tmp_path / "export"
    export.mkdir()
    limits = BoundaryLimits()
    value = {
        "Id": CID,
        "Image": runtime().image_id,
        "Config": {
            "Labels": {
                "autoengineering.nonce": "nonce",
                "autoengineering.intent": digest(declaration),
            },
            "User": "65534:65534",
            "WorkingDir": "/work",
            "Entrypoint": ["/usr/local/bin/python3.12"],
            "Cmd": ["-I", "-S", "-B", "/work/probe.py"],
        },
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "Privileged": False,
            "Memory": limits.memory_bytes,
            "MemorySwap": limits.memory_bytes,
            "NanoCpus": 1000000000,
            "PidsLimit": 8,
            "CapDrop": ["ALL"],
            "CapAdd": None,
            "SecurityOpt": ["no-new-privileges"],
            "LogConfig": {"Type": "none"},
            "Binds": None,
            "PidMode": "",
            "IpcMode": "private",
            "Tmpfs": {"/dev/shm": "ro,nosuid,nodev,noexec,size=65536,mode=000"},
            "Ulimits": [
                {"Name": name, "Soft": number, "Hard": number}
                for name, number in [
                    ("nofile", 32),
                    ("cpu", limits.cpu_seconds),
                    ("fsize", limits.output_bytes),
                ]
            ],
        },
        "Mounts": [{"Type": "bind", "Destination": "/work", "Source": str(export), "RW": False}],
    }
    return value, dict(
        root=tmp_path, nonce="nonce", intent=digest(declaration), export=export, limits=limits
    )


def test_exact_container_policy_is_checked_before_start(tmp_path):
    value, args = policy(tmp_path)
    DockerBoundary(runtime())._verify_policy(value, **args)
    for field, changed in [
        ("NetworkMode", "bridge"),
        ("ReadonlyRootfs", False),
        ("Privileged", True),
        ("Memory", 0),
        ("PidsLimit", 0),
        ("CapAdd", ["SYS_ADMIN"]),
        ("PidMode", "host"),
        ("IpcMode", "host"),
        ("SecurityOpt", []),
        ("Tmpfs", {}),
        ("Ulimits", []),
    ]:
        wrong = deepcopy(value)
        wrong["HostConfig"][field] = changed
        with pytest.raises(ValueError):
            DockerBoundary(runtime())._verify_policy(wrong, **args)
    for key, changed in [("RW", True), ("Source", str(tmp_path)), ("Destination", "/evaluator")]:
        wrong = deepcopy(value)
        wrong["Mounts"][0][key] = changed
        with pytest.raises(ValueError, match="mounts"):
            DockerBoundary(runtime())._verify_policy(wrong, **args)
    wrong = deepcopy(value)
    wrong["Config"]["Cmd"] = ["-c", "unapproved command"]
    with pytest.raises(ValueError, match="command"):
        DockerBoundary(runtime())._verify_policy(wrong, **args)


def test_runtime_rejects_mutable_images_private_repositories_and_remote_daemons():
    with pytest.raises(ValueError, match="immutable"):
        ContainerRuntime(
            "python:3.12-slim", runtime().repository_digest, "arm64", runtime().endpoint, "docker"
        )
    with pytest.raises(ValueError, match="official"):
        ContainerRuntime(
            runtime().image_id,
            "private/model@sha256:" + "b" * 64,
            "arm64",
            runtime().endpoint,
            "docker",
        )
    with pytest.raises(ValueError, match="local Unix"):
        ContainerRuntime(
            runtime().image_id, runtime().repository_digest, "arm64", "tcp://remote:2375", "docker"
        )


def test_discovery_never_pulls_a_missing_image(tmp_path, monkeypatch):
    executable = tmp_path / "docker"
    executable.write_text("fake metadata executable")
    calls = []

    def call(arguments, **kwargs):
        calls.append(arguments)
        if "context" in arguments:
            return subprocess.CompletedProcess(arguments, 0, stdout=runtime().endpoint + "\n")
        return subprocess.CompletedProcess(arguments, 1, stdout="", stderr="missing image")

    monkeypatch.setattr(subprocess, "run", call)
    with pytest.raises(ValueError, match="no image was pulled"):
        discover_runtime("python:3.12-slim", docker=str(executable))
    assert not any(argument in ("pull", "create") for call in calls for argument in call)


def test_invalid_probe_input_never_creates_an_execution_root(tmp_path):
    tmp_path.chmod(0o700)
    boundary = DockerBoundary(runtime())
    for source, payload, seconds in [
        ({"../escape.py": b"pass"}, b"", 1),
        ({"probe.py": b"pass"}, b"x" * 65537, 1),
        ({"probe.py": b"pass"}, b"", True),
    ]:
        with pytest.raises(ValueError):
            boundary.run_probe(
                source,
                entrypoint=next(iter(source)),
                payload=payload,
                root=tmp_path / "execution",
                wall_seconds=seconds,
            )
    assert not (tmp_path / "execution").exists()


def test_qualified_execution_rejects_changed_client_or_server_without_start(tmp_path, monkeypatch):
    from dataclasses import replace
    from types import SimpleNamespace
    import autoengineering.agents.containers as module
    import autoengineering.agents.qualification as qualification

    fixed = replace(runtime(), client_sha256="d" * 64, server_fingerprint="e" * 64)
    limits = BoundaryLimits()
    monkeypatch.setattr(
        qualification,
        "verify_qualification",
        lambda *a, **k: SimpleNamespace(runtime=fixed, limits=limits),
    )
    boundary = DockerBoundary(fixed)
    monkeypatch.setattr(
        boundary, "run_probe", lambda *a, **k: pytest.fail("unqualified execution started")
    )
    for changed in (
        replace(fixed, client_sha256="f" * 64),
        replace(fixed, server_fingerprint="f" * 64),
    ):
        monkeypatch.setattr(module, "discover_runtime", lambda *a, **k: changed)
        with pytest.raises(ValueError, match="changed since qualification"):
            boundary.run_qualified(
                {"probe.py": b"pass"},
                qualification_root=tmp_path,
                qualification_digest="a" * 64,
                limits=limits,
            )


def fake_docker(tmp_path, *, nonce="owned", status="running"):
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps(
            {
                "Id": CID,
                "Config": {
                    "Labels": {"autoengineering.nonce": nonce, "autoengineering.intent": "intent"}
                },
                "State": {
                    "Status": status,
                    "Running": status == "running",
                    "ExitCode": 0,
                    "OOMKilled": False,
                },
            }
        )
    )
    executable = tmp_path / "fake-docker"
    executable.write_text(f"""#!{sys.executable}
import json,os,sys
from pathlib import Path
state=Path({str(state)!r});args=sys.argv[5:]
if args[0]=='inspect': print(state.read_text())
elif args[0]=='kill':
 value=json.loads(state.read_text());value['State'].update(Status='exited',Running=False,ExitCode=137)
 temporary=state.with_suffix('.tmp');temporary.write_text(json.dumps(value));os.replace(temporary,state)
 Path({str(tmp_path / "killed")!r}).write_text(args[1])
elif args[0]=='rm':
 Path({str(tmp_path / "removed")!r}).write_text(args[1]);state.unlink()
else: sys.exit(2)
""")
    executable.chmod(0o700)
    return executable


@pytest.mark.parametrize("status", ["created", "running"])
def test_watchdog_deadline_removes_unstarted_or_kills_owned_running_container(tmp_path, status):
    executable = fake_docker(tmp_path, status=status)
    job = {
        "nonce": "owned",
        "container_id": CID,
        "intent_digest": "intent",
        "docker": str(executable),
        "endpoint": runtime().endpoint,
        "config": str(tmp_path),
        "deadline": time.monotonic() - 1,
    }
    path = tmp_path / "watchdog-job.json"
    path.write_text(json.dumps(job))
    from autoengineering.agents import container_watchdog

    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            container_watchdog.__file__,
            "--job",
            str(path),
            "--nonce",
            "owned",
        ],
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 0, result.stderr
    receipt = json.loads((tmp_path / "watchdog-result.json").read_text())
    assert receipt["stopped"] is True and receipt["reason"] == "timeout"
    marker = tmp_path / ("removed" if status == "created" else "killed")
    assert marker.read_text() == CID


def test_watchdog_never_signals_a_container_with_wrong_nonce(tmp_path):
    executable = fake_docker(tmp_path, nonce="unrelated")
    job = {
        "nonce": "owned",
        "container_id": CID,
        "intent_digest": "intent",
        "docker": str(executable),
        "endpoint": runtime().endpoint,
        "config": str(tmp_path),
        "deadline": time.monotonic() - 1,
    }
    path = tmp_path / "watchdog-job.json"
    path.write_text(json.dumps(job))
    from autoengineering.agents import container_watchdog

    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            container_watchdog.__file__,
            "--job",
            str(path),
            "--nonce",
            "owned",
        ],
        capture_output=True,
        timeout=5,
    )
    assert result.returncode == 124
    assert not (tmp_path / "killed").exists() and not (tmp_path / "removed").exists()
    assert json.loads((tmp_path / "watchdog-result.json").read_text())["stopped"] is False
