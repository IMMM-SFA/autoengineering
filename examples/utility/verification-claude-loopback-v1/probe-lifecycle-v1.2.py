"""Exercise native Claude against an authored loopback peer, never an upstream.

Only synthetic input and an authored credential are used. The candidate kernel
policy denies external network access. This is not a live model conformance call.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import platform
import sys
import threading
import time

from autoengineering.agents.hosts.claude import (
    inspect_claude, execute_claude_transport, recover_claude_transport,
)
from autoengineering.agents.hosts.claude_policy import (
    ClaudeEgress, ClaudePolicy, VERSION, render_claude_policy,
)
from autoengineering.agents.identity import host_source_identity

MODEL = "claude-sonnet-4-6"
KEY = "synthetic-loopback-fixture"
MAX_REQUEST = 1024 * 1024


@contextmanager
def peer(root, case):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def do_GET(self):
            self.reply(404, b'{"error":"no discovery"}', "application/json")

        def reply(self, status, data, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass
            self.close_connection = True

        def do_POST(self):
            self.connection.settimeout(1)
            try:
                size = int(self.headers.get("Content-Length", "-1"))
                if not 0 <= size <= MAX_REQUEST or len(requests) >= 4:
                    self.reply(413, b"{}", "application/json")
                    return
                raw = self.rfile.read(size)
                if len(raw) != size:
                    raise ValueError("short request")
                value = json.loads(raw)
                auth = (
                    self.headers.get("x-api-key") == KEY
                    or self.headers.get("Authorization") == "Bearer " + KEY
                )
                record = {
                    "path": self.path, "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "synthetic_auth_matched": auth, "requested_model": value.get("model"),
                    "stream": value.get("stream"), "tools": value.get("tools", []),
                    "output_config": value.get("output_config"),
                }
                requests.append(record)
                (root / f"request-{len(requests)}.json").write_bytes(raw)
                if (
                    self.path.split("?")[0] != "/v1/messages" or not auth
                    or value.get("model") != MODEL
                    or [t.get("name") for t in value.get("tools", [])] != ["StructuredOutput"]
                ):
                    self.reply(403, b"{}", "application/json")
                    return
                # The native CLI requests its StructuredOutput pseudo-tool even
                # with user tools disabled. This authored API event exercises
                # that fixed output mechanism, not an LLM or arbitrary tool.
                if case in ("timeout", "cancel"):
                    stopping.wait(20)
                text = json.dumps({
                    "handoff_json": "x" * 60000 if case == "output_limit"
                    else "synthetic controlled peer",
                })
                message = {
                    "id": "msg_synthetic_local", "type": "message", "role": "assistant",
                    "content": [], "model": MODEL, "stop_reason": None,
                    "stop_sequence": None, "usage": {
                        "input_tokens": 10, "output_tokens": 0,
                        "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0,
                    },
                }
                events = [
                    ("message_start", {"type": "message_start", "message": message}),
                    ("content_block_start", {"type": "content_block_start", "index": 0,
                                              "content_block": {"type": "tool_use",
                                                  "id": "toolu_synthetic_local",
                                                  "name": "StructuredOutput", "input": {}}}),
                    ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                              "delta": {"type": "input_json_delta",
                                                        "partial_json": text}}),
                    ("content_block_stop", {"type": "content_block_stop", "index": 0}),
                    ("message_delta", {"type": "message_delta", "delta": {
                        "stop_reason": "tool_use", "stop_sequence": None},
                        "usage": {"output_tokens": 8}}),
                    ("message_stop", {"type": "message_stop"}),
                ]
                response = "".join(
                    f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events
                ).encode()
                self.reply(200, response, "text/event-stream")
            except (ValueError, OSError):
                self.close_connection = True

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.timeout = 0.1
    stopping = threading.Event()

    def serve():
        while not stopping.is_set():
            server.handle_request()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield server.server_port, requests
    finally:
        stopping.set()
        thread.join(2)
        server.server_close()
        if thread.is_alive():
            raise ValueError("local controlled peer did not stop")


def probe(output, case):
    output = output.absolute()
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ("workspace", "home", "auth", "private"):
        (output / name).mkdir(mode=0o700)
    marker = output / "home/helper-observed"
    helper = output / "auth/helper"
    helper.write_text(
        f"#!{Path(sys.executable).resolve()}\nfrom pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('synthetic helper executed')\nprint({KEY!r})\n"
    )
    helper.chmod(0o700)
    schema = output / "workspace/schema.json"
    schema.write_text(json.dumps({
        "type": "object", "properties": {"handoff_json": {"type": "string"}},
        "required": ["handoff_json"], "additionalProperties": False,
    }))
    inventory = inspect_claude(Path('/Users/cam/.local/bin/claude'))
    with peer(output, case) as (port, requests):
        spec = ClaudePolicy(
            VERSION, str(output / "workspace"), str(output / "home"), inventory.executable,
            str(helper), str(Path(sys.executable).resolve()), str(Path(sys.prefix).resolve()),
            (), (ClaudeEgress("localhost", port),),
            (str(output / "private"), str(Path.cwd().resolve())),
        )
        policy = output / "client.sb"
        policy.write_text(render_claude_policy(spec))
        started = time.monotonic()
        output_limit = 4096 if case == "output_limit" else 65536
        result = execute_claude_transport(
            inventory, model=MODEL, schema=schema, helper=helper,
            helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
            directory=output / "native", workspace=output / "workspace", home=output / "home",
            nonce="claude-controlled-peer", prompt=b"Return the supplied synthetic fixture.",
            timeout_seconds=3 if case == "timeout" else 8,
            max_output_bytes=output_limit, max_budget_usd=0.10,
            on_launch=lambda _: None, loopback_port=port,
            cancelled=lambda: case == "cancel" and time.monotonic() - started >= 2,
            wrap_command=lambda command: ("/usr/bin/sandbox-exec", "-f", str(policy), *command),
        )
        recovery = None
        if case == "replay":
            before = len(requests)
            recovered = recover_claude_transport(
                output / "native", nonce="claude-controlled-peer",
                job_sha256=result.job_sha256, model=MODEL, max_output_bytes=output_limit,
            )
            recovery = {
                "same_process": recovered.process == result.process,
                "same_parsed_result": recovered.parsed == result.parsed,
                "same_job_sha256": recovered.job_sha256 == result.job_sha256,
                "extra_peer_requests": len(requests) - before,
            }
    report = {
        "version": "claude-controlled-peer-probe-1.2",
        "case": case,
        "source_identity": host_source_identity(),
        "runtime": {"platform": sys.platform, "machine": platform.machine()},
        "inventory": inventory.__dict__, "policy_specification": spec.to_dict(),
        "native_helper_observed": marker.is_file(), "requests": requests,
        "process_status": result.process.status, "returncode": result.process.returncode,
        "stopped": result.process.stopped, "transport_error": result.error,
        "structured_output": result.parsed.text if result.parsed else None,
        "job_sha256": result.job_sha256,
        "recovery": recovery,
        "production_admission": False, "provider_calls": 0, "scientific_calls": 0,
        "scope": "authored local peer, synthetic helper, no external endpoint or model",
    }
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--case", choices=("roundtrip", "timeout", "cancel", "output_limit", "replay"),
        default="roundtrip",
    )
    args = parser.parse_args()
    probe(args.output, args.case)
