"""Bounded loopback transport, request ownership and separate local stop states."""

from __future__ import annotations

from http.client import HTTPConnection, RemoteDisconnected
import json
import socket
import threading
import time

import pytest

from autoengineering.agents.hosts.text_endpoint import MAX_HEADER_BYTES, TextEndpoint
from autoengineering.agents.hosts.text_exchange import TextExchange
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL, response_stream

PROMPT = "approved endpoint prompt"
NONCE = "a" * 32


def setup(tmp_path, upstream=None, **kwargs):
    tmp_path.chmod(0o700)
    exchange = TextExchange.create(
        tmp_path / "exchange",
        invocation_id="endpoint-call",
        requested_model=OFFLINE_MODEL,
        approved_prompt=PROMPT,
        output_schema={"type": "object"},
    )
    calls = []

    def callback(raw):
        calls.append(raw)
        return response_stream() if upstream is None else upstream(raw)

    endpoint = TextEndpoint(
        exchange, callback, directory=tmp_path / "endpoint", route_nonce=NONCE, **kwargs
    )
    return exchange, endpoint, calls


def payload(prompt=PROMPT):
    return json.dumps(
        {
            "model": OFFLINE_MODEL,
            "stream": True,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
        }
    ).encode()


def request(endpoint, *, body=None, path=None, headers=None):
    connection = HTTPConnection("127.0.0.1", endpoint.port, timeout=3)
    try:
        connection.request(
            "POST",
            path or f"/{NONCE}/v1/responses",
            payload() if body is None else body,
            headers or {},
        )
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def assert_stopped(result):
    assert result.listener_closed and result.handler_stopped and result.upstream_callback_stopped


def test_exact_retries_replay_the_response_without_another_upstream_call(tmp_path):
    exchange, endpoint, calls = setup(tmp_path)
    try:
        first = request(endpoint)
        assert first[0] == 200 and b'"function_call"' not in first[1]
        assert request(endpoint) == first
        assert len(calls) == 1
        assert request(endpoint, body=payload("different task"))[0] == 409
        assert len(calls) == 1
    finally:
        stopped = endpoint.close()
    assert_stopped(stopped)
    assert stopped.request_attempts == 3 and stopped.exchange_requests == 3
    assert stopped.upstream_callbacks == 1
    assert exchange.recover().status == "completed"


def test_wrong_route_and_credential_headers_cannot_dispatch_or_enter_records(tmp_path):
    exchange, endpoint, calls = setup(tmp_path)
    try:
        assert request(endpoint, path="/wrong-private-canary/v1/responses")[0] == 404
        assert request(endpoint, headers={"Authorization": "Bearer private-canary"})[0] == 400
        assert request(endpoint, headers={"Cookie": "private-canary"})[0] == 400
        assert not calls and not (exchange.root / "dispatch.json").exists()
    finally:
        stopped = endpoint.close()
    assert_stopped(stopped)
    files = b"".join(p.read_bytes() for p in endpoint.directory.rglob("*") if p.is_file())
    assert b"private-canary" not in files
    assert NONCE.encode() not in files
    assert stopped.exchange_requests == 0


def test_framing_and_header_limits_stop_before_the_exchange(tmp_path):
    exchange, endpoint, calls = setup(tmp_path)
    try:
        assert request(endpoint, headers={"Transfer-Encoding": "chunked"})[0] == 400
        assert request(endpoint, headers={"Content-Length": "524289"})[0] == 413
        assert request(endpoint, headers={"Host": "unrelated.invalid"})[0] == 400
        assert request(endpoint, headers={"X-Large": "x" * MAX_HEADER_BYTES})[0] == 431
        assert not calls and not (exchange.root / "client.json").exists()
    finally:
        assert_stopped(endpoint.close())


def test_slowly_dripped_body_obeys_one_absolute_deadline(tmp_path):
    exchange, endpoint, calls = setup(tmp_path, request_seconds=0.15)
    sock = socket.create_connection(("127.0.0.1", endpoint.port), timeout=2)
    try:
        header = (
            f"POST /{NONCE}/v1/responses HTTP/1.1\r\nHost: 127.0.0.1:{endpoint.port}\r\n"
            f"Content-Length: {len(payload())}\r\n\r\n"
        ).encode()
        sock.sendall(header)
        began = time.monotonic()
        for _ in range(8):
            try:
                sock.sendall(b"x")
            except OSError:
                break
            time.sleep(0.04)
        raw = sock.recv(4096)
        assert b"408" in raw
        assert time.monotonic() - began < 1
        assert not calls and not (exchange.root / "dispatch.json").exists()
    finally:
        sock.close()
        assert_stopped(endpoint.close())
    events = [
        json.loads(p.read_text())["event"] for p in (endpoint.directory / "events").glob("*.json")
    ]
    assert "client_read_deadline" in events


def test_request_limit_closes_listener_without_replenishing_allowance(tmp_path):
    _, endpoint, calls = setup(tmp_path, max_requests=2)
    try:
        assert request(endpoint)[0] == 200
        assert request(endpoint)[0] == 200
    finally:
        stopped = endpoint.close()
    assert_stopped(stopped)
    assert stopped.request_attempts == 2 and stopped.upstream_callbacks == 1 and len(calls) == 1
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", endpoint.port), timeout=0.2)


def test_callback_failure_and_tool_rejection_do_not_deliver_actionable_bytes(tmp_path):
    exchange, endpoint, calls = setup(
        tmp_path, upstream=lambda _: response_stream(tool_command="touch marker")
    )
    try:
        status, raw = request(endpoint)
        assert status == 422 and b"touch marker" not in raw
        assert exchange.recover().reason == "forbidden_response_item"
        assert request(endpoint)[0] == 422 and len(calls) == 1
    finally:
        assert_stopped(endpoint.close())


def test_closing_listener_does_not_claim_an_active_callback_stopped(tmp_path):
    started, release = threading.Event(), threading.Event()

    def wait(_raw):
        started.set()
        assert release.wait(timeout=5)
        return response_stream()

    exchange, endpoint, calls = setup(tmp_path, upstream=wait)
    errors = []

    def client():
        try:
            request(endpoint)
        except (OSError, RemoteDisconnected) as exc:
            errors.append(type(exc).__name__)

    worker = threading.Thread(target=client)
    worker.start()
    try:
        assert started.wait(timeout=2)
        partial = endpoint.close(wait_seconds=0.05)
        assert partial.listener_closed
        assert not partial.handler_stopped and not partial.upstream_callback_stopped
        assert len(calls) == 1
    finally:
        release.set()
        worker.join(timeout=3)
        final = endpoint.close()
    assert not worker.is_alive() and errors
    assert_stopped(final)
    assert exchange.recover().status == "completed" and len(calls) == 1


def test_close_during_partial_headers_cannot_start_an_upstream_callback(tmp_path):
    exchange, endpoint, calls = setup(tmp_path)
    sock = socket.create_connection(("127.0.0.1", endpoint.port), timeout=2)
    try:
        sock.sendall(f"POST /{NONCE}/v1/responses HTTP/1.1\r\n".encode())
        # A server event, rather than a sleep, proves it owns the accepted socket.
        deadline = time.monotonic() + 2
        while not list((endpoint.directory / "events").glob("*.json")):
            assert time.monotonic() < deadline
            time.sleep(0.01)
        assert_stopped(endpoint.close())
        assert not calls and not (exchange.root / "dispatch.json").exists()
    finally:
        sock.close()
        endpoint.close()


def test_transport_exception_text_is_not_returned_or_persisted_and_is_not_retried(tmp_path):
    def fail(_raw):
        raise RuntimeError("private-credential-canary")

    exchange, endpoint, calls = setup(tmp_path, upstream=fail)
    try:
        status, raw = request(endpoint)
        assert status == 503 and b"private-credential-canary" not in raw
        assert request(endpoint)[0] == 503 and len(calls) == 1
    finally:
        assert_stopped(endpoint.close())
    assert exchange.recover().status == "reconciliation_required"
    files = b"".join(p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    assert b"private-credential-canary" not in files


def test_duplicate_lengths_are_rejected_before_body_or_provider_processing(tmp_path):
    exchange, endpoint, calls = setup(tmp_path)
    connection = HTTPConnection("127.0.0.1", endpoint.port, timeout=2)
    try:
        connection.putrequest("POST", f"/{NONCE}/v1/responses")
        connection.putheader("Content-Length", str(len(payload())))
        connection.putheader("Content-Length", str(len(payload()) + 1))
        connection.endheaders(payload())
        response = connection.getresponse()
        assert response.status == 400
        response.read()
        assert not calls and not (exchange.root / "client.json").exists()
    finally:
        connection.close()
        assert_stopped(endpoint.close())
