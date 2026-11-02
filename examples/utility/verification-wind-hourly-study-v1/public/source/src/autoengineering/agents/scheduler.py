"""Serial bounded role dispatch. Scientific operations remain broker-owned."""

from __future__ import annotations

from dataclasses import replace
from collections.abc import Callable
import hashlib
from importlib.resources import files
import time
import uuid

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError

from .hosts.base import Host, InvocationContext
from .identity import host_environment_identity, host_source_identity
from .output_contract import output_contract
from .permissions import (
    policy_digest,
    read_granted,
    validate_assignment,
    validate_handoff,
    validate_task_route,
)
from .records import ROLES, SINGLE_ROLE, AgentRunSpec, RoleHandoff, TaskAssignment, WorkerInvocation
from .store import WorkerStore, serialized_operation


def template_bytes(role: str) -> bytes:
    if role not in (*ROLES, SINGLE_ROLE):
        raise ValueError("unsupported role")
    return files("autoengineering.agents").joinpath(f"prompts/{role}.txt").read_bytes()


def template_digests(route="four_role") -> dict[str, str]:
    if route not in ("four_role", "single_agent"):
        raise ValueError("unsupported workflow route")
    roles = (SINGLE_ROLE,) if route == "single_agent" else ROLES
    return {role: hashlib.sha256(template_bytes(role)).hexdigest() for role in roles}


def validate_run_spec(spec: AgentRunSpec) -> None:
    if dict(spec.role_templates) != template_digests(spec.workflow_route):
        raise StoreError("role template identity mismatch")
    if spec.tool_policy_digest != policy_digest(spec.workflow_route):
        raise StoreError("tool policy identity mismatch")
    if (
        spec.execution_mode == "generated"
        and spec.host.kind != "fake"
        and spec.host.adapter_version not in ("2.1", "3.0")
    ):
        raise StoreError("generated worker execution requires a qualified production host boundary")
    if spec.source_identity != host_source_identity():
        raise StoreError("host source identity mismatch")
    if spec.environment_identity != host_environment_identity():
        raise StoreError("host environment identity mismatch")


def _implemented_brokered_host(host, kind):
    from .hosts.brokered_host import BrokeredCodexHost
    from .hosts.claude_host import BrokeredClaudeHost

    adapter = {"codex": BrokeredCodexHost, "claude": BrokeredClaudeHost}.get(kind)
    return adapter is not None and isinstance(host, adapter)


class SerialScheduler:
    """No host call is retried after an uncertain outcome.

    A caller must reconcile persisted pending reservations before another dispatch.
    Each repair is a new invocation. The fake host is permitted without an OS
    boundary because it does not execute tools or generated code.
    """

    def __init__(self, store: WorkerStore, host: Host, *, clock=time.time):
        self.store, self.host, self.clock = store, host, clock
        validate_run_spec(store.spec)
        if store.spec.host.kind != "fake":
            if _implemented_brokered_host(host, store.spec.host.kind):
                host.validate_selection(store.spec.host)
                host.validate_limits(store.spec.limits)

    def _cancelled(self):
        return any((self.store.root / "control").glob("cancel-*.json"))

    @serialized_operation
    def dispatch(
        self,
        task: TaskAssignment,
        *,
        campaign_revision: int,
        candidate_id: str | None = None,
        evaluation_id: str | None = None,
        validator: Callable[[RoleHandoff], None] | None = None,
    ) -> WorkerInvocation:
        """Dispatch one physical invocation or return the already completed one."""
        validate_run_spec(self.store.spec)
        with self.store.writer():
            projection = self.store.replay()
            validate_assignment(task)
            validate_task_route(task, self.store.spec)
            if task.run_id != self.store.spec.id:
                raise StoreError("task belongs to a different run")
            if task.campaign_revision != campaign_revision:
                raise StoreError("task campaign revision is stale")
            if projection.pending:
                raise StoreError("pending invocation requires reconciliation")
            if projection.pending_preparations:
                raise StoreError("pending source checks require reconciliation")
            if any(action.state == "reserved" for action in projection.actions.values()):
                raise StoreError("pending campaign action requires reconciliation")
            if self._cancelled():
                raise StoreError("worker cancellation is queued")
            if task.id in projection.tasks and projection.tasks[task.id] != task:
                raise StoreError("task identity mismatch")
            prior = [value for value in projection.invocations.values() if value.task_id == task.id]
            if prior and prior[-1].state == "completed":
                return prior[-1]
            if task.id not in projection.tasks:
                self.store.commit(task)
            capabilities = self.host.capabilities()
            if (
                projection.host_configuration is not None
                and capabilities != projection.host_configuration.capabilities
            ):
                raise StoreError("host capabilities differ from bound configuration")
            if any(v.capabilities != capabilities for v in projection.invocations.values()):
                raise StoreError("host capabilities changed during the worker run")
            if capabilities.host != self.store.spec.host.kind:
                raise StoreError("host capability mismatch")
            if capabilities.adapter_version != self.store.spec.host.adapter_version:
                raise StoreError("host adapter version mismatch")
            if capabilities.host != "fake" and (
                not capabilities.boundary_identity
                or not capabilities.process_supervision
                or not capabilities.structured_output
            ):
                raise StoreError("host execution boundary is unqualified")
            if capabilities.host != "fake":
                if not _implemented_brokered_host(self.host, capabilities.host):
                    raise StoreError("supervised host dispatch is not implemented for this adapter")
                self.host.validate_selection(self.store.spec.host)
            now = self.clock()
            limits = self.store.spec.limits
            started = projection.started_at
            if started is None:
                raise StoreError("worker run creation receipt is missing")
            remaining = min(
                task.deadline - now, started + limits.elapsed_seconds - now, limits.worker_seconds
            )
            if remaining <= 0:
                raise StoreError("worker deadline exhausted")
            usage = [
                v.usage.get("total_tokens")
                if v.usage.get("total_tokens") is not None
                else sum(v.usage.get(name) or 0 for name in ("input_tokens", "output_tokens"))
                for v in projection.invocations.values()
            ]
            if limits.observed_tokens is not None and sum(v or 0 for v in usage) >= (
                limits.observed_tokens
            ):
                raise StoreError("observed token stop reached")
            invocation_id = f"call-{len(projection.invocations) + 1:06d}"
            evidence = []
            for grant in task.grants:
                raw = read_granted(
                    self.store.root, task, grant.artifact.sha256, run_id=task.run_id, role=task.role
                )
                evidence.append({"id": grant.artifact.sha256, "content": raw.decode("utf-8")})
            # No previous role transcript or implementer scratch context is included.
            repair = None
            if prior:
                repair = (
                    read_bytes(self.store.root, prior[-1].parse_failure).decode()
                    if prior[-1].parse_failure is not None
                    else "Previous invocation failed without a valid role output."
                )
            prompt = (
                template_bytes(task.role).decode()
                + "\n"
                + canonical_json(
                    {
                        "task": task.to_dict(),
                        "invocation_id": invocation_id,
                        "approved_evidence": evidence,
                        "output_contract": output_contract(
                            task,
                            invocation_id,
                            permitted_implementations=self.store.spec.permitted_interventions,
                            generated=self.store.spec.execution_mode == "generated",
                            candidate_id=candidate_id,
                            evaluation_id=evaluation_id,
                        ),
                        "repair": repair,
                    }
                )
            )
            if capabilities.host != "fake":
                prompt = self.host.prepare_prompt(task, prompt)
            prompt_ref = self.store.put_private(
                prompt.encode(), name="prompt.txt", media_type="text/plain"
            )
            # Prompt/schema preparation is part of the original run clock.
            # Bind the reservation and recovery timeout to the time after those
            # bytes are durable, rather than extending the deadline by prep time.
            now = self.clock()
            remaining = min(
                task.deadline - now, started + limits.elapsed_seconds - now, limits.worker_seconds
            )
            if remaining <= 0:
                raise StoreError("worker deadline exhausted during prompt preparation")
            value = WorkerInvocation(
                "1.2" if capabilities.process_supervision else "1.0",
                invocation_id,
                task.run_id,
                task.id,
                len(prior),
                "reserved",
                prompt_ref,
                capabilities,
                self.store.spec.host.requested_model,
                None,
                self.store.spec.tool_policy_digest,
                uuid.uuid4().hex,
                None,
                None,
                None,
                None,
                now,
                None,
                {},
            )
            self.store.commit(value)
            used = sum(
                v.prompt.size_bytes
                + (v.raw_response.size_bytes if v.raw_response else 0)
                + (v.stderr_response.size_bytes if v.stderr_response else 0)
                for v in projection.invocations.values()
            )
            output_limit = min(65536, limits.transcript_bytes - used - prompt_ref.size_bytes)
            if output_limit <= 0:
                # Reserved allowance is retained, but no process was launched.
                receipt = self.store.put_private(
                    b'{"launched":false,"reason":"output_allowance"}',
                    name="completion.json",
                    media_type="application/json",
                )
                return self.store.commit(
                    replace(
                        value, state="host_failure", completion_receipt=receipt, elapsed_seconds=0
                    )
                )
        try:
            if capabilities.process_supervision:
                from autoengineering.campaign.execution import ProcessIdentity, identity_matches
                from autoengineering.campaign.store import checked_directory

                processes = self.store.root / "processes"
                processes.mkdir(mode=0o700, exist_ok=True)
                checked_directory(processes)

                def launched(receipt):
                    nonlocal value
                    identity = ProcessIdentity(**receipt)
                    if (
                        identity.nonce != value.launch_nonce
                        or identity.pid != identity.pgid
                        or not identity_matches(identity)
                    ):
                        raise ValueError("host launch ownership mismatch")
                    with self.store.writer():
                        reference = self.store.put_private(
                            canonical_json(receipt).encode(),
                            name="process.json",
                            media_type="application/json",
                        )
                        value = self.store.commit(
                            replace(value, state="running", process_receipt=reference)
                        )

                result = self.host.invoke_supervised(
                    task,
                    prompt,
                    InvocationContext(
                        invocation_id,
                        value.launch_nonce,
                        processes / invocation_id,
                        remaining,
                        output_limit,
                        launched,
                        self._cancelled,
                    ),
                )
            else:
                result = self.host.invoke(
                    task,
                    prompt,
                    invocation_id=invocation_id,
                    timeout_seconds=remaining,
                    max_output_bytes=output_limit,
                )
        except Exception:
            with self.store.writer():
                # A launch event may have committed before its acknowledgment
                # was lost. Preserve that authoritative ownership receipt.
                value = self.store.replay().invocations[invocation_id]
                receipt = self.store.put_private(
                    b'{"host_returned":false,"usage":"unknown"}',
                    name="completion.json",
                    media_type="application/json",
                )
                return self.store.commit(
                    replace(
                        value,
                        state="reconciliation_required"
                        if capabilities.process_supervision
                        else "host_failure",
                        completion_receipt=receipt,
                        elapsed_seconds=max(0, self.clock() - now),
                    )
                )
        with self.store.writer():
            raw = (
                result.raw_transcript
                if result.raw_transcript is not None
                else result.raw_output.encode("utf-8")
            )
            stderr = result.stderr or b""
            if len(raw) + len(stderr) > output_limit:
                raw = raw[:output_limit]
                stderr = stderr[: output_limit - len(raw)]
                status = "host_failure"
            else:
                status = result.status
            if not result.stop_verified:
                status = "reconciliation_required"
            raw_ref = self.store.put_private(raw, name="raw.txt", media_type="text/plain")
            stderr_ref = None
            final_ref = None
            if value.schema_version in ("1.1", "1.2"):
                stderr_ref = self.store.put_private(
                    stderr, name="stderr.txt", media_type="text/plain"
                )
                if len(result.raw_output.encode()) <= 65536:
                    final_ref = self.store.put_private(
                        result.raw_output.encode(), name="final.txt", media_type="text/plain"
                    )
                else:
                    status = "host_failure"
            receipt = self.store.put_private(
                canonical_json(
                    {
                        "status": status,
                        "host_returned": True,
                        "elapsed_seconds": result.elapsed_seconds,
                        "usage": dict(result.usage),
                        "stop_verified": result.stop_verified,
                    }
                ).encode(),
                name="completion.json",
                media_type="application/json",
            )
            # Persist raw bytes and the host result before interpreting worker text.
            value = self.store.commit(
                replace(
                    value,
                    state="reconciliation_required",
                    raw_response=raw_ref,
                    completion_receipt=receipt,
                    resolved_model=result.resolved_model,
                    elapsed_seconds=result.elapsed_seconds,
                    usage=result.usage,
                    final_response=final_ref,
                    stderr_response=stderr_ref,
                )
            )
            return self._normalize(
                value,
                result.raw_output,
                status,
                task=task,
                campaign_revision=campaign_revision,
                candidate_id=candidate_id,
                evaluation_id=evaluation_id,
                validator=validator,
            )

    def _normalize(
        self,
        value,
        text,
        status,
        *,
        task,
        campaign_revision,
        candidate_id=None,
        evaluation_id=None,
        validator=None,
    ):
        normalized = None
        parse_failure = None
        if status == "completed":
            try:
                handoff = RoleHandoff.from_json(text)
                validate_handoff(
                    handoff,
                    task,
                    invocation_id=value.id,
                    campaign_revision=campaign_revision,
                    permitted_implementations=self.store.spec.permitted_interventions,
                    candidate_id=candidate_id,
                    evaluation_id=evaluation_id,
                    generated=self.store.spec.execution_mode == "generated",
                )
                if validator is not None:
                    validator(handoff)
                normalized = self.store.put_private(
                    handoff.to_json().encode(),
                    name="handoff.json",
                    media_type="application/json",
                )
            except (ValueError, TypeError, UnicodeError) as error:
                status = "invalid_output"
                parse_failure = self.store.put_private(
                    canonical_json({"error": str(error), "schema": task.expected_schema}).encode(),
                    name="parse-failure.json",
                    media_type="application/json",
                )
        return self.store.commit(
            replace(value, state=status, normalized_output=normalized, parse_failure=parse_failure)
        )

    def handoff(self, invocation: WorkerInvocation) -> RoleHandoff:
        if invocation.state != "completed" or invocation.normalized_output is None:
            raise StoreError("invocation has no valid handoff")
        return RoleHandoff.from_json(
            read_bytes(self.store.root, invocation.normalized_output).decode()
        )

    @serialized_operation
    def recover_invocation(
        self,
        invocation_id: str,
        *,
        campaign_revision: int,
        candidate_id=None,
        evaluation_id=None,
        validator=None,
        stop_owned=False,
    ):
        """Reconcile saved results or explicitly stop a verifiably owned process.

        No new host call is made. Missing ownership or unresolved descendants
        preserve the pending state. Original completion receipts are immutable.
        """
        from autoengineering.campaign.artifacts import confined_file
        from autoengineering.campaign.execution import (
            ProcessIdentity,
            identity_matches,
            live_members,
            stop_recovered,
        )
        from autoengineering.campaign.spec import ExecutionSpec
        from autoengineering.campaign.serialization import unique_json
        from .process import recover_completed_process

        validate_run_spec(self.store.spec)
        with self.store.writer():
            projection = self.store.replay()
            value = projection.invocations.get(invocation_id)
            if value is None:
                raise StoreError("worker invocation is absent")
            if value.state not in ("reserved", "running", "reconciliation_required"):
                return value
            task = projection.tasks[value.task_id]
            raw, stderr, text, status = None, None, None, None
            evidence = {}
            if value.capabilities.host != "fake":
                if (
                    not _implemented_brokered_host(self.host, value.capabilities.host)
                    or self.host.capabilities() != value.capabilities
                ):
                    raise StoreError("brokered recovery capability mismatch")
                self.host.validate_selection(self.store.spec.host)
                if stop_owned:
                    self.host.cancel(value.id)
                prior = [v for key, v in projection.invocations.items() if key != value.id]
                used = sum(
                    v.prompt.size_bytes
                    + (v.raw_response.size_bytes if v.raw_response else 0)
                    + (v.stderr_response.size_bytes if v.stderr_response else 0)
                    for v in prior
                )
                original_limit = min(
                    65536, self.store.spec.limits.transcript_bytes - used - value.prompt.size_bytes
                )
                remaining = min(
                    task.deadline - value.started_at,
                    projection.started_at
                    + self.store.spec.limits.elapsed_seconds
                    - value.started_at,
                    self.store.spec.limits.worker_seconds,
                )
                if value.process_receipt is not None and unique_json(
                    read_bytes(self.store.root, value.process_receipt).decode()
                ) != unique_json(
                    confined_file(
                        self.store.root, f"processes/{value.id}/transport/client/process.json"
                    ).read_text()
                ):
                    raise StoreError("brokered process differs from journaled ownership")
                result = self.host.recover_supervised(
                    task,
                    read_bytes(self.store.root, value.prompt).decode(),
                    InvocationContext(
                        value.id,
                        value.launch_nonce,
                        self.store.root / "processes" / value.id,
                        remaining,
                        original_limit,
                        lambda _: None,
                        self._cancelled,
                    ),
                )
                if not result.stop_verified or result.status == "reconciliation_required":
                    raise StoreError("brokered host stop remains unverified")
                raw = (
                    result.raw_transcript
                    if result.raw_transcript is not None
                    else result.raw_output.encode()
                )
                stderr = result.stderr or b""
                if len(raw) + len(stderr) > original_limit:
                    raise StoreError("recovered brokered output exceeds original allowance")
                text, status = result.raw_output, result.status
                if (
                    value.raw_response is not None
                    and read_bytes(self.store.root, value.raw_response) != raw
                ):
                    raise StoreError("brokered recovery differs from journaled raw output")
                value = replace(
                    value,
                    resolved_model=result.resolved_model,
                    usage=result.usage,
                    elapsed_seconds=result.elapsed_seconds,
                )
                evidence = {
                    "kind": "abandoned_brokered_transport"
                    if result.elapsed_seconds is None
                    else "brokered_transport",
                    "status": status,
                    "stop_verified": True,
                    "adapter_manifest_sha256": hashlib.sha256(
                        confined_file(
                            self.store.root, f"processes/{value.id}/adapter.json"
                        ).read_bytes()
                    ).hexdigest(),
                }
                upstream_attempt = self.store.root / "processes" / value.id / "upstream/attempt"
                if upstream_attempt.exists():
                    from .hosts.command_upstream import inspect_command_stop

                    upstream_stop = inspect_command_stop(upstream_attempt)
                    if upstream_stop["state"] != "verified_stopped":
                        raise StoreError("upstream command stop remains unverified")
                    evidence["upstream_stop"] = upstream_stop
                if result.elapsed_seconds is None:
                    evidence["usage"] = "unknown"
                    evidence["elapsed_seconds"] = None
                    evidence["raw_result_recovered"] = False
                    evidence["bindings"] = {
                        name: hashlib.sha256(
                            confined_file(
                                self.store.root, f"processes/{value.id}/{name}"
                            ).read_bytes()
                        ).hexdigest()
                        for name in (
                            "transport/transport.json",
                            "transport/client/watchdog-job.json",
                            "transport/client/watchdog-result.json",
                            "upstream/policy.json",
                            "upstream/attempt/upstream.json",
                            "upstream/attempt/process/watchdog-job.json",
                            "upstream/attempt/process/watchdog-result.json",
                        )
                    }
            if (
                status is None
                and value.raw_response is not None
                and value.completion_receipt is not None
            ):
                receipt = unique_json(
                    read_bytes(self.store.root, value.completion_receipt).decode()
                )
                if (
                    receipt.get("host_returned") is True or receipt.get("recovered") is True
                ) and receipt.get("stop_verified") is True:
                    status = receipt["status"]
                    reference = value.final_response or value.raw_response
                    try:
                        text = read_bytes(self.store.root, reference).decode("utf-8")
                    except UnicodeError:
                        text = None
                    evidence = {
                        "kind": "journaled_result",
                        "completion_digest": value.completion_receipt.sha256,
                    }
            if status is None and value.capabilities.process_supervision:
                if value.schema_version != "1.2":
                    raise StoreError("physical recovery requires an invocation 1.2 receipt")
                directory = self.store.root / "processes" / value.id
                if directory.is_symlink():
                    raise StoreError("physical recovery directory is a symlink")
                if not directory.exists() and value.process_receipt is None:
                    # Directory and intent durability precede Popen in this
                    # source-bound protocol, so no physical host was launched.
                    status = "host_failure"
                    evidence = {"kind": "no_physical_launch", "usage": "unknown"}
                elif (directory / "completion.json").exists():
                    result = recover_completed_process(
                        directory,
                        nonce=value.launch_nonce,
                        max_output_bytes=min(65536, self.store.spec.limits.transcript_bytes),
                    )
                    if value.process_receipt is not None and (
                        result.identity is None
                        or result.identity.to_dict()
                        != unique_json(read_bytes(self.store.root, value.process_receipt).decode())
                    ):
                        raise StoreError("physical completion differs from journaled ownership")
                    if value.capabilities.host != "fake":
                        raise StoreError("qualified provider recovery decoder is unavailable")
                    raw, stderr = result.stdout, result.stderr
                    try:
                        text = raw.decode("utf-8")
                    except UnicodeError:
                        text = None
                    status = (
                        result.status
                        if result.status in ("completed", "timeout", "cancelled")
                        else "host_failure"
                    )
                    value = replace(value, elapsed_seconds=result.elapsed_seconds)
                    evidence = {
                        "kind": "physical_result",
                        "receipt_digest": __import__("hashlib")
                        .sha256(confined_file(directory, "completion.json").read_bytes())
                        .hexdigest(),
                    }
                else:
                    if value.process_receipt is None:
                        raise StoreError("launch outcome has no journaled ownership receipt")
                    identity = ProcessIdentity(
                        **unique_json(read_bytes(self.store.root, value.process_receipt).decode())
                    )
                    if (
                        type(identity.pid) is not int
                        or identity.pid <= 1
                        or identity.pid != identity.pgid
                        or identity.nonce != value.launch_nonce
                    ):
                        raise StoreError("invalid recovery ownership receipt")
                    if identity_matches(identity):
                        if not stop_owned:
                            raise StoreError("owned worker is still running")
                        if not stop_recovered(
                            identity,
                            ExecutionSpec(
                                ("host",), termination_grace_seconds=0.2, kill_wait_seconds=1
                            ),
                        ):
                            raise StoreError("owned worker stop remains unverified")
                        status = "cancelled"
                        evidence = {"kind": "verified_owned_stop", "usage": "unknown"}
                    elif not live_members(identity.pgid):
                        status = "host_failure"
                        evidence = {"kind": "verified_absent_group", "usage": "unknown"}
                    else:
                        raise StoreError("process root is unverifiable and descendants remain")
            if status is None:
                raise StoreError("worker outcome remains unresolved")
            if value.schema_version == "1.2":
                recovery = value.recovery_receipt or self.store.put_private(
                    canonical_json(evidence).encode(),
                    name="recovery.json",
                    media_type="application/json",
                )
                value = replace(value, recovery_receipt=recovery)
            if raw is not None:
                raw_ref = self.store.put_private(raw, name="raw.txt", media_type="text/plain")
                stderr_ref = self.store.put_private(
                    stderr, name="stderr.txt", media_type="text/plain"
                )
                final_ref = (
                    self.store.put_private(text.encode(), name="final.txt", media_type="text/plain")
                    if text is not None
                    else None
                )
                value = replace(
                    value,
                    raw_response=raw_ref,
                    stderr_response=stderr_ref,
                    final_response=final_ref,
                )
            if value.completion_receipt is None:
                value = replace(
                    value,
                    completion_receipt=self.store.put_private(
                        canonical_json(
                            {
                                "status": status,
                                "stop_verified": True,
                                "recovered": True,
                                "usage": "unknown",
                            }
                        ).encode(),
                        name="recovered-completion.json",
                        media_type="application/json",
                    ),
                )
            # Journal restored bytes before validating the role output.
            value = self.store.commit(replace(value, state="reconciliation_required"))
            if status == "completed" and text is None:
                text = "invalid UTF-8 host payload"
            return self._normalize(
                value,
                text,
                status,
                task=task,
                campaign_revision=campaign_revision,
                candidate_id=candidate_id,
                evaluation_id=evaluation_id,
                validator=validator,
            )
