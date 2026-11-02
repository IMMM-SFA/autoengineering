"""Caller-pinned Claude/API boundary attestations, distinct from Codex profiles.

This reader never runs qualification, opens a lease or authorizes provider work.
Only a trusted qualifier may attest observations. Decoder fixtures prove no OS fact.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
import re

from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef, sha256
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory
from .claude import ClaudeInventory, REQUIRED_FLAGS, SUPPORTED_VERSION
from .native_profile import native_runtime, OBSERVATIONS as NATIVE_OBSERVATIONS
from .anthropic_worker import API_VERSION

VERSION = "native-claude-api-boundary-1.0"
INDEX_VERSION = "claude-evidence-index-1.0"
LIMITATIONS = (
    "macos_arm64_only",
    "api_authentication_only",
    "remote_stop_unknown",
    "native_usd_is_estimated",
    "observed_tokens_are_a_stop_rule_not_a_hard_cap",
    "no_hard_memory_cpu_pid_or_home_disk_cap",
)
OBSERVATIONS = unique_json(canonical_json(NATIVE_OBSERVATIONS))
OBSERVATIONS["credentials"] = {
    "process_environment_unavailable_to_client": True,
    "cache_unavailable_to_client": True,
    "api_lease_unavailable_to_client": True,
    "local_capability_is_not_provider_key": True,
    "no_secret_in_client_artifacts": True,
    "no_refresh_retry_or_auth_fallback": True,
}
OBSERVATIONS["accounting"] = {
    "broker_unknowns_preserved": True,
    "rejected_handoff_usage_preserved": True,
    "native_estimate_separate": True,
    "billed_cost_unknown": True,
    "remote_stop_not_inferred": True,
}
OBSERVATIONS["upstream"] = {
    "request_rebuilt_before_lease_read": True,
    "fixed_route_and_api_version": True,
    "tls_hostname_and_certificate_verified": True,
    "reflected_secret_not_saved": True,
    "single_send_intent_durable": True,
    "local_worker_stop_verified": True,
    "replay_no_lease_read_or_send": True,
}


def boundary_source_identity():
    root = Path(__file__).parent
    return digest(
        {
            name: hashlib.sha256(confined_file(root, name).read_bytes()).hexdigest()
            for name in (
                "claude_policy.py",
                "claude.py",
                "claude_brokered.py",
                "anthropic_upstream.py",
                "anthropic_worker.py",
                "subscription_worker.py",
            )
        }
    )


@dataclass(frozen=True)
class VerifiedClaudeProfile:
    root: Path
    receipt_digest: str
    inventory: ClaudeInventory
    model: str
    max_worker_seconds: float
    max_output_bytes: int
    max_workspace_bytes: int
    runtime_identity: str
    max_output_tokens: int
    estimated_budget_usd: float
    limitations: tuple[str, ...] = LIMITATIONS


def _record(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise ValueError("Claude qualification exceeds size limit")
    return path.read_bytes()


def verify_claude_profile(root: Path, *, expected_digest: str) -> VerifiedClaudeProfile:
    """Verify every original artifact and fixed binding, without opening a key."""
    sha256(expected_digest)
    root = checked_directory(root)
    raw = _record(root, "qualification.json")
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("Claude qualification differs from trusted digest")
    value = unique_json(raw.decode())
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "version",
            "status",
            "source_identity",
            "runtime",
            "boundary_source_identity",
            "inventory",
            "model",
            "auth_mode",
            "api_version",
            "limits",
            "limitations",
            "checks",
            "provider_calls",
            "scientific_calls",
        }
        or value["version"] != VERSION
        or value["status"] != "qualified"
        or value["source_identity"] != host_source_identity()
        or value["runtime"] != native_runtime()
        or value["runtime"].get("platform") != "darwin"
        or value["runtime"].get("machine") != "arm64"
        or value["boundary_source_identity"] != boundary_source_identity()
        or value["auth_mode"] != "api"
        or value["api_version"] != API_VERSION
        or value["limitations"] != list(LIMITATIONS)
        or any(
            type(value[k]) is not int or value[k] != 0
            for k in ("provider_calls", "scientific_calls")
        )
    ):
        raise ValueError("Claude qualification incomplete or incompatible")
    inventory = ClaudeInventory(
        **{
            **value["inventory"],
            "supported_flags": tuple(value["inventory"]["supported_flags"]),
        }
    )
    executable = Path(inventory.executable)
    if (
        not executable.is_absolute()
        or inventory.version != SUPPORTED_VERSION
        or inventory.supported_flags != REQUIRED_FLAGS
        or not 0 < confined_file(executable.parent, executable.name).stat().st_size <= 536870912
        or hashlib.sha256(
            confined_file(executable.parent, executable.name).read_bytes()
        ).hexdigest()
        != inventory.sha256
    ):
        raise ValueError("Claude qualified executable changed or unsupported")
    limits = value["limits"]
    if (
        not isinstance(limits, dict)
        or set(limits)
        != {
            "max_worker_seconds",
            "max_output_bytes",
            "max_workspace_bytes",
            "max_output_tokens",
            "estimated_budget_usd",
        }
        or type(limits["max_worker_seconds"]) not in (int, float)
        or not math.isfinite(limits["max_worker_seconds"])
        or not 0 < limits["max_worker_seconds"] <= 3600
        or any(
            type(limits[k]) is not int or not 0 < limits[k] <= 65536
            for k in ("max_output_bytes", "max_workspace_bytes")
        )
        or type(limits["max_output_tokens"]) is not int
        or not 0 < limits["max_output_tokens"] <= 32768
        or type(limits["estimated_budget_usd"]) not in (int, float)
        or not math.isfinite(limits["estimated_budget_usd"])
        or limits["estimated_budget_usd"] <= 0
        or type(value["model"]) is not str
        or re.fullmatch(r"claude-[A-Za-z0-9._-]{1,128}", value["model"]) is None
        or not isinstance(value["checks"], dict)
        or set(value["checks"]) != set(OBSERVATIONS)
    ):
        raise ValueError("invalid Claude profile limits, model or checks")
    bindings = {
        "source_identity": value["source_identity"],
        "runtime_identity": digest(value["runtime"]),
        "inventory_identity": digest(asdict(inventory)),
        "boundary_source_identity": value["boundary_source_identity"],
        "limits": limits,
        "auth_mode": "api",
        "api_version": API_VERSION,
        "model": value["model"],
        "limitations": list(LIMITATIONS),
    }
    verified = set()
    for name, observed in OBSERVATIONS.items():
        check = unique_json(
            read_bytes(root, ArtifactRef.from_dict(value["checks"][name]), max_bytes=65536).decode()
        )
        if (
            set(check) != {"version", "name", "status", "bindings", "observed", "evidence"}
            or check["version"] != VERSION
            or check["name"] != name
            or check["status"] != "passed"
            or canonical_json(check["bindings"]) != canonical_json(bindings)
            or canonical_json(check["observed"]) != canonical_json(observed)
            or not isinstance(check["evidence"], list)
            or not 1 <= len(check["evidence"]) <= 32
        ):
            raise ValueError("Claude qualification has failed, missing or foreign checks")
        indexes = []
        for item in check["evidence"]:
            ref = ArtifactRef.from_dict(item)
            body = read_bytes(root, ref, max_bytes=1048576)
            if ref.metadata.get("kind") != INDEX_VERSION:
                continue
            indexes.append(ref.sha256)
            if ref.sha256 in verified:
                continue
            index = unique_json(body.decode())
            if (
                set(index) != {"version", "bindings", "files", "total_bytes"}
                or index["version"] != INDEX_VERSION
                or canonical_json(index["bindings"]) != canonical_json(bindings)
                or not isinstance(index["files"], list)
                or not 1 <= len(index["files"]) <= 1024
                or type(index["total_bytes"]) is not int
                or not 0 < index["total_bytes"] <= 67108864
            ):
                raise ValueError("invalid Claude raw evidence index")
            refs = [ArtifactRef.from_dict(item) for item in index["files"]]
            if (
                len({ref.path for ref in refs}) != len(refs)
                or sum(ref.size_bytes for ref in refs) != index["total_bytes"]
            ):
                raise ValueError("Claude evidence index duplicates or size mismatch")
            for ref in refs:
                read_bytes(root, ref, max_bytes=1048576)
            verified.add(indexes[-1])
        if len(indexes) != 1:
            raise ValueError("Claude check requires one raw evidence index")
    return VerifiedClaudeProfile(
        root,
        expected_digest,
        inventory,
        value["model"],
        limits["max_worker_seconds"],
        limits["max_output_bytes"],
        limits["max_workspace_bytes"],
        digest(value["runtime"]),
        limits["max_output_tokens"],
        limits["estimated_budget_usd"],
    )
