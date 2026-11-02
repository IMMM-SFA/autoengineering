"""Candidate guest identity/transport checks. No image or execution admission.

The fixed worker can verify a pinned Linux runtime and relocated input scope.
Only an eventual qualified owner-side launcher can attest the actual image,
enforced limits, original start/stop and complete selection/access barrier.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import re
import sys
import hashlib
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest, unique_json
from .contracts import sha256

LIMITS = (
    ("memory_bytes", 1073741824),
    ("cpu_count", 1),
    ("pids", 16),
    ("workspace_bytes", 134217728),
    ("network", "none"),
    ("read_only_root", True),
    ("timeout_seconds", 60),
)


@dataclass(frozen=True)
class GuestPythonIdentity(Record):
    schema: Literal["utility-guest-python-identity-v1"]
    system: Literal["Linux"]
    architecture: Literal["x86_64"]
    implementation: Literal["CPython"]
    version: str
    build_digest: str

    def _validate(self):
        sha256(self.build_digest)
        if not re.fullmatch(r"3\.12\.[0-9]+", self.version):
            raise ValueError("guest inference requires Python 3.12")


def observe_python():
    """Observe this process; a host mismatch refuses before driver/model reads."""
    return GuestPythonIdentity(
        "utility-guest-python-identity-v1",
        platform.system(),
        platform.machine(),
        platform.python_implementation(),
        ".".join(map(str, sys.version_info[:3])),
        hashlib.sha256(sys.version.encode()).hexdigest(),
    )


@dataclass(frozen=True)
class FrozenGuestProfile(Record):
    schema: Literal["utility-frozen-guest-profile-v1"]
    environment_inputs_digest: str
    lock_digest: str
    wheel_digest: str
    wheel_python_sources_digest: str
    image_id: str
    python: GuestPythonIdentity
    limits_digest: str
    boundary: Literal["unqualified-candidate"]

    def _validate(self):
        for value in (
            self.environment_inputs_digest,
            self.lock_digest,
            self.wheel_digest,
            self.wheel_python_sources_digest,
            self.limits_digest,
        ):
            sha256(value)
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.image_id):
            raise ValueError("guest inference needs an explicit immutable image identity")
        if self.limits_digest != digest(dict(LIMITS)):
            raise ValueError("guest inference resource profile is unsupported")

    def validate_environment(self, document):
        """Verify pinned metadata, never install or independently re-solve packages."""
        if (
            not isinstance(document, dict)
            or document.get("schema") != "utility-inference-environment-inputs-v1"
            or digest(document) != self.environment_inputs_digest
            or document.get("platform") != "linux-64"
            or document.get("environment") != "default"
            or document.get("starts_authorized") is not False
            or document.get("runtime_qualified") is not False
            or document.get("dependency_constraints_rechecked") is not False
        ):
            raise ValueError("guest environment metadata differs from its pinned inputs")
        lock, wheel = (ArtifactRef.from_dict(document[k]) for k in ("lock", "wheel"))
        sources = tuple(ArtifactRef.from_dict(r) for r in document["wheel_python_sources"])
        if (
            lock.sha256 != self.lock_digest
            or wheel.sha256 != self.wheel_digest
            or digest([r.to_dict() for r in sources]) != self.wheel_python_sources_digest
            or len({r.path for r in sources}) != len(sources)
            or any(r.media_type != "text/x-python" or not r.path.endswith(".py") for r in sources)
            or "autoengineering/utility/inference_guest.py" not in {r.path for r in sources}
        ):
            raise ValueError("guest environment lock/wheel/code binding differs")
        python = [p for p in document["archives"] if p["name"] == "python"]
        if len(python) != 1 or python[0]["version"] != self.python.version:
            raise ValueError("guest Python differs from the locked environment")
        return sources


def guest_executor_identity(source_digest, lock_digest, profile):
    sha256(source_digest)
    sha256(lock_digest)
    return digest(
        {
            "profile": "frozen-routing-guest-candidate-v1",
            "sources": source_digest,
            "lock": lock_digest,
            "guest": profile.to_dict(),
        }
    )


def guest_scope(job):
    """Opaque original scope identity, independent of host/guest file paths."""
    return digest(
        {
            "profile": "frozen-routing-guest-scope-v1",
            "grant": job.grant.digest,
            "executor": job.executor_digest,
            "nonce": job.nonce,
        }
    )


def package_root():
    # A built/installed wheel has autoengineering and examples below the same root.
    return Path(__file__).resolve().parents[2]


def validate_guest_context(job, root):
    """Validate observed interpreter and installed code before reading driver bytes.

    This cannot observe an OCI image ID or enforce OS resource/privacy policy.
    The future owner-side execution receipt must independently bind those facts.
    """
    if observe_python() != job.guest.python:
        raise ValueError("guest interpreter differs from its registered runtime")
    document = unique_json(read_bytes(root, job.environment, max_bytes=4 * 1024 * 1024).decode())
    sources = job.guest.validate_environment(document)
    declared = {r.path: r for r in sources}
    origin = package_root()
    package = origin / "autoengineering"
    for path in package.rglob("*.py"):
        name = str(path.relative_to(origin))
        if name not in declared:
            raise ValueError("guest wheel omits installed core source")
    if not package.is_dir():
        raise ValueError("guest execution requires the fixed wheel package layout")
    for ref in sources:
        if not (ref.path.startswith("autoengineering/") or ref.path.startswith("examples/")):
            raise ValueError("guest wheel source is outside the fixed package layout")
        read_bytes(origin, ref)
