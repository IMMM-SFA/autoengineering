"""Append-only, fail-closed JSONL persistence for optimization observations."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
import json
import os
from pathlib import Path
from typing import Protocol

from .records import EvaluationAction, EvaluationResult, EvaluationStatus


class LedgerCorruptionError(ValueError):
    """Raised when a durable observation line cannot be safely reconstructed."""

    def __init__(self, line_number: int, reason: str) -> None:
        super().__init__(f"ledger corruption at line {line_number}: {reason}")
        self.line_number = line_number


class LedgerLockError(RuntimeError):
    """Raised when the interprocess ledger lock cannot be acquired or released."""


class ObservationLedgerReader(Protocol):
    """Read-only observation surface available to optimization backends."""

    def entries(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]: ...

    def snapshot(
        self,
    ) -> tuple[tuple[tuple[EvaluationAction, EvaluationResult], ...], bytes]: ...

    def scientific_training_entries(
        self,
    ) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]: ...

    def constraint_training_entries(
        self,
    ) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]: ...

    def objective_training_entries(
        self,
    ) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]: ...


class _LedgerLock:
    """Exclusive, OS-managed advisory lock for one ledger path.

    The lock file intentionally remains after release. Its byte-range lock is
    released when the stream closes or a process exits, so removing the path
    would create a race between a releasing writer and a new writer.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(f"{path}.lock")
        self._stream = None

    def __enter__(self) -> "_LedgerLock":
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            stream = self.path.open("a+b")
            self._stream = stream
            if os.name == "nt":
                import msvcrt

                stream.seek(0, os.SEEK_END)
                if stream.tell() == 0:
                    stream.write(b"\0")
                    stream.flush()
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError) as error:
            self._close_after_failure()
            raise LedgerLockError(f"could not acquire ledger lock: {self.path}") from error
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        stream = self._stream
        if stream is None:
            return False
        try:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError) as error:
            raise LedgerLockError(f"could not release ledger lock: {self.path}") from error
        finally:
            stream.close()
            self._stream = None
        return False

    def _close_after_failure(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None


class ObservationLedger:
    """A JSONL ledger which only appends verified action/result observations."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        """Durably create an empty ledger without replacing an existing file."""
        with _LedgerLock(self.path):
            if self.path.is_symlink():
                raise ValueError("ledger path must be a regular nonsymlink file")
            if self.path.exists():
                if not self.path.is_file():
                    raise ValueError("ledger path must be a regular nonsymlink file")
                return
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            if os.name != "nt":
                parent_descriptor = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(parent_descriptor)
                finally:
                    os.close(parent_descriptor)

    def append(self, action: EvaluationAction, result: EvaluationResult) -> None:
        """Append one verified observation and durably synchronize it to disk."""
        if not isinstance(action, EvaluationAction) or not isinstance(result, EvaluationResult):
            raise TypeError("append requires an EvaluationAction and EvaluationResult")
        if action.id != result.action_id:
            raise ValueError("action and result IDs must match")
        line = self.record_bytes(action, result)
        with _LedgerLock(self.path):
            entries = self._entries()
            if any(existing_action.id == action.id for existing_action, _ in entries):
                raise ValueError(f"duplicate action id: {action.id}")
            recorded_units = {
                existing_result.cost_unit
                for _, existing_result in entries
                if existing_result.cost > 0
            }
            if result.cost > 0 and recorded_units and result.cost_unit not in recorded_units:
                raise ValueError("cost_unit must match earlier ledger entries")
            self._verify_artifacts(result)
            with self.path.open("ab") as stream:
                stream.write(line)
                stream.flush()
                os.fsync(stream.fileno())

    @staticmethod
    def record_bytes(action: EvaluationAction, result: EvaluationResult) -> bytes:
        """Return the exact canonical bytes appended for one observation."""
        if not isinstance(action, EvaluationAction) or not isinstance(result, EvaluationResult):
            raise TypeError("record_bytes requires an EvaluationAction and EvaluationResult")
        if action.id != result.action_id:
            raise ValueError("action and result IDs must match")
        return (
            json.dumps(
                {"action": action.to_dict(), "result": result.to_dict()},
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )

    def entries(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        """Read and validate every persisted observation without modifying the ledger."""
        with _LedgerLock(self.path):
            return self._entries()

    def snapshot(self) -> tuple[tuple[tuple[EvaluationAction, EvaluationResult], ...], bytes]:
        """Return validated entries and their exact bytes under one ledger lock."""
        with _LedgerLock(self.path):
            entries = self._entries()
            contents = b"" if not self.path.exists() else self.path.read_bytes()
            return entries, contents

    def _entries(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        """Read every entry while the caller holds the exclusive ledger lock."""
        if not self.path.exists():
            return ()
        entries: list[tuple[EvaluationAction, EvaluationResult]] = []
        seen_action_ids: set[str] = set()
        positive_cost_units: set[str] = set()
        for line_number, line in self._lines():
            action, result = self._parse_line(line_number, line)
            if action.id in seen_action_ids:
                raise LedgerCorruptionError(line_number, f"duplicate action id: {action.id}")
            if action.id != result.action_id:
                raise LedgerCorruptionError(line_number, "action and result IDs must match")
            try:
                self._verify_artifacts(result)
            except ValueError as error:
                raise LedgerCorruptionError(line_number, str(error)) from error
            if (
                result.cost > 0
                and positive_cost_units
                and result.cost_unit not in positive_cost_units
            ):
                raise LedgerCorruptionError(
                    line_number, "cost_unit must match earlier ledger entries"
                )
            if result.cost > 0:
                positive_cost_units.add(result.cost_unit)
            seen_action_ids.add(action.id)
            entries.append((action, result))
        return tuple(entries)

    def scientific_training_entries(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        """Return valid science observations, including infeasibility labels for constraints.

        Model, timeout, and infrastructure failures are operational observations and
        deliberately excluded from scientific objective and constraint training.
        """
        statuses = {EvaluationStatus.SUCCESS, EvaluationStatus.SCIENTIFIC_INFEASIBLE}
        return tuple(entry for entry in self.entries() if entry[1].status in statuses)

    def constraint_training_entries(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        """Return observations usable by constraint models, including infeasibility labels."""
        return self.scientific_training_entries()

    def objective_training_entries(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        """Return successful observations that can train an objective surrogate."""
        return tuple(
            entry for entry in self.entries() if entry[1].status is EvaluationStatus.SUCCESS
        )

    def _lines(self) -> Iterator[tuple[int, bytes]]:
        with self.path.open("rb") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.endswith(b"\n"):
                    raise LedgerCorruptionError(line_number, "truncated final line")
                yield line_number, line

    def _parse_line(
        self, line_number: int, line: bytes
    ) -> tuple[EvaluationAction, EvaluationResult]:
        try:
            data = json.loads(line.decode("utf-8"))
            if not isinstance(data, dict) or set(data) != {"action", "result"}:
                raise ValueError("record must contain exactly action and result")
            action = EvaluationAction.from_dict(data["action"])
            result = EvaluationResult.from_dict(data["result"])
        except (TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
            raise LedgerCorruptionError(line_number, str(error)) from error
        return action, result

    def _verify_artifacts(self, result: EvaluationResult) -> None:
        for artifact_id, artifact_path in result.artifacts.items():
            path = Path(artifact_path)
            if not path.is_absolute():
                path = self.path.parent / path
            if not path.is_file():
                raise ValueError(f"artifact {artifact_id!r} is missing: {artifact_path}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != result.artifact_sha256[artifact_id]:
                raise ValueError(f"artifact {artifact_id!r} SHA-256 does not match")
