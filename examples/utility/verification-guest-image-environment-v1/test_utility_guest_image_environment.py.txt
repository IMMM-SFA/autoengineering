"""Derivative image provenance and adverse controls; no actual Docker calls."""

import json
import shutil
import socket
import subprocess
import time

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import guest_image_environment as module
from examples.utility import guest_image_build as build
import test_utility_guest_image_build as parent

IID = "sha256:" + "4" * 64
SERVER = {"Os": "linux", "Arch": "arm64", "ApiVersion": "1.56"}


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    bundle, request, original_work, _, old_run = parent.prepared(tmp_path, monkeypatch)

    def source_run(argv, **kwargs):
        code = old_run(argv, **kwargs)
        if "version" in argv:
            kwargs["log"].write_text(json.dumps(SERVER))
        return code

    monkeypatch.setattr(build, "_run", source_run)
    original = build.execute(bundle, expected_digest=digest(request))
    output, work = tmp_path / "derivative", tmp_path / "derivative-work"
    q = module.prepare(
        original_work,
        completion_digest=digest(original),
        environment=tmp_path / "environment",
        output=output,
        work=work,
    )
    state = {
        "calls": [],
        "tag_status": 404,
        "derived": None,
        "source": module.read(original_work, "06.log"),
    }

    class API:
        def __init__(self, *a, **kw):
            pass

        def _request(self, method, path, **kwargs):
            assert method == "GET" and path.endswith("/json")
            assert 0 < kwargs["deadline"] - time.monotonic() <= 60
            return state["tag_status"], b"{}"

    monkeypatch.setattr(module, "GuestDaemonAPI", API)

    def run(argv, *, env, cwd, deadline, log):
        step = len(state["calls"])
        state["calls"].append((argv, dict(env)))
        if step == 0:
            value = SERVER
        elif step == 1:
            value = {
                "Name": "default",
                "Endpoints": {"docker": {"Host": "unix://" + str(tmp_path / "authored-endpoint")}},
            }
        elif step == 2:
            log.write_text("Driver: docker\nEndpoint: default\nPlatforms: linux/amd64\n")
            return 0
        elif step in (3, 5, 8):
            value = state["source"]
        elif step == 4:
            log.write_text("")
            return 0
        elif step == 6:
            (cwd / "image.id").write_text(IID + "\n")
            (cwd / "build-metadata.json").write_text(json.dumps({"containerimage.digest": IID}))
            log.write_text(
                "FROM "
                + module.recipe(q)[0]
                + "@"
                + q["source_image"]
                + "\nCOPY --from=frozen / /\nauthored build; no actual image\n"
            )
            return 0
        else:
            config = {
                "User": "1000:1000",
                "WorkingDir": "/work",
                "Entrypoint": [],
                "Cmd": list(module.BOOTSTRAP_COMMAND),
                "Env": [f"{k}={v}" for k, v in (*module.BASE_ENV, *module.ENVIRONMENT)],
                "Labels": module.recipe(q)[2],
            }
            value = state["derived"] or {
                "Id": IID,
                "Os": "linux",
                "Architecture": "amd64",
                "Config": config,
            }
        log.write_text(json.dumps(value))
        return 0

    monkeypatch.setattr(build, "_run", run)
    return output, q, work, state, run


def test_fixed_filesystem_copy_has_no_install_or_host_input(prepared, monkeypatch):
    bundle, q, work, state, _ = prepared
    monkeypatch.setenv("PRIVATE_CANARY", "not-a-client-input")
    monkeypatch.setenv("DOCKER_CONTEXT", "remote-context")
    result = module.execute(bundle, expected_digest=digest(q))
    assert result["image_id"] == IID and result["scientific_starts"] == 0
    assert len(state["calls"]) == 9
    alias, source, _ = module.recipe(q)
    assert source.startswith("FROM " + alias + " AS frozen\nFROM scratch\n")
    assert "RUN " not in source and source.count("COPY ") == 1
    assert "COPY --from=frozen / /\n" in source
    assert "PYTHON_VERSION" not in source and "GPG_KEY" not in source
    assert len(list((work / "context").iterdir())) == 2
    for argv, env in state["calls"]:
        assert "PRIVATE_CANARY" not in env and "DOCKER_CONTEXT" not in env
        assert "--push" not in argv and "--secret" not in argv and "--ssh" not in argv
        assert "pull" not in argv
    assert module.read_completion(work, expected_digest=digest(result)) == result
    with pytest.raises(ValueError, match="consumed"):
        module.execute(bundle, expected_digest=digest(q))


@pytest.mark.parametrize("step", range(9))
def test_each_failed_operation_is_consumed_without_retry(prepared, monkeypatch, step):
    bundle, q, work, state, original = prepared

    def fail(argv, **kwargs):
        number = len(state["calls"])
        result = original(argv, **kwargs)
        return 1 if number == step else result

    monkeypatch.setattr(build, "_run", fail)
    with pytest.raises(ValueError, match="consumed"):
        module.execute(bundle, expected_digest=digest(q))
    count = len(state["calls"])
    with pytest.raises(ValueError, match="consumed"):
        module.execute(bundle, expected_digest=digest(q))
    assert count == step + 1 == len(state["calls"])
    assert not (work / "complete.json").exists()


def test_existing_alias_is_never_overwritten(prepared):
    bundle, q, _, state, _ = prepared
    state["tag_status"] = 200
    with pytest.raises(ValueError, match="not absent"):
        module.execute(bundle, expected_digest=digest(q))
    assert len(state["calls"]) == 4


def test_foreign_source_refuses_before_tag(prepared):
    bundle, q, _, state, _ = prepared
    state["source"]["Id"] = "sha256:" + "8" * 64
    with pytest.raises(ValueError, match="source identity"):
        module.execute(bundle, expected_digest=digest(q))
    assert len(state["calls"]) == 4


def test_build_resolution_cannot_use_another_filesystem(prepared, monkeypatch):
    bundle, q, _, state, original = prepared

    def drift(argv, **kwargs):
        step = len(state["calls"])
        result = original(argv, **kwargs)
        if step == 6:
            path = kwargs["log"]
            path.write_text(path.read_text().replace(q["source_image"], "sha256:" + "9" * 64))
        return result

    monkeypatch.setattr(build, "_run", drift)
    with pytest.raises(ValueError, match="pinned source filesystem"):
        module.execute(bundle, expected_digest=digest(q))
    assert len(state["calls"]) == 7


@pytest.mark.parametrize(
    "problem", ["environment", "labels", "volumes", "command", "user", "health"]
)
def test_inherited_or_unapproved_final_configuration_refuses(prepared, problem):
    _, q, _, state, _ = prepared
    config = {
        "User": "1000:1000",
        "WorkingDir": "/work",
        "Entrypoint": [],
        "Cmd": list(module.BOOTSTRAP_COMMAND),
        "Env": [f"{k}={v}" for k, v in (*module.BASE_ENV, *module.ENVIRONMENT)],
        "Labels": module.recipe(q)[2],
    }
    if problem == "environment":
        config["Env"].append("PYTHON_VERSION=3.12.16")
    elif problem == "labels":
        config["Labels"] = {}
    elif problem == "volumes":
        config["Volumes"] = {"/host": {}}
    elif problem == "command":
        config["Cmd"] = ["arbitrary"]
    elif problem == "health":
        config["Healthcheck"] = {"Test": ["CMD", "arbitrary"]}
    else:
        config["User"] = "0"
    state["derived"] = {"Id": IID, "Os": "linux", "Architecture": "amd64", "Config": config}
    with pytest.raises(ValueError):
        module.execute(prepared[0], expected_digest=digest(q))
    assert len(state["calls"]) == 8


def test_relocated_reader_needs_no_original_service_or_clock(prepared, tmp_path, monkeypatch):
    bundle, q, work, _, _ = prepared
    result = module.execute(bundle, expected_digest=digest(q))
    moved = tmp_path / "moved"
    shutil.copytree(work, moved)
    shutil.rmtree(bundle)
    shutil.rmtree(work)

    def forbidden(*args, **kwargs):
        pytest.fail("live operation during saved replay")

    monkeypatch.setattr(build, "_binary", forbidden)
    monkeypatch.setattr(build, "_endpoint", forbidden)
    monkeypatch.setattr(build, "_run", forbidden)
    monkeypatch.setattr(module, "GuestDaemonAPI", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(time, "monotonic", forbidden)
    assert module.read_completion(moved, expected_digest=digest(result)) == result


@pytest.mark.parametrize(
    "name",
    [
        "Dockerfile",
        "runner.py",
        "build-helper.py.txt",
        "source-image.json",
        "07.log",
        "tag-absence.json",
    ],
)
def test_saved_metadata_corruption_refuses(prepared, name):
    bundle, q, work, _, _ = prepared
    result = module.execute(bundle, expected_digest=digest(q))
    (work / name).write_text("{}")
    with pytest.raises(ValueError):
        module.read_completion(work, expected_digest=digest(result))


@pytest.mark.parametrize(
    "name,limit",
    [
        ("runner.py", 1024**2),
        ("build-helper.py.txt", 1024**2),
        ("Dockerfile", 65536),
        ("image.id", 128),
    ],
)
def test_oversized_replay_inputs_refuse_before_unbounded_read(prepared, name, limit):
    bundle, q, work, _, _ = prepared
    result = module.execute(bundle, expected_digest=digest(q))
    (work / name).write_bytes(b"x" * (limit + 1))
    with pytest.raises(ValueError, match="exceeds envelope"):
        module.read_completion(work, expected_digest=digest(result))
