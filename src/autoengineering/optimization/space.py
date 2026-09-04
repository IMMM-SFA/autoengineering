"""Deterministic encodings for typed conditional optimization spaces.

Parameter order is declaration order. Categories use the order in each
``categories`` tuple and encode as evenly spaced values from zero to one.
Conditional numeric parameters add an activity dimension after their value:
inactive parameters encode as ``(0.5, 0.0)`` and active parameters as
``(normalized_value, 1.0)``. Conditional categorical parameters are not
supported because their inactive state would require a separate mask.
"""

from dataclasses import dataclass, field
import math
from numbers import Real
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping, Sequence, TypeAlias

import yaml

from .yaml_utils import safe_load_unique


Scalar: TypeAlias = str | int | float | bool
ActiveWhen: TypeAlias = Mapping[str, tuple[Scalar, ...]]
SEARCH_SPACE_SCHEMA_VERSION = "1.0"


def _write_yaml(path: str | Path, value: Mapping[str, object]) -> None:
    Path(path).write_text(yaml.safe_dump(dict(value), sort_keys=False), encoding="utf-8")


def _read_yaml(path: str | Path) -> object:
    return safe_load_unique(Path(path).read_text(encoding="utf-8"))


def _require_exact_keys(data: Mapping[str, Any], required: set[str], label: str) -> None:
    if not isinstance(data, Mapping):
        raise TypeError(f"{label} must be a mapping")
    if set(data) != required:
        raise ValueError(f"{label} keys must be exactly {sorted(required)}")


def _conditions_dict(active_when: ActiveWhen) -> dict[str, list[Scalar]]:
    return {name: list(values) for name, values in active_when.items()}


def _conditions_from_dict(value: object) -> dict[str, tuple[Scalar, ...]]:
    if not isinstance(value, Mapping):
        raise TypeError("active_when must be a mapping")
    conditions: dict[str, tuple[Scalar, ...]] = {}
    for name, values in value.items():
        if not isinstance(name, str) or not isinstance(values, list):
            raise TypeError("active_when must map names to lists")
        conditions[name] = tuple(values)
    return conditions


def _is_scalar(value: object) -> bool:
    return isinstance(value, str | int | float | bool)


def _same_scalar(left: Scalar, right: Scalar) -> bool:
    return type(left) is type(right) and left == right


def _category_index(categories: tuple[Scalar, ...], value: object) -> int | None:
    for index, category in enumerate(categories):
        if _same_scalar(category, value):
            return index
    return None


def _require_name(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _require_real(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _freeze_conditions(active_when: ActiveWhen) -> Mapping[str, tuple[Scalar, ...]]:
    if not isinstance(active_when, Mapping):
        raise TypeError("active_when must be a mapping")
    frozen: dict[str, tuple[Scalar, ...]] = {}
    for condition_name, values in active_when.items():
        _require_name(condition_name, "condition name")
        values_tuple = tuple(values)
        if not values_tuple:
            raise ValueError("condition values must be non-empty")
        if not all(_is_scalar(value) for value in values_tuple):
            raise ValueError("condition values must be non-null YAML/JSON scalars")
        frozen[condition_name] = values_tuple
    return MappingProxyType(frozen)


@dataclass(frozen=True)
class CategoricalParameter:
    """A categorical parameter encoded by declaration-order category index."""

    name: str
    categories: tuple[Scalar, ...]

    def __post_init__(self) -> None:
        _require_name(self.name, "parameter name")
        categories = tuple(self.categories)
        if not categories:
            raise ValueError("categories must be non-empty")
        if not all(_is_scalar(category) for category in categories):
            raise ValueError("categories must contain non-null YAML/JSON scalars")
        if any(
            isinstance(category, float) and not math.isfinite(category) for category in categories
        ):
            raise ValueError("float categories must be finite")
        if any(
            _same_scalar(category, other)
            for index, category in enumerate(categories)
            for other in categories[index + 1 :]
        ):
            raise ValueError("categories must not contain duplicates")
        object.__setattr__(self, "categories", categories)

    def to_dict(self) -> dict[str, object]:
        """Return the ordered public representation of this parameter."""
        return {"type": "categorical", "name": self.name, "categories": list(self.categories)}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CategoricalParameter":
        """Load a categorical parameter from its exact public schema."""
        _require_exact_keys(data, {"type", "name", "categories"}, "categorical parameter")
        if data["type"] != "categorical":
            raise ValueError("categorical parameter type must be 'categorical'")
        if not isinstance(data["categories"], list):
            raise TypeError("categorical parameter categories must be a list")
        return cls(name=data["name"], categories=tuple(data["categories"]))

    def to_yaml(self, path: str | Path) -> None:
        """Write this parameter as stable safe YAML."""
        _write_yaml(path, self.to_dict())

    @classmethod
    def from_yaml(cls, path: str | Path) -> "CategoricalParameter":
        """Load this parameter from YAML."""
        return cls.from_dict(_read_yaml(path))


@dataclass(frozen=True)
class ContinuousParameter:
    """A bounded floating-point parameter encoded on the unit interval."""

    name: str
    lower: float
    upper: float
    scale: Literal["linear", "log"] = "linear"
    active_when: ActiveWhen = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_name(self.name, "parameter name")
        lower = _require_real(self.lower, "lower")
        upper = _require_real(self.upper, "upper")
        if lower >= upper:
            raise ValueError("lower must be less than upper")
        if self.scale not in ("linear", "log"):
            raise ValueError("scale must be 'linear' or 'log'")
        if self.scale == "log" and lower <= 0:
            raise ValueError("log scale lower bound must be positive")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "active_when", _freeze_conditions(self.active_when))

    def to_dict(self) -> dict[str, object]:
        """Return the ordered public representation of this parameter."""
        return {
            "type": "continuous",
            "name": self.name,
            "lower": self.lower,
            "upper": self.upper,
            "scale": self.scale,
            "active_when": _conditions_dict(self.active_when),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ContinuousParameter":
        """Load a continuous parameter from its exact public schema."""
        required = {"type", "name", "lower", "upper", "scale", "active_when"}
        _require_exact_keys(data, required, "continuous parameter")
        if data["type"] != "continuous":
            raise ValueError("continuous parameter type must be 'continuous'")
        return cls(
            name=data["name"],
            lower=data["lower"],
            upper=data["upper"],
            scale=data["scale"],
            active_when=_conditions_from_dict(data["active_when"]),
        )

    def to_yaml(self, path: str | Path) -> None:
        """Write this parameter as stable safe YAML."""
        _write_yaml(path, self.to_dict())

    @classmethod
    def from_yaml(cls, path: str | Path) -> "ContinuousParameter":
        """Load this parameter from YAML."""
        return cls.from_dict(_read_yaml(path))


@dataclass(frozen=True)
class IntegerParameter:
    """A bounded integer parameter encoded on the unit interval."""

    name: str
    lower: int
    upper: int
    scale: Literal["linear", "log"] = "linear"
    active_when: ActiveWhen = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_name(self.name, "parameter name")
        if (
            isinstance(self.lower, bool)
            or isinstance(self.upper, bool)
            or not isinstance(self.lower, int)
            or not isinstance(self.upper, int)
        ):
            raise ValueError("integer bounds must be integers")
        if self.lower >= self.upper:
            raise ValueError("lower must be less than upper")
        if self.scale not in ("linear", "log"):
            raise ValueError("scale must be 'linear' or 'log'")
        if self.scale == "log" and self.lower <= 0:
            raise ValueError("log scale lower bound must be positive")
        object.__setattr__(self, "active_when", _freeze_conditions(self.active_when))

    def to_dict(self) -> dict[str, object]:
        """Return the ordered public representation of this parameter."""
        return {
            "type": "integer",
            "name": self.name,
            "lower": self.lower,
            "upper": self.upper,
            "scale": self.scale,
            "active_when": _conditions_dict(self.active_when),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IntegerParameter":
        """Load an integer parameter from its exact public schema."""
        required = {"type", "name", "lower", "upper", "scale", "active_when"}
        _require_exact_keys(data, required, "integer parameter")
        if data["type"] != "integer":
            raise ValueError("integer parameter type must be 'integer'")
        return cls(
            name=data["name"],
            lower=data["lower"],
            upper=data["upper"],
            scale=data["scale"],
            active_when=_conditions_from_dict(data["active_when"]),
        )

    def to_yaml(self, path: str | Path) -> None:
        """Write this parameter as stable safe YAML."""
        _write_yaml(path, self.to_dict())

    @classmethod
    def from_yaml(cls, path: str | Path) -> "IntegerParameter":
        """Load this parameter from YAML."""
        return cls.from_dict(_read_yaml(path))


NumericParameter: TypeAlias = ContinuousParameter | IntegerParameter
Parameter: TypeAlias = CategoricalParameter | NumericParameter


@dataclass(frozen=True)
class SearchSpace:
    """An immutable typed search space with a deterministic unit-cube encoding."""

    parameters: tuple[Parameter, ...]

    def __post_init__(self) -> None:
        parameters = tuple(self.parameters)
        if not parameters:
            raise ValueError("parameters must be non-empty")
        if not all(
            isinstance(parameter, (CategoricalParameter, ContinuousParameter, IntegerParameter))
            for parameter in parameters
        ):
            raise TypeError("parameters must be categorical, continuous, or integer")
        names = tuple(parameter.name for parameter in parameters)
        if len(set(names)) != len(names):
            raise ValueError("duplicate parameter names are not allowed")
        known: dict[str, Parameter] = {}
        for parameter in parameters:
            if isinstance(parameter, (ContinuousParameter, IntegerParameter)):
                for condition_name, values in parameter.active_when.items():
                    if condition_name not in known:
                        raise ValueError(f"unknown condition parameter: {condition_name}")
                    condition = known[condition_name]
                    if not isinstance(condition, CategoricalParameter):
                        raise ValueError("conditions may only reference categorical parameters")
                    if any(
                        _category_index(condition.categories, value) is None for value in values
                    ):
                        raise ValueError(f"condition category is invalid for {condition_name}")
            known[parameter.name] = parameter
        object.__setattr__(self, "parameters", parameters)

    def to_dict(self) -> dict[str, object]:
        """Return the ordered public representation of this search space."""
        return {
            "schema_version": SEARCH_SPACE_SCHEMA_VERSION,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SearchSpace":
        """Load a search space from its strict public representation."""
        _require_exact_keys(data, {"schema_version", "parameters"}, "search space")
        if data["schema_version"] != SEARCH_SPACE_SCHEMA_VERSION:
            raise ValueError("search space schema version differs")
        parameters = data["parameters"]
        if not isinstance(parameters, list):
            raise TypeError("search space parameters must be a list")
        loaded: list[Parameter] = []
        loaders = {
            "categorical": CategoricalParameter.from_dict,
            "continuous": ContinuousParameter.from_dict,
            "integer": IntegerParameter.from_dict,
        }
        for parameter in parameters:
            if not isinstance(parameter, Mapping):
                raise TypeError("search space parameter must be a mapping")
            parameter_type = parameter.get("type")
            if parameter_type not in loaders:
                raise ValueError(f"unknown search space parameter type: {parameter_type!r}")
            loaded.append(loaders[parameter_type](parameter))
        return cls(tuple(loaded))

    def to_yaml(self, path: str | Path) -> None:
        """Write this search space as stable safe YAML."""
        _write_yaml(path, self.to_dict())

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SearchSpace":
        """Load a search space from YAML."""
        return cls.from_dict(_read_yaml(path))

    @property
    def encoded_dimension(self) -> int:
        """Return the fixed length of encoded vectors for this space."""
        return sum(
            2
            if isinstance(parameter, (ContinuousParameter, IntegerParameter))
            and parameter.active_when
            else 1
            for parameter in self.parameters
        )

    def active_names(self, config: Mapping[str, Scalar]) -> tuple[str, ...]:
        """Return active parameter names in declaration order.

        Only categorical selectors are required to determine activity, so this
        method can be used while constructing a partial configuration.
        """
        self._validate_selectors(config)
        return tuple(
            parameter.name
            for parameter in self.parameters
            if not isinstance(parameter, (ContinuousParameter, IntegerParameter))
            or self._is_active(parameter, config)
        )

    def encode(self, config: Mapping[str, Scalar]) -> tuple[float, ...]:
        """Encode a complete active configuration as a tuple of unit-cube values."""
        self._validate_configuration(config)
        encoded: list[float] = []
        for parameter in self.parameters:
            if isinstance(parameter, CategoricalParameter):
                category_index = _category_index(parameter.categories, config[parameter.name])
                assert category_index is not None
                denominator = max(len(parameter.categories) - 1, 1)
                encoded.append(category_index / denominator)
                continue

            is_active = self._is_active(parameter, config)
            if parameter.active_when and not is_active:
                encoded.extend((0.5, 0.0))
                continue

            encoded.append(self._normalize(parameter, config[parameter.name]))
            if parameter.active_when:
                encoded.append(1.0)
        return tuple(encoded)

    def decode(self, encoded: Sequence[float]) -> dict[str, Scalar]:
        """Decode a canonical vector, omitting inactive conditional numeric keys."""
        values = tuple(encoded)
        if len(values) != self.encoded_dimension:
            raise ValueError(f"encoded vector must have {self.encoded_dimension} values")
        config: dict[str, Scalar] = {}
        index = 0
        for parameter in self.parameters:
            if isinstance(parameter, CategoricalParameter):
                normalized = self._unit_value(values[index], parameter.name)
                config[parameter.name] = self._decode_category(parameter, normalized)
                index += 1
                continue

            normalized = self._unit_value(values[index], parameter.name)
            index += 1
            is_active = self._is_active(parameter, config)
            if parameter.active_when:
                activity = self._unit_value(values[index], f"{parameter.name} activity")
                index += 1
                required_activity = 1.0 if is_active else 0.0
                if not math.isclose(activity, required_activity, abs_tol=1e-12):
                    raise ValueError(
                        f"activity mask conflicts with conditions for {parameter.name}"
                    )
                if not is_active:
                    continue
            config[parameter.name] = self._denormalize(parameter, normalized)
        return config

    def _validate_selectors(self, config: Mapping[str, Scalar]) -> None:
        if not isinstance(config, Mapping):
            raise TypeError("configuration must be a mapping")
        names = {parameter.name for parameter in self.parameters}
        unknown = set(config) - names
        if unknown:
            raise ValueError(f"unknown configuration parameters: {sorted(unknown)}")
        for parameter in self.parameters:
            if isinstance(parameter, CategoricalParameter):
                if parameter.name not in config:
                    raise ValueError(f"missing categorical parameter: {parameter.name}")
                if _category_index(parameter.categories, config[parameter.name]) is None:
                    raise ValueError(f"invalid category for {parameter.name}")

    def _validate_configuration(self, config: Mapping[str, Scalar]) -> None:
        self._validate_selectors(config)
        for parameter in self.parameters:
            if not isinstance(parameter, (ContinuousParameter, IntegerParameter)):
                continue
            is_active = self._is_active(parameter, config)
            if not is_active:
                if parameter.name in config:
                    raise ValueError(f"inactive parameter must be omitted: {parameter.name}")
                continue
            if parameter.name not in config:
                raise ValueError(f"missing active parameter: {parameter.name}")
            self._normalize(parameter, config[parameter.name])

    @staticmethod
    def _is_active(parameter: NumericParameter, config: Mapping[str, Scalar]) -> bool:
        return all(
            _category_index(tuple(values), config.get(condition_name)) is not None
            for condition_name, values in parameter.active_when.items()
        )

    @staticmethod
    def _unit_value(value: object, label: str) -> float:
        normalized = _require_real(value, label)
        if not 0.0 <= normalized <= 1.0:
            raise ValueError(f"{label} must be in [0, 1]")
        return normalized

    @staticmethod
    def _decode_category(parameter: CategoricalParameter, normalized: float) -> Scalar:
        if len(parameter.categories) == 1:
            return parameter.categories[0]
        index = math.floor(normalized * (len(parameter.categories) - 1) + 0.5)
        return parameter.categories[index]

    @staticmethod
    def _normalize(parameter: NumericParameter, value: object) -> float:
        numeric = _require_real(value, parameter.name)
        if not parameter.lower <= numeric <= parameter.upper:
            raise ValueError(
                f"{parameter.name} must be within [{parameter.lower}, {parameter.upper}]"
            )
        if parameter.scale == "linear":
            return (numeric - parameter.lower) / (parameter.upper - parameter.lower)
        return (math.log(numeric) - math.log(parameter.lower)) / (
            math.log(parameter.upper) - math.log(parameter.lower)
        )

    @staticmethod
    def _denormalize(parameter: NumericParameter, normalized: float) -> Scalar:
        if parameter.scale == "linear":
            value = parameter.lower + normalized * (parameter.upper - parameter.lower)
        else:
            value = math.exp(
                math.log(parameter.lower)
                + normalized * (math.log(parameter.upper) - math.log(parameter.lower))
            )
        if isinstance(parameter, IntegerParameter):
            return min(parameter.upper, max(parameter.lower, math.floor(value + 0.5)))
        return value
