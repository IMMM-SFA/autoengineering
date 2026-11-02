"""Fixed subscription transport against authored loopback HTTP fixtures only."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import ssl
import sys
import threading
import time

import pytest

from autoengineering.agents.hosts import subscription_worker as worker
from autoengineering.agents.hosts.command_upstream import (
    CommandUpstream,
    UpstreamProcessError,
    recover_command_upstream,
)
from autoengineering.agents.hosts.subscription import (
    ScopedSubscriptionUpstream,
    recover_subscription_response,
)
from autoengineering.agents.process import recover_watchdog_stop
from autoengineering.campaign.serialization import canonical_json
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL, response_stream

TOKEN = "authored-fixture-bearer-never-a-real-credential"
ACCOUNT = "authored-fixture-account"


def write(path, raw):
    path.write_bytes(raw)
    path.chmod(0o600)


def inputs(tmp_path, *, seconds=3):
    tmp_path.chmod(0o700)
    secrets = tmp_path / "credentials"
    secrets.mkdir(mode=0o700)
    attempt = tmp_path / "attempt"
    attempt.mkdir(mode=0o700)
    request = canonical_json(
        {
            "model": OFFLINE_MODEL,
            "instructions": worker.TRUSTED_INSTRUCTIONS,
            "stream": True,
            "store": False,
            "input": [
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "approved"}],
                }
            ],
            "tools": [],
            "tool_choice": "none",
            "parallel_tool_calls": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "role_response",
                    "strict": True,
                    "schema": {"type": "object"},
                }
            },
        }
    ).encode()
    auth = {
        "schema_version": "1.0",
        "kind": "codex-chatgpt-bearer",
        "lease_id": "test-lease",
        "bearer_token": TOKEN,
        "account_id": ACCOUNT,
        "not_after_utc": (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }
    write(secrets / "lease.json", canonical_json(auth).encode())
    policy = {
        "version": worker.VERSION,
        "model": OFFLINE_MODEL,
        "lease_id": "test-lease",
        "credential_path": str(secrets / "lease.json"),
        "deadline_monotonic": time.monotonic() + seconds,
        "request_sha256": hashlib.sha256(request).hexdigest(),
        "scope": str(tmp_path),
    }
    write(attempt / "request.bin", request)
    write(attempt / "response.bin", b"")
    write(tmp_path / "policy.json", canonical_json(policy).encode())
    return policy, auth, request, attempt


@contextmanager
def server(
    *,
    body=None,
    status=200,
    extra_headers=(),
    pause=0,
    chunked=False,
    header_drip=False,
    content_type="text/event-stream",
):
    requests = []
    body = response_stream() if body is None else body

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append((self.path, dict(self.headers), raw))
            if header_drip:
                try:
                    self.wfile.write(b"HTTP/1.1 200 OK\r\nX-Slow: ")
                    self.wfile.flush()
                    for _ in range(30):
                        self.wfile.write(b"x")
                        self.wfile.flush()
                        time.sleep(0.03)
                except OSError:
                    pass
                return
            self.send_response(status)
            if content_type is not None:
                self.send_header("Content-Type", content_type)
            self.send_header(
                "Transfer-Encoding" if chunked else "Content-Length",
                "chunked" if chunked else str(len(body)),
            )
            for name, value in extra_headers:
                self.send_header(name, value)
            self.end_headers()
            try:
                if pause:
                    self.wfile.write(body[:1])
                    self.wfile.flush()
                    time.sleep(pause)
                    self.wfile.write(body[1:])
                elif chunked:
                    for offset in range(0, len(body), 37):
                        chunk = body[offset : offset + 37]
                        self.wfile.write(f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n")
                    self.wfile.write(b"0\r\n\r\n")
                else:
                    self.wfile.write(body)
            except OSError:
                pass

    class QuietServer(HTTPServer):
        def handle_error(self, *_):
            pass

    httpd = QuietServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()

    def factory(host, port, *, context, timeout):
        assert (host, port) == ("chatgpt.com", 443)
        assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
        assert context.minimum_version >= ssl.TLSVersion.TLSv1_2
        return http.client.HTTPConnection("127.0.0.1", httpd.server_port, timeout=timeout)

    try:
        yield factory, requests, httpd.server_port
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def run(tmp_path, factory):
    attempt = tmp_path / "attempt"
    result = worker.run(
        tmp_path / "policy.json",
        attempt / "request.bin",
        attempt / "response.bin",
        connection_factory=factory,
    )
    receipt = json.loads((attempt / "provider-result.json").read_text())
    return result, receipt


def assert_no_credentials(tree):
    for path in tree.rglob("*"):
        if path.is_file():
            raw = path.read_bytes()
            assert TOKEN.encode() not in raw and ACCOUNT.encode() not in raw


@pytest.mark.parametrize("chunked", [False, True])
def test_one_fixed_destination_request_no_proxy_redirect_or_credential_artifacts(
    tmp_path, monkeypatch, chunked
):
    policy, auth, request, attempt = inputs(tmp_path)
    monkeypatch.setenv("HTTPS_PROXY", "http://must-not-be-used.invalid:81")
    with server(chunked=chunked) as (factory, calls, _):
        code, receipt = run(tmp_path, factory)
    assert code == 0 and receipt["status"] == "response_received" and receipt["usage"] is None
    assert receipt["request_may_have_been_sent"] is True
    assert len(calls) == 1 and calls[0][0] == worker.ROUTE and calls[0][2] == request
    assert calls[0][1]["Authorization"] == "Bearer " + TOKEN
    assert calls[0][1]["ChatGPT-Account-ID"] == ACCOUNT
    assert (attempt / "response.bin").read_bytes() == response_stream()
    assert_no_credentials(attempt)


@pytest.mark.parametrize("status", [301, 307, 401, 429, 500])
def test_errors_never_redirect_retry_or_persist_untrusted_error_body(tmp_path, status):
    _, _, _, attempt = inputs(tmp_path)
    with server(
        status=status,
        body=TOKEN.encode(),
        extra_headers=[("Location", "https://unapproved.invalid/")],
    ) as (factory, calls, _):
        code, receipt = run(tmp_path, factory)
    assert code == 125 and receipt["status"] == "http_status" and receipt["http_status"] == status
    assert len(calls) == 1 and not (attempt / "response.bin").read_bytes()
    assert_no_credentials(attempt)


@pytest.mark.parametrize("problem", ["missing", "changed", "non_string"])
def test_fixed_instructions_cannot_be_removed_or_replaced(tmp_path, problem):
    policy, _, raw, attempt = inputs(tmp_path)
    value = json.loads(raw)
    if problem == "missing":
        value.pop("instructions")
    else:
        value["instructions"] = [] if problem == "non_string" else "unapproved instruction"
    raw = canonical_json(value).encode()
    write(attempt / "request.bin", raw)
    policy["request_sha256"] = hashlib.sha256(raw).hexdigest()
    write(tmp_path / "policy.json", canonical_json(policy).encode())
    code, receipt = run(
        tmp_path, lambda *a, **k: pytest.fail("invalid instructions must not connect")
    )
    assert code == 125 and receipt["status"] == "request_policy"
    assert not (attempt / "provider-intent.json").exists()


@pytest.mark.parametrize(
    "body,expected",
    [
        (
            b'{"detail":"Instructions are required"}',
            {
                "state": "classified",
                "code": "missing_required_parameter",
                "parameter": "instructions",
            },
        ),
        (
            b'{"error":{"code":"unsupported_parameter","param":"tool_choice","message":"private server text"}}',
            {"state": "classified", "code": "unsupported_parameter", "parameter": "tool_choice"},
        ),
        (
            b'{"detail":"Unsupported parameter: tool_choice"}',
            {"state": "classified", "code": "unsupported_parameter", "parameter": "tool_choice"},
        ),
        (
            b'{"error":{"code":"private-server-value","param":"private-field"}}',
            {"state": "unrecognized", "code": None, "parameter": None},
        ),
        (b'{"detail":"' + TOKEN.encode() + b'"}', {"state": "redacted"}),
        (
            json.dumps({"detail": "".join(f"\\u{ord(c):04x}" for c in TOKEN)})
            .replace("\\\\u", "\\u")
            .encode(),
            {"state": "redacted"},
        ),
        (json.dumps({"detail": ACCOUNT}).encode(), {"state": "redacted"}),
        (b"x" * (worker.MAX_ERROR_BODY + 1), {"state": "size_limit"}),
        (b"not-json", {"state": "unrecognized"}),
    ],
    ids=[
        "required-instructions",
        "known-parameter",
        "detail-parameter",
        "untrusted-fields",
        "token",
        "encoded-token",
        "account",
        "oversize",
        "invalid-json",
    ],
)
def test_error_diagnostics_are_bounded_fixed_vocabulary_and_never_raw(tmp_path, body, expected):
    _, _, _, attempt = inputs(tmp_path)
    with server(status=400, body=body) as (factory, calls, _):
        code, receipt = run(tmp_path, factory)
    assert code == 125 and receipt["status"] == "http_status" and receipt["http_status"] == 400
    assert receipt["error_diagnostic"] == expected
    assert receipt["body_bytes_read"] <= worker.MAX_ERROR_BODY + 1
    assert len(calls) == 1 and not (attempt / "response.bin").read_bytes()
    assert b"private-server-value" not in (attempt / "provider-result.json").read_bytes()
    assert b"private server text" not in (attempt / "provider-result.json").read_bytes()
    assert_no_credentials(attempt)


def test_error_diagnostic_deadline_does_not_retry_or_hide_http_status(tmp_path):
    _, _, _, attempt = inputs(tmp_path, seconds=0.15)
    with server(status=400, body=b'{"detail":"Instructions are required"}', pause=0.4) as (
        factory,
        calls,
        _,
    ):
        code, receipt = run(tmp_path, factory)
    assert code == 125 and receipt["http_status"] == 400 and receipt["status"] == "http_status"
    assert receipt["error_diagnostic"]["state"] == "incomplete"
    assert len(calls) == 1 and not (attempt / "response.bin").read_bytes()


@pytest.mark.parametrize(
    "problem", ["lease", "expiry", "permissions", "symlink", "hardlink", "header"]
)
def test_invalid_credentials_never_reach_connection_factory(tmp_path, problem):
    policy, auth, _, attempt = inputs(tmp_path)
    path = Path(policy["credential_path"])
    if problem == "lease":
        auth["lease_id"] = "foreign-lease"
    elif problem == "expiry":
        auth["not_after_utc"] = "2000-01-01T00:00:00Z"
    elif problem == "header":
        auth["bearer_token"] = "invalid\r\nInjected: value"
    write(path, canonical_json(auth).encode())
    if problem == "permissions":
        path.chmod(0o644)
    elif problem == "symlink":
        target = path.with_name("real.json")
        path.rename(target)
        path.symlink_to(target)
    elif problem == "hardlink":
        import os

        os.link(path, path.with_name("another.json"))
    code, receipt = run(
        tmp_path, lambda *a, **k: pytest.fail("credential preflight must not connect")
    )
    assert code == 125 and receipt["phase"] == "preflight"
    assert not (attempt / "provider-intent.json").exists()
    assert_no_credentials(attempt)


@pytest.mark.parametrize("problem", ["tools", "extra", "digest", "model"])
def test_worker_rechecks_approved_request_policy_before_credentials_or_network(tmp_path, problem):
    policy, _, request, attempt = inputs(tmp_path)
    value = json.loads(request)
    if problem == "tools":
        value["tools"] = [{"type": "function", "name": "shell"}]
    elif problem == "extra":
        value["previous_response_id"] = "foreign-state"
    elif problem == "model":
        value["model"] = "unapproved-model"
    else:
        value["input"][0]["content"][0]["text"] = "changed"
    raw = canonical_json(value).encode()
    write(attempt / "request.bin", raw)
    if problem != "digest":
        policy["request_sha256"] = hashlib.sha256(raw).hexdigest()
        write(tmp_path / "policy.json", canonical_json(policy).encode())
    code, receipt = run(tmp_path, lambda *a, **k: pytest.fail("request preflight must not connect"))
    assert code == 125 and receipt["phase"] == "preflight"
    assert_no_credentials(attempt)


@pytest.mark.parametrize(
    "body,headers,reason",
    [
        (b"x" * 524289, [], "response_limit"),
        (response_stream(), [("Content-Encoding", "gzip")], "response_headers"),
        (response_stream(), [("X-Flood", "x" * 17000)], "wire_limit"),
        (response_stream(), [("Content-Length", "1")], "response_framing"),
        (b'data: {"text":"' + TOKEN.encode() + b'"}\n\n', [], "credential_reflection"),
        (
            ('data: {"text":"' + "".join(f"\\u{ord(c):04x}" for c in TOKEN) + '"}\n\n').encode(),
            [],
            "credential_reflection",
        ),
    ],
    ids=["oversize", "encoding", "headers", "framing", "raw-reflection", "escaped-reflection"],
)
def test_response_limits_framing_and_secret_reflection_never_deliver_bytes(
    tmp_path, body, headers, reason
):
    _, _, _, attempt = inputs(tmp_path)
    with server(body=body, extra_headers=headers) as (factory, calls, _):
        code, receipt = run(tmp_path, factory)
    assert code == 125 and receipt["status"] == reason and len(calls) == 1
    if reason == "response_headers":
        assert receipt["header_diagnostic"] == {
            "content_type": "text/event-stream",
            "content_encoding": "gzip",
        }
    assert not (attempt / "response.bin").read_bytes()
    assert_no_credentials(attempt)


@pytest.mark.parametrize(
    "mime,encoding,expected",
    [
        ("application/json; charset=utf-8", "identity", ("application/json", "identity")),
        ("text/html", "br", ("text/html", "br")),
        (TOKEN, ACCOUNT, ("redacted", "other")),
        ("", "identity", ("missing", "identity")),
        (
            "application/vnd.openai.responses+json",
            "identity",
            ("application/vnd.openai.responses+json", "identity"),
        ),
        ("text/" + ACCOUNT, "identity", ("redacted", "identity")),
        ("text/" + "a" * 129, "identity", ("other", "identity")),
    ],
)
def test_header_diagnostic_is_bounded_and_redacts_credentials(mime, encoding, expected):
    class Response:
        def getheader(self, name, default=None):
            return {"Content-Type": mime, "Content-Encoding": encoding}.get(name, default)

    result = worker.classify_response_headers(
        Response(), {"bearer_token": TOKEN, "account_id": ACCOUNT}
    )
    assert (result["content_type"], result["content_encoding"]) == expected
    assert TOKEN not in json.dumps(result) and ACCOUNT not in json.dumps(result)


def test_body_deadline_keeps_partial_response_private_and_usage_unknown(tmp_path):
    _, _, _, attempt = inputs(tmp_path, seconds=0.15)
    with server(pause=0.4) as (factory, calls, _):
        code, receipt = run(tmp_path, factory)
    assert code == 125 and receipt["status"] == "timeout" and len(calls) == 1
    assert receipt["usage"] is None and not (attempt / "response.bin").read_bytes()


def test_nonobject_policy_fails_with_static_receipt_and_no_network(tmp_path):
    _, _, _, attempt = inputs(tmp_path)
    write(tmp_path / "policy.json", b"[]")
    code, receipt = run(tmp_path, lambda *a, **k: pytest.fail("invalid policy must not connect"))
    assert code == 125 and receipt["status"] == "transport_policy"
    assert receipt["scope"] is None and not (attempt / "provider-intent.json").exists()


@pytest.mark.parametrize("spacing", ["", "   ", "multiline"])
def test_encoded_credential_reflection_checks_every_accepted_sse_data_form(tmp_path, spacing):
    _, _, _, attempt = inputs(tmp_path)
    value = '"' + "".join(f"\\u{ord(c):04x}" for c in TOKEN) + '"'
    body = (
        'data:{"text":\ndata:' + value + "}\n\n"
        if spacing == "multiline"
        else "data:" + spacing + '{"text":' + value + "}\n\n"
    ).encode()
    with server(body=body) as (factory, calls, _):
        code, receipt = run(tmp_path, factory)
    assert code == 125 and receipt["status"] == "credential_reflection" and len(calls) == 1
    assert not (attempt / "response.bin").read_bytes()
    assert_no_credentials(attempt)


def test_scoped_callback_refuses_credentials_in_client_roots_and_normalizes_parent_traversal(
    tmp_path,
):
    inputs(tmp_path)
    client = tmp_path / "client"
    client.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="scope"):
        ScopedSubscriptionUpstream(
            tmp_path / "call",
            credential_path=client / "lease.json",
            lease_id="lease",
            model=OFFLINE_MODEL,
            client_roots=(client,),
            deadline_monotonic=time.monotonic() + 3,
        )

    with pytest.raises(ValueError, match="scope"):
        ScopedSubscriptionUpstream(
            tmp_path / "call",
            credential_path=tmp_path / "credentials/../client/lease.json",
            lease_id="lease",
            model=OFFLINE_MODEL,
            client_roots=(client,),
            deadline_monotonic=time.monotonic() + 3,
        )


@pytest.mark.parametrize("cancelled", [False, True])
def test_real_scoped_command_failure_and_cancellation_do_not_read_or_expose_credentials(
    tmp_path, cancelled
):
    policy, _, request, _ = inputs(tmp_path)
    client = tmp_path / "client"
    client.mkdir(mode=0o700)
    callback = ScopedSubscriptionUpstream(
        tmp_path / "call",
        credential_path=Path(policy["credential_path"]),
        lease_id="intentionally-wrong-lease",
        model=OFFLINE_MODEL,
        client_roots=(client,),
        deadline_monotonic=time.monotonic() + 3,
        cancelled=lambda: cancelled,
    )
    if cancelled:
        Path(policy["credential_path"]).unlink()
    with pytest.raises(UpstreamProcessError) as exc:
        callback(request)
    assert exc.value.status == ("cancelled" if cancelled else "host_failure")
    root = callback.directory
    assert_no_credentials(root)
    assert not (root / "attempt/provider-intent.json").exists()
    assert (root / "attempt/process/stdout.bin").read_bytes() == b""
    assert (root / "attempt/process/stderr.bin").read_bytes() == b""
    if not cancelled:
        assert recover_watchdog_stop(root / "attempt/process")["stopped"]
        Path(policy["credential_path"]).unlink()
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises(UpstreamProcessError):
        recover_subscription_response(root)
    with pytest.raises(FileExistsError):
        callback(request)
    assert before == {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("scenario", ["text", "reflection", "slow-headers"])
def test_authored_connection_in_real_owned_worker_is_bounded_and_replays_without_credentials(
    tmp_path, scenario
):
    policy, _, request, attempt = inputs(tmp_path)
    for path in attempt.iterdir():
        path.unlink()
    attempt.rmdir()
    policy["deadline_monotonic"] = time.monotonic() + (0.4 if scenario == "slow-headers" else 4)
    write(tmp_path / "policy.json", canonical_json(policy).encode())
    body = (
        b'data: {"text":"' + TOKEN.encode() + b'"}\n\n'
        if scenario == "reflection"
        else response_stream()
    )
    with server(body=body, header_drip=scenario == "slow-headers") as (_, calls, port):
        script = tmp_path / "authored-connection.py"
        script.write_text(
            "import http.client,runpy,sys\n"
            f"worker=runpy.run_path({worker.__file__!r})\n"
            "def factory(host,port,*,context,timeout):\n"
            " assert (host,port)==('chatgpt.com',443)\n"
            f" return http.client.HTTPConnection('127.0.0.1',{port},timeout=timeout)\n"
            f"raise SystemExit(worker['run']({str(tmp_path / 'policy.json')!r},sys.argv[1],sys.argv[2],connection_factory=factory))\n"
        )
        callback = CommandUpstream(
            attempt,
            command=(sys.executable, "-I", "-S", str(script), "{request}", "{response}"),
            source_files=(script, Path(worker.__file__), tmp_path / "policy.json"),
            deadline_monotonic=policy["deadline_monotonic"],
        )
        if scenario == "text":
            assert callback(request) == response_stream()
        else:
            with pytest.raises(UpstreamProcessError) as exc:
                callback(request)
            assert exc.value.status == ("timeout" if scenario == "slow-headers" else "host_failure")
    assert len(calls) == 1
    assert recover_watchdog_stop(attempt / "process")["stopped"]
    Path(policy["credential_path"]).unlink()
    assert_no_credentials(attempt)
    before = {
        str(p.relative_to(attempt)): p.read_bytes() for p in attempt.rglob("*") if p.is_file()
    }
    if scenario == "text":
        assert recover_command_upstream(attempt) == response_stream()
    else:
        with pytest.raises(UpstreamProcessError):
            recover_command_upstream(attempt)
    assert before == {
        str(p.relative_to(attempt)): p.read_bytes() for p in attempt.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize(
    "tamper",
    [
        None,
        "command",
        "scope",
        "provider",
        "sources",
        "worker_alias",
        "missing_content_type",
        "header_extra",
        "header_type",
        "header_encoding",
        "header_shape",
        "extra_result",
    ],
)
def test_subscription_recovery_binds_policy_and_provider_receipts_without_credential_access(
    tmp_path, monkeypatch, tamper
):
    # Unit-test the subscription decoder around the separately tested process
    # proof. This is not evidence of a live production HTTPS exchange.
    import autoengineering.agents.hosts.subscription as subscription

    policy, _, _, attempt = inputs(tmp_path)
    missing_mime = tamper in {
        "missing_content_type",
        "header_extra",
        "header_type",
        "header_encoding",
        "header_shape",
    }
    with server(content_type=None if missing_mime else "text/event-stream") as (factory, calls, _):
        assert run(tmp_path, factory)[0] == 0
    assert len(calls) == 1
    command = [
        str(Path(sys.executable).resolve()),
        "-I",
        "-S",
        worker.__file__,
        "--policy",
        str(tmp_path / "policy.json"),
        "--request",
        "{request}",
        "--response",
        "{response}",
    ]
    manifest = {
        "command": command,
        "sources": {
            str(Path(sys.executable).resolve()): hashlib.sha256(
                Path(sys.executable).resolve().read_bytes()
            ).hexdigest(),
            worker.__file__: hashlib.sha256(Path(worker.__file__).read_bytes()).hexdigest(),
            str(tmp_path / "policy.json"): hashlib.sha256(
                (tmp_path / "policy.json").read_bytes()
            ).hexdigest(),
        },
        "request_sha256": policy["request_sha256"],
        "deadline_monotonic": policy["deadline_monotonic"],
    }
    if tamper == "command":
        command[3] = "/unapproved/transport.py"
    if tamper == "sources":
        manifest["sources"][policy["credential_path"]] = "0" * 64
    if tamper == "worker_alias":
        source_hash = manifest["sources"].pop(command[3])
        command[3] = policy["credential_path"]
        manifest["sources"][command[3]] = source_hash
    write(attempt / "upstream.json", canonical_json(manifest).encode())
    if tamper == "scope":
        policy["scope"] = str(tmp_path / "foreign")
        write(tmp_path / "policy.json", canonical_json(policy).encode())
    if tamper == "provider":
        result = json.loads((attempt / "provider-result.json").read_text())
        result["http_status"] = 307
        write(attempt / "provider-result.json", canonical_json(result).encode())
    if tamper in {"header_extra", "header_type", "header_encoding", "header_shape", "extra_result"}:
        result = json.loads((attempt / "provider-result.json").read_text())
        if tamper == "header_extra":
            result["header_diagnostic"]["unapproved"] = True
        elif tamper == "header_type":
            result["header_diagnostic"]["content_type"] = "text/html"
        elif tamper == "header_encoding":
            result["header_diagnostic"]["content_encoding"] = "gzip"
        elif tamper == "header_shape":
            result["header_diagnostic"] = []
        else:
            result["unapproved"] = True
        write(attempt / "provider-result.json", canonical_json(result).encode())
    Path(policy["credential_path"]).unlink()
    delegated = []
    monkeypatch.setattr(
        subscription,
        "recover_command_upstream",
        lambda root: delegated.append(root) or response_stream(),
    )
    before = {
        str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }
    if tamper in (None, "missing_content_type"):
        assert recover_subscription_response(tmp_path) == response_stream()
        assert delegated == [attempt]
    else:
        with pytest.raises(ValueError, match="binding|receipt"):
            recover_subscription_response(tmp_path)
    assert before == {
        str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize(
    "body,accepted",
    [
        (response_stream(), True),
        (b"<html>challenge</html>", False),
        (b'{"error":{"code":"invalid_request_error"}}', False),
    ],
)
def test_missing_content_type_keeps_stream_and_credential_checks(tmp_path, body, accepted):
    _, _, _, attempt = inputs(tmp_path)
    with server(body=body, content_type=None) as (factory, calls, _):
        code, receipt = run(tmp_path, factory)
    assert len(calls) == 1
    assert receipt["header_diagnostic"] == {
        "content_type": "missing",
        "content_encoding": "identity",
    }
    assert code == (0 if accepted else 125)
    if accepted:
        from autoengineering.agents.hosts.response_boundary import validate_text_response

        assert (
            validate_text_response((attempt / "response.bin").read_bytes()).reported_model
            == OFFLINE_MODEL
        )
    else:
        assert receipt["status"] == "response_stream"
        assert not (attempt / "response.bin").read_bytes()
    assert_no_credentials(attempt)


def test_missing_content_type_does_not_allow_tool_stream(tmp_path):
    _, _, _, attempt = inputs(tmp_path)
    with server(body=response_stream(tool_command="forbidden"), content_type=None) as (
        factory,
        calls,
        _,
    ):
        code, receipt = run(tmp_path, factory)
    assert code == 0 and len(calls) == 1
    from autoengineering.agents.hosts.response_boundary import (
        validate_text_response,
        ResponseBoundaryError,
    )

    with pytest.raises(ResponseBoundaryError, match="forbidden"):
        validate_text_response((attempt / "response.bin").read_bytes())
    assert_no_credentials(attempt)
