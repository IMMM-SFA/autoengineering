"""Fixed Codex subscription transport behind the owned command boundary.

Caller authorization, credential preparation and OS egress qualification are
separate. This module never selects or opens a user's existing auth cache.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import math
from pathlib import Path
import sys

from autoengineering.campaign.records import identifier
from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write

from .command_upstream import CommandUpstream, inspect_command_stop, recover_command_upstream
from .text_exchange import MAX_REQUEST_BYTES
from .subscription_worker import VERSION


class ScopedSubscriptionUpstream:
    """One trusted callback with an explicit, preauthorized credential lease.

    The credential is external to the command attempt and every declared client
    root. Only the worker reads it. No secret bytes or credential hash enter the
    command manifest. The declared expiry is checked, never refreshed or assumed
    to establish actual server validity. Live endpoint access needs authorization.
    """

    def __init__(
        self,
        directory: Path,
        *,
        credential_path: Path,
        lease_id: str,
        model: str,
        client_roots: tuple[Path, ...],
        deadline_monotonic: float,
        cancelled: Callable[[], bool] = lambda: False,
        on_launch: Callable[[dict], None] = lambda _receipt: None,
    ):
        identifier(lease_id)
        self.directory = Path(directory).absolute()
        self.credential_path = Path(credential_path).absolute()
        client_roots = tuple(checked_directory(Path(root)).resolve() for root in client_roots)
        credential_parent = checked_directory(self.credential_path.parent)
        self.credential_path = credential_parent.resolve() / self.credential_path.name
        self.directory = checked_directory(self.directory.parent).resolve() / self.directory.name
        if (
            not client_roots
            or not Path(credential_path).is_absolute()
            or self.credential_path.is_relative_to(self.directory)
            or any(
                self.credential_path.is_relative_to(Path(root).absolute()) for root in client_roots
            )
            or type(model) is not str
            or not model.strip()
            or len(model.encode()) > 256
            or type(deadline_monotonic) not in (int, float)
            or not math.isfinite(deadline_monotonic)
            or deadline_monotonic <= 0
        ):
            raise ValueError("invalid subscription scope or deadline")
        # Check physical parent paths without opening the credential itself.
        checked_directory(self.credential_path.parent)
        self.lease_id, self.model, self.deadline = lease_id, model, deadline_monotonic
        self.cancelled, self.on_launch = cancelled, on_launch

    def __call__(self, request: bytes) -> bytes:
        if type(request) is not bytes or not 0 < len(request) <= MAX_REQUEST_BYTES:
            raise ValueError("subscription request exceeds size limit")
        root = self.directory
        checked_directory(root.parent)
        root.mkdir(mode=0o700)
        policy = root / "policy.json"
        durable_write(
            policy,
            canonical_json(
                {
                    "version": VERSION,
                    "model": self.model,
                    "lease_id": self.lease_id,
                    "credential_path": str(self.credential_path),
                    "deadline_monotonic": self.deadline,
                    "request_sha256": hashlib.sha256(request).hexdigest(),
                    "scope": str(root),
                }
            ).encode(),
        )
        worker = Path(__file__).with_name("subscription_worker.py")
        callback = CommandUpstream(
            root / "attempt",
            command=(
                sys.executable,
                "-I",
                "-S",
                str(worker),
                "--policy",
                str(policy),
                "--request",
                "{request}",
                "--response",
                "{response}",
            ),
            source_files=(worker, policy),
            deadline_monotonic=self.deadline,
            cancelled=self.cancelled,
            on_launch=self.on_launch,
        )
        return callback(request)

    def stop_audit(self):
        """Verify local command ownership without opening the lease or retrying."""
        if not self.directory.exists() and not self.directory.is_symlink():
            return {"state": "not_launched"}
        attempt = self.directory / "attempt"
        if not (attempt / "process").exists() and not (attempt / "process").is_symlink():
            return {"state": "not_launched"}
        try:
            policy, _manifest = verify_subscription_attempt(self.directory)
            if (policy["model"], policy["lease_id"], policy["credential_path"]) != (
                self.model,
                self.lease_id,
                str(self.credential_path),
            ):
                raise ValueError("subscription stop scope mismatch")
            return inspect_command_stop(attempt)
        except (ValueError, OSError, KeyError):
            return {"state": "unresolved"}


def verify_subscription_attempt(directory: Path) -> tuple[dict, dict]:
    """Verify the fixed command and scope without reading a credential or response."""
    root = checked_directory(directory)

    def record(base, name):
        path = confined_file(base, name)
        if path.stat().st_size > 65536:
            raise ValueError("subscription receipt exceeds size limit")
        return unique_json(path.read_text())

    policy = record(root, "policy.json")
    manifest = record(root / "attempt", "upstream.json")
    command = manifest["command"]
    worker_path = Path(__file__).with_name("subscription_worker.py").resolve()
    worker_hash = hashlib.sha256(worker_path.read_bytes()).hexdigest()
    if (
        set(policy)
        != {
            "version",
            "model",
            "lease_id",
            "credential_path",
            "deadline_monotonic",
            "request_sha256",
            "scope",
        }
        or policy.get("version") != VERSION
        or policy.get("scope") != str(root)
        or policy.get("request_sha256") != manifest["request_sha256"]
        or policy.get("deadline_monotonic") != manifest["deadline_monotonic"]
        or len(command) != 10
        or command[:3] != [str(Path(sys.executable).resolve()), "-I", "-S"]
        or command[3] != str(worker_path)
        or command[4:]
        != [
            "--policy",
            str(root / "policy.json"),
            "--request",
            "{request}",
            "--response",
            "{response}",
        ]
        or manifest["sources"].get(command[3]) != worker_hash
        or set(manifest["sources"]) != {command[0], command[3], str(root / "policy.json")}
    ):
        raise ValueError("subscription command or scope binding mismatch")
    return policy, manifest


def recover_subscription_response(directory: Path) -> bytes:
    """Read saved response bytes without opening credentials or sending a request."""
    root = checked_directory(directory)
    policy, _manifest = verify_subscription_attempt(root)

    def record(base, name):
        path = confined_file(base, name)
        if path.stat().st_size > 65536:
            raise ValueError("subscription receipt exceeds size limit")
        return unique_json(path.read_text())

    raw = recover_command_upstream(root / "attempt")
    intent = record(root / "attempt", "provider-intent.json")
    result = record(root / "attempt", "provider-result.json")
    expected_result = {
        "version": VERSION,
        "status": "response_received",
        "phase": "response_body",
        "http_status": 200,
        "body_bytes_read": len(raw),
        "request_may_have_been_sent": True,
        "scope": str(root),
        "usage": None,
    }
    if "header_diagnostic" in result:
        # The fixed worker records this only for an omitted MIME header on a
        # successful SSE response. Other diagnostics cannot attest success.
        expected_result["header_diagnostic"] = {
            "content_type": "missing",
            "content_encoding": "identity",
        }
    if (
        intent
        != {
            "version": VERSION,
            "lease_id": policy["lease_id"],
            "host": "chatgpt.com",
            "port": 443,
            "path": "/backend-api/codex/responses",
            "request_sha256": policy["request_sha256"],
            "scope": str(root),
            "automatic_retries": 0,
        }
        or result != expected_result
    ):
        raise ValueError("subscription provider receipt mismatch")
    return raw
