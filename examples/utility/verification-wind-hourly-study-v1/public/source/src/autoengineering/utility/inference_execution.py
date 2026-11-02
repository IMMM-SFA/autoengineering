"""Candidate supervised frozen inference stage, separate from private scoring admission."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import math
import sys
from typing import Literal
from uuid import uuid4

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes, reference
from autoengineering.campaign.execution import (
    ProcessIdentity,
    SupervisedResult,
    live_members,
    supervise,
)
from autoengineering.campaign.records import ArtifactRef, CheckResult, ExecutionStatus
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.spec import ExecutionSpec
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .confirmation import read_selected_state
from .scoring import CompositeConfirmationGrant, validate_grant
from .inference_guest import FrozenGuestProfile, guest_executor_identity, guest_scope
from autoengineering.optimization import NpzReadLimits

PHYSICAL_CHECKS = ("finite", "nonnegative", "soil_capacity", "daily_balance")


@dataclass(frozen=True)
class FrozenInferenceJob(Record):
    schema: Literal["utility-frozen-inference-job-v1"]
    grant: CompositeConfirmationGrant
    executor_digest: str
    source_digest: str
    sources: tuple[ArtifactRef, ...]
    lock: ArtifactRef
    nonce: str
    staged_driver: ArtifactRef

    @classmethod
    def from_dict(cls, value):
        from collections.abc import Mapping

        if (
            cls is FrozenInferenceJob
            and isinstance(value, Mapping)
            and value.get("schema") == "utility-frozen-inference-job-v2"
        ):
            return FrozenGuestInferenceJob.from_dict(value)
        return super().from_dict(value)

    def claim_scope(self, root):
        return digest(str(root))

    def validate_runtime(self, root):
        if self.executor_digest != executor_identity(self.source_digest, self.lock):
            raise ValueError("inference worker environment differs")

    def _validate(self):
        from .contracts import sha256

        sha256(self.executor_digest)
        sha256(self.source_digest)
        _nonce(self.nonce)


@dataclass(frozen=True)
class FrozenGuestInferenceJob(FrozenInferenceJob):
    schema: Literal["utility-frozen-inference-job-v2"]
    guest: FrozenGuestProfile
    environment: ArtifactRef

    def _validate(self):
        super()._validate()
        if (
            self.lock.sha256 != self.guest.lock_digest
            or digest([r.to_dict() for r in self.sources]) != self.source_digest
            or len({r.path for r in self.sources}) != len(self.sources)
            or self.executor_digest
            != guest_executor_identity(self.source_digest, self.lock.sha256, self.guest)
            or self.environment.media_type != "application/json"
            or self.environment.size_bytes > 4 * 1024 * 1024
        ):
            raise ValueError("guest inference job differs from its runtime/environment binding")

    def claim_scope(self, root):
        return guest_scope(self)

    def validate_runtime(self, root):
        from .inference_guest import validate_guest_context

        validate_guest_context(self, root)


@dataclass(frozen=True)
class FrozenInferenceResult(Record):
    schema: Literal["utility-frozen-inference-result-v1"]
    grant_digest: str
    executor_digest: str
    nonce: str
    status: ExecutionStatus
    outputs: ArtifactRef | None
    predictions: ArtifactRef | None
    checks: tuple[CheckResult, ...]
    lifecycle_seconds: float | None

    def _validate(self):
        from .contracts import sha256

        for value in (self.grant_digest, self.executor_digest):
            sha256(value)
        if self.lifecycle_seconds is not None and self.lifecycle_seconds < 0:
            raise ValueError("inference lifecycle time must be nonnegative")
        if self.status == "success" and (
            self.outputs is None
            or self.predictions is None
            or not self.checks
            or any(c.required and c.status != "pass" for c in self.checks)
        ):
            raise ValueError("successful inference needs outputs and physical checks")
        if self.status != "success" and self.predictions is not None:
            raise ValueError("failed inference cannot supply a scoring vector")
        _nonce(self.nonce)
        if self.status in ("success", "scientific_infeasible"):
            if (
                self.outputs is None
                or self.lifecycle_seconds is None
                or tuple((c.name, c.version, c.required) for c in self.checks)
                != tuple((name, "1", True) for name in PHYSICAL_CHECKS)
            ):
                raise ValueError("completed inference requires all fixed physical checks")
            if self.status == "scientific_infeasible" and all(
                c.status == "pass" for c in self.checks
            ):
                raise ValueError("scientific rejection requires a failed physical check")


@dataclass(frozen=True)
class FrozenInferenceReceipt(Record):
    schema: Literal["utility-frozen-inference-receipt-v1"]
    grant_digest: str
    executor_digest: str
    nonce: str
    status: ExecutionStatus
    stop_verified: bool
    supervisor: ArtifactRef
    result: ArtifactRef | None
    claim: ArtifactRef

    def _validate(self):
        from .contracts import sha256

        sha256(self.grant_digest)
        sha256(self.executor_digest)
        _nonce(self.nonce)
        if self.status == "success" and (not self.stop_verified or self.result is None):
            raise ValueError("inference success needs its stopped original result")


def _nonce(value):
    import re

    if not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValueError("inference needs its original launch nonce")


def executor_identity(source_digest, lock):
    return digest(
        {
            "profile": "trusted-frozen-routing-stage-candidate-v1",
            "sources": source_digest,
            "lock": lock.sha256,
            "python": sys.version,
            "boundary": "unqualified-trusted-local-process",
        }
    )


def driver_limits(replay):
    member = 16 * len(replay.forcing.ports[0].time.dates) + 4096
    total = member * len(replay.forcing.ports)
    return NpzReadLimits(
        max_compressed_bytes=total + 65536,
        max_members=len(replay.forcing.ports),
        max_member_bytes=member,
        max_total_bytes=total,
    )


def verify_code(root, sources, lock, source_digest, model):
    """Verify code/environment only; source inventories may also name unread data."""
    if (
        digest([r.to_dict() for r in sources]) != source_digest
        or lock.sha256 != model.dependency_bundle
    ):
        raise StoreError("frozen inference source/environment identity differs")
    declared = {r.path: r for r in sources}
    if len(declared) != len(sources):
        raise StoreError("frozen inference source inventory contains duplicates")
    read_bytes(root, lock)
    package = Path(__file__).resolve().parents[1]
    for path in package.rglob("*.py"):
        relative = "src/autoengineering/" + str(path.relative_to(package))
        ref = declared.get(relative)
        if ref is None:
            raise StoreError("frozen inference engine source closure is incomplete")
        read_bytes(root, ref)
        read_bytes(package, replace(ref, path=str(path.relative_to(package))))
    for ref in model.source_bundle:
        if declared.get(ref.path) != ref:
            raise StoreError("frozen inference model sources are absent from inventory")
        read_bytes(root, ref)


class FrozenRoutingExecutor:
    """Fixed supplied code only. This candidate does not provide OS label isolation.

    A composite access reservation must already exist. No CLI/scorer registration
    activates this stage. Authored runs establish lifecycle behavior only.
    """

    def __init__(self, store, source_root, driver_root, work_root, *, sources, lock):
        self.store = store
        self.source_root = checked_directory(source_root)
        self.driver_root = checked_directory(driver_root)
        self.work_root = checked_directory(work_root)
        if any(
            self.work_root.is_relative_to(p) or p.is_relative_to(self.work_root)
            for p in (store.root, self.source_root, self.driver_root)
        ):
            raise StoreError("inference work must be separate from public and driver scopes")
        if any(
            self.driver_root.is_relative_to(p) or p.is_relative_to(self.driver_root)
            for p in (store.root, self.source_root)
        ):
            raise StoreError("inference drivers must be separate from public scopes")
        self.sources, self.lock = tuple(sources), lock
        if lock.sha256 != store.spec.lock_digest:
            raise StoreError("inference lock differs from frozen suite")
        self.identity = executor_identity(store.spec.source_digest, lock)

    def _preflight(self, grant, *, recovery=False):
        if not isinstance(grant, CompositeConfirmationGrant):
            raise StoreError("frozen inference requires a composite grant")
        state = self.store.replay()
        if state["cancelled"] and not recovery:
            raise StoreError("cancelled suite cannot start inference")
        selected = validate_grant(self.store, grant, state["frozen"])
        attempt = "confirmation-" + grant.cell_digest[:48]
        allocation = state["attempts"].get(attempt)
        if allocation is None or allocation[1] not in ("started", "finished"):
            raise StoreError("inference lacks an original composite access reservation")
        event = allocation[0]
        if (event.phase, event.child_digest, event.resources) != (
            "confirmation",
            grant.digest,
            grant.resources,
        ) or attempt not in state["confirmation_accesses"]:
            raise StoreError("inference differs from the charged composite access")
        bound = read_selected_state(self.store.root, selected.selected_state)
        if (
            grant.inference.forcing.artifact.size_bytes
            > driver_limits(grant.inference).max_compressed_bytes
        ):
            raise StoreError("inference drivers exceed the declared array shape envelope")
        verify_code(
            self.source_root, self.sources, self.lock, self.store.spec.source_digest, bound.model
        )
        return bound

    def _claim(self, grant, root, job):
        directory = self.store.root / "inference-claims"
        directory.mkdir(mode=0o700, exist_ok=True)
        checked_directory(directory)
        path = directory / f"{grant.digest}.json"
        if path.exists() or path.is_symlink():
            raise StoreError("inference grant is already claimed; explicit recovery required")
        value = {
            "grant": grant.digest,
            "executor": self.identity,
            "nonce": job.nonce,
            "job": job.digest,
            "scope": job.claim_scope(root),
        }
        ref = put_bytes(
            self.store.root,
            _encoded(value),
            name="inference-claim.json",
            media_type="application/json",
            producer="trusted-inference",
        )
        try:
            # Atomic create-only publication works while a caller holds the suite writer too.
            durable_write(path, ref.to_json().encode())
        except FileExistsError:
            raise StoreError("inference grant was claimed concurrently; retry refused") from None
        return ref

    def _read_claim(self, grant, root, job):
        ref = ArtifactRef.from_json(
            confined_file(self.store.root, f"inference-claims/{grant.digest}.json").read_text()
        )
        value = unique_json(read_bytes(self.store.root, ref, max_bytes=65536).decode())
        if value != {
            "grant": grant.digest,
            "executor": self.identity,
            "nonce": job.nonce,
            "job": job.digest,
            "scope": job.claim_scope(root),
        }:
            raise StoreError("inference differs from its original suite claim")
        return ref

    def execute(self, grant):
        bound = self._preflight(grant)
        root = self.work_root / grant.digest
        if root.exists() or root.is_symlink():
            raise StoreError("inference attempt exists; explicit recovery required")
        nonce = uuid4().hex
        original = grant.inference.forcing.artifact
        driver = ArtifactRef(
            f"artifacts/{original.sha256}/drivers.npz",
            original.sha256,
            original.size_bytes,
            "application/x-npz",
            "inference",
            {},
        )
        job = FrozenInferenceJob(
            "utility-frozen-inference-job-v1",
            grant,
            self.identity,
            self.store.spec.source_digest,
            self.sources,
            self.lock,
            nonce,
            driver,
        )
        claim = self._claim(grant, root, job)
        root.mkdir(mode=0o700)
        for name in ("artifacts", "attempts", "control"):
            (root / name).mkdir(mode=0o700)
        durable_write(root / "claim.json", read_bytes(self.store.root, claim, max_bytes=65536))
        durable_write(root / "job.json", job.to_json().encode())
        durable_write(
            root / "intent.json",
            _encoded(
                {
                    "grant": grant.digest,
                    "executor": self.identity,
                    "nonce": nonce,
                    "job": job.digest,
                }
            ),
        )
        # First reserved-driver byte access follows durable suite and stage intents.
        try:
            raw = read_bytes(
                self.driver_root,
                original,
                max_bytes=driver_limits(grant.inference).max_compressed_bytes,
            )
        except Exception:
            raise StoreError("reserved inference driver access failed; intent retained") from None
        saved_driver = put_bytes(
            root, raw, name="drivers.npz", media_type="application/x-npz", producer="inference"
        )
        if saved_driver != driver:
            raise StoreError("staged inference drivers differ from original grant")
        assets = (
            self.lock,
            grant.inference.selected_state,
            grant.inference.runtime_profile,
            *bound.training.references(),
            *bound.model.source_bundle,
            *(
                r
                for r in self.sources
                if r.path.startswith("src/autoengineering/") and r.path.endswith(".py")
            ),
        )
        for ref in assets:
            origin = (
                self.store.root
                if ref
                in (
                    grant.inference.selected_state,
                    grant.inference.runtime_profile,
                    *bound.training.references(),
                )
                else self.source_root
            )
            target = root / ref.path
            content = read_bytes(origin, ref)
            if target.exists():
                read_bytes(root, ref)
            else:
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                durable_write(target, content)
        from autoengineering.campaign.runtime import RUNTIME_ROOT

        supervise(
            (
                sys.executable,
                "-m",
                "autoengineering.utility.inference_worker",
                str(root / "job.json"),
            ),
            root=root,
            attempt_id="inference",
            campaign_id="frozen-routing-inference",
            settings=ExecutionSpec(
                ("hydrology-learned-routing-v1",), timeout_seconds=grant.inference.timeout_seconds
            ),
            cwd=RUNTIME_ROOT,
            launch_nonce=nonce,
        )
        return self.recover(grant)

    def recover(self, grant):
        self._preflight(grant, recovery=True)
        root = self.work_root / grant.digest
        intent = unique_json(confined_file(root, "intent.json").read_text())
        job = FrozenInferenceJob.from_json(confined_file(root, "job.json").read_text())
        claim = self._read_claim(grant, root, job)
        if intent != {
            "grant": grant.digest,
            "executor": self.identity,
            "nonce": job.nonce,
            "job": job.digest,
        }:
            raise StoreError("original inference intent differs")
        if (
            job.grant != grant
            or job.executor_digest != self.identity
            or job.nonce != intent["nonce"]
        ):
            raise StoreError("original inference job differs")
        folder = root / "attempts/inference"
        supervisor = reference(
            root,
            "attempts/inference/supervisor-result.json",
            media_type="application/json",
            producer="supervisor",
        )
        raw = unique_json(read_bytes(root, supervisor, max_bytes=65536).decode())
        proof = SupervisedResult(**dict(raw, identity=ProcessIdentity(**raw["identity"])))
        identity = ProcessIdentity(**unique_json(confined_file(folder, "process.json").read_text()))
        if (
            proof.identity != identity
            or identity.nonce != job.nonce
            or type(identity.pid) is not int
            or identity.pid <= 0
            or type(identity.pgid) is not int
            or identity.pgid != identity.pid
            or proof.stopped is not True
            or type(proof.elapsed_seconds) not in (int, float)
            or type(proof.returncode) is not int
            or type(proof.receipt_valid) is not bool
            or not math.isfinite(proof.elapsed_seconds)
            or proof.elapsed_seconds < 0
            or live_members(identity.pgid)
        ):
            raise StoreError("original inference stop is unverified")
        if (
            proof.status not in ("success", "model_failure", "timeout", "infrastructure_failure")
            or proof.stop_reason not in (None, "timeout", "cancelled")
            or (
                proof.status == "success"
                and (
                    proof.returncode != 0
                    or not proof.receipt_valid
                    or proof.stop_reason is not None
                )
            )
            or (proof.status == "timeout") != (proof.stop_reason == "timeout")
            or (proof.stop_reason == "cancelled" and proof.status != "infrastructure_failure")
        ):
            raise StoreError("original inference supervisor status is inconsistent")
        result_ref = None
        status = "timeout" if proof.status == "timeout" else "infrastructure_failure"
        if proof.status == "success" and proof.receipt_valid:
            result_ref = reference(
                root, "worker-result.json", media_type="application/json", producer="inference"
            )
            result = FrozenInferenceResult.from_json(
                read_bytes(root, result_ref, max_bytes=65536).decode()
            )
            if (result.grant_digest, result.executor_digest, result.nonce) != (
                grant.digest,
                self.identity,
                job.nonce,
            ):
                raise StoreError("original inference result differs")
            for ref in (result.outputs, result.predictions):
                if ref is not None:
                    read_bytes(
                        root,
                        ref,
                        max_bytes=grant.inference.output_limit_bytes
                        if ref == result.outputs
                        else 1048576,
                    )
            status = result.status
        receipt = FrozenInferenceReceipt(
            "utility-frozen-inference-receipt-v1",
            grant.digest,
            self.identity,
            job.nonce,
            status,
            True,
            supervisor,
            result_ref,
            claim,
        )
        path = root / "execution.json"
        if path.exists():
            if path.read_bytes() != receipt.to_json().encode():
                raise StoreError("inference receipt changed")
        else:
            durable_write(path, receipt.to_json().encode())
        return receipt


def _encoded(value):
    from autoengineering.campaign.serialization import canonical_json

    return canonical_json(value).encode()
