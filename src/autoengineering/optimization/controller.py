"""Sequential, budgeted, crash-recoverable optimization study controller."""

from __future__ import annotations

from collections.abc import Callable, Mapping
import json
import math
import os
from pathlib import Path
import time

import numpy as np

from .backend import OptimizerBackend, SearchSpaceExhausted
from .ledger import ObservationLedger
from .provenance import (
    SCHEMA_VERSION,
    atomic_write_json,
    remove_artifact,
    search_space_dict,
    sha256_json,
    study_dict,
    write_study_artifacts,
)
from .records import (
    EvaluationAction,
    EvaluationResult,
    EvaluationScope,
    EvaluationStatus,
    Recommendation,
)
from .space import SearchSpace
from .spec import StudySpec

_PENDING_NAME = "pending-actions.json"


class StudyRecoveryError(RuntimeError):
    """Raised when durable study state cannot be reconciled without ambiguity."""


class StudyLockError(RuntimeError):
    """Raised when another controller process owns a study work directory."""


class _StudyLock:
    """Nonblocking per-study writer lock; controller lock precedes ledger lock."""

    def __init__(self, directory: Path) -> None:
        self.path = directory / ".study.lock"
        self.stream = None

    def __enter__(self) -> "_StudyLock":
        try:
            self.stream = self.path.open("a+b")
            if os.name == "nt":
                import msvcrt

                self.stream.seek(0, os.SEEK_END)
                if self.stream.tell() == 0:
                    self.stream.write(b"\0")
                    self.stream.flush()
                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, OSError) as error:
            if self.stream is not None:
                self.stream.close()
                self.stream = None
            raise StudyLockError(
                f"another writer owns study directory: {self.path.parent}"
            ) from error
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool:
        assert self.stream is not None
        try:
            if os.name == "nt":
                import msvcrt

                self.stream.seek(0)
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        finally:
            self.stream.close()
            self.stream = None
        return False


class OptimizationStudy:
    """One single-writer sequential optimizer with durable exactly-once recovery.

    Controller operations take the study lock before invoking the ledger, whose
    independent lock is always acquired second.  Release A intentionally rejects
    batches and never performs evaluator work concurrently.
    """

    def __init__(
        self,
        spec: StudySpec,
        space: SearchSpace,
        backend: OptimizerBackend,
        ledger: ObservationLedger,
        evaluator: Callable[[EvaluationAction], EvaluationResult],
        work_directory: str | Path,
        *,
        wall_clock: Callable[[], str] | None = None,
        monotonic_clock: Callable[[], float] | None = None,
        target_value: float | None = None,
        target_predicate: Callable[[Recommendation], bool] | None = None,
        input_artifact_hashes: Mapping[str, str] | None = None,
    ) -> None:
        if not isinstance(spec, StudySpec) or not isinstance(space, SearchSpace):
            raise TypeError("spec and space must be immutable StudySpec and SearchSpace instances")
        if not isinstance(ledger, ObservationLedger) or not isinstance(backend, OptimizerBackend):
            raise TypeError("backend and ledger must implement their public protocols")
        if not callable(evaluator):
            raise TypeError("evaluator must be callable")
        if target_value is not None:
            if isinstance(target_value, bool) or not isinstance(target_value, (int, float)):
                raise TypeError("target_value must be a finite number or None")
            if not math.isfinite(target_value):
                raise ValueError("target_value must be finite")
        if target_predicate is not None and not callable(target_predicate):
            raise TypeError("target_predicate must be callable or None")
        if target_predicate is not None and target_value is not None:
            raise ValueError("configure target_value or target_predicate, not both")
        hashes = {} if input_artifact_hashes is None else dict(input_artifact_hashes)
        if any(
            not isinstance(name, str) or not isinstance(value, str)
            for name, value in hashes.items()
        ):
            raise TypeError("input_artifact_hashes must map strings to strings")
        if any(
            len(value) != 64 or any(character not in "0123456789abcdef" for character in value)
            for value in hashes.values()
        ):
            raise ValueError("input artifact hash must be a lowercase SHA-256 digest")
        directory = Path(work_directory)
        directory.mkdir(parents=True, exist_ok=True)
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("work_directory must be a real directory")
        self.spec = spec
        self.space = space
        self.backend = backend
        self.ledger = ledger
        self.evaluator = evaluator
        self.work_directory = directory
        self.wall_clock = wall_clock or (lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        self.monotonic_clock = monotonic_clock or time.monotonic
        self.target_value = None if target_value is None else float(target_value)
        self.target_predicate = target_predicate
        self.input_artifact_hashes = hashes
        self.start_timestamp = self._load_start_timestamp() or self.wall_clock()
        self.stop_reason: str | None = None
        self._pending_lock: _StudyLock | None = None
        with self._lock():
            self._reconcile_pending()
            self._update_artifacts()

    def ask(self, n: int = 1) -> tuple[EvaluationAction, ...]:
        """Durably reserve one affordable action before any evaluator work begins."""
        if isinstance(n, bool) or not isinstance(n, int) or n != 1:
            raise ValueError("Release A is sequential: ask(n=1) is the only supported request")
        lock = self._lock()
        lock.__enter__()
        keep_lock = False
        try:
            if self._read_pending() is not None:
                raise RuntimeError("an unresolved pending action already exists")
            reason = self._stop_before_suggest()
            if reason is not None:
                self.stop_reason = reason
                self._update_artifacts(end=True)
                return ()
            started = self.monotonic_clock()
            try:
                actions = self.backend.suggest(self.ledger, n=1)
            except SearchSpaceExhausted:
                self.stop_reason = "finite_space_exhausted"
                self._update_artifacts(end=True)
                return ()
            elapsed = self.monotonic_clock() - started
            if len(actions) != 1 or not isinstance(actions[0], EvaluationAction):
                raise StudyRecoveryError("backend must return exactly one EvaluationAction")
            action = actions[0]
            if action.scope is not EvaluationScope.SYSTEM:
                raise ValueError("Release A controller accepts only system-scope actions")
            self.space.encode(action.config)
            self._write_pending(action, None, optimizer_seconds=max(0.0, elapsed))
            self._pending_lock = lock
            keep_lock = True
            return (action,)
        finally:
            if not keep_lock:
                lock.__exit__(None, None, None)

    def tell(self, action: EvaluationAction, result: EvaluationResult) -> None:
        """Commit exactly the persisted action/result pair in result-before-ledger order."""
        if not isinstance(action, EvaluationAction) or not isinstance(result, EvaluationResult):
            raise TypeError("tell requires EvaluationAction and EvaluationResult")
        if action.id != result.action_id:
            raise ValueError("action and result IDs must match")
        lock = self._pending_lock
        acquired_here = lock is None
        if lock is None:
            lock = self._lock()
            lock.__enter__()
        committed = False
        try:
            pending = self._read_pending()
            if pending is None:
                raise ValueError("no pending action matches tell request")
            expected, completed = pending
            if expected != action or (completed is not None and completed != result):
                raise ValueError("tell action/result does not exactly match pending action")
            existing = self._ledger_entry(action.id)
            if existing is not None:
                raise ValueError(f"duplicate action already in ledger: {action.id}")
            self._validate_result(result)
            if completed is None:
                self._write_pending(action, result)
            self.ledger.append(action, result)
            remove_artifact(self.work_directory, _PENDING_NAME)
            self._update_artifacts()
            committed = True
        finally:
            if acquired_here or committed:
                lock.__exit__(None, None, None)
                if self._pending_lock is lock:
                    self._pending_lock = None

    def run(self, *, max_new_evaluations: int | None = None) -> Recommendation:
        """Ask, evaluate, and tell sequentially until stopped or the call limit is met."""
        if max_new_evaluations is not None and (
            isinstance(max_new_evaluations, bool)
            or not isinstance(max_new_evaluations, int)
            or max_new_evaluations < 0
        ):
            raise ValueError("max_new_evaluations must be a nonnegative integer or None")
        completed = 0
        while max_new_evaluations is None or completed < max_new_evaluations:
            actions = self.ask()
            if not actions:
                break
            action = actions[0]
            started = self.monotonic_clock()
            try:
                result = self.evaluator(action)
                if not isinstance(result, EvaluationResult):
                    raise TypeError("evaluator must return EvaluationResult")
            except Exception as error:
                elapsed = max(0.0, self.monotonic_clock() - started)
                result = EvaluationResult.infrastructure_failure(
                    action.id,
                    f"evaluator exception: {type(error).__name__}: {error}",
                    cost=0.0,
                    cost_unit=self.spec.budget.cost_unit,
                    evaluator_seconds=elapsed,
                )
            self.tell(action, result)
            completed += 1
        with self._lock():
            if self.stop_reason is None and max_new_evaluations != 0:
                reason = self._stop_before_suggest(check_budget=False)
                if reason in {"max_cost", "max_evaluations", "target_attained"}:
                    self.stop_reason = reason
                    self._update_artifacts(end=True)
        return self.recommend()

    def recommend(self) -> Recommendation:
        """Return the backend's recommendation over the current durable ledger."""
        with self._lock():
            self._validate_ledger()
            return self.backend.recommend(self.ledger)

    def _lock(self) -> _StudyLock:
        return _StudyLock(self.work_directory)

    def _pending_path(self) -> Path:
        return self.work_directory / _PENDING_NAME

    def _load_start_timestamp(self) -> str | None:
        path = self.work_directory / "manifest.json"
        if not path.exists() or path.is_symlink():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            value = payload.get("start_timestamp")
            return value if isinstance(value, str) else None
        except (OSError, json.JSONDecodeError):
            return None

    def _read_pending(self) -> tuple[EvaluationAction, EvaluationResult | None] | None:
        path = self._pending_path()
        if not path.exists():
            return None
        if path.is_symlink():
            raise StudyRecoveryError("pending state is a symlink")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            required = {
                "schema_version",
                "action",
                "result",
                "study_sha256",
                "search_space_sha256",
                "backend",
                "metadata",
            }
            if not isinstance(data, dict) or set(data) != required:
                raise ValueError("pending state has invalid keys")
            if data["schema_version"] != SCHEMA_VERSION:
                raise ValueError("pending state schema version differs")
            if data["study_sha256"] != sha256_json(study_dict(self.spec)):
                raise ValueError("pending state study hash differs")
            if data["search_space_sha256"] != sha256_json(search_space_dict(self.space)):
                raise ValueError("pending state search-space hash differs")
            if data["backend"] != self.backend.name:
                raise ValueError("pending state backend differs")
            if not isinstance(data["metadata"], dict):
                raise ValueError("pending state metadata is invalid")
            action = EvaluationAction.from_dict(data["action"])
            result = None if data["result"] is None else EvaluationResult.from_dict(data["result"])
            if result is not None and action.id != result.action_id:
                raise ValueError("pending action and result IDs differ")
            return action, result
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise StudyRecoveryError(f"corrupt or incompatible pending state: {error}") from error

    def _write_pending(
        self,
        action: EvaluationAction,
        result: EvaluationResult | None,
        *,
        optimizer_seconds: float = 0.0,
    ) -> None:
        atomic_write_json(
            self.work_directory,
            _PENDING_NAME,
            {
                "schema_version": SCHEMA_VERSION,
                "action": action.to_dict(),
                "result": None if result is None else result.to_dict(),
                "study_sha256": sha256_json(study_dict(self.spec)),
                "search_space_sha256": sha256_json(search_space_dict(self.space)),
                "backend": self.backend.name,
                "metadata": {"optimizer_seconds": optimizer_seconds},
            },
        )

    def _reconcile_pending(self) -> None:
        pending = self._read_pending()
        if pending is None:
            return
        action, result = pending
        existing = self._ledger_entry(action.id)
        if existing is not None:
            if existing[0] != action or result is None or existing[1] != result:
                raise StudyRecoveryError("pending action ID conflicts with ledger entry")
            remove_artifact(self.work_directory, _PENDING_NAME)
            return
        if result is None:
            result = EvaluationResult.infrastructure_failure(
                action.id,
                "interrupted evaluation recovered before a result was persisted",
                cost=0.0,
                cost_unit=self.spec.budget.cost_unit,
            )
            self._write_pending(action, result)
        self._validate_result(result)
        self.ledger.append(action, result)
        remove_artifact(self.work_directory, _PENDING_NAME)

    def _ledger_entry(self, action_id: str) -> tuple[EvaluationAction, EvaluationResult] | None:
        for entry in self.ledger.entries():
            if entry[0].id == action_id:
                return entry
        return None

    def _validate_result(self, result: EvaluationResult) -> None:
        if result.cost_unit != self.spec.budget.cost_unit:
            raise ValueError("result cost_unit must match study budget cost_unit")

    def _validate_ledger(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        entries = self.ledger.entries()
        total = 0.0
        for _, result in entries:
            self._validate_result(result)
            total += result.cost
        if not math.isfinite(total) or total < 0:
            raise ValueError("ledger total evaluator cost must be finite and nonnegative")
        return entries

    def _cost_estimate(self) -> float:
        costs = [
            result.cost
            for action, result in self._validate_ledger()
            if action.scope is EvaluationScope.SYSTEM
            and result.status is EvaluationStatus.SUCCESS
            and result.cost > 0
        ]
        observed = 0.0 if not costs else float(np.quantile(costs, 0.9, method="linear"))
        return max(self.spec.budget.initial_cost_estimate, observed)

    def _target_attained(self, recommendation: Recommendation) -> bool:
        if not recommendation.feasible:
            return False
        if self.target_predicate is not None:
            value = self.target_predicate(recommendation)
            if not isinstance(value, bool):
                raise TypeError("target_predicate must return bool")
            return value
        if self.target_value is None:
            return False
        objective = recommendation.outcomes.get(self.spec.objective.outcome)
        if objective is None:
            return False
        return (
            objective >= self.target_value
            if self.spec.objective.direction == "maximize"
            else objective <= self.target_value
        )

    def _stop_before_suggest(self, *, check_budget: bool = True) -> str | None:
        entries = self._validate_ledger()
        total = sum(result.cost for _, result in entries)
        if total >= self.spec.budget.max_cost:
            return "max_cost"
        if (
            self.spec.budget.max_evaluations is not None
            and len(entries) >= self.spec.budget.max_evaluations
        ):
            return "max_evaluations"
        if self._target_attained(self.backend.recommend(self.ledger)):
            return "target_attained"
        if check_budget and self._cost_estimate() > self.spec.budget.max_cost - total:
            return "insufficient_remaining_budget"
        return None

    def _update_artifacts(self, *, end: bool = False) -> None:
        self._validate_ledger()
        diagnostics = self.backend.diagnostics(self.ledger)
        end_timestamp = self.wall_clock() if end else None
        write_study_artifacts(
            directory=self.work_directory,
            spec=self.spec,
            space=self.space,
            ledger=self.ledger,
            backend_name=self.backend.name,
            backend_state=self.backend.state_dict(),
            diagnostics=diagnostics,
            recommendation=self.backend.recommend(self.ledger),
            start_timestamp=self.start_timestamp,
            end_timestamp=end_timestamp,
            stop_reason=self.stop_reason,
            input_artifact_hashes=self.input_artifact_hashes,
            pending_count=0 if self._read_pending() is None else 1,
        )
