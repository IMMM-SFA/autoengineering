"""Explicitly authored HTTP connection for offline subscription-worker probes.

This never selects the production HTTPS factory and never reads existing auth.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
import threading

from autoengineering.agents.hosts import subscription_worker as worker
from autoengineering.agents.hosts.command_upstream import CommandUpstream, inspect_command_stop
from autoengineering.agents.hosts.credential_lease import prepare_subscription_lease
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import durable_write

TOKEN = "authored-subscription-fixture-bearer-not-real"
ACCOUNT = "authored-subscription-fixture-account"
REFRESH_TOKEN = "authored-refresh-must-stay-in-source"
ID_TOKEN = "authored-id-must-stay-in-source"


class AuthoredSubscriptionFixture:
    def __init__(
        self,
        output,
        *,
        model,
        body,
        deadline,
        delay_response=False,
        cancelled=lambda: False,
        on_request=lambda: None,
    ):
        self.root = output / "subscription"
        self.root.mkdir(mode=0o700)
        self.credential = output / "credential-fixture"
        source_root = output / "auth-source-fixture"
        source_root.mkdir(mode=0o700)
        self.auth_source = source_root / "auth.json"
        self.model, self.deadline = model, deadline
        self.cancelled = cancelled
        self.requests = []
        self.release = threading.Event()
        owner = self
        durable_write(
            self.auth_source,
            canonical_json(
                {
                    "auth_mode": "chatgpt",
                    "OPENAI_API_KEY": None,
                    "last_refresh": datetime.now(timezone.utc).isoformat(),
                    "tokens": {
                        "access_token": TOKEN,
                        "account_id": ACCOUNT,
                        "refresh_token": REFRESH_TOKEN,
                        "id_token": ID_TOKEN,
                    },
                }
            ).encode(),
        )
        self._source_bytes = self.auth_source.read_bytes()
        self.prepared = prepare_subscription_lease(
            self.auth_source,
            self.credential,
            lease_id="authored-lease",
            expected_account_id=ACCOUNT,
            not_after_utc=(datetime.now(timezone.utc) + timedelta(minutes=5)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            client_roots=(output / "home", output / "workspace"),
        )

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_POST(self):
                raw = self.rfile.read(int(self.headers["Content-Length"]))
                valid = (
                    self.path == worker.ROUTE
                    and self.headers.get("Authorization") == "Bearer " + TOKEN
                    and self.headers.get("ChatGPT-Account-ID") == ACCOUNT
                )
                owner.requests.append(
                    {"request_sha256": hashlib.sha256(raw).hexdigest(), "valid_auth": valid}
                )
                self.send_response(200 if valid else 401)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                on_request()
                if delay_response:
                    owner.release.wait(timeout=5)
                try:
                    self.wfile.write(body)
                except OSError:
                    pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(
            target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True
        )
        self.thread.start()

    @property
    def attempt(self):
        return self.root / "attempt"

    def __call__(self, request):
        policy = self.root / "policy.json"
        durable_write(
            policy,
            canonical_json(
                {
                    "version": worker.VERSION,
                    "model": self.model,
                    "lease_id": "authored-lease",
                    "credential_path": str(self.credential / "lease.json"),
                    "deadline_monotonic": self.deadline,
                    "request_sha256": hashlib.sha256(request).hexdigest(),
                    "scope": str(self.root),
                }
            ).encode(),
        )
        source = self.root / "authored-connection.py"
        durable_write(
            source,
            (
                "import http.client,runpy,sys\n"
                f"worker=runpy.run_path({worker.__file__!r})\n"
                "def factory(host,port,*,context,timeout):\n"
                " assert (host,port)==('chatgpt.com',443)\n"
                f" return http.client.HTTPConnection('127.0.0.1',{self.server.server_port},timeout=timeout)\n"
                f"raise SystemExit(worker['run']({str(policy)!r},sys.argv[1],sys.argv[2],connection_factory=factory))\n"
            ).encode(),
        )
        callback = CommandUpstream(
            self.attempt,
            command=(sys.executable, "-I", "-S", str(source), "{request}", "{response}"),
            source_files=(source, policy, Path(worker.__file__)),
            deadline_monotonic=self.deadline,
            cancelled=self.cancelled,
        )
        return callback(request)

    def close(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def public_audit(self):
        completion = self.attempt / "process/completion.json"
        original_stopped = completion.exists() and json.loads(completion.read_text())["stopped"]
        stop_proof = inspect_command_stop(self.attempt)
        stopped = stop_proof["state"] == "verified_stopped"
        lease_bytes = self.prepared.credential_path.read_bytes()
        return {
            "authored_http_requests": len(self.requests),
            "all_auth_valid": all(r["valid_auth"] for r in self.requests),
            "upstream_stopped": bool(stopped),
            "original_upstream_stopped": bool(original_stopped),
            "upstream_stop_proof": stop_proof,
            "production_https_used": False,
            "fixture_credentials_only": True,
            "fixture_server_thread_stopped": not self.thread.is_alive(),
            "source_unchanged": self.auth_source.read_bytes() == self._source_bytes,
            "refresh_and_id_excluded_from_lease": all(
                value.encode() not in lease_bytes for value in (REFRESH_TOKEN, ID_TOKEN)
            ),
            "credential_preparation": self.prepared.receipt(),
        }
