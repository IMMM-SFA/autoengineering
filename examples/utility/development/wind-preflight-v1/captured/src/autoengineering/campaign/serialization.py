"""Strict, immutable JSON records shared by campaign contracts.

Mappings are sorted for hashing, while list order remains significant. All constructors
copy and freeze their inputs, including records constructed directly from Python.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import MISSING, fields
import hashlib
import json
import math
from types import MappingProxyType, UnionType
from typing import Literal, Union, get_args, get_origin, get_type_hints

from autoengineering.optimization.run_spec import OptimizationRunSpec


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def unique_json(text: str) -> object:
    def mapping(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"nonfinite JSON value: {value}")

    return json.loads(text, object_pairs_hook=mapping, parse_constant=invalid)


def _convert(value, annotation, label):
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, UnionType):
        for choice in args:
            try:
                return _convert(value, choice, label)
            except (ValueError, TypeError):
                pass
        raise ValueError(f"{label} has an invalid type or value")
    if annotation is type(None):
        if value is not None:
            raise ValueError(f"{label} must be null")
        return None
    if origin is Literal:
        if not any(type(value) is type(choice) and value == choice for choice in args):
            raise ValueError(f"{label} must be one of {args}")
        return value
    if origin is tuple:
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"{label} must be a list")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(_convert(item, args[0], label) for item in value)
        if len(value) != len(args):
            raise ValueError(f"{label} has the wrong length")
        return tuple(_convert(item, kind, label) for item, kind in zip(value, args))
    if origin is Mapping:
        if not isinstance(value, Mapping):
            raise ValueError(f"{label} must be a mapping")
        return MappingProxyType(
            {
                _convert(key, args[0], label): _convert(item, args[1], label)
                for key, item in value.items()
            }
        )
    if isinstance(annotation, type) and issubclass(annotation, Record):
        return value if isinstance(value, annotation) else annotation.from_dict(value)
    if annotation is OptimizationRunSpec:
        return annotation.from_dict(value.to_dict() if isinstance(value, annotation) else value)
    if annotation is float:
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"{label} must be finite numeric data")
        return float(value)
    if annotation in (str, int, bool):
        if type(value) is not annotation:
            raise ValueError(f"{label} must be {annotation.__name__}")
        if annotation is str and not value.strip():
            raise ValueError(f"{label} must be nonempty")
        return value
    raise TypeError(f"unsupported record annotation: {annotation}")


def _plain(value):
    if isinstance(value, (Record, OptimizationRunSpec)):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    return value


class Record:
    """Base for frozen dataclasses with an exact, recursively checked schema."""

    def __post_init__(self):
        hints = get_type_hints(type(self))
        for field in fields(self):
            object.__setattr__(
                self, field.name, _convert(getattr(self, field.name), hints[field.name], field.name)
            )
        self._validate()

    def _validate(self):
        pass

    def to_dict(self) -> dict:
        return {field.name: _plain(getattr(self, field.name)) for field in fields(self)}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, Mapping):
            raise ValueError(f"{cls.__name__} must be a mapping")
        declared = {field.name: field for field in fields(cls)}
        required = {
            name
            for name, field in declared.items()
            if field.default is MISSING and field.default_factory is MISSING
        }
        if set(value) - set(declared) or required - set(value):
            raise ValueError(f"{cls.__name__} has unknown or missing fields")
        return cls(**dict(value))

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_json(cls, text: str):
        return cls.from_dict(unique_json(text))

    @property
    def digest(self) -> str:
        return digest(self.to_dict())
