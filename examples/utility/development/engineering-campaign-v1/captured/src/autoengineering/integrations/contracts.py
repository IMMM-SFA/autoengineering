"""Immutable integration identity and external synchronization evidence.

These records describe evidence. They do not authorize evaluation or make an
external framework's trial database an authoritative scientific ledger.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from autoengineering.campaign.records import ArtifactRef, identifier, sha256, unique
from autoengineering.campaign.serialization import Record


@dataclass(frozen=True)
class IntegrationSpec(Record):
    schema_version: Literal[1]
    framework: str
    framework_version: str
    implementation_id: str
    mode: Literal["model", "policy"]
    configuration_digest: str
    environment_digest: str
    source_digest: str
    capabilities: tuple[str, ...]
    seed: int
    checkpoint_format: str

    def _validate(self):
        identifier(self.framework)
        identifier(self.implementation_id)
        for value in (self.configuration_digest, self.environment_digest, self.source_digest):
            sha256(value)
        unique(self.capabilities, "capability")
        for value in self.capabilities:
            identifier(value)
        if self.seed < 0:
            raise ValueError("seed cannot be negative")

    def require_compatible(self, other: IntegrationSpec) -> None:
        """Reject resume after any integration identity change."""
        if self != other:
            raise ValueError("integration identity changed; create a new study")


@dataclass(frozen=True)
class ExternalTrialLink(Record):
    schema_version: Literal[1]
    integration_digest: str
    campaign_id: str
    study_id: str
    action_id: str
    external_experiment_id: str
    external_trial_id: str | None
    proposal_digest: str | None
    attempt_ids: tuple[str, ...]
    observation_digest: str | None
    ledger_prefix_digest: str
    checkpoint: ArtifactRef | None
    synchronization: Literal[
        "ask_intent", "proposal_saved", "tell_intent", "synchronized", "reconciliation_required"
    ]

    def _validate(self):
        for value in (self.integration_digest, self.ledger_prefix_digest):
            sha256(value)
        for value in (self.proposal_digest, self.observation_digest):
            if value is not None:
                sha256(value)
        for value in (self.campaign_id, self.study_id, self.action_id, *self.attempt_ids):
            identifier(value)
        unique(self.attempt_ids, "attempt ID")
        if (self.external_trial_id is None) != (self.proposal_digest is None):
            raise ValueError("external trial and proposal must be saved together")
        if self.synchronization == "ask_intent":
            if self.external_trial_id is not None or self.observation_digest or self.attempt_ids:
                raise ValueError("ask intent cannot contain a proposal or evaluation")
        if self.synchronization in ("proposal_saved", "tell_intent", "synchronized"):
            if self.external_trial_id is None or self.checkpoint is None:
                raise ValueError("saved proposal requires external trial and checkpoint evidence")
        if self.synchronization == "proposal_saved" and self.observation_digest is not None:
            raise ValueError("result requires a tell intent")
        if self.synchronization in ("tell_intent", "synchronized"):
            if self.observation_digest is None or not self.attempt_ids:
                raise ValueError("tell requires committed observation and physical attempt links")


@dataclass(frozen=True)
class IntegrationReceipt(Record):
    schema_version: Literal[1]
    integration_digest: str
    platform: str
    direct_reference: tuple[ArtifactRef, ...]
    tolerance_definition: ArtifactRef
    capability_checks: tuple[str, ...]
    limitations: tuple[str, ...]
    qualification: Literal["verified", "failed", "blocked", "not_attempted"]

    def _validate(self):
        sha256(self.integration_digest)
        unique(self.capability_checks, "capability check")
        if self.qualification == "verified" and (
            not self.direct_reference or not self.capability_checks
        ):
            raise ValueError("verified integration requires direct evidence and capability checks")


@dataclass(frozen=True)
class CommittedTrialLink(Record):
    """A committed policy projection, with actual campaign attempts when available.

    Standalone optimization records evaluator dispatches through its action ledger.
    It does not manufacture campaign physical-attempt identifiers. Interrupted
    campaign actions may also have no physical start.
    """

    schema_version: Literal[1]
    integration_digest: str
    campaign_id: str | None
    study_id: str
    action_id: str
    external_experiment_id: str
    external_trial_id: str
    proposal_digest: str
    observation_digest: str
    ledger_prefix_digest: str
    attempt_ids: tuple[str, ...]
    result_status: Literal[
        "success", "scientific_infeasible", "model_failure", "timeout", "infrastructure_failure"
    ]
    projected_objective: float | None
    synchronization: Literal["tell_intent", "synchronized"]

    def _validate(self):
        for value in (self.integration_digest, self.proposal_digest,
                      self.observation_digest, self.ledger_prefix_digest):
            sha256(value)
        for value in (self.study_id, self.action_id, self.external_experiment_id,
                      self.external_trial_id, *self.attempt_ids):
            identifier(value)
        unique(self.attempt_ids, "attempt ID")
        if self.campaign_id is not None:
            identifier(self.campaign_id)
            if not self.attempt_ids and self.result_status != "infrastructure_failure":
                raise ValueError("campaign result requires existing physical attempt links")
        elif self.attempt_ids:
            raise ValueError("standalone results cannot invent campaign attempts")
        if self.result_status != "success" and self.projected_objective is not None:
            raise ValueError("failed results cannot supply an objective")
