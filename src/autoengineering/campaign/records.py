"""Public scientific, execution, and decision records for campaign version 1."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePosixPath
import re
from typing import Literal

from .serialization import Record

Scalar = str | bool | int | float | None
ExecutionStatus = Literal[
    "success", "scientific_infeasible", "model_failure", "timeout", "infrastructure_failure"
]
Outcome = Literal[
    "accepted_candidate",
    "retain_baseline",
    "no_suitable_intervention",
    "no_eligible_model",
    "insufficient_data",
    "invalid_task",
    "budget_exhausted",
    "cancelled",
    "failed_execution",
]


def identifier(value: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value):
        raise ValueError("identifier must contain only letters, digits, underscore, dot, or dash")


def sha256(value: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("expected lowercase SHA-256")


def relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ("", ".", "..") for part in value.split("/")):
        raise ValueError("path must be a confined relative path")
    if "\\" in value or "\x00" in value:
        raise ValueError("invalid path")


def unique(values, label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"duplicate {label}")


@dataclass(frozen=True)
class ArtifactRef(Record):
    path: str
    sha256: str
    size_bytes: int
    media_type: str
    producer: str
    metadata: Mapping[str, Scalar]

    def _validate(self):
        relative_path(self.path)
        sha256(self.sha256)
        if self.size_bytes < 0:
            raise ValueError("artifact size cannot be negative")


@dataclass(frozen=True)
class TimeContract(Record):
    dates: tuple[str, ...]
    semantics: Literal["instantaneous", "interval_mean", "interval_total"]
    timestep: Literal["P1D"]
    calendar: Literal["proleptic_gregorian"]
    timestamp: Literal["start", "end"]
    warmup_mask: tuple[bool, ...]
    scoring_mask: tuple[bool, ...]

    def _validate(self):
        parsed = [date.fromisoformat(value) for value in self.dates]
        if not parsed or any(value.isoformat() != raw for value, raw in zip(parsed, self.dates)):
            raise ValueError("time axis requires canonical ISO dates")
        if any((right - left).days != 1 for left, right in zip(parsed, parsed[1:])):
            raise ValueError("time axis must be consecutive daily dates")
        if len(self.warmup_mask) != len(parsed) or len(self.scoring_mask) != len(parsed):
            raise ValueError("time masks must match dates")
        if any(a and b for a, b in zip(self.warmup_mask, self.scoring_mask)):
            raise ValueError("warmup and scoring masks overlap")


@dataclass(frozen=True)
class SubdailyTimeContract(Record):
    """Version 2 UTC five-minute sample axis, with explicit state resets at gaps.

    Instantaneous power samples remain power. This contract does not turn them
    into interval energy or supply missing observations by interpolation.
    """

    schema_version: Literal["2.0"]
    dates: tuple[str, ...]
    semantics: Literal["instantaneous"]
    timestep: Literal["PT5M"]
    calendar: Literal["proleptic_gregorian"]
    timestamp: Literal["instant"]
    timezone: Literal["UTC"]
    gap_policy: Literal["restart_state"]
    warmup_mask: tuple[bool, ...]
    scoring_mask: tuple[bool, ...]

    def _validate(self):
        parsed = [datetime.fromisoformat(value) for value in self.dates]
        if not parsed:
            raise ValueError("subdaily time axis cannot be empty")
        for raw, value in zip(self.dates, parsed):
            if value.tzinfo is None or value.utcoffset() != timedelta(0):
                raise ValueError("subdaily timestamps require UTC")
            canonical = value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if raw != canonical or value.second != 0 or value.minute % 5:
                raise ValueError("subdaily timestamps require canonical UTC five-minute samples")
        if any((right - left).total_seconds() < 300 for left, right in zip(parsed, parsed[1:])):
            raise ValueError("subdaily timestamps must increase without duplicates")
        if len(self.warmup_mask) != len(parsed) or len(self.scoring_mask) != len(parsed):
            raise ValueError("subdaily masks must match timestamps")
        if any(a and b for a, b in zip(self.warmup_mask, self.scoring_mask)):
            raise ValueError("subdaily warmup and scoring masks overlap")


@dataclass(frozen=True)
class PortContract(Record):
    name: str
    dimensions: tuple[str, ...]
    units: str
    dtype_family: Literal["float", "integer", "numeric"]
    coordinates: tuple[str, ...]
    grid_id: str
    coordinate_digest: str
    time: TimeContract | SubdailyTimeContract | None
    missing: Literal["forbid"] = "forbid"

    def _validate(self):
        identifier(self.name)
        if self.units.lower() in ("unknown", "any") or self.grid_id.lower() == "unknown":
            raise ValueError("required port metadata cannot be unknown")
        sha256(self.coordinate_digest)
        if self.dimensions not in ((), ("time",)):
            raise ValueError("only scalar and one-dimensional daily series are supported")
        if bool(self.dimensions) != (self.time is not None):
            raise ValueError("time dimension requires a time contract")
        unique(self.coordinates, "coordinates")


@dataclass(frozen=True)
class DataContract(Record):
    id: str
    artifact: ArtifactRef
    ports: tuple[PortContract, ...]
    role: Literal["forcing", "fitting", "comparison", "confirmation", "development_replay"]
    prior_exposure: Literal["exposed", "unexposed", "unknown"]

    def _validate(self):
        identifier(self.id)
        if not self.ports:
            raise ValueError("data contract needs ports")
        unique([port.name for port in self.ports], "data port")


@dataclass(frozen=True)
class ModelSnapshot(Record):
    graph_digest: str
    implementations: Mapping[str, str]
    source_bundle: tuple[ArtifactRef, ...]
    dependency_bundle: str
    inputs: tuple[PortContract, ...]
    outputs: tuple[PortContract, ...]

    def _validate(self):
        sha256(self.graph_digest)
        sha256(self.dependency_bundle)
        if not self.implementations or not self.source_bundle or not self.outputs:
            raise ValueError("model snapshot must declare implementations, sources and outputs")
        for ports in (self.inputs, self.outputs):
            unique([port.name for port in ports], "model port")
        unique([source.path for source in self.source_bundle], "source path")
        times = [port.time for port in (*self.inputs, *self.outputs) if port.time is not None]
        if times and any(time.dates != times[0].dates for time in times):
            raise ValueError("model daily ports must have aligned dates")


@dataclass(frozen=True)
class CandidateProposal(Record):
    id: str
    target: str
    implementation_id: str
    hypothesis: str
    sources: tuple[str, ...]
    expected_benefit: str
    cost_estimate: float | None
    eligibility_evidence: tuple[ArtifactRef, ...]

    def _validate(self):
        for value in (self.id, self.target, self.implementation_id):
            identifier(value)
        if self.cost_estimate is not None and self.cost_estimate < 0:
            raise ValueError("cost estimate cannot be negative")


@dataclass(frozen=True)
class CandidateSnapshot(Record):
    proposal: CandidateProposal
    model: ModelSnapshot
    adapter_id: str
    parameter_space_digest: str
    fixed_parameters: Mapping[str, Scalar]

    def _validate(self):
        identifier(self.adapter_id)
        sha256(self.parameter_space_digest)
        if self.model.implementations.get(self.proposal.target) != self.proposal.implementation_id:
            raise ValueError("snapshot implementation differs from admitted proposal")


@dataclass(frozen=True)
class CheckResult(Record):
    name: str
    version: str
    status: Literal["pass", "fail", "unavailable", "error"]
    required: bool
    scope: str
    value: float | None
    threshold: float | None
    reason: str
    evidence: tuple[ArtifactRef, ...]


@dataclass(frozen=True)
class EvaluationRecord(Record):
    id: str
    model_id: str
    configuration: Mapping[str, Scalar]
    status: ExecutionStatus
    metrics: Mapping[str, float | None]
    checks: tuple[CheckResult, ...]
    outputs: tuple[ArtifactRef, ...]
    split_id: str
    attempt_id: str
    elapsed_seconds: float
    provenance: Mapping[str, str]

    def _validate(self):
        for value in (self.id, self.attempt_id):
            identifier(value)
        if self.elapsed_seconds < 0:
            raise ValueError("elapsed time cannot be negative")
        unique([check.name for check in self.checks], "check")

    @property
    def eligible(self) -> bool:
        return self.status == "success" and all(
            check.status == "pass" for check in self.checks if check.required
        )


@dataclass(frozen=True)
class DecisionRecord(Record):
    comparator_id: str
    eligible_alternatives: tuple[str, ...]
    selected_id: str | None
    selected_configuration: Mapping[str, Scalar] | None
    outcome: Outcome
    rules_digest: str
    reasons: tuple[str, ...]
    evidence: tuple[ArtifactRef, ...]

    def _validate(self):
        sha256(self.rules_digest)
        unique(self.eligible_alternatives, "eligible alternative")
        if self.selected_id is not None and self.selected_id not in self.eligible_alternatives:
            raise ValueError("selection is not eligible")
        if (self.selected_id is None) != (self.selected_configuration is None):
            raise ValueError("selected identity and configuration must both be present or absent")
        if self.outcome == "no_eligible_model" and self.selected_id is not None:
            raise ValueError("no eligible model cannot have a selection")


@dataclass(frozen=True)
class StudyLink(Record):
    study_id: str
    candidate_id: str
    fitting_inputs: tuple[ArtifactRef, ...]
    run_spec_digest: str
    seed: int
    work_path: str
    committed_manifest: ArtifactRef | None
    predecessor_id: str | None = None

    def _validate(self):
        identifier(self.study_id)
        relative_path(self.work_path)
        sha256(self.run_spec_digest)


@dataclass(frozen=True)
class AttemptRecord(Record):
    id: str
    reservation_id: str
    state: Literal["reserved", "launched", "finished", "uncertain", "reconciled"]
    child_action_id: str | None
    launch_nonce: str
    measured_cost: float | None
    elapsed_seconds: float | None
    uncertain_cost: bool
    receipt: ArtifactRef | None

    def _validate(self):
        for value in (self.id, self.reservation_id, self.launch_nonce):
            identifier(value)
        for value in (self.measured_cost, self.elapsed_seconds):
            if value is not None and value < 0:
                raise ValueError("attempt costs cannot be negative")
        if self.state == "uncertain" and not self.uncertain_cost:
            raise ValueError("uncertain attempt must retain uncertain cost")


@dataclass(frozen=True)
class Request(Record):
    schema_version: Literal["1.0"]
    campaign_id: str
    request_id: str
    expected_revision: int
    operation: Literal[
        "state",
        "diagnostics",
        "propose",
        "admit",
        "evaluate",
        "review",
        "freeze",
        "confirm",
        "cancel",
        "report",
    ]
    # Operation-specific payloads are validated by the service before dispatch.
    payload: Mapping[str, Scalar]

    def _validate(self):
        identifier(self.campaign_id)
        identifier(self.request_id)
        if self.expected_revision < 0:
            raise ValueError("expected_revision cannot be negative")
        if len(self.to_json().encode()) > 65536:
            raise ValueError("request exceeds 64 KiB")

    @classmethod
    def from_json(cls, text: str):
        if len(text.encode("utf-8")) > 65536:
            raise ValueError("request exceeds 64 KiB")
        return super().from_json(text)


@dataclass(frozen=True)
class Response(Record):
    request_id: str
    status: Literal["ok", "error"]
    revision: int
    result: Mapping[str, Scalar]
    error: (
        Literal[
            "schema_error",
            "stale_revision",
            "request_conflict",
            "identity_mismatch",
            "invalid_transition",
            "budget_exhausted",
            "reconciliation_required",
        ]
        | None
    )
    artifact_ids: tuple[str, ...]

    def _validate(self):
        identifier(self.request_id)
        if self.revision < 0 or (self.status == "error") != (self.error is not None):
            raise ValueError("invalid response status/revision")


@dataclass(frozen=True)
class CampaignEvent(Record):
    revision: int
    request_digest: str
    previous_hash: str | None
    owner: Literal["controller"]
    operation: str
    from_state: str
    to_state: str
    response: Response
    artifacts: tuple[ArtifactRef, ...]

    def _validate(self):
        if self.revision < 1 or self.response.revision != self.revision:
            raise ValueError("event and response revision differ")
        sha256(self.request_digest)
        if self.previous_hash is not None:
            sha256(self.previous_hash)
