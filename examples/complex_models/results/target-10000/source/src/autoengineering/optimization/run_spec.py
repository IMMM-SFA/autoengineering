"""Strict public configuration and input provenance for optimization runs."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import importlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import sys
from types import MappingProxyType
from typing import Any

import yaml

from .space import SearchSpace
from .spec import StudySpec
from .yaml_utils import safe_load_unique

RUN_SPEC_SCHEMA_VERSION = "1.0"
_ENTRY_POINT = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*$"
)
_POLICY_OPTIONS = {
    "random": {},
    "sobol": {},
    "botorch": {
        "min_initial": 1,
        "num_restarts": 1,
        "raw_samples": 2,
        "max_categorical_assignments": 1,
        "candidate_retry_limit": 1,
    },
}


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_exact_keys(data: Mapping[str, Any], required: set[str], label: str) -> None:
    if not isinstance(data, Mapping):
        raise TypeError(f"{label} must be a mapping")
    if set(data) != required:
        raise ValueError(f"{label} keys must be exactly {sorted(required)}")


def _validate_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty relative path")
    if "\\" in value:
        raise ValueError(f"{label} must use forward slashes")
    path = PurePosixPath(value)
    windows_path = PureWindowsPath(value)
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or path.as_posix() != value
        or value == "."
        or ".." in path.parts
    ):
        raise ValueError(f"{label} must be a normalized relative path without parent traversal")
    return value


def _specification_file(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_symlink() or not candidate.is_file():
        raise ValueError("run specification must be a regular nonsymlink file")
    return candidate.resolve(strict=True)


def _resolve_declared_file(value: str, specification_path: Path, label: str) -> Path:
    declared = _validate_relative_path(value, label)
    base = specification_path.parent.resolve(strict=True)
    candidate = base / declared
    current = base
    for part in PurePosixPath(declared).parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"{label} must not contain a symlink")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"{label} does not exist: {declared}") from error
    if not resolved.is_relative_to(base):
        raise ValueError(f"{label} escapes the run specification directory")
    if not resolved.is_file():
        raise ValueError(f"{label} must be a regular file")
    return resolved


def _local_module_source(base: Path, module_name: str) -> tuple[Path, Path | None] | None:
    parts = module_name.split(".")
    current = base
    for part in parts:
        current /= part
        if current.is_symlink():
            raise ValueError("local evaluator module path must not contain a symlink")
    module_file = current.with_suffix(".py")
    package_file = current / "__init__.py"
    if module_file.is_symlink() or package_file.is_symlink():
        raise ValueError("local evaluator source must not be a symlink")
    candidates = [path for path in (module_file, package_file) if path.exists()]
    if len(candidates) > 1:
        raise ValueError("local evaluator module path is ambiguous")
    if not candidates:
        return None
    source = candidates[0]
    if not source.is_file():
        raise ValueError("local evaluator source must be a regular file")
    package_directory = current if source == package_file else None
    return source, package_directory


def _evict_local_module_roots(base: Path) -> None:
    roots = {
        child.stem
        for child in base.iterdir()
        if child.is_file() and child.suffix == ".py" and child.stem.isidentifier()
    }
    roots.update(
        child.name
        for child in base.iterdir()
        if child.is_dir() and child.name.isidentifier() and (child / "__init__.py").is_file()
    )
    for name in tuple(sys.modules):
        if any(name == root or name.startswith(f"{root}.") for root in roots):
            del sys.modules[name]


def _load_source_module(module_name: str, source: Path, package_directory: Path | None) -> object:
    root_name = module_name.split(".", 1)[0]
    for name in tuple(sys.modules):
        if name == root_name or name.startswith(f"{root_name}."):
            del sys.modules[name]
    parent_name = module_name.rpartition(".")[0]
    if parent_name:
        importlib.import_module(parent_name)
    locations = None if package_directory is None else [str(package_directory)]
    spec = importlib.util.spec_from_file_location(
        module_name,
        source,
        submodule_search_locations=locations,
    )
    if spec is None:
        raise ValueError(f"evaluator factory module cannot be loaded: {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        code = compile(source.read_bytes(), str(source), "exec")
        exec(code, module.__dict__)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


@dataclass(frozen=True)
class OptimizationRunSpec:
    """One immutable, serializable optimization invocation contract."""

    study: StudySpec
    search_space: SearchSpace
    policy: str
    policy_options: Mapping[str, int]
    evaluator_factory: str
    input_files: tuple[str, ...] = ()
    target_value: float | None = None
    max_new_evaluations: int | None = None
    schema_version: str = RUN_SPEC_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.study, StudySpec):
            raise TypeError("study must be a StudySpec")
        if not isinstance(self.search_space, SearchSpace):
            raise TypeError("search_space must be a SearchSpace")
        if self.policy not in _POLICY_OPTIONS:
            raise ValueError(f"unknown optimization policy: {self.policy!r}")
        if not isinstance(self.policy_options, Mapping):
            raise TypeError("policy_options must be a mapping")
        options = dict(self.policy_options)
        allowed = _POLICY_OPTIONS[self.policy]
        unknown = set(options) - set(allowed)
        if unknown:
            raise ValueError(f"unknown {self.policy} policy options: {sorted(unknown)}")
        for name, value in options.items():
            minimum = allowed[name]
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(f"policy option {name} must be an integer >= {minimum}")
        ordered_options = {name: options[name] for name in allowed if name in options}
        object.__setattr__(self, "policy_options", MappingProxyType(ordered_options))
        if not isinstance(self.evaluator_factory, str) or not _ENTRY_POINT.fullmatch(
            self.evaluator_factory
        ):
            raise ValueError("evaluator_factory must be a module:callable entry point")
        if isinstance(self.input_files, str) or not isinstance(self.input_files, (list, tuple)):
            raise TypeError("input_files must be a list or tuple of relative paths")
        input_files = tuple(
            _validate_relative_path(value, "declared input path") for value in self.input_files
        )
        if len(set(input_files)) != len(input_files):
            raise ValueError("declared input paths must be unique")
        object.__setattr__(self, "input_files", input_files)
        if self.target_value is not None:
            if (
                isinstance(self.target_value, bool)
                or not isinstance(self.target_value, (int, float))
                or not math.isfinite(self.target_value)
            ):
                raise ValueError("target_value must be a finite number or None")
            object.__setattr__(self, "target_value", float(self.target_value))
        if self.max_new_evaluations is not None and (
            isinstance(self.max_new_evaluations, bool)
            or not isinstance(self.max_new_evaluations, int)
            or self.max_new_evaluations < 0
        ):
            raise ValueError("max_new_evaluations must be a nonnegative integer or None")
        if self.schema_version != RUN_SPEC_SCHEMA_VERSION:
            raise ValueError("run specification schema version differs")

    def to_dict(self) -> dict[str, object]:
        """Return the ordered public representation of this run."""
        return {
            "schema_version": self.schema_version,
            "study": self.study.to_dict(),
            "search_space": self.search_space.to_dict(),
            "policy": self.policy,
            "policy_options": dict(self.policy_options),
            "evaluator_factory": self.evaluator_factory,
            "input_files": list(self.input_files),
            "target_value": self.target_value,
            "max_new_evaluations": self.max_new_evaluations,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OptimizationRunSpec":
        """Load a run from its strict public representation."""
        required = {
            "schema_version",
            "study",
            "search_space",
            "policy",
            "policy_options",
            "evaluator_factory",
            "input_files",
            "target_value",
            "max_new_evaluations",
        }
        _require_exact_keys(data, required, "optimization run specification")
        if not isinstance(data["study"], Mapping):
            raise TypeError("run study must be a mapping")
        if not isinstance(data["search_space"], Mapping):
            raise TypeError("run search_space must be a mapping")
        if not isinstance(data["policy_options"], Mapping):
            raise TypeError("run policy_options must be a mapping")
        if not isinstance(data["input_files"], list):
            raise TypeError("run input_files must be a list")
        return cls(
            study=StudySpec.from_dict(data["study"]),
            search_space=SearchSpace.from_dict(data["search_space"]),
            policy=data["policy"],
            policy_options=data["policy_options"],
            evaluator_factory=data["evaluator_factory"],
            input_files=tuple(data["input_files"]),
            target_value=data["target_value"],
            max_new_evaluations=data["max_new_evaluations"],
            schema_version=data["schema_version"],
        )

    @property
    def canonical_json(self) -> str:
        """Return a canonical semantic representation independent of YAML formatting."""
        return _canonical_json(self.to_dict())

    @property
    def sha256(self) -> str:
        """Hash the canonical semantic representation of this run."""
        return hashlib.sha256(self.canonical_json.encode("utf-8")).hexdigest()

    def to_yaml(self, path: str | Path) -> None:
        """Write this run as stable safe YAML."""
        Path(path).write_text(yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8")

    @classmethod
    def from_yaml(cls, path: str | Path) -> "OptimizationRunSpec":
        """Load and validate a run specification and all declared local inputs."""
        specification_path = _specification_file(path)
        data = safe_load_unique(specification_path.read_text(encoding="utf-8"))
        run = cls.from_dict(data)
        run.resolve_input_files(specification_path)
        run.load_evaluator_factory(specification_path)
        return run

    def resolve_input_files(self, specification_path: str | Path) -> dict[str, Path]:
        """Resolve declared inputs relative to a checked run specification file."""
        spec_path = _specification_file(specification_path)
        return {
            declared: _resolve_declared_file(declared, spec_path, f"declared input {declared!r}")
            for declared in self.input_files
        }

    def resolve_system_file(
        self,
        system_path: str | Path,
        specification_path: str | Path,
    ) -> Path:
        """Resolve a system YAML path relative to a checked run specification file."""
        spec_path = _specification_file(specification_path)
        raw_system = Path(system_path)
        if raw_system.is_absolute():
            if raw_system.is_symlink() or not raw_system.is_file():
                raise ValueError("system YAML must be a regular nonsymlink file")
            return raw_system.resolve(strict=True)
        declared_system = _validate_relative_path(str(system_path), "system YAML path")
        return _resolve_declared_file(declared_system, spec_path, "system YAML path")

    def load_evaluator_factory(self, specification_path: str | Path) -> Callable[..., object]:
        """Import the declared callable with the specification directory on `sys.path`."""
        factory, _ = self._load_evaluator_factory_and_source(specification_path)
        return factory

    def _load_evaluator_factory_and_source(
        self, specification_path: str | Path
    ) -> tuple[Callable[..., object], Path]:
        spec_path = _specification_file(specification_path)
        module_name, callable_name = self.evaluator_factory.split(":", 1)
        base = str(spec_path.parent)
        local_source = _local_module_source(spec_path.parent, module_name)
        if local_source is not None:
            _evict_local_module_roots(spec_path.parent)
        added = base not in sys.path
        if added:
            sys.path.insert(0, base)
        try:
            importlib.invalidate_caches()
            try:
                if local_source is None:
                    module = importlib.import_module(module_name)
                else:
                    module = _load_source_module(module_name, *local_source)
            except (ImportError, ModuleNotFoundError) as error:
                raise ValueError(
                    f"evaluator factory module cannot be imported: {module_name}"
                ) from error
        finally:
            if added:
                sys.path.remove(base)
        factory = getattr(module, callable_name, None)
        if not callable(factory):
            raise ValueError(f"evaluator factory is not callable: {self.evaluator_factory}")
        if local_source is not None:
            source_path = local_source[0]
        else:
            module_file = getattr(module, "__file__", None)
            if not isinstance(module_file, str):
                raise ValueError("evaluator entry-point module source file cannot be determined")
            source_path = Path(module_file)
            if source_path.suffix == ".pyc":
                try:
                    source_path = Path(importlib.util.source_from_cache(str(source_path)))
                except ValueError as error:
                    raise ValueError(
                        "evaluator entry-point module source file cannot be determined"
                    ) from error
        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError(
                "evaluator entry-point module source must be a regular nonsymlink file"
            )
        return factory, source_path.resolve(strict=True)

    def input_artifact_hashes(
        self,
        *,
        system_path: str | Path,
        specification_path: str | Path,
    ) -> dict[str, str]:
        """Hash only the system, run specification, evaluator source, and declared inputs."""
        spec_path = _specification_file(specification_path)
        recorded = type(self).from_dict(safe_load_unique(spec_path.read_text(encoding="utf-8")))
        if recorded != self:
            raise ValueError("run specification file differs from the in-memory run contract")
        raw_system = Path(system_path)
        resolved_system = self.resolve_system_file(raw_system, spec_path)
        system_label = (
            raw_system.name
            if raw_system.is_absolute()
            else _validate_relative_path(str(system_path), "system YAML path")
        )
        _, source_path = self._load_evaluator_factory_and_source(spec_path)
        hashes = {
            f"system:{system_label}": _sha256_file(resolved_system),
            f"run_spec:{spec_path.name}": _sha256_file(spec_path),
            f"evaluator:{self.evaluator_factory}": _sha256_file(source_path),
        }
        for declared, resolved in self.resolve_input_files(spec_path).items():
            hashes[f"input:{declared}"] = _sha256_file(resolved)
        return hashes
