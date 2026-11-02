"""Invocation-scoped loopback endpoint for a durable text exchange.

The endpoint receives no provider credentials and forwards no client headers.
An opaque route and the exchange's exact prompt bind accepted requests. This is
not a qualified host boundary or an upstream transport. A trusted callback must
enforce its own network, credential and deadline policy. Stop receipts describe
local callback state, never whether remote provider computation has stopped.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import hashlib
from http.client import HTTPException
from http.server import BaseHTTPRequestHandler, HTTPServer
import math
from pathlib import Path
import re
import socket
import threading
import time
import uuid

from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write

from .text_exchange import MAX_REQUEST_BYTES, TextExchange

MAX_HEADER_BYTES = 16384


@dataclass(frozen=True)
class EndpointStop:
    listener_closed: bool
    handler_stopped: bool
    upstream_callback_stopped: bool
    request_attempts: int
    exchange_requests: int
    upstream_callbacks: int


class _RequestReader:
    """Read against one absolute deadline, including slowly dripped bytes."""

    def __init__(self, connection, seconds):
        self.connection = connection
        self.deadline = time.monotonic() + seconds
        self.buffer = bytearray()
        self.used = 0
        self.headers = True
        self.expired = False

    def _receive(self, size):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            self.expired = True
            raise TimeoutError("client_read_deadline")
        self.connection.settimeout(remaining)
        try:
            return self.connection.recv(min(size, 4096))
        except TimeoutError:
            self.expired = True
            raise

    def _take(self, size):
        data = bytes(self.buffer[:size])
        del self.buffer[:size]
        if self.headers:
            self.used += len(data)
            if self.used > MAX_HEADER_BYTES:
                raise HTTPException("header_limit")
        return data

    def readline(self, size=-1):
        limit = MAX_HEADER_BYTES + 1 if size < 0 else size
        if self.headers:
            limit = min(limit, MAX_HEADER_BYTES - self.used + 1)
        while True:
            newline = self.buffer.find(b"\n", 0, limit)
            if newline >= 0:
                return self._take(newline + 1)
            if len(self.buffer) >= limit:
                return self._take(limit)
            chunk = self._receive(limit - len(self.buffer))
            if not chunk:
                return self._take(len(self.buffer))
            self.buffer.extend(chunk)

    def read(self, size):
        result = bytearray(self._take(min(size, len(self.buffer))))
        while len(result) < size:
            chunk = self._receive(size - len(result))
            if not chunk:
                break
            result.extend(chunk)
        if time.monotonic() >= self.deadline:
            self.expired = True
            raise TimeoutError("client_read_deadline")
        return bytes(result)

    def close(self):
        self.buffer.clear()


class TextEndpoint:
    """Bounded serial HTTP adapter. A blocked callback leaves stop unverified.

    Duplicate exact requests may replay the exchange's saved normalized reply.
    They do not invoke the upstream callback again. Changed requests fail. The
    route is a scoped invocation identifier, not an upstream credential. Keep
    the full bootstrap URL private and render only its digest in reports.
    """

    def __init__(
        self,
        exchange: TextExchange,
        upstream: Callable[[bytes], bytes],
        *,
        directory: Path,
        route_nonce: str | None = None,
        max_requests: int = 8,
        request_seconds: float = 2,
    ):
        if type(max_requests) is not int or not 1 <= max_requests <= 16:
            raise ValueError("endpoint request limit must be in 1..16")
        if (
            type(request_seconds) not in (int, float)
            or not math.isfinite(request_seconds)
            or not 0 < request_seconds <= 5
        ):
            raise ValueError("invalid endpoint request deadline")
        nonce = uuid.uuid4().hex if route_nonce is None else route_nonce
        if type(nonce) is not str or re.fullmatch(r"[0-9a-f]{32}", nonce) is None:
            raise ValueError("invalid endpoint route nonce")
        directory = Path(directory).absolute()
        checked_directory(directory.parent)
        directory.mkdir(mode=0o700)
        (directory / "events").mkdir(mode=0o700)
        self.directory = checked_directory(directory)
        self.exchange = exchange
        self._upstream = upstream
        self._route = f"/{nonce}/v1/responses"
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._listener_closed = threading.Event()
        self._handler_stopped = threading.Event()
        self._connection = None
        self._upstream_active = False
        self._attempts = self._exchange_requests = self._upstream_callbacks = 0
        self._event_number = self._stop_number = 0
        self._max_requests = max_requests
        owner = self

        class Server(HTTPServer):
            allow_reuse_address = False

            def handle_error(self, _request, _address):
                # Never let a traceback echo untrusted request or transport text.
                owner._record("handler_error")

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def setup(self):
                super().setup()
                self.connection.settimeout(request_seconds)
                self.rfile.close()
                self.rfile = _RequestReader(self.connection, request_seconds)
                self.request_version, self.requestline, self.command = "HTTP/1.0", "", ""
                with owner._lock:
                    owner._connection = self.connection
                    owner._attempts += 1
                owner._record("connection_opened")

            def handle_one_request(self):
                try:
                    super().handle_one_request()
                except HTTPException:
                    self.close_connection = True
                    self.send_error(431)

            def parse_request(self):
                try:
                    return super().parse_request()
                finally:
                    self.rfile.headers = False

            def finish(self):
                try:
                    super().finish()
                finally:
                    with owner._lock:
                        if owner._connection is self.connection:
                            owner._connection = None
                    if self.rfile.expired:
                        owner._record("client_read_deadline")
                    owner._record("connection_closed")

            def send_error(self, code, message=None, explain=None):
                self.reply(code, "invalid_http_request")

            def reply(self, code, reason, body=None):
                self.close_connection = True
                if owner._stop.is_set():
                    return
                payload = (
                    canonical_json({"error": {"code": reason, "message": reason}}).encode()
                    if body is None
                    else body
                )
                try:
                    self.send_response(code)
                    self.send_header(
                        "Content-Type", "application/json" if body is None else "text/event-stream"
                    )
                    self.send_header("Content-Length", str(len(payload)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(payload)
                except (OSError, ValueError):
                    owner._record("client_delivery_interrupted")

            def reject(self, code, reason):
                owner._record(reason)
                self.reply(code, reason)

            def do_POST(self):
                if self.path != owner._route:
                    return self.reject(404, "wrong_invocation_route")
                if any(
                    name in self.headers
                    for name in ("Authorization", "Proxy-Authorization", "Cookie")
                ):
                    return self.reject(400, "credential_header_forbidden")
                hosts = self.headers.get_all("Host", [])
                if len(hosts) != 1 or hosts[0] not in {
                    f"127.0.0.1:{owner.port}",
                    f"localhost:{owner.port}",
                }:
                    return self.reject(400, "invalid_endpoint_host")
                lengths = self.headers.get_all("Content-Length", [])
                if (
                    len(lengths) != 1
                    or len(lengths[0]) > 7
                    or not lengths[0].isascii()
                    or not lengths[0].isdigit()
                ):
                    return self.reject(400, "invalid_request_length")
                length = int(lengths[0])
                if not 0 < length <= MAX_REQUEST_BYTES:
                    return self.reject(413, "client_request_size_limit")
                if (
                    "Transfer-Encoding" in self.headers
                    or self.headers.get("Content-Encoding", "identity") != "identity"
                ):
                    return self.reject(400, "unsupported_request_encoding")
                try:
                    raw = self.rfile.read(length)
                except (OSError, ValueError):
                    return self.reject(408, "incomplete_client_request")
                if len(raw) != length:
                    return self.reject(400, "incomplete_client_request")
                self.connection.settimeout(request_seconds)
                with owner._lock:
                    if owner._stop.is_set():
                        return
                    owner._exchange_requests += 1
                try:
                    result = owner.exchange.execute(raw, owner._invoke)
                except Exception:
                    return self.reject(409, "exchange_evidence_conflict")
                owner._record("exchange_" + result.status)
                if result.status == "completed":
                    self.reply(200, "completed", result.response.normalized_sse)
                else:
                    self.reply(422 if result.status == "rejected" else 503, result.reason)

        self._server = Server(("127.0.0.1", 0), Handler)
        self._server.timeout = 0.1
        self._base_url = f"http://127.0.0.1:{self.port}/{nonce}/v1"
        manifest = {
            "schema_version": "1.0",
            "invocation_id": exchange.manifest["invocation_id"],
            "owner_source_identity": exchange.manifest["source_identity"],
            "address": "127.0.0.1",
            "port": self.port,
            "route_sha256": hashlib.sha256(self._route.encode()).hexdigest(),
            "max_requests": max_requests,
            "request_seconds": request_seconds,
            "max_header_bytes": MAX_HEADER_BYTES,
            "max_request_bytes": MAX_REQUEST_BYTES,
        }
        try:
            durable_write(directory / "endpoint.json", canonical_json(manifest).encode())
        except BaseException:
            self._server.server_close()
            raise
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    @property
    def base_url(self):
        return self._base_url

    @property
    def port(self):
        return self._server.server_port

    def _record(self, code):
        with self._lock:
            self._event_number += 1
            durable_write(
                self.directory / "events" / f"{self._event_number:06d}.json",
                canonical_json({"event": code}).encode(),
            )

    def _invoke(self, request):
        with self._lock:
            if self._stop.is_set():
                raise RuntimeError("endpoint_stopping")
            self._upstream_active = True
            self._upstream_callbacks += 1
        self._record("upstream_callback_started")
        try:
            return self._upstream(request)
        finally:
            with self._lock:
                self._upstream_active = False
            self._record("upstream_callback_returned")

    def _serve(self):
        try:
            while not self._stop.is_set():
                with self._lock:
                    exhausted = self._attempts >= self._max_requests
                if exhausted:
                    break
                try:
                    self._server.handle_request()
                except (OSError, ValueError):
                    if not self._stop.is_set():
                        self._record("listener_failed")
                    break
        finally:
            self._server.server_close()
            self._listener_closed.set()
            self._handler_stopped.set()

    def close(self, *, wait_seconds: float = 3) -> EndpointStop:
        if (
            type(wait_seconds) not in (int, float)
            or not math.isfinite(wait_seconds)
            or not 0 < wait_seconds <= 5
        ):
            raise ValueError("invalid endpoint stop deadline")
        with self._lock:
            self._stop.set()
            connection = self._connection
        self._server.server_close()
        self._listener_closed.set()
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self._thread.join(timeout=wait_seconds)
        with self._lock:
            result = EndpointStop(
                self._listener_closed.is_set(),
                self._handler_stopped.is_set(),
                not self._upstream_active,
                self._attempts,
                self._exchange_requests,
                self._upstream_callbacks,
            )
            self._stop_number += 1
            durable_write(
                self.directory / f"stop-{self._stop_number:06d}.json",
                canonical_json(asdict(result)).encode(),
            )
        return result
