"""Public metadata from a registered trusted scorer, with no private paths or arrays.

Offline validation checks bindings and record integrity. It does not contact a
daemon or independently attest the private producer's execution claims.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from autoengineering.campaign.serialization import Record
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
