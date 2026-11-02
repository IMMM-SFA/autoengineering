"""Claude preparation contracts with authored qualification, no provider use."""

from dataclasses import replace
import hashlib
import json

from click.testing import CliRunner
import pytest

from autoengineering.agents.conformance import (
    ConformancePreparation,
    inspect_conformance,
    load_conformance,
    _case_bindings,
    prepare_conformance,
)
from autoengineering.agents.conformance_protocol import (
    CLAUDE_VERSION,
    CLAUDE_POLICIES,
    CLAUDE_PROTOCOL_DIGEST,
    PROTOCOL_DIGEST,
    CLAUDE_IMPLEMENTED_CASES,
)
from autoengineering.agents.conformance_runtime import ConformanceRuntime
from autoengineering.agents.hosts import claude_host
from autoengineering.agents.hosts.claude_profile import VerifiedClaudeProfile
from autoengineering.agents.records import HostSelection
from autoengineering.cli import cli
from test_agent_claude_brokered import setup as cli_fixture, MODEL
from test_agent_conformance import fixture, snapshot


def authored(tmp_path, monkeypatch):
    root, worker, config, _, calls = fixture(tmp_path, monkeypatch)
    executable_root = tmp_path / "claude-executable"
    executable_root.mkdir(mode=0o700)
    inventory, _, _, _ = cli_fixture(executable_root)
    profile = VerifiedClaudeProfile(
        config.qualification_root,
        "0" * 64,
        inventory,
        MODEL,
        300,
        65536,
        65536,
        "1" * 64,
        512,
        0.1,
    )
    monkeypatch.setattr(claude_host, "verify_claude_profile", lambda *_a, **_k: profile)
    worker = replace(worker, host=HostSelection("claude", "api", MODEL, "3.0", "0" * 64))
    config = replace(config, schema_version="1.1", host_kind="claude", auth_mode="api")
    return root, worker, config, calls


def test_claude_preparation_roundtrip_and_readiness_do_not_execute(tmp_path, monkeypatch):
    root, worker, config, calls = authored(tmp_path, monkeypatch)
    before = snapshot(root)
    output, runtime = tmp_path / "proposal", tmp_path / "runtime"
    plan = prepare_conformance(worker, root / "campaign", config, output, runtime)
    assert plan.schema_version == CLAUDE_VERSION
    assert plan.protocol_digest == CLAUDE_PROTOCOL_DIGEST != PROTOCOL_DIGEST
    assert ConformancePreparation.from_json(plan.to_json()) == plan
    assert plan.batch.cases != _case_bindings(plan.worker, plan.scientific_digest, CLAUDE_POLICIES)
    assert plan.batch.cases == _case_bindings(
        plan.worker, plan.scientific_digest, CLAUDE_POLICIES, CLAUDE_PROTOCOL_DIGEST
    )
    assert plan.batch.host == worker.host
    assert plan.batch.capabilities.host == "claude"
    assert plan.batch.capabilities.limitations
    assert sum(c.host_invocations for c in plan.batch.cases) == 13
    assert sum(c.scientific_starts for c in plan.batch.cases) == 2
    captured = snapshot(output)
    status = inspect_conformance(output, expected_digest=plan.digest, configuration=config)
    assert status["protocol_digest"] == CLAUDE_PROTOCOL_DIGEST
    assert status["execution_ready"] is True
    assert status["implemented_execution_handlers"] == list(CLAUDE_IMPLEMENTED_CASES)
    assert status["missing_execution_handlers"] == [
        p[0] for p in CLAUDE_POLICIES if p[0] not in CLAUDE_IMPLEMENTED_CASES
    ]
    assert not status["credential_opened"] and status["provider_calls"] == 0
    assert not status["runtime_created"] and not status["clock_started"]
    assert snapshot(root) == before and snapshot(output) == captured
    assert not calls and not runtime.exists()
    # Loading/inspection without the host configuration still checks all captures.
    assert load_conformance(output, expected_digest=plan.digest) == plan


@pytest.mark.parametrize("problem", ["schema", "protocol", "case", "configuration"])
def test_claude_preparation_refuses_cross_profile_bindings(tmp_path, monkeypatch, problem):
    root, worker, config, calls = authored(tmp_path, monkeypatch)
    output = tmp_path / "proposal"
    plan = prepare_conformance(worker, root / "campaign", config, output, tmp_path / "runtime")
    value = plan.to_dict()
    if problem == "schema":
        value["schema_version"] = "host-conformance-preparation-1.0"
    elif problem == "protocol":
        value["protocol_digest"] = PROTOCOL_DIGEST
    elif problem == "case":
        value["batch"]["cases"][0]["configuration_digest"] = "f" * 64
    else:
        config = replace(config, schema_version="1.0", host_kind="codex", auth_mode="subscription")
    raw = json.dumps(value).encode()
    (output / "conformance.json").write_bytes(raw)
    with pytest.raises(ValueError):
        inspect_conformance(
            output, expected_digest=hashlib.sha256(raw).hexdigest(), configuration=config
        )
    assert not calls and not (tmp_path / "runtime").exists()


def test_claude_runtime_creation_binds_distinct_origin_without_calls(tmp_path, monkeypatch):
    root, worker, config, calls = authored(tmp_path, monkeypatch)
    output, runtime = tmp_path / "proposal", tmp_path / "runtime"
    plan = prepare_conformance(worker, root / "campaign", config, output, runtime)
    before = snapshot(output)
    runner = ConformanceRuntime.create(output, expected_digest=plan.digest, configuration=config)
    origin = json.loads((runtime / "origin.json").read_text())
    assert origin["version"] == "conformance-runtime-1.1"
    reopened = ConformanceRuntime.open(
        output,
        expected_digest=plan.digest,
        configuration=config,
        runtime_digest=runner.batch.digest,
    )
    assert reopened.report()["live_conformance_complete"] is False
    assert reopened.report()["missing_execution_handlers"] == []
    assert not calls and snapshot(output) == before
    origin["version"] = "conformance-runtime-1.0"
    (runtime / "origin.json").write_text(json.dumps(origin))
    with pytest.raises(ValueError, match="origin"):
        ConformanceRuntime.open(
            output,
            expected_digest=plan.digest,
            configuration=config,
            runtime_digest=runner.batch.digest,
        )


def test_cli_inspection_reports_implemented_claude_handlers(tmp_path, monkeypatch):
    root, worker, config, calls = authored(tmp_path, monkeypatch)
    output = tmp_path / "proposal"
    plan = prepare_conformance(worker, root / "campaign", config, output, tmp_path / "runtime")
    result = CliRunner().invoke(
        cli, ["agents", "conformance-inspect", str(output), "--expected-digest", plan.digest]
    )
    assert result.exit_code == 0, result.output
    status = json.loads(result.stdout)
    assert status["execution_ready"] is True and status["host_profile_checked"] is False
    assert status["missing_execution_handlers"] == [
        p[0] for p in CLAUDE_POLICIES if p[0] not in CLAUDE_IMPLEMENTED_CASES
    ]
    assert not calls


def test_cli_preparation_captures_claude_inputs_with_explicit_configuration(tmp_path, monkeypatch):
    root, worker, config, calls = authored(tmp_path, monkeypatch)
    (root / "agent-run.json").write_text(worker.to_json())
    config_file = tmp_path / "claude.toml"
    config_file.write_text(
        'schema_version = "1.1"\nhost_kind = "claude"\nauth_mode = "api"\n'
        f'qualification_root = "{config.qualification_root}"\n'
        f'qualification_digest = "{config.qualification_digest}"\n'
        f'credential_path = "{config.credential_path}"\n'
        f'lease_id = "{config.lease_id}"\n'
    )
    output, runtime = tmp_path / "proposal", tmp_path / "runtime"
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "conformance-prepare",
            str(root / "agent-run.json"),
            "--campaign",
            str(root / "campaign"),
            "--host-config",
            str(config_file),
            "--output",
            str(output),
            "--runtime-root",
            str(runtime),
        ],
    )
    assert result.exit_code == 0, result.output
    status = json.loads(result.stdout)
    assert status["host_profile_checked"] and status["execution_ready"]
    assert status["authorization"] == "not_granted_by_preparation"
    assert status["provider_calls"] == status["scientific_starts"] == 0
    assert not calls and not runtime.exists() and not config.credential_path.exists()


def test_absent_qualification_refuses_before_preparation_writes(tmp_path, monkeypatch):
    root, worker, config, calls = authored(tmp_path, monkeypatch)

    def absent(*_args, **_kwargs):
        raise ValueError("missing real qualification")

    monkeypatch.setattr(claude_host, "verify_claude_profile", absent)
    output = tmp_path / "proposal"
    with pytest.raises(ValueError, match="missing real qualification"):
        prepare_conformance(worker, root / "campaign", config, output, tmp_path / "runtime")
    assert not calls and not output.exists() and not config.credential_path.exists()
