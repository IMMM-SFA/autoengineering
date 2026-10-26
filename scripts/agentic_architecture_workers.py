"""Subscription-only Codex handoffs for the bounded Part 1 investigation.

Live host control stays outside the frozen numerical task identity. Replays are
reported explicitly and never counted as fresh numerical executions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from examples.agentic_architecture_pilot.control import CANDIDATE, request
from examples.agentic_architecture_pilot.science import ROOT, write_json

SCHEMA = {
    "type": "object",
    "properties": {
        "role": {"type": "string"},
        "candidate": {"type": "string"},
        "decision": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["role", "candidate", "decision", "rationale"],
    "additionalProperties": False,
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    # Never use an API key or a configured alternate provider for this pilot.
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in {
            "OPENAI_API_KEY",
            "CODEX_API_KEY",
            "OPENAI_BASE_URL",
            "OPENAI_ORG_ID",
            "OPENAI_PROJECT_ID",
        }
    }
    status = subprocess.run(["codex", "login", "status"], capture_output=True, text=True, env=env)
    if status.returncode or "Logged in using ChatGPT" not in status.stdout + status.stderr:
        raise SystemExit("ChatGPT subscription authentication is required; no API fallback")
    args.output.mkdir(parents=True, exist_ok=False)
    policy = dict(
        version=2,
        mode="subscription_only",
        paid_api_usd_limit=0,
        max_calls=18,
        max_total_observed_tokens=50000,
        per_call_timeout_seconds=90,
        token_enforcement="stop before next call after reported usage; no in-flight hard cap",
        fresh_campaigns=1,
        replayed_campaigns=5,
        worker_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    write_json(args.output / "policy.json", policy)
    repository = ROOT.parent.parent if ROOT.parent.name == ".worktrees" else ROOT
    rows = []
    total_tokens = 0
    with tempfile.TemporaryDirectory(prefix="ae-codex-worker-") as temporary:
        staged = Path(temporary).resolve()
        schema = staged / "response-schema.json"
        write_json(schema, SCHEMA)
        profile = staged / "profile.sb"
        # The worker may contact its subscription endpoint, but cannot read or write
        # any checkout or scientific record. The parent process owns all tool calls.
        protected = json.dumps(str(repository.resolve()))
        profile.write_text(
            f"(version 1)(allow default)"
            f"(deny file-read* (subpath {protected}))"
            f"(deny file-write* (subpath {protected}))"
        )
        write_json(
            staged / "brief.json",
            dict(
                task="routing architecture development fixture",
                candidate=CANDIDATE,
                intervention="supplied gamma routing only",
                fitting="2019-04-01 to 2019-12-31",
                comparison="2020 development only",
            ),
        )
        for route in ("cli", "standalone"):
            for repeat in range(3):
                fresh = route == "cli" and repeat == 0
                campaign = (
                    args.output / "fresh-campaign"
                    if fresh
                    else ROOT
                    / "background-research/agentic-architecture/comparison"
                    / f"{route}-{repeat}"
                )

                def tool(message):
                    if route == "standalone":
                        return request(campaign, message)
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "examples.agentic_architecture_pilot.control",
                            str(campaign),
                        ],
                        input=json.dumps(message),
                        text=True,
                        capture_output=True,
                        env=os.environ,
                        timeout=1800,
                    )
                    if result.returncode:
                        raise RuntimeError(result.stdout + result.stderr)
                    return json.loads(result.stdout)

                diagnostic = tool(dict(id="diagnose", tool="diagnose", payload={}))
                feedback = diagnostic
                for role in ("investigator", "implementer", "reviewer"):
                    if total_tokens >= 50000:
                        raise RuntimeError("observed token limit reached")
                    label = f"{route}-{repeat}-{role}"
                    prompt = (
                        f"You are the {role} in a bounded scientific workflow. "
                        "Use no tools. Return only the requested JSON. "
                        f"role must be {role}; candidate must be {CANDIDATE}. "
                        "For investigator and implementer set decision to request_calibration. "
                        "Explain the rationale or adapter interface (runoff and recharge arrays; "
                        "gamma_shape, gamma_scale, k_base, recharge_frac). "
                        "For reviewer set decision to the evaluator decision exactly and explain "
                        "its development-only limits. Never claim whole-catchment conservation. "
                        f"Evidence: {json.dumps(feedback)}"
                    )
                    print(
                        f"Live subscription handoff {label} ({'fresh' if fresh else 'replay'})",
                        flush=True,
                    )
                    started = time.monotonic()
                    command = [
                        "/usr/bin/sandbox-exec",
                        "-f",
                        str(profile),
                        "codex",
                        "exec",
                        "--ignore-user-config",
                        "--ignore-rules",
                        "--ephemeral",
                        "--skip-git-repo-check",
                        "--sandbox",
                        "read-only",
                        "--json",
                        "--output-schema",
                        str(schema),
                        "-c",
                        'approval_policy="never"',
                        "-c",
                        'model_reasoning_effort="low"',
                        "-C",
                        str(staged),
                        prompt,
                    ]
                    result = subprocess.run(
                        command, capture_output=True, text=True, env=env, timeout=90
                    )
                    (args.output / f"{label}.jsonl").write_text(result.stdout)
                    (args.output / f"{label}.stderr.txt").write_text(result.stderr)
                    if result.returncode:
                        raise RuntimeError(f"worker failed: {label}")
                    events = [
                        json.loads(line) for line in result.stdout.splitlines() if line.strip()
                    ]
                    completed = [e for e in events if e.get("type") == "turn.completed"]
                    messages = [
                        e["item"]["text"]
                        for e in events
                        if e.get("type") == "item.completed"
                        and e.get("item", {}).get("type") == "agent_message"
                    ]
                    if not completed or not messages:
                        raise RuntimeError("missing worker receipt")
                    reply = json.loads(messages[-1])
                    usage = completed[-1]["usage"]
                    total_tokens += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    if reply["role"] != role or reply["candidate"] != CANDIDATE:
                        raise RuntimeError("worker identity or candidate mismatch")
                    if role == "implementer":
                        if reply["decision"] != "request_calibration":
                            raise RuntimeError("unexpected implementer decision")
                        tool(dict(id="submit", tool="submit", payload={"candidate": CANDIDATE}))
                        feedback = tool(dict(id="evaluate", tool="evaluate", payload={}))
                    elif role == "reviewer":
                        for step in ("review", "decide"):
                            tool(dict(id=step, tool=step, payload={"decision": reply["decision"]}))
                    else:
                        feedback = reply
                    rows.append(
                        dict(
                            route=route,
                            repeat=repeat,
                            role=role,
                            mode="fresh" if fresh else "replay",
                            seconds=time.monotonic() - started,
                            usage=usage,
                            response=reply,
                            trace=f"{label}.jsonl",
                        )
                    )
                    write_json(args.output / "handoffs.json", rows)
    write_json(
        args.output / "summary.json",
        dict(
            handoffs=len(rows),
            campaigns=6,
            fresh_campaigns=1,
            replayed_campaigns=5,
            new_scientific_executions=38,
            observed_tokens=total_tokens,
            paid_api_calls=0,
            subscription_cost_usd="unknown",
        ),
    )


if __name__ == "__main__":
    main()
