"""Scripted host for offline contract tests. It executes no worker tools."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from autoengineering.agents.records import HostCapabilities, TaskAssignment
from .base import HostResult


class FakeHost:
    def __init__(
        self,
        results: Iterable[
            HostResult | Exception | Callable[[TaskAssignment, str, str], HostResult]
        ],
    ):
        self._results = iter(results)
        self.calls: list[tuple[str, TaskAssignment, str]] = []
        self._seen: set[str] = set()

    def capabilities(self) -> HostCapabilities:
        return HostCapabilities(
            "1.0", "fake", "1.0", "scripted-1.0", "none", True, False, None, "offline"
        )

    def invoke(
        self,
        task: TaskAssignment,
        prompt: str,
        *,
        invocation_id: str,
        timeout_seconds: float,
        max_output_bytes: int,
    ) -> HostResult:
        if invocation_id in self._seen:
            raise ValueError("physical invocation identity was already dispatched")
        if timeout_seconds <= 0 or max_output_bytes <= 0:
            raise ValueError("host call requires positive limits")
        self._seen.add(invocation_id)
        self.calls.append((invocation_id, task, prompt))
        result = next(self._results)
        if callable(result):
            result = result(task, prompt, invocation_id)
        if isinstance(result, Exception):
            raise result
        if len(result.raw_output.encode("utf-8")) > max_output_bytes:
            return HostResult("host_failure", "output limit exceeded", None, {}, 0)
        if result.elapsed_seconds is not None and result.elapsed_seconds > timeout_seconds:
            return HostResult("timeout", result.raw_output, None, {}, timeout_seconds)
        return result

    def cancel(self, invocation_id: str) -> bool:
        # Calls are synchronous and have no surviving process.
        return invocation_id in self._seen
