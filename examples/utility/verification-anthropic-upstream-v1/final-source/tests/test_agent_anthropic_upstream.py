"""Prepared-lease callback construction and strict original-attempt binding."""

import hashlib
import json
import os
from pathlib import Path
import sys
import time

import pytest

from autoengineering.agents.hosts import anthropic_upstream as upstream
from autoengineering.agents.hosts.anthropic_worker import API_VERSION, VERSION
from autoengineering.campaign.serialization import canonical_json
from autoengineering.agents.hosts.command_upstream import UpstreamProcessError
from test_agent_anthropic_worker import MODEL, inputs


def test_scoped_callback_pins_actual_worker_support_and_policy_without_reading_key(
    tmp_path, monkeypatch
):
    tmp_path.chmod(0o700)
    for name in ("client", "credentials"):
        (tmp_path / name).mkdir(mode=0o700)
    seen = []

    class FakeCommand:
        def __init__(self, directory, **kwargs):
            seen.append((directory, kwargs))

        def __call__(self, request):
            assert request == b"approved"
            return b"authored-response"

    monkeypatch.setattr(upstream, "CommandUpstream", FakeCommand)
    monkeypatch.setattr(upstream, "recover_anthropic_response", lambda _: b"authored-response")
    callback = upstream.ScopedAnthropicUpstream(
        tmp_path / "upstream",
        credential_path=tmp_path / "credentials/nonexistent.json",
        lease_id="lease",
        model=MODEL,
        client_read_roots=(tmp_path / "client",),
        max_output_tokens=512,
        deadline_monotonic=time.monotonic() + 3,
    )
    assert callback(b"approved") == b"authored-response"
    folder, arguments = seen[0]
    assert folder == tmp_path / "upstream/attempt"
    command = arguments["command"]
    assert command[1:3] == ("-I", "-S")
    assert Path(command[3]).name == "anthropic_worker.py"
    assert "--support-sha256" in command
    sources = {p.name for p in arguments["source_files"]}
    assert sources == {"anthropic_worker.py", "subscription_worker.py", "policy.json"}
    policy = json.loads((tmp_path / "upstream/policy.json").read_text())
    assert policy["version"] == VERSION and policy["api_version"] == API_VERSION
    assert policy["request_sha256"] == hashlib.sha256(b"approved").hexdigest()
    assert "nonexistent.json" not in repr(arguments["source_files"])
    with pytest.raises(FileExistsError):
        callback(b"approved")
    assert len(seen) == 1


def bound_attempt(tmp_path):
    policy, _lease, raw = inputs(tmp_path)
    worker = Path(upstream.__file__).with_name("anthropic_worker.py").resolve()
    support = Path(upstream.__file__).with_name("subscription_worker.py").resolve()
    python = str(Path(sys.executable).resolve())
    support_sha = hashlib.sha256(support.read_bytes()).hexdigest()
    manifest = {
        "request_sha256": hashlib.sha256(raw).hexdigest(),
        "deadline_monotonic": policy["deadline_monotonic"],
        "command": [
            python,
            "-I",
            "-S",
            str(worker),
            "--support-sha256",
            support_sha,
            "--policy",
            str(tmp_path / "policy.json"),
            "--request",
            "{request}",
            "--response",
            "{response}",
        ],
        "sources": {
            python: "unused-by-this-unit",
            str(worker): hashlib.sha256(worker.read_bytes()).hexdigest(),
            str(support): support_sha,
            str(tmp_path / "policy.json"): hashlib.sha256(
                (tmp_path / "policy.json").read_bytes()
            ).hexdigest(),
        },
    }
    (tmp_path / "attempt/upstream.json").write_text(canonical_json(manifest))
    return policy, manifest


def test_binding_reader_opens_no_credential_and_checks_fixed_command(tmp_path):
    policy, manifest = bound_attempt(tmp_path)
    (tmp_path / "credentials/lease.json").unlink()
    assert upstream.verify_anthropic_attempt(tmp_path) == (policy, manifest)
    manifest["command"][3] = "/unapproved/program"
    (tmp_path / "attempt/upstream.json").write_text(canonical_json(manifest))
    with pytest.raises(ValueError, match="binding"):
        upstream.verify_anthropic_attempt(tmp_path)


def test_provider_receipts_must_match_original_response_and_send_intent(tmp_path, monkeypatch):
    policy, manifest = bound_attempt(tmp_path)
    raw = b'{"authored":true}'
    monkeypatch.setattr(upstream, "recover_command_upstream", lambda _: raw)
    intent = {
        "version": VERSION,
        "api_version": API_VERSION,
        "lease_id": policy["lease_id"],
        "host": "api.anthropic.com",
        "port": 443,
        "path": "/v1/messages",
        "request_sha256": manifest["request_sha256"],
        "automatic_retries": 0,
        "scope": str(tmp_path),
    }
    result = {
        "version": VERSION,
        "api_version": API_VERSION,
        "status": "response_received",
        "phase": "response_body",
        "http_status": 200,
        "body_bytes_read": len(raw),
        "request_may_have_been_sent": True,
        "usage": None,
        "scope": str(tmp_path),
        "remote_stop_verified": False,
    }
    for name, value in (("provider-intent.json", intent), ("provider-result.json", result)):
        (tmp_path / "attempt" / name).write_text(canonical_json(value))
    (tmp_path / "credentials/lease.json").unlink()
    assert upstream.recover_anthropic_response(tmp_path) == raw
    result["http_status"] = 201
    (tmp_path / "attempt/provider-result.json").write_text(canonical_json(result))
    with pytest.raises(ValueError, match="not completed"):
        upstream.recover_anthropic_response(tmp_path)
    result["http_status"] = 200
    (tmp_path / "attempt/provider-result.json").write_text(canonical_json(result))
    intent["automatic_retries"] = 1
    (tmp_path / "attempt/provider-intent.json").write_text(canonical_json(intent))
    with pytest.raises(ValueError, match="send intent"):
        upstream.recover_anthropic_response(tmp_path)


@pytest.mark.parametrize("credential_kind", ["missing", "fifo"])
def test_exact_isolated_command_refuses_before_send_and_cannot_relaunch(tmp_path, credential_kind):
    _policy, _lease, raw = inputs(tmp_path)
    credential = tmp_path / "credentials/lease.json"
    credential.unlink()
    if credential_kind == "fifo":
        os.mkfifo(credential, 0o600)
    launches = []
    callback = upstream.ScopedAnthropicUpstream(
        tmp_path / "owned-upstream",
        credential_path=credential,
        lease_id="test-lease",
        model=MODEL,
        client_read_roots=(tmp_path / "client",),
        max_output_tokens=512,
        deadline_monotonic=time.monotonic() + 5,
        on_launch=launches.append,
    )
    with pytest.raises(UpstreamProcessError, match="host_failure"):
        callback(raw)
    root = callback.directory
    assert len(launches) == 1
    upstream.verify_anthropic_attempt(root)
    assert callback.stop_audit()["state"] == "verified_stopped"
    attempt = root / "attempt"
    result = json.loads((attempt / "provider-result.json").read_text())
    assert result["phase"] == "preflight"
    assert result["request_may_have_been_sent"] is False
    assert result["remote_stop_verified"] is False
    assert not (attempt / "provider-intent.json").exists()
    assert (attempt / "response.bin").read_bytes() == b""
    assert (attempt / "process/stdout.bin").read_bytes() == b""
    assert (attempt / "process/stderr.bin").read_bytes() == b""
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(ValueError):
        upstream.recover_anthropic_response(root)
    with pytest.raises(FileExistsError):
        callback(raw)
    assert len(launches) == 1
    assert before == {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
