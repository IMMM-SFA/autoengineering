"""Frozen, JSON-serializable records for optimization observations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import math
from numbers import Real
from types import MappingProxyType
from typing import TypeAlias

Scalar: TypeAlias = str | int | float | bool
JSONValue: TypeAlias = Scalar | None | tuple["JSONValue", ...] | Mapping[str, "JSONValue"]


class EvaluationScope(StrEnum):
    """The portion of a system evaluated by an action."""

    SYSTEM = "system"
    COMPONENT = "component"


class EvaluationStatus(StrEnum):
    """The durable status taxonomy for an evaluation attempt."""

    SUCCESS = "success"
    SCIENTIFIC_INFEASIBLE = "scientific_infeasible"
    MODEL_FAILURE = "model_failure"
    TIMEOUT = "timeout"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"


def _require_name(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_finite(value: object, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    numeric = float(value)
    if nonnegative and numeric < 0:
        raise ValueError(f"{label} must be non-negative")
    return numeric


def _freeze_scalar_mapping(values: Mapping[str, Scalar], label: str) -> Mapping[str, Scalar]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{label} must be a mapping")
    frozen: dict[str, Scalar] = {}
    for key, value in values.items():
        _require_name(key, f"{label} key")
        if not isinstance(value, (str, int, float, bool)):
            raise TypeError(f"{label} values must be scalar")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{label} floats must be finite")
        frozen[key] = value
    return MappingProxyType(frozen)


def _freeze_float_mapping(
    values: Mapping[str, float], label: str, *, nonnegative: bool = False
) -> Mapping[str, float]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return MappingProxyType(
        {
            _require_name(key, f"{label} key"): _require_finite(
                value, f"{label}[{key!r}]", nonnegative=nonnegative
            )
            for key, value in values.items()
        }
    )


def _freeze_string_mapping(values: Mapping[str, str], label: str) -> Mapping[str, str]:
    if not isinstance(values, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return MappingProxyType(
        {
            _require_name(key, f"{label} key"): _require_name(value, f"{label}[{key!r}]")
            for key, value in values.items()
        }
    )


def _json_value(value: JSONValue) -> object:
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    return value


def _freeze_json(value: object, label: str) -> JSONValue:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return _require_finite(value, label)
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                _require_name(key, f"{label} key"): _freeze_json(item, f"{label}[{key!r}]")
                for key, item in value.items()
            }
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item, label) for item in value)
    raise TypeError(f"{label} must be a JSON value")


@dataclass(frozen=True)
class EvaluationAction:
    """An immutable request to evaluate a system or one component."""

    id: str
    config: Mapping[str, Scalar]
    scope: EvaluationScope
    component: str | None
    parent_artifact_ids: tuple[str, ...] = ()
    replicates: int = 1
    seed: int = 0
    suggested_by: str = "unknown"

    def __post_init__(self) -> None:
        _require_name(self.id, "action id")
        object.__setattr__(self, "config", _freeze_scalar_mapping(self.config, "config"))
        try:
            scope = EvaluationScope(self.scope)
        except ValueError as error:
            raise ValueError("scope must be 'system' or 'component'") from error
        object.__setattr__(self, "scope", scope)
        if scope is EvaluationScope.SYSTEM:
            if self.component is not None:
                raise ValueError("system actions must not name a component")
        else:
            _require_name(self.component, "component")
        parent_ids = tuple(self.parent_artifact_ids)
        for artifact_id in parent_ids:
            _require_name(artifact_id, "parent artifact id")
        object.__setattr__(self, "parent_artifact_ids", parent_ids)
        if (
            isinstance(self.replicates, bool)
            or not isinstance(self.replicates, int)
            or self.replicates <= 0
        ):
            raise ValueError("replicates must be a positive integer")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        _require_name(self.suggested_by, "suggested_by")

    @classmethod
    def system(
        cls,
        action_id: str,
        config: Mapping[str, Scalar],
        *,
        seed: int = 0,
        parent_artifact_ids: tuple[str, ...] = (),
        replicates: int = 1,
        suggested_by: str = "unknown",
    ) -> "EvaluationAction":
        """Create a whole-system evaluation action."""
        return cls(
            id=action_id,
            config=config,
            scope=EvaluationScope.SYSTEM,
            component=None,
            parent_artifact_ids=parent_artifact_ids,
            replicates=replicates,
            seed=seed,
            suggested_by=suggested_by,
        )

    @classmethod
    def component(
        cls,
        action_id: str,
        component: str,
        config: Mapping[str, Scalar],
        *,
        seed: int = 0,
        parent_artifact_ids: tuple[str, ...] = (),
        replicates: int = 1,
        suggested_by: str = "unknown",
    ) -> "EvaluationAction":
        """Create a component-scope evaluation action."""
        return cls(
            id=action_id,
            config=config,
            scope=EvaluationScope.COMPONENT,
            component=component,
            parent_artifact_ids=parent_artifact_ids,
            replicates=replicates,
            seed=seed,
            suggested_by=suggested_by,
        )

    def to_dict(self) -> dict[str, object]:
        """Return the canonical JSON-compatible representation."""
        return {
            "id": self.id,
            "config": dict(self.config),
            "scope": self.scope.value,
            "component": self.component,
            "parent_artifact_ids": list(self.parent_artifact_ids),
            "replicates": self.replicates,
            "seed": self.seed,
            "suggested_by": self.suggested_by,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EvaluationAction":
        """Reconstruct an action from its canonical representation."""
        required = {
            "id",
            "config",
            "scope",
            "component",
            "parent_artifact_ids",
            "replicates",
            "seed",
            "suggested_by",
        }
        if not isinstance(data, Mapping) or set(data) != required:
            raise ValueError("action record has invalid keys")
        if not isinstance(data["config"], Mapping) or not isinstance(
            data["parent_artifact_ids"], list
        ):
            raise TypeError("action record has invalid mapping or list fields")
        return cls(
            id=data["id"],
            config=data["config"],
            scope=data["scope"],
            component=data["component"],
            parent_artifact_ids=tuple(data["parent_artifact_ids"]),
            replicates=data["replicates"],
            seed=data["seed"],
            suggested_by=data["suggested_by"],
        )


@dataclass(frozen=True)
class EvaluationResult:
    """An immutable, classified result of executing one evaluation action."""

    action_id: str
    status: EvaluationStatus
    outcomes: Mapping[str, float] = field(default_factory=dict)
    standard_errors: Mapping[str, float] = field(default_factory=dict)
    cost: float = 0.0
    cost_unit: str = "evaluation"
    artifacts: Mapping[str, str] = field(default_factory=dict)
    artifact_sha256: Mapping[str, str] = field(default_factory=dict)
    optimizer_seconds: float = 0.0
    evaluator_seconds: float = 0.0
    message: str = ""

    def __post_init__(self) -> None:
        _require_name(self.action_id, "action_id")
        try:
            status = EvaluationStatus(self.status)
        except ValueError as error:
            raise ValueError("status is invalid") from error
        object.__setattr__(self, "status", status)
        outcomes = _freeze_float_mapping(self.outcomes, "outcomes")
        errors = _freeze_float_mapping(self.standard_errors, "standard_errors", nonnegative=True)
        if not set(errors).issubset(outcomes):
            raise ValueError("standard_errors keys must be outcome keys")
        if status is EvaluationStatus.SUCCESS and not outcomes:
            raise ValueError("successful results must include outcomes")
        if status is not EvaluationStatus.SUCCESS and (outcomes or errors):
            raise ValueError("failure results must not include outcomes or standard_errors")
        object.__setattr__(self, "outcomes", outcomes)
        object.__setattr__(self, "standard_errors", errors)
        object.__setattr__(self, "cost", _require_finite(self.cost, "cost", nonnegative=True))
        _require_name(self.cost_unit, "cost_unit")
        object.__setattr__(self, "artifacts", _freeze_string_mapping(self.artifacts, "artifacts"))
        hashes = _freeze_string_mapping(self.artifact_sha256, "artifact_sha256")
        if set(hashes) != set(self.artifacts):
            raise ValueError("artifact_sha256 keys must exactly match artifacts")
        for artifact_id, digest in hashes.items():
            if len(digest) != 64 or any(
                character not in "0123456789abcdef" for character in digest
            ):
                raise ValueError(
                    f"artifact_sha256[{artifact_id!r}] must be a lowercase SHA-256 hex digest"
                )
        object.__setattr__(self, "artifact_sha256", hashes)
        object.__setattr__(
            self,
            "optimizer_seconds",
            _require_finite(self.optimizer_seconds, "optimizer_seconds", nonnegative=True),
        )
        object.__setattr__(
            self,
            "evaluator_seconds",
            _require_finite(self.evaluator_seconds, "evaluator_seconds", nonnegative=True),
        )
        if not isinstance(self.message, str):
            raise TypeError("message must be a string")

    @classmethod
    def success(
        cls,
        action_id: str,
        outcomes: Mapping[str, float],
        standard_errors: Mapping[str, float],
        cost: float,
        cost_unit: str,
        *,
        artifacts: Mapping[str, str] | None = None,
        artifact_sha256: Mapping[str, str] | None = None,
        optimizer_seconds: float = 0.0,
        evaluator_seconds: float = 0.0,
        message: str = "",
    ) -> "EvaluationResult":
        """Create a successful result with measured scientific outcomes."""
        return cls(
            action_id=action_id,
            status=EvaluationStatus.SUCCESS,
            outcomes=outcomes,
            standard_errors=standard_errors,
            cost=cost,
            cost_unit=cost_unit,
            artifacts={} if artifacts is None else artifacts,
            artifact_sha256={} if artifact_sha256 is None else artifact_sha256,
            optimizer_seconds=optimizer_seconds,
            evaluator_seconds=evaluator_seconds,
            message=message,
        )

    @classmethod
    def scientific_infeasible(
        cls, action_id: str, message: str, **kwargs: object
    ) -> "EvaluationResult":
        """Create a result denoting a valid but scientifically infeasible evaluation."""
        return cls._failure(EvaluationStatus.SCIENTIFIC_INFEASIBLE, action_id, message, **kwargs)

    @classmethod
    def model_failure(cls, action_id: str, message: str, **kwargs: object) -> "EvaluationResult":
        """Create a result denoting a model execution failure."""
        return cls._failure(EvaluationStatus.MODEL_FAILURE, action_id, message, **kwargs)

    @classmethod
    def timeout(cls, action_id: str, message: str, **kwargs: object) -> "EvaluationResult":
        """Create a result denoting an execution timeout."""
        return cls._failure(EvaluationStatus.TIMEOUT, action_id, message, **kwargs)

    @classmethod
    def infrastructure_failure(
        cls, action_id: str, message: str, **kwargs: object
    ) -> "EvaluationResult":
        """Create a result denoting a scheduler, storage, or transport failure."""
        return cls._failure(EvaluationStatus.INFRASTRUCTURE_FAILURE, action_id, message, **kwargs)

    @classmethod
    def _failure(
        cls, status: EvaluationStatus, action_id: str, message: str, **kwargs: object
    ) -> "EvaluationResult":
        permitted = {
            "cost",
            "cost_unit",
            "artifacts",
            "artifact_sha256",
            "optimizer_seconds",
            "evaluator_seconds",
        }
        unexpected = set(kwargs) - permitted
        if unexpected:
            raise TypeError(f"unexpected failure result fields: {sorted(unexpected)}")
        return cls(action_id=action_id, status=status, message=message, **kwargs)

    def to_dict(self) -> dict[str, object]:
        """Return the canonical JSON-compatible representation."""
        return {
            "action_id": self.action_id,
            "status": self.status.value,
            "outcomes": dict(self.outcomes),
            "standard_errors": dict(self.standard_errors),
            "cost": self.cost,
            "cost_unit": self.cost_unit,
            "artifacts": dict(self.artifacts),
            "artifact_sha256": dict(self.artifact_sha256),
            "optimizer_seconds": self.optimizer_seconds,
            "evaluator_seconds": self.evaluator_seconds,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "EvaluationResult":
        """Reconstruct a result from its canonical representation."""
        required = {
            "action_id",
            "status",
            "outcomes",
            "standard_errors",
            "cost",
            "cost_unit",
            "artifacts",
            "artifact_sha256",
            "optimizer_seconds",
            "evaluator_seconds",
            "message",
        }
        if not isinstance(data, Mapping) or set(data) != required:
            raise ValueError("result record has invalid keys")
        mapping_fields = ("outcomes", "standard_errors", "artifacts", "artifact_sha256")
        if any(not isinstance(data[field_name], Mapping) for field_name in mapping_fields):
            raise TypeError("result record has invalid mapping fields")
        return cls(**data)


@dataclass(frozen=True)
class Recommendation:
    """A serializable recommendation emitted by an optimizer backend."""

    action_id: str | None
    config: Mapping[str, Scalar]
    outcomes: Mapping[str, float]
    feasible: bool
    message: str = ""

    def __post_init__(self) -> None:
        if self.action_id is not None:
            _require_name(self.action_id, "action_id")
        object.__setattr__(self, "config", _freeze_scalar_mapping(self.config, "config"))
        object.__setattr__(self, "outcomes", _freeze_float_mapping(self.outcomes, "outcomes"))
        if not isinstance(self.feasible, bool):
            raise TypeError("feasible must be a boolean")
        if not isinstance(self.message, str):
            raise TypeError("message must be a string")

    def to_dict(self) -> dict[str, object]:
        return {
            "action_id": self.action_id,
            "config": dict(self.config),
            "outcomes": dict(self.outcomes),
            "feasible": self.feasible,
            "message": self.message,
        }


@dataclass(frozen=True)
class BackendDiagnostics:
    """Frozen backend state suitable for reports and provenance snapshots."""

    backend: str
    fit_state: str = "not_fit"
    fallback_reasons: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    optimizer_seconds: float = 0.0
    details: Mapping[str, JSONValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_name(self.backend, "backend")
        _require_name(self.fit_state, "fit_state")
        for value in (*self.fallback_reasons, *self.warnings):
            _require_name(value, "diagnostic message")
        object.__setattr__(self, "fallback_reasons", tuple(self.fallback_reasons))
        object.__setattr__(self, "warnings", tuple(self.warnings))
        object.__setattr__(
            self,
            "optimizer_seconds",
            _require_finite(self.optimizer_seconds, "optimizer_seconds", nonnegative=True),
        )
        object.__setattr__(self, "details", _freeze_json(self.details, "details"))

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "fit_state": self.fit_state,
            "fallback_reasons": list(self.fallback_reasons),
            "warnings": list(self.warnings),
            "optimizer_seconds": self.optimizer_seconds,
            "details": _json_value(self.details),
        }
