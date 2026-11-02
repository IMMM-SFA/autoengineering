"""Fixed API worker against authored responses, never an external provider."""

from datetime import datetime, timedelta, timezone
from email.message import Message
import hashlib
import io
import json
from pathlib import Path
import ssl
import time

import pytest

from autoengineering.agents.hosts import anthropic_worker as worker
from autoengineering.agents.hosts.anthropic_upstream import ScopedAnthropicUpstream
from autoengineering.campaign.serialization import canonical_json

KEY = "authored-fixture-api-key-never-valid"
WORKSPACE = "wrkspc_authored_fixture"
MODEL = "claude-authored-fixture"


def write(path, raw):
    path.write_bytes(raw)
    path.chmod(0o600)


def inputs(tmp_path):
    tmp_path.chmod(0o700)
    for name in ("credentials", "attempt", "client"):
        (tmp_path / name).mkdir(mode=0o700)
    raw = canonical_json(
        {
            "model": MODEL,
            "system": worker.TRUSTED_INSTRUCTIONS,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "approved"}]}],
            "max_tokens": 512,
            "stream": False,
            "tools": [],
            "output_config": {"format": {"type": "json_schema", "schema": worker.WIRE_SCHEMA}},
        }
    ).encode()
    lease = {
        "schema_version": "1.0",
        "kind": "anthropic-api-key",
        "lease_id": "test-lease",
        "api_key": KEY,
        "workspace_id": WORKSPACE,
        "not_after_utc": (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    policy = {
        "version": worker.VERSION,
        "api_version": worker.API_VERSION,
        "model": MODEL,
        "lease_id": "test-lease",
        "credential_path": str(tmp_path / "credentials/lease.json"),
        "client_read_roots": [str(tmp_path / "client")],
        "max_output_tokens": 512,
        "deadline_monotonic": time.monotonic() + 5,
        "request_sha256": hashlib.sha256(raw).hexdigest(),
        "scope": str(tmp_path),
    }
    write(tmp_path / "credentials/lease.json", canonical_json(lease).encode())
    write(tmp_path / "policy.json", canonical_json(policy).encode())
    write(tmp_path / "attempt/request.bin", raw)
    write(tmp_path / "attempt/response.bin", b"")
    return policy, lease, raw


class Response:
    def __init__(self, body=b'{"type":"message","fixture":true}', status=200, headers=None):
        self.status = status
        self.headers = Message()
        for name, value in (
            headers
            if headers is not None
            else [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
            ]
        ):
            self.headers.add_header(name, value)
        self.body = io.BytesIO(body)
        self.closed = False

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read1(self, size):
        return self.body.read(size)

    def close(self):
        self.closed = True


def run(tmp_path, response=None, *, fail=False):
    calls = []
    response = Response() if response is None else response

    class Connection:
        def __init__(self, host, port, *, timeout, context):
            assert (host, port) == (worker.HOST, 443)
            assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
            assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
            assert timeout > 0
            self.closed = False

        def request(self, method, path, *, body, headers):
            calls.append((method, path, body, headers))
            if fail:
                raise OSError(KEY + " must never be logged")

        def getresponse(self):
            return response

        def close(self):
            self.closed = True

    support = Path(worker.__file__).with_name("subscription_worker.py")
    code = worker.run(
        tmp_path / "policy.json",
        tmp_path / "attempt/request.bin",
        tmp_path / "attempt/response.bin",
        support_sha256=hashlib.sha256(support.read_bytes()).hexdigest(),
        connection_factory=Connection,
    )
    result = json.loads((tmp_path / "attempt/provider-result.json").read_text())
    return code, result, calls


def assert_private(tmp_path):
    for path in (tmp_path / "attempt").rglob("*"):
        if path.is_file():
            assert KEY.encode() not in path.read_bytes()
            assert WORKSPACE.encode() not in path.read_bytes()


def test_one_fixed_send_has_no_proxy_retry_or_secret_receipt(tmp_path, monkeypatch):
    _, _, raw = inputs(tmp_path)
    monkeypatch.setenv("HTTPS_PROXY", "http://unapproved.invalid:1234")
    code, result, calls = run(tmp_path)
    assert code == 0 and len(calls) == 1
    method, route, outgoing, headers = calls[0]
    assert method == "POST" and route == "/v1/messages" and outgoing == raw
    assert headers["Authorization"] == "Bearer " + KEY
    assert headers["anthropic-workspace-id"] == WORKSPACE
    assert headers["anthropic-version"] == "2026-10-21"
    assert "x-api-key" not in headers and "Proxy-Authorization" not in headers
    assert result["status"] == "response_received" and result["request_may_have_been_sent"]
    assert result["remote_stop_verified"] is False and result["usage"] is None
    intent = json.loads((tmp_path / "attempt/provider-intent.json").read_text())
    assert intent["automatic_retries"] == 0 and intent["api_version"] == worker.API_VERSION
    assert_private(tmp_path)


@pytest.mark.parametrize("status", [301, 307, 400, 401, 403, 429, 500, 529])
def test_http_error_and_redirect_never_retry_or_save_server_body(tmp_path, status):
    inputs(tmp_path)
    code, result, calls = run(tmp_path, Response(KEY.encode(), status=status))
    assert code == 125 and result["status"] == "http_status" and len(calls) == 1
    assert result["body_bytes_read"] == 0
    assert (tmp_path / "attempt/response.bin").read_bytes() == b""
    assert_private(tmp_path)


@pytest.mark.parametrize(
    "body",
    [
        json.dumps({"echo": KEY}).encode(),
        ('{"echo":"' + "".join("\\u%04x" % ord(c) for c in KEY) + '"}').encode(),
        json.dumps({"echo": WORKSPACE}).encode(),
        json.dumps({KEY: "value"}).encode(),
    ],
)
def test_secret_or_workspace_reflections_are_discarded_even_when_json_escaped(tmp_path, body):
    inputs(tmp_path)
    code, result, calls = run(tmp_path, Response(body))
    assert code == 125 and result["status"] == "credential_reflection" and len(calls) == 1
    assert (tmp_path / "attempt/response.bin").read_bytes() == b""
    assert_private(tmp_path)


@pytest.mark.parametrize(
    "headers,body,reason",
    [
        (
            [("Content-Type", "application/json"), ("Content-Type", "application/json")],
            b"{}",
            "response_framing",
        ),
        (
            [
                ("Content-Type", "application/json"),
                ("Content-Length", "2"),
                ("Transfer-Encoding", "chunked"),
            ],
            b"{}",
            "response_framing",
        ),
        (
            [("Content-Type", "application/json"), ("Content-Encoding", "gzip")],
            b"{}",
            "response_headers",
        ),
        ([], b"{}", "response_headers"),
        (
            [("Content-Type", "application/json"), ("Content-Length", "3")],
            b"{}",
            "incomplete_response",
        ),
        ([("Content-Type", "application/json")], b"not JSON", "transport_failure"),
        ([("Content-Type", "application/json")], b'{"a":1,"a":2}', "invalid_json"),
        ([("Content-Type", "application/json")], b'{"a":NaN}', "invalid_json"),
        (
            [("Content-Type", "application/json")],
            b"x" * (worker.MAX_RESPONSE + 1),
            "response_limit",
        ),
    ],
)
def test_bad_protocol_bytes_are_not_persisted_as_a_complete_response(
    tmp_path, headers, body, reason
):
    inputs(tmp_path)
    code, result, calls = run(tmp_path, Response(body, headers=headers))
    assert code == 125 and result["status"] == reason and len(calls) == 1
    assert (tmp_path / "attempt/response.bin").read_bytes() == b""
    assert_private(tmp_path)


def test_unknown_send_error_preserves_intent_without_error_text(tmp_path):
    inputs(tmp_path)
    code, result, calls = run(tmp_path, fail=True)
    assert code == 125 and len(calls) == 1
    assert result["status"] == "transport_failure" and result["request_may_have_been_sent"]
    assert (tmp_path / "attempt/provider-intent.json").exists()
    assert_private(tmp_path)


@pytest.mark.parametrize(
    "problem",
    [
        "request",
        "lease-id",
        "expiry",
        "workspace",
        "key-newline",
        "key-public",
        "key-symlink",
        "key-hardlink",
        "client-scope",
        "deadline",
    ],
)
def test_preflight_rejects_before_any_connection_or_send(tmp_path, problem):
    policy, lease, raw = inputs(tmp_path)
    key_path = tmp_path / "credentials/lease.json"
    if problem == "request":
        value = json.loads(raw)
        value["tools"] = [{"name": "exec_command"}]
        changed = canonical_json(value).encode()
        write(tmp_path / "attempt/request.bin", changed)
        policy["request_sha256"] = hashlib.sha256(changed).hexdigest()
        key_path.unlink()  # A rejected request must not need this file.
    elif problem == "lease-id":
        lease["lease_id"] = "different"
    elif problem == "expiry":
        lease["not_after_utc"] = "2000-01-01T00:00:00Z"
    elif problem == "workspace":
        lease["workspace_id"] = "unqualified"
    elif problem == "key-newline":
        lease["api_key"] += "\nInjected: value"
    elif problem == "key-public":
        key_path.chmod(0o644)
    elif problem == "key-symlink":
        key_path.rename(tmp_path / "credentials/real.json")
        key_path.symlink_to(tmp_path / "credentials/real.json")
    elif problem == "key-hardlink":
        (tmp_path / "credentials/link.json").hardlink_to(key_path)
    elif problem == "client-scope":
        policy["client_read_roots"] = [str(tmp_path)]
    else:
        policy["deadline_monotonic"] = time.monotonic() - 1
    if problem in ("lease-id", "expiry", "workspace", "key-newline"):
        write(key_path, canonical_json(lease).encode())
    write(tmp_path / "policy.json", canonical_json(policy).encode())
    code, result, calls = run(tmp_path)
    assert code == 125 and calls == [] and not result["request_may_have_been_sent"]
    assert not (tmp_path / "attempt/provider-intent.json").exists()
    assert_private(tmp_path)


def test_support_identity_is_checked_before_policy_or_credential_read(tmp_path):
    with pytest.raises(ValueError, match="support identity"):
        worker.run(
            tmp_path / "absent",
            tmp_path / "absent-request",
            tmp_path / "absent-response",
            support_sha256="0" * 64,
        )


def test_scope_constructor_never_opens_the_credential_and_refuses_client_or_git_scope(tmp_path):
    tmp_path.chmod(0o700)
    (tmp_path / "client").mkdir(mode=0o700)
    (tmp_path / "auth").mkdir(mode=0o700)
    scoped = ScopedAnthropicUpstream(
        tmp_path / "upstream",
        credential_path=tmp_path / "auth/nonexistent.json",
        lease_id="lease",
        model=MODEL,
        client_read_roots=(tmp_path / "client",),
        max_output_tokens=512,
        deadline_monotonic=time.monotonic() + 3,
    )
    assert scoped.stop_audit() == {"state": "not_launched"}
    with pytest.raises(ValueError):
        ScopedAnthropicUpstream(
            tmp_path / "other",
            credential_path=tmp_path / "client/lease.json",
            lease_id="lease",
            model=MODEL,
            client_read_roots=(tmp_path / "client",),
            max_output_tokens=512,
            deadline_monotonic=time.monotonic() + 3,
        )
    (tmp_path / "auth/.git").mkdir()
    with pytest.raises(ValueError):
        ScopedAnthropicUpstream(
            tmp_path / "other",
            credential_path=tmp_path / "auth/lease.json",
            lease_id="lease",
            model=MODEL,
            client_read_roots=(tmp_path / "client",),
            max_output_tokens=512,
            deadline_monotonic=time.monotonic() + 3,
        )
