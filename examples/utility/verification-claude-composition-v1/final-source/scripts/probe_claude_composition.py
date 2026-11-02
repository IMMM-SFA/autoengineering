"""Native Claude composition against authored JSON only, never a provider.

No real authentication or scientific data is used. All usage/cost values are
fixture data. This does not admit a production Host or authorize live conformance.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from pathlib import Path
import sys

from autoengineering.agents.hosts.base import InvocationContext
from autoengineering.agents.hosts.claude import inspect_claude
from autoengineering.agents.hosts.claude_brokered import (
    execute_brokered_claude,
    recover_brokered_claude,
)
from autoengineering.agents.hosts.claude_policy import (
    ClaudeEgress,
    ClaudePolicy,
    VERSION,
    render_claude_policy,
)
from autoengineering.agents.hosts.codex_brokered import WrappedCommand
from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import durable_write

MODEL = "claude-sonnet-4-6"
PROMPT = "Return the supplied synthetic reviewer role envelope."
INNER = canonical_json({"role": "reviewer", "fixture": True})


def probe(root: Path):
    root = root.absolute()
    inventory = inspect_claude(Path("/Users/cam/.local/bin/claude"))
    calls, launches = [], []

    def upstream(raw):
        value = unique_json(raw.decode())
        assert value["messages"] == [
            {"role": "user", "content": [{"type": "text", "text": PROMPT}]}
        ]
        assert value["tools"] == [] and value["stream"] is False
        assert value["max_tokens"] == 512
        calls.append(hashlib.sha256(raw).hexdigest())
        return canonical_json(
            {
                "id": "msg_authored_composition",
                "type": "message",
                "role": "assistant",
                "model": MODEL,
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "content": [{"type": "text", "text": canonical_json({"handoff_json": INNER})}],
                # Missing cache counters must stay unknown in normalized broker usage.
                "usage": {"input_tokens": 7, "output_tokens": 10},
            }
        ).encode()

    def wrapper(command, endpoint, helper, capability):
        (root / "private").mkdir(mode=0o700)
        spec = ClaudePolicy(
            VERSION,
            str(root / "workspace"),
            str(root / "home"),
            inventory.executable,
            str(helper),
            str(Path(sys.executable).resolve()),
            str(Path(sys.prefix).resolve()),
            (str(capability),),
            (ClaudeEgress("localhost", endpoint.port),),
            (
                str(root / "private"),
                str(root / "exchange"),
                str(root / "endpoint"),
                str(Path.cwd()),
            ),
        )
        policy = root / "client.sb"
        durable_write(policy, render_claude_policy(spec).encode())
        durable_write(root / "policy-spec.json", canonical_json(spec.to_dict()).encode())
        return WrappedCommand(("/usr/bin/sandbox-exec", "-f", str(policy), *command), policy)

    result = execute_brokered_claude(
        inventory,
        model=MODEL,
        prompt=PROMPT,
        context=InvocationContext(
            "native-composed",
            "native-composed-owner",
            root,
            8,
            65536,
            launches.append,
            lambda: False,
        ),
        upstream=upstream,
        boundary_identity="d" * 64,
        max_output_tokens=512,
        estimated_budget_usd=0.1,
        wrap_command=wrapper,
    )
    before = len(calls)
    recovered = recover_brokered_claude(root)
    report = {
        "version": "claude-composition-probe-1.0",
        "source_identity": host_source_identity(),
        "inventory": asdict(inventory),
        "host_status": result.host_result.status,
        "local_stop_verified": result.host_result.stop_verified,
        "native_status": result.native.process.status,
        "native_error": result.native.error,
        "endpoint_stop": asdict(result.endpoint_stop),
        "callback_calls": len(calls),
        "native_launches": len(launches),
        "added_replay_callbacks": len(calls) - before,
        "recovered_host_result_equal": recovered.host_result == result.host_result,
        "broker_usage": dict(result.host_result.usage),
        "native_diagnostic_usage": dict(result.native.parsed.usage)
        if result.native.parsed
        else None,
        "native_estimated_usd": result.native.parsed.estimated_cost_usd
        if result.native.parsed
        else None,
        "billed_cost_usd": None,
        "actual_provider_calls": 0,
        "real_credentials_read": 0,
        "production_admission": False,
        "scope": "native CLI with authored local callback; no real model or cost evidence",
    }
    durable_write(root / "probe.json", canonical_json(report).encode())
    assert report["host_status"] == "completed" and report["local_stop_verified"]
    assert report["callback_calls"] == report["native_launches"] == 1
    assert report["added_replay_callbacks"] == 0 and report["recovered_host_result_equal"]
    assert report["broker_usage"]["total_tokens"] is None
    print(canonical_json(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    probe(parser.parse_args().output)
