"""Explicit scalar/daily interface and model lifecycle contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

import numpy as np

from autoengineering.campaign.records import ArtifactRef, ModelSnapshot, PortContract, Scalar
from autoengineering.campaign.serialization import Record


@dataclass(frozen=True)
class PrepareContext(Record):
    model: ModelSnapshot
    parameters: Mapping[str, Scalar]
    seed: int
    scratch_path: str
    permitted_data_ids: tuple[str, ...]


@dataclass(frozen=True)
class TrainingResult(Record):
    status: str
    artifact: ArtifactRef | None
    cost: float | None

    def _validate(self):
        if self.status not in ("not_applicable", "trained"):
            raise ValueError("invalid training status")
        if self.status == "trained" and (self.artifact is None or self.cost is None):
            raise ValueError("training must record its artifact and cost")
        if self.cost is not None and self.cost < 0:
            raise ValueError("training cost cannot be negative")


class ModelAdapter(Protocol):
    """Only trusted factories implement this interface. Cleanup accepts a partial handle."""

    def prepare(self, context: PrepareContext) -> object: ...
    def validate(self, handle: object) -> None: ...
    def train(self, handle: object, fitting_data: Mapping[str, np.ndarray]) -> TrainingResult: ...
    def run(
        self, handle: object, forcing: Mapping[str, np.ndarray]
    ) -> Mapping[str, np.ndarray]: ...
    def inspect(
        self, handle: object, outputs: Mapping[str, np.ndarray]
    ) -> Mapping[str, np.ndarray]: ...
    def cleanup(self, handle: object | None) -> None: ...


def validate_arrays(
    arrays: Mapping[str, np.ndarray],
    declared: tuple[PortContract, ...],
    supplied: tuple[PortContract, ...],
) -> Mapping[str, np.ndarray]:
    """Validate metadata exactly and return isolated, read-only arrays.

    No conversion, date joining, feature reordering or broadcasting is implicit.
    """
    if declared != supplied:
        raise ValueError("port names, units, coordinates, grids or time support differ")
    if set(arrays) != {port.name for port in declared}:
        raise ValueError("missing or extra arrays")
    copied = {}
    for port in declared:
        array = np.asarray(arrays[port.name])
        expected = () if port.time is None else (len(port.time.dates),)
        kinds = {"float": "f", "integer": "iu", "numeric": "fiu"}[port.dtype_family]
        if array.shape != expected or array.dtype.kind not in kinds:
            raise ValueError("array shape or dtype differs from port contract")
        if not np.isfinite(array).all():
            raise ValueError("array has nonfinite or missing values")
        array = array.copy()
        array.setflags(write=False)
        copied[port.name] = array
    return MappingProxyType(copied)


@dataclass(frozen=True)
class AdapterRegistration:
    id: str
    version: str
    factory: object
    sources: tuple[str, ...]
    source_root: Path | None = None


class AdapterRegistry:
    """Application-owned factories. Requests cannot register executable content."""

    def __init__(self, registrations: tuple[AdapterRegistration, ...]):
        self._entries = {entry.id: entry for entry in registrations}
        if len(self._entries) != len(registrations):
            raise ValueError("duplicate adapter registration")
        for entry in registrations:
            if not callable(entry.factory) or not entry.sources:
                raise ValueError(
                    "adapter requires a trusted factory and declared dependency closure"
                )

    def validate(self, adapter_id: str, model: ModelSnapshot, root: Path) -> None:
        entry = self._entries.get(adapter_id)
        if entry is None:
            raise ValueError("adapter is not registered")
        declared = {ref.path: ref for ref in model.source_bundle}
        if not set(entry.sources) <= set(declared):
            raise ValueError("adapter dependency closure is incomplete")
        from autoengineering.campaign.artifacts import read_bytes

        for path in entry.sources:
            read_bytes(root, declared[path])
            if entry.source_root is not None:
                read_bytes(entry.source_root, declared[path])

    def create(self, adapter_id: str) -> ModelAdapter:
        if adapter_id not in self._entries:
            raise ValueError("adapter is not registered")
        entry = self._entries[adapter_id]
        adapter = entry.factory()
        if entry.source_root is not None:
            import sys

            for path in entry.sources:
                parts = list(Path(path).with_suffix("").parts)
                if parts[-1] == "__init__":
                    parts.pop()
                module = sys.modules.get(".".join(parts))
                actual = getattr(module, "__file__", None)
                if actual is None or Path(actual).resolve() != (entry.source_root / path).resolve():
                    raise ValueError("loaded adapter source differs from its registered location")
        return adapter
