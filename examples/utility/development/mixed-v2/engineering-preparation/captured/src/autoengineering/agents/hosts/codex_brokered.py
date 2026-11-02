"""Experimental version 2 Codex transport through a private text endpoint.

Version 1 remains unchanged. This primitive grants no live-call authority and
is not registered with the production scheduler. The caller must qualify the
OS wrapper and separately supervise the trusted upstream transport. No provider
credentials enter the client home or environment.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
import hashlib
import math
from pathlib import Path
import subprocess
import time

from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import (
    ProcessResult,
    recover_completed_process,
    supervise_process,
)
from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.execution import live_members
from autoengineering.campaign.records import ArtifactRef, identifier, sha256
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write

from .base import HostResult, InvocationContext
from .codex import CodexInventory, REQUIRED_FLAGS, inspect_codex, parse_events
from .text_endpoint import EndpointStop, TextEndpoint
from .text_exchange import ExchangeResult, TextExchange
from .model_catalog import read_model_catalog, validate_model_catalog

VERSION = "codex-text-2.0"
OWNED_VERSION = "codex-text-2.1"
STOP_GRACE_SECONDS = 0.2
BROKERED_FLAGS = (*REQUIRED_FLAGS, "--dangerously-bypass-approvals-and-sandbox")
DISABLED_FEATURES = (
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


@dataclass(frozen=True)
class WrappedCommand:
    command: tuple[str, ...]
    policy: Path


@dataclass(frozen=True)
class BrokeredExecution:
    root: Path
    host_result: HostResult
    native: ProcessResult
    endpoint_stop: EndpointStop
    exchange_result: ExchangeResult | None
    endpoint: TextEndpoint | None = None


def inspect_brokered_codex(executable: Path) -> CodexInventory:
    inventory = inspect_codex(executable)
    result = subprocess.run(
        (inventory.executable, "exec", "--help"),
        capture_output=True,
        timeout=5,
        check=False,
        env={
            "PATH": "/usr/bin:/bin",
            "LANG": "C",
            "HOME": "/nonexistent",
            "CODEX_HOME": "/nonexistent",
        },
    )
    if (
        result.returncode
        or len(result.stdout) > 65536
        or len(result.stderr) > 65536
        or not all(flag in result.stdout.decode() for flag in BROKERED_FLAGS)
    ):
        raise ValueError("Codex lacks brokered transport capabilities")
    return CodexInventory(inventory.executable, inventory.sha256, inventory.version, BROKERED_FLAGS)


def _json(root, name, limit=1048576):
    path = confined_file(root, name)
    if path.stat().st_size > limit:
        raise ValueError("brokered transport record exceeds size limit")
    return unique_json(path.read_text())


def _put(root, data, name, producer):
    media = "text/plain" if name.endswith((".txt", ".sb")) else "application/json"
    return put_bytes(root, data, name=name, media_type=media, producer=producer)


def _manifest(root):
    manifest = _json(root, "transport.json")
    if (
        not isinstance(manifest, dict)
        or set(manifest)
        != {
            "version",
            "source_identity",
            "invocation_id",
            "nonce",
            "requested_model",
            "inventory",
            "boundary_identity",
            "workspace",
            "environment",
            "timeout_seconds",
            "max_output_bytes",
            "command_sha256",
            "prompt",
            "schema",
            "endpoint",
            "boundary_policy",
            "stop_grace_seconds",
            "exchange_invocation_id",
            "model_catalog",
        }
        or manifest.get("version") not in (VERSION, OWNED_VERSION)
        or manifest.get("source_identity") != host_source_identity()
    ):
        raise ValueError("incompatible brokered transport identity")
    identifier(manifest["invocation_id"])
    identifier(manifest["nonce"])
    identifier(manifest["exchange_invocation_id"])
    sha256(manifest["boundary_identity"])
    sha256(manifest["command_sha256"])
    if (
        type(manifest["timeout_seconds"]) not in (int, float)
        or not math.isfinite(manifest["timeout_seconds"])
        or manifest["timeout_seconds"] <= 0
        or type(manifest["max_output_bytes"]) is not int
        or not 0 < manifest["max_output_bytes"] <= 65536
        or type(manifest["requested_model"]) is not str
        or not manifest["requested_model"].strip()
        or manifest["stop_grace_seconds"] != STOP_GRACE_SECONDS
    ):
        raise ValueError("invalid brokered transport limits")
    return manifest


def capture_endpoint_stop(
    root: Path, endpoint: TextEndpoint, *, wait_seconds: float = 0.2
) -> EndpointStop:
    """Append an owned endpoint stop capture. Never infer stop from a port number.

    A later verified stop can follow an uncertain one. Original captures and the
    original transport outcome remain unchanged. This does not call upstream.
    """
    root = checked_directory(root)
    manifest = _manifest(root)
    if (
        endpoint.directory != root / "endpoint"
        or endpoint.exchange.root != root / "exchange"
        or endpoint.exchange.manifest["invocation_id"] != manifest["exchange_invocation_id"]
    ):
        raise ValueError("endpoint belongs to another transport")
    endpoint_metadata = read_bytes(
        root, ArtifactRef.from_dict(manifest["endpoint"]), max_bytes=16384
    )
    if confined_file(root, "endpoint/endpoint.json").read_bytes() != endpoint_metadata:
        raise ValueError("endpoint binding changed")
    stopped = endpoint.close(wait_seconds=wait_seconds)
    captures = sorted((root / "stops").glob("*.json"))
    previous = None if not captures else digest(_json(root, str(captures[-1].relative_to(root))))
    reference = _put(
        root,
        canonical_json(asdict(stopped)).encode(),
        "endpoint-stop.json",
        manifest["invocation_id"],
    )
    capture = {
        "sequence": len(captures) + 1,
        "previous": previous,
        "transport_sha256": digest(manifest),
        "stop": reference.to_dict(),
    }
    durable_write(
        root / "stops" / f"{len(captures) + 1:06d}.json", canonical_json(capture).encode()
    )
    return stopped


def _stop_history(root, manifest):
    captures = sorted((root / "stops").glob("*.json"))
    if not captures or len(captures) > 16:
        raise ValueError("endpoint stop capture is missing or exceeds limit")
    previous, history = None, []
    for sequence, path in enumerate(captures, 1):
        if path.name != f"{sequence:06d}.json":
            raise ValueError("endpoint stop sequence mismatch")
        value = _json(root, str(path.relative_to(root)))
        if (
            set(value) != {"sequence", "previous", "transport_sha256", "stop"}
            or type(value["sequence"]) is not int
            or value["sequence"] != sequence
            or value["previous"] != previous
            or value["transport_sha256"] != digest(manifest)
        ):
            raise ValueError("endpoint stop binding mismatch")
        body = unique_json(
            read_bytes(root, ArtifactRef.from_dict(value["stop"]), max_bytes=16384).decode()
        )
        if (
            set(body)
            != {
                "listener_closed",
                "handler_stopped",
                "upstream_callback_stopped",
                "request_attempts",
                "exchange_requests",
                "upstream_callbacks",
            }
            or any(
                type(body[k]) is not bool
                for k in ("listener_closed", "handler_stopped", "upstream_callback_stopped")
            )
            or any(
                type(body[k]) is not int or not 0 <= body[k] <= 16
                for k in ("request_attempts", "exchange_requests", "upstream_callbacks")
            )
            or not body["upstream_callbacks"] <= 1
            or not body["upstream_callbacks"]
            <= body["exchange_requests"]
            <= body["request_attempts"]
        ):
            raise ValueError("invalid endpoint stop capture")
        history.append(EndpointStop(**body))
        previous = digest(value)
    return history


def _latest_stop(root, manifest):
    return _stop_history(root, manifest)[-1]


def _classify(native, stop, exchanged, timing, manifest):
    local_stop = (
        native.stopped
        and stop.listener_closed
        and stop.handler_stopped
        and stop.upstream_callback_stopped
    )
    response = None if exchanged is None else exchanged.response
    usage = {} if response is None else dict(response.usage)
    model = None if response is None else response.reported_model
    text = ""
    if not local_stop:
        status = "reconciliation_required"
    elif timing["cancelled"]:
        status = "cancelled"
    elif timing["elapsed_seconds"] > manifest["timeout_seconds"] or timing["prelaunch_timeout"]:
        status = "timeout"
    elif native.status in {"cancelled", "timeout"}:
        status = native.status
    elif native.status != "completed" or native.truncated:
        status = "host_failure"
    elif exchanged is None or exchanged.status == "reconciliation_required":
        status = "reconciliation_required"
    elif (
        exchanged.status != "completed"
        or not timing["schema_unchanged"]
        or not timing["boundary_unchanged"]
    ):
        status = "host_failure"
    else:
        try:
            final, cli_model, _cli_usage = parse_events(native.stdout)
        except (ValueError, TypeError, UnicodeError):
            status = "host_failure"
        else:
            if final != response.text or (cli_model is not None and cli_model != model):
                status = "host_failure"
            else:
                status, text = "completed", final
    return HostResult(
        status,
        text,
        model,
        usage,
        timing["elapsed_seconds"],
        native.stdout,
        native.stderr,
        local_stop,
    )


def recover_brokered_transport(root: Path) -> BrokeredExecution:
    """Verify saved process/endpoint/exchange evidence; never launch or signal."""
    root = checked_directory(root)
    manifest = _manifest(root)
    prompt = read_bytes(root, ArtifactRef.from_dict(manifest["prompt"]), max_bytes=65536)
    schema = read_bytes(root, ArtifactRef.from_dict(manifest["schema"]), max_bytes=65536)
    if manifest["model_catalog"] is not None:
        catalog = read_bytes(
            root, ArtifactRef.from_dict(manifest["model_catalog"]), max_bytes=65536
        )
        validate_model_catalog(catalog, manifest["requested_model"])
        home = Path(manifest["environment"]["CODEX_HOME"])
        if read_model_catalog(home / "model-catalog.json", manifest["requested_model"]) != catalog:
            raise ValueError("native model catalog changed")
    endpoint = read_bytes(root, ArtifactRef.from_dict(manifest["endpoint"]), max_bytes=16384)
    if confined_file(root, "endpoint/endpoint.json").read_bytes() != endpoint:
        raise ValueError("endpoint metadata changed")
    if manifest["boundary_policy"] is not None:
        policy = manifest["boundary_policy"]
        if set(policy) != {"path", "artifact"}:
            raise ValueError("invalid boundary policy binding")
        read_bytes(root, ArtifactRef.from_dict(policy["artifact"]), max_bytes=65536)
    native = recover_completed_process(
        root / "client", nonce=manifest["nonce"], max_output_bytes=manifest["max_output_bytes"]
    )
    if native.identity is not None and live_members(native.identity.pgid):
        raise ValueError("native process group is still live or ambiguous")
    job = _json(root, "client/job.json")
    expected_keys = {"command", "cwd", "environment"}
    if manifest["version"] == OWNED_VERSION:
        expected_keys |= {"keep_group_leader", "owner_lease"}
    if (
        set(job) != expected_keys
        or (
            manifest["version"] == OWNED_VERSION
            and (
                job.get("keep_group_leader") is not True or job.get("owner_lease") != "pipe-eof-v1"
            )
        )
        or digest(job["command"]) != manifest["command_sha256"]
        or job["cwd"] != manifest["workspace"]
        or job["environment"] != manifest["environment"]
        or confined_file(root, "client/stdin.bin").read_bytes() != prompt
    ):
        raise ValueError("native command or input binding mismatch")
    exchange = TextExchange(root / "exchange")
    if (
        exchange.manifest["invocation_id"] != manifest["exchange_invocation_id"]
        or exchange.manifest["requested_model"] != manifest["requested_model"]
        or exchange.manifest["approved_prompt"].encode() != prompt
        or exchange.manifest["output_schema"] != unique_json(schema.decode())
    ):
        raise ValueError("exchange policy binding mismatch")
    history = _stop_history(root, manifest)
    stop = history[-1]
    timing = _json(root, "timing.json")
    if (
        set(timing)
        != {
            "transport_sha256",
            "elapsed_seconds",
            "cancelled",
            "prelaunch_timeout",
            "schema_unchanged",
            "boundary_unchanged",
        }
        or timing["transport_sha256"] != digest(manifest)
        or type(timing["elapsed_seconds"]) not in (int, float)
        or not math.isfinite(timing["elapsed_seconds"])
        or timing["elapsed_seconds"] < 0
        or any(
            type(timing[k]) is not bool
            for k in ("cancelled", "prelaunch_timeout", "schema_unchanged", "boundary_unchanged")
        )
    ):
        raise ValueError("invalid transport timing receipt")
    exchanged = None
    if stop.handler_stopped and stop.upstream_callback_stopped:
        exchanged = exchange.recover()
    result = _classify(native, stop, exchanged, timing, manifest)
    outcome = root / "transport-outcome.json"
    if outcome.exists():
        saved = _json(root, "transport-outcome.json")
        if set(saved) != {
            "transport_sha256",
            "native_completion",
            "timing",
            "status",
            "initial_stop_sequence",
        }:
            raise ValueError("invalid transport outcome fields")
        # The original outcome binds immutable native/timing bytes. A later stop
        # capture may resolve uncertainty without rewriting that old outcome.
        for name in ("native_completion", "timing"):
            reference = ArtifactRef.from_dict(saved[name])
            value = read_bytes(root, reference, max_bytes=1048576)
            live = confined_file(
                root, "client/completion.json" if name == "native_completion" else "timing.json"
            )
            if live.read_bytes() != value:
                raise ValueError("transport outcome artifact mismatch")
        if saved["transport_sha256"] != digest(manifest):
            raise ValueError("transport outcome identity mismatch")
        if saved["status"] not in {
            "completed",
            "host_failure",
            "timeout",
            "cancelled",
            "reconciliation_required",
        }:
            raise ValueError("invalid original transport outcome")
        sequence = saved["initial_stop_sequence"]
        if type(sequence) is not int or not 1 <= sequence <= len(history):
            raise ValueError("invalid initial stop sequence")
        original_status = _classify(
            native, history[sequence - 1], exchanged, timing, manifest
        ).status
        if saved["status"] != original_status:
            raise ValueError("original transport status contradicts evidence")
    return BrokeredExecution(root, result, native, stop, exchanged)


def execute_brokered_codex(
    inventory: CodexInventory,
    *,
    model: str,
    schema: Path,
    workspace: Path,
    home: Path,
    prompt: bytes,
    context: InvocationContext,
    upstream: Callable[[bytes], bytes],
    boundary_identity: str,
    wrap_command: Callable[[tuple[str, ...], TextEndpoint], tuple[str, ...] | WrappedCommand],
    fault: Callable[[str], None] = lambda _stage: None,
    owned_native: bool = False,
    model_catalog: bytes | None = None,
) -> BrokeredExecution:
    """Launch one credentialless CLI invocation under a caller's OS wrapper.

    Raw events and provider evidence are separate. Success requires exact final
    text agreement and verified local stops. The wrapper is mandatory, but its
    digest is not proof of qualification. This does not enable scheduler use.
    """
    began = time.monotonic()
    if type(owned_native) is not bool:
        raise ValueError("owned native profile selection must be boolean")
    identifier(context.invocation_id)
    identifier(context.nonce)
    sha256(boundary_identity)
    if (
        type(context.timeout_seconds) not in (int, float)
        or not math.isfinite(context.timeout_seconds)
        or context.timeout_seconds <= 0
        or type(context.max_output_bytes) is not int
        or not 0 < context.max_output_bytes <= 65536
        or type(prompt) is not bytes
        or not 0 < len(prompt) <= 65536
    ):
        raise ValueError("invalid brokered invocation limits")
    text = prompt.decode()
    workspace, home = checked_directory(workspace), checked_directory(home)
    if any(home.iterdir()):
        raise ValueError("brokered client home must be fresh and empty")
    if model_catalog is not None:
        validate_model_catalog(model_catalog, model)
    executable = Path(inventory.executable)
    if not all(flag in inventory.supported_flags for flag in BROKERED_FLAGS):
        raise ValueError("brokered capability inspection is required")
    if (
        hashlib.sha256(confined_file(executable.parent, executable.name).read_bytes()).hexdigest()
        != inventory.sha256
    ):
        raise ValueError("Codex executable changed after inspection")
    schema_path = confined_file(schema.parent, schema.name)
    if schema_path.stat().st_size > 65536:
        raise ValueError("output schema exceeds size limit")
    schema_raw = schema_path.read_bytes()
    schema_data = unique_json(schema_raw.decode())
    root = Path(context.directory).absolute()
    checked_directory(root.parent)
    root.mkdir(mode=0o700)
    for name in ("artifacts", "stops"):
        (root / name).mkdir(mode=0o700)
    producer = context.invocation_id
    prompt_ref = _put(root, prompt, "prompt.txt", producer)
    schema_ref = _put(root, schema_raw, "schema.json", producer)
    exchange_id = "exchange-" + digest(
        {"invocation_id": producer, "nonce": context.nonce, "directory": str(root)}
    )
    exchange = TextExchange.create(
        root / "exchange",
        invocation_id=exchange_id,
        requested_model=model,
        approved_prompt=text,
        output_schema=schema_data,
    )
    endpoint = TextEndpoint(exchange, upstream, directory=root / "endpoint")
    result, prelaunch_timeout = None, False
    try:
        options = {
            "model_provider": '"bounded_text"',
            "model_providers.bounded_text.name": '"Bounded text broker"',
            "model_providers.bounded_text.base_url": canonical_json(endpoint.base_url),
            "model_providers.bounded_text.wire_api": '"responses"',
            "model_providers.bounded_text.requires_openai_auth": "false",
            "model_providers.bounded_text.supports_websockets": "false",
            "model_providers.bounded_text.request_max_retries": "0",
            "model_providers.bounded_text.stream_max_retries": "0",
            "model_providers.bounded_text.stream_idle_timeout_ms": "5000",
            "web_search": '"disabled"',
            "skills.bundled.enabled": "false",
            "skills.include_instructions": "false",
            **{f"features.{name}": "false" for name in DISABLED_FEATURES},
        }
        catalog_ref = None
        if model_catalog is not None:
            durable_write(home / "model-catalog.json", model_catalog)
            catalog_ref = _put(root, model_catalog, "model-catalog.json", producer).to_dict()
            options["model_catalog_json"] = canonical_json(str(home / "model-catalog.json"))
        command = [
            inventory.executable,
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            "--model",
            model,
            "--color",
            "never",
            "--output-schema",
            str(schema_path),
        ]
        for key, value in options.items():
            command.extend(("-c", f"{key}={value}"))
        command.append("-")
        wrapped = wrap_command(tuple(command), endpoint)
        policy = None
        if isinstance(wrapped, WrappedCommand):
            path = confined_file(wrapped.policy.parent, wrapped.policy.name)
            if path.stat().st_size > 65536:
                raise ValueError("boundary policy exceeds size limit")
            reference = _put(root, path.read_bytes(), "boundary-policy.sb", producer)
            policy = {"path": str(path), "artifact": reference.to_dict()}
            wrapped = wrapped.command
        environment = {
            "PATH": "/usr/bin:/bin",
            "LANG": "C",
            "LC_ALL": "C",
            "HOME": str(home),
            "CODEX_HOME": str(home),
            "TMPDIR": str(home),
        }
        metadata = _put(
            root,
            confined_file(root, "endpoint/endpoint.json").read_bytes(),
            "endpoint.json",
            producer,
        )
        manifest = {
            "version": OWNED_VERSION if owned_native else VERSION,
            "source_identity": host_source_identity(),
            "invocation_id": producer,
            "nonce": context.nonce,
            "requested_model": model,
            "model_catalog": catalog_ref,
            "inventory": asdict(inventory),
            "boundary_identity": boundary_identity,
            "workspace": str(workspace),
            "environment": environment,
            "timeout_seconds": context.timeout_seconds,
            "max_output_bytes": context.max_output_bytes,
            "command_sha256": digest(list(wrapped)),
            "prompt": prompt_ref.to_dict(),
            "schema": schema_ref.to_dict(),
            "endpoint": metadata.to_dict(),
            "boundary_policy": policy,
            "stop_grace_seconds": STOP_GRACE_SECONDS,
            "exchange_invocation_id": exchange_id,
        }
        durable_write(root / "transport.json", canonical_json(manifest).encode())
        remaining = context.timeout_seconds - (time.monotonic() - began)
        prelaunch_timeout = remaining <= 0
        result = supervise_process(
            wrapped,
            directory=root / "client",
            cwd=workspace,
            environment=environment,
            nonce=context.nonce,
            stdin=prompt,
            timeout_seconds=max(remaining, 0.001),
            max_output_bytes=context.max_output_bytes,
            on_launch=context.on_launch,
            cancelled=lambda: prelaunch_timeout or context.cancelled(),
            parent_watchdog=owned_native,
        )
    finally:
        if (root / "transport.json").exists():
            capture_endpoint_stop(root, endpoint, wait_seconds=STOP_GRACE_SECONDS)
            unchanged = (
                schema_path.is_file()
                and not schema_path.is_symlink()
                and schema_path.stat().st_size <= 65536
                and hashlib.sha256(schema_path.read_bytes()).hexdigest() == schema_ref.sha256
            )
            timing = {
                "transport_sha256": digest(manifest),
                "elapsed_seconds": time.monotonic() - began,
                "cancelled": bool(context.cancelled()),
                "prelaunch_timeout": prelaunch_timeout,
                "schema_unchanged": unchanged,
                "boundary_unchanged": (
                    policy is None
                    or (
                        Path(policy["path"]).is_file()
                        and not Path(policy["path"]).is_symlink()
                        and Path(policy["path"]).stat().st_size <= 65536
                        and hashlib.sha256(Path(policy["path"]).read_bytes()).hexdigest()
                        == policy["artifact"]["sha256"]
                    )
                ),
            }
            durable_write(root / "timing.json", canonical_json(timing).encode())
        else:
            endpoint.close()
    if result.stopped:
        recovered = recover_brokered_transport(root)
    else:
        stopped = _latest_stop(root, manifest)
        host = HostResult(
            "reconciliation_required",
            "",
            None,
            {},
            timing["elapsed_seconds"],
            result.stdout,
            result.stderr,
            False,
        )
        recovered = BrokeredExecution(root, host, result, stopped, None)
    fault("before_outcome_commit")
    completion = _put(
        root,
        confined_file(root, "client/completion.json").read_bytes(),
        "native-completion.json",
        producer,
    )
    timing_ref = _put(
        root, confined_file(root, "timing.json").read_bytes(), "timing.json", producer
    )
    durable_write(
        root / "transport-outcome.json",
        canonical_json(
            {
                "transport_sha256": digest(manifest),
                "native_completion": completion.to_dict(),
                "timing": timing_ref.to_dict(),
                "status": recovered.host_result.status,
                "initial_stop_sequence": len(list((root / "stops").glob("*.json"))),
            }
        ).encode(),
    )
    return BrokeredExecution(
        root,
        recovered.host_result,
        result,
        recovered.endpoint_stop,
        recovered.exchange_result,
        endpoint,
    )
