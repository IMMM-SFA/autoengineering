"""Small single-writer campaign sketch shared by two transports.

This is a trusted control-process API, not a sandbox or a general agent runtime.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
from pathlib import Path
import re
import sys
import time

from .science import evaluate_choices, identity, task, write_json

STEPS = ("diagnose", "submit", "evaluate", "review", "decide")
CANDIDATE = "supplied-gamma-v1"


class ProtocolError(ValueError):
    """Rejected request. Rejection never authorizes scientific execution."""


@contextmanager
def writer(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / ".campaign.lock").open("a") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ProtocolError("another writer owns campaign") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def validate_request(request: dict) -> None:
    if not isinstance(request, dict) or set(request) != {"id", "tool", "payload"}:
        raise ProtocolError("request requires exactly id, tool, payload")
    if not isinstance(request["id"], str) or not re.fullmatch(r"[a-z0-9_-]{1,64}", request["id"]):
        raise ProtocolError("invalid request id")
    if not isinstance(request["tool"], str) or request["tool"] not in (*STEPS, "state", "cancel"):
        raise ProtocolError("unsupported tool")
    if not isinstance(request["payload"], dict):
        raise ProtocolError("payload must be an object")
    expected = {"submit": {"candidate"}, "review": {"decision"}, "decide": {"decision"}}
    if set(request["payload"]) != expected.get(request["tool"], set()):
        raise ProtocolError("unsupported payload fields")
    if request["tool"] == "submit" and request["payload"]["candidate"] != CANDIDATE:
        raise ProtocolError("only supplied immutable candidate is admissible")


def request(directory: Path, message: dict, *, fault: str | None = None) -> dict:
    """Reconcile result-before-ack crashes; refuse uncertain executions on resume."""
    validate_request(message)
    with writer(directory):
        hashes = identity()
        state_path = directory / "state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text())
            if state["hashes"] != hashes:
                raise ProtocolError("source, task or input identity changed")
        else:
            state = dict(
                hashes=hashes,
                step=0,
                requests={},
                cancelled=False,
                pending=None,
                reserved_executions=0,
                tool_calls=0,
                started=time.time(),
            )
            write_json(state_path, state)
        request_id = message["id"]
        if request_id in state["requests"]:
            previous = state["requests"][request_id]
            if previous["request"] != message:
                raise ProtocolError("request identity reused for different content")
            return previous["response"]
        if state["pending"]:
            pending = state["pending"]
            if pending["request"] != message:
                raise ProtocolError("pending request must be reconciled first")
            result_path = directory / "evaluation.json"
            if not result_path.exists():
                raise ProtocolError(
                    "uncertain execution; reservation retained; manual reconciliation"
                )
            result = json.loads(result_path.read_text())
            if result["request"] != message or result["hashes"] != hashes:
                raise ProtocolError("saved result identity mismatch")
            response = result["response"]
            state["pending"] = None
            state["step"] += 1
        else:
            tool = message["tool"]
            if tool == "state":
                return dict(
                    next_tool=STEPS[state["step"]] if state["step"] < len(STEPS) else "complete",
                    cancelled=state["cancelled"],
                    reserved_executions=state["reserved_executions"],
                )
            if tool == "cancel":
                state["cancelled"] = True
                response = dict(status="cancelled")
            else:
                if state["cancelled"]:
                    raise ProtocolError("campaign cancelled")
                if time.time() - state["started"] > task()["resources"]["max_wall_seconds"]:
                    raise ProtocolError("campaign time budget exhausted")
                if state["tool_calls"] >= task()["resources"]["max_tool_requests"]:
                    raise ProtocolError("tool request budget exhausted")
                if state["step"] >= len(STEPS) or STEPS[state["step"]] != tool:
                    raise ProtocolError("illegal workflow transition")
                state["tool_calls"] += 1
                if tool == "diagnose":
                    response = dict(
                        status="ok",
                        scope=task()["scope"],
                        hypothesis="compare supplied routing after equal calibration",
                    )
                elif tool == "submit":
                    response = dict(
                        status="admitted",
                        candidate=CANDIDATE,
                        candidate_sha256=hashes["examples/leaf_river/models/routing_calibrated.py"],
                    )
                elif tool == "evaluate":
                    if (
                        state["reserved_executions"] + 40
                        > task()["resources"]["max_system_executions"]
                    ):
                        raise ProtocolError("scientific execution budget exhausted")
                    state["reserved_executions"] += 40
                    state["pending"] = dict(request=message, status="execution_outcome_uncertain")
                    write_json(state_path, state)
                    if fault == "before_evaluation":
                        raise RuntimeError("injected uncertain execution")
                    response = evaluate_choices(directory, hashes)
                    write_json(
                        directory / "evaluation.json",
                        dict(request=message, hashes=hashes, response=response),
                    )
                    if fault == "after_evaluation":
                        raise RuntimeError("injected result-before-ack crash")
                    state["pending"] = None
                else:
                    result = json.loads((directory / "evaluation.json").read_text())["response"]
                    if message["payload"]["decision"] != result["decision"]:
                        raise ProtocolError(
                            "unsupported conclusion conflicts with executable evidence"
                        )
                    response = dict(status="ok", decision=result["decision"], scope=result["scope"])
                state["step"] += 1
        state["requests"][request_id] = dict(request=message, response=response)
        write_json(state_path, state)
        # State is authoritative. This derived view can be rebuilt after interruption.
        write_json(directory / "requests.json", list(state["requests"].values()))
        return response


def scripted_messages():
    for step in ("diagnose", "submit", "evaluate"):
        yield dict(id=step, tool=step, payload={"candidate": CANDIDATE} if step == "submit" else {})


def replay(directory: Path) -> dict:
    """Standalone route with deterministic role responses, including durable restart."""
    response = None
    for message in scripted_messages():
        response = request(directory, message)
    decision = response["decision"]
    for step in ("review", "decide"):
        request(directory, dict(id=step, tool=step, payload=dict(decision=decision)))
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--replay", action="store_true")
    args = parser.parse_args()
    try:
        if args.replay:
            response = replay(args.directory)
        else:
            raw = sys.stdin.read(65537)
            if len(raw) > 65536:
                raise ProtocolError("request exceeds 64 KiB")
            response = request(args.directory, json.loads(raw))
        print(json.dumps(response, allow_nan=False))
    except (ValueError, OSError) as exc:
        print(json.dumps(dict(error=str(exc))))
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
