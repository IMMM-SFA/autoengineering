"""CLI configuration tests with authored qualification, executable and replies.

No test attestation here qualifies a real native boundary or opens a real lease.
"""

from dataclasses import replace
import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.hosts import brokered_host as adapter
from autoengineering.agents.hosts.codex_brokered import WrappedCommand, inspect_brokered_codex
from autoengineering.agents.hosts.native_profile import VerifiedNativeProfile
from autoengineering.agents.hosts.scripted import supplied_reply
from autoengineering.agents.records import HostSelection, TaskAssignment
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import durable_write
from autoengineering.cli import cli
from examples.agent_campaign.check_brokered_scheduler_fixture import authored_stream
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL
from examples.agent_campaign.run import prepare
from test_agent_brokered_codex import program


def write_config(tmp_path, *, lease_id="unit-lease", pin="0" * 64):
    qualification = tmp_path / "qualification"
    qualification.mkdir(mode=0o700, exist_ok=True)
    filename = tmp_path / "host.toml"
    filename.write_text(
        'schema_version = "1.0"\n'
        f'qualification_root = "{qualification}"\n'
        f'qualification_digest = "{pin}"\n'
        f'credential_path = "{tmp_path / "never-open-lease.json"}"\n'
        f'lease_id = "{lease_id}"\n'
    )
    return filename


def configured(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    root = tmp_path / "example"
    _, spec = prepare(root)
    spec = replace(
        spec, host=HostSelection("codex", "subscription", OFFLINE_MODEL, "2.1", "0" * 64)
    )
    (root / "agent-run.json").write_text(spec.to_json())
    inventory = inspect_brokered_codex(program(tmp_path))
    profile = VerifiedNativeProfile(
        tmp_path, "0" * 64, inventory, OFFLINE_MODEL, 30, 65536, 65536, "1" * 64
    )
    monkeypatch.setattr(adapter, "verify_native_profile", lambda *a, **k: profile)
    calls = []

    def upstream(self, root, workspace, home, deadline, cancelled):
        def call(raw):
            calls.append(raw)
            prompt = unique_json(raw.decode())["input"][0]["content"][0]["text"]
            context = unique_json(prompt[prompt.index('{"approved_evidence"') :])
            task = TaskAssignment.from_dict(context["task"])
            reply = supplied_reply(task, prompt, context["invocation_id"])
            return authored_stream(canonical_json({"handoff_json": reply.raw_output}))

        return call

    def wrap(self, command, endpoint, *_):
        policy = endpoint.directory.parent / "unit-policy.sb"
        durable_write(policy, b"authored unit wrapper, no native qualification")
        return WrappedCommand(command, policy)

    monkeypatch.setattr(adapter.BrokeredCodexHost, "_upstream", upstream)
    monkeypatch.setattr(adapter.BrokeredCodexHost, "_wrap", wrap)
    filename = write_config(tmp_path)
    original_open = Path.open

    def no_lease_read(path, *args, **kwargs):
        if path == tmp_path / "never-open-lease.json":
            pytest.fail("CLI configuration/validation opened a credential")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", no_lease_read)
    return root, filename, calls


def command(root, name, config=None):
    args = [
        "agents",
        name,
        str(root / ("worker" if name == "resume" else "agent-run.json")),
        "--campaign",
        str(root / "campaign"),
    ]
    if name == "run":
        args += ["--workdir", str(root / "worker")]
    if config is not None:
        args += ["--host-config", str(config)]
    return args


def test_validate_requires_explicit_config_and_never_reads_lease_or_starts_host(
    tmp_path, monkeypatch
):
    root, config, calls = configured(tmp_path, monkeypatch)
    runner = CliRunner()
    absent = runner.invoke(cli, command(root, "run"))
    assert absent.exit_code == 2 and "--host-config" in absent.stdout
    assert not (root / "worker").exists()
    checked = runner.invoke(cli, command(root, "validate", config))
    assert checked.exit_code == 0, checked.output
    assert not calls and not (root / "worker").exists()


def test_cli_dispatch_binds_config_before_calls_and_replay_is_unchanged(tmp_path, monkeypatch):
    root, config, calls = configured(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(cli, command(root, "run", config))
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "completed" and len(calls) == 7
    store = WorkerStore(root / "worker")
    binding = store.replay().host_configuration
    assert binding.configuration_digest == HostConfiguration.from_file(config).digest
    assert store.replay().events[1].record == binding
    assert report["host_configuration"] == binding.to_dict()
    before = {
        str(p.relative_to(store.root)): p.read_bytes() for p in store.root.rglob("*") if p.is_file()
    }
    resumed = runner.invoke(cli, command(root, "resume", config))
    assert resumed.exit_code == 0, resumed.output
    assert len(calls) == 7 and before == {
        str(p.relative_to(store.root)): p.read_bytes() for p in store.root.rglob("*") if p.is_file()
    }
    write_config(tmp_path, lease_id="different-lease")
    changed = runner.invoke(cli, command(root, "resume", config))
    assert changed.exit_code == 2 and "configuration changed" in changed.stdout
    assert len(calls) == 7 and store.replay().host_configuration == binding


def test_wrong_pin_fails_before_worker_creation(tmp_path, monkeypatch):
    root, config, calls = configured(tmp_path, monkeypatch)
    write_config(tmp_path, pin="1" * 64)
    result = CliRunner().invoke(cli, command(root, "run", config))
    assert result.exit_code == 2 and not calls and not (root / "worker").exists()


@pytest.mark.parametrize("field,value", [("worker_seconds", 31), ("workspace_bytes", 1)])
def test_unqualified_worker_limits_fail_before_any_scientific_work(
    tmp_path, monkeypatch, field, value
):
    root, config, calls = configured(tmp_path, monkeypatch)
    path = root / "agent-run.json"
    data = json.loads(path.read_text())
    data["limits"][field] = value
    path.write_text(json.dumps(data))
    before = {
        str(p.relative_to(root / "campaign")): p.read_bytes()
        for p in (root / "campaign").rglob("*")
        if p.is_file()
    }
    result = CliRunner().invoke(cli, command(root, "run", config))
    assert result.exit_code == 2 and "worker limits" in result.stdout
    assert not calls and not (root / "worker").exists()
    assert before == {
        str(p.relative_to(root / "campaign")): p.read_bytes()
        for p in (root / "campaign").rglob("*")
        if p.is_file()
    }


@pytest.mark.parametrize(
    "problem", ["extra", "duplicate", "boolean", "relative", "large", "symlink"]
)
def test_strict_config_rejects_unsupported_or_unbounded_input(tmp_path, problem):
    tmp_path.chmod(0o700)
    config = write_config(tmp_path)
    raw = config.read_text()
    if problem == "extra":
        raw += 'access_token="must-not-be-copied"\n'
    elif problem == "duplicate":
        raw += 'lease_id="again"\n'
    elif problem == "boolean":
        raw = raw.replace('schema_version = "1.0"', "schema_version = true")
    elif problem == "relative":
        raw = raw.replace(str(tmp_path / "never-open-lease.json"), "relative-lease.json")
    elif problem == "large":
        raw += "#" * 65537
    else:
        original = tmp_path / "original.toml"
        config.rename(original)
        config.symlink_to(original)
    if problem != "symlink":
        config.write_text(raw)
    with pytest.raises(ValueError) as caught:
        HostConfiguration.from_file(config)
    assert "must-not-be-copied" not in str(caught.value)


def test_credential_cannot_be_under_any_client_or_qualification_root(tmp_path):
    tmp_path.chmod(0o700)
    config = write_config(tmp_path)
    value = HostConfiguration.from_file(config)
    with pytest.raises(ValueError, match="outside worker"):
        value.check_scope(tmp_path)
    config.write_text(
        config.read_text().replace(
            str(tmp_path / "never-open-lease.json"), str(tmp_path / "qualification/lease.json")
        )
    )
    with pytest.raises(ValueError, match="outside native"):
        HostConfiguration.from_file(config)
