"""Version 1 branch mapping: active decisions plus explicit inactive defaults."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from autoengineering.campaign.serialization import digest
from autoengineering.optimization.space import CategoricalParameter, SearchSpace


def active(parameter, config):
    return all(
        any(type(config.get(name)) is type(value) and config.get(name) == value for value in values)
        for name, values in getattr(parameter, "active_when", {}).items()
    )


def project_sobol(space, point):
    """Project random cube samples using the existing Sobol backend convention."""
    config = {}
    index = 0
    for parameter in space.parameters:
        value = float(point[index])
        index += 1
        if isinstance(parameter, CategoricalParameter):
            config[parameter.name] = space._decode_category(parameter, value)
        else:
            if parameter.active_when:
                index += 1  # Activity follows the selector, never a random mask.
            if active(parameter, config):
                config[parameter.name] = space._denormalize(parameter, value)
    space.encode(config)
    return config


@dataclass(frozen=True)
class BranchMapping:
    space: SearchSpace
    inactive_defaults: Mapping[str, int | float]

    def __post_init__(self):
        defaults = dict(self.inactive_defaults)
        conditional = {p.name: p for p in self.space.parameters if getattr(p, "active_when", {})}
        if set(defaults) != set(conditional):
            raise ValueError("explicit inactive defaults required for every conditional parameter")
        for name, value in defaults.items():
            p = conditional[name]
            if type(value) is not type(p.lower) or not p.lower <= value <= p.upper:
                raise ValueError("inactive default has wrong type or bounds")
        object.__setattr__(self, "inactive_defaults", MappingProxyType(defaults))

    def canonical(self, config):
        # The framework supplies active decisions only. Inactive values are
        # deterministic placeholders, never sampled scientific decisions.
        self.space.encode(config)
        return {p.name: config[p.name] if active(p, config) else self.inactive_defaults[p.name]
                for p in self.space.parameters}

    def scientific(self, config):
        result = {}
        for p in self.space.parameters:
            if active(p, config):
                result[p.name] = config[p.name]
            elif p.name in config and (
                type(config[p.name]) is not type(self.inactive_defaults[p.name])
                or config[p.name] != self.inactive_defaults[p.name]
            ):
                raise ValueError("noncanonical inactive decision")
        if set(config) - {p.name for p in self.space.parameters}:
            raise ValueError("unknown branch parameter")
        self.space.encode(result)
        return result

    def configuration_digest(self, config):
        return digest(self.canonical(self.scientific(config)))
