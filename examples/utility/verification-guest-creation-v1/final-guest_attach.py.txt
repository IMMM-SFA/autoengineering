"""Bounded local Docker attach transport for the candidate stdio guest.

Only a Unix stream socket and a fixed attach endpoint are supported. The owner
must verify daemon/image/container identity, durably intend the single start and
start the container separately. This transport supplies no execution admission,
start/retry logic, process supervision, cleanup or independent OS attestation.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import re
import socket
import struct
import time

from autoengineering.campaign.store import StoreError
from .contracts import sha256
from .guest_bootstrap import (
    MAX_HEADER,
    MAX_RESULT_HEADER,
    MAX_PREDICTION,
    REQUEST_MAGIC,
    RESPONSE_MAGIC,
    decode_request,
)
from .guest_inputs import MAX_TAR_BYTES

MAX_HTTP_HEADER = 65536
MAX_FRAMES = 16384
MAX_STDERR = 65536
MAX_STDOUT = len(RESPONSE_MAGIC) + 4 + MAX_RESULT_HEADER + 64 * 1024 * 1024 + MAX_PREDICTION
MAX_REQUEST = len(REQUEST_MAGIC) + 4 + MAX_HEADER + MAX_TAR_BYTES
MAX_SESSION_SECONDS = 60.0
POLL_SECONDS = 0.1
MEDIA_TYPES = {
    "application/vnd.docker.raw-stream",
    "application/vnd.docker.multiplexed-stream",
}


class GuestAttachError(StoreError):
    """Transport evidence is incomplete; it cannot authorize a retry."""


class GuestAttachTimeout(GuestAttachError):
    """Original absolute I/O deadline expired, not an observed model failure."""


class GuestAttachCancelled(GuestAttachError):
    """Owner cancellation observed; container termination still needs proof."""


def _now():
    return time.monotonic()


def _arguments(api_version, container_id):
    if not isinstance(api_version, str) or not re.fullmatch(r"1\.[0-9]{1,3}", api_version):
        raise GuestAttachError("guest attach requires an explicit API version")
    sha256(container_id)


class GuestAttachSession:
    """One connection, one stdin write and a bounded non-TTY output reader.

    A failed or cancelled write consumes the connection's write attempt. No
    method reconnects, restarts a container or extends its original deadline.
    The same absolute deadline covers handshake, input, output and waiting EOF.
    """

    def __init__(self, stream, *, deadline, cancelled=None):
        if stream.family != socket.AF_UNIX or stream.type != socket.SOCK_STREAM:
            raise GuestAttachError("guest attach requires a local Unix stream")
        if type(deadline) not in (int, float) or not math.isfinite(deadline):
            raise GuestAttachError("guest attach deadline must be finite")
        remaining = deadline - _now()
        if not 0 < remaining <= MAX_SESSION_SECONDS:
            raise GuestAttachError("guest attach requires a bounded future deadline")
        self._stream = stream
        self._deadline = float(deadline)
        self._cancelled = cancelled
        self._wire = bytearray()
        self._used = False
        self._closed = False
        self._upgraded = False
        self._eof = False
        self._frame_remaining = 0
        self._channel = None
        self._frames = 0
        self._declared_stdout = self._declared_stderr = 0
        self.stdout_bytes = self.stderr_bytes = 0

    @property
    def deadline(self):
        return self._deadline

    @property
    def input_consumed(self):
        return self._used

    def _check(self):
        if self._closed:
            raise GuestAttachError("guest attach connection is closed")
        if self._cancelled is not None:
            try:
                cancelled = self._cancelled()
            except Exception:
                raise GuestAttachError("guest attach cancellation state is unavailable") from None
            if type(cancelled) is not bool:
                raise GuestAttachError("guest attach cancellation state is invalid")
            if cancelled:
                raise GuestAttachCancelled("guest attach cancelled; owned stop remains unverified")
        remaining = self._deadline - _now()
        if remaining <= 0:
            raise GuestAttachTimeout("guest attach original deadline expired")
        try:
            self._stream.settimeout(min(POLL_SECONDS, remaining))
        except OSError:
            raise GuestAttachError("guest attach timeout configuration failed") from None

    def _recv(self, size):
        while True:
            self._check()
            try:
                value = self._stream.recv(size)
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                raise GuestAttachError("guest attach receive failed") from None
            self._check()
            return value

    def _send(self, raw):
        view = memoryview(raw)
        while view:
            self._check()
            try:
                size = self._stream.send(view[:65536])
            except (TimeoutError, socket.timeout):
                continue
            except OSError:
                raise GuestAttachError("guest attach send failed") from None
            if type(size) is not int or not 0 < size <= min(65536, len(view)):
                raise GuestAttachError("guest attach send did not complete")
            view = view[size:]
        self._check()

    def _exact(self, size, *, eof_ok=False):
        value = bytearray()
        if self._wire:
            count = min(len(self._wire), size)
            value.extend(self._wire[:count])
            del self._wire[:count]
        while len(value) < size:
            chunk = self._recv(size - len(value))
            if not chunk:
                if not value and eof_ok:
                    return None
                raise GuestAttachError("guest attach output frame is truncated")
            value.extend(chunk)
        self._check()
        return bytes(value)

    def _headers(self):
        raw = bytearray()
        while True:
            boundary = raw.find(b"\r\n\r\n")
            if boundary >= 0:
                if boundary + 4 > MAX_HTTP_HEADER:
                    raise GuestAttachError("guest attach HTTP header exceeds bound")
                self._wire.extend(raw[boundary + 4 :])
                header = bytes(raw[:boundary])
                break
            if len(raw) >= MAX_HTTP_HEADER:
                raise GuestAttachError("guest attach HTTP header exceeds bound")
            chunk = self._recv(min(4096, MAX_HTTP_HEADER - len(raw)))
            if not chunk:
                raise GuestAttachError("guest attach upgrade ended before its header")
            raw.extend(chunk)
        lines = header.split(b"\r\n")
        status = re.fullmatch(rb"HTTP/1\.1 ([1-5][0-9]{2})(?: [\x20-\x7e]*)?", lines[0])
        if status is None:
            raise GuestAttachError("guest HTTP response status is malformed")
        if len(lines) > 128:
            raise GuestAttachError("guest attach HTTP header count exceeds bound")
        fields = {}
        for line in lines[1:]:
            if len(line) > 4096 or b":" not in line:
                raise GuestAttachError("guest attach HTTP header is malformed")
            name, value = line.split(b":", 1)
            if not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name) or any(
                c < 32 and c != 9 or c == 127 for c in value
            ):
                raise GuestAttachError("guest attach HTTP header is malformed")
            key = name.decode("ascii").lower()
            if key in fields:
                raise GuestAttachError("guest attach HTTP header is duplicated")
            fields[key] = value.decode("latin1").strip().lower()
        return int(status.group(1)), fields

    def upgrade(self, api_version, container_id):
        """Send only the fixed attach request; preserve prefetched output bytes."""
        try:
            _arguments(api_version, container_id)
            if self._upgraded:
                raise GuestAttachError("guest attach upgrade is already consumed")
            request = (
                f"POST /v{api_version}/containers/{container_id}/attach"
                "?logs=0&stream=1&stdin=1&stdout=1&stderr=1 HTTP/1.1\r\n"
                "Host: localhost\r\nConnection: Upgrade\r\nUpgrade: tcp\r\n"
                "Content-Type: text/plain\r\nContent-Length: 0\r\n\r\n"
            ).encode("ascii")
            self._send(request)
            status, fields = self._headers()
            if status != 101:
                raise GuestAttachError("guest attach HTTP upgrade was refused")
            connections = {s.strip() for s in fields.get("connection", "").split(",")}
            if (
                "upgrade" not in connections
                or "close" in connections
                or fields.get("upgrade") != "tcp"
                or fields.get("content-type") not in MEDIA_TYPES
                or fields.get("content-length") not in (None, "0")
                or "transfer-encoding" in fields
                or "content-encoding" in fields
            ):
                raise GuestAttachError("guest attach HTTP stream configuration differs")
            self._upgraded = True
            return self
        except BaseException:
            self.close()
            raise

    def send_once(self, packet, *, job_digest, launch_digest, package_digest):
        """Write one verified request and half-close stdin, without reconnecting."""
        try:
            if not self._upgraded or self._used:
                raise GuestAttachError("guest attach stdin is unavailable or already consumed")
            if not isinstance(packet, bytes) or not 0 < len(packet) <= MAX_REQUEST:
                raise GuestAttachError("guest attach input exceeds bound")
            try:
                request, _ = decode_request(io.BytesIO(packet))
            except (ValueError, TypeError, KeyError):
                raise GuestAttachError(
                    "guest attach input is not a verified frozen request"
                ) from None
            if (request.job.digest, request.launch.digest, request.package.digest) != (
                job_digest,
                launch_digest,
                package_digest,
            ):
                raise GuestAttachError("guest attach input belongs to another original transfer")
            self._used = True
            self._send(packet)
            self._check()
            try:
                self._stream.shutdown(socket.SHUT_WR)
            except OSError:
                raise GuestAttachError("guest attach stdin closure is unverified") from None
        except BaseException:
            self.close()
            raise

    def _next_frame(self):
        header = self._exact(8, eof_ok=True)
        if header is None:
            self._eof = True
            return
        self._frames += 1
        if self._frames > MAX_FRAMES:
            raise GuestAttachError("guest attach output frame count exceeds bound")
        channel = header[0]
        if header[1:4] != b"\x00\x00\x00" or channel not in (1, 2):
            raise GuestAttachError("guest attach output channel/header differs")
        size = struct.unpack("!I", header[4:])[0]
        if channel == 1:
            self._declared_stdout += size
            if self._declared_stdout > MAX_STDOUT:
                raise GuestAttachError("guest attach stdout exceeds bound")
        else:
            self._declared_stderr += size
            if self._declared_stderr > MAX_STDERR:
                raise GuestAttachError("guest attach diagnostics exceed bound")
        self._channel, self._frame_remaining = channel, size

    def read(self, size):
        """Return stdout only; bound/discard stderr without exposing its bytes."""
        try:
            if not self._upgraded or type(size) is not int or not 0 <= size <= 65536:
                raise GuestAttachError("guest attach read requires an upgraded bounded stream")
            self._check()
            if size == 0:
                return b""
            while not self._eof:
                if not self._frame_remaining:
                    self._next_frame()
                    continue
                amount = min(self._frame_remaining, size if self._channel == 1 else 65536)
                chunk = self._exact(amount)
                self._frame_remaining -= len(chunk)
                if self._channel == 1:
                    self.stdout_bytes += len(chunk)
                    return chunk
                self.stderr_bytes += len(chunk)
            return b""
        except BaseException:
            self.close()
            raise

    def close(self):
        if not self._closed:
            self._closed = True
            try:
                self._stream.close()
            except OSError:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def attach(socket_path, api_version, container_id, *, deadline, cancelled=None):
    """Open one explicit Unix endpoint; never create, start or retry a container."""
    _arguments(api_version, container_id)
    path = str(socket_path)
    if not Path(path).is_absolute() or "\x00" in path or ".." in Path(path).parts:
        raise GuestAttachError("guest attach requires an explicit local Unix socket path")
    stream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    session = None
    try:
        session = GuestAttachSession(stream, deadline=deadline, cancelled=cancelled)
        session._check()
        try:
            stream.connect(path)
        except (TimeoutError, socket.timeout):
            session._check()
            raise GuestAttachError("guest attach connection outcome is unverified") from None
        except OSError:
            raise GuestAttachError("guest attach connection failed") from None
        return session.upgrade(api_version, container_id)
    except BaseException:
        if session is not None:
            session.close()
        else:
            stream.close()
        raise
