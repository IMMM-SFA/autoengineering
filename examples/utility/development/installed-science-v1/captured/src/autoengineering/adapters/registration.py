"""Immutable reviewed source registrations and confined evidence archives.

These records are supplied by trusted application code. Worker handoffs cannot
create a registration or select its trusted identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import io
from pathlib import Path
import stat
from typing import Literal
import zipfile

from autoengineering.agents.interface import InterfaceRecord, InterfaceSpec, InterfaceReceipt
from autoengineering.agents.workspaces import SourceCapture
from autoengineering.campaign.artifacts import confined_file, read_bytes, reference
from autoengineering.campaign.records import Scalar, identifier, sha256, relative_path
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.campaign.serialization import digest

MAX_ARCHIVE_BYTES = 4 * 1024 * 1024
MAX_MEMBERS = 512
FILES = (
    "generated/registration.json",
    "generated/adapter.py",
    "generated/driver.py",
    "generated/evidence.zip",
)

EXECUTION_FILES = (
    "agents/__init__.py",
    "adapters/contracts.py",
    "adapters/python.py",
    "adapters/registration.py",
    "adapters/isolated.py",
    "agents/interface.py",
    "agents/interface_worker.py",
    "agents/workspaces.py",
    "agents/qualification.py",
    "agents/containers.py",
    "agents/container_watchdog.py",
    "agents/container_recovery.py",
    "agents/sandbox.py",
    "campaign/artifacts.py",
    "campaign/serialization.py",
    "campaign/records.py",
    "campaign/store.py",
)


def execution_source_identity():
    """Explicit execution closure. Provider adapters and role prompts are absent."""
    from autoengineering.campaign.identity import scientific_source_paths

    package = Path(__file__).resolve().parents[1]
    core = {
        name.removeprefix("src/autoengineering/")
        for name in scientific_source_paths(package, version="2")
    }
    return digest(
        {
            name: hashlib.sha256(confined_file(package, name).read_bytes()).hexdigest()
            for name in sorted(set(EXECUTION_FILES) | core)
        }
    )


@dataclass(frozen=True)
class AdmissionReview(InterfaceRecord):
    schema_version: Literal["1.0"]
    target: str
    capture_digest: str
    interface_digest: str
    qualification_digest: str
    fixed_parameters: Mapping[str, Scalar]
    reviewer: str
    reason: str
    decision: Literal["approve", "reject"]

    def _validate(self):
        identifier(self.target)
        if self.fixed_parameters:
            raise ValueError("initial registered functions have no tunable parameters")
        for value in (self.capture_digest, self.interface_digest, self.qualification_digest):
            sha256(value)
        if len(self.reviewer) > 256 or len(self.reason) > 2048:
            raise ValueError("admission review exceeds its text allowance")


@dataclass(frozen=True)
class SourceRegistration(InterfaceRecord):
    schema_version: Literal["1.0", "1.1"]
    capture: SourceCapture
    specification: InterfaceSpec
    interface_receipt: InterfaceReceipt
    review: AdmissionReview
    driver_sha256: str
    evidence_sha256: str
    evidence_bytes: int
    execution_identity: str | None = None

    def _validate(self):
        sha256(self.driver_sha256)
        sha256(self.evidence_sha256)
        if self.schema_version == "1.1":
            if self.execution_identity is None:
                raise ValueError("registration requires an explicit execution source identity")
            sha256(self.execution_identity)
        elif self.execution_identity is not None:
            raise ValueError("legacy registration cannot include new execution identity fields")
        if not 0 < self.evidence_bytes <= MAX_ARCHIVE_BYTES:
            raise ValueError("registration evidence exceeds its byte ceiling")
        if (
            self.review.decision != "approve"
            or self.interface_receipt.status != "pass"
            or self.capture.issues
        ):
            raise ValueError("registration requires a trusted approval and passing checks")
        if set(self.capture.sources) != {"adapter.py"}:
            raise ValueError("registration changes the fixed source allowlist")
        if (
            self.review.capture_digest != self.capture.digest
            or self.review.interface_digest != self.interface_receipt.digest
            or self.review.qualification_digest != self.interface_receipt.qualification_digest
            or self.interface_receipt.capture_digest != self.capture.digest
            or self.interface_receipt.source_digest != self.capture.source_digest
            or self.interface_receipt.specification_digest != self.specification.digest
        ):
            raise ValueError("registration review, source and checks have different identities")

    @property
    def adapter_id(self):
        return f"generated-{self.digest}"

    def to_dict(self):
        value = super().to_dict()
        if self.schema_version == "1.0":
            value.pop("execution_identity")
        return value

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, Mapping):
            raise ValueError("registration must be a mapping")
        if value.get("schema_version") == "1.0" and "execution_identity" in value:
            raise ValueError("legacy registration cannot include new execution identity fields")
        return super().from_dict(value)


def make_archive(files: Mapping[str, bytes]) -> bytes:
    """Build a deterministic stored ZIP from an explicit, already verified allowlist."""
    if not 1 <= len(files) <= MAX_MEMBERS or sum(map(len, files.values())) > MAX_ARCHIVE_BYTES:
        raise ValueError("registration evidence envelope exceeds policy")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, raw in sorted(files.items()):
            relative_path(name)
            if (
                name.split("/")[0] not in ("workspace", "qualification", "interface")
                or len(raw) > 65536
            ):
                raise ValueError("registration evidence contains an undeclared member")
            member = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            member.external_attr = (stat.S_IFREG | 0o600) << 16
            archive.writestr(member, raw)
    raw = output.getvalue()
    if len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("registration archive exceeds its byte ceiling")
    return raw


def extract_archive(raw: bytes, output: Path):
    """Check the complete member table before writing any evidence bytes."""
    if type(raw) is not bytes or len(raw) > MAX_ARCHIVE_BYTES:
        raise ValueError("registration archive exceeds its byte ceiling")
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if (
            not 1 <= len(members) <= MAX_MEMBERS
            or sum(m.file_size for m in members) > MAX_ARCHIVE_BYTES
        ):
            raise ValueError("registration archive member allowance exceeded")
        names = set()
        for member in members:
            relative_path(member.filename)
            if (
                member.filename.split("/")[0] not in ("workspace", "qualification", "interface")
                or member.filename.casefold() in names
                or len(member.filename) > 256
                or len(Path(member.filename).parts) > 32
                or member.is_dir()
                or member.file_size > 65536
                or member.compress_type != zipfile.ZIP_STORED
                or member.flag_bits & 1
                or stat.S_IFMT(member.external_attr >> 16) not in (0, stat.S_IFREG)
            ):
                raise ValueError("registration archive has an unsafe or duplicate member")
            names.add(member.filename.casefold())
        if any(
            "/".join(name.split("/")[:index]) in names
            for name in names
            for index in range(1, len(name.split("/")))
        ):
            raise ValueError("registration archive has a file/directory collision")
        output = Path(output).absolute()
        checked_directory(output.parent)
        if output.exists() or output.is_symlink():
            raise ValueError("evidence extraction requires a fresh directory")
        output.mkdir(mode=0o700)
        for member in members:
            path = output / member.filename
            parent = output
            for part in Path(member.filename).parts[:-1]:
                parent = parent / part
                if not parent.exists():
                    parent.mkdir(mode=0o700)
                checked_directory(parent)
            data = archive.read(member)
            if len(data) != member.file_size:
                raise ValueError("registration archive member size mismatch")
            durable_write(path, data)
    # The candidate working directory is deliberately empty. Only captured
    # source artifacts enter the evidence packet, never mutable working bytes.
    (output / "workspace/candidate").mkdir(mode=0o700)


def load_registration(root: Path, *, expected_identity: str):
    root = checked_directory(root)
    path = confined_file(root, FILES[0])
    if path.stat().st_size > 65536:
        raise ValueError("registration exceeds 64 KiB")
    registration = SourceRegistration.from_json(path.read_text())
    if registration.digest != expected_identity:
        raise ValueError("registration differs from the trusted identity")
    if registration.execution_identity != execution_source_identity():
        raise ValueError("registered execution source changed or its identity is unbound")
    refs = tuple(
        reference(
            root, name, media_type="application/octet-stream", producer="trusted-registration"
        )
        for name in FILES
    )
    for ref in refs:
        read_bytes(root, ref, max_bytes=MAX_ARCHIVE_BYTES)
    if (
        refs[1].sha256 != registration.capture.sources["adapter.py"].sha256
        or refs[2].sha256 != registration.driver_sha256
        or refs[3].sha256 != registration.evidence_sha256
        or refs[3].size_bytes != registration.evidence_bytes
    ):
        raise ValueError("registered source, driver or evidence bytes changed")
    driver = confined_file(
        Path(__file__).resolve().parents[1], "agents/interface_worker.py"
    ).read_bytes()
    if hashlib.sha256(driver).hexdigest() != registration.driver_sha256:
        raise ValueError("registered driver differs from the fixed execution harness")
    return registration, refs


def validate_model(registration, refs, model, parameters):
    """Require the exact reviewed component, ports, fixed values and source refs."""
    declared = {ref.path: ref for ref in model.source_bundle}
    if (
        dict(model.implementations) != {registration.review.target: registration.adapter_id}
        or model.inputs != registration.specification.inputs
        or model.outputs != registration.specification.outputs
        or dict(parameters) != dict(registration.review.fixed_parameters)
        or any(declared.get(ref.path) != ref for ref in refs)
    ):
        raise ValueError("model or configuration differs from the reviewed registration")


def verify_evidence(root: Path, registration: SourceRegistration):
    """Verify extracted evidence without importing or executing candidate code."""
    from autoengineering.agents.workspaces import CandidateWorkspace, WorkspaceManifest
    from autoengineering.agents.interface import verify_interface

    workroot = root / "workspace"
    workspace = CandidateWorkspace(
        workroot, WorkspaceManifest.from_json(confined_file(workroot, "manifest.json").read_text())
    )
    return verify_interface(
        root / "interface",
        workspace,
        registration.capture,
        registration.specification,
        qualification_root=root / "qualification",
        qualification_digest=registration.review.qualification_digest,
        expected_receipt_digest=registration.review.interface_digest,
        relocated=True,
    )
