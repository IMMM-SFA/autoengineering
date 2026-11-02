"""Qualification-gated version 2.1 host adapter for serial worker dispatch.

The CLI requires explicit qualification and prepared-lease configuration.
Qualification is not live-call authority. Only the trusted caller selects a lease.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import threading
import time

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.execution import live_members
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write

from ..records import HostCapabilities
from .base import HostResult
from .codex_brokered import (
    WrappedCommand,
    capture_endpoint_stop,
    execute_brokered_codex,
    recover_brokered_transport,
)
from .native_policy import render_native_policy
from .native_profile import verify_native_profile
from .subscription import ScopedSubscriptionUpstream, verify_subscription_attempt

WIRE_VERSION = "role-handoff-envelope-1.0"
WIRE_PREFIX = (
    "Transport format: return one JSON object with exactly one field, handoff_json. "
    "Its value must be a string containing the complete role-handoff JSON object "
    "specified below. Do not add prose or tools. The broker validates that inner "
    "object and retains all scientific authority.\n\n"
)
WIRE_SCHEMA = {
    "type": "object",
    "properties": {"handoff_json": {"type": "string"}},
    "required": ["handoff_json"],
    "additionalProperties": False,
}


def _json(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise ValueError("adapter record exceeds size limit")
    return unique_json(path.read_text())


def _inner(result):
    if result.status != "completed":
        return result
    try:
        value = unique_json(result.raw_output)
        if (
            not isinstance(value, dict)
            or set(value) != {"handoff_json"}
            or type(value["handoff_json"]) is not str
        ):
            raise ValueError()
        text = value["handoff_json"]
        if len(text.encode()) > 65536:
            raise ValueError()
    except (ValueError, TypeError, RecursionError):
        text = "invalid role transport envelope"
    # The scheduler performs the authoritative typed role validation. Keep raw
    # native events intact rather than presenting transformed text as the wire.
    return replace(result, raw_output=text)


class BrokeredCodexHost:
    def __init__(
        self,
        *,
        qualification_root: Path,
        qualification_digest: str,
        credential_path: Path,
        lease_id: str,
        model: str,
    ):
        self.root, self.pin = Path(qualification_root), qualification_digest
        self.credential_path = Path(credential_path).absolute()
        self.lease_id, self.model = lease_id, model
        self._active = {}
        self._stopped = set()
        self._pending = {}
        self._owner_parent = None
        self._verify()

    def _verify(self):
        profile = verify_native_profile(self.root, expected_digest=self.pin)
        if profile.model != self.model:
            raise ValueError("model differs from qualified native profile")
        return profile

    def _config(self):
        return digest(
            {
                "profile": self.pin,
                "model": self.model,
                "credential_path": str(self.credential_path),
                "lease_id": self.lease_id,
                "wire_version": WIRE_VERSION,
            }
        )

    def capabilities(self):
        profile = self._verify()
        return HostCapabilities(
            "1.0",
            "codex",
            "2.1",
            profile.inventory.version + ":" + self._config(),
            "subscription",
            True,
            True,
            self.pin,
            profile.runtime_identity,
        )

    def prepare_prompt(self, task, prompt):
        wire = WIRE_PREFIX + prompt
        if len(wire.encode()) > 65536:
            raise ValueError("framed worker prompt exceeds size limit")
        return wire

    def invoke(self, *args, **kwargs):
        raise ValueError("brokered host requires a reserved invocation context")

    def validate_selection(self, selection):
        if (
            selection.kind,
            selection.auth_mode,
            selection.adapter_version,
            selection.requested_model,
            selection.qualification_digest,
        ) != ("codex", "subscription", "2.1", self.model, self.pin):
            raise ValueError("worker selection differs from brokered host configuration")

    def validate_limits(self, limits):
        profile = self._verify()
        if (
            limits.worker_seconds > profile.max_worker_seconds
            or min(65536, limits.transcript_bytes) > profile.max_output_bytes
            or len(canonical_json(WIRE_SCHEMA).encode())
            > min(profile.max_workspace_bytes, limits.workspace_bytes)
        ):
            raise ValueError("worker limits exceed qualified native profile or staged workspace")

    def _bind(self, context):
        parent = checked_directory(context.directory.parent).resolve()
        if context.directory.name != context.invocation_id or (
            self._owner_parent is not None and parent != self._owner_parent
        ):
            raise ValueError("brokered host belongs to another invocation scope")
        self._owner_parent = parent

    def _wrap(self, command, endpoint, workspace, home, inventory):
        path = endpoint.directory.parent / "native-boundary.sb"
        durable_write(
            path,
            render_native_policy(
                workspace, home, Path(inventory.executable), endpoint.port
            ).encode(),
        )
        return WrappedCommand(("/usr/bin/sandbox-exec", "-f", str(path), *command), path)

    def _upstream(self, root, workspace, home, deadline, cancelled):
        return ScopedSubscriptionUpstream(
            root / "upstream",
            credential_path=self.credential_path,
            lease_id=self.lease_id,
            model=self.model,
            client_roots=(workspace, home),
            deadline_monotonic=deadline,
            cancelled=cancelled,
        )

    def invoke_supervised(self, task, prompt, context):
        began = time.monotonic()
        profile = self._verify()
        self._bind(context)
        if self._active or self._pending:
            raise ValueError("brokered host has an unresolved invocation")
        if (
            not prompt.startswith(WIRE_PREFIX)
            or context.timeout_seconds > profile.max_worker_seconds
            or context.max_output_bytes > profile.max_output_bytes
        ):
            raise ValueError("invocation exceeds qualified host profile")
        root = Path(context.directory).absolute()
        checked_directory(root.parent)
        root.mkdir(mode=0o700)
        stop = threading.Event()
        self._active[context.invocation_id] = stop
        try:
            workspace, home = root / "workspace", root / "home"
            workspace.mkdir(mode=0o700)
            home.mkdir(mode=0o700)
            schema = canonical_json(WIRE_SCHEMA).encode()
            if len(schema) > profile.max_workspace_bytes:
                raise ValueError("qualified workspace allowance exhausted")
            durable_write(workspace / "schema.json", schema)
            manifest = {
                "version": "2.1",
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
            durable_write(root / "adapter.json", canonical_json(manifest).encode())

            def cancelled():
                return stop.is_set() or context.cancelled()

            upstream = None
            setup_failed = False
            if time.monotonic() - began < context.timeout_seconds and not cancelled():
                try:
                    upstream = self._upstream(
                        root, workspace, home, began + context.timeout_seconds, cancelled
                    )
                except (OSError, ValueError):
                    setup_failed = True
            prep = time.monotonic() - began
            durable_write(
                root / "preparation.json", canonical_json({"elapsed_seconds": prep}).encode()
            )
            remaining = context.timeout_seconds - prep
            if remaining <= 0 or cancelled() or setup_failed:
                result = HostResult(
                    "timeout"
                    if remaining <= 0
                    else "host_failure"
                    if setup_failed
                    else "cancelled",
                    "",
                    None,
                    {},
                    prep,
                    b"",
                    b"",
                    True,
                )
                durable_write(
                    root / "prelaunch.json",
                    canonical_json({"status": result.status, "launched": False}).encode(),
                )
                self._stopped.add(context.invocation_id)
                return result
            execution = execute_brokered_codex(
                profile.inventory,
                model=self.model,
                schema=workspace / "schema.json",
                workspace=workspace,
                home=home,
                prompt=prompt.encode(),
                context=replace(
                    context,
                    directory=root / "transport",
                    timeout_seconds=remaining,
                    cancelled=cancelled,
                ),
                upstream=upstream,
                boundary_identity=self.pin,
                owned_native=True,
                model_catalog=profile.model_catalog,
                wrap_command=lambda command, endpoint: self._wrap(
                    command, endpoint, workspace, home, profile.inventory
                ),
            )
            result = _inner(execution.host_result)
            upstream_stop = (
                upstream.stop_audit()
                if isinstance(upstream, ScopedSubscriptionUpstream)
                else {"state": "not_launched"}
            )
            durable_write(root / "upstream-stop.json", canonical_json(upstream_stop).encode())
            if upstream_stop["state"] == "unresolved":
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
                self._pending[context.invocation_id] = (execution, stop, upstream)
            return result
        finally:
            self._active.pop(context.invocation_id, None)

    def recover_supervised(self, task, prompt, context):
        self._verify()
        self._bind(context)
        root = checked_directory(context.directory)
        manifest = _json(root, "adapter.json")
        expected = {
            "version": "2.1",
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
        if manifest != expected:
            raise ValueError("adapter recovery identity mismatch")
        prep = _json(root, "preparation.json")["elapsed_seconds"]
        if type(prep) not in (int, float) or not 0 <= prep <= 86400:
            raise ValueError("invalid adapter preparation timing")
        if (root / "prelaunch.json").exists():
            saved = _json(root, "prelaunch.json")
            if (
                set(saved) != {"status", "launched"}
                or saved["status"] not in ("timeout", "cancelled", "host_failure")
                or saved["launched"] is not False
                or (root / "transport").exists()
            ):
                raise ValueError("prelaunch receipt contradicts transport state")
            return HostResult(saved["status"], "", None, {}, prep, b"", b"", True)
        transport = _json(root / "transport", "transport.json")
        if (
            transport["invocation_id"] != context.invocation_id
            or transport["nonce"] != context.nonce
            or transport["requested_model"] != self.model
            or transport["boundary_identity"] != self.pin
            or transport["workspace"] != str(root / "workspace")
            or transport["prompt"]["sha256"] != expected["prompt_sha256"]
            or transport["schema"]["sha256"]
            != hashlib.sha256(canonical_json(WIRE_SCHEMA).encode()).hexdigest()
        ):
            raise ValueError("adapter transport differs from reserved context")
        if not (root / "transport/client/completion.json").exists():
            from .abandoned import recover_abandoned_brokered_transport

            policy, _manifest = verify_subscription_attempt(root / "upstream")
            if (policy["model"], policy["lease_id"], policy["credential_path"]) != (
                self.model,
                self.lease_id,
                str(self.credential_path),
            ):
                raise ValueError("abandoned subscription differs from host selection")
            return recover_abandoned_brokered_transport(
                root / "transport", upstream_attempt=root / "upstream/attempt"
            )
        recovered = recover_brokered_transport(root / "transport")
        # A returned callback is not proof that its separately owned command
        # stopped. Preserve uncertainty until a fresh bound watchdog proof exists.
        if (root / "upstream").exists():
            policy, _manifest = verify_subscription_attempt(root / "upstream")
            if (policy["model"], policy["lease_id"], policy["credential_path"]) != (
                self.model,
                self.lease_id,
                str(self.credential_path),
            ):
                raise ValueError("subscription recovery scope mismatch")
            from .command_upstream import inspect_command_stop

            if inspect_command_stop(root / "upstream/attempt")["state"] == "unresolved":
                return replace(
                    recovered.host_result,
                    status="reconciliation_required",
                    stop_verified=False,
                    raw_output="",
                )
        if recovered.native.identity is not None and live_members(recovered.native.identity.pgid):
            raise ValueError("native ownership remains live")
        result = _inner(recovered.host_result)
        elapsed = prep + result.elapsed_seconds
        if result.status == "completed" and elapsed > context.timeout_seconds:
            result = replace(result, status="timeout", raw_output="")
        return replace(result, elapsed_seconds=elapsed)

    def cancel(self, invocation_id):
        if invocation_id in self._stopped:
            return True
        stop = self._active.get(invocation_id)
        if stop is not None:
            stop.set()
        pending = self._pending.get(invocation_id)
        if pending is not None:
            execution, event, upstream = pending
            event.set()
            stopped = capture_endpoint_stop(execution.root, execution.endpoint, wait_seconds=0.2)
            if (
                stopped.listener_closed
                and stopped.handler_stopped
                and stopped.upstream_callback_stopped
                and execution.native.stopped
                and (
                    not isinstance(upstream, ScopedSubscriptionUpstream)
                    or upstream.stop_audit()["state"] != "unresolved"
                )
                and (
                    execution.native.identity is None
                    or not live_members(execution.native.identity.pgid)
                )
            ):
                self._pending.pop(invocation_id)
                self._stopped.add(invocation_id)
                return True
        return False
