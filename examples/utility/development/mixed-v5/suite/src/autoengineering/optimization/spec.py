"""Immutable, serializable specifications for an optimization study."""

from dataclasses import dataclass
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Literal, Mapping

import yaml


def _require_name(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        msg = f"{label} must be a non-empty string"
        raise ValueError(msg)


def _require_finite(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        msg = f"{label} must be a finite number"
        raise ValueError(msg)


@dataclass(frozen=True)
class ObjectiveSpec:
    """The one outcome optimized by a study."""

    outcome: str
    direction: Literal["maximize", "minimize"]

    def __post_init__(self) -> None:
        _require_name(self.outcome, "objective outcome")
        if self.direction not in ("maximize", "minimize"):
            msg = "objective direction must be 'maximize' or 'minimize'"
            raise ValueError(msg)


@dataclass(frozen=True)
class ConstraintSpec:
    """A validation threshold, distinct from the study's primary objective."""

    outcome: str
    operator: Literal[">=", "<="]
    threshold: float
    safety: bool = False

    def __post_init__(self) -> None:
        _require_name(self.outcome, "constraint outcome")
        if self.operator not in (">=", "<="):
            msg = "constraint operator must be '>=' or '<='"
            raise ValueError(msg)
        _require_finite(self.threshold, "constraint threshold")
        if self.safety:
            msg = "safety constraints are unsupported in this release"
            raise ValueError(msg)


@dataclass(frozen=True)
class BudgetSpec:
    """The resource limit for a study."""

    max_cost: float
    cost_unit: str
    max_evaluations: int | None = None
    initial_cost_estimate: float = 1.0

    def __post_init__(self) -> None:
        _require_finite(self.max_cost, "max_cost")
        if self.max_cost <= 0:
            msg = "max_cost must be positive"
            raise ValueError(msg)
        _require_name(self.cost_unit, "cost_unit")
        if self.max_evaluations is not None and (
            isinstance(self.max_evaluations, bool)
            or not isinstance(self.max_evaluations, int)
            or self.max_evaluations <= 0
        ):
            msg = "max_evaluations must be a positive integer or None"
            raise ValueError(msg)
        _require_finite(self.initial_cost_estimate, "initial_cost_estimate")
        if self.initial_cost_estimate <= 0:
            msg = "initial_cost_estimate must be positive"
            raise ValueError(msg)


@dataclass(frozen=True)
class NoiseSpec:
    """The observation-noise assumption supplied to later optimizers."""

    mode: Literal["deterministic", "known", "learned"] = "deterministic"
    noise_floor: float = 1e-6

    def __post_init__(self) -> None:
        if self.mode not in ("deterministic", "known", "learned"):
            msg = "noise mode must be 'deterministic', 'known', or 'learned'"
            raise ValueError(msg)
        _require_finite(self.noise_floor, "noise_floor")
        if self.noise_floor < 0:
            msg = "noise_floor must be non-negative"
            raise ValueError(msg)


@dataclass(frozen=True)
class StudySpec:
    """The complete immutable contract for one optimization study.

    ``to_dict`` and ``to_json`` preserve field order. ``to_yaml`` writes the
    same ordered scalar representation, making repeated YAML writes stable.
    """

    name: str
    objective: ObjectiveSpec
    constraints: tuple[ConstraintSpec, ...]
    budget: BudgetSpec
    noise: NoiseSpec
    backend: Literal["system", "function_network_full", "function_network_partial"]
    seed: int = 0
    schema_version: str = "1.0"

    def __post_init__(self) -> None:
        _require_name(self.name, "study name")
        if not isinstance(self.objective, ObjectiveSpec):
            raise TypeError("objective must be an ObjectiveSpec")
        constraints = tuple(self.constraints)
        if not all(isinstance(constraint, ConstraintSpec) for constraint in constraints):
            raise TypeError("constraints must contain ConstraintSpec records")
        object.__setattr__(self, "constraints", constraints)
        if not isinstance(self.budget, BudgetSpec):
            raise TypeError("budget must be a BudgetSpec")
        if not isinstance(self.noise, NoiseSpec):
            raise TypeError("noise must be a NoiseSpec")
        if self.backend not in ("system", "function_network_full", "function_network_partial"):
            msg = "backend must be 'system', 'function_network_full', or 'function_network_partial'"
            raise ValueError(msg)
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        _require_name(self.schema_version, "schema_version")

    def to_dict(self) -> dict[str, Any]:
        """Return an ordered, scalar-only representation suitable for YAML or JSON."""
        return {
            "name": self.name,
            "objective": {"outcome": self.objective.outcome, "direction": self.objective.direction},
            "constraints": [
                {
                    "outcome": constraint.outcome,
                    "operator": constraint.operator,
                    "threshold": constraint.threshold,
                    "safety": constraint.safety,
                }
                for constraint in self.constraints
            ],
            "budget": {
                "max_cost": self.budget.max_cost,
                "cost_unit": self.budget.cost_unit,
                "max_evaluations": self.budget.max_evaluations,
                "initial_cost_estimate": self.budget.initial_cost_estimate,
            },
            "noise": {"mode": self.noise.mode, "noise_floor": self.noise.noise_floor},
            "backend": self.backend,
            "seed": self.seed,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StudySpec":
        """Construct a study from the representation returned by ``to_dict``."""
        if not isinstance(data, Mapping):
            raise TypeError("study specification must be a mapping")
        required = {
            "name",
            "objective",
            "constraints",
            "budget",
            "noise",
            "backend",
            "seed",
            "schema_version",
        }
        if set(data) != required:
            msg = f"study specification keys must be exactly {sorted(required)}"
            raise ValueError(msg)
        objective = data["objective"]
        budget = data["budget"]
        noise = data["noise"]
        constraints = data["constraints"]
        if (
            not isinstance(objective, Mapping)
            or not isinstance(budget, Mapping)
            or not isinstance(noise, Mapping)
        ):
            raise TypeError("objective, budget, and noise must be mappings")
        if not isinstance(constraints, list):
            raise TypeError("constraints must be a list")
        return cls(
            name=data["name"],
            objective=ObjectiveSpec(**objective),
            constraints=tuple(ConstraintSpec(**constraint) for constraint in constraints),
            budget=BudgetSpec(**budget),
            noise=NoiseSpec(**noise),
            backend=data["backend"],
            seed=data["seed"],
            schema_version=data["schema_version"],
        )

    def to_json(self) -> str:
        """Serialize this study to canonical compact JSON."""
        return json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_json(cls, value: str) -> "StudySpec":
        """Deserialize a study from JSON."""
        return cls.from_dict(json.loads(value))

    def to_yaml(self, path: str | Path) -> None:
        """Write this study's canonical YAML representation to ``path``."""
        Path(path).write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "StudySpec":
        """Read a study specification from a YAML file."""
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)
