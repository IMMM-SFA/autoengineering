"""Verify caller-pinned native boundary evidence. This does not run probes.

Only a trusted qualifier may supply this root and digest. Worker handoffs cannot
choose them. Current development fixtures are not a qualified production profile.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import platform
import ssl
import subprocess
import sys

from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef, sha256
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory

from .codex import CodexInventory
from .model_catalog import validate_model_catalog

VERSION = "native-codex-boundary-1.3"
INDEX_VERSION = "native-evidence-index-1.0"
OBSERVATIONS = {
    "preferences": {
        "private_preference_read_denied": True,
        "workspace_preference_read_denied": True,
        "unapproved_preference_shm_denied": True,
    },
    "filesystem": {
        "private_read_denied": True,
        "checkout_read_denied": True,
        "evaluator_read_denied": True,
        "write_outside_denied": True,
        "allowed_read_succeeded": True,
    },
    "symlinks": {"read_escape_denied": True, "write_escape_denied": True},
    "network": {
        "unapproved_tcp_denied": True,
        "unapproved_unix_denied": True,
        "endpoint_allowed": True,
    },
    "tools": {"forbidden_response_rejected": True, "native_tool_executions": 0},
    "credentials": {
        "process_environment_unavailable_to_client": True,
        "cache_unavailable_to_client": True,
        "lease_unavailable_to_client": True,
        "no_secret_in_client_artifacts": True,
    },
    "lifecycle": {
        "timeout_stopped": True,
        "cancel_stopped": True,
        "parent_death_stopped": True,
        "replay_no_relaunch": True,
        "missing_completion_not_success": True,
    },
    "bounds": {
        "output_limit_enforced": True,
        "read_deadline_enforced": True,
        "workspace_limit_enforced": True,
    },
    "native": {"client_started": True, "text_roundtrip": True, "client_stopped": True},
}


def native_runtime():
    """OS/TLS runtime binding, separate from the legacy worker environment ID."""
    # Match the upstream worker's clean environment. Only public CA certificate
    # fingerprints are returned, never private key or authentication material.
    code = (
        "import hashlib,json,ssl\n"
        "context=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)\ncontext.load_default_certs()\n"
        "roots=sorted(hashlib.sha256(cert).hexdigest() for cert in context.get_ca_certs(binary_form=True))\n"
        "print(json.dumps(roots,separators=(',',':')))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", code],
        capture_output=True,
        timeout=5,
        env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        check=False,
    )
    if result.returncode or len(result.stdout) > 65536 or result.stderr:
        raise ValueError("native public trust inventory is unavailable")
    roots = unique_json(result.stdout.decode())
    if (
        not isinstance(roots, list)
        or not roots
        or any(type(value) is not str or len(value) != 64 for value in roots)
    ):
        raise ValueError("invalid native public trust inventory")
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": sys.platform,
        "machine": platform.machine(),
        "os_release": platform.release(),
        "os_version": platform.version(),
        "tls_library": ssl.OPENSSL_VERSION,
        "public_trust_identity": digest(roots),
        "python_sha256": hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),
    }


def boundary_source_identity():
    return hashlib.sha256(Path(__file__).with_name("native_policy.py").read_bytes()).hexdigest()


@dataclass(frozen=True)
class VerifiedNativeProfile:
    root: Path
    receipt_digest: str
    inventory: CodexInventory
    model: str
    max_worker_seconds: float
    max_output_bytes: int
    max_workspace_bytes: int
    runtime_identity: str
    model_catalog: bytes | None = None


def verify_native_profile(root: Path, *, expected_digest: str) -> VerifiedNativeProfile:
    """Verify a source/runtime-bound trusted qualification and every artifact.

    Observations are attestations of the trusted qualifier, not claims that this
    reader executed a canary. Hashes alone do not establish their truth. The
    caller must pin evidence produced by the reviewed qualification procedure.
    """
    sha256(expected_digest)
    root = checked_directory(root)
    path = confined_file(root, "qualification.json")
    if path.stat().st_size > 65536:
        raise ValueError("native qualification exceeds size limit")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise ValueError("native qualification differs from trusted digest")
    value = unique_json(raw.decode())
    if (
        not isinstance(value, dict)
        or set(value) - {"model_catalog"}
        != {
            "version",
            "status",
            "source_identity",
            "runtime",
            "boundary_source_identity",
            "inventory",
            "model",
            "limits",
            "checks",
            "provider_calls",
            "scientific_calls",
        }
        or value["version"] != VERSION
        or value["status"] != "qualified"
        or value["source_identity"] != host_source_identity()
        or value["runtime"] != native_runtime()
        or value["boundary_source_identity"] != boundary_source_identity()
        or type(value["provider_calls"]) is not int
        or value["provider_calls"] != 0
        or type(value["scientific_calls"]) is not int
        or value["scientific_calls"] != 0
    ):
        raise ValueError("native qualification incomplete or incompatible")
    if value["runtime"]["platform"] != "darwin" or value["runtime"]["machine"] != "arm64":
        raise ValueError("native boundary platform is unsupported")
    inventory = CodexInventory(
        **{**value["inventory"], "supported_flags": tuple(value["inventory"]["supported_flags"])}
    )
    executable = Path(inventory.executable)
    if (
        hashlib.sha256(confined_file(executable.parent, executable.name).read_bytes()).hexdigest()
        != inventory.sha256
    ):
        raise ValueError("qualified native executable changed")
    limits = value["limits"]
    if (
        set(limits) != {"max_worker_seconds", "max_output_bytes", "max_workspace_bytes"}
        or any(
            type(v) not in (int, float) or not 0 < v <= 3600
            for k, v in limits.items()
            if k == "max_worker_seconds"
        )
        or any(
            type(limits[k]) is not int or not 0 < limits[k] <= 65536
            for k in ("max_output_bytes", "max_workspace_bytes")
        )
        or type(value["model"]) is not str
        or not value["model"].strip()
        or set(value["checks"]) != set(OBSERVATIONS)
    ):
        raise ValueError("invalid native qualification limits or check set")
    verified_indexes = set()
    catalog = None
    if value.get("model_catalog") is not None:
        catalog = read_bytes(root, ArtifactRef.from_dict(value["model_catalog"]), max_bytes=65536)
        validate_model_catalog(catalog, value["model"])
    for name, observed in OBSERVATIONS.items():
        ref = ArtifactRef.from_dict(value["checks"][name])
        check = unique_json(read_bytes(root, ref, max_bytes=65536).decode())
        if (
            set(check) != {"version", "name", "status", "bindings", "observed", "evidence"}
            or check["version"] != VERSION
            or check["name"] != name
            or check["status"] != "passed"
            or check["bindings"]
            != {
                "source_identity": value["source_identity"],
                "runtime_identity": digest(value["runtime"]),
                "inventory_identity": digest(asdict(inventory)),
                "boundary_source_identity": value["boundary_source_identity"],
                "limits": limits,
            }
            or canonical_json(check["observed"]) != canonical_json(observed)
            or not isinstance(check["evidence"], list)
            or not 1 <= len(check["evidence"]) <= 32
        ):
            raise ValueError("native qualification has failed, missing or foreign checks")
        indexes = []
        for artifact in check["evidence"]:
            ref = ArtifactRef.from_dict(artifact)
            raw_artifact = read_bytes(root, ref, max_bytes=1048576)
            if ref.metadata.get("kind") == INDEX_VERSION:
                indexes.append(ref.sha256)
                if ref.sha256 not in verified_indexes:
                    index = unique_json(raw_artifact.decode())
                    if (
                        not isinstance(index, dict)
                        or set(index) != {"version", "bindings", "files", "total_bytes"}
                        or index["version"] != INDEX_VERSION
                        or index["bindings"] != check["bindings"]
                        or not isinstance(index["files"], list)
                        or not 1 <= len(index["files"]) <= 1024
                        or type(index["total_bytes"]) is not int
                        or not 0 < index["total_bytes"] <= 67108864
                    ):
                        raise ValueError("invalid native evidence index")
                    refs = [ArtifactRef.from_dict(item) for item in index["files"]]
                    if (
                        len({item.path for item in refs}) != len(refs)
                        or sum(item.size_bytes for item in refs) != index["total_bytes"]
                    ):
                        raise ValueError("native evidence index has duplicate paths or wrong size")
                    for item in refs:
                        read_bytes(root, item, max_bytes=1048576)
                    verified_indexes.add(ref.sha256)
        if len(indexes) != 1:
            raise ValueError("native qualification requires one raw evidence index per check")
    return VerifiedNativeProfile(
        root,
        expected_digest,
        inventory,
        value["model"],
        limits["max_worker_seconds"],
        limits["max_output_bytes"],
        limits["max_workspace_bytes"],
        digest(value["runtime"]),
        catalog,
    )
