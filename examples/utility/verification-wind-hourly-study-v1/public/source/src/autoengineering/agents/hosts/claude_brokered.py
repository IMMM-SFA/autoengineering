"""Owned Claude process/exchange composition, without production admission.

The caller supplies the OS wrapper and separately owns upstream credentials,
network authority and process stops. Native counters never fill broker gaps.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
import sys
import time

from autoengineering.agents.identity import host_source_identity
from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.records import identifier, sha256
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from .anthropic_boundary import WIRE_SCHEMA
from .anthropic_endpoint import AnthropicEndpoint
from .anthropic_exchange import AnthropicExchange
from .base import HostResult, InvocationContext
from .claude import (
    ClaudeExecution,
    ClaudeInventory,
    execute_claude_transport,
    recover_claude_transport,
)
from .codex_brokered import WrappedCommand
from .text_endpoint import EndpointStop
from .text_exchange import ExchangeResult

VERSION = "claude-brokered-1.0"


def _hash(path):
    path = confined_file(Path(path).parent, Path(path).name)
    if path.stat().st_size > 1048576:
        raise ValueError("Claude composition record exceeds limit")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 1048576:
        raise ValueError("Claude composition record exceeds limit")
    return unique_json(path.read_text())


@dataclass(frozen=True)
class ClaudeBrokeredExecution:
    root: Path
    host_result: HostResult
    native: ClaudeExecution
    endpoint_stop: EndpointStop
    exchange_result: ExchangeResult | None
    endpoint: AnthropicEndpoint | None = None


def _manifest(root):
    value = _json(root, "transport.json")
    if (
        not isinstance(value, dict)
        or set(value)
        != {
            "version",
            "source_identity",
            "invocation_id",
            "nonce",
            "model",
            "boundary_identity",
            "timeout_seconds",
            "max_output_bytes",
            "max_output_tokens",
            "estimated_budget_usd",
            "inventory",
            "job",
            "prompt_sha256",
            "schema_sha256",
            "helper_sha256",
            "capability_sha256",
            "endpoint_sha256",
            "policy",
            "policy_sha256",
        }
        or value.get("version") != VERSION
        or value.get("source_identity") != host_source_identity()
    ):
        raise ValueError("incompatible Claude composition identity")
    for name in ("invocation_id", "nonce"):
        identifier(value[name])
    for name in (
        "boundary_identity",
        "prompt_sha256",
        "schema_sha256",
        "helper_sha256",
        "capability_sha256",
        "endpoint_sha256",
        "policy_sha256",
    ):
        sha256(value[name])
    if (
        type(value["timeout_seconds"]) not in (int, float)
        or not math.isfinite(value["timeout_seconds"])
        or not 0 < value["timeout_seconds"] <= 86400
        or type(value["max_output_bytes"]) is not int
        or not 0 < value["max_output_bytes"] <= 65536
        or type(value["max_output_tokens"]) is not int
        or not 0 < value["max_output_tokens"] <= 32768
        or type(value["estimated_budget_usd"]) not in (int, float)
        or not math.isfinite(value["estimated_budget_usd"])
        or value["estimated_budget_usd"] <= 0
    ):
        raise ValueError("invalid Claude composition limits")
    return value


def capture_claude_endpoint_stop(root, endpoint, *, wait_seconds=0.2):
    """Append a bound stop observation without rewriting the original outcome."""
    root = checked_directory(root)
    manifest = _manifest(root)
    if (
        endpoint.directory != root / "endpoint"
        or endpoint.exchange.root != root / "exchange"
        or endpoint.exchange.manifest["invocation_id"] != manifest["invocation_id"]
        or _hash(root / "endpoint/endpoint.json") != manifest["endpoint_sha256"]
    ):
        raise ValueError("Claude endpoint belongs to another invocation")
    stop = endpoint.close(wait_seconds=wait_seconds)
    paths = sorted((root / "stops").glob("*.json"))
    if len(paths) >= 16:
        raise ValueError("Claude stop capture limit")
    record = {
        "transport_sha256": digest(manifest),
        "sequence": len(paths) + 1,
        "previous": None if not paths else _hash(paths[-1]),
        "stop": asdict(stop),
    }
    durable_write(root / "stops" / f"{len(paths) + 1:06d}.json", canonical_json(record).encode())
    return stop


def _stops(root, manifest):
    paths = sorted((root / "stops").glob("*.json"))
    if not 1 <= len(paths) <= 16:
        raise ValueError("Claude stop captures missing or excessive")
    previous, stops = None, []
    booleans = ("listener_closed", "handler_stopped", "upstream_callback_stopped")
    counts = ("request_attempts", "exchange_requests", "upstream_callbacks")
    for number, path in enumerate(paths, 1):
        record = _json(path.parent, path.name)
        body = record.get("stop")
        if (
            path.name != f"{number:06d}.json"
            or set(record) != {"transport_sha256", "sequence", "previous", "stop"}
            or record["transport_sha256"] != digest(manifest)
            or type(record["sequence"]) is not int
            or record["sequence"] != number
            or record["previous"] != previous
            or not isinstance(body, dict)
            or set(body) != set((*booleans, *counts))
            or any(type(body[k]) is not bool for k in booleans)
            or any(type(body[k]) is not int or not 0 <= body[k] <= 16 for k in counts)
            or not body["upstream_callbacks"] <= 1
            or not body["upstream_callbacks"]
            <= body["exchange_requests"]
            <= body["request_attempts"]
        ):
            raise ValueError("invalid bound Claude stop capture")
        stops.append(EndpointStop(**body))
        previous = _hash(path)
    return stops


def _classify(native, stop, exchanged, timing, manifest, observation):
    local_stop = native.process.stopped and all(
        (
            stop.listener_closed,
            stop.handler_stopped,
            stop.upstream_callback_stopped,
        )
    )
    response = None if exchanged is None else exchanged.response
    usage = observation["usage"] if observation is not None else {}
    model = observation["reported_model"] if observation is not None else None
    text = ""
    if not local_stop:
        status = "reconciliation_required"
    elif timing["cancelled"]:
        status = "cancelled"
    elif timing["elapsed_seconds"] > manifest["timeout_seconds"]:
        status = "timeout"
    elif native.process.status in ("timeout", "cancelled"):
        status = native.process.status
    elif native.error is not None:
        status = "host_failure"
    elif exchanged is None or exchanged.status == "reconciliation_required":
        status = "reconciliation_required"
    elif (
        exchanged.status != "completed"
        or not timing["bindings_unchanged"]
        or response is None
        or native.parsed is None
        or native.parsed.text != response.text
        or native.parsed.resolved_model != response.reported_model
    ):
        status = "host_failure"
    else:
        status, text = "completed", response.text
    return HostResult(
        status,
        text,
        model,
        usage,
        timing["elapsed_seconds"],
        native.process.stdout,
        native.process.stderr,
        local_stop,
    )


def _observation(exchange):
    # Recompute from the digest-bound raw exchange bytes. Never trust a standalone
    # usage receipt or native SDK zero-fill to manufacture broker counters.
    if not (exchange.root / "usage-observation.json").exists():
        return None
    from .anthropic_boundary import observe_anthropic_usage
    from autoengineering.campaign.artifacts import read_bytes
    from autoengineering.campaign.records import ArtifactRef

    reference = ArtifactRef.from_dict(_json(exchange.root, "outcome.json")["raw"])
    observation = observe_anthropic_usage(read_bytes(exchange.root, reference, max_bytes=524288))
    if _json(exchange.root, "usage-observation.json") != observation:
        raise ValueError("Claude broker usage observation changed")
    return observation


def execute_brokered_claude(
    inventory: ClaudeInventory,
    *,
    model: str,
    prompt: str,
    context: InvocationContext,
    upstream: Callable[[bytes], bytes],
    boundary_identity: str,
    max_output_tokens: int,
    estimated_budget_usd: float,
    wrap_command: Callable[[tuple[str, ...], AnthropicEndpoint, Path, Path], WrappedCommand],
    fault: Callable[[str], None] = lambda _stage: None,
) -> ClaudeBrokeredExecution:
    """Compose one owned invocation. This grants no live or scheduler authority.

    The mandatory trusted wrapper receives the local helper/capability paths.
    They contain no provider credential. Upstream process stops remain a separate
    caller obligation, including when its callback has returned.
    """
    began = time.monotonic()
    identifier(context.invocation_id)
    identifier(context.nonce)
    sha256(boundary_identity)
    if type(prompt) is not str or not 0 < len(prompt.encode()) <= 65536:
        raise ValueError("invalid Claude broker prompt")
    if (
        type(context.timeout_seconds) not in (int, float)
        or not math.isfinite(context.timeout_seconds)
        or not 0 < context.timeout_seconds <= 86400
        or type(context.max_output_bytes) is not int
        or not 0 < context.max_output_bytes <= 65536
        or type(max_output_tokens) is not int
        or not 0 < max_output_tokens <= 32768
        or type(estimated_budget_usd) not in (int, float)
        or not math.isfinite(estimated_budget_usd)
        or estimated_budget_usd <= 0
    ):
        raise ValueError("invalid Claude broker limits")
    root = Path(context.directory).absolute()
    checked_directory(root.parent)
    root.mkdir(mode=0o700)
    for name in ("workspace", "home", "auth", "stops"):
        (root / name).mkdir(mode=0o700)
    durable_write(root / "prompt.txt", prompt.encode())
    schema = root / "workspace/schema.json"
    durable_write(schema, canonical_json(WIRE_SCHEMA).encode())
    exchange = AnthropicExchange.create(
        root / "exchange",
        invocation_id=context.invocation_id,
        requested_model=model,
        approved_prompt=prompt,
        output_schema=WIRE_SCHEMA,
        max_output_tokens=max_output_tokens,
    )
    endpoint = AnthropicEndpoint(exchange, upstream, directory=root / "endpoint")
    capability, helper = root / "auth/capability", root / "auth/helper"
    native = None
    try:
        durable_write(capability, endpoint.bootstrap_token.encode())
        durable_write(
            helper,
            (
                f"#!{Path(sys.executable).resolve()}\nfrom pathlib import Path\n"
                f"print(Path({str(capability)!r}).read_text())\n"
            ).encode(),
        )
        helper.chmod(0o700)

        def wrap(command):
            wrapped = wrap_command(command, endpoint, helper, capability)
            if not isinstance(wrapped, WrappedCommand):
                raise ValueError("Claude broker requires a pinned boundary policy")
            policy = Path(wrapped.policy).absolute()
            manifest = {
                "version": VERSION,
                "source_identity": host_source_identity(),
                "invocation_id": context.invocation_id,
                "nonce": context.nonce,
                "model": model,
                "boundary_identity": boundary_identity,
                "timeout_seconds": context.timeout_seconds,
                "max_output_bytes": context.max_output_bytes,
                "max_output_tokens": max_output_tokens,
                "estimated_budget_usd": estimated_budget_usd,
                "inventory": asdict(inventory),
                "job": {
                    "command": list(wrapped.command),
                    "cwd": str(root / "workspace"),
                    "environment": {
                        "PATH": "/usr/bin:/bin",
                        "LANG": "C.UTF-8",
                        "HOME": str(root / "home"),
                        "TMPDIR": str(root / "home"),
                        "CLAUDE_CODE_TMPDIR": str(root / "home"),
                    },
                    "keep_group_leader": True,
                    "owner_lease": "pipe-eof-v1",
                },
                "prompt_sha256": _hash(root / "prompt.txt"),
                "schema_sha256": _hash(schema),
                "helper_sha256": _hash(helper),
                "capability_sha256": _hash(capability),
                "endpoint_sha256": _hash(root / "endpoint/endpoint.json"),
                "policy": str(policy),
                "policy_sha256": _hash(policy),
            }
            durable_write(root / "transport.json", canonical_json(manifest).encode())
            _manifest(root)
            return wrapped.command

        def launched(identity):
            manifest = _manifest(root)
            if _json(root / "client", "job.json") != manifest["job"]:
                raise ValueError("Claude job differs before launch")
            durable_write(
                root / "job-binding.json",
                canonical_json(
                    {
                        "transport_sha256": digest(manifest),
                        "job_sha256": _hash(root / "client/job.json"),
                    }
                ).encode(),
            )
            context.on_launch(identity)

        native = execute_claude_transport(
            inventory,
            model=model,
            schema=schema,
            helper=helper,
            helper_sha256=_hash(helper),
            directory=root / "client",
            workspace=root / "workspace",
            home=root / "home",
            nonce=context.nonce,
            prompt=prompt.encode(),
            timeout_seconds=context.timeout_seconds - (time.monotonic() - began),
            max_output_bytes=context.max_output_bytes,
            max_budget_usd=estimated_budget_usd,
            on_launch=launched,
            wrap_command=wrap,
            cancelled=context.cancelled,
            loopback_port=endpoint.port,
        )
    finally:
        if (root / "transport.json").exists():
            try:
                stop = capture_claude_endpoint_stop(root, endpoint)
            except BaseException:
                # A damaged binding cannot excuse leaving the owned listener
                # live. This close does not invent a valid bound stop capture.
                endpoint.close(wait_seconds=0.2)
                raise
        else:
            endpoint.close(wait_seconds=0.2)
    manifest = _manifest(root)
    timing = {
        "transport_sha256": digest(manifest),
        "elapsed_seconds": time.monotonic() - began,
        "cancelled": bool(context.cancelled()),
        "bindings_unchanged": all(
            (
                _hash(schema) == manifest["schema_sha256"],
                _hash(helper) == manifest["helper_sha256"],
                _hash(capability) == manifest["capability_sha256"],
                _hash(Path(manifest["policy"])) == manifest["policy_sha256"],
            )
        ),
    }
    durable_write(root / "timing.json", canonical_json(timing).encode())
    exchanged = (
        exchange.recover() if stop.handler_stopped and stop.upstream_callback_stopped else None
    )
    result = _classify(
        native,
        stop,
        exchanged,
        timing,
        manifest,
        _observation(exchange) if exchanged is not None else None,
    )
    fault("before_outcome_commit")
    durable_write(
        root / "outcome.json",
        canonical_json(
            {
                "transport_sha256": digest(manifest),
                "native_completion_sha256": _hash(root / "client/completion.json"),
                "timing_sha256": _hash(root / "timing.json"),
                "initial_stop_sequence": 1,
                "status": result.status,
            }
        ).encode(),
    )
    return ClaudeBrokeredExecution(root, result, native, stop, exchanged, endpoint)


def recover_brokered_claude(root: Path) -> ClaudeBrokeredExecution:
    """Read original bound evidence only. Never launch, signal or open a lease."""
    root = checked_directory(root)
    manifest = _manifest(root)
    for path, field in (
        ("prompt.txt", "prompt_sha256"),
        ("workspace/schema.json", "schema_sha256"),
        ("auth/helper", "helper_sha256"),
        ("auth/capability", "capability_sha256"),
        ("endpoint/endpoint.json", "endpoint_sha256"),
    ):
        if _hash(root / path) != manifest[field]:
            raise ValueError("Claude original input binding changed")
    if _hash(Path(manifest["policy"])) != manifest["policy_sha256"]:
        raise ValueError("Claude boundary policy changed")
    if _json(root / "client", "job.json") != manifest["job"]:
        raise ValueError("Claude job binding changed")
    if (root / "client/process.json").exists():
        binding = _json(root, "job-binding.json")
        if binding != {
            "transport_sha256": digest(manifest),
            "job_sha256": _hash(root / "client/job.json"),
        }:
            raise ValueError("Claude prelaunch binding changed")
    if _hash(root / "client/stdin.bin") != manifest["prompt_sha256"]:
        raise ValueError("Claude original stdin changed")
    native = recover_claude_transport(
        root / "client",
        nonce=manifest["nonce"],
        model=manifest["model"],
        job_sha256=_hash(root / "client/job.json"),
        max_output_bytes=manifest["max_output_bytes"],
    )
    exchange = AnthropicExchange(root / "exchange")
    if (
        exchange.manifest["invocation_id"] != manifest["invocation_id"]
        or exchange.manifest["requested_model"] != manifest["model"]
        or exchange.manifest["approved_prompt"].encode() != (root / "prompt.txt").read_bytes()
        or exchange.manifest["output_schema"] != WIRE_SCHEMA
        or exchange.manifest["max_output_tokens"] != manifest["max_output_tokens"]
    ):
        raise ValueError("Claude exchange differs from original invocation")
    stops = _stops(root, manifest)
    timing = _json(root, "timing.json")
    if (
        set(timing) != {"transport_sha256", "elapsed_seconds", "cancelled", "bindings_unchanged"}
        or timing["transport_sha256"] != digest(manifest)
        or type(timing["elapsed_seconds"]) not in (int, float)
        or not math.isfinite(timing["elapsed_seconds"])
        or timing["elapsed_seconds"] < 0
        or any(type(timing[k]) is not bool for k in ("cancelled", "bindings_unchanged"))
    ):
        raise ValueError("invalid Claude timing receipt")
    stop = stops[-1]
    exchanged = (
        exchange.recover() if stop.handler_stopped and stop.upstream_callback_stopped else None
    )
    observation = _observation(exchange) if exchanged is not None else None
    if (root / "outcome.json").exists():
        saved = _json(root, "outcome.json")
        initial = saved.get("initial_stop_sequence")
        if (
            type(initial) is not int
            or not 1 <= initial <= len(stops)
            or saved
            != {
                "transport_sha256": digest(manifest),
                "native_completion_sha256": _hash(root / "client/completion.json"),
                "timing_sha256": _hash(root / "timing.json"),
                "initial_stop_sequence": initial,
                "status": _classify(
                    native, stops[initial - 1], exchanged, timing, manifest, observation
                ).status,
            }
        ):
            raise ValueError("Claude original outcome contradicts bound evidence")
    result = _classify(native, stop, exchanged, timing, manifest, observation)
    return ClaudeBrokeredExecution(root, result, native, stop, exchanged)
