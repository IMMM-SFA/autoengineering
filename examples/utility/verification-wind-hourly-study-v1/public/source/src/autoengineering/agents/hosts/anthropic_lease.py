"""Explicit raw-key source to a fresh, short-lived private API lease.

The trusted caller authorizes the named read. No source discovery, environment
lookup, login, key refresh, server probe or provider call is performed. Receipts
contain no key or key hash. Actual key validity/expiry is not established here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import stat

from autoengineering.campaign.records import identifier
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write
from .subscription_worker import private_read

VERSION = "anthropic-api-lease-preparation-1.0"
MIN_SECONDS, MAX_SECONDS = 30, 900


class ApiLeaseError(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__("API lease preparation: " + reason)


@dataclass(frozen=True)
class PreparedApiLease:
    directory: Path
    lease_id: str
    not_after_utc: str

    @property
    def credential_path(self):
        return self.directory / "lease.json"

    def receipt(self):
        return {
            "version": VERSION,
            "authentication_mode": "api",
            "status": "prepared",
            "lease_id": self.lease_id,
            "not_after_utc": self.not_after_utc,
            "scope": str(self.directory),
            "server_validity_verified": False,
            "actual_key_expiry_verified": False,
            "refresh_performed": False,
        }


def _snapshot(path):
    s = path.lstat()
    return s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink


def _within(path, root):
    key = (root.stat().st_dev, root.stat().st_ino)
    return any((p.stat().st_dev, p.stat().st_ino) == key for p in (path, *path.parents))


def _git(path):
    return any((p / ".git").exists() or (p / ".git").is_symlink() for p in (path, *path.parents))


def prepare_api_lease(
    source_path: Path,
    directory: Path,
    *,
    lease_id: str,
    not_after_utc: str,
    workspace_id: str | None,
    client_read_roots: tuple[Path, ...],
) -> PreparedApiLease:
    """Reserve a fresh destination before reading the explicit raw-key file.

    One trailing LF is allowed. Source/lease must be outside Git and all native
    client read roots. The original source remains unchanged. Partial destinations
    are never reused. Expiry is a declared local-use ceiling, not server validity.
    """
    try:
        identifier(lease_id)
        now = datetime.now(timezone.utc)
        expiry = datetime.strptime(not_after_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if (
            expiry.strftime("%Y-%m-%dT%H:%M:%SZ") != not_after_utc
            or not MIN_SECONDS < (expiry - now).total_seconds() <= MAX_SECONDS
        ):
            raise ApiLeaseError("lease_expiry")
        if workspace_id is not None and (
            type(workspace_id) is not str
            or re.fullmatch(r"wrkspc_[A-Za-z0-9_-]{1,128}", workspace_id) is None
        ):
            raise ApiLeaseError("workspace")
        source_path, directory = Path(source_path), Path(directory)
        if (
            not source_path.is_absolute()
            or not directory.is_absolute()
            or ".." in source_path.parts
            or ".." in directory.parts
            or not 1 <= len(client_read_roots) <= 32
        ):
            raise ApiLeaseError("source_scope")
        source = checked_directory(source_path.parent).resolve() / source_path.name
        target = checked_directory(directory.parent).resolve() / directory.name
        roots = tuple(Path(root).absolute() for root in client_read_roots)
        for root in roots:
            if (
                not root.is_dir()
                or ".." in root.parts
                or any(p.is_symlink() for p in (root, *root.parents))
            ):
                raise ApiLeaseError("client_scope")
        if (
            _git(source.parent)
            or _git(target.parent)
            or source == target
            or source.is_relative_to(target)
            or any(_within(source.parent, root) or _within(target.parent, root) for root in roots)
        ):
            raise ApiLeaseError("source_scope")
        target.mkdir(mode=0o700)
        durable_write(
            target / "preparation.json",
            canonical_json(
                {
                    "version": VERSION,
                    "lease_id": lease_id,
                    "state": "reserved",
                    "not_after_utc": not_after_utc,
                }
            ).encode(),
        )
        if not stat.S_ISREG(source.lstat().st_mode):
            raise ApiLeaseError("source_regular_file")
        before = _snapshot(source)
        raw = private_read(source, 4097)
        if _snapshot(source) != before:
            raise ApiLeaseError("source_changed")
        key = raw.decode("ascii").removesuffix("\n")
        if not 0 < len(key) <= 4096 or any(not 33 <= ord(c) <= 126 for c in key):
            raise ApiLeaseError("raw_key_format")
        durable_write(
            target / "lease.json",
            canonical_json(
                {
                    "schema_version": "1.0",
                    "kind": "anthropic-api-key",
                    "lease_id": lease_id,
                    "api_key": key,
                    "workspace_id": workspace_id,
                    "not_after_utc": not_after_utc,
                }
            ).encode(),
        )
        lease = PreparedApiLease(target, lease_id, not_after_utc)
        durable_write(target / "receipt.json", canonical_json(lease.receipt()).encode())
        return lease
    except FileExistsError:
        raise ApiLeaseError("destination_reserved") from None
    except ApiLeaseError:
        raise
    except (OSError, ValueError, TypeError, UnicodeError):
        raise ApiLeaseError("preparation_failed") from None
