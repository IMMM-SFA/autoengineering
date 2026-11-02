"""Bounded conditional byte ranges for WIND development objects, never reserve years.

This read-only file object supports optional h5py without whole-object downloads.
ETags are opaque consistency pins, not full-file cryptographic verification.
A failed or uncertain request consumes its reservation and poisons the reader.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import io
import re
import time
from typing import Literal
import urllib.error
import urllib.request

from autoengineering.campaign.serialization import Record


class RangeReadError(ValueError):
    pass


@dataclass(frozen=True)
class WindObjectPin(Record):
    schema: Literal["utility-wind-development-object-v1"]
    year: int
    size_bytes: int
    etag: str

    def _validate(self):
        if not 2007 <= self.year <= 2011 or not 0 < self.size_bytes <= 2 * 1024**4:
            raise ValueError("wind range reader permits only bounded 2007-2011 development objects")
        if not re.fullmatch(r'"[0-9a-f]{32}(?:-[0-9]{1,6})?"', self.etag):
            raise ValueError("wind source needs its explicit strong S3 ETag")

    @property
    def url(self):
        return (
            f"https://nrel-pds-wtk.s3.us-west-2.amazonaws.com/conus/v1.0.0/wtk_conus_{self.year}.h5"
        )


@dataclass(frozen=True)
class RangeLimits(Record):
    requests: int = 64
    response_bytes: int = 5 * 1024**2
    block_bytes: int = 65536
    cached_blocks: int = 16
    max_read_bytes: int = 1024**2
    elapsed_seconds: float = 60.0

    def _validate(self):
        if (
            not 1 <= self.requests <= 1024
            or not 1 <= self.response_bytes <= 64 * 1024**2
            or not 4096 <= self.block_bytes <= 262144
            or self.block_bytes & (self.block_bytes - 1)
            or not 1 <= self.cached_blocks <= 64
            or not 1 <= self.max_read_bytes <= 1024**2
            or not 0 < self.elapsed_seconds <= 120
        ):
            raise ValueError("wind range limits exceed supported bounds")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RangeReadError("wind range redirects are forbidden")


def fetch_range(pin, lo, hi, timeout):
    """One anonymous request, no retries or redirects; at most requested bytes + 1.

    Timeout applies to socket operations. The caller also checks elapsed time.
    This is not an OS-enforced whole-operation deadline or memory qualification.
    """
    request = urllib.request.Request(
        pin.url,
        headers={"Range": f"bytes={lo}-{hi}", "If-Match": pin.etag, "Accept-Encoding": "identity"},
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            headers = {}
            for name in ("Content-Range", "Content-Length", "ETag", "Content-Encoding"):
                values = response.headers.get_all(name, [])
                if len(values) > 1:
                    raise RangeReadError("duplicated wind response identity")
                if values:
                    headers[name.lower()] = values[0]
            if response.status != 206 or response.url != pin.url:
                raise RangeReadError("wind server did not honor the fixed range")
            if (
                headers.get("content-range") != f"bytes {lo}-{hi}/{pin.size_bytes}"
                or headers.get("content-length") != str(hi - lo + 1)
                or headers.get("etag") != pin.etag
                or headers.get("content-encoding") not in (None, "identity")
            ):
                raise RangeReadError("wind response headers differ from the pinned range")
            raw = response.read(hi - lo + 2)
            return response.status, headers, raw
    except urllib.error.HTTPError as error:
        error.close()
        raise RangeReadError("wind range HTTP request refused") from None


class WindRangeFile(io.RawIOBase):
    def __init__(
        self, pin, limits=RangeLimits(), *, fetch=fetch_range, record=None, clock=time.monotonic
    ):
        super().__init__()
        if not isinstance(pin, WindObjectPin) or not isinstance(limits, RangeLimits):
            raise ValueError("wind source pin and limits must be explicit records")
        self.pin, self.limits, self.fetch, self.record, self.clock = (
            pin,
            limits,
            fetch,
            record,
            clock,
        )
        self._position = 0
        self._cache = OrderedDict()
        self._failed = False
        self._requests = self._reserved = self._received = 0
        self._deadline = clock() + limits.elapsed_seconds
        self._events = []

    def readable(self):
        return True

    def seekable(self):
        return True

    def writable(self):
        return False

    def _check(self):
        if self.closed or self._failed:
            raise RangeReadError("wind range reader is closed or consumed")
        if self.clock() >= self._deadline:
            self._failed = True
            raise RangeReadError("wind range elapsed allowance exhausted")

    def tell(self):
        self._check()
        return self._position

    def seek(self, offset, whence=io.SEEK_SET):
        self._check()
        if type(offset) is not int or type(whence) is not int:
            raise RangeReadError("wind range seek requires integers")
        if whence not in (io.SEEK_SET, io.SEEK_CUR, io.SEEK_END):
            raise RangeReadError("wind range seek origin differs")
        position = (
            offset
            + {io.SEEK_SET: 0, io.SEEK_CUR: self._position, io.SEEK_END: self.pin.size_bytes}[
                whence
            ]
        )
        if not 0 <= position <= self.pin.size_bytes:
            raise RangeReadError("wind range seek outside object")
        self._position = position
        return position

    def _block(self, index):
        self._check()
        if index in self._cache:
            self._cache.move_to_end(index)
            return self._cache[index]
        lo = index * self.limits.block_bytes
        hi = min(lo + self.limits.block_bytes, self.pin.size_bytes) - 1
        size = hi - lo + 1
        if (
            self._requests >= self.limits.requests
            or self._reserved + size + 1 > self.limits.response_bytes
        ):
            self._failed = True
            raise RangeReadError("wind range request or byte reservation exhausted")
        self._requests += 1
        self._reserved += size + 1
        event = {
            "request": self._requests,
            "lo": lo,
            "hi": hi,
            "reserved_bytes": size + 1,
            "status": "intended",
        }
        failed = False
        try:
            if self.record:
                self.record(dict(event), None)
            status, headers, raw = self.fetch(
                self.pin, lo, hi, min(10.0, self._deadline - self.clock())
            )
            if not isinstance(raw, bytes) or len(raw) > size + 1:
                raise RangeReadError("wind transport exceeded its byte contract")
            self._received += len(raw)
            if (
                status != 206
                or headers.get("content-range") != f"bytes {lo}-{hi}/{self.pin.size_bytes}"
                or headers.get("content-length") != str(size)
                or headers.get("etag") != self.pin.etag
                or headers.get("content-encoding") not in (None, "identity")
                or len(raw) != size
            ):
                raise RangeReadError("wind range response identity or byte count differs")
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
                "wind range response unverified; automatic retry forbidden"
            ) from None
        self._events.append(event)
        self._cache[index] = raw
        if len(self._cache) > self.limits.cached_blocks:
            self._cache.popitem(last=False)
        return raw

    def read(self, size=-1):
        self._check()
        if type(size) is not int or not 0 <= size <= self.limits.max_read_bytes:
            raise RangeReadError("wind range refuses unbounded or oversized reads")
        stop = min(self._position + size, self.pin.size_bytes)
        position = self._position
        parts = []
        while position < stop:
            block = self._block(position // self.limits.block_bytes)
            offset = position % self.limits.block_bytes
            piece = block[offset : offset + stop - position]
            if not piece:
                raise RangeReadError("wind range cache ended unexpectedly")
            parts.append(piece)
            position += len(piece)
        self._position = stop
        return b"".join(parts)

    def readinto(self, buffer):
        target = memoryview(buffer).cast("B")
        raw = self.read(len(target))
        target[: len(raw)] = raw
        return len(raw)

    def write(self, data):
        raise io.UnsupportedOperation("wind source is read-only")

    def truncate(self, size=None):
        raise io.UnsupportedOperation("wind source is read-only")

    def stats(self):
        uncertain = any(e["status"] != "complete" for e in self._events)
        return {
            "response_bytes_total": None if uncertain else self._received,
            "requests": self._requests,
            "reserved_response_bytes": self._reserved,
            "received_response_bytes": self._received,
            "cached_blocks": len(self._cache),
            "failed": self._failed,
            "events": [dict(e) for e in self._events],
        }

    def close(self):
        if hasattr(self, "_cache"):
            self._cache.clear()
        super().close()
