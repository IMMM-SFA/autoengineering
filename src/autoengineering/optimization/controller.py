"""Sequential, budgeted, crash-recoverable optimization study controller."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import time

import numpy as np

from .backend import OptimizerBackend, SearchSpaceExhausted
from .ledger import ObservationLedger
from .provenance import (
    RunIdentity,
    SCHEMA_VERSION,
    artifact_sha256,
    atomic_write_json,
    canonical_json,
    ledger_sha256,
    read_json_artifact,
    remove_artifact,
    sha256_json,
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
_PENDING_CONTROL_NAME = "pending-control.json"
_PENDING_BOOTSTRAP_NAME = "pending-bootstrap.json"
_MANIFEST_NAME = "manifest.json"
_REPLACEABLE_NAMES = (
    "backend-state.json",
    "recommendation.json",
    "optimization-report.md",
)
_RESERVED_STUDY_NAMES = {
    _PENDING_NAME,
    _PENDING_CONTROL_NAME,
    _PENDING_BOOTSTRAP_NAME,
    _MANIFEST_NAME,
    *_REPLACEABLE_NAMES,
    ".study.lock",
}
_TERMINAL_REASONS = {
    "finite_space_exhausted",
    "insufficient_remaining_budget",
    "max_cost",
    "max_evaluations",
    "target_attained",
}


@dataclass(frozen=True)
class _PendingTransition:
    """One exact transition from a committed run identity."""

    run_identity_sha256: str
    committed_ledger_sha256: str
    original_start_timestamp: str
    action: EvaluationAction
    result: EvaluationResult | None
    optimizer_seconds: float

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_identity_sha256": self.run_identity_sha256,
            "committed_ledger_sha256": self.committed_ledger_sha256,
            "original_start_timestamp": self.original_start_timestamp,
            "action": self.action.to_dict(),
            "result": None if self.result is None else self.result.to_dict(),
            "metadata": {"optimizer_seconds": self.optimizer_seconds},
        }

    @property
    def sha256(self) -> str:
        return sha256_json(self.to_dict())


@dataclass(frozen=True)
class _PendingControlTransition:
    """One terminal metadata transition from a committed run identity."""

    run_identity_sha256: str
    committed_ledger_sha256: str
    original_start_timestamp: str
    stop_reason: str
    end_timestamp: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_identity_sha256": self.run_identity_sha256,
            "committed_ledger_sha256": self.committed_ledger_sha256,
            "original_start_timestamp": self.original_start_timestamp,
            "stop_reason": self.stop_reason,
            "end_timestamp": self.end_timestamp,
        }

    @property
    def sha256(self) -> str:
        return sha256_json(self.to_dict())


@dataclass(frozen=True)
class _PendingBootstrapTransition:
    """One initial artifact commit for an empty durable ledger."""

    run_identity_sha256: str
    committed_ledger_sha256: str
    original_start_timestamp: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": SCHEMA_VERSION,
            "run_identity_sha256": self.run_identity_sha256,
            "committed_ledger_sha256": self.committed_ledger_sha256,
            "original_start_timestamp": self.original_start_timestamp,
        }

    @property
    def sha256(self) -> str:
        return sha256_json(self.to_dict())


class _LedgerReplay:
    """Read-only committed ledger view used to replay a durable suggestion."""

    def __init__(
        self,
        entries: tuple[tuple[EvaluationAction, EvaluationResult], ...],
        contents: bytes,
    ) -> None:
        self._entries = entries
        self._contents = contents

    def entries(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        return self._entries

    record_bytes = staticmethod(ObservationLedger.record_bytes)

    def snapshot(self) -> tuple[tuple[tuple[EvaluationAction, EvaluationResult], ...], bytes]:
        return self._entries, self._contents

    def scientific_training_entries(
        self,
    ) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        statuses = {EvaluationStatus.SUCCESS, EvaluationStatus.SCIENTIFIC_INFEASIBLE}
        return tuple(entry for entry in self._entries if entry[1].status in statuses)

    def constraint_training_entries(
        self,
    ) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        return self.scientific_training_entries()

    def objective_training_entries(
        self,
    ) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        return tuple(
            entry for entry in self._entries if entry[1].status is EvaluationStatus.SUCCESS
        )


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
        if backend.spec != spec or backend.space != space:
            raise ValueError("backend spec and search space must match the controller")
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
        ledger_path = ledger.path
        if (
            ledger_path.name in _RESERVED_STUDY_NAMES
            or f"{ledger_path.name}.lock" in _RESERVED_STUDY_NAMES
        ):
            raise StudyRecoveryError("ledger path uses a reserved study control filename")
        if directory.is_symlink():
            raise ValueError("work_directory must be a real directory")
        if ledger_path.is_symlink():
            raise StudyRecoveryError("ledger path must not be a symlink")
        if ledger_path.exists() and not ledger_path.is_file():
            raise StudyRecoveryError("ledger path must be a regular file")
        if ledger_path.parent.resolve() != directory.resolve():
            raise StudyRecoveryError("ledger path must be inside the study directory")
        if not directory.exists():
            directory.mkdir(parents=True)
        if not directory.is_dir():
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
        self.start_timestamp = ""
        self.end_timestamp: str | None = None
        self.stop_reason: str | None = None
        self.run_identity: RunIdentity | None = None
        self._pending_lock: _StudyLock | None = None
        self._validate_ledger_path()
        with self._lock():
            self._initialize_or_recover()

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
            if self._read_control_pending() is not None:
                raise RuntimeError("an unresolved pending control transition already exists")
            if self._read_bootstrap_pending() is not None:
                raise RuntimeError("an unresolved pending bootstrap transition already exists")
            self._assert_committed_ledger()
            if self.stop_reason is not None:
                return ()
            reason = self._stop_before_suggest()
            if reason is not None:
                self._commit_terminal(reason)
                return ()
            started = self.monotonic_clock()
            try:
                actions = self.backend.suggest(self.ledger, n=1)
            except SearchSpaceExhausted:
                self._commit_terminal("finite_space_exhausted")
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
            assert self.run_identity is not None
            self._validate_pending_source(pending, self.run_identity)
            if pending.action != action or (
                pending.result is not None and pending.result != result
            ):
                raise ValueError("tell action/result does not exactly match pending action")
            existing = self._ledger_entry(action.id)
            if existing is not None:
                if (
                    existing != (action, result)
                    or pending.result is None
                    or not self._is_exact_pending_extension(self._ledger_bytes(), pending)
                ):
                    raise ValueError(f"duplicate action conflicts with pending state: {action.id}")
                self._update_artifacts(committed_pending_sha256=pending.sha256)
                remove_artifact(self.work_directory, _PENDING_NAME)
                committed = True
                return
            self._assert_committed_ledger(allow_pending=True)
            self._validate_result(result)
            if pending.result is None:
                pending = self._write_pending(
                    action,
                    result,
                    optimizer_seconds=pending.optimizer_seconds,
                )
            self.ledger.append(action, result)
            self._update_artifacts(committed_pending_sha256=pending.sha256)
            remove_artifact(self.work_directory, _PENDING_NAME)
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
                    self._commit_terminal(reason)
        return self.recommend()

    def recommend(self) -> Recommendation:
        """Return the backend's recommendation over the current durable ledger."""
        with self._lock():
            self._assert_committed_ledger(allow_pending=True)
            self._validate_ledger()
            return self.backend.recommend(self.ledger)

    def _lock(self) -> _StudyLock:
        return _StudyLock(self.work_directory)

    def _pending_path(self) -> Path:
        return self.work_directory / _PENDING_NAME

    def _control_pending_path(self) -> Path:
        return self.work_directory / _PENDING_CONTROL_NAME

    def _bootstrap_pending_path(self) -> Path:
        return self.work_directory / _PENDING_BOOTSTRAP_NAME

    def _validate_ledger_path(self) -> None:
        ledger_path = self.ledger.path
        if ledger_path.is_symlink():
            raise StudyRecoveryError("ledger path must not be a symlink")
        if ledger_path.exists() and not ledger_path.is_file():
            raise StudyRecoveryError("ledger path must be a regular file")
        try:
            directory = self.work_directory.resolve(strict=True)
            ledger_parent = ledger_path.parent.resolve(strict=True)
        except OSError as error:
            raise StudyRecoveryError(f"ledger path cannot be resolved: {error}") from error
        if ledger_parent != directory or ledger_path.name in {"", ".", ".."}:
            raise StudyRecoveryError("ledger path must be inside the study directory")
        if (
            ledger_path.name in _RESERVED_STUDY_NAMES
            or f"{ledger_path.name}.lock" in _RESERVED_STUDY_NAMES
        ):
            raise StudyRecoveryError("ledger path uses a reserved study control filename")

    def _initialize_or_recover(self) -> None:
        manifest_present = self._artifact_present(_MANIFEST_NAME)
        if manifest_present and not self.ledger.path.exists():
            raise StudyRecoveryError("the ledger recorded by the manifest is missing")
        other_control_present = any(
            self._artifact_present(name)
            for name in (*_REPLACEABLE_NAMES, _PENDING_NAME, _PENDING_CONTROL_NAME)
        )
        bootstrap_pending = self._read_bootstrap_pending()
        entries, ledger_bytes = self._read_ledger_snapshot()
        if not manifest_present:
            if bootstrap_pending is not None:
                if self._artifact_present(_PENDING_NAME) or self._artifact_present(
                    _PENDING_CONTROL_NAME
                ):
                    raise StudyRecoveryError(
                        "bootstrap and later study transitions cannot both be pending"
                    )
                if ledger_bytes or entries:
                    raise StudyRecoveryError("bootstrap transition requires an empty ledger")
                self.ledger.initialize()
                self._recover_bootstrap_transition(bootstrap_pending)
                return
            if other_control_present:
                raise StudyRecoveryError("study control artifacts exist without a manifest")
            if ledger_bytes or entries:
                raise StudyRecoveryError("a nonempty ledger cannot be adopted without a manifest")
            self.ledger.initialize()
            ledger_bytes = self._ledger_bytes()
            self.start_timestamp = self.wall_clock()
            self.run_identity = self._make_identity(hashlib.sha256(ledger_bytes).hexdigest())
            bootstrap_pending = self._write_bootstrap_pending()
            self._update_artifacts(committed_bootstrap_sha256=bootstrap_pending.sha256)
            remove_artifact(self.work_directory, _PENDING_BOOTSTRAP_NAME)
            return

        manifest, identity = self._read_manifest()
        self._validate_invocation(identity)
        self.run_identity = identity
        self.start_timestamp = identity.start_timestamp
        self.stop_reason = manifest["stop_reason"]
        self.end_timestamp = manifest["end_timestamp"]
        pending = self._read_pending()
        control_pending = self._read_control_pending()
        active_transitions = sum(
            item is not None for item in (pending, control_pending, bootstrap_pending)
        )
        if active_transitions > 1:
            raise StudyRecoveryError("multiple study transitions cannot be pending")
        current_hash = hashlib.sha256(ledger_bytes).hexdigest()
        committed_hash = identity.committed_ledger_sha256

        if bootstrap_pending is not None:
            self._recover_committed_bootstrap_residue(
                manifest,
                identity,
                bootstrap_pending,
                entries,
                current_hash,
                committed_hash,
            )
            return

        if control_pending is not None:
            self._recover_control_transition(
                manifest,
                identity,
                control_pending,
                entries,
                current_hash,
                committed_hash,
            )
            return

        if pending is None:
            if current_hash != committed_hash:
                raise StudyRecoveryError("ledger differs from the committed manifest")
            self._validate_manifest_metrics(manifest, entries)
            self._validate_replaceable_artifacts(manifest, identity, allow_transition=False)
            return

        if current_hash == committed_hash and self._is_committed_pending_residue(
            manifest, pending, ledger_bytes
        ):
            if not entries:
                raise StudyRecoveryError("committed pending residue has no ledger observation")
            self._validate_pending_action(
                pending,
                entries[:-1],
                self._committed_bytes_before_pending(ledger_bytes, pending),
            )
            self._validate_manifest_metrics(manifest, entries)
            self._validate_replaceable_artifacts(manifest, identity, allow_transition=False)
            remove_artifact(self.work_directory, _PENDING_NAME)
            return

        self._validate_pending_source(pending, identity)
        if current_hash == committed_hash:
            self._validate_pending_action(pending, entries, ledger_bytes)
            self._validate_manifest_metrics(manifest, entries)
            self._validate_replaceable_artifacts(manifest, identity, allow_transition=False)
            if pending.result is None:
                result = EvaluationResult.infrastructure_failure(
                    pending.action.id,
                    "interrupted evaluation recovered before a result was persisted",
                    cost=0.0,
                    cost_unit=self.spec.budget.cost_unit,
                )
                pending = self._write_pending(
                    pending.action,
                    result,
                    optimizer_seconds=pending.optimizer_seconds,
                )
            assert pending.result is not None
            self._validate_result(pending.result)
            self.ledger.append(pending.action, pending.result)
        else:
            if pending.result is None or not self._is_exact_pending_extension(
                ledger_bytes, pending
            ):
                raise StudyRecoveryError(
                    "ledger change is not the exact transition proved by pending state"
                )
            if not entries or entries[-1] != (pending.action, pending.result):
                raise StudyRecoveryError("pending result is not the final ledger observation")
            self._validate_pending_action(
                pending,
                entries[:-1],
                self._committed_bytes_before_pending(ledger_bytes, pending),
            )
            self._validate_manifest_metrics(manifest, entries[:-1])
            self._validate_replaceable_artifacts(manifest, identity, allow_transition=True)

        self._update_artifacts(committed_pending_sha256=pending.sha256)
        remove_artifact(self.work_directory, _PENDING_NAME)

    def _artifact_present(self, name: str) -> bool:
        path = self.work_directory / name
        return path.exists() or path.is_symlink()

    def _ledger_bytes(self) -> bytes:
        if not self.ledger.path.exists():
            return b""
        try:
            return self.ledger.path.read_bytes()
        except OSError as error:
            raise StudyRecoveryError(f"ledger cannot be read: {error}") from error

    def _read_ledger_snapshot(
        self,
    ) -> tuple[tuple[tuple[EvaluationAction, EvaluationResult], ...], bytes]:
        try:
            entries, contents = self.ledger.snapshot()
            self._validate_entries(entries)
            return entries, contents
        except (OSError, TypeError, ValueError) as error:
            raise StudyRecoveryError(f"ledger is corrupt or incompatible: {error}") from error

    def _make_identity(
        self,
        committed_ledger_sha256: str,
        *,
        start_timestamp: str | None = None,
    ) -> RunIdentity:
        try:
            configuration = self.backend.identity_dict()
            canonical_json(configuration)
            return RunIdentity.create(
                spec=self.spec,
                space=self.space,
                backend_name=self.backend.name,
                backend_configuration=configuration,
                ledger_path=self.ledger.path.name,
                committed_ledger_sha256=committed_ledger_sha256,
                input_artifact_hashes=self.input_artifact_hashes,
                start_timestamp=start_timestamp or self.start_timestamp,
            )
        except (TypeError, ValueError) as error:
            raise StudyRecoveryError(f"backend identity is invalid: {error}") from error

    def _read_manifest(self) -> tuple[dict[str, object], RunIdentity]:
        try:
            data = read_json_artifact(self.work_directory, _MANIFEST_NAME)
            required = {
                "schema_version",
                "run_identity",
                "run_identity_sha256",
                "runtime",
                "end_timestamp",
                "stop_reason",
                "total_evaluator_cost",
                "optimizer_overhead_seconds",
                "total_evaluator_seconds",
                "evaluation_count",
                "status_counts",
                "pending_count",
                "committed_pending_sha256",
                "committed_control_sha256",
                "committed_bootstrap_sha256",
                "artifact_sha256",
                "verification_commands",
            }
            if set(data) != required:
                raise ValueError("manifest has invalid keys")
            if data["schema_version"] != SCHEMA_VERSION:
                raise ValueError("manifest schema version differs")
            if not isinstance(data["run_identity"], Mapping):
                raise TypeError("manifest run identity must be a mapping")
            identity = RunIdentity.from_dict(data["run_identity"])
            if identity.sha256 != data["run_identity_sha256"]:
                raise ValueError("manifest run identity hash differs")
            if not isinstance(data["runtime"], Mapping):
                raise TypeError("manifest runtime must be a mapping")
            if (data["end_timestamp"] is None) != (data["stop_reason"] is None):
                raise ValueError("manifest terminal timestamps and stop reason disagree")
            if data["end_timestamp"] is not None and (
                not isinstance(data["end_timestamp"], str) or not data["end_timestamp"]
            ):
                raise TypeError("manifest end timestamp is invalid")
            if data["stop_reason"] is not None and data["stop_reason"] not in _TERMINAL_REASONS:
                raise ValueError("manifest stop reason is invalid")
            for field in (
                "total_evaluator_cost",
                "optimizer_overhead_seconds",
                "total_evaluator_seconds",
            ):
                value = data[field]
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or value < 0
                ):
                    raise ValueError(f"manifest {field} is invalid")
            if (
                isinstance(data["evaluation_count"], bool)
                or not isinstance(data["evaluation_count"], int)
                or data["evaluation_count"] < 0
            ):
                raise ValueError("manifest evaluation count is invalid")
            if not isinstance(data["status_counts"], Mapping) or any(
                not isinstance(name, str)
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 0
                for name, count in data["status_counts"].items()
            ):
                raise ValueError("manifest status counts are invalid")
            if data["pending_count"] != 0:
                raise ValueError("committed manifest must have zero pending actions")
            committed_pending = data["committed_pending_sha256"]
            if committed_pending is not None and not self._is_digest(committed_pending):
                raise ValueError("manifest committed pending hash is invalid")
            committed_control = data["committed_control_sha256"]
            if committed_control is not None and not self._is_digest(committed_control):
                raise ValueError("manifest committed control hash is invalid")
            committed_bootstrap = data["committed_bootstrap_sha256"]
            if committed_bootstrap is not None and not self._is_digest(committed_bootstrap):
                raise ValueError("manifest committed bootstrap hash is invalid")
            artifact_hashes = data["artifact_sha256"]
            if not isinstance(artifact_hashes, Mapping) or set(artifact_hashes) != set(
                _REPLACEABLE_NAMES
            ):
                raise ValueError("manifest artifact hashes are invalid")
            if any(not self._is_digest(value) for value in artifact_hashes.values()):
                raise ValueError("manifest artifact hash is invalid")
            if not isinstance(data["verification_commands"], list) or not all(
                isinstance(value, str) for value in data["verification_commands"]
            ):
                raise TypeError("manifest verification commands are invalid")
            return data, identity
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise StudyRecoveryError(f"corrupt or incompatible manifest: {error}") from error

    def _validate_invocation(self, identity: RunIdentity) -> None:
        expected = self._make_identity(
            identity.committed_ledger_sha256,
            start_timestamp=identity.start_timestamp,
        )
        given = identity.to_dict()
        wanted = expected.to_dict()
        checks = (
            ("study", "study specification"),
            ("search_space", "search space or encoding"),
            ("backend", "backend name or configuration"),
            ("ledger", "ledger path"),
            ("input_artifact_hashes", "input artifact hashes"),
            ("seed", "study seed"),
        )
        for field, label in checks:
            if given[field] != wanted[field]:
                raise StudyRecoveryError(f"requested {label} differs from the manifest")

    def _validate_manifest_metrics(
        self,
        manifest: Mapping[str, object],
        entries: tuple[tuple[EvaluationAction, EvaluationResult], ...],
    ) -> None:
        expected_counts = {
            status: sum(result.status.value == status for _, result in entries)
            for status in sorted({result.status.value for _, result in entries})
        }
        expected_cost = sum(result.cost for _, result in entries)
        expected_seconds = sum(result.evaluator_seconds for _, result in entries)
        if manifest["evaluation_count"] != len(entries):
            raise StudyRecoveryError("manifest evaluation count differs from the committed ledger")
        if manifest["total_evaluator_cost"] != expected_cost:
            raise StudyRecoveryError("manifest evaluator cost differs from the committed ledger")
        if manifest["total_evaluator_seconds"] != expected_seconds:
            raise StudyRecoveryError("manifest evaluator time differs from the committed ledger")
        if manifest["status_counts"] != expected_counts:
            raise StudyRecoveryError("manifest status counts differ from the committed ledger")

    def _validate_replaceable_artifacts(
        self,
        manifest: Mapping[str, object],
        identity: RunIdentity,
        *,
        allow_transition: bool,
    ) -> None:
        try:
            backend_state = read_json_artifact(self.work_directory, "backend-state.json")
            recommendation = read_json_artifact(self.work_directory, "recommendation.json")
            report_path = self.work_directory / "optimization-report.md"
            if report_path.is_symlink() or not report_path.is_file():
                raise ValueError(
                    "required study artifact is missing or symlinked: optimization-report.md"
                )
            report = report_path.read_text(encoding="utf-8")
            if not report.startswith("# Optimization study\n"):
                raise ValueError("optimization report has invalid content")
            required_backend = {
                "schema_version",
                "backend",
                "run_identity_sha256",
                "ledger_sha256",
                "state",
            }
            if set(backend_state) != required_backend:
                raise ValueError("backend snapshot has invalid keys")
            if backend_state["schema_version"] != SCHEMA_VERSION:
                raise ValueError("backend snapshot schema version differs")
            if backend_state["backend"] != self.backend.name or not isinstance(
                backend_state["state"], Mapping
            ):
                raise ValueError("backend snapshot is incompatible")
            accepted = {
                identity.sha256: identity.committed_ledger_sha256,
            }
            if allow_transition:
                current = self._make_identity(ledger_sha256(self.ledger))
                accepted[current.sha256] = current.committed_ledger_sha256
            snapshot_identity = backend_state["run_identity_sha256"]
            if (
                snapshot_identity not in accepted
                or backend_state["ledger_sha256"] != accepted[snapshot_identity]
            ):
                raise ValueError("backend snapshot does not match an allowed commit state")
            required_recommendation = {
                "action_id",
                "config",
                "outcomes",
                "feasible",
                "message",
            }
            if set(recommendation) != required_recommendation:
                raise ValueError("recommendation has invalid keys")
            Recommendation(**recommendation)
            recorded_hashes = manifest["artifact_sha256"]
            if allow_transition:
                if (
                    artifact_sha256(self.work_directory / "recommendation.json")
                    != recorded_hashes["recommendation.json"]
                    and recommendation != self.backend.recommend(self.ledger).to_dict()
                ):
                    raise ValueError("replacement recommendation does not match the current ledger")
                if artifact_sha256(report_path) != recorded_hashes["optimization-report.md"] and (
                    f"- Ledger hash: {ledger_sha256(self.ledger)}" not in report
                    or f"- Manifest study hash: {identity.to_dict()['study_sha256']}" not in report
                ):
                    raise ValueError("replacement report does not match the current ledger")
            else:
                for name in _REPLACEABLE_NAMES:
                    if artifact_sha256(self.work_directory / name) != recorded_hashes[name]:
                        raise ValueError(f"study artifact hash differs: {name}")
        except (OSError, UnicodeDecodeError, TypeError, ValueError) as error:
            raise StudyRecoveryError(f"corrupt or incompatible study artifact: {error}") from error

    def _read_pending(self) -> _PendingTransition | None:
        path = self._pending_path()
        if not path.exists():
            if path.is_symlink():
                raise StudyRecoveryError("pending state is a symlink")
            return None
        if path.is_symlink():
            raise StudyRecoveryError("pending state is a symlink")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            required = {
                "schema_version",
                "run_identity_sha256",
                "committed_ledger_sha256",
                "original_start_timestamp",
                "action",
                "result",
                "metadata",
            }
            if not isinstance(data, dict) or set(data) != required:
                raise ValueError("pending state has invalid keys")
            if data["schema_version"] != SCHEMA_VERSION:
                raise ValueError("pending state schema version differs")
            if not self._is_digest(data["run_identity_sha256"]) or not self._is_digest(
                data["committed_ledger_sha256"]
            ):
                raise ValueError("pending state identity hashes are invalid")
            if (
                not isinstance(data["original_start_timestamp"], str)
                or not data["original_start_timestamp"]
            ):
                raise ValueError("pending state original start timestamp is invalid")
            if not isinstance(data["metadata"], dict) or set(data["metadata"]) != {
                "optimizer_seconds"
            }:
                raise ValueError("pending state metadata is invalid")
            optimizer_seconds = data["metadata"]["optimizer_seconds"]
            if (
                isinstance(optimizer_seconds, bool)
                or not isinstance(optimizer_seconds, (int, float))
                or not math.isfinite(optimizer_seconds)
                or optimizer_seconds < 0
            ):
                raise ValueError("pending optimizer time is invalid")
            action = EvaluationAction.from_dict(data["action"])
            result = None if data["result"] is None else EvaluationResult.from_dict(data["result"])
            if result is not None and action.id != result.action_id:
                raise ValueError("pending action and result IDs differ")
            return _PendingTransition(
                run_identity_sha256=data["run_identity_sha256"],
                committed_ledger_sha256=data["committed_ledger_sha256"],
                original_start_timestamp=data["original_start_timestamp"],
                action=action,
                result=result,
                optimizer_seconds=float(optimizer_seconds),
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise StudyRecoveryError(f"corrupt or incompatible pending state: {error}") from error

    def _read_control_pending(self) -> _PendingControlTransition | None:
        path = self._control_pending_path()
        if not path.exists():
            if path.is_symlink():
                raise StudyRecoveryError("pending control state is a symlink")
            return None
        if path.is_symlink():
            raise StudyRecoveryError("pending control state is a symlink")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            required = {
                "schema_version",
                "run_identity_sha256",
                "committed_ledger_sha256",
                "original_start_timestamp",
                "stop_reason",
                "end_timestamp",
            }
            if not isinstance(data, dict) or set(data) != required:
                raise ValueError("pending control state has invalid keys")
            if data["schema_version"] != SCHEMA_VERSION:
                raise ValueError("pending control state schema version differs")
            if not self._is_digest(data["run_identity_sha256"]) or not self._is_digest(
                data["committed_ledger_sha256"]
            ):
                raise ValueError("pending control state identity hashes are invalid")
            if (
                not isinstance(data["original_start_timestamp"], str)
                or not data["original_start_timestamp"]
            ):
                raise ValueError("pending control original start timestamp is invalid")
            if data["stop_reason"] not in _TERMINAL_REASONS:
                raise ValueError("pending control stop reason is invalid")
            if not isinstance(data["end_timestamp"], str) or not data["end_timestamp"]:
                raise ValueError("pending control end timestamp is invalid")
            return _PendingControlTransition(
                run_identity_sha256=data["run_identity_sha256"],
                committed_ledger_sha256=data["committed_ledger_sha256"],
                original_start_timestamp=data["original_start_timestamp"],
                stop_reason=data["stop_reason"],
                end_timestamp=data["end_timestamp"],
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise StudyRecoveryError(
                f"corrupt or incompatible pending control state: {error}"
            ) from error

    def _read_bootstrap_pending(self) -> _PendingBootstrapTransition | None:
        path = self._bootstrap_pending_path()
        if not path.exists():
            if path.is_symlink():
                raise StudyRecoveryError("pending bootstrap state is a symlink")
            return None
        if path.is_symlink():
            raise StudyRecoveryError("pending bootstrap state is a symlink")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            required = {
                "schema_version",
                "run_identity_sha256",
                "committed_ledger_sha256",
                "original_start_timestamp",
            }
            if not isinstance(data, dict) or set(data) != required:
                raise ValueError("pending bootstrap state has invalid keys")
            if data["schema_version"] != SCHEMA_VERSION:
                raise ValueError("pending bootstrap state schema version differs")
            if not self._is_digest(data["run_identity_sha256"]) or not self._is_digest(
                data["committed_ledger_sha256"]
            ):
                raise ValueError("pending bootstrap identity hashes are invalid")
            if (
                not isinstance(data["original_start_timestamp"], str)
                or not data["original_start_timestamp"]
            ):
                raise ValueError("pending bootstrap original start timestamp is invalid")
            return _PendingBootstrapTransition(
                run_identity_sha256=data["run_identity_sha256"],
                committed_ledger_sha256=data["committed_ledger_sha256"],
                original_start_timestamp=data["original_start_timestamp"],
            )
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise StudyRecoveryError(
                f"corrupt or incompatible pending bootstrap state: {error}"
            ) from error

    def _write_pending(
        self,
        action: EvaluationAction,
        result: EvaluationResult | None,
        *,
        optimizer_seconds: float = 0.0,
    ) -> _PendingTransition:
        if self.run_identity is None:
            raise StudyRecoveryError("study identity is not initialized")
        pending = _PendingTransition(
            run_identity_sha256=self.run_identity.sha256,
            committed_ledger_sha256=self.run_identity.committed_ledger_sha256,
            original_start_timestamp=self.start_timestamp,
            action=action,
            result=result,
            optimizer_seconds=optimizer_seconds,
        )
        atomic_write_json(
            self.work_directory,
            _PENDING_NAME,
            pending.to_dict(),
        )
        return pending

    def _write_control_pending(self, stop_reason: str) -> _PendingControlTransition:
        if self.run_identity is None:
            raise StudyRecoveryError("study identity is not initialized")
        if stop_reason not in _TERMINAL_REASONS:
            raise StudyRecoveryError("terminal transition has an invalid stop reason")
        pending = _PendingControlTransition(
            run_identity_sha256=self.run_identity.sha256,
            committed_ledger_sha256=self.run_identity.committed_ledger_sha256,
            original_start_timestamp=self.start_timestamp,
            stop_reason=stop_reason,
            end_timestamp=self.wall_clock(),
        )
        atomic_write_json(
            self.work_directory,
            _PENDING_CONTROL_NAME,
            pending.to_dict(),
        )
        return pending

    def _write_bootstrap_pending(self) -> _PendingBootstrapTransition:
        if self.run_identity is None:
            raise StudyRecoveryError("study identity is not initialized")
        pending = _PendingBootstrapTransition(
            run_identity_sha256=self.run_identity.sha256,
            committed_ledger_sha256=self.run_identity.committed_ledger_sha256,
            original_start_timestamp=self.start_timestamp,
        )
        atomic_write_json(
            self.work_directory,
            _PENDING_BOOTSTRAP_NAME,
            pending.to_dict(),
        )
        return pending

    def _validate_pending_source(self, pending: _PendingTransition, identity: RunIdentity) -> None:
        if pending.run_identity_sha256 != identity.sha256:
            raise StudyRecoveryError("pending state run identity differs from the manifest")
        if pending.committed_ledger_sha256 != identity.committed_ledger_sha256:
            raise StudyRecoveryError("pending state committed ledger hash differs")
        if pending.original_start_timestamp != identity.start_timestamp:
            raise StudyRecoveryError("pending state original start timestamp differs")

    def _validate_control_source(
        self, pending: _PendingControlTransition, identity: RunIdentity
    ) -> None:
        if pending.run_identity_sha256 != identity.sha256:
            raise StudyRecoveryError("pending control run identity differs from the manifest")
        if pending.committed_ledger_sha256 != identity.committed_ledger_sha256:
            raise StudyRecoveryError("pending control committed ledger hash differs")
        if pending.original_start_timestamp != identity.start_timestamp:
            raise StudyRecoveryError("pending control original start timestamp differs")

    def _validate_bootstrap_source(
        self, pending: _PendingBootstrapTransition, identity: RunIdentity
    ) -> None:
        if pending.run_identity_sha256 != identity.sha256:
            raise StudyRecoveryError("pending bootstrap run identity differs")
        if pending.committed_ledger_sha256 != identity.committed_ledger_sha256:
            raise StudyRecoveryError("pending bootstrap committed ledger hash differs")
        if pending.original_start_timestamp != identity.start_timestamp:
            raise StudyRecoveryError("pending bootstrap original start timestamp differs")

    def _validate_pending_action(
        self,
        pending: _PendingTransition,
        committed_entries: tuple[tuple[EvaluationAction, EvaluationResult], ...],
        committed_bytes: bytes,
    ) -> None:
        try:
            if pending.action.scope is not EvaluationScope.SYSTEM:
                raise ValueError("scope must be system")
            self.space.encode(pending.action.config)
            if pending.result is not None:
                self._validate_result(pending.result)
            expected = self.backend.suggest(_LedgerReplay(committed_entries, committed_bytes), n=1)
            if len(expected) != 1 or expected[0] != pending.action:
                raise ValueError("action differs from deterministic backend replay")
        except Exception as error:
            if isinstance(error, StudyRecoveryError):
                raise
            raise StudyRecoveryError(f"pending action is invalid: {error}") from error

    def _recover_control_transition(
        self,
        manifest: Mapping[str, object],
        identity: RunIdentity,
        pending: _PendingControlTransition,
        entries: tuple[tuple[EvaluationAction, EvaluationResult], ...],
        current_hash: str,
        committed_hash: str,
    ) -> None:
        self._validate_control_source(pending, identity)
        if current_hash != committed_hash:
            raise StudyRecoveryError("ledger changed during a pending control transition")
        committed_residue = manifest["committed_control_sha256"] == pending.sha256
        if committed_residue:
            if (
                manifest["stop_reason"] != pending.stop_reason
                or manifest["end_timestamp"] != pending.end_timestamp
            ):
                raise StudyRecoveryError("committed control transition differs from the manifest")
            self._validate_manifest_metrics(manifest, entries)
            self._validate_replaceable_artifacts(manifest, identity, allow_transition=False)
            remove_artifact(self.work_directory, _PENDING_CONTROL_NAME)
            return
        if self.stop_reason is not None or self.end_timestamp is not None:
            raise StudyRecoveryError("a terminal manifest cannot begin another control transition")
        self._validate_control_reason(pending.stop_reason)
        self._validate_manifest_metrics(manifest, entries)
        self._validate_replaceable_artifacts(manifest, identity, allow_transition=True)
        self.stop_reason = pending.stop_reason
        self.end_timestamp = pending.end_timestamp
        self._update_artifacts(committed_control_sha256=pending.sha256)
        remove_artifact(self.work_directory, _PENDING_CONTROL_NAME)

    def _validate_control_reason(self, stop_reason: str) -> None:
        derived = self._stop_before_suggest()
        if stop_reason == "finite_space_exhausted":
            if derived is not None:
                raise StudyRecoveryError(
                    "pending finite-space stop conflicts with a derived stop reason"
                )
            try:
                self.backend.suggest(self.ledger, n=1)
            except SearchSpaceExhausted:
                return
            except Exception as error:
                raise StudyRecoveryError(
                    f"pending control reason could not be replayed: {error}"
                ) from error
            raise StudyRecoveryError("pending finite-space stop cannot be replayed")
        if derived != stop_reason:
            raise StudyRecoveryError("pending control reason differs from committed study state")

    def _recover_bootstrap_transition(self, pending: _PendingBootstrapTransition) -> None:
        empty_hash = hashlib.sha256(b"").hexdigest()
        if pending.committed_ledger_sha256 != empty_hash:
            raise StudyRecoveryError("bootstrap transition does not identify an empty ledger")
        self.start_timestamp = pending.original_start_timestamp
        identity = self._make_identity(empty_hash, start_timestamp=self.start_timestamp)
        self._validate_bootstrap_source(pending, identity)
        self.run_identity = identity
        self._update_artifacts(committed_bootstrap_sha256=pending.sha256)
        remove_artifact(self.work_directory, _PENDING_BOOTSTRAP_NAME)

    def _recover_committed_bootstrap_residue(
        self,
        manifest: Mapping[str, object],
        identity: RunIdentity,
        pending: _PendingBootstrapTransition,
        entries: tuple[tuple[EvaluationAction, EvaluationResult], ...],
        current_hash: str,
        committed_hash: str,
    ) -> None:
        self._validate_bootstrap_source(pending, identity)
        if current_hash != committed_hash or entries:
            raise StudyRecoveryError("committed bootstrap residue requires an empty ledger")
        if manifest["committed_bootstrap_sha256"] != pending.sha256:
            raise StudyRecoveryError("bootstrap transition was not committed by the manifest")
        self._validate_manifest_metrics(manifest, entries)
        self._validate_replaceable_artifacts(manifest, identity, allow_transition=False)
        remove_artifact(self.work_directory, _PENDING_BOOTSTRAP_NAME)

    def _commit_terminal(self, stop_reason: str) -> None:
        if self.stop_reason is not None:
            if self.stop_reason != stop_reason:
                raise StudyRecoveryError("terminal stop reason cannot be replaced")
            return
        if self._read_pending() is not None:
            raise StudyRecoveryError("cannot end a study with an unresolved action transition")
        if self._read_control_pending() is not None:
            raise StudyRecoveryError("a terminal control transition is already pending")
        pending = self._write_control_pending(stop_reason)
        self.stop_reason = pending.stop_reason
        self.end_timestamp = pending.end_timestamp
        self._update_artifacts(committed_control_sha256=pending.sha256)
        remove_artifact(self.work_directory, _PENDING_CONTROL_NAME)

    def _is_exact_pending_extension(self, ledger_bytes: bytes, pending: _PendingTransition) -> bool:
        if pending.result is None:
            return False
        record = self.ledger.record_bytes(pending.action, pending.result)
        if not ledger_bytes.endswith(record):
            return False
        prefix = ledger_bytes[: -len(record)]
        return hashlib.sha256(prefix).hexdigest() == pending.committed_ledger_sha256

    def _committed_bytes_before_pending(
        self, ledger_bytes: bytes, pending: _PendingTransition
    ) -> bytes:
        if pending.result is None:
            raise StudyRecoveryError("pending result is required to reconstruct prior ledger bytes")
        record = self.ledger.record_bytes(pending.action, pending.result)
        if not ledger_bytes.endswith(record):
            raise StudyRecoveryError("pending record is not the final ledger byte sequence")
        return ledger_bytes[: -len(record)]

    def _is_committed_pending_residue(
        self,
        manifest: Mapping[str, object],
        pending: _PendingTransition,
        ledger_bytes: bytes,
    ) -> bool:
        return (
            manifest["committed_pending_sha256"] == pending.sha256
            and pending.original_start_timestamp == self.start_timestamp
            and self._is_exact_pending_extension(ledger_bytes, pending)
        )

    @staticmethod
    def _is_digest(value: object) -> bool:
        return (
            isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdef" for character in value)
        )

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
        self._validate_entries(entries)
        return entries

    def _validate_entries(
        self, entries: tuple[tuple[EvaluationAction, EvaluationResult], ...]
    ) -> None:
        total = 0.0
        for action, result in entries:
            if action.scope is not EvaluationScope.SYSTEM:
                raise ValueError(f"ledger action must have system scope: {action.id!r}")
            try:
                self.space.encode(action.config)
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"ledger action has invalid configuration: {action.id!r}"
                ) from error
            self._validate_result(result)
            total += result.cost
        if not math.isfinite(total) or total < 0:
            raise ValueError("ledger total evaluator cost must be finite and nonnegative")

    def _assert_committed_ledger(self, *, allow_pending: bool = False) -> None:
        if self.run_identity is None:
            raise StudyRecoveryError("study identity is not initialized")
        pending = self._read_pending()
        control_pending = self._read_control_pending()
        bootstrap_pending = self._read_bootstrap_pending()
        if (
            pending is not None or control_pending is not None or bootstrap_pending is not None
        ) and not allow_pending:
            raise StudyRecoveryError("study has an unresolved pending transition")
        if ledger_sha256(self.ledger) != self.run_identity.committed_ledger_sha256:
            raise StudyRecoveryError("ledger differs from the committed study identity")

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

    def _update_artifacts(
        self,
        *,
        committed_pending_sha256: str | None = None,
        committed_control_sha256: str | None = None,
        committed_bootstrap_sha256: str | None = None,
    ) -> None:
        entries, ledger_bytes = self.ledger.snapshot()
        self._validate_entries(entries)
        identity = self._make_identity(hashlib.sha256(ledger_bytes).hexdigest())
        diagnostics = self.backend.diagnostics(self.ledger)
        write_study_artifacts(
            directory=self.work_directory,
            ledger=self.ledger,
            run_identity=identity,
            backend_name=self.backend.name,
            backend_state=self.backend.state_dict(),
            diagnostics=diagnostics,
            recommendation=self.backend.recommend(self.ledger),
            end_timestamp=self.end_timestamp,
            stop_reason=self.stop_reason,
            committed_pending_sha256=committed_pending_sha256,
            committed_control_sha256=committed_control_sha256,
            committed_bootstrap_sha256=committed_bootstrap_sha256,
        )
        self.run_identity = identity
