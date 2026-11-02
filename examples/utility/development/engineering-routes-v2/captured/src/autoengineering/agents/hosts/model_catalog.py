"""Explicit, bounded model metadata selected by the trusted qualifier."""

from __future__ import annotations

from pathlib import Path

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import unique_json


def validate_model_catalog(raw: bytes, model: str) -> bytes:
    """Accept one exact model. Never discover a cache or select a fallback."""
    if type(raw) is not bytes or not 0 < len(raw) <= 65536:
        raise ValueError("model catalog exceeds limit")
    value = unique_json(raw.decode())
    if (
        not isinstance(value, dict)
        or set(value) != {"models"}
        or not isinstance(value["models"], list)
        or len(value["models"]) != 1
        or not isinstance(value["models"][0], dict)
        or value["models"][0].get("slug") != model
    ):
        raise ValueError("model catalog must describe only the selected model")
    return raw


def read_model_catalog(path: Path, model: str) -> bytes:
    path = confined_file(path.parent, path.name)
    if path.stat().st_size > 65536:
        raise ValueError("model catalog exceeds limit")
    with path.open("rb") as stream:
        return validate_model_catalog(stream.read(65537), model)
