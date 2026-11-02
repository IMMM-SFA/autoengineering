"""Real TLS on loopback with a private fixture CA and an authored API key.

The test factory changes TCP routing and adds only the ephemeral fixture trust.
Hostname/certificate verification stays enabled. No external host is contacted.
"""

from contextlib import contextmanager
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import time

import pytest

from autoengineering.agents.hosts import anthropic_worker as worker
from autoengineering.agents.hosts.anthropic_upstream import verify_anthropic_attempt
from autoengineering.agents.hosts.command_upstream import (
    CommandUpstream,
    inspect_command_stop,
    recover_command_upstream,
)
from test_agent_anthropic_worker import KEY, WORKSPACE, inputs, assert_private


@pytest.fixture(scope="module")
def certificate(tmp_path_factory):
    root = tmp_path_factory.mktemp("anthropic-api-tls")
    root.chmod(0o700)
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("TLS fixture generation requires openssl")
    key, cert = root / "key.pem", root / "cert.pem"
    result = subprocess.run(
        [
            openssl,
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
            "/CN=" + worker.HOST,
            "-addext",
            "subjectAltName=DNS:" + worker.HOST,
        ],
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0, "authored certificate generation failed"
    key.chmod(0o600)
    cert.chmod(0o600)
    return key, cert


@contextmanager
def tls_server(certificate, *, trust_ca=True, hostname=worker.HOST):
    key, cert = certificate
    calls = []
    body = b'{"type":"message","fixture":true}'

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers["Content-Length"]))
            calls.append(
                {
                    "path": self.path,
                    "request_sha256": hashlib.sha256(raw).hexdigest(),
                    "auth_matched": self.headers.get("Authorization") == "Bearer " + KEY,
                    "workspace_matched": self.headers.get("anthropic-workspace-id") == WORKSPACE,
                    "api_version": self.headers.get("anthropic-version"),
                    "tls": self.connection.version(),
                }
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class Server(HTTPServer):
        def handle_error(self, *_args):
            pass

    server = Server(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(certfile=cert, keyfile=key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
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
                    ("127.0.0.1", server.server_port), timeout=self.timeout
                )
                try:
                    self.sock = self._context.wrap_socket(raw, server_hostname=hostname)
                except BaseException:
                    raw.close()
                    raise

        return Connection(host, port, context=context, timeout=timeout)

    try:
        factory.fixture_port = server.server_port
        yield factory, calls, body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
        assert not thread.is_alive()


def execute(tmp_path, factory):
    support = Path(worker.__file__).with_name("subscription_worker.py")
    return worker.run(
        tmp_path / "policy.json",
        tmp_path / "attempt/request.bin",
        tmp_path / "attempt/response.bin",
        support_sha256=hashlib.sha256(support.read_bytes()).hexdigest(),
        connection_factory=factory,
    )


def test_verified_loopback_tls_delivers_one_request_and_no_secret_receipt(tmp_path, certificate):
    _, _, raw = inputs(tmp_path)
    with tls_server(certificate) as (factory, calls, body):
        assert execute(tmp_path, factory) == 0
    assert len(calls) == 1
    assert calls[0]["path"] == "/v1/messages"
    assert calls[0]["request_sha256"] == hashlib.sha256(raw).hexdigest()
    assert calls[0]["auth_matched"] and calls[0]["workspace_matched"]
    assert calls[0]["api_version"] == "2026-10-21"
    assert calls[0]["tls"] in ("TLSv1.2", "TLSv1.3")
    assert (tmp_path / "attempt/response.bin").read_bytes() == body
    assert_private(tmp_path)


@pytest.mark.parametrize("problem", ["untrusted-ca", "wrong-hostname"])
def test_invalid_tls_never_sends_http_or_authentication(tmp_path, certificate, problem):
    inputs(tmp_path)
    with tls_server(
        certificate,
        trust_ca=problem != "untrusted-ca",
        hostname="unapproved.invalid" if problem == "wrong-hostname" else worker.HOST,
    ) as (factory, calls, _body):
        assert execute(tmp_path, factory) == 125
    assert calls == [] and (tmp_path / "attempt/response.bin").read_bytes() == b""
    assert_private(tmp_path)


def test_owned_isolated_worker_with_fixture_routing_stops_and_replays(tmp_path, certificate):
    """The shim permits a local peer only. It must fail production command admission."""
    _, _, raw = inputs(tmp_path)
    for path in (tmp_path / "attempt").iterdir():
        path.unlink()
    (tmp_path / "attempt").rmdir()
    source = Path(worker.__file__).resolve()
    support = source.with_name("subscription_worker.py")
    shim = tmp_path / "fixture-routing.py"
    shim.write_text(
        "import hashlib,http.client,socket,ssl,sys\n"
        "from pathlib import Path\n"
        "assert sys.flags.isolated and sys.flags.no_site\n"
        "assert 'autoengineering' not in sys.modules\n"
        "source,expected,support,policy,cert,port,request,response=sys.argv[1:]\n"
        "raw=Path(source).read_bytes()\n"
        "assert hashlib.sha256(raw).hexdigest()==expected\n"
        "namespace={'__file__':source,'__name__':'_fixture_worker'}\n"
        "exec(compile(raw,source,'exec'),namespace)\n"
        "def factory(host,number,*,context,timeout):\n"
        " assert host=='api.anthropic.com' and number==443\n"
        " assert context.check_hostname and context.verify_mode==ssl.CERT_REQUIRED\n"
        " context.load_verify_locations(cafile=cert)\n"
        " class Connection(http.client.HTTPSConnection):\n"
        "  def connect(self):\n"
        "   raw=socket.create_connection(('127.0.0.1',int(port)),timeout=self.timeout)\n"
        "   try: self.sock=self._context.wrap_socket(raw,server_hostname=host)\n"
        "   except BaseException: raw.close(); raise\n"
        " return Connection(host,number,context=context,timeout=timeout)\n"
        "raise SystemExit(namespace['run'](Path(policy),Path(request),Path(response),"
        "support_sha256=support,connection_factory=factory))\n"
    )
    launches = []
    with tls_server(certificate) as (factory, calls, body):
        callback = CommandUpstream(
            tmp_path / "attempt",
            command=(
                sys.executable,
                "-I",
                "-S",
                str(shim),
                str(source),
                hashlib.sha256(source.read_bytes()).hexdigest(),
                hashlib.sha256(support.read_bytes()).hexdigest(),
                str(tmp_path / "policy.json"),
                str(certificate[1]),
                str(factory.fixture_port),
                "{request}",
                "{response}",
            ),
            source_files=(shim, source, support, tmp_path / "policy.json", certificate[1]),
            deadline_monotonic=time.monotonic() + 5,
            on_launch=launches.append,
        )
        assert callback(raw) == body
        assert len(calls) == len(launches) == 1
        assert inspect_command_stop(tmp_path / "attempt")["state"] == "verified_stopped"
        # Remove the authored lease. Recovery must use saved response evidence.
        (tmp_path / "credentials/lease.json").unlink()
        before = {
            str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
        }
        assert recover_command_upstream(tmp_path / "attempt") == body
        with pytest.raises(FileExistsError):
            callback(raw)
        assert len(calls) == len(launches) == 1
        assert before == {
            str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
        }
    result = json.loads((tmp_path / "attempt/provider-result.json").read_text())
    assert result["status"] == "response_received"
    assert result["remote_stop_verified"] is False
    assert_private(tmp_path)
    with pytest.raises(ValueError, match="binding"):
        verify_anthropic_attempt(tmp_path)
