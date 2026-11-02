"""Strict safe YAML loading for optimization configuration files."""

from __future__ import annotations

from typing import Any

import yaml


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """Safe loader that treats duplicate mapping keys as invalid input."""


def _construct_unique_mapping(
    loader: _UniqueKeySafeLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[object, object]:
    values: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in values
        except TypeError as error:
            raise ValueError("YAML mapping keys must be scalar") from error
        if duplicate:
            raise ValueError(f"duplicate YAML mapping key: {key!r}")
        values[key] = loader.construct_object(value_node, deep=deep)
    return values


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def safe_load_unique(text: str) -> Any:
    """Safely load YAML while rejecting duplicate keys at every nesting level."""
    return yaml.load(text, Loader=_UniqueKeySafeLoader)
