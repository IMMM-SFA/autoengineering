"""Run native Claude through the durable Anthropic exchange, with no provider.

The only upstream is an authored in-process JSON callback. Authentication uses a
fixed synthetic local capability. Token/cost fields are fixture data. This script
qualifies no production host, real credential interface or LLM role behavior.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

from autoengineering.agents.hosts.anthropic_boundary import WIRE_SCHEMA
from autoengineering.agents.hosts.anthropic_endpoint import AnthropicEndpoint
from autoengineering.agents.hosts.anthropic_exchange import AnthropicExchange
from autoengineering.agents.hosts.claude import (
    execute_claude_transport, inspect_claude, recover_claude_transport,
)
from autoengineering.agents.hosts.claude_policy import ClaudeEgress, ClaudePolicy, VERSION
from autoengineering.agents.hosts.claude_policy import render_claude_policy
from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import durable_write

MODEL = "claude-sonnet-4-6"
PROMPT = "Return the supplied synthetic reviewer role envelope."
INNER = canonical_json({"role": "reviewer", "fixture": True})
TOKEN = "c" * 32


def probe(root, *, missing_cache):
    root = root.absolute()
    root.mkdir(mode=0o700, parents=True, exist_ok=False)
    for name in ("workspace", "home", "private", "auth"):
        (root / name).mkdir(mode=0o700)
    schema = root / "workspace/schema.json"
    schema.write_text(canonical_json(WIRE_SCHEMA))
    capability = root / "auth/synthetic-capability"
    durable_write(capability, TOKEN.encode())
    helper = root / "auth/helper"
    helper.write_text(
        f"#!{Path(sys.executable).resolve()}\nfrom pathlib import Path\n"
        f"print(Path({str(capability)!r}).read_text())\n"
    )
    helper.chmod(0o700)
    broker = AnthropicExchange.create(
        root / "exchange", invocation_id="native-local-exchange", requested_model=MODEL,
        approved_prompt=PROMPT, output_schema=WIRE_SCHEMA, max_output_tokens=512,
    )
    calls = []

    def authored_upstream(raw):
        value = unique_json(raw.decode())
        assert value["messages"] == [
            {"role": "user", "content": [{"type": "text", "text": PROMPT}]}
        ]
        assert value["tools"] == [] and value["stream"] is False
        assert value["max_tokens"] == 512 and b"CWD:" not in raw and b"user_id" not in raw
        calls.append(hashlib.sha256(raw).hexdigest())
        usage = {"input_tokens": 7, "output_tokens": 10}
        if not missing_cache:
            usage.update(cache_read_input_tokens=2, cache_creation_input_tokens=3)
        return canonical_json({
            "id": "msg_authored_durable_exchange", "type": "message", "role": "assistant",
            "model": MODEL, "stop_reason": "end_turn", "stop_sequence": None,
            "content": [{"type": "text", "text": canonical_json({"handoff_json": INNER})}],
            "usage": usage,
        }).encode()

    endpoint = AnthropicEndpoint(
        broker, authored_upstream, directory=root / "endpoint", route_nonce=TOKEN,
    )
    try:
        inventory = inspect_claude(Path('/Users/cam/.local/bin/claude'))
        policy_spec = ClaudePolicy(
            VERSION, str(root / "workspace"), str(root / "home"), inventory.executable,
            str(helper), str(Path(sys.executable).resolve()), str(Path(sys.prefix).resolve()),
            (str(capability),), (ClaudeEgress("localhost", endpoint.port),),
            (str(root / "private"), str(root / "exchange"), str(root / "endpoint"), str(Path.cwd())),
        )
        policy = root / "client.sb"
        policy.write_text(render_claude_policy(policy_spec))

        def bind(_identity):
            durable_write(root / "caller-binding.json", canonical_json({
                "nonce": "claude-durable-local", "model": MODEL,
                "job_sha256": hashlib.sha256((root / "native/job.json").read_bytes()).hexdigest(),
            }).encode())

        native = execute_claude_transport(
            inventory, model=MODEL, schema=schema, helper=helper,
            helper_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
            directory=root / "native", workspace=root / "workspace", home=root / "home",
            nonce="claude-durable-local", prompt=PROMPT.encode(), timeout_seconds=8,
            max_output_bytes=65536, max_budget_usd=0.1, on_launch=bind,
            loopback_port=endpoint.port,
            wrap_command=lambda command: ("/usr/bin/sandbox-exec", "-f", str(policy), *command),
        )
    finally:
        stopped = endpoint.close()
    before = len(calls)
    saved = broker.recover()
    binding = unique_json((root / "caller-binding.json").read_text())
    recovered = recover_claude_transport(
        root / "native", nonce=binding["nonce"], model=binding["model"],
        job_sha256=binding["job_sha256"], max_output_bytes=65536,
    )
    report = {
        "version": "claude-durable-exchange-probe-1.0", "source_identity": host_source_identity(),
        "missing_cache_case": missing_cache, "policy_specification": policy_spec.to_dict(),
        "inventory": inventory.__dict__, "native_status": native.process.status,
        "native_stopped": native.process.stopped, "native_error": native.error,
        "native_structured_output": native.parsed.text if native.parsed else None,
        "native_diagnostic_usage": dict(native.parsed.usage) if native.parsed else None,
        "broker_status": saved.status, "broker_usage": dict(saved.response.usage) if saved.response else None,
        "provider_requests_reserved": saved.provider_requests_reserved,
        "authored_upstream_callbacks": len(calls), "extra_callbacks_on_recovery": len(calls) - before,
        "same_native_process_on_recovery": native.process == recovered.process,
        "same_native_result_on_recovery": native.parsed == recovered.parsed,
        "endpoint_stop": asdict(stopped), "provider_calls": 0, "scientific_calls": 0,
        "production_admission": False,
        "usage_cost_basis": "authored fixture, not measured provider work or billing",
    }
    success = (
        native.error is None and native.process.status == "completed" and native.process.stopped
        and saved.status == "completed" and len(calls) == 1 and len(calls) == before
        and saved.response.text == canonical_json({"handoff_json": INNER})
        and native.parsed.text == saved.response.text
        and native.process == recovered.process and native.parsed == recovered.parsed
        and stopped.listener_closed and stopped.handler_stopped and stopped.upstream_callback_stopped
        and (saved.response.usage["input_tokens"] is None if missing_cache
             else saved.response.usage["total_tokens"] == 22)
    )
    report["status"] = "passed_limited_scope" if success else "failed"
    (root / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    if not success:
        raise ValueError("native durable exchange probe failed; raw evidence retained")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--missing-cache", action="store_true")
    args = parser.parse_args()
    probe(args.output, missing_cache=args.missing_cache)
