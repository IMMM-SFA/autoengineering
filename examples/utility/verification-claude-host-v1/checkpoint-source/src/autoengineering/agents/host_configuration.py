"""Explicit local host metadata. Loading this file never opens a credential."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.records import identifier, sha256
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import checked_directory


@dataclass(frozen=True)
class HostConfiguration:
    qualification_root: Path
    qualification_digest: str
    credential_path: Path
    lease_id: str
    schema_version: str = "1.0"
    host_kind: str = "codex"
    auth_mode: str = "subscription"

    def __post_init__(self):
        if (self.schema_version, self.host_kind, self.auth_mode) not in (
            ("1.0", "codex", "subscription"),
            ("1.1", "claude", "api"),
        ):
            raise ValueError("host configuration version/host/authentication mismatch")

    @classmethod
    def from_file(cls, filename: Path) -> HostConfiguration:
        filename = Path(filename).absolute()
        parent = checked_directory(filename.parent)
        path = confined_file(parent, filename.name)
        with path.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("host configuration exceeds 64 KiB")
        try:
            value = tomllib.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeError):
            raise ValueError("invalid host configuration TOML") from None
        fields = {
            "schema_version",
            "qualification_root",
            "qualification_digest",
            "credential_path",
            "lease_id",
        }
        if value.get("schema_version") == "1.1":
            fields |= {"host_kind", "auth_mode"}
        if (
            set(value) != fields
            or any(type(item) is not str for item in value.values())
            or value["schema_version"] not in ("1.0", "1.1")
        ):
            raise ValueError("invalid host configuration fields or version")
        identifier(value["lease_id"])
        sha256(value["qualification_digest"])
        root, credential = Path(value["qualification_root"]), Path(value["credential_path"])
        if not root.is_absolute() or not credential.is_absolute():
            raise ValueError("host configuration paths must be absolute")
        root = checked_directory(root).resolve()
        credential_parent = checked_directory(credential.parent).resolve()
        if credential.is_symlink():
            raise ValueError("credential path must not be a symlink")
        credential = credential_parent / credential.name
        if credential.is_relative_to(root):
            raise ValueError("credential must be outside native qualification evidence")
        return cls(
            root,
            value["qualification_digest"],
            credential,
            value["lease_id"],
            value["schema_version"],
            value.get("host_kind", "codex"),
            value.get("auth_mode", "subscription"),
        )

    @property
    def digest(self) -> str:
        value = {
            "schema_version": self.schema_version,
            "qualification_root": str(self.qualification_root),
            "qualification_digest": self.qualification_digest,
            "credential_path": str(self.credential_path),
            "lease_id": self.lease_id,
        }
        if self.schema_version == "1.1":
            value.update(host_kind=self.host_kind, auth_mode=self.auth_mode)
        return digest(value)

    def check_scope(self, *roots: Path) -> None:
        if any(self.credential_path.is_relative_to(Path(root).resolve()) for root in roots):
            raise ValueError(
                "credential must be outside worker and scientific campaign directories"
            )

    def build(self, spec):
        from .hosts.brokered_host import BrokeredCodexHost
        from .hosts.claude_host import BrokeredClaudeHost

        if spec.host.kind != self.host_kind or spec.host.auth_mode != self.auth_mode:
            raise ValueError("host configuration differs from run host/authentication selection")

        adapter = BrokeredClaudeHost if self.host_kind == "claude" else BrokeredCodexHost
        host = adapter(
            qualification_root=self.qualification_root,
            qualification_digest=self.qualification_digest,
            credential_path=self.credential_path,
            lease_id=self.lease_id,
            model=spec.host.requested_model,
        )
        host.validate_selection(spec.host)
        host.validate_limits(spec.limits)
        return host
