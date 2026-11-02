"""Saved native proof bindings with explicit unit-only transport verifiers."""

import json
from types import SimpleNamespace

import pytest

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.serialization import canonical_json
from examples.agent_campaign.native_evidence import (
    PROVIDER_BINDINGS,
    capture_provider,
    verify_provider,
)

H = "a" * 64


def fixture(tmp_path, monkeypatch, *, stubs=True):
    from autoengineering.agents.hosts import subscription
    from autoengineering.agents.hosts.response_boundary import validate_text_response
    from examples.agent_campaign.check_brokered_scheduler_fixture import authored_stream

    root = tmp_path / "batch"
    root.mkdir(mode=0o700)
    (root / "artifacts").mkdir(mode=0o700)
    worker = SimpleNamespace(
        root=root / "worker", spec=SimpleNamespace(host=SimpleNamespace(requested_model="model"))
    )
    raw = authored_stream('{"handoff_json":"{}"}')
    decoded = validate_text_response(raw)
    call = SimpleNamespace(
        id="call-000001", digest=H, resolved_model=decoded.reported_model, usage=decoded.usage
    )
    config = SimpleNamespace(lease_id="fixture", credential_path=tmp_path / "never-open", digest=H)
    batch = SimpleNamespace(root=root, spec=SimpleNamespace(host_configuration_digest=H))
    batch.evidence = lambda doc: put_bytes(
        root,
        canonical_json(doc).encode(),
        name="proof.json",
        media_type="application/json",
        producer="fixture",
    )
    scope = worker.root / "processes" / call.id
    for name in PROVIDER_BINDINGS:
        path = scope / name
        for parent in reversed(path.parents):
            if parent.is_relative_to(root):
                parent.mkdir(mode=0o700, exist_ok=True)
        path.write_bytes(b"fixture" if name.endswith(".bin") else b"{}")
    policy = {
        "model": "model",
        "lease_id": "fixture",
        "credential_path": str(config.credential_path),
        "request_sha256": H,
    }
    intent = {
        "host": "chatgpt.com",
        "port": 443,
        "path": "/backend-api/codex/responses",
        "automatic_retries": 0,
        "lease_id": "fixture",
        "request_sha256": H,
        "scope": str(scope / "upstream"),
    }
    result = {
        "status": "response_received",
        "http_status": 200,
        "request_may_have_been_sent": True,
        "scope": str(scope / "upstream"),
    }
    (scope / "upstream/attempt/provider-intent.json").write_text(json.dumps(intent))
    (scope / "upstream/attempt/provider-result.json").write_text(json.dumps(result))
    (scope / "upstream/attempt/response.bin").write_bytes(raw)
    if stubs:
        monkeypatch.setattr(
            subscription,
            "verify_subscription_attempt",
            lambda *a: (policy, {"unit_attestation_only": True}),
        )
        monkeypatch.setattr(subscription, "recover_subscription_response", lambda *a: raw)
    return batch, worker, call, config, scope, policy


def test_real_fixed_worker_verifier_rejects_authored_metadata(tmp_path, monkeypatch):
    batch, worker, call, config, scope, policy = fixture(tmp_path, monkeypatch, stubs=False)
    proof = capture_provider(batch, worker, call, config)
    assert not proof["verified"] and proof["reason"] == "fixed_worker_response_proof_unavailable"
    assert not config.credential_path.exists()


def test_authored_proof_roundtrip_without_host_import_on_reader(tmp_path, monkeypatch):
    batch, worker, call, config, scope, policy = fixture(tmp_path, monkeypatch)
    proof = capture_provider(batch, worker, call, config)
    assert proof["verified"] and verify_provider(batch, worker, call, proof)
    assert not verify_provider(batch, worker, call, {**proof, "unit_attestation_only": True})
    assert not config.credential_path.exists()


@pytest.mark.parametrize("name", PROVIDER_BINDINGS)
def test_changed_transport_evidence_fails_readonly_reconstruction(tmp_path, monkeypatch, name):
    batch, worker, call, config, scope, policy = fixture(tmp_path, monkeypatch)
    proof = capture_provider(batch, worker, call, config)
    (scope / name).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed after verdict"):
        verify_provider(batch, worker, call, proof)


@pytest.mark.parametrize(
    "problem", ["requested-model", "observed-model", "lease", "scope", "retry"]
)
def test_capture_does_not_verify_missing_or_mismatched_provider_identity(
    tmp_path, monkeypatch, problem
):
    batch, worker, call, config, scope, policy = fixture(tmp_path, monkeypatch)
    if problem == "requested-model":
        policy["model"] = "other"
    elif problem == "observed-model":
        call.resolved_model = None
    elif problem == "lease":
        policy["lease_id"] = "other"
    else:
        path = scope / "upstream/attempt/provider-intent.json"
        data = json.loads(path.read_text())
        data["scope" if problem == "scope" else "automatic_retries"] = (
            "other" if problem == "scope" else 1
        )
        path.write_text(json.dumps(data))
    assert capture_provider(batch, worker, call, config)["verified"] is False


@pytest.mark.parametrize("problem", ["call", "model", "configuration", "oversize"])
def test_proof_reader_rejects_changed_call_configuration_or_oversize(
    tmp_path, monkeypatch, problem
):
    batch, worker, call, config, scope, policy = fixture(tmp_path, monkeypatch)
    proof = capture_provider(batch, worker, call, config)
    if problem == "call":
        call.digest = "b" * 64
    elif problem == "model":
        call.resolved_model = "other"
    elif problem == "configuration":
        batch.spec.host_configuration_digest = "b" * 64
    else:
        (scope / "upstream/attempt/response.bin").write_bytes(b"x" * 1048577)
    with pytest.raises(ValueError):
        verify_provider(batch, worker, call, proof)
