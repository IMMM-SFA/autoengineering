"""Controller state is an immutable artifact referenced by committed events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .budget import BudgetAccount
from .records import (
    CandidateProposal,
    CandidateSnapshot,
    DecisionRecord,
    EvaluationRecord,
    Outcome,
    StudyLink,
)
from .serialization import Record


@dataclass(frozen=True)
class ControllerState(Record):
    budget: BudgetAccount
    baseline: EvaluationRecord | None = None
    evaluations: tuple[EvaluationRecord, ...] = ()
    proposals: tuple[CandidateProposal, ...] = ()
    snapshots: tuple[CandidateSnapshot, ...] = ()
    decisions: tuple[DecisionRecord, ...] = ()
    studies: tuple[StudyLink, ...] = ()
    phase: Literal["model", "diagnostics", "confirmation"] = "model"
    active_candidate: str | None = None
    active_mode: Literal["fixed", "calibrate"] | None = None
    active_reservation: str | None = None
    resume_state: str | None = None
    frozen_id: str | None = None
    outcome: Outcome | None = None
    confirmation: Literal[
        "pending", "confirmation_not_attempted", "pass", "fail", "unavailable"
    ] = "pending"
