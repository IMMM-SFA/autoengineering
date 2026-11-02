"""Owned one-send API callback with an explicit prepared Anthropic lease.

No cache discovery, lease preparation, authentication probe or live authority.
The native client receives only its local capability. Only the worker opens the
named API lease. Production qualification and operator authorization are separate.
"""

from __future__ import annotations

from collections.abc import Callable
import hashlib
import math
from pathlib import Path
import re
import sys

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.records import identifier
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from .anthropic_worker import VERSION, API_VERSION
from .command_upstream import CommandUpstream, inspect_command_stop, recover_command_upstream
from .text_exchange import MAX_REQUEST_BYTES


class ScopedAnthropicUpstream:
    def __init__(
        self,
        directory: Path,
        *,
        credential_path: Path,
        lease_id: str,
        model: str,
        client_read_roots: tuple[Path, ...],
        max_output_tokens: int,
        deadline_monotonic: float,
        cancelled: Callable[[], bool] = lambda: False,
        on_launch: Callable[[dict], None] = lambda _receipt: None,
    ):
        identifier(lease_id)
        if ".." in Path(directory).parts:
            raise ValueError("upstream directory cannot traverse parents")
        original = Path(credential_path)
        if not original.is_absolute() or ".." in original.parts:
            raise ValueError("credential requires an explicit absolute source")
        self.credential_path = checked_directory(original.parent).resolve() / original.name
        self.directory = (
            checked_directory(Path(directory).absolute().parent).resolve() / Path(directory).name
        )
        roots = tuple(Path(p).absolute() for p in client_read_roots)
        for root in roots:
            if not root.is_dir() or any(p.is_symlink() for p in (root, *root.parents)):
                raise ValueError("client read scope is missing or symlinked")
        if (
            not roots
            or len(roots) > 32
            or self.credential_path.is_relative_to(self.directory)
            or any(self.credential_path.resolve().is_relative_to(root.resolve()) for root in roots)
            or any(
                (p / ".git").exists() or (p / ".git").is_symlink()
                for p in (self.credential_path.parent, *self.credential_path.parent.parents)
            )
            or type(model) is not str
            or re.fullmatch(r"claude-[A-Za-z0-9._-]{1,128}", model) is None
            or type(max_output_tokens) is not int
            or not 0 < max_output_tokens <= 32768
            or type(deadline_monotonic) not in (int, float)
            or not math.isfinite(deadline_monotonic)
            or deadline_monotonic <= 0
        ):
            raise ValueError("invalid Anthropic lease scope or limits")
        self.client_roots = roots
        self.lease_id, self.model = lease_id, model
        self.deadline, self.max_output_tokens = deadline_monotonic, max_output_tokens
        self.cancelled, self.on_launch = cancelled, on_launch

    def __call__(self, request: bytes) -> bytes:
        if type(request) is not bytes or not 0 < len(request) <= MAX_REQUEST_BYTES:
            raise ValueError("Anthropic request exceeds size limit")
        root = self.directory
        checked_directory(root.parent)
        root.mkdir(mode=0o700)
        policy = root / "policy.json"
        durable_write(
            policy,
            canonical_json(
                {
                    "version": VERSION,
                    "api_version": API_VERSION,
                    "model": self.model,
                    "lease_id": self.lease_id,
                    "credential_path": str(self.credential_path),
                    "client_read_roots": [str(p) for p in self.client_roots],
                    "max_output_tokens": self.max_output_tokens,
                    "deadline_monotonic": self.deadline,
                    "request_sha256": hashlib.sha256(request).hexdigest(),
                    "scope": str(root),
                }
            ).encode(),
        )
        worker = Path(__file__).with_name("anthropic_worker.py")
        support = Path(__file__).with_name("subscription_worker.py")
        callback = CommandUpstream(
            root / "attempt",
            command=(
                sys.executable,
                "-I",
                "-S",
                str(worker),
                "--support-sha256",
                hashlib.sha256(
                    confined_file(support.parent, support.name).read_bytes()
                ).hexdigest(),
                "--policy",
                str(policy),
                "--request",
                "{request}",
                "--response",
                "{response}",
            ),
            source_files=(worker, support, policy),
            deadline_monotonic=self.deadline,
            cancelled=self.cancelled,
            on_launch=self.on_launch,
        )
        raw = callback(request)
        if recover_anthropic_response(root) != raw:
            raise ValueError("Anthropic response changed before delivery")
        return raw

    def stop_audit(self):
        if not self.directory.exists() and not self.directory.is_symlink():
            return {"state": "not_launched"}
        try:
            verify_anthropic_attempt(self.directory)
        except (ValueError, OSError, KeyError, TypeError):
            return {"state": "unresolved"}
        return inspect_command_stop(self.directory / "attempt")


def verify_anthropic_attempt(directory: Path) -> tuple[dict, dict]:
    """Bind the fixed worker/policy/command without opening any credential."""
    root = checked_directory(Path(directory))

    def record(base, name):
        path = confined_file(base, name)
        if path.stat().st_size > 65536:
            raise ValueError("Anthropic record exceeds size limit")
        return unique_json(path.read_text())

    policy = record(root, "policy.json")
    manifest = record(root / "attempt", "upstream.json")
    worker = Path(__file__).with_name("anthropic_worker.py").resolve()
    support = Path(__file__).with_name("subscription_worker.py").resolve()
    python = str(Path(sys.executable).resolve())
    support_sha = hashlib.sha256(support.read_bytes()).hexdigest()
    expected_command = [
        python,
        "-I",
        "-S",
        str(worker),
        "--support-sha256",
        support_sha,
        "--policy",
        str(root / "policy.json"),
        "--request",
        "{request}",
        "--response",
        "{response}",
    ]
    if (
        set(policy)
        != {
            "version",
            "api_version",
            "model",
            "lease_id",
            "credential_path",
            "client_read_roots",
            "max_output_tokens",
            "deadline_monotonic",
            "request_sha256",
            "scope",
        }
        or policy.get("version") != VERSION
        or policy.get("api_version") != API_VERSION
        or policy.get("scope") != str(root)
        or policy.get("request_sha256") != manifest.get("request_sha256")
        or policy.get("deadline_monotonic") != manifest.get("deadline_monotonic")
        or manifest.get("command") != expected_command
        or set(manifest.get("sources", {}))
        != {python, str(worker), str(support), str(root / "policy.json")}
        or manifest["sources"].get(str(worker)) != hashlib.sha256(worker.read_bytes()).hexdigest()
        or manifest["sources"].get(str(support)) != support_sha
    ):
        raise ValueError("Anthropic fixed command or policy binding differs")
    return policy, manifest


def recover_anthropic_response(directory: Path) -> bytes:
    """Recover only original owned bytes. Never read the lease or send a request."""
    root = checked_directory(Path(directory))
    policy, manifest = verify_anthropic_attempt(root)
    receipt = confined_file(root / "attempt", "provider-result.json")
    if receipt.stat().st_size > 16384:
        raise ValueError("Anthropic result receipt exceeds bound")
    result = unique_json(receipt.read_text())
    raw = recover_command_upstream(root / "attempt")
    expected = {
        "version": VERSION,
        "api_version": API_VERSION,
        "status": "response_received",
        "phase": "response_body",
        "http_status": 200,
        "body_bytes_read": len(raw),
        "request_may_have_been_sent": True,
        "usage": None,
        "scope": str(root),
        "remote_stop_verified": False,
    }
    if canonical_json(result) != canonical_json(expected):
        raise ValueError("original Anthropic response was not completed")
    intent = confined_file(root / "attempt", "provider-intent.json")
    if intent.stat().st_size > 16384:
        raise ValueError("Anthropic intent receipt exceeds bound")
    expected_intent = {
        "version": VERSION,
        "api_version": API_VERSION,
        "lease_id": policy["lease_id"],
        "host": "api.anthropic.com",
        "port": 443,
        "path": "/v1/messages",
        "request_sha256": manifest["request_sha256"],
        "automatic_retries": 0,
        "scope": str(root),
    }
    if canonical_json(unique_json(intent.read_text())) != canonical_json(expected_intent):
        raise ValueError("original Anthropic send intent differs")
    return raw
