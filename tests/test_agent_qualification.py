"""Pinned qualification reconstruction with synthetic evidence, without Docker."""

from dataclasses import asdict
import hashlib
import json
import platform

import pytest

from autoengineering.agents.containers import ContainerRuntime, boundary_source_identity
from autoengineering.agents.qualification import CHECKS, verify_qualification
from autoengineering.campaign.serialization import canonical_json, digest


def put(root, name, value):
    raw = canonical_json(value).encode()
    (root / name).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def evidence(tmp_path):
    tmp_path.chmod(0o700)
    runtime = ContainerRuntime(
        "sha256:" + "a" * 64,
        "python@sha256:" + "b" * 64,
        "arm64",
        "unix:///private/tmp/test.sock",
        "/usr/local/bin/docker",
    )
    limits = {"cpu_seconds": 1, "memory_bytes": 128 * 1024 * 1024, "output_bytes": 4096}
    manifest = {
        "schema_version": "1.0",
        "purpose": "generated-boundary-qualification",
        "max_probe_executions": 9,
        "max_elapsed_seconds": 90,
        "provider_calls": 0,
        "scientific_campaigns": 0,
        "limits": limits,
        "boundary_source_identity": boundary_source_identity(),
        "platform": platform.platform(),
    }
    put(tmp_path, "manifest.json", manifest)
    put(tmp_path, "runtime.json", asdict(runtime))
    checks = []
    for index, name in enumerate(CHECKS):
        root = tmp_path / ("parent-death" if name == "parent_death" else name)
        root.mkdir(mode=0o700)
        (root / "export").mkdir()
        source = b"# synthetic evidence; not a real qualification\n"
        (root / "export/probe.py").write_bytes(source)
        (root / "stdin.bin").write_bytes(b"")
        cid = f"{index:064x}"
        (root / "container-id").write_text(cid)
        intent = {
            **limits,
            "nonce": name,
            "image_id": runtime.image_id,
            "repository_digest": runtime.repository_digest,
            "sources": {"probe.py": hashlib.sha256(source).hexdigest()},
            "input_sha256": hashlib.sha256(b"").hexdigest(),
        }
        put(root, "intent.json", intent)
        put(
            root,
            "watchdog-job.json",
            {
                "container_id": cid,
                "nonce": name,
                "intent_digest": digest(intent),
                "docker": runtime.docker,
                "endpoint": runtime.endpoint,
            },
        )
        result = {"container_id": cid, "nonce": name, "stopped": True}
        check = {
            "name": name,
            "status": "pass",
            "stopped": True,
            "probe_sha256": hashlib.sha256(source).hexdigest(),
        }
        if name == "parent_death":
            result["reason"] = "timeout"
            receipt_digest = put(root, "watchdog-result.json", result)
        else:
            status = {
                "memory": "model_failure",
                "cpu": "model_failure",
                "output": "output_limit",
                "sleep": "timeout",
            }.get(name, "success")
            for stream in ("stdout", "stderr"):
                (root / f"{stream}.bin").write_bytes(b"")
                result[f"{stream}_sha256"] = hashlib.sha256(b"").hexdigest()
            result.update(status=status, oom_killed=name == "memory", intent_digest=digest(intent))
            check["observed_status"] = status
            receipt_digest = put(root, "result.json", result)
        check["execution_receipt"] = receipt_digest
        checks.append(check)
    receipt = {
        **manifest,
        "runtime": asdict(runtime),
        "status": "qualified",
        "remaining_gate": None,
        "elapsed_seconds": 12.0,
        "image_download_attempted": False,
        "checks": checks,
    }
    expected = put(tmp_path, "qualification.json", receipt)
    return tmp_path, expected


def test_reconstructs_caller_pinned_evidence_without_execution(evidence, monkeypatch):
    import subprocess

    def forbidden(*args, **kwargs):
        raise AssertionError("qualification reading must not execute code")

    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    root, expected = evidence
    assert verify_qualification(root, expected_digest=expected).receipt_digest == expected


@pytest.mark.parametrize(
    "name",
    [
        "qualification.json",
        "manifest.json",
        "runtime.json",
        "startup/intent.json",
        "memory/result.json",
        "parent-death/watchdog-result.json",
        "privacy/export/probe.py",
        "network/stdin.bin",
        "output/stdout.bin",
        "sleep/container-id",
        "cpu/watchdog-job.json",
    ],
)
def test_changed_evidence_is_rejected(evidence, name):
    root, expected = evidence
    path = root / name
    if path.suffix == ".json":
        record = json.loads(path.read_text())
        record["changed"] = True
        put(root, name, record)
        # An unrelated extra field is not necessarily an identity change for
        # runtime/intent/job checks. Change the bound field too.
        if name == "runtime.json":
            record["image_id"] = "sha256:" + "d" * 64
        elif name.endswith("intent.json"):
            record["nonce"] = "different"
        elif name.endswith("watchdog-job.json"):
            record["container_id"] = "different"
        elif name == "manifest.json":
            record["max_probe_executions"] = 10
        put(root, name, record)
    else:
        path.write_bytes(b"changed")
    with pytest.raises((ValueError, TypeError)):
        verify_qualification(root, expected_digest=expected)


def test_boundary_change_invalidates_existing_qualification(evidence, monkeypatch):
    import autoengineering.agents.qualification as module

    root, expected = evidence
    monkeypatch.setattr(module, "boundary_source_identity", lambda: "c" * 64)
    with pytest.raises(ValueError, match="source or platform changed"):
        verify_qualification(root, expected_digest=expected)


def test_symlinked_probe_output_is_rejected(evidence):
    root, expected = evidence
    target = root / "output/stdout.bin"
    target.unlink()
    target.symlink_to(root / "output/stderr.bin")
    with pytest.raises(ValueError):
        verify_qualification(root, expected_digest=expected)
