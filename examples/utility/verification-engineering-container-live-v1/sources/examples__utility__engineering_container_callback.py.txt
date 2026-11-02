"""Join authorized generated-source access to a supplied fixed container runtime.

This is a separate candidate callback. It does not admit a runtime, execute a
model on the host, infer a successful start from an allocation, or retry an
uncertain source read/runtime operation. Runtime qualification remains separate.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.confirmation import read_manifest, read_selected_state
from autoengineering.utility.execution_receipts import ConfirmationContainerExecution
from autoengineering.utility.load_container_costs import (
    WORK_DIRECTORY,
    ContainerLoadCostRegistration,
    ContainerLoadWorkReceipt,
    decode_worker_output,
    join_container_load_costs,
    validate_container_resources,
    verify_runtime_execution,
)
from autoengineering.utility.load_costs import _charged_scope
from examples.utility import engineering_source_binding as binding


def source_identity():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


@dataclass(frozen=True)
class ContainerLoadRun:
    """Supplied runtime result. The callback validates every field before use."""

    output: bytes
    execution: ConfirmationContainerExecution
    packet_sha256: str


class ContainerLoadScorer:
    def __init__(self, store, public_root, private_root, work_root, *, registration, runtime):
        if not isinstance(registration, ContainerLoadCostRegistration):
            raise ValueError("versioned coupled-container registration required")
        self.store, self.registration, self.runtime = store, registration, runtime
        self.public_root = checked_directory(public_root)
        self.private_root = checked_directory(private_root)
        self.work_root = checked_directory(work_root)
        roots = (store.root, self.public_root, self.private_root, self.work_root)
        if any(
            a.is_relative_to(b) or b.is_relative_to(a)
            for i, a in enumerate(roots)
            for b in roots[i + 1 :]
        ):
            raise ValueError("coupled-container source and work scopes must be separate")
        self.binding = binding.read_binding(store, registration.binding_artifact)
        self.outcome_contract = registration.outcome
        self.identity = binding.scorer_identity(self.binding, registration.code_digest)
        self._verify_registration()

    def _verify_registration(self):
        r = self.registration
        if (
            r.callback_source_digest != source_identity()
            or self.runtime.registration != r.runtime
            or self.runtime.source_identity() != r.runtime.runtime_source_digest
            or self.identity != binding.scorer_identity(self.binding, r.code_digest)
        ):
            raise ValueError("coupled-container callback or runtime changed")

    def __call__(self, grant, model):
        self._verify_registration()
        fixed, access, receipt = _charged_scope(self.store, grant, self.registration)
        state = self.store.replay()
        attempt = "confirmation-" + grant.cell_digest[:48]
        if (
            access is None
            or receipt is not None
            or model.sha256 != grant.model_digest
            or fixed.digest != self.binding.digest
            or state["attempts"][attempt][1] != "started"
        ):
            raise ValueError("coupled container needs its original active confirmation access")
        validate_container_resources(grant, self.registration.runtime)
        selected = read_selected_state(
            self.store.root,
            next(
                c
                for c in read_manifest(self.store.root, state["frozen"]).cells
                if c.cell_digest == grant.cell_digest
            ).selected_state,
        )
        # The trusted runtime preflight must check daemon/image/source policy
        # before the one durable private-source read. It receives no source rows.
        self.runtime.preflight(grant)
        scope = self.work_root / grant.digest
        scope.mkdir(mode=0o700)
        durable_write(
            scope / "intent.json",
            canonical_json(
                {
                    "grant_digest": grant.digest,
                    "registration_digest": self.registration.digest,
                    "source_binding_digest": fixed.digest,
                    "automatic_retries": 0,
                }
            ).encode(),
        )
        rows = binding.open_for_confirmation(
            self.store,
            grant,
            self.registration.binding_artifact,
            self.public_root,
            self.private_root,
            scorer_code_digest=self.registration.code_digest,
        )
        p = self.registration.policy
        packet = canonical_json(
            {
                "schema": "utility-coupled-load-packet-v1",
                "execution_digest": grant.digest,
                "source_binding_digest": fixed.digest,
                "model_digest": p.expected_model_digest,
                "kernel_digest": p.scorer_source_digest,
                "source_current_A": selected.configuration["source_current"],
                "minimum_node2_voltage_V": p.minimum_node2_voltage_V,
                "cases": rows,
            }
        ).encode()
        pin = hashlib.sha256(packet).hexdigest()
        if len(packet) > 32768:
            raise ValueError("coupled source packet exceeds fixed worker envelope")
        self._verify_registration()
        run = self.runtime.run(grant, packet, expected_sha256=pin, work_root=scope)
        if not isinstance(run, ContainerLoadRun) or run.packet_sha256 != pin:
            raise ValueError("coupled runtime returned a foreign packet result")
        work = decode_worker_output(run.output)
        verify_runtime_execution(
            run.execution, self.registration.runtime, grant=grant, score=work.score
        )
        output = put_bytes(
            self.store.root,
            run.output,
            name="coupled-worker-output.json",
            media_type="application/json",
            producer="engineering-container-output",
        )
        proof = ContainerLoadWorkReceipt(
            "utility-container-load-work-v1",
            grant.digest,
            self.identity,
            fixed.digest,
            p.digest,
            pin,
            output,
            run.execution,
        )
        public = self.store.root / WORK_DIRECTORY
        if public.is_symlink():
            raise ValueError("coupled work receipt scope is a symlink")
        public.mkdir(mode=0o700, exist_ok=True)
        checked_directory(public)
        durable_write(public / (grant.digest + ".json"), proof.to_json().encode())
        artifact = reference(
            self.store.root,
            f"{WORK_DIRECTORY}/{grant.digest}.json",
            media_type="application/json",
            producer="engineering-container-load-work",
        )
        # Recovery uses this original pin. It must not refresh a changed public
        # work record or repeat a runtime whose final publication was uncertain.
        durable_write(
            scope / "complete.json",
            canonical_json(
                {
                    "schema": "utility-container-load-completion-v1",
                    "registration_digest": self.registration.digest,
                    "work_artifact": artifact.to_dict(),
                }
            ).encode(),
        )
        return work.score

    def _read_completed(self, grant, model):
        self._verify_registration()
        if model.sha256 != grant.model_digest:
            raise ValueError("coupled recovery selected model differs")
        path = confined_file(self.work_root, f"{grant.digest}/complete.json")
        if path.stat().st_size > 65536:
            raise ValueError("coupled completion exceeds metadata envelope")
        anchor = unique_json(path.read_text())
        if set(anchor) != {"schema", "registration_digest", "work_artifact"} or (
            anchor["schema"],
            anchor["registration_digest"],
        ) != ("utility-container-load-completion-v1", self.registration.digest):
            raise ValueError("coupled completion registration differs")
        artifact = ArtifactRef.from_dict(anchor["work_artifact"])
        join_container_load_costs(self.store, grant, self.registration, work_artifact=artifact)
        proof = ContainerLoadWorkReceipt.from_dict(
            unique_json(read_bytes(self.store.root, artifact, max_bytes=65536).decode())
        )
        work = decode_worker_output(
            read_bytes(self.store.root, proof.output_artifact, max_bytes=16384)
        )
        return proof, work

    def recover(self, grant, model):
        """Read only pinned completion metadata; no runtime preflight or source read."""
        _, work = self._read_completed(grant, model)
        return work.score

    def public_execution(self, grant, model, score):
        proof, work = self._read_completed(grant, model)
        if work.score != score or proof.source_binding_digest != self.binding.digest:
            raise ValueError("coupled execution differs from source or score")
        verify_runtime_execution(
            proof.execution, self.registration.runtime, grant=grant, score=score
        )
        return proof.execution
