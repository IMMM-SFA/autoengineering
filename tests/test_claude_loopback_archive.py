"""Offline checks of saved native CLI bytes from the authored local peer."""

import json
from pathlib import Path
import shutil
import socket
import subprocess

import pytest

from scripts.verify_claude_loopback_archive import inspect
from scripts.verify_claude_policy_archive import digest

ARCHIVE = Path(__file__).parents[1] / "examples/utility/development/claude-loopback-v7"
PIN = "e558989c33097a7547cd1f8025a2aa5867ace6365c6db859137c4c6a2813f3eb"


def repin(root, changed):
    index = json.loads((root / "archive.json").read_text())
    for name in changed:
        data = (root / name).read_bytes()
        index["files"][name].update(sha256=digest(data), size_bytes=len(data))
    index["total_bytes"] = sum(value["size_bytes"] for value in index["files"].values())
    data = json.dumps(index).encode()
    (root / "archive.json").write_bytes(data)
    return digest(data)


def test_saved_native_roundtrip_reads_without_original_or_processes(tmp_path, monkeypatch):
    root = tmp_path / "saved"
    shutil.copytree(ARCHIVE, root)
    original = Path(json.loads((root / "archive.json").read_text())["original_root"])
    old_open = Path.open

    def guarded(path, *args, **kwargs):
        assert not path.is_relative_to(original), "original access"
        return old_open(path, *args, **kwargs)

    def denied(*args, **kwargs):
        raise AssertionError("unexpected process/network access")

    monkeypatch.setattr(Path, "open", guarded)
    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(socket, "socket", denied)
    value = inspect(root, PIN)
    assert value["status"] == "verified_saved_synthetic_roundtrip"
    assert value["production_admission"] is False and value["provider_calls"] == 0
    assert value["live_process_state_checked"] is False
    assert value["billed_cost_usd"] is None
    assert "fixture" in value["usage_and_estimated_cost_basis"]


@pytest.mark.parametrize("case", ["bytes", "auth", "model", "helper", "stop", "report", "request"])
def test_saved_roundtrip_contradictions_refuse(tmp_path, case):
    root = tmp_path / "saved"
    shutil.copytree(ARCHIVE, root)
    if case == "bytes":
        (root / "native/stdout.bin").write_bytes(b"tampered")
        pin = PIN
    else:
        name = {
            "auth": "report.json", "model": "request-1.json",
            "helper": "auth/helper", "stop": "native/watchdog-result.json",
            "report": "report.json", "request": "report.json",
        }[case]
        path = root / name
        if case == "helper":
            path.write_text("changed helper code")
        else:
            value = json.loads(path.read_text())
            if case == "auth":
                value["requests"][0]["synthetic_auth_matched"] = False
            elif case == "model":
                value["model"] = "different-model"
            elif case == "stop":
                value["stopped"] = False
            elif case == "report":
                value["production_admission"] = True
            else:
                value["requests"] = []
            path.write_text(json.dumps(value))
        pin = repin(root, [name])
    with pytest.raises(ValueError):
        inspect(root, pin)
