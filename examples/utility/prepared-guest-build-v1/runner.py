"""Prepare one local candidate-image job; execute only with separate authority.

Client termination is bounded while the owner survives. Daemon-side cancellation,
resource enforcement and storage quotas are not qualified by this helper.
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.guest_receipts import BOOTSTRAP_COMMAND, ENVIRONMENT
from examples.utility import guest_image_context, guest_image

SECONDS = 1200
MAX_LOG = 16 * 1024**2


def _binary(path):
    path = Path(path).absolute()
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or not os.access(path, os.X_OK):
        raise ValueError("build client must be an existing executable")
    size = resolved.stat().st_size
    if size > 128 * 1024**2:
        raise ValueError("build client exceeds fingerprint envelope")
    sha = hashlib.sha256()
    with resolved.open("rb") as stream:
        for data in iter(lambda: stream.read(1024**2), b""):
            sha.update(data)
    return {
        "path_digest": digest(str(path)),
        "resolved_digest": digest(str(resolved)),
        "sha256": sha.hexdigest(),
        "size_bytes": size,
    }


def _endpoint(path):
    path = Path(path).resolve(strict=True)
    metadata = path.stat()
    if not stat.S_ISSOCK(metadata.st_mode):
        raise ValueError("build endpoint must be an existing local Unix socket")
    return {
        "path_digest": digest(str(path)),
        "device": metadata.st_dev,
        "inode": metadata.st_ino,
        "owner_uid": metadata.st_uid,
    }


def _commands(plan):
    base = plan["base"]["repository"] + "@" + plan["base"]["manifest_digest"]
    return [
        ["version", "--format", "{{json .Server}}"],
        ["buildx", "inspect", "default"],
        ["pull", "--platform", "linux/amd64", base],
        ["image", "inspect", base, "--format", "{{json .}}"],
        [
            "buildx",
            "build",
            "--builder",
            "default",
            "--load",
            "--platform",
            "linux/amd64",
            "--network",
            "none",
            "--pull=false",
            "--no-cache",
            "--provenance=false",
            "--sbom=false",
            "--resource",
            "memory=2g",
            "--resource",
            "memory-swap=2g",
            "--resource",
            "cpu-period=100000",
            "--resource",
            "cpu-quota=100000",
            "--iidfile",
            "{work}/image.id",
            "--metadata-file",
            "{work}/build-metadata.json",
            "--progress",
            "plain",
            "{context}/build",
        ],
        ["image", "inspect", "{image_id}", "--format", "{{json .}}"],
    ]


def _request(context, plan, bindings, binary, endpoint, source):
    return {
        "schema": "utility-local-image-build-request-v1",
        "context_digest": digest(context),
        "image_plan": plan,
        "bindings_digest": digest(bindings),
        "binary": binary,
        "endpoint": endpoint,
        "runner_digest": source,
        "commands": _commands(plan),
        "client_deadline_seconds": SECONDS,
        "per_command_log_bytes": MAX_LOG,
        "base_pull_commands": 1,
        "build_commands": 1,
        "automatic_retries": 0,
        "base_compressed_layer_bytes": plan["base"]["compressed_layer_bytes"],
        "daemon_cancellation_qualified": False,
        "disk_quota_enforced": False,
        "step_resource_enforcement_qualified": False,
        "runtime_qualified": False,
        "scientific_starts": 0,
        "provider_calls": 0,
        "independent_label_accesses": 0,
    }


def prepare(context_root, *, context_digest, cli, endpoint, work, output):
    context_root = checked_directory(context_root)
    context = guest_image_context.verify(context_root, expected_digest=context_digest)
    plan = guest_image.verify(context_root / "proof", expected_digest=context["image_plan_digest"])
    cli = Path(cli).absolute()
    endpoint = Path(endpoint).resolve(strict=True)
    work, output = Path(work).absolute(), Path(output).absolute()
    for path in (work, output):
        guest_image._public_directory(path.parent)
        if path.exists() or path.is_symlink():
            raise ValueError("build request and work directories must be absent")
    if any(
        a.is_relative_to(b) or b.is_relative_to(a)
        for a, b in [(work, output), (work, context_root), (output, context_root)]
    ):
        raise ValueError("build job scopes must be disjoint")
    bindings = {
        "context": str(context_root),
        "cli": str(cli),
        "endpoint": str(endpoint),
        "work": str(work),
    }
    binary, socket = _binary(cli), _endpoint(endpoint)
    source = Path(__file__).read_bytes()
    request = _request(context, plan, bindings, binary, socket, hashlib.sha256(source).hexdigest())
    output.mkdir(mode=0o700)
    for name, value in [("request.json", request), ("bindings.json", bindings)]:
        durable_write(output / name, canonical_json(value).encode())
    durable_write(output / "runner.py", source)
    return request


def _read(root, name, limit=1024**2):
    path = confined_file(root, name)
    if path.stat().st_size > limit:
        raise ValueError("build metadata exceeds envelope")
    return unique_json(path.read_text())


def _kill_client(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGKILL)
    process.wait(timeout=5)


def _run(argv, *, env, cwd, deadline, log):
    """One owned process group. Stopping it does not prove daemon cancellation."""
    if time.monotonic() >= deadline:
        raise TimeoutError("original build client deadline expired")
    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=cwd,
        env=env,
        start_new_session=True,
    )
    size = 0
    try:
        with log.open("xb") as output, selectors.DefaultSelector() as selector:
            os.fchmod(output.fileno(), 0o600)
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("original build client deadline expired")
                for key, _ in selector.select(min(0.1, remaining)):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    size += len(data)
                    if size > MAX_LOG:
                        raise ValueError("build client output exceeds envelope")
                    output.write(data)
            status = process.wait(timeout=max(0.01, deadline - time.monotonic()))
            output.flush()
            os.fsync(output.fileno())
            if time.monotonic() >= deadline:
                raise TimeoutError("original build client deadline expired before log commit")
        return status
    finally:
        _kill_client(process)
        process.stdout.close()


def _validate(step, raw, request, bindings):
    if step == 0:
        value = unique_json(raw.decode())
        if value.get("Os") != "linux":
            raise ValueError("build daemon is not Linux")
    elif step == 1:
        text = raw.decode()
        driver = re.findall(r"^Driver:\s*(\S+)\s*$", text, re.MULTILINE)
        endpoints = re.findall(r"^Endpoint:\s*(\S+)\s*$", text, re.MULTILINE)
        if driver != ["docker"] or endpoints != ["unix://" + bindings["endpoint"]]:
            raise ValueError("builder must use the pinned local Docker driver and endpoint")
        if "linux/amd64" not in text:
            raise ValueError("builder does not advertise the target platform")
    elif step in (3, 5):
        value = unique_json(raw.decode())
        if value.get("Os") != "linux" or value.get("Architecture") != "amd64":
            raise ValueError("built/base image platform differs")
        if step == 3 and value.get("Id") != request["image_plan"]["base"]["image_id"]:
            raise ValueError("pulled base image identity differs")
        if step == 5:
            config = value.get("Config", {})
            if (
                config.get("Cmd") != list(BOOTSTRAP_COMMAND)
                or config.get("User") != "1000:1000"
                or config.get("WorkingDir") != "/work"
                or config.get("Entrypoint") not in (None, [])
                or not all(f"{k}={v}" in config.get("Env", []) for k, v in ENVIRONMENT)
            ):
                raise ValueError("candidate image fixed command/user differs")


def execute(bundle, *, expected_digest):
    """Run only after explicit authority for local pull, installation and image assembly."""
    bundle = checked_directory(bundle)
    request = _read(bundle, "request.json")
    bindings = _read(bundle, "bindings.json")
    if digest(request) != expected_digest or digest(bindings) != request["bindings_digest"]:
        raise ValueError("build request/bindings differ from explicit pin")
    context_root = Path(bindings["context"])
    work = Path(bindings["work"])
    context = guest_image_context.verify(context_root, expected_digest=request["context_digest"])
    plan = guest_image.verify(context_root / "proof", expected_digest=context["image_plan_digest"])
    if request != _request(
        context, plan, bindings, request["binary"], request["endpoint"], request["runner_digest"]
    ):
        raise ValueError("build request commands or limits changed")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != request["runner_digest"]:
        raise ValueError("build runner source changed")
    if (
        _binary(bindings["cli"]) != request["binary"]
        or _endpoint(bindings["endpoint"]) != request["endpoint"]
    ):
        raise ValueError("build client or local endpoint changed")
    guest_image._public_directory(work.parent)
    if work.exists() or work.is_symlink():
        raise ValueError("build job consumed; new allowance or automatic retry forbidden")
    work.mkdir(mode=0o700)
    (work / "config").mkdir(mode=0o700)
    durable_write(work / "config/config.json", b"{}")
    durable_write(work / "request.json", canonical_json(request).encode())
    durable_write(work / "bindings.json", canonical_json(bindings).encode())
    durable_write(work / "context.json", canonical_json(context).encode())
    durable_write(work / "runner.py", Path(__file__).read_bytes())
    began = time.monotonic()
    deadline = began + SECONDS
    durable_write(
        work / "intent.json",
        canonical_json(
            {"request_digest": expected_digest, "began_at": began, "deadline": deadline}
        ).encode(),
    )
    env = {
        k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR") if k in os.environ
    }
    env.update(
        {
            "DOCKER_HOST": "unix://" + bindings["endpoint"],
            "DOCKER_CONFIG": str(work / "config"),
            "BUILDKIT_PROGRESS": "plain",
            "DOCKER_BUILDKIT": "1",
            "NO_COLOR": "1",
        }
    )
    image_id = None
    try:
        for step, template in enumerate(request["commands"]):
            if (
                _binary(bindings["cli"]) != request["binary"]
                or _endpoint(bindings["endpoint"]) != request["endpoint"]
            ):
                raise ValueError("build client/endpoint changed during original job")
            parts = []
            for argument in template:
                argument = argument.replace("{work}", str(work)).replace(
                    "{context}", str(context_root)
                )
                argument = argument.replace("{image_id}", image_id or "")
                parts.append(argument)
            argv = [
                bindings["cli"],
                "--config",
                str(work / "config"),
                "--host",
                "unix://" + bindings["endpoint"],
                *parts,
            ]
            durable_write(
                work / f"{step:02d}-intent.json",
                canonical_json(
                    {"request_digest": expected_digest, "step": step, "argv_digest": digest(argv)}
                ).encode(),
            )
            print(f"Image preparation command {step + 1}/{len(request['commands'])}", flush=True)
            log = work / f"{step:02d}.log"
            status = _run(argv, env=env, cwd=work, deadline=deadline, log=log)
            raw = log.read_bytes()
            durable_write(
                work / f"{step:02d}-result.json",
                canonical_json(
                    {
                        "step": step,
                        "exit_code": status,
                        "log_sha256": hashlib.sha256(raw).hexdigest(),
                        "log_bytes": len(raw),
                    }
                ).encode(),
            )
            if status != 0:
                raise ValueError("original image preparation command failed; retry forbidden")
            _validate(step, raw, request, bindings)
            if step == 5 and unique_json(raw.decode()).get("Id") != image_id:
                raise ValueError("final inspected image differs from original build ID")
            if step == 4:
                path = confined_file(work, "image.id")
                if path.stat().st_size > 128:
                    raise ValueError("build image ID exceeds envelope")
                image_id = path.read_text().strip()
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
                    raise ValueError("build did not supply a valid original image ID")
        result = {
            "schema": "utility-local-image-build-completion-v1",
            "request_digest": expected_digest,
            "image_id": image_id,
            "status": "candidate_image_built",
            "runtime_qualified": False,
            "daemon_cancellation_qualified": False,
            "disk_quota_enforced": False,
            "elapsed_seconds": time.monotonic() - began,
        }
        if time.monotonic() >= deadline:
            raise TimeoutError("original build deadline expired before completion")
        durable_write(work / "complete.json", canonical_json(result).encode())
        return result
    except BaseException:
        # Saved intents remain charged. No cancellation/absence assertion about
        # the daemon follows merely from client exit or loss of this owner.
        raise


def read_completion(work, *, expected_digest):
    """Validate required saved build proofs without any original/live scope."""
    work = checked_directory(work)
    result = _read(work, "complete.json")
    if digest(result) != expected_digest:
        raise ValueError("build completion differs from explicit pin")
    request, bindings = _read(work, "request.json"), _read(work, "bindings.json")
    context = _read(work, "context.json")
    if result["request_digest"] != digest(request) or request != _request(
        context,
        request["image_plan"],
        bindings,
        request["binary"],
        request["endpoint"],
        request["runner_digest"],
    ):
        raise ValueError("saved build request/bindings changed")
    code = confined_file(work, "runner.py")
    if (
        code.stat().st_size > 1024**2
        or hashlib.sha256(code.read_bytes()).hexdigest() != request["runner_digest"]
    ):
        raise ValueError("saved build source differs")
    intent = _read(work, "intent.json")
    if (
        intent["request_digest"] != digest(request)
        or intent["deadline"] - intent["began_at"] != SECONDS
    ):
        raise ValueError("original build intent changed")
    image_path = confined_file(work, "image.id")
    if image_path.stat().st_size > 128:
        raise ValueError("saved image ID exceeds envelope")
    image_id = image_path.read_text().strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) or image_id != result["image_id"]:
        raise ValueError("saved image ID differs from original completion")
    elapsed = result["elapsed_seconds"]
    if (
        type(elapsed) not in (int, float)
        or not math.isfinite(elapsed)
        or not 0 <= elapsed <= SECONDS
    ):
        raise ValueError("saved build elapsed time is invalid")
    expected = {
        "schema": "utility-local-image-build-completion-v1",
        "request_digest": digest(request),
        "image_id": image_id,
        "status": "candidate_image_built",
        "runtime_qualified": False,
        "daemon_cancellation_qualified": False,
        "disk_quota_enforced": False,
        "elapsed_seconds": elapsed,
    }
    if result != expected:
        raise ValueError("build completion cannot qualify a runtime or storage limit")
    for step, template in enumerate(request["commands"]):
        parts = [
            arg.replace("{work}", bindings["work"])
            .replace("{context}", bindings["context"])
            .replace("{image_id}", image_id)
            for arg in template
        ]
        argv = [
            bindings["cli"],
            "--config",
            bindings["work"] + "/config",
            "--host",
            "unix://" + bindings["endpoint"],
            *parts,
        ]
        event = _read(work, f"{step:02d}-intent.json")
        if event != {"request_digest": digest(request), "step": step, "argv_digest": digest(argv)}:
            raise ValueError("original build command intent changed")
        record = _read(work, f"{step:02d}-result.json")
        path = confined_file(work, f"{step:02d}.log")
        if path.stat().st_size > MAX_LOG:
            raise ValueError("saved build log exceeds envelope")
        raw = path.read_bytes()
        if record != {
            "step": step,
            "exit_code": 0,
            "log_sha256": hashlib.sha256(raw).hexdigest(),
            "log_bytes": len(raw),
        }:
            raise ValueError("saved build command result differs")
        _validate(step, raw, request, bindings)
        if step == 5 and unique_json(raw.decode()).get("Id") != image_id:
            raise ValueError("saved final image differs from original build ID")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("prepare")
    for name in ("context", "cli", "endpoint", "work", "output"):
        create.add_argument(name, type=Path)
    create.add_argument("--context-digest", required=True)
    run = commands.add_parser("execute")
    run.add_argument("bundle", type=Path)
    run.add_argument("--expected-digest", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.context,
            context_digest=args.context_digest,
            cli=args.cli,
            endpoint=args.endpoint,
            work=args.work,
            output=args.output,
        )
    else:
        result = execute(args.bundle, expected_digest=args.expected_digest)
    print(canonical_json({"digest": digest(result)}))


if __name__ == "__main__":
    main()
