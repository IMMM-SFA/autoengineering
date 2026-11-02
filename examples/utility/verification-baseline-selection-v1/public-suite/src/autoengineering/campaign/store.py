"""Single-writer, immutable event commits and replayable projections."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import stat
from typing import Callable
import uuid

from .artifacts import read_bytes
from .records import CampaignEvent, Response
from .serialization import canonical_json, unique_json


class StoreError(ValueError):
    pass


class WriterBusy(StoreError):
    pass


def checked_directory(path: Path) -> Path:
    path = Path(path).absolute()
    for part in (*reversed(path.parents), path):
        if part.is_symlink():
            raise StoreError("campaign directory contains a symlink")
    if not path.is_dir():
        raise StoreError("campaign directory does not exist")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) & 0o077:
        raise StoreError("campaign directory must be owner-private")
    return path


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def durable_write(path: Path, data: bytes, *, replace: bool = False) -> None:
    """Stage and fsync, then link without replacement (or replace a projection)."""
    temporary = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    if replace:
        if path.is_symlink():
            raise StoreError("projection cannot be a symlink")
        os.replace(temporary, path)
    else:
        os.link(temporary, path)
        temporary.unlink()
    sync_directory(path.parent)


@dataclass(frozen=True)
class Projection:
    revision: int
    state: str
    head_hash: str | None
    responses: dict[str, tuple[str, Response]]
    events: tuple[CampaignEvent, ...]

    def to_dict(self):
        return {
            "revision": self.revision,
            "state": self.state,
            "head_hash": self.head_hash,
            "responses": {
                key: {"digest": value[0], "response": value[1].to_dict()}
                for key, value in self.responses.items()
            },
        }


def reduce_events(events: tuple[CampaignEvent, ...]) -> Projection:
    state, previous = "created", None
    responses = {}
    for revision, event in enumerate(events, 1):
        if (
            event.revision != revision
            or event.previous_hash != previous
            or event.from_state != state
        ):
            raise StoreError("event chain revision, hash or state mismatch")
        request_id = event.response.request_id
        if request_id in responses:
            raise StoreError("duplicate committed request identity")
        responses[request_id] = (event.request_digest, event.response)
        state, previous = event.to_state, event.digest
    return Projection(len(events), state, previous, responses, events)


class EventStore:
    """The event commit is authoritative. state.json is a disposable cache.

    Fault injection hooks receive named commit boundaries and are used only by tests.
    Interrupted temporary files remain on disk for explicit recovery inspection.
    """

    def __init__(self, root: Path, *, fault: Callable[[str], None] | None = None):
        self.root = checked_directory(root)
        self.events_path = checked_directory(self.root / "events")
        self._locked = False
        self.fault = fault or (lambda stage: None)

    @classmethod
    def create(cls, root: Path, **kwargs):
        root = Path(root).absolute()
        if root.is_symlink() or (root.exists() and (not root.is_dir() or any(root.iterdir()))):
            raise StoreError("run requires an absent or empty work directory")
        for part in (*reversed(root.parents), root):
            if part.is_symlink():
                raise StoreError("work directory contains a symlink")
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        root.chmod(0o700)
        for name in ("events", "artifacts", "children", "attempts", "control", "reports"):
            (root / name).mkdir(mode=0o700)
        sync_directory(root)
        return cls(root, **kwargs)

    @contextmanager
    def writer(self):
        if self._locked:
            raise WriterBusy("campaign writer is already held")
        descriptor = os.open(
            self.root / ".campaign.lock",
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise StoreError("lock is not a regular file")
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise WriterBusy("another controller owns the campaign") from error
            self._locked = True
            yield self
        finally:
            self._locked = False
            os.close(descriptor)

    def replay(self) -> Projection:
        """Read only committed files, validating artifacts without touching observations elsewhere."""
        files = []
        for path in self.events_path.iterdir():
            if path.name.startswith(".") and path.name.endswith(".tmp"):
                continue
            if len(path.name) != 17 or not path.name[:12].isdigit() or path.suffix != ".json":
                raise StoreError("unexpected event file")
            files.append(path)
        events = []
        for sequence, path in enumerate(sorted(files), 1):
            if path.name != f"{sequence:012d}.json":
                raise StoreError("gap in committed event sequence")
            if (
                path.is_symlink()
                or not stat.S_ISREG(path.stat().st_mode)
                or path.stat().st_size > 1048576
            ):
                raise StoreError("invalid event file")
            raw = path.read_text(encoding="utf-8")
            try:
                document = unique_json(raw)
                if not isinstance(document, dict) or set(document) != {"event", "sha256"}:
                    raise ValueError("invalid event envelope")
                event = CampaignEvent.from_dict(document["event"])
                if document["sha256"] != event.digest:
                    raise ValueError("event checksum mismatch")
            except (ValueError, TypeError, KeyError) as error:
                raise StoreError("malformed committed event") from error
            if raw != canonical_json({"event": event.to_dict(), "sha256": event.digest}) + "\n":
                raise StoreError("committed event is not canonical")
            for artifact in event.artifacts:
                try:
                    read_bytes(self.root, artifact)
                except (OSError, ValueError) as error:
                    raise StoreError("committed artifact is missing or modified") from error
            if not set(event.response.artifact_ids) <= {ref.sha256 for ref in event.artifacts}:
                raise StoreError("response references an uncommitted result")
            events.append(event)
        return reduce_events(tuple(events))

    def refresh_projection(self) -> Projection:
        if not self._locked:
            raise StoreError("projection rebuild requires the writer lock")
        projection = self.replay()
        durable_write(
            self.root / "state.json",
            (canonical_json(projection.to_dict()) + "\n").encode(),
            replace=True,
        )
        return projection

    def commit(self, event: CampaignEvent) -> Response:
        if not self._locked:
            raise StoreError("commit requires the writer lock")
        projection = self.replay()
        reduce_events((*projection.events, event))
        self.fault("before_staging")
        for artifact in event.artifacts:
            read_bytes(self.root, artifact)
        if not set(event.response.artifact_ids) <= {ref.sha256 for ref in event.artifacts}:
            raise StoreError("response references an uncommitted result")
        self.fault("after_artifact_durability")
        durable_write(
            self.events_path / f"{event.revision:012d}.json",
            (canonical_json({"event": event.to_dict(), "sha256": event.digest}) + "\n").encode(),
        )
        self.fault("after_event_commit")
        self.refresh_projection()
        self.fault("after_projection")
        self.fault("before_acknowledgment")
        return event.response

    def quarantine_temporaries(self) -> tuple[str, ...]:
        """Explicit recovery preserves interrupted files instead of deleting evidence."""
        if not self._locked:
            raise StoreError("recovery requires the writer lock")
        quarantine = self.root / "recovery"
        if quarantine.is_symlink():
            raise StoreError("recovery directory cannot be a symlink")
        quarantine.mkdir(mode=0o700, exist_ok=True)
        preserved = []
        for parent in (self.root, self.events_path):
            for path in parent.glob(".*.tmp"):
                if path.is_symlink() or not path.is_file():
                    raise StoreError("invalid temporary evidence")
                target = quarantine / f"{parent.name}-{path.name}"
                os.link(path, target)
                path.unlink()
                preserved.append(str(target.relative_to(self.root)))
        sync_directory(quarantine)
        return tuple(preserved)
