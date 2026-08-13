"""Canonical provenance and atomic artifacts for optimization studies."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
from typing import Any

from .ledger import ObservationLedger
from .records import BackendDiagnostics, Recommendation
from .space import CategoricalParameter, IntegerParameter, SearchSpace
from .spec import StudySpec

SCHEMA_VERSION = "1.0"


def canonical_json(value: Any) -> str:
    """Encode JSON data deterministically, rejecting non-finite values."""
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def sha256_json(value: Any) -> str:
    """Return the SHA-256 digest of canonical JSON data."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _typed_scalar(value: str | int | float | bool) -> dict[str, object]:
    if isinstance(value, bool):
        kind = "bool"
    elif isinstance(value, int):
        kind = "int"
    elif isinstance(value, float):
        kind = "float"
    else:
        kind = "str"
    return {"type": kind, "value": value}


def search_space_dict(space: SearchSpace) -> dict[str, object]:
    """Serialize typed dimensions without conflating equal Python scalar values."""
    if not isinstance(space, SearchSpace):
        raise TypeError("space must be a SearchSpace")
    parameters: list[dict[str, object]] = []
    for parameter in space.parameters:
        if isinstance(parameter, CategoricalParameter):
            parameters.append(
                {
                    "type": "categorical",
                    "name": parameter.name,
                    "categories": [_typed_scalar(value) for value in parameter.categories],
                    "active_when": [],
                }
            )
            continue
        conditions = [
            {"parameter": name, "values": [_typed_scalar(value) for value in values]}
            for name, values in parameter.active_when.items()
        ]
        parameters.append(
            {
                "type": "integer" if isinstance(parameter, IntegerParameter) else "continuous",
                "name": parameter.name,
                "lower": parameter.lower,
                "upper": parameter.upper,
                "scale": parameter.scale,
                "active_when": conditions,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "encoded_dimension": space.encoded_dimension,
        "parameters": parameters,
    }


def study_dict(spec: StudySpec) -> dict[str, object]:
    """Return the canonical immutable study contract."""
    if not isinstance(spec, StudySpec):
        raise TypeError("spec must be a StudySpec")
    return spec.to_dict()


def _safe_file(directory: Path, name: str) -> Path:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("study work directory must be a real directory")
    path = directory / name
    if path.exists() and path.is_symlink():
        raise ValueError(f"refusing to follow symlinked study artifact: {name}")
    return path


def _fsync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(directory: Path, name: str, value: Any) -> Path:
    """Atomically replace one compact JSON artifact in a checked study directory."""
    return atomic_write_text(directory, name, canonical_json(value) + "\n")


def atomic_write_text(directory: Path, name: str, text: str) -> Path:
    """Atomically replace one UTF-8 artifact and synchronize file and directory."""
    directory = Path(directory)
    path = _safe_file(directory, name)
    temporary = directory / f".{name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = None
            stream.write(text.encode("utf-8"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(directory)
    except BaseException:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    return path


def remove_artifact(directory: Path, name: str) -> None:
    """Durably remove a controller artifact without following symlinks."""
    path = _safe_file(directory, name)
    if path.exists():
        path.unlink()
        _fsync_directory(directory)


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def runtime_provenance() -> dict[str, object]:
    """Return bounded runtime details without collecting environment variables."""
    source = Path(__file__).resolve()
    root = next((parent for parent in source.parents if (parent / ".git").exists()), None)
    revision: str | None = None
    dirty: bool | None = None
    if root is not None:
        try:
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip()
            dirty = bool(
                subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()
            )
        except (OSError, subprocess.CalledProcessError):
            revision, dirty = None, None
    return {
        "package_version": _package_version("autoengineering"),
        "git_revision": revision,
        "git_dirty": dirty,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "botorch_version": _package_version("botorch"),
        "torch_version": _package_version("torch"),
        "gpytorch_version": _package_version("gpytorch"),
    }


def ledger_sha256(ledger: ObservationLedger) -> str:
    """Hash the exact ledger bytes, including the specified empty-ledger digest."""
    if not ledger.path.exists():
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(ledger.path.read_bytes()).hexdigest()


def write_study_artifacts(
    *,
    directory: Path,
    spec: StudySpec,
    space: SearchSpace,
    ledger: ObservationLedger,
    backend_name: str,
    backend_state: Mapping[str, object],
    diagnostics: BackendDiagnostics,
    recommendation: Recommendation,
    start_timestamp: str,
    end_timestamp: str | None,
    stop_reason: str | None,
    input_artifact_hashes: Mapping[str, str],
    pending_count: int,
) -> None:
    """Write the four replaceable study artifacts from one durable ledger snapshot."""
    spec_json = study_dict(spec)
    space_json = search_space_dict(space)
    entries = ledger.entries()
    total_cost = sum(result.cost for _, result in entries)
    evaluator_seconds = sum(result.evaluator_seconds for _, result in entries)
    result_optimizer_seconds = sum(result.optimizer_seconds for _, result in entries)
    state = dict(backend_state)
    snapshot = ledger_sha256(ledger)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "study": spec_json,
        "study_sha256": sha256_json(spec_json),
        "search_space": space_json,
        "search_space_sha256": sha256_json(space_json),
        **runtime_provenance(),
        "input_artifact_hashes": dict(input_artifact_hashes),
        "backend": backend_name,
        "seed": spec.seed,
        "start_timestamp": start_timestamp,
        "end_timestamp": end_timestamp,
        "stop_reason": stop_reason,
        "ledger_path": ledger.path.name,
        "ledger_sha256": snapshot,
        "total_evaluator_cost": total_cost,
        "optimizer_overhead_seconds": result_optimizer_seconds + diagnostics.optimizer_seconds,
        "total_evaluator_seconds": evaluator_seconds,
        "evaluation_count": len(entries),
        "status_counts": {
            status: sum(result.status.value == status for _, result in entries)
            for status in sorted({result.status.value for _, result in entries})
        },
        "pending_count": pending_count,
        "verification_commands": [
            "python -m pytest tests -q -p no:cacheprovider",
            "ruff check src tests",
        ],
    }
    backend_snapshot = {
        "schema_version": SCHEMA_VERSION,
        "backend": backend_name,
        "ledger_sha256": snapshot,
        "state": state,
    }
    report = _report(
        recommendation,
        entries,
        diagnostics,
        total_cost,
        result_optimizer_seconds + diagnostics.optimizer_seconds,
        evaluator_seconds,
        stop_reason,
        pending_count,
        manifest["study_sha256"],
        snapshot,
    )
    atomic_write_json(directory, "manifest.json", manifest)
    atomic_write_json(directory, "backend-state.json", backend_snapshot)
    atomic_write_json(directory, "recommendation.json", recommendation.to_dict())
    atomic_write_text(directory, "optimization-report.md", report)


def _report(
    recommendation: Recommendation,
    entries: tuple[tuple[object, object], ...],
    diagnostics: BackendDiagnostics,
    cost: float,
    optimizer_seconds: float,
    evaluator_seconds: float,
    stop_reason: str | None,
    pending_count: int,
    study_hash: str,
    ledger_hash: str,
) -> str:
    lines = ["# Optimization study", "", "## Recommendation", ""]
    lines.extend(
        [
            f"- Feasible: {recommendation.feasible}",
            f"- Action: {recommendation.action_id or 'none'}",
            f"- Configuration: {canonical_json(dict(recommendation.config))}",
            f"- Objective and constraint observations: {canonical_json(dict(recommendation.outcomes))}",
            f"- Message: {recommendation.message or 'none'}",
            "",
            "## Evidence",
            "",
        ]
    )
    matching = next(
        (result for action, result in entries if action.id == recommendation.action_id), None
    )
    standard_errors = {} if matching is None else dict(matching.standard_errors)
    lines.extend(
        [
            f"- Standard errors: {canonical_json(standard_errors)}",
            f"- Total evaluator cost: {cost}",
            f"- Evaluator seconds: {evaluator_seconds}",
            f"- Optimizer overhead seconds: {optimizer_seconds}",
            f"- Stop reason: {stop_reason or 'not_terminal'}",
            f"- Resume pending actions: {pending_count}",
            "",
            "## Diagnostics",
            "",
            f"- Fallback events: {canonical_json(list(diagnostics.fallback_reasons))}",
            f"- Warnings: {canonical_json(list(diagnostics.warnings))}",
            f"- Manifest study hash: {study_hash}",
            f"- Ledger hash: {ledger_hash}",
            "",
            "## Verification",
            "",
            "- `python -m pytest tests -q -p no:cacheprovider`",
            "- `ruff check src tests`",
            "",
        ]
    )
    return "\n".join(lines)
