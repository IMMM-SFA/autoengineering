"""Optimization study contracts and search-space definitions."""

from .backend import (
    MarginalValueExhausted,
    OptimizerBackend,
    RandomBackend,
    ScopedActionBackend,
    SearchSpaceExhausted,
    SobolBackend,
)
from .controller import OptimizationStudy, StudyLockError, StudyRecoveryError, StudyRunResult
from .function_network import (
    CouplingSpec,
    FunctionComponentSpec,
    FunctionNetworkSpec,
    FunctionPortSpec,
    ScalarOutputSpec,
    TerminalConstraintSpec,
    TerminalObjectiveSpec,
    reduce_scalar,
    scalar_observation_name,
)
from .function_network_evaluator import (
    ComponentTrainingRow,
    FunctionNetworkArtifactError,
    FunctionNetworkEvaluator,
    LedgerBackedFunctionNetworkEvaluator,
    NpzReadLimits,
    read_verified_npz,
    reconstruct_component_training_tables,
    reconstruct_parent_artifact_registry,
)
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
    "CouplingSpec",
    "ComponentTrainingRow",
    "EvaluationAction",
    "EvaluationResult",
    "EvaluationScope",
    "EvaluationStatus",
    "FunctionComponentSpec",
    "FunctionNetworkArtifactError",
    "FunctionNetworkEvaluator",
    "LedgerBackedFunctionNetworkEvaluator",
    "FunctionNetworkSpec",
    "FunctionPortSpec",
    "IntegerParameter",
    "JSONValue",
    "LedgerCorruptionError",
    "MarginalValueExhausted",
    "NoiseSpec",
    "NpzReadLimits",
    "OptimizationStudy",
    "OptimizationRunSpec",
    "ObjectiveSpec",
    "ObservationLedger",
    "ObservationLedgerReader",
    "OptimizerBackend",
    "Recommendation",
    "RandomBackend",
    "RunIdentity",
    "ScalarOutputSpec",
    "SearchSpace",
    "SearchSpaceExhausted",
    "Scalar",
    "ScopedActionBackend",
    "StudySpec",
    "StudyLockError",
    "StudyRecoveryError",
    "StudyRunResult",
    "SobolBackend",
    "TerminalConstraintSpec",
    "TerminalObjectiveSpec",
    "read_verified_npz",
    "reconstruct_component_training_tables",
    "reconstruct_parent_artifact_registry",
    "reduce_scalar",
    "scalar_observation_name",
]
