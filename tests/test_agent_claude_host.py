"""Claude scheduler adapter with a stubbed qualifier and authored CLI/provider.

No fixture here is actual qualification, authentication or live-call authority.
"""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import sys

import pytest

from autoengineering.agents.hosts import claude_host as adapter
from autoengineering.agents.hosts.brokered_host import WIRE_PREFIX
from autoengineering.agents.hosts.claude_profile import VerifiedClaudeProfile, LIMITATIONS
from autoengineering.agents.hosts.codex_brokered import WrappedCommand
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.identity import host_source_identity, host_environment_identity
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.records import HostSelection, HostCapabilities, HostConfigurationBinding
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import durable_write
from test_agent_claude_brokered import setup as cli_fixture, PROMPT, MODEL
from test_agent_contracts import run_spec
from test_agent_scheduler import setup


def worker(tmp_path, monkeypatch, *, missing_cache=False, invalid_inner=False):
    tmp_path.chmod(0o700)
    executable_root = tmp_path / "executables"
    executable_root.mkdir(mode=0o700)
    inventory, _, _, _ = cli_fixture(executable_root)
    path = Path(inventory.executable)
    path.write_text(
        path.read_text().replace(
            f"assert prompt=={PROMPT!r}", f"assert prompt.startswith({WIRE_PREFIX!r})"
        )
    )
    inventory = replace(inventory, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    qualification = tmp_path / "qualification"
    qualification.mkdir(mode=0o700)
    credentials = tmp_path / "credentials"
    credentials.mkdir(mode=0o700)
    profile = VerifiedClaudeProfile(
        qualification, "0" * 64, inventory, MODEL, 300, 65536, 65536, "1" * 64, 512, 0.1
    )
    monkeypatch.setattr(adapter, "verify_claude_profile", lambda *_a, **_k: profile)
    host = adapter.BrokeredClaudeHost(
        qualification_root=qualification,
        qualification_digest="0" * 64,
        credential_path=credentials / "never-open-lease.json",
        lease_id="authored-lease",
        model=MODEL,
    )
    spec = replace(
        run_spec(),
        host=HostSelection("claude", "api", MODEL, "3.0", "0" * 64),
        role_templates=template_digests(),
        tool_policy_digest=POLICY_DIGEST,
        source_identity=host_source_identity(),
        environment_identity=host_environment_identity(),
    )
    store, _, task, output = setup(tmp_path, spec=spec)
    calls = []

    def upstream(*_args):
        def call(raw):
            calls.append(raw)
            request = json.loads(raw)
            assert request["messages"][0]["content"][0]["text"].startswith(WIRE_PREFIX)
            usage = {"input_tokens": 7, "output_tokens": 10}
            if not missing_cache:
                usage.update(cache_read_input_tokens=2, cache_creation_input_tokens=3)
            return canonical_json(
                {
                    "id": "msg_scheduler_fixture",
                    "type": "message",
                    "role": "assistant",
                    "model": MODEL,
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": usage,
                    "content": [
                        {
                            "type": "text",
                            "text": canonical_json(
                                {
                                    "handoff_json": '{"role":"wrong"}'
                                    if invalid_inner
                                    else output.to_json(),
                                }
                            ),
                        }
                    ],
                }
            ).encode()

        return call

    def wrap(command, endpoint, *_args):
        policy = endpoint.directory.parent / "authored-policy.txt"
        durable_write(policy, b"authored identity wrapper, no OS qualification")
        return WrappedCommand(command, policy)

    monkeypatch.setattr(host, "_upstream", upstream)
    monkeypatch.setattr(host, "_wrap", wrap)
    return SerialScheduler(store, host, clock=lambda: 100), task, output, calls


@pytest.mark.parametrize("missing_cache", [False, True])
def test_scheduler_commits_claude_handoff_and_broker_usage_without_native_fill(
    tmp_path, monkeypatch, missing_cache
):
    scheduler, task, output, calls = worker(tmp_path, monkeypatch, missing_cache=missing_cache)
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "completed" and scheduler.handoff(result) == output
    assert result.resolved_model == MODEL and result.usage["total_tokens"] == (
        None if missing_cache else 22
    )
    assert result.capabilities.host == "claude" and result.capabilities.limitations == LIMITATIONS
    assert result.capabilities.usage_basis == "reported_message_fields_only"
    assert len(calls) == 1 and read_bytes(scheduler.store.root, result.prompt).startswith(
        WIRE_PREFIX.encode()
    )
    assert scheduler.dispatch(task, campaign_revision=3) == result and len(calls) == 1


def test_lost_return_reconciles_original_claude_evidence_without_relaunch(tmp_path, monkeypatch):
    scheduler, task, output, calls = worker(tmp_path, monkeypatch)
    original = scheduler.host.invoke_supervised

    def lost(*args):
        original(*args)
        raise RuntimeError("authored lost host return")

    monkeypatch.setattr(scheduler.host, "invoke_supervised", lost)
    pending = scheduler.dispatch(task, campaign_revision=3)
    assert pending.state == "reconciliation_required" and pending.process_receipt
    root = scheduler.store.root / "processes" / pending.id
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    result = scheduler.recover_invocation(pending.id, campaign_revision=3)
    assert result.state == "completed" and scheduler.handoff(result) == output
    assert result.usage["total_tokens"] == 22 and len(calls) == 1
    assert before == {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def test_typed_role_validation_still_rejects_a_valid_transport_envelope(tmp_path, monkeypatch):
    scheduler, task, _, calls = worker(tmp_path, monkeypatch, invalid_inner=True)
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "invalid_output" and len(calls) == 1
    assert result.usage["total_tokens"] == 22 and result.normalized_output is None


def test_missing_real_qualification_refuses_before_any_credential_read(tmp_path):
    tmp_path.chmod(0o700)
    with pytest.raises(ValueError):
        adapter.BrokeredClaudeHost(
            qualification_root=tmp_path,
            qualification_digest="0" * 64,
            credential_path=tmp_path / "never-open.json",
            lease_id="lease",
            model=MODEL,
        )


def test_selection_and_capabilities_keep_legacy_shapes_and_separate_new_versions():
    old = HostSelection("codex", "subscription", "old", "1.0")
    assert old.to_dict() == {
        "kind": "codex",
        "auth_mode": "subscription",
        "requested_model": "old",
        "adapter_version": "1.0",
    }
    caps = HostCapabilities(
        "1.0", "codex", "2.1", "version", "subscription", True, True, "0" * 64, "darwin"
    )
    assert set(caps.to_dict()) == {
        "schema_version",
        "host",
        "adapter_version",
        "executable_version",
        "auth_mode",
        "structured_output",
        "process_supervision",
        "boundary_identity",
        "platform",
    }
    assert HostCapabilities.from_dict(caps.to_dict()) == caps
    new = HostCapabilities(
        "1.1",
        "claude",
        "3.0",
        "version",
        "api",
        True,
        True,
        "0" * 64,
        "darwin",
        LIMITATIONS,
        "reported_message_fields_only",
    )
    assert HostCapabilities.from_dict(new.to_dict()) == new
    HostConfigurationBinding("1.1", "run-one", "0" * 64, new)
    with pytest.raises(ValueError):
        HostConfigurationBinding("1.0", "run-one", "0" * 64, new)
    for kind, auth, version, pin in [
        ("claude", "subscription", "3.0", "0" * 64),
        ("claude", "api", "2.1", "0" * 64),
        ("codex", "api", "3.0", "0" * 64),
        ("claude", "api", "3.0", None),
    ]:
        with pytest.raises(ValueError):
            HostSelection(kind, auth, MODEL, version, pin)
    with pytest.raises(ValueError):
        HostCapabilities.from_dict({**caps.to_dict(), "usage_basis": None})


def test_configuration_versions_bind_host_and_keep_old_digest(tmp_path, monkeypatch):
    scheduler, _, _, _ = worker(tmp_path, monkeypatch)
    host = scheduler.host
    old = HostConfiguration(host.root, host.pin, host.credential_path, host.lease_id)
    assert old.digest == digest(
        {
            "schema_version": "1.0",
            "qualification_root": str(host.root),
            "qualification_digest": host.pin,
            "credential_path": str(host.credential_path),
            "lease_id": host.lease_id,
        }
    )
    config = HostConfiguration(
        host.root, host.pin, host.credential_path, host.lease_id, "1.1", "claude", "api"
    )
    assert config.build(scheduler.store.spec).capabilities() == host.capabilities()
    with pytest.raises(ValueError, match="selection"):
        old.build(scheduler.store.spec)
    filename = tmp_path / "host.toml"
    filename.write_text(
        "\n".join(
            f"{k} = {json.dumps(v)}"
            for k, v in {
                "schema_version": "1.1",
                "host_kind": "claude",
                "auth_mode": "api",
                "qualification_root": str(host.root),
                "qualification_digest": host.pin,
                "credential_path": str(host.credential_path),
                "lease_id": host.lease_id,
            }.items()
        )
    )
    assert HostConfiguration.from_file(filename) == config


@pytest.mark.skipif(sys.platform != "darwin", reason="Declared API profile is macOS only")
def test_exact_api_worker_missing_lease_fails_before_send_and_preserves_stop(tmp_path, monkeypatch):
    scheduler, task, _, calls = worker(tmp_path, monkeypatch)
    monkeypatch.delattr(scheduler.host, "_upstream")
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "host_failure" and not result.usage and not calls
    root = scheduler.store.root / "processes" / result.id
    receipt = json.loads((root / "upstream/attempt/provider-result.json").read_text())
    assert receipt["phase"] == "preflight" and receipt["request_may_have_been_sent"] is False
    proof = json.loads((root / "upstream-stop.json").read_text())
    assert proof["state"] == "verified_stopped"


@pytest.mark.parametrize("lost_ack", [False, True])
def test_claude_batch_charges_once_and_recovers_original_observation(
    tmp_path, monkeypatch, lost_ack
):
    from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
    from autoengineering.agents.batch_native import BatchClaudeHost
    from autoengineering.agents.store import WorkerStore

    original, task, output, calls = worker(tmp_path, monkeypatch)
    spec = original.store.spec
    host = original.host
    config = HostConfiguration(
        host.root, host.pin, host.credential_path, host.lease_id, "1.1", "claude", "api"
    )
    batch_spec = BatchSpec(
        "1.0",
        "claude-batch",
        spec.source_identity,
        spec.environment_identity,
        spec.host,
        host.capabilities(),
        config.digest,
        spec.limits,
        0,
        (BatchCase("native", "text", "0" * 64, 2, 0),),
    )
    batch = BatchStore.create(tmp_path / "batch", batch_spec, clock=lambda: 100)
    batch.start_case("native", "0" * 64)
    case = batch.root / "cases/native"
    case.mkdir(mode=0o700)
    store = WorkerStore.create(case / "worker", spec, clock=lambda: 100)
    shutil.copytree(original.store.root / "artifacts", store.root / "artifacts", dirs_exist_ok=True)
    batched = BatchClaudeHost(config, batch, "native")
    monkeypatch.setattr(batched, "_upstream", host._upstream)
    monkeypatch.setattr(batched, "_wrap", host._wrap)
    scheduler = SerialScheduler(store, batched, clock=lambda: 100)

    def fault(stage):
        if stage == "after_event_commit" and any(
            (store.root / "processes").rglob("completion.json")
        ):
            raise RuntimeError("authored batch observation acknowledgement loss")

    if lost_ack:
        batch.fault = fault
    result = scheduler.dispatch(task, campaign_revision=3)
    if lost_ack:
        assert result.state == "reconciliation_required"
        batch.fault = lambda _: None
        result = scheduler.recover_invocation(result.id, campaign_revision=3)
    assert result.state == "completed" and scheduler.handoff(result) == output
    assert result.usage["total_tokens"] == 22 and len(calls) == 1
    assert batch.report()["host_reservations_charged"] == 1 and not batch.replay().pending
    assert scheduler.dispatch(task, campaign_revision=3) == result and len(calls) == 1


def test_cli_run_resume_binds_claude_configuration_and_all_roles(tmp_path, monkeypatch):
    from click.testing import CliRunner
    from autoengineering.agents.hosts.scripted import supplied_reply
    from autoengineering.agents.records import TaskAssignment
    from autoengineering.agents.store import WorkerStore
    from autoengineering.cli import cli
    from examples.agent_campaign.run import prepare
    from test_agent_host_configuration import command

    scheduler, _, _, _ = worker(tmp_path, monkeypatch)
    host = scheduler.host
    root = tmp_path / "example"
    _, spec = prepare(root)
    spec = replace(spec, host=HostSelection("claude", "api", MODEL, "3.0", "0" * 64))
    (root / "agent-run.json").write_text(spec.to_json())
    calls = []

    def upstream(*_args):
        def call(raw):
            calls.append(raw)
            prompt = json.loads(raw)["messages"][0]["content"][0]["text"]
            context = json.loads(prompt[prompt.index('{"approved_evidence"') :])
            task = TaskAssignment.from_dict(context["task"])
            reply = supplied_reply(task, prompt, context["invocation_id"])
            return canonical_json(
                {
                    "id": "msg_cli_fixture",
                    "type": "message",
                    "role": "assistant",
                    "model": MODEL,
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "content": [
                        {"type": "text", "text": canonical_json({"handoff_json": reply.raw_output})}
                    ],
                    "usage": {"input_tokens": 7, "output_tokens": 10},
                }
            ).encode()

        return call

    monkeypatch.setattr(adapter.BrokeredClaudeHost, "_upstream", staticmethod(upstream))
    monkeypatch.setattr(adapter.BrokeredClaudeHost, "_wrap", staticmethod(host._wrap))
    filename = tmp_path / "cli-host.toml"
    filename.write_text(
        "\n".join(
            f"{k} = {json.dumps(v)}"
            for k, v in {
                "schema_version": "1.1",
                "host_kind": "claude",
                "auth_mode": "api",
                "qualification_root": str(host.root),
                "qualification_digest": host.pin,
                "credential_path": str(host.credential_path),
                "lease_id": host.lease_id,
            }.items()
        )
    )
    runner = CliRunner()
    result = runner.invoke(cli, command(root, "run", filename))
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == "completed" and len(calls) == 7
    store = WorkerStore(root / "worker")
    binding = store.replay().host_configuration
    assert binding.schema_version == "1.1" and binding.capabilities.host == "claude"
    assert binding.capabilities.usage_basis == "reported_message_fields_only"
    assert all(value.usage["total_tokens"] is None for value in store.replay().invocations.values())
    before = {
        str(p.relative_to(store.root)): p.read_bytes() for p in store.root.rglob("*") if p.is_file()
    }
    resumed = runner.invoke(cli, command(root, "resume", filename))
    assert resumed.exit_code == 0, resumed.output
    assert len(calls) == 7 and before == {
        str(p.relative_to(store.root)): p.read_bytes() for p in store.root.rglob("*") if p.is_file()
    }
