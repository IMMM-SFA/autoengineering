"""Synthetic qualification decoder evidence. These fixtures qualify no OS profile."""

from dataclasses import asdict, replace
import hashlib

import pytest

from autoengineering.agents.hosts import claude_profile as profile
from autoengineering.agents.hosts.claude import ClaudeInventory, REQUIRED_FLAGS, SUPPORTED_VERSION
from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.serialization import canonical_json, digest


def fixture(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    runtime = {"platform": "darwin", "machine": "arm64", "test_only": "authored runtime"}
    monkeypatch.setattr(profile, "native_runtime", lambda: runtime)
    executable = tmp_path / "authored-claude"
    executable.write_text("authored nonexecutable inventory fixture")
    inventory = ClaudeInventory(
        str(executable),
        hashlib.sha256(executable.read_bytes()).hexdigest(),
        SUPPORTED_VERSION,
        REQUIRED_FLAGS,
    )
    limits = {
        "max_worker_seconds": 30,
        "max_output_bytes": 65536,
        "max_workspace_bytes": 65536,
        "max_output_tokens": 512,
        "estimated_budget_usd": 0.1,
    }
    bindings = {
        "source_identity": host_source_identity(),
        "runtime_identity": digest(runtime),
        "inventory_identity": digest(asdict(inventory)),
        "boundary_source_identity": profile.boundary_source_identity(),
        "limits": limits,
        "auth_mode": "api",
        "api_version": profile.API_VERSION,
        "model": "claude-fixture-1",
        "limitations": list(profile.LIMITATIONS),
    }
    (tmp_path / "artifacts").mkdir(mode=0o700)
    raw = put_bytes(
        tmp_path,
        b"decoder fixture, no OS facts",
        name="raw.txt",
        media_type="text/plain",
        producer="test",
    )
    index = replace(
        put_bytes(
            tmp_path,
            canonical_json(
                {
                    "version": profile.INDEX_VERSION,
                    "bindings": bindings,
                    "files": [raw.to_dict()],
                    "total_bytes": raw.size_bytes,
                }
            ).encode(),
            name="index.json",
            media_type="application/json",
            producer="test",
        ),
        metadata={"kind": profile.INDEX_VERSION},
    )
    checks = {}
    for name, observed in profile.OBSERVATIONS.items():
        checks[name] = put_bytes(
            tmp_path,
            canonical_json(
                {
                    "version": profile.VERSION,
                    "name": name,
                    "status": "passed",
                    "bindings": bindings,
                    "observed": observed,
                    "evidence": [raw.to_dict(), index.to_dict()],
                }
            ).encode(),
            name=f"{name}.json",
            media_type="application/json",
            producer="test",
        ).to_dict()
    return {
        "version": profile.VERSION,
        "status": "qualified",
        "source_identity": host_source_identity(),
        "runtime": runtime,
        "boundary_source_identity": profile.boundary_source_identity(),
        "inventory": asdict(inventory),
        "model": "claude-fixture-1",
        "auth_mode": "api",
        "api_version": profile.API_VERSION,
        "limits": limits,
        "limitations": list(profile.LIMITATIONS),
        "checks": checks,
        "provider_calls": 0,
        "scientific_calls": 0,
    }


@pytest.mark.parametrize(
    "problem",
    [
        None,
        "pin",
        "candidate",
        "codex",
        "source",
        "runtime",
        "boundary",
        "auth",
        "api-version",
        "limitations",
        "tokens",
        "usd",
        "counter",
        "checks",
        "artifact",
        "executable",
        "extra",
    ],
)
def test_every_profile_binding_and_artifact_is_required(tmp_path, monkeypatch, problem):
    value = fixture(tmp_path, monkeypatch)
    if problem == "candidate":
        value["status"] = "candidate"
    elif problem == "codex":
        value["version"] = "native-codex-boundary-1.3"
    elif problem == "source":
        value["source_identity"] = "0" * 64
    elif problem == "runtime":
        value["runtime"] = {"platform": "linux", "machine": "x86_64"}
    elif problem == "boundary":
        value["boundary_source_identity"] = "0" * 64
    elif problem == "auth":
        value["auth_mode"] = "subscription"
    elif problem == "api-version":
        value["api_version"] = "old"
    elif problem == "limitations":
        value["limitations"] = []
    elif problem == "tokens":
        value["limits"]["max_output_tokens"] = True
    elif problem == "usd":
        value["limits"]["estimated_budget_usd"] = False
    elif problem == "counter":
        value["provider_calls"] = False
    elif problem == "checks":
        value["checks"].pop("credentials")
    elif problem == "artifact":
        (tmp_path / value["checks"]["upstream"]["path"]).write_text("changed")
    elif problem == "executable":
        (tmp_path / "authored-claude").write_text("changed")
    elif problem == "extra":
        value["unknown"] = True
    raw = canonical_json(value).encode()
    (tmp_path / "qualification.json").write_bytes(raw)
    pin = "0" * 64 if problem == "pin" else hashlib.sha256(raw).hexdigest()
    if problem is None:
        checked = profile.verify_claude_profile(tmp_path, expected_digest=pin)
        assert checked.max_output_tokens == 512 and checked.estimated_budget_usd == 0.1
        assert checked.limitations == profile.LIMITATIONS
    else:
        with pytest.raises(ValueError):
            profile.verify_claude_profile(tmp_path, expected_digest=pin)


def test_boolean_observation_cannot_replace_integer_native_tool_counter(tmp_path, monkeypatch):
    from autoengineering.campaign.serialization import unique_json

    value = fixture(tmp_path, monkeypatch)
    old = value["checks"]["tools"]
    report = unique_json((tmp_path / old["path"]).read_text())
    report["observed"]["native_tool_executions"] = False
    value["checks"]["tools"] = put_bytes(
        tmp_path,
        canonical_json(report).encode(),
        name="changed.json",
        media_type="application/json",
        producer="test",
    ).to_dict()
    raw = canonical_json(value).encode()
    (tmp_path / "qualification.json").write_bytes(raw)
    with pytest.raises(ValueError, match="foreign checks"):
        profile.verify_claude_profile(tmp_path, expected_digest=hashlib.sha256(raw).hexdigest())
