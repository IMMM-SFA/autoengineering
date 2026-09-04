"""Canonical provenance and atomic artifacts for optimization studies."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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

SCHEMA_VERSION = "2.0"


def canonical_json(value: Any) -> str:
    """Encode JSON data deterministically, rejecting non-finite values."""
    return json.dumps(
        value, allow_nan=False, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def sha256_json(value: Any) -> str:
    """Return the SHA-256 digest of canonical JSON data."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


@dataclass(frozen=True)
class RunIdentity:
    """Immutable canonical identity for one committed study ledger snapshot."""

    _study_json: str
    _search_space_json: str
    _backend_json: str
    ledger_path: str
    committed_ledger_sha256: str
    input_artifact_hashes: tuple[tuple[str, str], ...]
    seed: int
    start_timestamp: str

    @classmethod
    def create(
        cls,
        *,
        spec: StudySpec,
        space: SearchSpace,
        backend_name: str,
        backend_configuration: Mapping[str, object],
        ledger_path: str,
        committed_ledger_sha256: str,
        input_artifact_hashes: Mapping[str, str],
        start_timestamp: str,
    ) -> "RunIdentity":
        """Build an identity after validating each canonical field."""
        payload = {
            "schema_version": SCHEMA_VERSION,
            "study": study_dict(spec),
            "study_sha256": sha256_json(study_dict(spec)),
            "search_space": search_space_dict(space),
            "search_space_sha256": sha256_json(search_space_dict(space)),
            "backend": {
                "name": backend_name,
                "configuration": dict(backend_configuration),
                "configuration_sha256": sha256_json(dict(backend_configuration)),
            },
            "ledger": {
                "path": ledger_path,
                "committed_sha256": committed_ledger_sha256,
            },
            "input_artifact_hashes": dict(input_artifact_hashes),
            "seed": spec.seed,
            "start_timestamp": start_timestamp,
        }
        return cls.from_dict(payload)

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "RunIdentity":
        """Validate and freeze a serialized run identity."""
        required = {
            "schema_version",
            "study",
            "study_sha256",
            "search_space",
            "search_space_sha256",
            "backend",
            "ledger",
            "input_artifact_hashes",
            "seed",
            "start_timestamp",
        }
        if not isinstance(data, Mapping) or set(data) != required:
            raise ValueError("run identity has invalid keys")
        if data["schema_version"] != SCHEMA_VERSION:
            raise ValueError("run identity schema version differs")
        study = data["study"]
        search_space = data["search_space"]
        backend = data["backend"]
        ledger = data["ledger"]
        input_hashes = data["input_artifact_hashes"]
        if not all(
            isinstance(value, Mapping)
            for value in (study, search_space, backend, ledger, input_hashes)
        ):
            raise TypeError("run identity object fields must be mappings")
        if sha256_json(study) != data["study_sha256"]:
            raise ValueError("run identity study hash differs")
        if sha256_json(search_space) != data["search_space_sha256"]:
            raise ValueError("run identity search-space hash differs")
        if set(backend) != {"name", "configuration", "configuration_sha256"}:
            raise ValueError("run identity backend has invalid keys")
        if not isinstance(backend["name"], str) or not backend["name"].strip():
            raise ValueError("run identity backend name is invalid")
        if not isinstance(backend["configuration"], Mapping):
            raise TypeError("run identity backend configuration must be a mapping")
        if sha256_json(backend["configuration"]) != backend["configuration_sha256"]:
            raise ValueError("run identity backend configuration hash differs")
        if set(ledger) != {"path", "committed_sha256"}:
            raise ValueError("run identity ledger has invalid keys")
        if (
            not isinstance(ledger["path"], str)
            or not ledger["path"].strip()
            or Path(ledger["path"]).name != ledger["path"]
        ):
            raise ValueError("run identity ledger path is invalid")
        if not _is_sha256(ledger["committed_sha256"]):
            raise ValueError("run identity committed ledger hash is invalid")
        if any(
            not isinstance(name, str) or not name or not _is_sha256(digest)
            for name, digest in input_hashes.items()
        ):
            raise ValueError("run identity input artifact hashes are invalid")
        if isinstance(data["seed"], bool) or not isinstance(data["seed"], int):
            raise ValueError("run identity seed must be an integer")
        if data["seed"] != study.get("seed"):
            raise ValueError("run identity seed differs from the study")
        if not isinstance(data["start_timestamp"], str) or not data["start_timestamp"].strip():
            raise ValueError("run identity start timestamp is invalid")
        return cls(
            _study_json=canonical_json(study),
            _search_space_json=canonical_json(search_space),
            _backend_json=canonical_json(backend),
            ledger_path=ledger["path"],
            committed_ledger_sha256=ledger["committed_sha256"],
            input_artifact_hashes=tuple(sorted(input_hashes.items())),
            seed=data["seed"],
            start_timestamp=data["start_timestamp"],
        )

    def to_dict(self) -> dict[str, object]:
        """Return the canonical JSON-compatible identity representation."""
        study = json.loads(self._study_json)
        search_space = json.loads(self._search_space_json)
        backend = json.loads(self._backend_json)
        return {
            "schema_version": SCHEMA_VERSION,
            "study": study,
            "study_sha256": sha256_json(study),
            "search_space": search_space,
            "search_space_sha256": sha256_json(search_space),
            "backend": backend,
            "ledger": {
                "path": self.ledger_path,
                "committed_sha256": self.committed_ledger_sha256,
            },
            "input_artifact_hashes": dict(self.input_artifact_hashes),
            "seed": self.seed,
            "start_timestamp": self.start_timestamp,
        }

    @property
    def sha256(self) -> str:
        """Return the canonical digest of this committed identity."""
        return sha256_json(self.to_dict())


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


def read_json_artifact(directory: Path, name: str) -> dict[str, object]:
    """Read one required nonsymlink JSON object without changing study state."""
    path = _safe_file(Path(directory), name)
    if not path.is_file():
        raise ValueError(f"required study artifact is missing: {name}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"study artifact is malformed: {name}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"study artifact must contain a JSON object: {name}")
    return value


def artifact_sha256(path: Path) -> str:
    """Hash the exact bytes of one regular nonsymlink artifact."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required study artifact is missing or symlinked: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    ledger: ObservationLedger,
    run_identity: RunIdentity,
    backend_name: str,
    backend_state: Mapping[str, object],
    diagnostics: BackendDiagnostics,
    recommendation: Recommendation,
    end_timestamp: str | None,
    stop_reason: str | None,
    committed_pending_sha256: str | None,
    committed_control_sha256: str | None,
    committed_bootstrap_sha256: str | None,
) -> None:
    """Write replaceable artifacts first and atomically commit the manifest last."""
    entries, ledger_bytes = ledger.snapshot()
    total_cost = sum(result.cost for _, result in entries)
    evaluator_seconds = sum(result.evaluator_seconds for _, result in entries)
    result_optimizer_seconds = sum(result.optimizer_seconds for _, result in entries)
    state = dict(backend_state)
    snapshot = hashlib.sha256(ledger_bytes).hexdigest()
    if snapshot != run_identity.committed_ledger_sha256:
        raise ValueError("run identity does not match the ledger snapshot")
    if backend_name != json.loads(run_identity._backend_json)["name"]:
        raise ValueError("run identity does not match the backend name")
    identity_json = run_identity.to_dict()
    identity_hash = run_identity.sha256
    backend_snapshot = {
        "schema_version": SCHEMA_VERSION,
        "backend": backend_name,
        "run_identity_sha256": identity_hash,
        "ledger_sha256": snapshot,
        "state": state,
    }
    recommendation_json = recommendation.to_dict()
    report = _report(
        recommendation,
        entries,
        diagnostics,
        total_cost,
        result_optimizer_seconds + diagnostics.optimizer_seconds,
        evaluator_seconds,
        stop_reason,
        0,
        identity_json["study_sha256"],
        snapshot,
    )
    backend_text = canonical_json(backend_snapshot) + "\n"
    recommendation_text = canonical_json(recommendation_json) + "\n"
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_identity": identity_json,
        "run_identity_sha256": identity_hash,
        "runtime": runtime_provenance(),
        "end_timestamp": end_timestamp,
        "stop_reason": stop_reason,
        "total_evaluator_cost": total_cost,
        "optimizer_overhead_seconds": result_optimizer_seconds + diagnostics.optimizer_seconds,
        "total_evaluator_seconds": evaluator_seconds,
        "evaluation_count": len(entries),
        "status_counts": {
            status: sum(result.status.value == status for _, result in entries)
            for status in sorted({result.status.value for _, result in entries})
        },
        "pending_count": 0,
        "committed_pending_sha256": committed_pending_sha256,
        "committed_control_sha256": committed_control_sha256,
        "committed_bootstrap_sha256": committed_bootstrap_sha256,
        "artifact_sha256": {
            "backend-state.json": hashlib.sha256(backend_text.encode("utf-8")).hexdigest(),
            "recommendation.json": hashlib.sha256(recommendation_text.encode("utf-8")).hexdigest(),
            "optimization-report.md": hashlib.sha256(report.encode("utf-8")).hexdigest(),
        },
        "verification_commands": [
            "python -m pytest tests -q -p no:cacheprovider",
            "ruff check src tests",
        ],
    }
    atomic_write_json(directory, "backend-state.json", backend_snapshot)
    atomic_write_json(directory, "recommendation.json", recommendation_json)
    atomic_write_text(directory, "optimization-report.md", report)
    atomic_write_json(directory, "manifest.json", manifest)


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
