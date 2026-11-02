"""Native adapter reservations shared across serial batch cases.

This is a trusted runner adapter, not a new host/provider. It preserves the
native profile and worker journal contracts. A manifest grants no live authority.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import StoreError

from .batch import BatchStore, PhysicalObservation, PhysicalReservation
from .host_configuration import HostConfiguration
from .hosts.brokered_host import BrokeredCodexHost, WIRE_SCHEMA


class BatchCodexHost(BrokeredCodexHost):
    def __init__(self, configuration: HostConfiguration, batch: BatchStore, case_id: str):
        self.batch, self.case_id = batch, case_id
        if case_id not in {case.id for case in batch.spec.cases}:
            raise StoreError("native host case is absent from frozen batch")
        if batch._trusted_pin != batch.digest:
            raise StoreError("native batch host requires a caller-pinned manifest")
        configuration.check_scope(batch.root)
        if configuration.digest != batch.spec.host_configuration_digest:
            raise StoreError("native host configuration differs from frozen batch")
        super().__init__(
            qualification_root=configuration.qualification_root,
            qualification_digest=configuration.qualification_digest,
            credential_path=configuration.credential_path,
            lease_id=configuration.lease_id,
            model=batch.spec.host.requested_model,
        )
        self.validate_selection(batch.spec.host)
        self.validate_limits(batch.spec.limits)
        if super().capabilities() != batch.spec.capabilities:
            raise StoreError("native capabilities differ from frozen batch")

    def capabilities(self):
        original = super().capabilities()
        return replace(
            original,
            executable_version=original.executable_version
            + ":batch:"
            + self.batch.digest
            + ":"
            + self.case_id,
        )

    def _key(self, context):
        return "native-" + digest({"case": self.case_id, "invocation": context.invocation_id})[:32]

    def _identity(self, task, prompt, context):
        scope = self.batch.root / "cases" / self.case_id
        if not Path(context.directory).resolve().is_relative_to(scope):
            raise StoreError("native invocation lies outside its frozen batch case")
        return digest(
            {
                "case": self.case_id,
                "task": task.to_dict(),
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "invocation": context.invocation_id,
                "nonce": context.nonce,
                "directory": str(Path(context.directory).absolute()),
                "original_timeout": context.timeout_seconds,
                "output_limit": context.max_output_bytes,
            }
        )

    def _observation(self, reservation, result, context):
        root = Path(context.directory)
        # Local termination can be proven while response reconciliation is
        # pending. The batch must retain that unresolved reservation and ceiling.
        settled = result.stop_verified and result.status != "reconciliation_required"
        bindings = {}
        names = [
            "adapter.json",
            "transport/transport.json",
            "transport/client/completion.json",
            "upstream-stop.json",
            "upstream/attempt/provider-intent.json",
        ]
        names.extend(
            str(p.relative_to(root)) for p in sorted((root / "transport/stops").glob("*.json"))
        )
        for name in names:
            path = root / name
            if path.exists() or path.is_symlink():
                path = confined_file(root, name)
                if path.stat().st_size > 65536:
                    raise StoreError("batch native receipt exceeds limit")
                bindings[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        intent = (
            "present"
            if "upstream/attempt/provider-intent.json" in bindings
            else "absent"
            if result.stop_verified
            else "unknown"
        )
        raw = (
            result.raw_transcript
            if result.raw_transcript is not None
            else result.raw_output.encode()
        )
        size = (
            reservation.prompt_bytes
            + len(raw)
            + len(result.stderr or b"")
            + len(result.raw_output.encode())
            if settled and result.elapsed_seconds is not None
            else None
        )
        proof = self.batch.evidence(
            {
                "kind": "native_adapter_observation",
                "scope": str(root),
                "bindings": bindings,
                "reservation": reservation.id,
                "status": result.status,
                "stop_verified": settled,
                "local_stop_verified": result.stop_verified,
                "request_intent": intent,
            }
        )
        return PhysicalObservation(
            reservation.id,
            result.status,
            settled,
            size,
            result.usage,
            result.resolved_model,
            intent,
            result.elapsed_seconds,
            (proof,),
        )

    def invoke_supervised(self, task, prompt, context):
        now = self.batch.clock()
        remaining = self.batch.created_at + self.batch.spec.limits.elapsed_seconds - now
        available = (
            self.batch.spec.limits.transcript_bytes - self.batch.replay().charged_transcript_bytes
        )
        output_limit = min(context.max_output_bytes, (available - len(prompt.encode())) // 2)
        if output_limit <= 0:
            raise StoreError("batch transcript allowance exhausted before native launch")
        reservation = PhysicalReservation(
            self._key(context),
            self.case_id,
            "host",
            self._identity(task, prompt, context),
            task.id,
            now,
            min(context.timeout_seconds, remaining),
            len(prompt.encode()),
            output_limit,
            len(canonical_json(WIRE_SCHEMA).encode()),
        )
        bounded = replace(
            context,
            timeout_seconds=reservation.timeout_seconds,
            max_output_bytes=reservation.output_limit,
        )
        return self.batch.execute(
            reservation,
            lambda _: super(BatchCodexHost, self).invoke_supervised(task, prompt, bounded),
            lambda r, result: self._observation(r, result, bounded),
        )

    def recover_supervised(self, task, prompt, context):
        with self.batch.operation():
            reservation = self.batch.replay().reservations.get(self._key(context))
            if reservation is None or reservation.invocation_digest != self._identity(
                task, prompt, context
            ):
                raise StoreError("original native batch reservation is absent or changed")
            bounded = replace(
                context,
                timeout_seconds=reservation.timeout_seconds,
                max_output_bytes=reservation.output_limit,
            )
            result = super().recover_supervised(task, prompt, bounded)
            self.batch.observe(self._observation(reservation, result, bounded))
            return result
