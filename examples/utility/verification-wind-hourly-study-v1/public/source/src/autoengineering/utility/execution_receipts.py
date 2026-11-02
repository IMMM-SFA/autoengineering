"""Public metadata from a registered trusted scorer, with no private paths or arrays.

Offline validation checks bindings and record integrity. It does not contact a
daemon or independently attest the private producer's execution claims.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Literal

from autoengineering.campaign.serialization import Record
from autoengineering.campaign.records import ArtifactRef
from .contracts import sha256


@dataclass(frozen=True)
class ConfirmationContainerExecution(Record):
    schema: Literal["utility-confirmation-container-execution-v1"]
    grant_digest: str
    scorer_digest: str
    score_digest: str
    runtime_digest: str
    container_id: str
    nonce: str
    image_id: str
    runtime_source_digest: str
    wrapper_source_digest: str
    worker_source_digest: str
    start_receipt_digest: str
    stop_receipt_digest: str
    cleanup_receipt_digest: str
    container_starts: Literal[1]
    scoring_process_starts: Literal[1]
    lifecycle_seconds: float | None = None

    def _validate(self):
        for value in (
            self.grant_digest,
            self.scorer_digest,
            self.score_digest,
            self.runtime_digest,
            self.container_id,
            self.runtime_source_digest,
            self.wrapper_source_digest,
            self.worker_source_digest,
            self.start_receipt_digest,
            self.stop_receipt_digest,
            self.cleanup_receipt_digest,
        ):
            sha256(value)
        if not re.fullmatch(r"[0-9a-f]{32}", self.nonce):
            raise ValueError("container execution needs its original nonce")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", self.image_id):
            raise ValueError("container execution needs a pinned image")
        if self.lifecycle_seconds is not None and self.lifecycle_seconds < 0:
            raise ValueError("container lifecycle duration must be nonnegative")


@dataclass(frozen=True)
class CompositeScorerRegistration(Record):
    """Public metadata pins, never private paths or a runtime qualification claim."""

    schema: Literal["utility-composite-scorer-registration-v1"]
    executor_digest: str
    inference_digest: str
    vector_source_digest: str
    vector_runtime_digest: str
    labels_digest: str
    partition_digest: str
    outcome_digest: str
    boundary: Literal["unqualified-candidate"]

    def _validate(self):
        for name, value in self.to_dict().items():
            if name.endswith("_digest"):
                sha256(value)

    @classmethod
    def from_dict(cls, value):
        if (
            cls is CompositeScorerRegistration
            and isinstance(value, Mapping)
            and value.get("schema") == ("utility-composite-scorer-registration-v2")
        ):
            return GuestCompositeScorerRegistration.from_dict(value)
        return super().from_dict(value)


@dataclass(frozen=True)
class GuestCompositeScorerRegistration(CompositeScorerRegistration):
    schema: Literal["utility-composite-scorer-registration-v2"]
    executor_registration_digest: str
    inference_runtime_digest: str
    inference_publisher_digest: str
    inference_policy_digest: str


@dataclass(frozen=True)
class CompositeConfirmationExecution(Record):
    schema: Literal["utility-composite-confirmation-execution-v1"]
    grant_digest: str
    score_digest: str
    registration: CompositeScorerRegistration
    inference_archive: ArtifactRef
    inner_grant: ArtifactRef | None
    inner_execution: ConfirmationContainerExecution | None

    def _validate(self):
        sha256(self.grant_digest)
        sha256(self.score_digest)
        if (self.inner_grant is None) != (self.inner_execution is None):
            raise ValueError("composite score needs both inner grant and execution")
        if (
            self.inner_execution is not None
            and self.inner_execution.score_digest != self.score_digest
        ):
            raise ValueError("composite score differs from inner execution")
