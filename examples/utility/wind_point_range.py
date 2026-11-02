"""Versioned direct large-read profile for bounded WIND development extraction.

The metadata-only reader and its limits stay unchanged. Large contiguous reads
share its counters, deadline and consumed-failure state, without block overfetch.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from examples.utility.wind_range import RangeLimits, RangeReadError, WindRangeFile


@dataclass(frozen=True)
class PointRangeLimits(RangeLimits):
    requests: int = 128
    response_bytes: int = 64 * 1024**2
    max_read_bytes: int = 4 * 1024**2
    elapsed_seconds: float = 120.0

    def _validate(self):
        if not 1 <= self.max_read_bytes <= 4 * 1024**2:
            raise ValueError("wind point read exceeds 4 MiB")
        RangeLimits(
            self.requests,
            self.response_bytes,
            self.block_bytes,
            self.cached_blocks,
            min(self.max_read_bytes, 1024**2),
            self.elapsed_seconds,
        )


class WindPointRangeFile(WindRangeFile):
    def __init__(self, pin, limits=PointRangeLimits(), **kwargs):
        if not isinstance(limits, PointRangeLimits):
            raise ValueError("point ranges require their explicit versioned limits")
        super().__init__(pin, limits, **kwargs)

    def read(self, size=-1):
        self._check()
        if type(size) is not int or not 0 <= size <= self.limits.max_read_bytes:
            raise RangeReadError("wind point refuses unbounded or oversized reads")
        if size <= self.limits.block_bytes:
            return super().read(size)
        lo = self._position
        hi = min(lo + size, self.pin.size_bytes) - 1
        if hi < lo:
            return b""
        count = hi - lo + 1
        if (
            self._requests >= self.limits.requests
            or self._reserved + count + 1 > self.limits.response_bytes
        ):
            self._failed = True
            raise RangeReadError("wind point request or byte reservation exhausted")
        self._requests += 1
        self._reserved += count + 1
        event = {
            "request": self._requests,
            "lo": lo,
            "hi": hi,
            "reserved_bytes": count + 1,
            "status": "intended",
            "profile": "direct-large-read-v1",
        }
        failed = False
        try:
            if self.record:
                self.record(dict(event), None)
            status, headers, raw = self.fetch(
                self.pin, lo, hi, min(10.0, self._deadline - self.clock())
            )
            if not isinstance(raw, bytes) or len(raw) > count + 1:
                raise RangeReadError("wind point transport exceeded byte contract")
            self._received += len(raw)
            if (
                status != 206
                or headers.get("content-range") != f"bytes {lo}-{hi}/{self.pin.size_bytes}"
                or headers.get("content-length") != str(count)
                or headers.get("etag") != self.pin.etag
                or headers.get("content-encoding") not in (None, "identity")
                or len(raw) != count
            ):
                raise RangeReadError("wind point response identity or bytes differ")
            self._check()
            event.update(
                status="complete", received_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()
            )
            if self.record:
                self.record(dict(event), raw)
        except Exception:
            failed = True
        if failed:
            self._failed = True
            event["status"] = "unverified"
            self._events.append(event)
            if self.record:
                self.record(dict(event), None)
            raise RangeReadError(
                "wind point response unverified; automatic retry forbidden"
            ) from None
        self._events.append(event)
        self._position = hi + 1
        return raw
