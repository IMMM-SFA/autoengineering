"""Optimization study contracts and search-space definitions."""

from .backend import OptimizerBackend, RandomBackend, SearchSpaceExhausted, SobolBackend
from .controller import OptimizationStudy, StudyLockError, StudyRecoveryError
from .ledger import LedgerCorruptionError, ObservationLedger, ObservationLedgerReader
from .provenance import RunIdentity
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
from .run_spec import OptimizationRunSpec
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
    "OptimizationStudy",
    "OptimizationRunSpec",
    "ObjectiveSpec",
    "ObservationLedger",
    "ObservationLedgerReader",
    "OptimizerBackend",
    "Recommendation",
    "RandomBackend",
    "RunIdentity",
    "SearchSpace",
    "SearchSpaceExhausted",
    "Scalar",
    "StudySpec",
    "StudyLockError",
    "StudyRecoveryError",
    "SobolBackend",
]
