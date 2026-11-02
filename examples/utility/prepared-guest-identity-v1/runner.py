"""Fixed metadata-only discovery for a built candidate, never runtime admission."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import time
from uuid import uuid4

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_receipts import ENVIRONMENT
from autoengineering.utility.inference_guest import FrozenGuestProfile, GuestPythonIdentity, LIMITS
from examples.utility import guest_image_build as build
from examples.utility.inference_environment import InferenceEnvironmentInputs, verify_inputs

PURPOSE = "utility-guest-python-discovery-v1"
PROGRAM = """import signal
signal.alarm(10)
import hashlib, importlib.metadata, json, os, sys
from pathlib import Path
from autoengineering.utility import inference_guest
print(json.dumps({
    "schema": "utility-guest-python-observation-v1",
    "nonce": os.environ["AE_IDENTITY_NONCE"],
    "python": inference_guest.observe_python().to_dict(),
    "executable": sys.executable,
    "isolated": sys.flags.isolated,
    "uid": os.geteuid(), "gid": os.getegid(),
    "package_version": importlib.metadata.version("autoengineering"),
    "identity_source_sha256": hashlib.sha256(
        Path(inference_guest.__file__).read_bytes()).hexdigest()
}, sort_keys=True, allow_nan=False))
"""


def _save(root, name, value):
    durable_write(root / name, canonical_json(value).encode())


def _read(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 4 * 1024**2:
        raise ValueError("identity metadata exceeds envelope")
    return unique_json(path.read_text())


def _command(request, work):
    nonce = request["nonce"]
    if not re.fullmatch(r"[0-9a-f]{32}", nonce):
        raise ValueError("identity nonce differs")
    return [
        "run",
        "--rm",
        "--pull=never",
        "--platform",
        "linux/amd64",
        "--name",
        "ae-guest-identity-" + nonce,
        "--cidfile",
        str(work / "container.id"),
        "--network",
        "none",
        "--read-only",
        "--user",
        "1000:1000",
        "--workdir",
        "/work",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--memory",
        "1g",
        "--memory-swap",
        "1g",
        "--cpus",
        "1",
        "--pids-limit",
        "16",
        "--ipc",
        "none",
        "--cgroupns",
        "private",
        "--log-driver",
        "none",
        "--tmpfs",
        "/work:rw,noexec,nosuid,nodev,size=128m,mode=0700,uid=1000,gid=1000",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=16m,mode=1777",
        *[
            part
            for k, v in (*ENVIRONMENT, ("AE_IDENTITY_NONCE", nonce))
            for part in ("--env", f"{k}={v}")
        ],
        "--entrypoint",
        "/opt/inference/bin/python",
        request["image_id"],
        "-I",
        "-B",
        "-c",
        PROGRAM,
    ]


def _request(completion, inputs, bindings, runtime, nonce, source):
    return {
        "schema": "utility-guest-python-discovery-request-v1",
        "completion_digest": digest(completion),
        "image_id": completion["image_id"],
        "environment_digest": inputs.digest,
        "bindings_digest": digest(bindings),
        "binary": build._binary(bindings["cli"]),
        "endpoint": build._endpoint(bindings["endpoint"]),
        "runtime": runtime,
        "nonce": nonce,
        "source_sha256": source,
        "program_sha256": hashlib.sha256(PROGRAM.encode()).hexdigest(),
        "active_seconds": 60,
        "cleanup_seconds": 10,
        "inner_alarm_seconds": 10,
        "container_creations_reserved": 1,
        "container_starts_reserved": 1,
        "client_capture_bytes": build.MAX_LOG,
        "result_bytes": 16384,
        "scientific_starts": 0,
        "private_label_reads": 0,
        "automatic_retries": 0,
        "runtime_qualified": False,
    }


def prepare(build_work, *, completion_digest, environment, output, work):
    original = checked_directory(build_work)
    completion = build.read_completion(original, expected_digest=completion_digest)
    build_request, old = _read(original, "request.json"), _read(original, "bindings.json")
    inputs = verify_inputs(
        environment, expected_digest=build_request["image_plan"]["environment_inputs_digest"]
    )
    if not any(
        r.path == "autoengineering/utility/inference_guest.py" for r in inputs.wheel_python_sources
    ):
        raise ValueError("identity source is absent from the frozen wheel")
    output, work = Path(output).absolute(), Path(work).absolute()
    for path in (output, work):
        build.guest_image._public_directory(path.parent)
        if path.exists() or path.is_symlink():
            raise ValueError("identity output and work must be absent")
    if output.is_relative_to(work) or work.is_relative_to(output):
        raise ValueError("identity scopes overlap")
    environment = checked_directory(environment)
    if any(
        a.is_relative_to(b) or b.is_relative_to(a)
        for a in (output, work)
        for b in (original, environment)
    ):
        raise ValueError("identity scopes overlap original build/environment")
    bindings = {"cli": old["cli"], "endpoint": old["endpoint"], "work": str(work)}
    version = _read(original, "00.log")
    api = GuestDaemonAPI(
        old["endpoint"], api_version=version["ApiVersion"], server_digest=digest(version)
    )
    server = api._json("GET", "/version", deadline=time.monotonic() + 10)
    if any(server.get(k) != version.get(k) for k in ("Os", "Arch", "Version", "ApiVersion")):
        raise ValueError("identity daemon changed since the image build")
    api = GuestDaemonAPI(
        old["endpoint"], api_version=server["ApiVersion"], server_digest=digest(server)
    )
    source = Path(__file__).read_bytes()
    request = _request(
        completion,
        inputs,
        bindings,
        api.profile.to_dict(),
        uuid4().hex,
        hashlib.sha256(source).hexdigest(),
    )
    output.mkdir(mode=0o700)
    for name, value in (
        ("completion.json", completion),
        ("environment.json", inputs.to_dict()),
        ("request.json", request),
        ("bindings.json", bindings),
    ):
        _save(output, name, value)
    durable_write(output / "runner.py", source)
    return request


def _profile(raw, request, inputs):
    if not 0 < len(raw) <= request["result_bytes"]:
        raise ValueError("identity result exceeds envelope")
    value = unique_json(raw.decode())
    if set(value) != {
        "schema",
        "nonce",
        "python",
        "executable",
        "isolated",
        "uid",
        "gid",
        "package_version",
        "identity_source_sha256",
    }:
        raise ValueError("identity result schema differs")
    source = next(
        r
        for r in inputs.wheel_python_sources
        if r.path == "autoengineering/utility/inference_guest.py"
    )
    python = GuestPythonIdentity.from_dict(value["python"])
    expected_python = next(p.version for p in inputs.archives if p.name == "python")
    if (
        value["schema"] != "utility-guest-python-observation-v1"
        or value["nonce"] != request["nonce"]
        or value["executable"] != "/opt/inference/bin/python"
        or type(value["isolated"]) is not int
        or value["isolated"] != 1
        or type(value["uid"]) is not int
        or type(value["gid"]) is not int
        or (value["uid"], value["gid"]) != (1000, 1000)
        or value["package_version"] != inputs.wheel_version
        or python.version != expected_python
        or value["identity_source_sha256"] != source.sha256
    ):
        raise ValueError("observed identity differs from the fixed image/environment")
    profile = FrozenGuestProfile(
        "utility-frozen-guest-profile-v1",
        inputs.digest,
        inputs.lock.sha256,
        inputs.wheel.sha256,
        digest([r.to_dict() for r in inputs.wheel_python_sources]),
        request["image_id"],
        python,
        digest(dict(LIMITS)),
        "unqualified-candidate",
    )
    profile.validate_environment(inputs.to_dict())
    return profile


def _cleanup(api, request, work, *, deadline):
    cid_path = work / "container.id"
    cid = None
    if cid_path.exists():
        path = confined_file(work, "container.id")
        if path.stat().st_size > 128:
            raise ValueError("identity container ID exceeds envelope")
        cid = path.read_text().strip()
        if not re.fullmatch(r"[0-9a-f]{64}", cid):
            raise ValueError("identity container ID differs")
    target = cid or "ae-guest-identity-" + request["nonce"]
    status, raw = api._request("GET", f"/containers/{target}/json", deadline=deadline)
    if status == 200:
        value = unique_json(raw.decode())
        config = value.get("Config", {})
        labels = config.get("Labels", {})
        if (
            value.get("Name") != "/ae-guest-identity-" + request["nonce"]
            or config.get("Image") != request["image_id"]
            or labels.get("org.autoengineering.purpose") != PURPOSE
            or labels.get("org.autoengineering.nonce") != request["nonce"]
            or (cid is not None and value.get("Id") != cid)
        ):
            raise ValueError("identity cleanup ownership differs")
        cid = value["Id"]
        if not re.fullmatch(r"[0-9a-f]{64}", cid):
            raise ValueError("identity cleanup ID differs")
        _save(
            work,
            "cleanup-delete-intent.json",
            {"container_id": cid, "request_digest": digest(request)},
        )
        status, _ = api._request("DELETE", f"/containers/{cid}?force=true", deadline=deadline)
        if status not in (204, 404):
            raise ValueError("identity cleanup deletion is unverified")
        status, _ = api._request("GET", f"/containers/{cid}/json", deadline=deadline)
    if status != 404:
        raise ValueError("identity container absence is unverified")
    result = {
        "schema": "utility-guest-python-cleanup-v1",
        "container_id": cid,
        "request_digest": digest(request),
        "absent": True,
        "creation_outcome_known": cid is not None,
        "owner_loss_qualified": False,
    }
    _save(work, "cleanup.json", result)
    return result


def execute(bundle, *, expected_digest):
    bundle = checked_directory(bundle)
    request, bindings = _read(bundle, "request.json"), _read(bundle, "bindings.json")
    inputs = InferenceEnvironmentInputs.from_dict(_read(bundle, "environment.json"))
    completion = _read(bundle, "completion.json")
    if (
        digest(request) != expected_digest
        or request
        != _request(
            completion,
            inputs,
            bindings,
            request["runtime"],
            request["nonce"],
            request["source_sha256"],
        )
        or hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != request["source_sha256"]
    ):
        raise ValueError("identity request/source or client bindings changed")
    api = GuestDaemonAPI(
        bindings["endpoint"],
        api_version=request["runtime"]["api_version"],
        server_digest=request["runtime"]["server_digest"],
    )
    if api.profile.to_dict() != request["runtime"]:
        raise ValueError("identity runtime implementation changed")
    work = Path(bindings["work"])
    build.guest_image._public_directory(work.parent)
    if work.exists() or work.is_symlink():
        raise ValueError("identity job consumed; automatic retry forbidden")
    work.mkdir(mode=0o700)
    (work / "config").mkdir(mode=0o700)
    durable_write(work / "config/config.json", b"{}")
    for name in (
        "request.json",
        "bindings.json",
        "completion.json",
        "environment.json",
        "runner.py",
    ):
        durable_write(work / name, confined_file(bundle, name).read_bytes())
    began = time.monotonic()
    deadline = began + request["active_seconds"]
    argv = [
        bindings["cli"],
        "--config",
        str(work / "config"),
        "--host",
        "unix://" + bindings["endpoint"],
        *_command(request, work),
    ]
    # Labels are fixed ownership evidence, never data or a caller-supplied command.
    argv[argv.index("--entrypoint") : argv.index("--entrypoint")] = [
        "--label",
        f"org.autoengineering.purpose={PURPOSE}",
        "--label",
        "org.autoengineering.nonce=" + request["nonce"],
    ]
    _save(
        work,
        "intent.json",
        {
            "request_digest": expected_digest,
            "argv_digest": digest(argv),
            "began_at": began,
            "deadline": deadline,
            "creations_reserved": 1,
            "starts_reserved": 1,
        },
    )
    env = {
        k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR") if k in os.environ
    }
    env.update(DOCKER_HOST="unix://" + bindings["endpoint"], DOCKER_CONFIG=str(work / "config"))
    cleanup_started = False
    physical_starts = None

    def cleanup_once():
        nonlocal cleanup_started
        if cleanup_started:
            raise ValueError("identity cleanup already attempted")
        cleanup_started = True
        cleanup_deadline = min(began + 70, time.monotonic() + 10)
        _save(
            work,
            "cleanup-intent.json",
            {"request_digest": expected_digest, "deadline": cleanup_deadline},
        )
        return _cleanup(api, request, work, deadline=cleanup_deadline)

    try:
        server = api._json("GET", "/version", deadline=deadline)
        if digest(server) != request["runtime"]["server_digest"]:
            raise ValueError("identity daemon changed")
        status = build._run(argv, env=env, cwd=work, deadline=deadline, log=work / "output.log")
        _save(work, "client-result.json", {"exit_code": status})
        if status != 0:
            raise ValueError("identity client failed; retry forbidden")
        physical_starts = 1
        profile = _profile(confined_file(work, "output.log").read_bytes(), request, inputs)
        cleanup = cleanup_once()
        if not cleanup["creation_outcome_known"]:
            raise ValueError("identity creation outcome remains unknown")
    except BaseException:
        if not cleanup_started:
            try:
                cleanup_once()
            except BaseException:
                _save(
                    work,
                    "cleanup-unknown.json",
                    {
                        "request_digest": expected_digest,
                        "outcome": "unknown",
                        "new_start_allowed": False,
                    },
                )
        elif not (work / "cleanup.json").exists():
            _save(
                work,
                "cleanup-unknown.json",
                {
                    "request_digest": expected_digest,
                    "outcome": "unknown",
                    "new_start_allowed": False,
                },
            )
        _save(
            work,
            "failure.json",
            {
                "request_digest": expected_digest,
                "physical_container_starts": physical_starts,
                "starts_reserved": 1,
                "automatic_retry_allowed": False,
            },
        )
        raise
    result = {
        "schema": "utility-guest-python-discovery-completion-v1",
        "request_digest": expected_digest,
        "profile": profile.to_dict(),
        "cleanup": cleanup,
        "elapsed_seconds": time.monotonic() - began,
        "runtime_qualified": False,
        "scientific_starts": 0,
        "physical_container_starts": physical_starts,
    }
    _save(work, "complete.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    for name in ("build_work", "environment", "work", "output"):
        prepare_parser.add_argument(name, type=Path)
    prepare_parser.add_argument("--completion-digest", required=True)
    run = sub.add_parser("execute")
    run.add_argument("bundle", type=Path)
    run.add_argument("--expected-digest", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.build_work,
            completion_digest=args.completion_digest,
            environment=args.environment,
            work=args.work,
            output=args.output,
        )
    else:
        result = execute(args.bundle, expected_digest=args.expected_digest)
    print(canonical_json({"digest": digest(result)}))


if __name__ == "__main__":
    main()
