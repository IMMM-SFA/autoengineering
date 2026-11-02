"""API receipt readers with authored bytes and explicit lower-level proof stubs."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from autoengineering.agents import conformance_anthropic as proof
from autoengineering.agents.hosts import anthropic_upstream
from autoengineering.agents.hosts.anthropic_worker import VERSION, API_VERSION
from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.serialization import canonical_json
from test_agent_anthropic_upstream import bound_attempt


def records(tmp_path, monkeypatch):
    (tmp_path / "artifacts").mkdir(mode=0o700)
    scope = tmp_path / "call"
    scope.mkdir(mode=0o700)
    root = scope / "upstream"
    root.mkdir(mode=0o700)
    policy, manifest = bound_attempt(root)
    raw = b'{"authored":true}'
    # Original process verification is covered by the upstream tests. Here only
    # the conformance reader is exercised; these stubs attest no owned process.
    monkeypatch.setattr(anthropic_upstream, "recover_command_upstream", lambda _: raw)
    monkeypatch.setattr(proof, "inspect_command_stop", lambda _: {"state": "verified_stopped"})
    intent = {
        "version": VERSION,
        "api_version": API_VERSION,
        "lease_id": policy["lease_id"],
        "host": "api.anthropic.com",
        "port": 443,
        "path": "/v1/messages",
        "request_sha256": manifest["request_sha256"],
        "automatic_retries": 0,
        "scope": str(root),
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
        "scope": str(root),
        "remote_stop_verified": False,
    }
    for name, value in (("provider-intent.json", intent), ("provider-result.json", result)):
        (root / "attempt" / name).write_text(canonical_json(value))
    (root / "attempt/process").mkdir(mode=0o700)
    (root / "attempt/process/completion.json").write_text('{"unit_attestation_only":true}')
    credential = Path(policy["credential_path"])
    credential.unlink()
    original = Path.open

    def deny_key(path, *args, **kwargs):
        if path == credential:
            pytest.fail("proof reader opened credential")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", deny_key)

    def evidence(value):
        return put_bytes(
            tmp_path,
            canonical_json(value).encode(),
            name="proof.json",
            media_type="application/json",
            producer="unit-fixture",
        )

    runtime = SimpleNamespace(
        plan=SimpleNamespace(
            worker=SimpleNamespace(host=SimpleNamespace(requested_model=policy["model"]))
        ),
        configuration=SimpleNamespace(credential_path=credential, lease_id=policy["lease_id"]),
        batch=SimpleNamespace(evidence=evidence),
    )
    assert proof.request_evidence(runtime, scope)["verified"]
    assert proof.response_evidence(runtime, scope)["verified"]
    return runtime, scope, intent, result, raw


def test_original_api_proofs_keep_remote_stop_unknown_without_key_access(tmp_path, monkeypatch):
    runtime, scope, _, _, raw = records(tmp_path, monkeypatch)
    response = proof.response_evidence(runtime, scope)
    request = proof.request_evidence(runtime, scope)
    assert response["verified"] and request["verified"]
    assert response["response_sha256"] == hashlib.sha256(raw).hexdigest()
    assert (
        response["remote_computation_stopped"] == request["remote_computation_stopped"] == "unknown"
    )
    assert proof.request_evidence(runtime, scope, require_stop=False)["evidence"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("api_version", "foreign"),
        ("host", "chatgpt.com"),
        ("path", "/backend-api/codex/responses"),
        ("automatic_retries", 1),
        ("request_sha256", "f" * 64),
        ("port", 80),
    ],
)
def test_foreign_or_retrying_send_intent_is_never_accepted(tmp_path, monkeypatch, field, value):
    runtime, scope, intent, _, _ = records(tmp_path, monkeypatch)
    intent[field] = value
    (scope / "upstream/attempt/provider-intent.json").write_text(json.dumps(intent))
    assert not proof.request_evidence(runtime, scope)["verified"]
    assert not proof.response_evidence(runtime, scope)["verified"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("http_status", 201),
        ("remote_stop_verified", True),
        ("body_bytes_read", 999),
    ],
)
def test_changed_response_evidence_is_refused(tmp_path, monkeypatch, field, value):
    runtime, scope, _, result, _ = records(tmp_path, monkeypatch)
    result[field] = value
    (scope / "upstream/attempt/provider-result.json").write_text(json.dumps(result))
    assert not proof.response_evidence(runtime, scope)["verified"]


def test_unknown_local_stop_is_not_a_verified_request(tmp_path, monkeypatch):
    runtime, scope, _, _, _ = records(tmp_path, monkeypatch)
    monkeypatch.setattr(proof, "inspect_command_stop", lambda _: {"state": "unknown"})
    assert not proof.request_evidence(runtime, scope)["verified"]
    # The cancellation monitor can still observe the original durable intent.
    assert proof.request_evidence(runtime, scope, require_stop=False)["verified"]


@pytest.mark.parametrize("binding", ["model", "lease", "credential"])
def test_provider_scope_cannot_cross_the_prepared_configuration(tmp_path, monkeypatch, binding):
    runtime, scope, _, _, _ = records(tmp_path, monkeypatch)
    if binding == "model":
        runtime.plan.worker.host.requested_model = "claude-other"
    elif binding == "lease":
        runtime.configuration.lease_id = "other"
    else:
        runtime.configuration.credential_path = tmp_path / "other-key"
    assert not proof.request_evidence(runtime, scope)["verified"]
    assert not proof.response_evidence(runtime, scope)["verified"]
