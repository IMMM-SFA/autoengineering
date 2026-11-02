"""Confirmation access/score accounting for application-owned trusted scorers.

This module does not admit a private data path or provide process isolation.
Scorers receive only a selected-model reference and immutable grant identities.
Custodians must qualify their own scorer boundary before real confirmation use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import time

from autoengineering.campaign.artifacts import read_bytes, put_bytes, reference
from autoengineering.campaign.serialization import Record
from autoengineering.campaign.store import StoreError
from .contracts import ResourceCap, sha256
from .confirmation import read_manifest, read_selected_state
from .outcomes import OutcomeSpec
from .execution_receipts import ConfirmationContainerExecution, CompositeConfirmationExecution
from .inference_contracts import FrozenRoutingInference


@dataclass(frozen=True)
class ConfirmationGrant(Record):
    suite_digest: str
    cell_digest: str
    partition_digest: str
    scorer_digest: str
    outcome_digest: str
    model_digest: str
    selection_digest: str
    resources: tuple[ResourceCap, ...]

    @classmethod
    def from_dict(cls, value):
        from collections.abc import Mapping

        if (
            cls is ConfirmationGrant
            and isinstance(value, Mapping)
            and value.get("schema") == "utility-confirmation-grant-v2"
        ):
            return CompositeConfirmationGrant.from_dict(value)
        return super().from_dict(value)

    @property
    def scientific_starts(self):
        return 1

    def _validate(self):
        for value in (
            self.suite_digest,
            self.cell_digest,
            self.partition_digest,
            self.scorer_digest,
            self.outcome_digest,
            self.model_digest,
            self.selection_digest,
        ):
            sha256(value)
        if not self.resources or len({r.name for r in self.resources}) != len(self.resources):
            raise ValueError("confirmation grant needs unique bounded resources")
        if not any(
            r.name == "scientific_starts"
            and r.units == "count"
            and r.limit == self.scientific_starts
            and r.enforcement == "reservation"
            for r in self.resources
        ):
            if self.scientific_starts == 1:
                raise ValueError("confirmation requires one explicitly reserved scoring start")
            raise ValueError("composite confirmation requires two reserved scientific starts")
        if any(
            r.limit > 0 and r.name in ("host_invocations", "training_starts")
            for r in self.resources
        ):
            raise ValueError("confirmation cannot invoke agents or training")


@dataclass(frozen=True)
class CompositeConfirmationGrant(ConfirmationGrant):
    """Two-stage contract. Current vector-only services refuse its execution."""

    schema: Literal["utility-confirmation-grant-v2"]
    inference: FrozenRoutingInference

    @property
    def scientific_starts(self):
        return 2

    def _validate(self):
        super()._validate()
        active = next((r for r in self.resources if r.name == "active_time"), None)
        if (
            active is None
            or active.units != "s"
            or active.enforcement != "reservation"
            or active.limit < self.inference.minimum_reserved_seconds
        ):
            raise ValueError("composite confirmation lacks reserved inference/scoring time")


@dataclass(frozen=True)
class PublicScore(Record):
    status: Literal[
        "success",
        "scientific_infeasible",
        "model_failure",
        "timeout",
        "infrastructure_failure",
        "insufficient_data",
    ]
    outcome: str
    units: str
    value: float | None
    feasible: bool | None

    def _validate(self):
        if self.status == "success" and (self.value is None or self.feasible is None):
            raise ValueError("successful confirmation needs finite outcome and feasibility")
        if self.status != "success" and self.value is not None:
            raise ValueError("failed confirmation cannot supply a penalty objective")


def _read(root, identity, name, kind):
    sha256(identity)
    ref = reference(
        root, f"artifacts/{identity}/{name}", media_type="application/json", producer="reader"
    )
    if ref.sha256 != identity:
        raise StoreError("confirmation artifact identity changed")
    return kind.from_json(read_bytes(root, ref).decode())


def validate_grant(store, grant, frozen):
    if grant.suite_digest != store.spec.digest or grant.selection_digest != frozen:
        raise StoreError("confirmation grant is stale")
    cell = next((c for c in store.spec.cells if c.digest == grant.cell_digest), None)
    if cell is None:
        raise StoreError("confirmation cell is absent")
    task = next(t for t in store.spec.tasks if t.task_id == cell.task_id)
    if (grant.partition_digest, grant.outcome_digest) != (
        task.partition_digest,
        task.scoring_outcome_identity,
    ):
        raise StoreError("confirmation data/outcome identity differs")
    selected = next(
        c for c in read_manifest(store.root, frozen).cells if c.cell_digest == cell.digest
    )
    if selected.status != "selected" or selected.model.sha256 != grant.model_digest:
        raise StoreError("confirmation model is not the sealed selection")
    read_bytes(store.root, selected.model)
    bound = read_selected_state(store.root, selected.selected_state)
    if isinstance(grant, CompositeConfirmationGrant):
        if (
            task.family != "hydrology"
            or "protected_frozen_routing_score" not in task.required_capabilities
        ):
            raise StoreError(
                "composite confirmation requires a declared protected routing capability"
            )
        grant.inference.validate_selection(store.root, selected.selected_state, bound)
    if store.spec.baseline_reuse is not None:
        from .baseline_execution import validate_source_selection

        validate_source_selection(
            store, grant.cell_digest, read_manifest(store.root, frozen), grant.scorer_digest
        )
    return selected


def validate_access(store, event, frozen, allocation):
    grant = _read(store.root, event.result_digest, "confirmation-grant.json", ConfirmationGrant)
    validate_grant(store, grant, frozen)
    if grant.resources != allocation.resources:
        raise StoreError("confirmation access resources differ from charged reservation")
    if grant.cell_digest != event.cell_digest or grant.digest != event.child_digest:
        raise StoreError("access intent differs from reserved confirmation grant")


@dataclass(frozen=True)
class ConfirmationMeasurement(Record):
    schema: Literal["utility-confirmation-callback-measurement-v1"]
    grant_digest: str
    scorer_digest: str
    score_digest: str
    elapsed_seconds: float

    def _validate(self):
        for value in (self.grant_digest, self.scorer_digest, self.score_digest):
            sha256(value)
        if self.elapsed_seconds < 0:
            raise ValueError("confirmation callback duration must be nonnegative")


@dataclass(frozen=True)
class ConfirmationRecovery(Record):
    schema: Literal["utility-confirmation-recovery-v1"]
    attempt_id: str
    grant_digest: str
    access_digest: str
    scorer_digest: str
    score_digest: str

    def _validate(self):
        from .contracts import identifier

        identifier(self.attempt_id)
        for value in (self.grant_digest, self.access_digest, self.scorer_digest, self.score_digest):
            sha256(value)


@dataclass(frozen=True)
class ConfirmationReceipt(Record):
    grant_digest: str
    access_digest: str
    score: PublicScore
    outcome_contract: OutcomeSpec
    measurement: ConfirmationMeasurement | None = None
    recovery: ConfirmationRecovery | None = None
    execution: ConfirmationContainerExecution | None = None
    composite: CompositeConfirmationExecution | None = None

    def to_dict(self):
        value = super().to_dict()
        if self.measurement is None:
            value.pop("measurement")
        if self.recovery is None:
            value.pop("recovery")
        if self.execution is None:
            value.pop("execution")
        if self.composite is None:
            value.pop("composite")
        return value

    def _validate(self):
        sha256(self.grant_digest)
        sha256(self.access_digest)
        if (self.score.outcome, self.score.units) != (
            self.outcome_contract.name,
            self.outcome_contract.units,
        ):
            raise ValueError("public score semantics differ from registered outcome")
        if self.measurement is not None and (
            self.measurement.grant_digest != self.grant_digest
            or self.measurement.score_digest != self.score.digest
        ):
            raise ValueError("confirmation measurement differs from grant or score")
        if self.recovery is not None:
            if self.measurement is not None:
                raise ValueError("recovery cannot invent an original callback measurement")
            if (
                self.recovery.grant_digest,
                self.recovery.access_digest,
                self.recovery.score_digest,
            ) != (self.grant_digest, self.access_digest, self.score.digest):
                raise ValueError("confirmation recovery differs from grant, access or score")
        if self.execution is not None and (
            self.execution.grant_digest != self.grant_digest
            or self.execution.score_digest != self.score.digest
        ):
            raise ValueError("confirmation execution differs from grant or score")
        if self.composite is not None:
            if self.execution is not None or (
                self.composite.grant_digest,
                self.composite.score_digest,
            ) != (self.grant_digest, self.score.digest):
                raise ValueError("composite execution differs from grant or score")


def validate_score(store, event, access, frozen):
    receipt = _read(store.root, event.result_digest, "confirmation-score.json", ConfirmationReceipt)
    grant = _read(store.root, access, "confirmation-grant.json", ConfirmationGrant)
    validate_grant(store, grant, frozen)
    if isinstance(grant, CompositeConfirmationGrant):
        from .composite_scoring import validate_composite_receipt

        validate_composite_receipt(store, grant, receipt)
    elif receipt.composite is not None:
        raise StoreError("vector grant cannot carry composite execution")
    if receipt.measurement is not None and receipt.measurement.scorer_digest != grant.scorer_digest:
        raise StoreError("confirmation measurement belongs to another scorer")
    if receipt.recovery is not None and (
        receipt.recovery.scorer_digest != grant.scorer_digest
        or receipt.recovery.attempt_id != event.attempt_id
    ):
        raise StoreError("confirmation recovery belongs to another scorer or attempt")
    if receipt.execution is not None and receipt.execution.scorer_digest != grant.scorer_digest:
        raise StoreError("confirmation execution belongs to another scorer")
    if receipt.outcome_contract.digest != grant.outcome_digest:
        raise StoreError("public outcome differs from frozen task")
    if (receipt.grant_digest, receipt.access_digest) != (grant.digest, access):
        raise StoreError("confirmation score differs from access intent")


class ConfirmationService:
    """One attempt per selected cell, with explicit application-owned scorer pins."""

    def __init__(self, store, scorer, *, scorer_digest, outcome_contract: OutcomeSpec):
        sha256(scorer_digest)
        self.store, self.scorer, self.scorer_digest = store, scorer, scorer_digest
        self.outcome_contract = outcome_contract

    def confirm(self, grant: ConfirmationGrant):
        with self.store.writer():
            state = self.store.replay()
            selected = validate_grant(self.store, grant, state["frozen"])
            if self.outcome_contract.digest != grant.outcome_digest:
                raise StoreError("confirmation outcome registration differs from task")
            if grant.scorer_digest != self.scorer_digest:
                raise StoreError("unregistered confirmation scorer identity")
            self._validate_profile(grant, "execute")
            attempt = "confirmation-" + grant.cell_digest[:48]
            allocation = state["attempts"].get(attempt)
            if allocation is not None:
                if attempt in state["confirmation_scores"]:
                    return self._acknowledge(grant, attempt, state["confirmation_scores"][attempt])
                raise StoreError("confirmation attempt is uncertain; automatic retry refused")
            arguments = {
                "cell_digest": grant.cell_digest,
                "attempt_id": attempt,
                "child_digest": grant.digest,
                "phase": "confirmation",
            }
            self.store.append(
                request_id=attempt + "-reserve",
                operation="reserve",
                resources=grant.resources,
                **arguments,
            )
            self.store.append(request_id=attempt + "-start", operation="start", **arguments)
            access = put_bytes(
                self.store.root,
                grant.to_json().encode(),
                name="confirmation-grant.json",
                media_type="application/json",
                producer="trusted-confirmation",
            )
            self.store.append(
                request_id=attempt + "-access",
                operation="confirmation_access",
                result_digest=access.sha256,
                **arguments,
            )
            self.store.fault("confirmation_access_committed")
            began = time.monotonic()
            try:
                score = self.scorer(grant, selected.model)
                if not isinstance(score, PublicScore):
                    raise ValueError("invalid public score")
                measurement = ConfirmationMeasurement(
                    "utility-confirmation-callback-measurement-v1",
                    grant.digest,
                    self.scorer_digest,
                    score.digest,
                    time.monotonic() - began,
                )
            except Exception:
                raise StoreError(
                    "confirmation scoring uncertain; access and charges retained"
                ) from None
            receipt = self._make_receipt(
                grant,
                selected.model,
                access.sha256,
                score,
                measurement=measurement,
            )
            ref = put_bytes(
                self.store.root,
                receipt.to_json().encode(),
                name="confirmation-score.json",
                media_type="application/json",
                producer="trusted-confirmation",
            )
            self.store.fault("confirmation_score_created")
            self.store.append(
                request_id=attempt + "-score",
                operation="confirmation_score",
                result_digest=ref.sha256,
                **arguments,
            )
            self.store.fault("confirmation_score_committed")
            return self._acknowledge(grant, attempt, ref.sha256)

    def recover(self, grant: ConfirmationGrant):
        """Explicitly publish an original saved result, without new scoring.

        The registered scorer must provide recover(grant, model). That trusted
        method must verify original completion and never restart a worker or
        open labels. Missing evidence leaves the original attempt charged.
        """
        with self.store.writer():
            state = self.store.replay()
            selected = validate_grant(self.store, grant, state["frozen"])
            if self.outcome_contract.digest != grant.outcome_digest:
                raise StoreError("confirmation outcome registration differs from task")
            if grant.scorer_digest != self.scorer_digest:
                raise StoreError("unregistered confirmation scorer identity")
            self._validate_profile(grant, "recover")
            attempt = "confirmation-" + grant.cell_digest[:48]
            allocated = state["attempts"].get(attempt)
            if allocated is None:
                raise StoreError("confirmation recovery requires an original charged attempt")
            allocation, status = allocated
            if (
                allocation.phase,
                allocation.cell_digest,
                allocation.child_digest,
                allocation.resources,
            ) != ("confirmation", grant.cell_digest, grant.digest, grant.resources):
                raise StoreError("confirmation recovery differs from original reservation")
            if attempt in state["confirmation_scores"]:
                return self._acknowledge(grant, attempt, state["confirmation_scores"][attempt])
            access = state["confirmation_accesses"].get(attempt)
            if status != "started" or access is None:
                raise StoreError(
                    "confirmation recovery requires the original committed access intent"
                )
            original = _read(self.store.root, access, "confirmation-grant.json", ConfirmationGrant)
            if original != grant:
                raise StoreError("confirmation recovery access differs from the original grant")
            recover = getattr(self.scorer, "recover", None)
            if not callable(recover):
                raise StoreError("registered confirmation scorer has no original-result recovery")
            try:
                score = recover(grant, selected.model)
                if not isinstance(score, PublicScore):
                    raise ValueError("invalid recovered public score")
            except Exception:
                raise StoreError(
                    "original confirmation result remains unverified; access and charges retained"
                ) from None
            recovery = ConfirmationRecovery(
                "utility-confirmation-recovery-v1",
                attempt,
                grant.digest,
                access,
                self.scorer_digest,
                score.digest,
            )
            receipt = self._make_receipt(
                grant,
                selected.model,
                access,
                score,
                recovery=recovery,
            )
            ref = put_bytes(
                self.store.root,
                receipt.to_json().encode(),
                name="confirmation-score.json",
                media_type="application/json",
                producer="trusted-confirmation-recovery",
            )
            self.store.fault("confirmation_recovery_score_created")
            self.store.append(
                request_id=attempt + "-score",
                operation="confirmation_score",
                cell_digest=grant.cell_digest,
                attempt_id=attempt,
                child_digest=grant.digest,
                phase="confirmation",
                result_digest=ref.sha256,
            )
            self.store.fault("confirmation_recovery_score_committed")
            return self._acknowledge(grant, attempt, ref.sha256)

    def _validate_profile(self, grant, operation):
        if isinstance(grant, CompositeConfirmationGrant):
            raise StoreError(f"vector-only service cannot {operation} composite confirmation")

    def _make_receipt(self, grant, model, access, score, *, measurement=None, recovery=None):
        return ConfirmationReceipt(
            grant.digest,
            access,
            score,
            self.outcome_contract,
            measurement,
            recovery,
            execution=self._public_execution(grant, model, score),
        )

    def _public_execution(self, grant, model, score):
        try:
            export = getattr(self.scorer, "public_execution", None)
            evidence = export(grant, model, score) if callable(export) else None
            if evidence is not None:
                if not isinstance(evidence, ConfirmationContainerExecution):
                    raise ValueError("invalid public execution record")
                if (evidence.grant_digest, evidence.scorer_digest, evidence.score_digest) != (
                    grant.digest,
                    self.scorer_digest,
                    score.digest,
                ):
                    raise ValueError("foreign public execution record")
            return evidence
        except Exception:
            raise StoreError(
                "confirmation execution evidence unverified; access and charges retained"
            ) from None

    def _acknowledge(self, grant, attempt, identity):
        receipt = _read(self.store.root, identity, "confirmation-score.json", ConfirmationReceipt)
        if receipt.grant_digest != grant.digest:
            raise StoreError("cannot resume confirmation under a changed grant")
        self.store.append(
            request_id=attempt + "-finish",
            operation="finish",
            cell_digest=grant.cell_digest,
            attempt_id=attempt,
            child_digest=grant.digest,
            phase="confirmation",
            result_digest=identity,
        )
        return receipt


def read_receipt(root, identity):
    """Read a hash-verified public confirmation receipt without invoking its scorer."""
    return _read(root, identity, "confirmation-score.json", ConfirmationReceipt)
