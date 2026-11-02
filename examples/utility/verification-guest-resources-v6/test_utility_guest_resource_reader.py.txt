"""Saved diagnostic replay and corruption controls using authored receipts."""

from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess
import time

import pytest

from autoengineering.campaign.serialization import digest
from autoengineering.utility.inference_guest import LIMITS
from examples.utility import guest_resource_reader as reader, guest_resource_runner as runner
from examples.utility import guest_resources as policy
import test_utility_guest_resources as fixture


@pytest.fixture(params=policy.FIXED_IMAGES)
def image_id(request):
    return request.param


@pytest.fixture
def archive(tmp_path, image_id):
    tmp_path.chmod(0o700)
    (tmp_path / "producer-sources").mkdir(mode=0o700)
    source_pins = runner.sources()
    for name in source_pins:
        (tmp_path / "producer-sources" / (name + ".txt")).write_bytes(
            Path(runner.__file__).with_name(name).read_bytes()
        )
    bindings = {
        "work": "/original/work",
        "cli": "/original/docker",
        "endpoint": "/original/daemon.sock",
        "canaries": {},
    }
    request = {
        "schema": "utility-guest-resource-request-v1",
        "cases": [],
        "sources": source_pins,
        "daemon": {"server_digest": digest({"authored": True})},
        "active_seconds": 60,
        "cleanup_seconds": 10,
        "creations_reserved": 6,
        "starts_reserved": 6,
        "automatic_retries": 0,
        "scientific_starts": 0,
        "runtime_qualified": False,
        "profile": {
            "schema": "utility-frozen-guest-profile-v1",
            "environment_inputs_digest": "0" * 64,
            "lock_digest": "1" * 64,
            "wheel_digest": "2" * 64,
            "wheel_python_sources_digest": "3" * 64,
            "image_id": image_id,
            "limits_digest": digest(dict(LIMITS)),
            "boundary": "unqualified-candidate",
            "python": {
                "schema": "utility-guest-python-identity-v1",
                "system": "Linux",
                "architecture": "x86_64",
                "implementation": "CPython",
                "version": "3.12.13",
                "build_digest": policy.probe.PYTHON_BUILD,
            },
        },
    }
    if policy.image_labels(image_id):
        labels = policy.image_labels(image_id)
        request["profile"]["environment_inputs_digest"] = labels["org.autoengineering.environment"]
        request["profile"]["wheel_digest"] = labels["org.autoengineering.wheel"]
    cases = []
    for index, mode in enumerate(policy.probe.MODES):
        nonce, cid = f"{index + 1:032x}", f"{index + 1:064x}"
        value, lines, kwargs = fixture.authored(mode, image_id=image_id)
        value = json.loads(
            json.dumps(value).replace(fixture.NONCE, nonce).replace(fixture.CID, cid)
        )
        lines = json.loads(json.dumps(lines).replace(fixture.NONCE, nonce))
        canary = fixture.CANARY.replace(fixture.NONCE, nonce) if kwargs else None
        if canary:
            bindings["canaries"][nonce] = canary
        config = policy.configuration(mode, nonce, canary=canary, image_id=image_id)
        request["cases"].append(
            {"mode": mode, "nonce": nonce, "configuration_digest": digest(config)}
        )
        cases.append((mode, nonce, cid, value, lines, canary))
    request["bindings_digest"] = digest(bindings)
    runner.save(tmp_path, "request.json", request)
    runner.save(tmp_path, "bindings.json", bindings)
    results = []
    for mode, nonce, cid, value, lines, canary in cases:
        root = tmp_path / mode
        root.mkdir(mode=0o700)
        before = deepcopy(value)
        before["State"].update(
            Status="created",
            OOMKilled=False,
            ExitCode=0,
            StartedAt="0001-01-01T00:00:00Z",
            FinishedAt="0001-01-01T00:00:00Z",
        )
        raw = fixture.encoded(lines)
        (root / "output.log").write_bytes(raw)
        observation = policy.verify_terminal(
            value, raw, mode, nonce, cid=cid, canary=canary, image_id=image_id
        )
        cleanup = {
            "container_id": cid,
            "absent": True,
            "nonce": nonce,
            "delete_attempts": 1,
            "owner_loss_qualified": False,
        }
        result = {"observation": observation, "cleanup": cleanup, "elapsed_seconds": 6.5}
        original = Path(bindings["work"])
        argv = [
            bindings["cli"],
            "--config",
            str(original / "config"),
            "--host",
            "unix://" + bindings["endpoint"],
            "start",
            "--attach",
            cid,
        ]
        documents = {
            "intent.json": {
                "request_digest": digest(request),
                "began_at": 100,
                "deadline": 160,
                "creations_reserved": 1,
                "starts_reserved": 1,
            },
            "create-intent.json": {
                "configuration_digest": request["cases"][len(results)]["configuration_digest"],
                "nonce": nonce,
            },
            "created.json": {"Id": cid},
            "before.json": before,
            "start-intent.json": {"container_id": cid, "nonce": nonce, "starts": 1},
            "watchdog-ready.json": {"request_digest": digest(request), "pid": 1234},
            "server.json": {"authored": True},
            "image.json": {
                "Id": image_id,
                "Os": "linux",
                "Architecture": "amd64",
                "Config": {
                    "Labels": policy.image_labels(image_id),
                    "Env": [f"{k}={v}" for k, v in (*policy.BASE_ENV, *policy.ENVIRONMENT)],
                },
            },
            "terminal.json": value,
            "observation.json": observation,
            "client.json": {
                "exit_code": 137 if mode == "memory_limit" else 0,
                "argv_digest": digest(argv),
            },
            "watchdog-trigger.json": {"reason": "owner_pipe_closed", "at": 106},
            "cleanup-intent.json": {"deadline": 116, "nonce": nonce},
            "delete-intent.json": {"container_id": cid, "nonce": nonce},
            "cleanup.json": cleanup,
            "complete.json": result,
        }
        for name, document in documents.items():
            runner.save(root, name, document)
        results.append(result)
    complete = {
        "schema": "utility-guest-resource-completion-v1",
        "request_digest": digest(request),
        "cases": results,
        "physical_container_starts": 6,
        "scientific_starts": 0,
        "runtime_qualified": False,
        "owner_loss_qualified": False,
    }
    runner.save(tmp_path, "complete.json", complete)
    return tmp_path, complete


def test_replay_uses_only_saved_metadata(archive, monkeypatch):
    root, complete = archive
    for parent, name in (
        (socket, "socket"),
        (subprocess, "Popen"),
        (time, "monotonic"),
        (policy, "worker_source"),
    ):
        monkeypatch.setattr(
            parent, name, lambda *a, **kw: pytest.fail("live operation during replay")
        )
    assert reader.read_completion(root, expected_digest=digest(complete)) == complete


@pytest.mark.parametrize(
    "name,field,value",
    [
        ("start-intent.json", "starts", 2),
        ("cleanup.json", "absent", False),
        ("created.json", "Id", "f" * 64),
        ("watchdog-ready.json", "pid", True),
        ("cleanup-intent.json", "deadline", 180),
        ("intent.json", "deadline", 180),
        ("watchdog-trigger.json", "reason", "deadline"),
        ("delete-intent.json", "container_id", "f" * 64),
    ],
)
def test_corrupt_original_receipts_refuse(archive, name, field, value):
    root, complete = archive
    path = root / "memory_limit" / name
    document = json.loads(path.read_text())
    document[field] = value
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        reader.read_completion(root, expected_digest=digest(complete))


def test_archived_source_drift_refuses(archive):
    root, complete = archive
    path = root / "producer-sources/guest_resource_runner.py.txt"
    path.write_text(path.read_text() + "# changed\n")
    with pytest.raises(ValueError, match="source changed"):
        reader.read_completion(root, expected_digest=digest(complete))


def test_symlinked_output_refuses(archive):
    root, complete = archive
    path = root / "memory_limit/output.log"
    path.rename(root / "original.log")
    path.symlink_to(root / "original.log")
    with pytest.raises(ValueError):
        reader.read_completion(root, expected_digest=digest(complete))


def test_uncertain_cleanup_cannot_complete(archive):
    root, complete = archive
    (root / "memory_limit/cleanup-unknown.json").write_text("{}")
    with pytest.raises(ValueError, match="uncertain"):
        reader.read_completion(root, expected_digest=digest(complete))


def test_explicit_completion_pin_is_required(archive):
    root, _ = archive
    with pytest.raises(ValueError, match="explicit pin"):
        reader.read_completion(root, expected_digest="0" * 64)
