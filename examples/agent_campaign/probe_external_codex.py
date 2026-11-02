"""Run installed Codex against one local authored response behind an OS boundary.

This uses no authentication and cannot reach a provider. It is an offline
transport probe, not production host or subscription conformance.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import shutil
import sys
import threading
import uuid

from autoengineering.agents.hosts.codex import inspect_codex, parse_events
from autoengineering.agents.hosts.response_boundary import (
    VERSION as RESPONSE_BOUNDARY_VERSION,
    ResponseBoundaryError,
)
from autoengineering.agents.hosts.text_exchange import TextExchange
from autoengineering.agents.process import supervise_process
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.probe_external_boundary import external_policy

# A bundled catalog name avoids fallback-metadata errors. The service still
# returns authored bytes only. This is neither model access nor a live choice.
OFFLINE_MODEL = "gpt-5.5"
OFFLINE_PROMPT = 'Return {"ok":true}. Do not use tools.\n'
OFFLINE_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}
TEXT_DISABLED_FEATURES = (
    "apps",
    "browser_use",
    "browser_use_external",
    "code_mode",
    "code_mode_host",
    "code_mode_only",
    "computer_use",
    "goals",
    "hooks",
    "image_generation",
    "in_app_browser",
    "in_app_local_automation",
    "memories",
    "multi_agent",
    "plugins",
    "request_permissions_tool",
    "shell_snapshot",
    "shell_tool",
    "skill_mcp_dependency_install",
    "skill_search",
    "sleep_tool",
    "unified_exec",
    "view_image",
    "workspace_dependencies",
)


def response_stream(*, tool_command: str | None = None, model: str = OFFLINE_MODEL) -> bytes:
    """An authored Responses stream, without a model or generated tool calls."""
    message = {
        "id": "msg_part3_fixture",
        "type": "message",
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": '{"ok":true}', "annotations": []}],
    }
    if tool_command is not None:
        message = {
            "id": "fc_part3_fixture",
            "type": "function_call",
            "call_id": "call_part3_fixture",
            "name": "exec_command",
            "status": "completed",
            "arguments": canonical_json(
                {
                    "cmd": tool_command,
                    "shell": "/bin/bash",
                    "login": False,
                    "tty": False,
                    "yield_time_ms": 1000,
                    "max_output_tokens": 128,
                }
            ),
        }
    response = {
        "id": "resp_part3_fixture",
        "object": "response",
        "created_at": 1,
        "model": model,
        "status": "completed",
        "output": [message],
        "usage": {
            "input_tokens": 1,
            "output_tokens": 1,
            "total_tokens": 2,
            "input_tokens_details": {"cached_tokens": 0},
            "output_tokens_details": {"reasoning_tokens": 0},
        },
    }
    events = (
        {
            "type": "response.created",
            "response": {**response, "status": "in_progress", "output": []},
        },
        {"type": "response.output_item.done", "output_index": 0, "item": message},
        {"type": "response.completed", "response": response},
    )
    return b"".join(
        f"event: {event['type']}\ndata: {canonical_json(event)}\n\n".encode() for event in events
    )


class FakeResponses:
    def __init__(self, output: Path, *, body: bytes | None = None, guarded: bool = True):
        self.requests = []
        self.attempts = 0
        self.errors = []
        self.boundary = None
        self.exchange = (
            None
            if not guarded
            else TextExchange.create(
                output / "exchange",
                invocation_id="offline-client",
                requested_model=OFFLINE_MODEL,
                approved_prompt=OFFLINE_PROMPT,
                output_schema=OFFLINE_SCHEMA,
            )
        )
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass

            def do_POST(self):
                owner.attempts += 1
                self.connection.settimeout(2)
                try:
                    encoded_length = self.headers.get("Content-Length", "0")
                    if (
                        not encoded_length.isascii()
                        or not encoded_length.isdigit()
                        or len(encoded_length) > 7
                    ):
                        raise ValueError("invalid offline request length")
                    length = int(encoded_length)
                    if not 0 < length <= 524288:
                        raise ValueError("request size exceeds offline fixture limit")
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete fixture request")
                    # The staged client uses no auth. Never save unexpected
                    # authorization headers, even in this synthetic fixture.
                    if self.headers.get("Authorization"):
                        raise ValueError("offline fixture received unexpected authentication")
                    payload = json.loads(raw)
                    if (
                        not isinstance(payload, dict)
                        or payload.get("model") != OFFLINE_MODEL
                        or payload.get("stream") is not True
                    ):
                        raise ValueError("unexpected offline request envelope")
                    index = len(owner.requests) + 1
                    if index > 1 or self.path != "/v1/responses":
                        raise ValueError("unexpected or duplicate offline request")
                    durable_write(output / "request.bin", raw)
                    owner.requests.append(
                        {
                            "path": self.path,
                            "bytes": len(raw),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                        }
                    )
                    upstream = response_stream() if body is None else body
                    durable_write(output / "upstream-response.bin", upstream)
                    try:
                        normalized = None
                        if owner.exchange is not None:

                            def authored(request):
                                durable_write(output / "upstream-request.bin", request)
                                return upstream

                            exchanged = owner.exchange.execute(raw, authored)
                            if exchanged.status != "completed":
                                raise ResponseBoundaryError(exchanged.reason)
                            normalized = exchanged.response
                    except ResponseBoundaryError as exc:
                        owner.boundary = {
                            "version": RESPONSE_BOUNDARY_VERSION,
                            "status": "rejected",
                            "reason": str(exc),
                            "raw_sha256": hashlib.sha256(upstream).hexdigest(),
                            "client_response_bytes": 0,
                        }
                        durable_write(
                            output / "boundary.json", canonical_json(owner.boundary).encode()
                        )
                        raise
                    client_body = upstream if normalized is None else normalized.normalized_sse
                    owner.boundary = {
                        "version": RESPONSE_BOUNDARY_VERSION,
                        "status": "control_bypassed" if normalized is None else "validated",
                        "raw_sha256": hashlib.sha256(upstream).hexdigest(),
                        "client_response_sha256": hashlib.sha256(client_body).hexdigest(),
                        "client_response_bytes": len(client_body),
                        "reported_model": None if normalized is None else normalized.reported_model,
                        "usage": None if normalized is None else dict(normalized.usage),
                    }
                    durable_write(output / "boundary.json", canonical_json(owner.boundary).encode())
                    durable_write(output / "client-response.bin", client_body)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Content-Length", str(len(client_body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(client_body)
                except (ValueError, OSError) as exc:
                    owner.errors.append(type(exc).__name__ + ": " + str(exc))
                    self.send_error(400)

            def do_GET(self):
                owner.errors.append("unexpected GET")
                self.send_error(400)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.server.timeout = 0.1
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        while not self.stop.is_set():
            self.server.handle_request()

    @property
    def port(self):
        return self.server.server_port

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}/v1"

    def close(self):
        self.stop.set()
        self.thread.join(timeout=3)
        self.server.server_close()
        if self.thread.is_alive():
            raise RuntimeError("offline response server did not stop")


def exercise(output: Path, *, scenario: str = "text"):
    if scenario not in {"text", "blocked_tool", "tool_control"}:
        raise ValueError("unsupported offline scenario")
    if sys.platform != "darwin":
        raise ValueError("external Codex probe requires macOS")
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("external Codex probe requires a fresh output directory")
    installed = shutil.which("codex")
    if installed is None:
        raise ValueError("installed Codex executable is unavailable")
    inventory = inspect_codex(Path(installed))
    managed_requirements = Path("/etc/codex/requirements.toml").resolve()
    if managed_requirements.exists() or managed_requirements.is_symlink():
        raise ValueError(
            "offline probe requires absent system requirements; no ambient policy read"
        )
    output.mkdir(mode=0o700)
    for name in ("workspace", "scratch", "receipts"):
        (output / name).mkdir(mode=0o700)
    workspace, scratch = (output / name for name in ("workspace", "scratch"))
    durable_write(workspace / "schema.json", canonical_json(OFFLINE_SCHEMA).encode())
    durable_write(output / "probe-source.py", Path(__file__).read_bytes())
    marker = scratch / "tool-executed"
    # The paired malicious-response control uses an authored fixed command.
    # Paths contain only a validated fresh output root, and are shell quoted.
    import shlex

    upstream = (
        response_stream(tool_command=f"/usr/bin/touch {shlex.quote(str(marker))}")
        if scenario != "text"
        else response_stream()
    )
    if scenario == "tool_control":
        service = FakeResponses(output, body=upstream, guarded=False)
    else:
        from examples.agent_campaign.endpoint_fixture import AuthoredTextEndpoint

        service = AuthoredTextEndpoint(
            output, body=upstream, model=OFFLINE_MODEL, prompt=OFFLINE_PROMPT, schema=OFFLINE_SCHEMA
        )
    # Only the owned fake service is reachable. Neither native CLI command
    # sandboxing nor a user-selected proxy can expand this external policy.
    policy = external_policy(workspace, scratch, Path(inventory.executable)) + (
        '(allow user-preference-read (preference-domain "com.openai.codex"))\n'
        '(allow mach-lookup (global-name "com.apple.cfprefsd.agent") '
        '(global-name "com.apple.cfprefsd.daemon") (local-name "com.apple.cfprefsd.agent"))\n'
        '(allow ipc-posix-shm-read* (ipc-posix-name-prefix "apple.cfprefs."))\n'
        f'(allow network-outbound (remote ip "localhost:{service.port}"))\n'
        f'(allow file-read* (literal "/etc") (literal {json.dumps(str(managed_requirements))}))\n'
        "(allow file-read-metadata "
        + " ".join(f"(literal {json.dumps(str(p))})" for p in managed_requirements.parents)
        + ")\n"
    )
    durable_write(output / "external.sb", policy.encode())
    options = {
        "model_provider": '"part3_fake"',
        "model_providers.part3_fake.name": '"Part3 offline fixture"',
        "model_providers.part3_fake.base_url": json.dumps(service.base_url),
        "model_providers.part3_fake.wire_api": '"responses"',
        "model_providers.part3_fake.requires_openai_auth": "false",
        "model_providers.part3_fake.supports_websockets": "false",
        "model_providers.part3_fake.request_max_retries": "0",
        "model_providers.part3_fake.stream_max_retries": "0",
        "model_providers.part3_fake.stream_idle_timeout_ms": "5000",
        "web_search": '"disabled"',
        "skills.bundled.enabled": "false",
        "skills.include_instructions": "false",
        **{f"features.{name}": "false" for name in TEXT_DISABLED_FEATURES},
    }
    if scenario != "text":
        # Identical client permissions in both tool cases isolate the response
        # boundary. The control can write only inside this fixture's scratch.
        options["features.shell_tool"] = "true"
        options["features.unified_exec"] = "true"
    args = [
        "/usr/bin/sandbox-exec",
        "-f",
        str(output / "external.sb"),
        inventory.executable,
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--model",
        OFFLINE_MODEL,
        "--color",
        "never",
        "--output-schema",
        str(workspace / "schema.json"),
    ]
    for key, value in options.items():
        args.extend(("-c", f"{key}={value}"))
    args.append("-")
    print("Checking installed CLI against the local authored response", flush=True)
    try:
        result = supervise_process(
            tuple(args),
            directory=output / "receipts" / "client",
            cwd=workspace,
            environment={
                "PATH": "/usr/bin:/bin",
                "HOME": str(scratch),
                "CODEX_HOME": str(scratch),
                "TMPDIR": str(scratch),
                "LANG": "C",
                "LC_ALL": "C",
            },
            nonce=uuid.uuid4().hex,
            stdin=OFFLINE_PROMPT.encode(),
            timeout_seconds=15,
            max_output_bytes=65536,
            on_launch=lambda owner: durable_write(
                output / "receipts" / "client-owner.json", canonical_json(owner).encode()
            ),
        )
    finally:
        service.close()
    final, parse_error = None, None
    try:
        final, _model, _usage = parse_events(result.stdout)
    except ValueError as exc:
        parse_error = str(exc)
    passed_text = (
        result.stopped
        and not result.truncated
        and result.returncode == 0
        and final == '{"ok":true}'
        and len(service.requests) == 1
        and not service.errors
    )
    bounded = result.stopped and not result.truncated
    blocked = (
        bounded
        and result.returncode != 0
        and not marker.exists()
        and len(service.requests) == 1
        and service.attempts == 1
        and service.boundary is not None
        and service.boundary["status"] == "rejected"
        and service.boundary["reason"] == "forbidden_response_item"
        and not (output / "client-response.bin").exists()
    )
    control = (
        bounded
        and marker.is_file()
        and len(service.requests) == 1
        and service.attempts == 2
        and service.boundary is not None
        and service.boundary["status"] == "control_bypassed"
    )
    status = (
        "offline_transport_passed"
        if scenario == "text" and passed_text
        else "tool_response_blocked"
        if scenario == "blocked_tool" and blocked
        else "tool_control_executed"
        if scenario == "tool_control" and control
        else "failed"
    )
    receipt = {
        "schema_version": "1.0",
        "purpose": "external-codex-offline-transport-probe",
        "status": status,
        "scenario": scenario,
        "host_qualified": False,
        "live_conformance": False,
        "real_credentials_used": False,
        "provider_calls": 0,
        "client_invocations": 1,
        "requested_catalog_model": OFFLINE_MODEL,
        "requests": service.requests,
        "request_attempts": service.attempts,
        "boundary": service.boundary,
        "endpoint_stop": getattr(service, "stop_receipt", None),
        "tool_marker_exists": marker.exists(),
        "service_errors": service.errors,
        "inventory": asdict(inventory),
        "checked_absent_requirements": str(managed_requirements),
        "policy_sha256": hashlib.sha256(policy.encode()).hexdigest(),
        "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "returncode": result.returncode,
        "process_status": result.status,
        "stopped": result.stopped,
        "truncated": result.truncated,
        "elapsed_seconds": result.elapsed_seconds,
        "parse_error": parse_error,
    }
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    print(f"Offline Codex transport: {receipt['status']}", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--scenario", choices=("text", "blocked_tool", "tool_control"), default="text"
    )
    args = parser.parse_args()
    return 0 if exercise(args.output, scenario=args.scenario)["status"] != "failed" else 4


if __name__ == "__main__":
    raise SystemExit(main())
