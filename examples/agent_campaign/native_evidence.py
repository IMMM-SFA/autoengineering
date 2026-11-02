"""Capture fixed-worker proof and reread it without loading a host or model."""

from __future__ import annotations

import hashlib

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.store import StoreError

from .comparison_status import read_json

PROVIDER_BINDINGS = (
    "adapter.json",
    "upstream/policy.json",
    "upstream/attempt/upstream.json",
    "upstream/attempt/provider-intent.json",
    "upstream/attempt/provider-result.json",
    "upstream/attempt/request.bin",
    "upstream/attempt/response.bin",
    "upstream/attempt/response.json",
    "upstream/attempt/process/job.json",
    "upstream/attempt/process/intent.json",
    "upstream/attempt/process/process.json",
    "upstream/attempt/process/completion.json",
)


def file_digest(root, name):
    with confined_file(root, name).open("rb") as stream:
        raw = stream.read(1048577 if name.endswith(".bin") else 65537)
    if len(raw) > (1048576 if name.endswith(".bin") else 65536):
        raise StoreError("native proof artifact exceeds allowance")
    return hashlib.sha256(raw).hexdigest()


def capture_provider(batch, worker, call, configuration):
    """Read the original fixed-worker receipts. Never request or open a lease."""
    from autoengineering.agents.hosts.subscription import (
        verify_subscription_attempt,
        recover_subscription_response,
    )
    from autoengineering.agents.hosts.subscription_worker import HOST, PORT, ROUTE
    from autoengineering.agents.hosts.response_boundary import validate_text_response

    scope = worker.root / "processes" / call.id
    try:
        policy, manifest = verify_subscription_attempt(scope / "upstream")
        attempt = scope / "upstream/attempt"
        response = recover_subscription_response(scope / "upstream")
        decoded = validate_text_response(response, max_text_bytes=65536)
        result = read_json(attempt, "provider-result.json")
        intent = read_json(attempt, "provider-intent.json")
        valid = (
            (policy["model"], policy["lease_id"], policy["credential_path"])
            == (
                worker.spec.host.requested_model,
                configuration.lease_id,
                str(configuration.credential_path),
            )
            and result["status"] == "response_received"
            and result["http_status"] == 200
            and result["request_may_have_been_sent"] is True
            and result["scope"] == str(scope / "upstream")
            and (intent["host"], intent["port"], intent["path"], intent["automatic_retries"])
            == (HOST, PORT, ROUTE, 0)
            and intent["lease_id"] == configuration.lease_id
            and intent["request_sha256"] == policy["request_sha256"]
            and intent["scope"] == result["scope"]
            and isinstance(call.resolved_model, str)
            and bool(call.resolved_model.strip())
            and decoded.reported_model == call.resolved_model
            and dict(decoded.usage) == dict(call.usage)
        )
        bindings = {n: file_digest(scope, n) for n in PROVIDER_BINDINGS}
        proof = {
            "kind": "matched_fixed_worker_response",
            "call_digest": call.digest,
            "resolved_model": call.resolved_model,
            "observed_usage": dict(decoded.usage),
            "configuration_digest": configuration.digest,
            "policy": policy,
            "command_manifest": manifest,
            "provider_result": result,
            "provider_intent": intent,
            "response_sha256": hashlib.sha256(response).hexdigest(),
            "bindings": bindings,
        }
        return {"verified": bool(valid), "evidence": batch.evidence(proof).to_dict()}
    except (ValueError, OSError, KeyError, TypeError):
        return {"verified": False, "reason": "fixed_worker_response_proof_unavailable"}


def verify_provider(batch, worker, call, proof):
    """Verify all saved proof bindings without host imports or credential reads."""
    if proof.get("verified") is not True or proof.get("unit_attestation_only"):
        return False
    value = read_json_artifact(batch, proof["evidence"])
    if (
        value["kind"] != "matched_fixed_worker_response"
        or value["call_digest"] != call.digest
        or not call.resolved_model
        or value["resolved_model"] != call.resolved_model
        or value["observed_usage"] != dict(call.usage)
        or value["configuration_digest"] != batch.spec.host_configuration_digest
        or set(value["bindings"]) != set(PROVIDER_BINDINGS)
    ):
        raise StoreError("native provider proof differs from worker/configuration")
    scope = worker.root / "processes" / call.id
    for name, expected in value["bindings"].items():
        if file_digest(scope, name) != expected:
            raise StoreError("native provider evidence changed after verdict")
    return True


def read_json_artifact(batch, ref):
    from autoengineering.campaign.serialization import unique_json

    return unique_json(read_bytes(batch.root, ArtifactRef.from_dict(ref), max_bytes=65536).decode())
