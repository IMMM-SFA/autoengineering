"""Host protocol. The scheduler owns reservations, permissions and parsing."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import math
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Protocol

from autoengineering.agents.records import HostCapabilities, TaskAssignment


@dataclass(frozen=True)
class HostResult:
    """Internal transport result. Raw bytes may be empty, partial or non-JSON."""

    status: Literal["completed", "timeout", "cancelled", "host_failure", "reconciliation_required"]
    raw_output: str
    resolved_model: str | None
    usage: Mapping[str, int | None]
    elapsed_seconds: float | None
    raw_transcript: bytes | None = None
    stderr: bytes | None = None
    stop_verified: bool = True

    def __post_init__(self):
        if self.status not in (
            "completed",
            "timeout",
            "cancelled",
            "host_failure",
            "reconciliation_required",
        ):
            raise ValueError("invalid host result status")
        if type(self.raw_output) is not str:
            raise ValueError("host final output must be text")
        if self.resolved_model is not None and (
            type(self.resolved_model) is not str or not self.resolved_model.strip()
        ):
            raise ValueError("invalid resolved model")
        if self.elapsed_seconds is None and self.status == "completed":
            raise ValueError("completed host result requires a measured duration")
        if self.elapsed_seconds is not None and (
            type(self.elapsed_seconds) not in (int, float)
            or not math.isfinite(self.elapsed_seconds)
            or self.elapsed_seconds < 0
        ):
            raise ValueError("invalid host duration")
        if not isinstance(self.usage, Mapping) or any(
            type(key) is not str or (value is not None and (type(value) is not int or value < 0))
            for key, value in self.usage.items()
        ):
            raise ValueError("invalid host usage")
        for value in (self.raw_transcript, self.stderr):
            if value is not None and type(value) is not bytes:
                raise ValueError("host transcripts must be bytes")
        if type(self.stop_verified) is not bool:
            raise ValueError("host stop receipt must be boolean")
        object.__setattr__(self, "usage", MappingProxyType(dict(self.usage)))


@dataclass(frozen=True)
class InvocationContext:
    invocation_id: str
    nonce: str
    directory: Path
    timeout_seconds: float
    max_output_bytes: int
    on_launch: Callable[[dict], None]
    cancelled: Callable[[], bool]


class Host(Protocol):
    def capabilities(self) -> HostCapabilities: ...

    def invoke(
        self,
        task: TaskAssignment,
        prompt: str,
        *,
        invocation_id: str,
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> HostResult: ...

    def cancel(self, invocation_id: str) -> bool:
        """True only when an owned invocation has verifiably stopped."""
        ...
