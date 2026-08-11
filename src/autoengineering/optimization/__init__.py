"""Optimization study contracts and search-space definitions."""

from .ledger import LedgerCorruptionError, ObservationLedger
from .records import (
    BackendDiagnostics,
    EvaluationAction,
    EvaluationResult,
    EvaluationScope,
    EvaluationStatus,
    JSONValue,
    Recommendation,
    Scalar,
)
from .space import CategoricalParameter, ContinuousParameter, IntegerParameter, SearchSpace
from .spec import BudgetSpec, ConstraintSpec, NoiseSpec, ObjectiveSpec, StudySpec

__all__ = [
    "BudgetSpec",
    "BackendDiagnostics",
    "CategoricalParameter",
    "ConstraintSpec",
    "ContinuousParameter",
    "EvaluationAction",
    "EvaluationResult",
    "EvaluationScope",
    "EvaluationStatus",
    "IntegerParameter",
    "JSONValue",
    "LedgerCorruptionError",
    "NoiseSpec",
    "ObjectiveSpec",
    "ObservationLedger",
    "Recommendation",
    "SearchSpace",
    "Scalar",
    "StudySpec",
]
