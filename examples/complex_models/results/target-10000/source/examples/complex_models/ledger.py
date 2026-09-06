"""Reuse parsed immutable records without caching integrity checks in large benchmarks."""

from __future__ import annotations

from functools import lru_cache

from autoengineering.optimization.ledger import ObservationLedger


class BenchmarkLedger(ObservationLedger):
    """Cache successful parses of exact bytes; reread and validate the ledger each time.

    The pinned core returns immutable records through its supported API. File,
    duplicate, unit, artifact and controller checks remain outside this cache.
    Capacity covers a complete 10000-call study without sequential-scan thrashing.
    This adapter does not change production ledgers or optimizer policy.
    """

    def __init__(self, path):
        super().__init__(path)
        self._cached_parse = lru_cache(maxsize=16384)(super()._parse_line)

    def _parse_line(self, line_number, line):
        return self._cached_parse(line_number, line)
