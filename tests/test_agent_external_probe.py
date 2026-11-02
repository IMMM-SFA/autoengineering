"""Local fixture guards, without invoking a CLI or contacting a provider."""

from __future__ import annotations

from http.client import HTTPConnection
import json

from autoengineering.agents.hosts.response_boundary import validate_text_response
from examples.agent_campaign.probe_external_codex import (
    OFFLINE_MODEL,
    OFFLINE_PROMPT,
    FakeResponses,
    response_stream,
)


def request(service, *, path="/v1/responses", headers=None, body=None):
    connection = HTTPConnection("127.0.0.1", service.port, timeout=2)
    try:
        payload = (
            body
            if body is not None
            else json.dumps(
                {
                    "model": OFFLINE_MODEL,
                    "stream": True,
                    "input": [
                        {
                            "type": "message",
                            "role": "user",
                            "content": [{"type": "input_text", "text": OFFLINE_PROMPT}],
                        }
                    ],
                }
            ).encode()
        )
        connection.request("POST", path, payload, headers or {})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_offline_service_serves_one_authored_response(tmp_path):
    service = FakeResponses(tmp_path)
    try:
        status, raw = request(service)
        assert status == 200
        assert raw == validate_text_response(response_stream()).normalized_sse
        events = [
            json.loads(line[6:]) for line in raw.decode().splitlines() if line.startswith("data: ")
        ]
        completed = events[-1]["response"]
        assert completed["status"] == "completed"
        assert completed["output"][0]["content"][0]["text"] == '{"ok":true}'
        saved = (tmp_path / "request.bin").read_bytes()
        assert json.loads(saved)["model"] == OFFLINE_MODEL
        assert len(service.requests) == 1
        assert not service.errors
        status, _ = request(service)
        assert status == 400
        assert len(service.requests) == 1
        assert (tmp_path / "request.bin").read_bytes() == saved
        assert service.errors == ["ValueError: unexpected or duplicate offline request"]
    finally:
        service.close()
    assert not service.thread.is_alive()


def test_offline_service_rejects_auth_without_saving_it(tmp_path):
    service = FakeResponses(tmp_path)
    try:
        assert request(service, headers={"Authorization": "Bearer synthetic-canary"})[0] == 400
        assert not service.requests
        assert not (tmp_path / "request.bin").exists()
        assert "synthetic-canary" not in repr(service.errors)
        assert service.errors == ["ValueError: offline fixture received unexpected authentication"]
        assert request(service, headers={"Content-Length": "synthetic-canary"})[0] == 400
        assert "synthetic-canary" not in repr(service.errors)
        assert not (tmp_path / "request.bin").exists()
    finally:
        service.close()


def test_offline_service_rejects_wrong_endpoint_and_envelope(tmp_path):
    service = FakeResponses(tmp_path)
    try:
        assert request(service, path="/unapproved")[0] == 400
        assert request(service, body=b'{"model":"other","stream":true}')[0] == 400
        assert request(service, headers={"Content-Length": "524289"}, body=b"x")[0] == 400
        assert not service.requests
        assert len(service.errors) == 3
        assert not (tmp_path / "request.bin").exists()
    finally:
        service.close()


def test_offline_service_rejects_tools_before_delivering_response_bytes(tmp_path):
    upstream = response_stream(tool_command="touch synthetic-marker")
    service = FakeResponses(tmp_path, body=upstream)
    try:
        status, raw = request(service)
        assert status == 400
        assert b"synthetic-marker" not in raw
        assert len(service.requests) == 1 and service.attempts == 1
        assert service.boundary["status"] == "rejected"
        assert service.boundary["client_response_bytes"] == 0
        assert (tmp_path / "upstream-response.bin").read_bytes() == upstream
        assert not (tmp_path / "client-response.bin").exists()
    finally:
        service.close()
