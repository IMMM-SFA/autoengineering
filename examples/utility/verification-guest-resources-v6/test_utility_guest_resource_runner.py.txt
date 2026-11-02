"""Owned diagnostic lifecycle tests with authored API and process outcomes."""

from copy import deepcopy
import json
import os

import pytest

from examples.utility import guest_resource_runner as runner
from examples.utility import guest_resources as policy
import test_utility_guest_resources as fixture


@pytest.fixture
def cleanup_state(tmp_path):
    tmp_path.chmod(0o700)
    value, _, _ = fixture.authored("memory_limit")
    state = {"value": value, "calls": [], "unknown_delete": False}

    class API:
        def _request(self, method, path, **kwargs):
            state["calls"].append((method, path))
            if method == "DELETE":
                if state["unknown_delete"]:
                    raise OSError("authored lost acknowledgment")
                state["value"] = None
                return 204, b""
            if state["value"] is None:
                return 404, b"{}"
            return 200, json.dumps(state["value"]).encode()

    runner.save(tmp_path, "created.json", {"Id": fixture.CID})
    return tmp_path, API(), state


def clean(root, api):
    return runner.cleanup(
        api, {"mode": "memory_limit", "nonce": fixture.NONCE}, root, canary=None, deadline=1.0
    )


def test_cleanup_deletes_only_owned_container_then_proves_absence(cleanup_state):
    root, api, state = cleanup_state
    assert clean(root, api)["absent"] is True
    assert [method for method, _ in state["calls"]] == ["GET", "DELETE", "GET"]
    assert runner.read(root, "delete-intent.json")["container_id"] == fixture.CID


def test_unknown_delete_is_never_reissued(cleanup_state):
    root, api, state = cleanup_state
    state["unknown_delete"] = True
    with pytest.raises(OSError):
        clean(root, api)
    calls = list(state["calls"])
    with pytest.raises(FileExistsError):
        clean(root, api)
    assert calls == state["calls"]
    assert not (root / "cleanup.json").exists()


def test_wrong_owner_blocks_deletion(cleanup_state):
    root, api, state = cleanup_state
    state["value"]["Name"] = "/someone-else"
    with pytest.raises(ValueError, match="identity"):
        clean(root, api)
    assert all(method != "DELETE" for method, _ in state["calls"])


def test_changed_cid_blocks_deletion_before_mutation(cleanup_state):
    root, api, state = cleanup_state
    state["value"]["Id"] = "c" * 64
    with pytest.raises(ValueError, match="original container ID"):
        clean(root, api)
    assert all(method != "DELETE" for method, _ in state["calls"])


def test_absence_after_unknown_creation_cannot_complete(cleanup_state):
    root, api, state = cleanup_state
    (root / "created.json").unlink()
    state["value"] = None
    with pytest.raises((ValueError, FileNotFoundError)):
        clean(root, api)
    assert not (root / "cleanup.json").exists()


@pytest.mark.parametrize("mode", policy.probe.MODES)
@pytest.mark.parametrize("image_id", policy.FIXED_IMAGES)
def test_case_one_start_and_original_terminal_cleanup(tmp_path, monkeypatch, mode, image_id):
    tmp_path.chmod(0o700)
    value, lines, kwargs = fixture.authored(mode, image_id=image_id)
    state = {"started": False, "deleted": False, "calls": []}
    before = deepcopy(value)
    before["State"].update(
        Status="created",
        OOMKilled=False,
        ExitCode=0,
        StartedAt="0001-01-01T00:00:00Z",
        FinishedAt="0001-01-01T00:00:00Z",
    )

    class API:
        def _json(self, method, path, payload=None, **kw):
            state["calls"].append((method, path))
            if path == "/version":
                return {"authored": True}
            if path.startswith("/images/"):
                return {
                    "Id": image_id,
                    "Os": "linux",
                    "Architecture": "amd64",
                    "Config": {
                        "Labels": policy.image_labels(image_id),
                        "Env": [f"{k}={v}" for k, v in (*policy.BASE_ENV, *policy.ENVIRONMENT)],
                    },
                }
            assert payload == policy.configuration(mode, fixture.NONCE, image_id=image_id, **kwargs)
            assert (tmp_path / mode / "create-intent.json").exists()
            return {"Id": fixture.CID}

        def _request(self, method, path, **kw):
            state["calls"].append((method, path))
            if method == "DELETE":
                assert (tmp_path / mode / "delete-intent.json").exists()
                state["deleted"] = True
                return 204, b""
            if state["deleted"]:
                return 404, b"{}"
            return 200, json.dumps(value if state["started"] else before).encode()

    api = API()
    monkeypatch.setattr(runner, "api_for", lambda *a: api)

    class Child:
        pid = 12345

        def __init__(self, *a, **kw):
            assert "watchdog" in a[0]
            os.write(kw["pass_fds"][1], b"R")

        def wait(self, **kw):
            runner.cleanup(
                api,
                {"mode": mode, "nonce": fixture.NONCE},
                tmp_path / mode,
                canary=kwargs.get("canary"),
                deadline=1.0,
                image_id=image_id,
            )
            return 0

    monkeypatch.setattr(runner.subprocess, "Popen", Child)

    def launch(argv, **kw):
        assert argv[-3:] == ["start", "--attach", fixture.CID]
        assert (tmp_path / mode / "start-intent.json").exists()
        state["started"] = True
        kw["log"].write_bytes(fixture.encoded(lines))
        return 137 if mode == "memory_limit" else 0

    monkeypatch.setattr(runner.build, "_run", launch)
    case = {"mode": mode, "nonce": fixture.NONCE}
    request = {
        "cases": [case],
        "profile": {"image_id": image_id},
        "daemon": {"server_digest": runner.digest({"authored": True})},
    }
    bindings = {
        "canaries": {fixture.NONCE: fixture.CANARY} if kwargs else {},
        "cli": "/authored/docker",
        "endpoint": "/authored/local.sock",
    }
    result = runner.run_case(tmp_path, request, bindings, tmp_path, 0)
    assert result["cleanup"]["absent"] is True
    assert result["observation"]["runtime_qualified"] is False
    assert sum(method == "POST" for method, _ in state["calls"]) == 1
    assert sum(method == "DELETE" for method, _ in state["calls"]) == 1


def test_no_request_can_run_twice(tmp_path, monkeypatch):
    monkeypatch.setattr(
        runner,
        "load",
        lambda *a: (
            tmp_path,
            {"binary": {}, "endpoint": {}},
            {"work": str(tmp_path), "cli": "x", "endpoint": "y"},
        ),
    )
    monkeypatch.setattr(runner.build, "_binary", lambda path: {})
    monkeypatch.setattr(runner.build, "_endpoint", lambda path: {})
    monkeypatch.setattr(runner, "run_case", lambda *a: pytest.fail("attempt repeated"))
    with pytest.raises(ValueError, match="consumed"):
        runner.execute(tmp_path, expected_digest="a" * 64)


def test_unapproved_image_inheritance_refuses_before_creation(tmp_path, monkeypatch):
    calls = []

    class API:
        def _json(self, method, path, **kwargs):
            calls.append((method, path))
            assert method == "GET"
            if path == "/version":
                return {"authored": True}
            return {
                "Id": policy.DERIVATIVE_IMAGE,
                "Os": "linux",
                "Architecture": "amd64",
                "Config": {
                    "Labels": policy.image_labels(policy.DERIVATIVE_IMAGE),
                    "Env": ["TOKEN=authored-canary"],
                },
            }

    monkeypatch.setattr(runner, "api_for", lambda *a: API())
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *a, **kw: pytest.fail("watchdog launched after bad preflight"),
    )
    request = {
        "cases": [{"mode": "memory_limit", "nonce": fixture.NONCE}],
        "profile": {"image_id": policy.DERIVATIVE_IMAGE},
        "daemon": {"server_digest": runner.digest({"authored": True})},
    }
    with pytest.raises(ValueError, match="inherited"):
        runner.run_case(tmp_path, request, {"canaries": {}}, tmp_path, 0)
    assert len(calls) == 2 and not (tmp_path / "memory_limit/create-intent.json").exists()
