"""Bounded Anthropic HTTP endpoint with an opaque local invocation capability."""

from http.client import HTTPConnection
import json

import pytest

from autoengineering.agents.hosts.anthropic_endpoint import AnthropicEndpoint
from autoengineering.agents.hosts.text_endpoint import TextEndpoint
from autoengineering.agents.hosts.text_exchange import TextExchange
from test_agent_anthropic_exchange import exchange, client, message, snapshot

TOKEN = "b" * 32


def setup(tmp_path):
    broker = exchange(tmp_path)
    calls = []
    endpoint = AnthropicEndpoint(
        broker,
        lambda raw: calls.append(raw) or message(),
        directory=tmp_path / "endpoint",
        route_nonce=TOKEN,
    )
    return broker, endpoint, calls


def request(endpoint, headers=None, path="/v1/messages?beta=true"):
    connection = HTTPConnection("127.0.0.1", endpoint.port, timeout=3)
    try:
        connection.request("POST", path, client(), headers or {})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_local_capability_is_checked_not_forwarded_and_exact_repeats_replay(tmp_path):
    broker, endpoint, calls = setup(tmp_path)
    try:
        assert endpoint.base_url == f"http://127.0.0.1:{endpoint.port}"
        assert endpoint.bootstrap_token == TOKEN
        for headers in (
            {"x-api-key": TOKEN},
            {"x-api-key": TOKEN, "Authorization": "Bearer " + TOKEN},
        ):
            code, raw = request(endpoint, headers)
            assert code == 200 and b"StructuredOutput" in raw
        assert len(calls) == 1 and TOKEN.encode() not in calls[0]
        assert b"unapproved" not in calls[0]
        assert broker.recover().replayed
    finally:
        stop = endpoint.close()
    assert stop.listener_closed and stop.handler_stopped and stop.upstream_callback_stopped
    assert TOKEN not in repr(snapshot(endpoint.directory))
    assert (
        stop.request_attempts == 2 and stop.exchange_requests == 2 and stop.upstream_callbacks == 1
    )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"x-api-key": "wrong"},
        {"Authorization": "Bearer wrong"},
        {"x-api-key": TOKEN, "Authorization": "Bearer wrong"},
        {"x-api-key": "wrong", "Authorization": "Bearer " + TOKEN},
        {"x-api-key": TOKEN, "Cookie": "private-canary"},
        {"x-api-key": TOKEN, "Proxy-Authorization": "private-canary"},
    ],
)
def test_missing_conflicting_or_foreign_credentials_do_not_dispatch(tmp_path, headers):
    broker, endpoint, calls = setup(tmp_path)
    try:
        code, raw = request(endpoint, headers)
        assert code in (400, 401) and b"private-canary" not in raw
        assert not calls and not (broker.root / "dispatch.json").exists()
    finally:
        stop = endpoint.close()
    assert stop.upstream_callbacks == 0 and stop.handler_stopped
    assert "private-canary" not in repr(snapshot(endpoint.directory))


def test_duplicate_auth_header_is_not_treated_as_a_matching_single_value(tmp_path):
    broker, endpoint, calls = setup(tmp_path)
    connection = HTTPConnection("127.0.0.1", endpoint.port, timeout=3)
    try:
        raw = client()
        connection.putrequest("POST", "/v1/messages?beta=true")
        connection.putheader("Content-Length", str(len(raw)))
        connection.putheader("x-api-key", TOKEN)
        connection.putheader("X-Api-Key", TOKEN)
        connection.endheaders(raw)
        response = connection.getresponse()
        assert response.status == 401
        response.read()
        assert not calls and not (broker.root / "dispatch.json").exists()
    finally:
        connection.close()
        endpoint.close()


@pytest.mark.parametrize("path", ["/v1/messages", "/v1/messages?beta=false", "/v1/models"])
def test_unqualified_operations_and_query_flags_refuse(tmp_path, path):
    broker, endpoint, calls = setup(tmp_path)
    try:
        assert request(endpoint, {"x-api-key": TOKEN}, path)[0] == 404
        assert not calls and not (broker.root / "dispatch.json").exists()
    finally:
        endpoint.close()


def test_endpoint_protocols_are_not_interchangeable(tmp_path):
    broker = exchange(tmp_path)
    with pytest.raises(ValueError, match="protocols differ"):
        TextEndpoint(broker, lambda _: pytest.fail("dispatch"), directory=tmp_path / "wrong")
    assert not (tmp_path / "wrong").exists()
    legacy = TextExchange.create(
        tmp_path / "legacy",
        invocation_id="legacy",
        requested_model="old-model",
        approved_prompt="old-prompt",
        output_schema={"type": "object"},
    )
    with pytest.raises(ValueError, match="protocols differ"):
        AnthropicEndpoint(legacy, lambda _: pytest.fail("dispatch"), directory=tmp_path / "wrong")
    assert not (tmp_path / "wrong").exists()
    manifest = json.loads((legacy.root / "exchange.json").read_text())
    assert "max_output_tokens" not in manifest
    assert manifest["response_boundary"] == "text-response-1.1"
