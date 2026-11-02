"""Offline Claude transport tests. All executable responses are authored fixtures."""

from dataclasses import replace
import hashlib
import json
import sys

import pytest

from autoengineering.agents.hosts.claude import (
    REQUIRED_FLAGS,
    SUPPORTED_VERSION,
    execute_claude_transport,
    inspect_claude,
    parse_result,
    recover_claude_transport,
)

MODEL = "claude-fixture-1"


def document(**updates):
    value = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "num_turns": 1,
        "stop_reason": "end_turn",
        "structured_output": {"handoff_json": '{"role":"reviewer"}'},
        "usage": {
            "input_tokens": 5,
            "cache_read_input_tokens": 2,
            "cache_creation_input_tokens": 3,
            "output_tokens": 4,
        },
        "modelUsage": {MODEL: {}},
        "total_cost_usd": 0.01,
        "permission_denials": [],
    }
    return value | updates


def encoded(**updates):
    return json.dumps(document(**updates)).encode()


def setup(tmp_path, *, raw=None, exitcode=0, mode="result"):
    tmp_path.chmod(0o700)
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    auth = tmp_path / "private"
    auth.mkdir(mode=0o700)
    secret = auth / "not-a-real-credential"
    secret.write_text("fixture-key-never-forwarded")
    helper = auth / "helper with spaces;literal"
    helper.write_text(
        f"#!{sys.executable}\nfrom pathlib import Path\nprint(Path({str(secret)!r}).read_text())\n"
    )
    helper.chmod(0o700)
    schema = workspace / "schema.json"
    schema.write_text('{"type":"object","properties":{"handoff_json":{"type":"string"}}}')
    executable = tmp_path / "fake-claude"
    executable.write_text(f"""#!{sys.executable}
import json,os,shlex,subprocess,sys,time
if sys.argv[1:]==['--version']:
 print({SUPPORTED_VERSION!r})
elif sys.argv[1:]==['--help']:
 print({" ".join(REQUIRED_FLAGS)!r})
else:
 assert not any(name in os.environ for name in ('ANTHROPIC_API_KEY','CLAUDE_CODE_OAUTH_TOKEN','OPENAI_API_KEY'))
 assert '--bare' in sys.argv and '--no-session-persistence' in sys.argv
 assert '--tools=' in sys.argv
 assert '--setting-sources=' in sys.argv
 assert json.loads(sys.argv[sys.argv.index('--mcp-config')+1])=={{'mcpServers':{{}}}}
 settings=json.loads(sys.argv[sys.argv.index('--settings')+1])
 assert settings['disableAllHooks'] is True
 credential=subprocess.run(shlex.split(settings['apiKeyHelper']),capture_output=True,check=True).stdout
 assert credential.strip()==b'fixture-key-never-forwarded'
 assert sys.stdin.read()=='approved brief'
 if {mode!r}=='timeout': time.sleep(10)
 if {mode!r}=='output': sys.stdout.write('x'*200000)
 else: sys.stdout.buffer.write({raw if raw is not None else encoded()!r})
 sys.exit({exitcode})
""")
    executable.chmod(0o700)
    inventory = inspect_claude(executable)
    kwargs = dict(
        model=MODEL,
        schema=schema,
        helper=helper,
        helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
        directory=tmp_path / "physical",
        workspace=workspace,
        home=home,
        nonce="claude-offline-test",
        prompt=b"approved brief",
        timeout_seconds=4.0,
        max_output_bytes=65536,
        max_budget_usd=0.1,
        on_launch=lambda _: None,
        # Authored fake only. This identity wrapper is not a live OS boundary.
        wrap_command=lambda command: command,
    )
    return inventory, kwargs


def test_cache_tokens_are_included_once_and_cost_is_reported():
    value = parse_result(encoded())
    assert value.usage["input_tokens"] == 10
    assert value.usage["total_tokens"] == 14
    assert value.usage["output_tokens"] == 4
    assert value.usage["cached_input_tokens"] == 2
    assert value.cost_usd == 0.01 and value.resolved_model == MODEL
    assert json.loads(value.text) == document()["structured_output"]
    with pytest.raises(TypeError):
        value.usage["total_tokens"] = 0


def test_absent_categories_models_and_cost_remain_unknown():
    value = parse_result(
        encoded(usage={"input_tokens": 5, "output_tokens": 4}, modelUsage=None, total_cost_usd=None)
    )
    assert value.usage["input_tokens"] is None and value.usage["total_tokens"] is None
    assert value.usage["uncached_input_tokens"] == 5
    assert value.resolved_model is None and value.cost_usd is None


@pytest.mark.parametrize(
    "update",
    [
        {"is_error": True},
        {"is_error": "false"},
        {"subtype": "error_max_turns"},
        {"num_turns": 0},
        {"num_turns": True},
        {"stop_reason": "max_tokens"},
        {"permission_denials": [{"tool_name": "Read"}]},
        {"errors": ["fixture failure"]},
        {"structured_output": None},
        {"structured_output": {}},
        {"usage": {"server_tool_use": {"web_search_requests": 1}}},
    ],
)
def test_failed_or_incomplete_result_never_yields_a_handoff(update):
    value = parse_result(encoded(**update))
    assert value.text is None and value.rejection
    assert value.cost_usd == 0.01


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"{partial",
        b"[]",
        b'{"type":"result","type":"result"}',
        encoded() + encoded(),
        encoded(usage={"input_tokens": True}),
        encoded(total_cost_usd=-1),
        encoded(total_cost_usd=True),
        encoded(total_cost_usd=float("nan")),
        b"x" * 65537,
    ],
)
def test_malformed_output_is_refused(raw):
    with pytest.raises(ValueError):
        parse_result(raw)


def test_supervised_transport_keeps_secret_out_of_job_and_recovers_original(tmp_path, monkeypatch):
    inventory, kwargs = setup(tmp_path)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ambient-do-not-forward")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "ambient-do-not-forward")
    value = execute_claude_transport(inventory, **kwargs)
    assert value.error is None and value.process.stopped and value.parsed.text
    assert value.parsed.usage["total_tokens"] == 14
    job = (kwargs["directory"] / "job.json").read_text()
    assert "fixture-key-never-forwarded" not in job and "ambient-do-not-forward" not in job
    assert kwargs["helper_sha256"] in job
    assert (kwargs["directory"] / "stdout.bin").read_bytes() == encoded()
    # Completed inspection has no need for credentials or the current executable.
    kwargs["helper"].unlink()
    (kwargs["helper"].parent / "not-a-real-credential").unlink()
    monkeypatch.setattr(
        "autoengineering.agents.hosts.claude.supervise_process",
        lambda *a, **k: pytest.fail("recovery relaunched"),
    )
    recovered = recover_claude_transport(
        kwargs["directory"],
        nonce=kwargs["nonce"],
        job_sha256=value.job_sha256,
        model=MODEL,
        max_output_bytes=65536,
    )
    assert recovered == value


@pytest.mark.parametrize(
    "raw,exitcode,error",
    [
        (encoded(), 3, "claude_process_incomplete"),
        (encoded(is_error=True), 0, "claude_reported_failure"),
        (encoded(modelUsage={"claude-other-model": {}}), 0, "claude_model_identity_mismatch"),
        (
            encoded(modelUsage={MODEL: {}, "claude-other-model": {}}),
            0,
            "claude_model_identity_mismatch",
        ),
        (encoded(total_cost_usd=0.2), 0, "claude_budget_overrun"),
        (b"{partial", 0, "invalid_claude_result"),
    ],
)
def test_failed_process_or_identity_keeps_raw_and_available_charges(tmp_path, raw, exitcode, error):
    inventory, kwargs = setup(tmp_path, raw=raw, exitcode=exitcode)
    value = execute_claude_transport(inventory, **kwargs)
    assert value.error == error
    assert value.parsed is None or value.parsed.text is None
    if value.parsed:
        assert value.parsed.cost_usd is not None
        assert value.parsed.usage["total_tokens"] == 14
    assert (kwargs["directory"] / "stdout.bin").read_bytes() == raw


@pytest.mark.parametrize("mode,expected", [("timeout", "timeout"), ("output", "output_limit")])
def test_process_limits_stop_owned_fake_without_completed_handoff(tmp_path, mode, expected):
    inventory, kwargs = setup(tmp_path, mode=mode)
    kwargs.update(timeout_seconds=0.15 if mode == "timeout" else 4.0, max_output_bytes=1024)
    value = execute_claude_transport(inventory, **kwargs)
    assert value.process.status == expected and value.process.stopped
    assert value.parsed is None or value.parsed.text is None
    assert len(value.process.stdout) + len(value.process.stderr) <= 1024


@pytest.mark.parametrize("change", ["helper", "executable", "version", "model", "budget"])
def test_changed_configuration_refuses_before_process(tmp_path, change):
    inventory, kwargs = setup(tmp_path)
    if change == "helper":
        kwargs["helper"].write_text("changed")
    if change == "executable":
        from pathlib import Path

        Path(inventory.executable).write_text("changed")
    if change == "version":
        inventory = replace(inventory, version="unsupported")
    if change == "model":
        kwargs["model"] = "sonnet"
    if change == "budget":
        kwargs["max_budget_usd"] = float("inf")
    with pytest.raises(ValueError):
        execute_claude_transport(inventory, **kwargs)
    assert not kwargs["directory"].exists()


def test_recovery_rejects_changed_job_or_requested_model(tmp_path):
    inventory, kwargs = setup(tmp_path)
    value = execute_claude_transport(inventory, **kwargs)
    recovery = dict(
        nonce=kwargs["nonce"], job_sha256=value.job_sha256, model=MODEL, max_output_bytes=65536
    )
    with pytest.raises(ValueError, match="model"):
        recover_claude_transport(
            kwargs["directory"], **(recovery | {"model": "claude-other-model"})
        )
    path = kwargs["directory"] / "job.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="binding"):
        recover_claude_transport(kwargs["directory"], **recovery)


def test_cancelled_original_keeps_stop_without_handoff(tmp_path):
    inventory, kwargs = setup(tmp_path, mode="timeout")
    value = execute_claude_transport(inventory, **(kwargs | {"cancelled": lambda: True}))
    assert value.process.status == "cancelled" and value.process.stopped
    assert value.parsed is None or value.parsed.text is None
    assert value.error


def test_helper_changed_after_precheck_never_runs_or_exposes_key(tmp_path):
    inventory, kwargs = setup(tmp_path)
    marker = kwargs["helper"].parent / "changed-helper-ran"

    def changed(command):
        kwargs["helper"].write_text(
            f'#!{sys.executable}\nfrom pathlib import Path\nPath({str(marker)!r}).touch()\nprint("forbidden")\n'
        )
        return command

    value = execute_claude_transport(inventory, **(kwargs | {"wrap_command": changed}))
    assert value.error and not marker.exists()
    assert b"fixture-key-never-forwarded" not in value.process.stdout + value.process.stderr
    assert value.process.returncode != 0 and value.process.stopped


def test_lost_owner_before_command_does_not_obtain_a_fresh_attempt(tmp_path):
    inventory, kwargs = setup(tmp_path)

    def lost(_):
        raise RuntimeError("authored owner loss")

    with pytest.raises(RuntimeError, match="owner loss"):
        execute_claude_transport(inventory, **(kwargs | {"on_launch": lost}))
    assert kwargs["directory"].exists()
    # A fresh execution attempt cannot reuse the original physical directory.
    with pytest.raises(FileExistsError):
        execute_claude_transport(inventory, **kwargs)


def test_flag_prefix_is_not_a_supported_exact_option(tmp_path):
    from pathlib import Path

    inventory, _ = setup(tmp_path)
    executable = Path(inventory.executable)
    executable.write_text(executable.read_text().replace("--tools", "--tools-not-the-option"))
    with pytest.raises(ValueError, match="capabilities"):
        inspect_claude(executable)


def test_transport_does_not_silently_admit_a_new_scheduler_kind():
    from autoengineering.agents.records import HostSelection

    with pytest.raises(ValueError):
        HostSelection("claude", "subscription", MODEL, "1.0")


@pytest.mark.parametrize("wrapper", [lambda c: (c[0], "--print"), lambda c: " ".join(c)])
def test_boundary_wrapper_cannot_drop_or_replace_fixed_policy(tmp_path, wrapper):
    inventory, kwargs = setup(tmp_path)
    with pytest.raises(ValueError, match="bound command"):
        execute_claude_transport(inventory, **(kwargs | {"wrap_command": wrapper}))
    assert not kwargs["directory"].exists()
