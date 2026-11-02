"""Explicit managed-cache snapshot to a short-lived subscription credential lease.

No source discovery, login, refresh, provider request or global configuration.
The caller authorizes this read and supplies the expected account and expiry.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import time

from autoengineering.campaign.records import identifier
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write

from .subscription_worker import credential as read_lease
from .subscription_worker import private_read, unique_json

VERSION = "subscription-lease-preparation-1.0"
MAX_SOURCE_BYTES = 131072
MAX_SOURCE_AGE_SECONDS = 7 * 86400
MAX_LEASE_SECONDS = 900
MIN_LEASE_SECONDS = 30


class CredentialPreparationError(ValueError):
    """Static reason only. Never include source values or parser diagnostics."""

    def __init__(self, reason):
        self.reason = reason
        super().__init__("credential preparation: " + reason)


@dataclass(frozen=True)
class PreparedLease:
    directory: Path
    lease_id: str
    not_after_utc: str
    authentication_mode: str = "subscription"

    @property
    def credential_path(self):
        return self.directory / "lease.json"

    def receipt(self):
        return {
            "version": VERSION,
            "status": "prepared",
            "authentication_mode": self.authentication_mode,
            "lease_id": self.lease_id,
            "not_after_utc": self.not_after_utc,
            "refresh_performed": False,
            "server_validity_verified": False,
            "scope": str(self.directory),
        }


def _utc(value):
    if type(value) is not str:
        raise ValueError()
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError()
    return parsed


def _snapshot(metadata):
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def prepare_subscription_lease(
    source_path: Path,
    directory: Path,
    *,
    lease_id: str,
    expected_account_id: str | None,
    not_after_utc: str,
    client_roots: tuple[Path, ...],
) -> PreparedLease:
    """Read only the named physical source and write one fresh private lease.

    These checks verify source shape and declared bounds, not token signatures,
    server validity, actual token expiry or account access. The cache is never
    modified. Expiry/staleness requires its separate trusted owner to refresh it.
    A failed/partial destination is never reused. Receipts contain no secret hash.
    """
    try:
        identifier(lease_id)
        now = datetime.now(timezone.utc)
        expiry = _utc(not_after_utc)
        lifetime = (expiry - now).total_seconds()
        if not MIN_LEASE_SECONDS < lifetime <= MAX_LEASE_SECONDS:
            raise CredentialPreparationError("lease_expiry")
        if expected_account_id is not None and (
            type(expected_account_id) is not str
            or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", expected_account_id) is None
        ):
            raise CredentialPreparationError("expected_account")
        source_path, directory = Path(source_path), Path(directory)
        if not source_path.is_absolute() or not directory.is_absolute() or not client_roots:
            raise CredentialPreparationError("source_scope")
        source = checked_directory(source_path.parent).resolve() / source_path.name
        destination = checked_directory(directory.parent).resolve() / directory.name
        roots = tuple(checked_directory(Path(root)).resolve() for root in client_roots)
        if (
            source == destination
            or source.is_relative_to(destination)
            or any(
                (parent / ".git").exists() or (parent / ".git").is_symlink()
                for parent in (destination, *destination.parents)
            )
            or any(path.is_relative_to(root) for path in (source, destination) for root in roots)
        ):
            raise CredentialPreparationError("source_scope")
        # Reserve before reading secrets. A duplicate or partial attempt cannot
        # perform another read or overwrite a previously prepared credential.
        destination.mkdir(mode=0o700)
        before = source.lstat()
        raw = private_read(source, MAX_SOURCE_BYTES)
        if _snapshot(before) != _snapshot(source.lstat()):
            raise CredentialPreparationError("source_changed")
        value = unique_json(raw)
        if (
            not isinstance(value, dict)
            or set(value) - {"auth_mode", "tokens", "last_refresh", "OPENAI_API_KEY"}
            or value.get("auth_mode") != "chatgpt"
            or value.get("OPENAI_API_KEY") is not None
        ):
            raise CredentialPreparationError("source_authentication_mode")
        tokens = value.get("tokens")
        if (
            not isinstance(tokens, dict)
            or set(tokens) - {"access_token", "id_token", "refresh_token", "account_id"}
            or type(tokens.get("access_token")) is not str
            or re.fullmatch(r"[A-Za-z0-9._~+/-]{1,8192}={0,2}", tokens["access_token"]) is None
            or type(tokens.get("refresh_token")) is not str
            or not tokens["refresh_token"]
        ):
            raise CredentialPreparationError("unsupported_managed_cache")
        if tokens.get("account_id") != expected_account_id:
            raise CredentialPreparationError("account_mismatch")
        refreshed = datetime.fromisoformat(value["last_refresh"].replace("Z", "+00:00"))
        if refreshed.tzinfo is None:
            raise CredentialPreparationError("source_refresh_required")
        age = (now - refreshed).total_seconds()
        if not 0 <= age <= MAX_SOURCE_AGE_SECONDS:
            raise CredentialPreparationError("source_refresh_required")
        if _snapshot(before) != _snapshot(source.lstat()):
            raise CredentialPreparationError("source_changed")
        lease = PreparedLease(destination, lease_id, not_after_utc)
        durable_write(
            lease.credential_path,
            canonical_json(
                {
                    "schema_version": "1.0",
                    "kind": "codex-chatgpt-bearer",
                    "lease_id": lease_id,
                    "bearer_token": tokens["access_token"],
                    "account_id": expected_account_id,
                    "not_after_utc": not_after_utc,
                }
            ).encode(),
        )
        durable_write(destination / "prepared.json", canonical_json(lease.receipt()).encode())
        return lease
    except CredentialPreparationError:
        raise
    except FileExistsError:
        raise CredentialPreparationError("destination_exists") from None
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise CredentialPreparationError("source_unavailable_or_invalid") from None


def recover_prepared_subscription_lease(
    directory: Path,
    *,
    lease_id: str,
    expected_account_id: str | None,
    not_after_utc: str,
    client_roots: tuple[Path, ...],
) -> PreparedLease:
    """Read-only reuse of one prepared lease. Never reopen its source or refresh.

    A missing commit receipt or expired lease stays incomplete. This cannot
    reseed credentials, extend expiry or change account identity during resume.
    """
    try:
        identifier(lease_id)
        root = checked_directory(Path(directory)).resolve()
        roots = tuple(checked_directory(Path(path)).resolve() for path in client_roots)
        if (
            not roots
            or any(root.is_relative_to(path) for path in roots)
            or any(
                (parent / ".git").exists() or (parent / ".git").is_symlink()
                for parent in (root, *root.parents)
            )
        ):
            raise CredentialPreparationError("source_scope")
        lifetime = (_utc(not_after_utc) - datetime.now(timezone.utc)).total_seconds()
        if not MIN_LEASE_SECONDS < lifetime <= MAX_LEASE_SECONDS:
            raise CredentialPreparationError("lease_expiry")
        prepared = PreparedLease(root, lease_id, not_after_utc)
        if unique_json(private_read(root / "prepared.json", 16384)) != prepared.receipt():
            raise CredentialPreparationError("prepared_receipt_mismatch")
        auth = read_lease(
            {
                "credential_path": str(prepared.credential_path),
                "lease_id": lease_id,
                "deadline_monotonic": time.monotonic(),
            }
        )
        if auth["account_id"] != expected_account_id or auth["not_after_utc"] != not_after_utc:
            raise CredentialPreparationError("prepared_lease_mismatch")
        return prepared
    except CredentialPreparationError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        raise CredentialPreparationError("prepared_lease_unavailable_or_invalid") from None
