"""Actual TLS on loopback with a private ephemeral CA and synthetic lease.

The authored factory overrides TCP routing only. Verification stays enabled.
No production host is contacted and no existing credential is opened.
"""

from contextlib import contextmanager
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import shutil
import socket
import ssl
import subprocess
import threading

import pytest

from autoengineering.agents.hosts import subscription_worker as worker
from examples.agent_campaign.probe_external_codex import response_stream
from test_agent_subscription import ACCOUNT, TOKEN, assert_no_credentials, inputs, run


@pytest.fixture(scope="module")
def certificate(tmp_path_factory):
    root = tmp_path_factory.mktemp("subscription-tls")
    root.chmod(0o700)
    executable = shutil.which("openssl")
    if executable is None:
        pytest.skip("TLS fixture certificate generation requires openssl")
    key, cert = root / "server-key.pem", root / "fixture-ca.pem"
    result = subprocess.run(
        [
            executable,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=chatgpt.com",
            "-addext",
            "subjectAltName=DNS:chatgpt.com",
        ],
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, "authored TLS certificate generation failed"
    key.chmod(0o600)
    cert.chmod(0o600)
    return key, cert


@contextmanager
def tls_server(certificate, *, trust_ca=True, hostname="chatgpt.com"):
    key, cert = certificate
    calls = []
    body = response_stream()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            calls.append(
                {
                    "path": self.path,
                    "request_sha256": hashlib.sha256(raw).hexdigest(),
                    "auth_valid": self.headers.get("Authorization") == "Bearer " + TOKEN,
                    "account_valid": self.headers.get("ChatGPT-Account-ID") == ACCOUNT,
                    "tls": self.connection.version(),
                }
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class Server(HTTPServer):
        def handle_error(self, *_):
            pass

    httpd = Server(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert, keyfile=key)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    thread = threading.Thread(
        target=httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
    )
    thread.start()

    def factory(host, port, *, context, timeout):
        assert (host, port) == (worker.HOST, worker.PORT)
        assert context.check_hostname and context.verify_mode == ssl.CERT_REQUIRED
        if trust_ca:
            context.load_verify_locations(cafile=cert)

        class Connection(http.client.HTTPSConnection):
            def connect(self):
                raw = socket.create_connection(
                    ("127.0.0.1", httpd.server_port), timeout=self.timeout
                )
                try:
                    self.sock = self._context.wrap_socket(raw, server_hostname=hostname)
                except BaseException:
                    raw.close()
                    raise

        return Connection(host, port, context=context, timeout=timeout)

    try:
        yield factory, calls
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)


def test_valid_local_tls_preserves_verification_and_delivers_one_approved_request(
    tmp_path, certificate
):
    policy, _, request, attempt = inputs(tmp_path)
    with tls_server(certificate) as (factory, calls):
        code, result = run(tmp_path, factory)
    assert code == 0 and result["status"] == "response_received"
    assert calls == [
        {
            "path": worker.ROUTE,
            "request_sha256": hashlib.sha256(request).hexdigest(),
            "auth_valid": True,
            "account_valid": True,
            "tls": calls[0]["tls"],
        }
    ]
    assert calls[0]["tls"] in ("TLSv1.2", "TLSv1.3")
    assert (attempt / "response.bin").read_bytes() == response_stream()
    assert_no_credentials(attempt)


@pytest.mark.parametrize("problem", ["untrusted-ca", "wrong-hostname"])
def test_invalid_tls_never_sends_http_or_credentials(tmp_path, certificate, problem):
    _, _, _, attempt = inputs(tmp_path)
    with tls_server(
        certificate,
        trust_ca=problem != "untrusted-ca",
        hostname="unapproved.invalid" if problem == "wrong-hostname" else worker.HOST,
    ) as (factory, calls):
        code, result = run(tmp_path, factory)
    assert code == 125 and result["status"] == "transport_failure"
    assert calls == [] and (attempt / "response.bin").read_bytes() == b""
    assert (
        result["request_may_have_been_sent"] is True
    )  # Local intent cannot prove remote processing.
    assert result["usage"] is None
    assert_no_credentials(attempt)
