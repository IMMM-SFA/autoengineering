"""Construction and summary helpers for the public optimization command."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
import shutil
import tempfile
from typing import TYPE_CHECKING

from .backend import OptimizerBackend, RandomBackend, SobolBackend
from .controller import OptimizationStudy
from .ledger import ObservationLedger
from .records import EvaluationAction, EvaluationResult
from .run_spec import OptimizationRunSpec

if TYPE_CHECKING:
    from autoengineering.system.graph import System

_RESUME_MARKERS = ("manifest.json", "pending-bootstrap.json")
_RESUME_REQUIRED = ("observations.jsonl",)


def _reject_symlink_components(path: Path) -> None:
    candidate = path if path.is_absolute() else Path.cwd() / path
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current /= part
        if current.is_symlink():
            raise ValueError(
                f"optimization work directory path must not contain a symlink: {current}"
            )


def build_backend(run: OptimizationRunSpec) -> OptimizerBackend:
    """Construct the configured policy without importing optional modules eagerly."""
    if run.study.backend != "system":
        raise ValueError("Release A optimize supports only the system study backend")
    if run.policy == "random":
        return RandomBackend(run.study, run.search_space)
    if run.policy == "sobol":
        return SobolBackend(run.study, run.search_space)
    if run.policy == "botorch":
        try:
            from .system_backend import SystemBayesBackend
        except ImportError as error:
            raise ImportError(
                "the botorch policy requires optional Bayesian dependencies; "
                "run this command with 'pixi run -e bayes autoengineering optimize'"
            ) from error
        return SystemBayesBackend(
            run.study,
            run.search_space,
            **dict(run.policy_options),
        )
    raise ValueError(f"unknown optimization policy: {run.policy!r}")


def validate_work_directory(path: str | Path, *, resume: bool) -> Path:
    """Validate explicit new or resume intent without creating the destination."""
    directory = Path(path)
    _reject_symlink_components(directory)
    if not directory.exists():
        if resume:
            raise ValueError("resume requires an existing optimization work directory")
        return directory
    if not directory.is_dir():
        raise ValueError("optimization work directory must be a directory")
    entries = tuple(directory.iterdir())
    if not resume:
        if entries:
            raise ValueError(
                "optimization work directory is not empty; pass --resume for existing state"
            )
        return directory
    marker_paths = tuple(directory / marker for marker in _RESUME_MARKERS)
    if not any(path.exists() or path.is_symlink() for path in marker_paths):
        raise ValueError("resume requires recognizable optimization study state")
    required_paths = tuple(directory / name for name in _RESUME_REQUIRED)
    for artifact in (*marker_paths, *required_paths):
        if artifact.is_symlink():
            raise ValueError(f"resume artifact must not be a symlink: {artifact.name}")
    for artifact in required_paths:
        if not artifact.is_file():
            raise ValueError(f"resume requires regular study artifact: {artifact.name}")
    for lock_name in (".study.lock", "observations.jsonl.lock"):
        lock_path = directory / lock_name
        if lock_path.is_symlink() or (lock_path.exists() and not lock_path.is_file()):
            raise ValueError(
                f"resume lock path must be a regular nonsymlink file when present: {lock_name}"
            )
    if not any(path.is_file() for path in marker_paths):
        raise ValueError("resume requires a regular manifest or bootstrap transition")
    return directory


def execute_optimization(
    run: OptimizationRunSpec,
    system: System,
    evaluator_factory: Callable[[System], object],
    *,
    system_path: str | Path,
    specification_path: str | Path,
    work_directory: str | Path,
    resume: bool,
    max_new_evaluations: int | None,
) -> dict[str, object]:
    """Run one validated CLI invocation and return a JSON-compatible summary."""
    evaluator = evaluator_factory(system)
    if not callable(evaluator):
        raise TypeError("evaluator factory must return a callable")
    input_hashes = run.input_artifact_hashes(
        system_path=system_path,
        specification_path=specification_path,
    )
    backend = build_backend(run)
    directory = validate_work_directory(work_directory, resume=resume)
    if resume and not all(
        (directory / name).is_file() for name in (".study.lock", "observations.jsonl.lock")
    ):
        _validate_resume_copy(run, evaluator, directory, input_hashes)
    ledger = ObservationLedger(directory / "observations.jsonl")
    study = OptimizationStudy(
        run.study,
        run.search_space,
        backend,
        ledger,
        evaluator,
        directory,
        target_value=run.target_value,
        input_artifact_hashes=input_hashes,
    )
    limit = run.max_new_evaluations if max_new_evaluations is None else max_new_evaluations
    run_result = study.run_result(max_new_evaluations=limit)
    entries = run_result.entries
    counts = Counter(observation.status.value for _, observation in entries)
    return {
        "work_directory": str(directory.resolve()),
        "state": run_result.stop_reason or "invocation_limit",
        "evaluation_count": len(entries),
        "new_evaluation_count": run_result.new_evaluation_count,
        "total_evaluator_cost": sum(result.cost for _, result in entries),
        "cost_unit": run.study.budget.cost_unit,
        "status_counts": dict(sorted(counts.items())),
        "recommendation": run_result.recommendation.to_dict(),
    }


def _validate_resume_copy(
    run: OptimizationRunSpec,
    evaluator: Callable[[EvaluationAction], EvaluationResult],
    directory: Path,
    input_hashes: dict[str, str],
) -> None:
    """Validate lock recreation against a disposable copy before touching durable state."""
    with tempfile.TemporaryDirectory(prefix="autoengineering-resume-") as temporary:
        clone = Path(temporary) / "study"
        shutil.copytree(directory, clone, symlinks=True)
        OptimizationStudy(
            run.study,
            run.search_space,
            build_backend(run),
            ObservationLedger(clone / "observations.jsonl"),
            evaluator,
            clone,
            target_value=run.target_value,
            input_artifact_hashes=input_hashes,
        )
