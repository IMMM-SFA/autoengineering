"""Saved synthetic boundary evidence remains inspectable without original paths."""

import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from scripts.verify_claude_policy_archive import FIELDS, archive, digest, inspect


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())


def fixture(root):
    root.mkdir()
    put(root, "code/probe.c", b"synthetic C source, never executed\n")
    observed = {}
    for name, nonce in (
        ("control", "claude-policy-control"), ("sandbox", "claude-policy-sandbox"),
        ("client-help", "claude-policy-help"), ("helper-proof", "claude-policy-helper"),
    ):
        identity = {"nonce": nonce, "pid": 99999, "pgid": 99999, "started": "synthetic"}
        job = {"keep_group_leader": True, "owner_lease": "pipe-eof-v1"}
        if name in ("control", "sandbox"):
            command = [str(root) + "/code/probe", *["synthetic-argument"] * 13]
            job["command"] = (
                command if name == "control"
                else ["/usr/bin/sandbox-exec", "-f", str(root) + "/canary.sb", *command]
            )
            output = {f: (0 if name == "control" and f.endswith("_denied") else 1) for f in FIELDS}
            observed[name] = output
            output = json.dumps(output).encode()
        elif name == "client-help":
            output = b"Usage: claude [options]\n"
            job["command"] = [
                "/usr/bin/sandbox-exec", "-f", str(root) + "/client.sb", "/pinned/claude",
                "--bare", "--tools=", "--setting-sources=", "--help",
            ]
            observed["actual_cli_help"] = {
                "status": "completed", "returncode": 0, "stopped": True, "help_returned": True,
            }
        else:
            output = b"synthetic authentication fixture\n"
            observed["synthetic_helper_bootstrap"] = {
                "status": "completed", "returncode": 0, "stopped": True,
                "expected_synthetic_output": True, "native_CLI_helper_hook_exercised": False,
            }
        watchdog = {"target": identity, "nonce": "watchdog-" + name}
        put(root, name + "/watchdog-job.json", watchdog)
        put(root, name + "/watchdog-result.json", {
            "nonce": watchdog["nonce"], "stopped": True, "reason": "group_stopped",
            "job_sha256": digest((root / name / "watchdog-job.json").read_bytes()),
        })
        put(root, name + "/intent.json", {"nonce": nonce})
        put(root, name + "/process.json", identity)
        put(root, name + "/job.json", job)
        put(root, name + "/stdin.bin", b"")
        put(root, name + "/stdout.bin", output)
        put(root, name + "/stderr.bin", b"")
        completion = {
            "schema_version": "1.0", "status": "completed", "returncode": 0,
            "stopped": True, "truncated": False, "identity": identity,
        }
        for field, suffix in (("job", ".json"), ("stdin", ".bin"), ("stdout", ".bin"), ("stderr", ".bin")):
            data = (root / name / (field + suffix)).read_bytes()
            completion[field + "_sha256"] = digest(data)
            if field in ("stdout", "stderr"):
                completion[field + "_bytes"] = len(data)
        put(root, name + "/completion.json", completion)
    put(root, "report.json", {
        "version": "claude-policy-probe-1.3", "status": "passed_limited_scope",
        "production_admission": False, "provider_calls": 0, "scientific_calls": 0,
        "runtime": {"platform": "darwin"}, "unqualified": ["actual_inference"],
        "source_identity": "synthetic-source", "observed": observed,
        "raw_source_sha256": digest((root / "code/probe.c").read_bytes()),
        "inventory": {"executable": "/pinned/claude"},
    })
    return root


def test_relocated_reader_never_launches_or_opens_original(tmp_path, monkeypatch):
    original = fixture(tmp_path / "original")
    destination = tmp_path / "saved"
    pin = archive(original, destination)
    shutil.rmtree(original)

    def denied(*args, **kwargs):
        raise AssertionError("unexpected process or socket")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    old_open = Path.open

    def guarded(path, *args, **kwargs):
        assert not path.is_relative_to(original), "original access"
        return old_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    result = inspect(destination, pin)
    assert result["status"] == "verified_saved_limited_scope"
    assert result["production_admission"] is False
    assert result["live_process_state_checked"] is False


@pytest.mark.parametrize("name", ["control/stdout.bin", "helper-proof/stdout.bin", "client-help/job.json"])
def test_changed_bytes_refuse(tmp_path, name):
    destination = tmp_path / "saved"
    pin = archive(fixture(tmp_path / "original"), destination)
    (destination / name).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest|size"):
        inspect(destination, pin)


@pytest.mark.parametrize("kind", ["control", "report", "stop", "help", "helper", "sandbox"])
def test_semantic_contradictions_refuse_even_with_new_outer_index(tmp_path, kind):
    original = fixture(tmp_path / "original")
    if kind == "control":
        value = json.loads((original / "control/stdout.bin").read_text())
        value["private_read_denied"] = 1
        put(original, "control/stdout.bin", value)
        # Rebind receipt too, so rejection checks the fixed syscall contract.
        completion = json.loads((original / "control/completion.json").read_text())
        data = (original / "control/stdout.bin").read_bytes()
        completion.update(stdout_sha256=digest(data), stdout_bytes=len(data))
        put(original, "control/completion.json", completion)
    elif kind == "report":
        value = json.loads((original / "report.json").read_text())
        value["production_admission"] = True
        put(original, "report.json", value)
    elif kind == "stop":
        value = json.loads((original / "helper-proof/watchdog-result.json").read_text())
        value["stopped"] = False
        put(original, "helper-proof/watchdog-result.json", value)
    elif kind == "sandbox":
        value = json.loads((original / "sandbox/job.json").read_text())
        value["command"] = value["command"][3:]
        put(original, "sandbox/job.json", value)
    else:
        name = "client-help" if kind == "help" else "helper-proof"
        put(original, name + "/stdout.bin", b"unexpected output")
        completion = json.loads((original / name / "completion.json").read_text())
        completion.update(stdout_sha256=digest(b"unexpected output"), stdout_bytes=17)
        put(original, name + "/completion.json", completion)
    destination = tmp_path / "saved"
    pin = archive(original, destination)
    with pytest.raises(ValueError):
        inspect(destination, pin)


def test_links_are_described_and_not_followed(tmp_path):
    original = fixture(tmp_path / "original")
    (original / "link").symlink_to(tmp_path / "absent")
    destination = tmp_path / "saved"
    pin = archive(original, destination)
    assert not (destination / "link").exists()
    index = json.loads((destination / "archive.json").read_text())
    assert index["excluded_nodes"]["link"]["type"] == "symlink"
    assert inspect(destination, pin)["production_admission"] is False


def test_wrong_index_pin_and_nested_archive_refuse(tmp_path):
    original = fixture(tmp_path / "original")
    with pytest.raises(ValueError, match="within"):
        archive(original, original / "recursive")
    destination = tmp_path / "saved"
    archive(original, destination)
    with pytest.raises(ValueError, match="index digest"):
        inspect(destination, hashlib.sha256(b"wrong").hexdigest())
