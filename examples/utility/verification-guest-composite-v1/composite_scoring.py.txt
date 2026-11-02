"""Candidate frozen-inference/vector-score chain with explicit nested identities.

Only application construction activates this profile. It does not admit private
data or qualify the local inference process as an OS privacy boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from . import container_scoring
from .container_scoring import ContainerRMSEScorer, vector_scorer_identity
from .execution_receipts import (
    CompositeScorerRegistration,
    CompositeConfirmationExecution,
    GuestCompositeScorerRegistration,
)
from .inference_evidence import archive_inference, verify_inference_archive
from .scoring import (
    CompositeConfirmationGrant,
    ConfirmationGrant,
    ConfirmationReceipt,
    ConfirmationService,
    PublicScore,
)


def validate_registration(registration, grant):
    if not isinstance(grant, CompositeConfirmationGrant) or (
        registration.digest,
        registration.inference_digest,
        registration.partition_digest,
        registration.outcome_digest,
    ) != (
        grant.scorer_digest,
        grant.inference.digest,
        grant.partition_digest,
        grant.outcome_digest,
    ):
        raise StoreError("composite registration differs from frozen grant")


def inner_grant(registration, grant, predictions):
    """A subordinate allocation of the original two-start reservation, never new work."""
    validate_registration(registration, grant)
    scorer = vector_scorer_identity(
        source_digest=registration.vector_source_digest,
        labels_digest=registration.labels_digest,
        predictions_digest=predictions.sha256,
        partition_digest=grant.partition_digest,
        outcome_digest=grant.outcome_digest,
        runtime_digest=registration.vector_runtime_digest,
    )
    resources = tuple(
        replace(r, limit=1)
        if r.name == "scientific_starts"
        else replace(r, limit=64)
        if r.name == "active_time"
        else r
        for r in grant.resources
    )
    return ConfirmationGrant(
        grant.suite_digest,
        grant.cell_digest,
        grant.partition_digest,
        scorer,
        grant.outcome_digest,
        grant.model_digest,
        grant.selection_digest,
        resources,
    )


@dataclass(frozen=True)
class CompositeStageTransition(Record):
    schema: Literal["utility-composite-stage-transition-v1"]
    grant_digest: str
    registration: CompositeScorerRegistration
    inference_archive: ArtifactRef
    inner_grant: ArtifactRef | None

    def _validate(self):
        from .contracts import sha256

        sha256(self.grant_digest)


def read_stage_transition(store, grant):
    """Verify the original public handoff without a scorer instance or execution."""
    transition = CompositeStageTransition.from_json(
        confined_file(store.root, f"composite-transitions/{grant.digest}.json").read_text()
    )
    if transition.grant_digest != grant.digest:
        raise StoreError("composite transition belongs to another grant")
    validate_registration(transition.registration, grant)
    archived = _archive(store, transition.registration, grant, transition.inference_archive)
    archive, receipt, _, _ = archived
    if receipt.status != "success":
        if transition.inner_grant is not None:
            raise StoreError("failed inference cannot authorize inner scoring")
    elif transition.inner_grant is None or ConfirmationGrant.from_json(
        read_bytes(store.root, transition.inner_grant).decode()
    ) != inner_grant(transition.registration, grant, archive.predictions):
        raise StoreError("composite transition changes the inner grant")
    return transition, archived


def _archive(store, registration, grant, ref):
    if isinstance(registration, GuestCompositeScorerRegistration):
        from .guest_archive import GuestDispatchEvidence
        from .guest_executor import GuestExecutorInitialization
        from .guest_receipts import GuestDispatchInferenceArchive, verify_guest_archive
        from .inference_execution import FrozenGuestInferenceJob
        from .guest_receipts import GuestLaunchIntent

        archive = GuestDispatchInferenceArchive.from_json(read_bytes(store.root, ref).decode())
        checked = verify_guest_archive(
            store.root,
            ref,
            grant,
            source_digest=store.spec.source_digest,
            lock_digest=store.spec.lock_digest,
            executor_digest=registration.executor_digest,
            runtime_digest=registration.inference_runtime_digest,
            publisher_digest=registration.inference_publisher_digest,
        )
        path = confined_file(store.root, f"guest-executor-inits/{grant.digest}.json")
        if path.stat().st_size > 4 * 1024 * 1024:
            raise StoreError("composite guest initialization exceeds bound")
        initialization = GuestExecutorInitialization.from_json(path.read_text())
        job = FrozenGuestInferenceJob.from_json(read_bytes(store.root, archive.job).decode())
        launch = GuestLaunchIntent.from_json(read_bytes(store.root, archive.launch).decode())
        proof = GuestDispatchEvidence.from_json(read_bytes(store.root, archive.dispatch).decode())
        original = initialization.registration
        if (
            initialization.suite_digest != store.spec.digest
            or initialization.owner.job != job
            or initialization.owner.launch != launch
            or initialization.owner.digest != proof.completion.owner_digest
            or original.digest != registration.executor_registration_digest
            or (
                original.executor_digest,
                original.runtime_digest,
                original.publisher_digest,
                original.policy_digest,
            )
            != (
                registration.executor_digest,
                registration.inference_runtime_digest,
                registration.inference_publisher_digest,
                registration.inference_policy_digest,
            )
        ):
            raise StoreError("composite guest archive differs from original facade registration")
        marker = confined_file(store.root, f"guest-executor-inits/{grant.digest}.complete.json")
        from autoengineering.campaign.serialization import unique_json

        if marker.stat().st_size > 65536 or unique_json(marker.read_text()) != {
            "initialization_digest": initialization.digest,
            "owner_digest": initialization.owner.digest,
        }:
            raise StoreError("composite guest lacks original completed initialization")
        return (
            archive,
            checked,
            checked.result,
            {
                "elapsed_seconds": checked.lifecycle_seconds,
                "container_starts": checked.container_starts,
            },
        )
    return verify_inference_archive(
        store.root,
        ref,
        grant,
        registration.executor_digest,
        store.spec.source_digest,
        store.spec.lock_digest,
    )


def _failure(status, outcome):
    return PublicScore(
        status,
        outcome.name,
        outcome.units,
        None,
        False if status == "scientific_infeasible" else None,
    )


def validate_composite_receipt(store, grant, receipt):
    evidence = receipt.composite
    if evidence is None:
        raise StoreError("composite scores require a verified two-stage execution receipt")
    registration = evidence.registration
    validate_registration(registration, grant)
    transition, _ = read_stage_transition(store, grant)
    if (transition.registration, transition.inference_archive, transition.inner_grant) != (
        registration,
        evidence.inference_archive,
        evidence.inner_grant,
    ):
        raise StoreError("composite receipt differs from original pre-scoring transition")
    archive, inference, _, _ = _archive(store, registration, grant, evidence.inference_archive)
    if inference.status != "success":
        if evidence.inner_grant is not None or receipt.score != _failure(
            inference.status, receipt.outcome_contract
        ):
            raise StoreError("failed inference cannot produce an inner score")
        return
    if evidence.inner_grant is None or evidence.inner_execution is None:
        raise StoreError("successful inference lacks the original inner scoring execution")
    expected = inner_grant(registration, grant, archive.predictions)
    actual = ConfirmationGrant.from_json(read_bytes(store.root, evidence.inner_grant).decode())
    if actual != expected:
        raise StoreError("inner scorer grant differs from parent/prediction transition")
    inner = evidence.inner_execution
    if (inner.grant_digest, inner.scorer_digest, inner.runtime_digest, inner.score_digest) != (
        actual.digest,
        actual.scorer_digest,
        registration.vector_runtime_digest,
        receipt.score.digest,
    ):
        raise StoreError("inner execution differs from the registered composite transition")


class CompositeRMSEScorer:
    """Fixed two-stage candidate; recovery never starts either stage or reads labels."""

    def __init__(
        self,
        executor,
        private_root,
        *,
        labels,
        runtime,
        inference,
        partition_digest,
        outcome_contract,
    ):
        self.executor, self.store = executor, executor.store
        self._check_executor()
        self.private_root = checked_directory(private_root)
        if any(
            self.private_root.is_relative_to(p) or p.is_relative_to(self.private_root)
            for p in (
                self.store.root,
                executor.source_root,
                executor.driver_root,
                executor.work_root,
            )
            if p is not None
        ):
            raise StoreError("composite labels must be separate from all inference/public scopes")
        if (
            labels.size_bytes > 1048576
            or outcome_contract.name != "rmse"
            or outcome_contract.direction != "minimize"
        ):
            raise ValueError("composite scorer requires bounded labels and minimized RMSE")
        self.labels, self.runtime = labels, runtime
        self.inference = inference
        self.partition_digest, self.outcome_contract = partition_digest, outcome_contract
        self.registration = self._registration()
        self.identity = self.registration.digest

    def _check_executor(self):
        from .guest_executor import GuestRoutingExecutor

        if isinstance(self.executor, GuestRoutingExecutor):
            raise StoreError("local composite scorer cannot admit a guest executor")

    def _registration(self):
        return CompositeScorerRegistration(
            "utility-composite-scorer-registration-v1",
            self.executor.identity,
            self.inference.digest,
            hashlib.sha256(Path(container_scoring.__file__).read_bytes()).hexdigest(),
            self.runtime.identity,
            self.labels.sha256,
            self.partition_digest,
            self.outcome_contract.digest,
            "unqualified-candidate",
        )

    def validate(self, grant, model=None):
        if self.registration != self._registration():
            raise StoreError("composite scorer registration changed")
        validate_registration(self.registration, grant)
        if model is not None and model.sha256 != grant.model_digest:
            raise StoreError("composite scorer model differs from frozen grant")

    def _path(self, grant):
        return self.store.root / "composite-transitions" / f"{grant.digest}.json"

    def _inner(self, grant, transition):
        archive, receipt, _, _ = _archive(
            self.store, self.registration, grant, transition.inference_archive
        )
        if receipt.status != "success":
            if transition.inner_grant is not None:
                raise StoreError("failed inference cannot authorize inner scoring")
            return receipt, None, None
        expected = inner_grant(self.registration, grant, archive.predictions)
        if (
            transition.inner_grant is None
            or ConfirmationGrant.from_json(
                read_bytes(self.store.root, transition.inner_grant).decode()
            )
            != expected
        ):
            raise StoreError("composite transition changes the inner grant")
        scorer = ContainerRMSEScorer(
            self.store.root,
            self.private_root,
            labels=self.labels,
            predictions=archive.predictions,
            partition_digest=self.partition_digest,
            outcome_contract=self.outcome_contract,
            runtime=self.runtime,
        )
        if scorer.identity != expected.scorer_digest:
            raise StoreError("inner scorer identity differs from published transition")
        return receipt, expected, scorer

    def _read_transition(self, grant):
        transition, _ = read_stage_transition(self.store, grant)
        if transition.registration != self.registration:
            raise StoreError("composite transition belongs to another grant/registration")
        return transition

    def _save_transition(self, grant):
        return self._publish_transition(grant, archive_inference(self.executor, grant))

    def _publish_transition(self, grant, archive_ref):
        archive, receipt, _, _ = _archive(self.store, self.registration, grant, archive_ref)
        inner = None
        if receipt.status == "success":
            child = inner_grant(self.registration, grant, archive.predictions)
            inner = put_bytes(
                self.store.root,
                child.to_json().encode(),
                name="inner-confirmation-grant.json",
                media_type="application/json",
                producer="trusted-composite-confirmation",
            )
        transition = CompositeStageTransition(
            "utility-composite-stage-transition-v1",
            grant.digest,
            self.registration,
            archive_ref,
            inner,
        )
        directory = self._path(grant).parent
        directory.mkdir(mode=0o700, exist_ok=True)
        checked_directory(directory)
        durable_write(self._path(grant), transition.to_json().encode())
        self.store.fault("composite_inference_committed")
        return transition

    def __call__(self, grant, model):
        self.validate(grant, model)
        self.executor.execute(grant)
        transition = self._save_transition(grant)
        receipt, child, scorer = self._inner(grant, transition)
        if scorer is None:
            return _failure(receipt.status, self.outcome_contract)
        if self.store.replay()["cancelled"]:
            raise StoreError("cancelled suite cannot start inner scoring")
        return scorer(child, model)

    def recover(self, grant, model):
        self.validate(grant, model)
        # If inference completed before transition publication, archive its original
        # proof. Never start an inner stage that had not completed before the loss.
        transition = (
            self._read_transition(grant)
            if self._path(grant).exists()
            else self._save_transition(grant)
        )
        receipt, child, scorer = self._inner(grant, transition)
        return (
            _failure(receipt.status, self.outcome_contract)
            if scorer is None
            else scorer.recover(child, model)
        )

    def public_execution(self, grant, model, score):
        self.validate(grant, model)
        transition = self._read_transition(grant)
        _, child, scorer = self._inner(grant, transition)
        execution = scorer.public_execution(child, model, score) if scorer is not None else None
        if scorer is not None and execution is None:
            raise StoreError("composite score lacks original inner execution evidence")
        return CompositeConfirmationExecution(
            "utility-composite-confirmation-execution-v1",
            grant.digest,
            score.digest,
            self.registration,
            transition.inference_archive,
            transition.inner_grant,
            execution,
        )


class CompositeConfirmationService(ConfirmationService):
    """Explicit application-owned candidate; the default vector service stays closed."""

    def _validate_profile(self, grant, operation):
        if (
            not isinstance(self.scorer, CompositeRMSEScorer)
            or self.scorer.store is not self.store
            or type(self.scorer.registration) is not CompositeScorerRegistration
        ):
            raise StoreError("local composite service requires its owned local fixed scorer")
        self.scorer.validate(grant)

    def _make_receipt(self, grant, model, access, score, *, measurement=None, recovery=None):
        try:
            receipt = ConfirmationReceipt(
                grant.digest,
                access,
                score,
                self.outcome_contract,
                measurement,
                recovery,
                composite=self.scorer.public_execution(grant, model, score),
            )
            validate_composite_receipt(self.store, grant, receipt)
            return receipt
        except Exception:
            raise StoreError(
                "composite execution evidence unverified; access and charges retained"
            ) from None


class GuestCompositeRMSEScorer(CompositeRMSEScorer):
    """Explicit guest candidate; neither this registration nor fixtures qualify privacy."""

    def _check_executor(self):
        from .guest_executor import GuestRoutingExecutor

        if not isinstance(self.executor, GuestRoutingExecutor):
            raise StoreError("guest composite scorer requires its fixed guest facade")

    def _registration(self):
        original = self.executor.registration
        value = super()._registration().to_dict()
        value.update(
            schema="utility-composite-scorer-registration-v2",
            executor_registration_digest=original.digest,
            inference_runtime_digest=original.runtime_digest,
            inference_publisher_digest=original.publisher_digest,
            inference_policy_digest=original.policy_digest,
        )
        return GuestCompositeScorerRegistration.from_dict(value)

    def validate_live_registration(self):
        from .guest_archive import publisher_identity

        if self.executor._recovery_only:
            raise StoreError("recovery-only guest composite cannot execute")
        if (
            self.executor.registration != self.executor._registration()
            or self.executor.publisher_digest != publisher_identity()
        ):
            raise StoreError("guest composite facade/publisher registration changed")
        self.executor.api._identity()

    def _save_transition(self, grant):
        # Recovery can complete only original saved inference/publication. It can
        # never create, start or attach a missing inference stage.
        self.executor.recover(grant)
        return self._publish_transition(grant, self.executor.archive(grant))


class GuestCompositeConfirmationService(CompositeConfirmationService):
    """Application-owned candidate, separate from vector and local composite services."""

    def _validate_profile(self, grant, operation):
        if (
            not isinstance(self.scorer, GuestCompositeRMSEScorer)
            or self.scorer.store is not self.store
        ):
            raise StoreError("guest composite service requires its owned guest fixed scorer")
        self.scorer.validate(grant)
        if operation == "execute":
            self.scorer.validate_live_registration()
