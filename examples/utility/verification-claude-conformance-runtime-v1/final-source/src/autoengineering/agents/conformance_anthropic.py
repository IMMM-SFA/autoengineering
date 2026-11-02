"""Verify original Anthropic conformance receipts without credentials or dispatch."""

from __future__ import annotations

import hashlib

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, unique_json
from .hosts.anthropic_upstream import verify_anthropic_attempt, recover_anthropic_response
from .hosts.anthropic_worker import VERSION, API_VERSION
from .hosts.command_upstream import inspect_command_stop


def _record(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise ValueError("Anthropic conformance metadata exceeds bound")
    return unique_json(path.read_text())


def _policy(runtime, scope):
    policy, manifest = verify_anthropic_attempt(scope / "upstream")
    if (policy["model"], policy["lease_id"], policy["credential_path"]) != (
        runtime.plan.worker.host.requested_model,
        runtime.configuration.lease_id,
        str(runtime.configuration.credential_path),
    ):
        raise ValueError("Anthropic conformance provider scope mismatch")
    return policy, manifest


def response_evidence(runtime, scope):
    """A completed fixed API worker proves received bytes, never remote stopping."""
    try:
        policy, manifest = _policy(runtime, scope)
        response = recover_anthropic_response(scope / "upstream")
        attempt = scope / "upstream/attempt"
        body_hash = hashlib.sha256(response).hexdigest()
        return {
            "verified": True,
            "evidence": runtime.batch.evidence(
                {
                    "kind": "fixed_anthropic_response_metadata",
                    "policy": policy,
                    "command_manifest": manifest,
                    "provider_result": _record(attempt, "provider-result.json"),
                    "provider_intent": _record(attempt, "provider-intent.json"),
                    "command_completion": _record(attempt / "process", "completion.json"),
                    "response_sha256": body_hash,
                }
            ).to_dict(),
            "response_sha256": body_hash,
            "remote_computation_stopped": "unknown",
            "metadata_hashes": {
                name: hashlib.sha256(confined_file(attempt, name).read_bytes()).hexdigest()
                for name in ("provider-result.json", "provider-intent.json")
            },
        }
    except (ValueError, OSError, KeyError, TypeError):
        return {"verified": False, "reason": "fixed_anthropic_response_proof_unavailable"}


def request_evidence(runtime, scope, *, require_stop=True):
    """A durable API send intent is possible dispatch, not provider acceptance."""
    try:
        policy, manifest = _policy(runtime, scope)
        attempt = scope / "upstream/attempt"
        intent = _record(attempt, "provider-intent.json")
        expected = {
            "version": VERSION,
            "api_version": API_VERSION,
            "lease_id": policy["lease_id"],
            "host": "api.anthropic.com",
            "port": 443,
            "path": "/v1/messages",
            "request_sha256": policy["request_sha256"],
            "automatic_retries": 0,
            "scope": str(scope / "upstream"),
        }
        valid = canonical_json(intent) == canonical_json(expected)
        stopped = inspect_command_stop(attempt) if require_stop else None
        if require_stop:
            valid = valid and stopped["state"] == "verified_stopped"
        return {
            "verified": valid,
            "evidence": runtime.batch.evidence(
                {
                    "kind": "fixed_anthropic_request_metadata",
                    "policy": policy,
                    "command_manifest": manifest,
                    "provider_intent": intent,
                    "stop_audit": stopped,
                }
            ).to_dict()
            if require_stop
            else None,
            "request_may_have_been_sent": True if valid else None,
            "remote_computation_stopped": "unknown",
            "intent_sha256": hashlib.sha256(
                confined_file(attempt, "provider-intent.json").read_bytes()
            ).hexdigest(),
        }
    except (ValueError, OSError, KeyError, TypeError):
        return {"verified": False, "request_may_have_been_sent": None}
