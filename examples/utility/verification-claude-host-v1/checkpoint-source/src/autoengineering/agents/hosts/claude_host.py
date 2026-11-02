"""Qualification-gated Claude API host. Qualification is not live-call authority."""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import sys
import threading
import time

from autoengineering.agents.records import HostCapabilities
from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.execution import live_members
from autoengineering.campaign.records import identifier, sha256
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from .anthropic_upstream import ScopedAnthropicUpstream, verify_anthropic_attempt
from .base import HostResult
from .brokered_host import WIRE_PREFIX, WIRE_SCHEMA, WIRE_VERSION, _inner
from .claude_brokered import (
    execute_brokered_claude,
    recover_brokered_claude,
    capture_claude_endpoint_stop,
)
from .claude_policy import (
    ClaudePolicy,
    ClaudeEgress,
    VERSION as POLICY_VERSION,
    render_claude_policy,
)
from .claude_profile import verify_claude_profile
from .codex_brokered import WrappedCommand
from .command_upstream import inspect_command_stop


def _json(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise ValueError("Claude adapter record exceeds limit")
    return unique_json(path.read_text())


class BrokeredClaudeHost:
    def __init__(
        self,
        *,
        qualification_root: Path,
        qualification_digest: str,
        credential_path: Path,
        lease_id: str,
        model: str,
    ):
        sha256(qualification_digest)
        identifier(lease_id)
        self.root, self.pin = Path(qualification_root), qualification_digest
        self.credential_path = Path(credential_path).absolute()
        self.lease_id, self.model = lease_id, model
        self._owner_parent = None
        self._active, self._pending, self._stopped = {}, {}, set()
        self._verify()  # Refuse incomplete evidence before touching a credential.

    def _verify(self):
        profile = verify_claude_profile(self.root, expected_digest=self.pin)
        if profile.model != self.model:
            raise ValueError("Claude model differs from qualified profile")
        return profile

    def _config(self):
        return digest(
            {
                "profile": self.pin,
                "model": self.model,
                "auth_mode": "api",
                "credential_path": str(self.credential_path),
                "lease_id": self.lease_id,
                "wire_version": WIRE_VERSION,
            }
        )

    def capabilities(self):
        profile = self._verify()
        return HostCapabilities(
            "1.1",
            "claude",
            "3.0",
            profile.inventory.version + ":" + self._config(),
            "api",
            True,
            True,
            self.pin,
            profile.runtime_identity,
            profile.limitations,
            "reported_message_fields_only",
        )

    def validate_selection(self, selection):
        if (
            selection.kind,
            selection.auth_mode,
            selection.adapter_version,
            selection.requested_model,
            selection.qualification_digest,
        ) != ("claude", "api", "3.0", self.model, self.pin):
            raise ValueError("worker selection differs from Claude host configuration")

    def validate_limits(self, limits):
        profile = self._verify()
        if (
            limits.worker_seconds > profile.max_worker_seconds
            or min(65536, limits.transcript_bytes) > profile.max_output_bytes
            or len(canonical_json(WIRE_SCHEMA).encode())
            > min(profile.max_workspace_bytes, limits.workspace_bytes)
        ):
            raise ValueError("worker limits exceed qualified Claude profile")

    def prepare_prompt(self, task, prompt):
        text = WIRE_PREFIX + prompt
        if len(text.encode()) > 65536:
            raise ValueError("framed Claude prompt exceeds limit")
        return text

    def invoke(self, *args, **kwargs):
        raise ValueError("Claude host requires a reserved invocation context")

    def _bind(self, context):
        parent = checked_directory(context.directory.parent).resolve()
        if (
            context.directory.name != context.invocation_id
            or self._owner_parent is not None
            and self._owner_parent != parent
        ):
            raise ValueError("Claude host belongs to another invocation scope")
        self._owner_parent = parent

    def _upstream(self, root, roots, deadline, cancelled, profile):
        return ScopedAnthropicUpstream(
            root / "upstream",
            credential_path=self.credential_path,
            lease_id=self.lease_id,
            model=self.model,
            client_read_roots=roots,
            max_output_tokens=profile.max_output_tokens,
            deadline_monotonic=deadline,
            cancelled=cancelled,
        )

    def _wrap(self, command, endpoint, helper, capability, profile, root):
        transport = root / "transport"
        spec = ClaudePolicy(
            POLICY_VERSION,
            str(transport / "workspace"),
            str(transport / "home"),
            profile.inventory.executable,
            str(helper),
            str(Path(sys.executable).resolve()),
            str(Path(sys.prefix).resolve()),
            (str(capability),),
            (ClaudeEgress("localhost", endpoint.port),),
            (
                str(root / "private"),
                str(transport / "exchange"),
                str(transport / "endpoint"),
                str(self.root.resolve()),
            ),
        )
        path = root / "native-boundary.sb"
        durable_write(path, render_claude_policy(spec).encode())
        return WrappedCommand(("/usr/bin/sandbox-exec", "-f", str(path), *command), path)

    def _manifest(self, task, prompt, context):
        return {
            "version": "3.0",
            "wire_version": WIRE_VERSION,
            "profile": self.pin,
            "config": self._config(),
            "invocation_id": context.invocation_id,
            "nonce": context.nonce,
            "task_digest": digest(task.to_dict()),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "timeout_seconds": context.timeout_seconds,
            "max_output_bytes": context.max_output_bytes,
        }

    def invoke_supervised(self, task, prompt, context):
        began = time.monotonic()
        profile = self._verify()
        self._bind(context)
        if self._active or self._pending:
            raise ValueError("Claude host has an unresolved invocation")
        if (
            not prompt.startswith(WIRE_PREFIX)
            or context.timeout_seconds > profile.max_worker_seconds
            or context.max_output_bytes > profile.max_output_bytes
        ):
            raise ValueError("invocation exceeds qualified Claude profile")
        root = Path(context.directory).absolute()
        root.mkdir(mode=0o700)
        (root / "private").mkdir(mode=0o700)
        durable_write(
            root / "adapter.json", canonical_json(self._manifest(task, prompt, context)).encode()
        )
        stop = threading.Event()
        self._active[context.invocation_id] = stop
        upstream = None

        def cancelled():
            return stop.is_set() or context.cancelled()

        def callback(raw):
            if upstream is None:
                raise ValueError("Claude upstream was not prepared before native launch")
            return upstream(raw)

        def wrapper(command, endpoint, helper, capability):
            nonlocal upstream
            # Cover every allowed native read tree and conservative parents of
            # literal executable/helper grants. The real API lease is never one.
            transport = root / "transport"
            roots = (
                transport / "workspace",
                transport / "home",
                helper.parent,
                Path(sys.prefix).resolve(),
                Path(profile.inventory.executable).parent,
                Path("/usr/lib"),
                Path("/System/Library"),
                Path("/usr/share/icu"),
                Path("/bin"),
            )
            upstream = self._upstream(
                root, roots, began + context.timeout_seconds, cancelled, profile
            )
            return self._wrap(command, endpoint, helper, capability, profile, root)

        try:
            prep = time.monotonic() - began
            durable_write(
                root / "preparation.json", canonical_json({"elapsed_seconds": prep}).encode()
            )
            remaining = context.timeout_seconds - prep
            if remaining <= 0 or cancelled():
                status = "timeout" if remaining <= 0 else "cancelled"
                durable_write(
                    root / "prelaunch.json",
                    canonical_json({"status": status, "launched": False}).encode(),
                )
                self._stopped.add(context.invocation_id)
                return HostResult(status, "", None, {}, prep, b"", b"", True)
            execution = execute_brokered_claude(
                profile.inventory,
                model=self.model,
                prompt=prompt,
                context=replace(
                    context,
                    directory=root / "transport",
                    timeout_seconds=remaining,
                    cancelled=cancelled,
                ),
                upstream=callback,
                boundary_identity=self.pin,
                max_output_tokens=profile.max_output_tokens,
                estimated_budget_usd=profile.estimated_budget_usd,
                wrap_command=wrapper,
            )
            proof = (
                upstream.stop_audit()
                if isinstance(upstream, ScopedAnthropicUpstream)
                else {"state": "not_launched"}
            )
            durable_write(root / "upstream-stop.json", canonical_json(proof).encode())
            result = _inner(execution.host_result)
            if proof["state"] == "unresolved":
                result = replace(
                    result, status="reconciliation_required", stop_verified=False, raw_output=""
                )
            elapsed = prep + result.elapsed_seconds
            if result.status == "completed" and elapsed > context.timeout_seconds:
                result = replace(result, status="timeout", raw_output="")
            result = replace(result, elapsed_seconds=elapsed)
            if result.stop_verified:
                self._stopped.add(context.invocation_id)
            else:
                self._pending[context.invocation_id] = execution, stop, upstream
            return result
        finally:
            self._active.pop(context.invocation_id, None)

    def recover_supervised(self, task, prompt, context):
        self._verify()
        self._bind(context)
        root = checked_directory(context.directory)
        if _json(root, "adapter.json") != self._manifest(task, prompt, context):
            raise ValueError("Claude adapter recovery identity mismatch")
        prep = _json(root, "preparation.json")["elapsed_seconds"]
        if type(prep) not in (int, float) or not 0 <= prep <= 86400:
            raise ValueError("invalid Claude preparation timing")
        if (root / "prelaunch.json").exists():
            saved = _json(root, "prelaunch.json")
            if (
                set(saved) != {"status", "launched"}
                or saved["status"] not in ("timeout", "cancelled")
                or saved["launched"] is not False
                or (root / "transport").exists()
            ):
                raise ValueError("Claude prelaunch evidence contradicts transport")
            return HostResult(saved["status"], "", None, {}, prep, b"", b"", True)
        manifest = _json(root / "transport", "transport.json")
        profile = self._verify()
        if (
            manifest["invocation_id"] != context.invocation_id
            or manifest["nonce"] != context.nonce
            or manifest["model"] != self.model
            or manifest["boundary_identity"] != self.pin
            or manifest["timeout_seconds"] != context.timeout_seconds - prep
            or manifest["max_output_bytes"] != context.max_output_bytes
            or manifest["max_output_tokens"] != profile.max_output_tokens
            or manifest["estimated_budget_usd"] != profile.estimated_budget_usd
            or manifest["prompt_sha256"] != hashlib.sha256(prompt.encode()).hexdigest()
        ):
            raise ValueError("Claude transport differs from reserved invocation")
        result = _inner(recover_brokered_claude(root / "transport").host_result)
        if (root / "upstream").exists():
            policy, _ = verify_anthropic_attempt(root / "upstream")
            if (
                policy["model"],
                policy["lease_id"],
                policy["credential_path"],
                policy["max_output_tokens"],
            ) != (self.model, self.lease_id, str(self.credential_path), profile.max_output_tokens):
                raise ValueError("Claude upstream recovery scope mismatch")
            if inspect_command_stop(root / "upstream/attempt")["state"] == "unresolved":
                return replace(
                    result, status="reconciliation_required", stop_verified=False, raw_output=""
                )
        elapsed = prep + result.elapsed_seconds
        if result.status == "completed" and elapsed > context.timeout_seconds:
            result = replace(result, status="timeout", raw_output="")
        return replace(result, elapsed_seconds=elapsed)

    def cancel(self, invocation_id):
        if invocation_id in self._stopped:
            return True
        if invocation_id in self._active:
            self._active[invocation_id].set()
        pending = self._pending.get(invocation_id)
        if pending is not None:
            execution, event, upstream = pending
            event.set()
            stopped = capture_claude_endpoint_stop(execution.root, execution.endpoint)
            if (
                stopped.listener_closed
                and stopped.handler_stopped
                and stopped.upstream_callback_stopped
                and execution.native.process.stopped
                and (
                    execution.native.process.identity is None
                    or not live_members(execution.native.process.identity.pgid)
                )
                and (
                    not isinstance(upstream, ScopedAnthropicUpstream)
                    or upstream.stop_audit()["state"] != "unresolved"
                )
            ):
                self._pending.pop(invocation_id)
                self._stopped.add(invocation_id)
                return True
        return False
