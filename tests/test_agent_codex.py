"""Offline Codex executable conformance. No provider or real authentication is used."""

import json
import sys

import pytest

from autoengineering.agents.hosts.codex import (
    REQUIRED_FLAGS,
    execute_codex_transport,
    inspect_codex,
    parse_events,
    subscription_authentication,
)


def events(*, model=None, usage=None, tool=False):
    start = {"type": "thread.started", "thread_id": "offline"}
    if model is not None:
        start["model"] = model
    return (
        "\n".join(
            json.dumps(value)
            for value in (
                start,
                {"type": "turn.started"},
                {
                    "type": "item.completed",
                    "item": {
                        "type": "command_execution" if tool else "agent_message",
                        "text": '{"role":"reviewer"}',
                    },
                },
                {
                    "type": "turn.completed",
                    "usage": usage
                    if usage is not None
                    else {"input_tokens": 5, "cached_input_tokens": 2, "output_tokens": 3},
                },
            )
        )
        + "\n"
    )


def executable(tmp_path, raw, *, exitcode=0):
    path = tmp_path / "fake-codex"
    path.write_text(f"""#!{sys.executable}
import os,sys
if sys.argv[1:]==['--version']:
 print('codex-cli 0.164.0')
elif sys.argv[1:]==['exec','--help']:
 print({" ".join(REQUIRED_FLAGS)!r})
else:
 assert not os.environ.get('OPENAI_API_KEY')
 assert '--ignore-user-config' in sys.argv and '--ignore-rules' in sys.argv
 assert sys.argv[-1]=='-'
 assert sys.stdin.read()=='approved brief'
 sys.stdout.write({raw!r})
 sys.exit({exitcode})
""")
    path.chmod(0o700)
    return path


def transport(tmp_path, raw, *, exitcode=0):
    tmp_path.chmod(0o700)
    path = executable(tmp_path, raw, exitcode=exitcode)
    home = tmp_path / "auth"
    home.mkdir(mode=0o700)
    (home / "auth.json").write_text(
        '{"auth_mode":"chatgpt","tokens":{"access_token":"fixture-only"}}'
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir(mode=0o700)
    schema = workspace / "schema.json"
    schema.write_text('{"type":"object"}')
    inventory = inspect_codex(path)
    result = execute_codex_transport(
        inventory,
        model="requested-fixture-model",
        schema=schema,
        directory=tmp_path / "physical",
        workspace=workspace,
        home=home,
        nonce="fake-codex-nonce",
        prompt=b"approved brief",
        timeout_seconds=3,
        max_output_bytes=65536,
        on_launch=lambda _: None,
        # Trusted fake executable only. This does not qualify a live worker boundary.
        wrap_command=lambda command: command,
    )
    return result


def test_reported_model_and_usage_are_distinct_from_requested_model(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-never-forwarded")
    result = transport(tmp_path, events(model="actually-reported"))
    assert result.process.status == "completed" and result.process.stopped
    assert result.final_text == '{"role":"reviewer"}'
    assert result.resolved_model == "actually-reported"
    assert result.usage["total_tokens"] == 8
    assert result.usage["cached_input_tokens"] == 2
    assert result.usage["reasoning_output_tokens"] is None
    assert result.parse_error is None
    job = (tmp_path / "physical/job.json").read_text()
    assert "ambient-never-forwarded" not in job
    assert "fixture-only" not in job
    assert (tmp_path / "physical/stdout.bin").read_bytes() == result.process.stdout


def test_missing_model_metadata_remains_unknown(tmp_path):
    result = transport(tmp_path, events())
    assert result.resolved_model is None
    assert result.usage["total_tokens"] == 8


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "{partial",
        events(tool=True),
        events(usage={"input_tokens": True}),
        events() + json.dumps({"type": "turn.completed", "usage": {}}) + "\n",
        events().replace(
            '"type": "thread.started"', '"type":"thread.started","type":"turn.started"'
        ),
    ],
)
def test_invalid_stream_retains_raw_bytes_before_parse_failure(tmp_path, raw):
    result = transport(tmp_path, raw)
    assert result.parse_error == "invalid_codex_events"
    assert result.final_text is None and result.resolved_model is None
    assert dict(result.usage) == {}
    assert (tmp_path / "physical/stdout.bin").read_bytes() == raw.encode()


def test_nonzero_exit_does_not_turn_valid_text_into_a_completed_handoff(tmp_path):
    result = transport(tmp_path, events(), exitcode=7)
    assert result.process.status == "host_failure"
    assert result.process.stopped and result.final_text is None
    assert result.usage["total_tokens"] == 8


def test_capability_and_authentication_fail_closed_without_exposing_values(tmp_path):
    tmp_path.chmod(0o700)
    with pytest.raises(FileNotFoundError):
        inspect_codex(tmp_path / "missing")
    bad = executable(tmp_path, "")
    bad.write_text(f'#!{sys.executable}\nprint("unsupported executable")\n')
    with pytest.raises(ValueError, match="capabilities"):
        inspect_codex(bad)
    auth = tmp_path / "auth"
    auth.mkdir(mode=0o700)
    (auth / "auth.json").write_text('{"auth_mode":"apikey","OPENAI_API_KEY":"private-fixture"}')
    with pytest.raises(ValueError, match="mode mismatch") as error:
        subscription_authentication(auth)
    assert "private-fixture" not in str(error.value)
    assert "OPENAI_API_KEY" not in str(error.value)


def test_unknown_usage_is_not_zero_and_completed_without_usage_is_rejected():
    _, model, usage = parse_events(events(usage={}).encode())
    assert model is None and all(value is None for value in usage.values())
    raw = events().replace(
        '"usage": {"input_tokens": 5, "cached_input_tokens": 2, "output_tokens": 3}', '"other": {}'
    )
    with pytest.raises(ValueError, match="usage envelope"):
        parse_events(raw.encode())
