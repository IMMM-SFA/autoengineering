"""Build a fixed derivative with explicit environment and provenance labels.

The filesystem comes only from the already built, digest-pinned local image.
The recipe has no RUN, download, package install, host file COPY or model action.
Existing image recipes, wheels, receipt policies and failed attempts stay intact.
"""

from __future__ import annotations

import argparse
import hashlib
import math
from pathlib import Path
import re
import time
from uuid import uuid4

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.guest_daemon import GuestDaemonAPI
from autoengineering.utility.guest_observations import BASE_ENV, PURPOSE, _environment
from autoengineering.utility.guest_receipts import BOOTSTRAP_COMMAND, ENVIRONMENT
from examples.utility import guest_image_build as build
from examples.utility.inference_environment import verify_inputs

SECONDS = 1200


def save(root, name, value):
    durable_write(root / name, canonical_json(value).encode())


def _bytes(root, name, limit=1024**2):
    path = confined_file(root, name)
    if path.stat().st_size > limit:
        raise ValueError("image environment metadata exceeds envelope")
    with path.open("rb") as stream:
        value = stream.read(limit + 1)
    if len(value) > limit:
        raise ValueError("image environment metadata exceeds envelope")
    return value


def read(root, name):
    return unique_json(_bytes(root, name).decode())


def recipe(request):
    if not re.fullmatch(r"[0-9a-f]{32}", request["nonce"]):
        raise ValueError("image environment nonce differs")
    # The unique localhost tag is checked absent before tagging, then inspected
    # against the original image ID. It is never pushed or reused for a retry.
    alias = "localhost/ae-guest-source-" + request["nonce"] + ":frozen"
    labels = {
        "org.autoengineering.purpose": PURPOSE,
        "org.autoengineering.environment": request["environment_digest"],
        "org.autoengineering.wheel": request["wheel_digest"],
        "org.autoengineering.source-image": request["source_image"],
        "org.autoengineering.environment-recipe": "scratch-final-v1",
    }
    source = f"FROM {alias} AS frozen\nFROM scratch\nCOPY --from=frozen / /\n"
    source += "".join(
        f"ENV {key}={canonical_json(value)}\n" for key, value in (*BASE_ENV, *ENVIRONMENT)
    )
    source += "".join(f"LABEL {key}={canonical_json(value)}\n" for key, value in labels.items())
    source += (
        "WORKDIR /work\nUSER 1000:1000\nENTRYPOINT []\nCMD "
        + canonical_json(list(BOOTSTRAP_COMMAND))
        + "\n"
    )
    return alias, source, labels


def commands(request):
    alias, _, _ = recipe(request)
    return [
        ["version", "--format", "{{json .Server}}"],
        ["context", "inspect", "default", "--format", "{{json .}}"],
        ["buildx", "inspect", "default"],
        ["image", "inspect", request["source_image"], "--format", "{{json .}}"],
        ["image", "tag", request["source_image"], alias],
        ["image", "inspect", alias, "--format", "{{json .}}"],
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
            "{work}/context",
        ],
        ["image", "inspect", "{image_id}", "--format", "{{json .}}"],
        ["image", "inspect", alias, "--format", "{{json .}}"],
    ]


def request_for(
    original,
    original_request,
    inputs,
    bindings,
    nonce,
    source,
    *,
    binary,
    plugin,
    endpoint,
    helper_sha256,
    source_inspect,
):
    if (
        original.get("schema") != "utility-local-image-build-completion-v1"
        or original.get("status") != "candidate_image_built"
        or original.get("request_digest") != digest(original_request)
        or not re.fullmatch(r"sha256:[0-9a-f]{64}", original["image_id"])
        or (source_inspect.get("Id"), source_inspect.get("Os"), source_inspect.get("Architecture"))
        != (original["image_id"], "linux", "amd64")
        or original_request["image_plan"]["environment_inputs_digest"] != inputs.digest
    ):
        raise ValueError("image environment original image/input provenance differs")
    request = {
        "schema": "utility-guest-image-environment-request-v1",
        "source_completion_digest": digest(original),
        "source_request_digest": digest(original_request),
        "source_image": original["image_id"],
        "environment_digest": inputs.digest,
        "wheel_digest": inputs.wheel.sha256,
        "nonce": nonce,
        "bindings_digest": digest(bindings),
        "binary": binary,
        "buildx": plugin,
        "endpoint": endpoint,
        "runner_sha256": source,
        "helper_sha256": helper_sha256,
        "source_inspect_digest": digest(source_inspect),
        "client_deadline_seconds": SECONDS,
        "per_command_log_bytes": build.MAX_LOG,
        "tag_operations": 1,
        "build_operations": 1,
        "pull_commands": 0,
        "install_commands": 0,
        "automatic_retries": 0,
        "scientific_starts": 0,
        "runtime_qualified": False,
        "disk_quota_enforced": False,
        "daemon_cancellation_qualified": False,
    }
    request["commands"] = commands(request)
    request["recipe_sha256"] = hashlib.sha256(recipe(request)[1].encode()).hexdigest()
    return request


def prepare(original_work, *, completion_digest, environment, output, work):
    original_work = checked_directory(original_work)
    original = build.read_completion(original_work, expected_digest=completion_digest)
    original_request, old = (
        read(original_work, "request.json"),
        read(original_work, "bindings.json"),
    )
    inputs = verify_inputs(
        environment, expected_digest=original_request["image_plan"]["environment_inputs_digest"]
    )
    output, work = Path(output).absolute(), Path(work).absolute()
    for path in (output, work):
        build.guest_image._public_directory(path.parent)
        if path.exists() or path.is_symlink():
            raise ValueError("image environment scopes must be absent")
    scopes = (output, work, original_work, checked_directory(environment))
    if any(
        a.is_relative_to(b) or b.is_relative_to(a)
        for i, a in enumerate(scopes[:2])
        for b in scopes[i + 1 :]
    ):
        raise ValueError("image environment scopes overlap")
    bindings = {
        "cli": old["cli"],
        "buildx": old["buildx"],
        "endpoint": old["endpoint"],
        "work": str(work),
    }
    source = Path(__file__).read_bytes()
    request = request_for(
        original,
        original_request,
        inputs,
        bindings,
        uuid4().hex,
        hashlib.sha256(source).hexdigest(),
        binary=build._binary(old["cli"]),
        plugin=build._binary(old["buildx"]),
        endpoint=build._endpoint(old["endpoint"]),
        helper_sha256=hashlib.sha256(Path(build.__file__).read_bytes()).hexdigest(),
        source_inspect=read(original_work, "06.log"),
    )
    output.mkdir(mode=0o700)
    for name, value in (
        ("request.json", request),
        ("bindings.json", bindings),
        ("source-completion.json", original),
        ("source-request.json", original_request),
        ("environment.json", inputs.to_dict()),
        ("source-image.json", read(original_work, "06.log")),
    ):
        save(output, name, value)
    durable_write(output / "runner.py", source)
    durable_write(output / "build-helper.py.txt", Path(build.__file__).read_bytes())
    durable_write(output / "Dockerfile", recipe(request)[1].encode())
    return request


def validate(step, raw, request, bindings):
    if step in (0, 1, 2):
        # Original helper's fixed server/context/builder semantics; this request
        # has the same ordering for those three read-only operations.
        build._validate(step, raw, {"context_check": True}, bindings)
    elif step in (3, 5, 8):
        value = unique_json(raw.decode())
        if (value.get("Id"), value.get("Os"), value.get("Architecture")) != (
            request["source_image"],
            "linux",
            "amd64",
        ):
            raise ValueError("image environment source identity differs")
    elif step == 6:
        text = raw.decode()
        alias = recipe(request)[0]
        if (
            f"FROM {alias}@{request['source_image']}" not in text
            or "COPY --from=frozen / /" not in text
        ):
            raise ValueError("derived build did not resolve the pinned source filesystem")
    elif step == 7:
        value = unique_json(raw.decode())
        config = value.get("Config", {})
        _, _, labels = recipe(request)
        if (
            value.get("Os") != "linux"
            or value.get("Architecture") != "amd64"
            or config.get("User") != "1000:1000"
            or config.get("WorkingDir") != "/work"
            or config.get("Cmd") != list(BOOTSTRAP_COMMAND)
            or config.get("Entrypoint") not in (None, [])
            or _environment(config.get("Env")) != dict((*BASE_ENV, *ENVIRONMENT))
            or config.get("Labels") != labels
            or config.get("Volumes") not in (None, {})
            or config.get("OnBuild") not in (None, [])
        ):
            raise ValueError("derived image environment, command or provenance differs")
        if config.get("Healthcheck") not in (None, {"Test": ["NONE"]}):
            raise ValueError("derived image has an unapproved health process")


def load(bundle, expected_digest, *, live):
    from examples.utility.inference_environment import InferenceEnvironmentInputs

    bundle = checked_directory(bundle)
    q, b = read(bundle, "request.json"), read(bundle, "bindings.json")
    inputs = InferenceEnvironmentInputs.from_dict(read(bundle, "environment.json"))
    original, original_request = (
        read(bundle, "source-completion.json"),
        read(bundle, "source-request.json"),
    )
    # The helper's fingerprint is read from the archived bytes during replay.
    helper = _bytes(bundle, "build-helper.py.txt")
    if digest(q) != expected_digest or hashlib.sha256(helper).hexdigest() != q["helper_sha256"]:
        raise ValueError("image environment request or helper changed")
    expected = request_for(
        original,
        original_request,
        inputs,
        b,
        q["nonce"],
        q["runner_sha256"],
        binary=q["binary"],
        plugin=q["buildx"],
        endpoint=q["endpoint"],
        helper_sha256=q["helper_sha256"],
        source_inspect=read(bundle, "source-image.json"),
    )
    if (
        q != expected
        or hashlib.sha256(_bytes(bundle, "runner.py")).hexdigest() != q["runner_sha256"]
        or _bytes(bundle, "Dockerfile", 65536).decode() != recipe(q)[1]
    ):
        raise ValueError("image environment sources or recipe changed")
    if live and (
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != q["runner_sha256"]
        or hashlib.sha256(Path(build.__file__).read_bytes()).hexdigest() != q["helper_sha256"]
    ):
        raise ValueError("image environment producer source changed")
    return bundle, q, b


def execute(bundle, *, expected_digest):
    bundle, q, b = load(bundle, expected_digest, live=True)
    work = Path(b["work"])
    build.guest_image._public_directory(work.parent)
    if work.exists() or work.is_symlink():
        raise ValueError("image environment attempt consumed; retry is forbidden")
    if (
        build._binary(b["cli"]) != q["binary"]
        or build._binary(b["buildx"]) != q["buildx"]
        or build._endpoint(b["endpoint"]) != q["endpoint"]
    ):
        raise ValueError("image environment client or endpoint changed")
    work.mkdir(mode=0o700)
    for name in ("config", "home", "context"):
        (work / name).mkdir(mode=0o700)
    durable_write(work / "config/config.json", b"{}")
    for name in (
        "request.json",
        "bindings.json",
        "source-completion.json",
        "source-request.json",
        "environment.json",
        "source-image.json",
        "runner.py",
        "build-helper.py.txt",
        "Dockerfile",
    ):
        path = confined_file(bundle, name)
        if path.stat().st_size > 1024**2:
            raise ValueError("image environment input metadata exceeds envelope")
        durable_write(work / name, path.read_bytes())
    durable_write(work / "context/Dockerfile", recipe(q)[1].encode())
    durable_write(work / "context/.dockerignore", b"**\n!Dockerfile\n!.dockerignore\n")
    build._copy_plugin(work, b["buildx"], q["buildx"])
    began = time.monotonic()
    deadline = began + SECONDS
    save(
        work,
        "intent.json",
        {"request_digest": expected_digest, "began_at": began, "deadline": deadline},
    )
    version = None
    image_id = None
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work / "home"),
        "DOCKER_CONFIG": str(work / "config"),
        "DOCKER_HOST": "unix://" + b["endpoint"],
        "BUILDKIT_PROGRESS": "plain",
        "DOCKER_BUILDKIT": "1",
        "NO_COLOR": "1",
    }
    for step, template in enumerate(q["commands"]):
        if (
            build._binary(b["cli"]) != q["binary"]
            or build._binary(b["buildx"]) != q["buildx"]
            or build._endpoint(b["endpoint"]) != q["endpoint"]
        ):
            raise ValueError("image environment client changed during original job")
        build._verify_plugin(work, q["buildx"])
        if step == 4:
            api = GuestDaemonAPI(
                b["endpoint"], api_version=version["ApiVersion"], server_digest=digest(version)
            )
            alias = recipe(q)[0]
            status, _ = api._request(
                "GET", f"/images/{alias}/json", deadline=min(deadline, time.monotonic() + 10)
            )
            if status != 404:
                raise ValueError("image environment local tag is not absent")
            save(work, "tag-absence.json", {"alias": alias, "status": status})
        parts = [
            part.replace("{work}", str(work)).replace("{image_id}", image_id or "")
            for part in template
        ]
        argv = [
            b["cli"],
            "--config",
            str(work / "config"),
            "--host",
            "unix://" + b["endpoint"],
            *parts,
        ]
        save(
            work,
            f"{step:02}-intent.json",
            {"argv_digest": digest(argv), "request_digest": expected_digest},
        )
        code = build._run(argv, env=env, cwd=work, deadline=deadline, log=work / f"{step:02}.log")
        save(work, f"{step:02}-result.json", {"exit_code": code})
        if code != 0:
            raise ValueError("image environment command did not complete; attempt consumed")
        raw = confined_file(work, f"{step:02}.log").read_bytes()
        validate(step, raw, q, b)
        if step == 0:
            version = unique_json(raw.decode())
        if step == 6:
            image_id = _bytes(work, "image.id", 128).decode().strip()
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
                raise ValueError("derived image identity is absent")
    final = read(work, "07.log")
    if (
        final["Id"] != image_id
        or read(work, "build-metadata.json").get("containerimage.digest") != image_id
    ):
        raise ValueError("derived image metadata differs")
    result = {
        "schema": "utility-guest-image-environment-completion-v1",
        "request_digest": expected_digest,
        "source_image": q["source_image"],
        "image_id": image_id,
        "elapsed_seconds": time.monotonic() - began,
        "runtime_qualified": False,
        "scientific_starts": 0,
        "disk_quota_enforced": False,
        "daemon_cancellation_qualified": False,
    }
    if result["elapsed_seconds"] > SECONDS:
        raise ValueError("image environment original deadline exceeded")
    save(work, "complete.json", result)
    return result


def read_completion(work, *, expected_digest):
    work = checked_directory(work)
    done = read(work, "complete.json")
    if digest(done) != expected_digest:
        raise ValueError("derived image completion differs from explicit pin")
    _, q, b = load(work, done["request_digest"], live=False)
    intent = read(work, "intent.json")
    if intent["request_digest"] != digest(q) or intent["deadline"] - intent["began_at"] != SECONDS:
        raise ValueError("derived image original allowance changed")
    image_id = _bytes(work, "image.id", 128).decode().strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("derived image saved identity differs")
    for step, template in enumerate(q["commands"]):
        parts = [
            part.replace("{work}", b["work"]).replace("{image_id}", image_id) for part in template
        ]
        argv = [
            b["cli"],
            "--config",
            str(Path(b["work"]) / "config"),
            "--host",
            "unix://" + b["endpoint"],
            *parts,
        ]
        if read(work, f"{step:02}-intent.json") != {
            "argv_digest": digest(argv),
            "request_digest": digest(q),
        } or read(work, f"{step:02}-result.json") != {"exit_code": 0}:
            raise ValueError("derived image original client changed")
        path = confined_file(work, f"{step:02}.log")
        if path.stat().st_size > build.MAX_LOG:
            raise ValueError("derived image log exceeds envelope")
        validate(step, path.read_bytes(), q, b)
    if (
        read(work, "tag-absence.json") != {"alias": recipe(q)[0], "status": 404}
        or read(work, "07.log")["Id"] != image_id
        or read(work, "build-metadata.json").get("containerimage.digest") != image_id
    ):
        raise ValueError("derived image identity/tag proof changed")
    elapsed = done["elapsed_seconds"]
    if (
        type(elapsed) not in (int, float)
        or not math.isfinite(elapsed)
        or not 0 <= elapsed <= SECONDS
        or done
        != {
            "schema": "utility-guest-image-environment-completion-v1",
            "request_digest": digest(q),
            "source_image": q["source_image"],
            "image_id": image_id,
            "elapsed_seconds": elapsed,
            "runtime_qualified": False,
            "scientific_starts": 0,
            "disk_quota_enforced": False,
            "daemon_cancellation_qualified": False,
        }
    ):
        raise ValueError("derived image completion cannot grant runtime admission")
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    for name in ("original_work", "environment", "output", "work"):
        prep.add_argument(name, type=Path)
    prep.add_argument("--completion-digest", required=True)
    for command in ("execute", "verify"):
        p = sub.add_parser(command)
        p.add_argument("path", type=Path)
        p.add_argument("--expected-digest", required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(
            args.original_work,
            completion_digest=args.completion_digest,
            environment=args.environment,
            output=args.output,
            work=args.work,
        )
    elif args.command == "execute":
        result = execute(args.path, expected_digest=args.expected_digest)
    else:
        result = read_completion(args.path, expected_digest=args.expected_digest)
    print(canonical_json({"digest": digest(result), "schema": result["schema"]}))


if __name__ == "__main__":
    main()
