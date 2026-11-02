"""Versioned Codex CLI transport and offline conformance hooks.

This module does not authorize live dispatch. The scheduler still requires a
separately qualified host boundary. CLI read-only mode is not a privacy boundary.
Official event/structured-output reference:
https://learn.chatgpt.com/docs/non-interactive-mode
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
from pathlib import Path
import subprocess
from types import MappingProxyType

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import unique_json
from autoengineering.campaign.store import checked_directory

from ..process import ProcessResult, supervise_process

ADAPTER_VERSION = "1.0"
REQUIRED_FLAGS = (
    "--json",
    "--output-schema",
    "--ephemeral",
    "--ignore-user-config",
    "--ignore-rules",
    "--skip-git-repo-check",
    "--sandbox",
    "--model",
)


@dataclass(frozen=True)
class CodexInventory:
    executable: str
    sha256: str
    version: str
    supported_flags: tuple[str, ...]


def inspect_codex(executable: Path) -> CodexInventory:
    path = Path(executable).resolve(strict=True)
    confined_file(path.parent, path.name)
    outputs = []
    for arguments in (("--version",), ("exec", "--help")):
        result = subprocess.run(
            (str(path), *arguments),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=5,
            check=False,
            env={
                "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "HOME": "/nonexistent",
                "CODEX_HOME": "/nonexistent",
            },
        )
        if result.returncode or len(result.stdout) > 65536 or len(result.stderr) > 65536:
            raise ValueError("Codex capability probe failed")
        outputs.append(result.stdout.decode("utf-8"))
    version, help_text = outputs
    if not version.startswith("codex-cli ") or not all(
        flag in help_text for flag in REQUIRED_FLAGS
    ):
        raise ValueError("Codex executable lacks required capabilities")
    return CodexInventory(
        str(path), hashlib.sha256(path.read_bytes()).hexdigest(), version.strip(), REQUIRED_FLAGS
    )


def subscription_authentication(home: Path) -> str:
    """Return only the mode. Never retain credentials or include them in errors."""
    checked_directory(home)
    path = confined_file(home, "auth.json")
    if path.stat().st_size > 262144:
        raise ValueError("authentication file exceeds size limit")
    data = unique_json(path.read_text())
    if not isinstance(data, dict) or data.get("auth_mode") != "chatgpt":
        raise ValueError("Codex subscription authentication mode mismatch")
    return "subscription"


@dataclass(frozen=True)
class CodexExecution:
    process: ProcessResult
    final_text: str | None
    resolved_model: str | None
    usage: Mapping[str, int | None]
    parse_error: str | None


def parse_events(raw: bytes) -> tuple[str, str | None, Mapping[str, int | None]]:
    """Extract reported text and usage. Requested model is never a resolved model."""
    if len(raw) > 65536:
        raise ValueError("Codex transcript exceeds event-parser limit")
    final = None
    model = None
    terminal = 0
    usage = {
        name: None
        for name in (
            "input_tokens",
            "cached_input_tokens",
            "output_tokens",
            "reasoning_output_tokens",
            "total_tokens",
        )
    }
    lines = raw.decode("utf-8").splitlines()
    if not lines:
        raise ValueError("Codex produced no event stream")
    for line in lines:
        event = unique_json(line)
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ValueError("invalid Codex event envelope")
        kind = event["type"]
        if kind in ("error", "turn.failed"):
            raise ValueError("Codex reported a failed turn")
        if terminal:
            raise ValueError("Codex emitted events after completion")
        # Only actual host metadata can establish the model. Current exec
        # streams may omit this field, which remains incomplete provenance.
        if "model" in event:
            if type(event["model"]) is not str or not event["model"].strip():
                raise ValueError("invalid reported model metadata")
            if model is not None and model != event["model"]:
                raise ValueError("conflicting reported model metadata")
            model = event["model"]
        if kind.startswith("item."):
            item = event.get("item")
            if not isinstance(item, dict) or item.get("type") not in ("agent_message", "reasoning"):
                raise ValueError("Codex used a tool outside the supplied-role policy")
            if kind == "item.completed" and item["type"] == "agent_message":
                if type(item.get("text")) is not str or not item["text"].strip():
                    raise ValueError("Codex completed an empty agent message")
                final = item["text"]
        elif kind == "turn.completed":
            supplied = event.get("usage")
            if not isinstance(supplied, dict):
                raise ValueError("Codex completed without a usage envelope")
            for name in usage:
                if name in supplied:
                    value = supplied[name]
                    if value is not None and (type(value) is not int or value < 0):
                        raise ValueError("Codex reported invalid token usage")
                    usage[name] = value
            if usage["total_tokens"] is None and all(
                usage[key] is not None for key in ("input_tokens", "output_tokens")
            ):
                usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
            terminal += 1
        elif kind not in ("thread.started", "turn.started"):
            raise ValueError("unsupported Codex event type")
    if terminal != 1 or final is None:
        raise ValueError("Codex event stream has no complete final response")
    return final, model, MappingProxyType(usage)


def execute_codex_transport(
    inventory: CodexInventory,
    *,
    model: str,
    schema: Path,
    directory: Path,
    workspace: Path,
    home: Path,
    nonce: str,
    prompt: bytes,
    timeout_seconds: float,
    max_output_bytes: int,
    on_launch: Callable[[dict], None],
    cancelled: Callable[[], bool] = lambda: False,
    wrap_command: Callable[[tuple[str, ...]], tuple[str, ...]],
) -> CodexExecution:
    """Trusted transport primitive. A caller must supply an OS boundary wrapper.

    Offline tests use trusted fake executables. Live callers must independently
    qualify the wrapper's filesystem, network and tool boundaries before use.
    This primitive is not exposed as a worker tool or production scheduler host.
    """
    path = Path(inventory.executable)
    if (
        hashlib.sha256(confined_file(path.parent, path.name).read_bytes()).hexdigest()
        != inventory.sha256
    ):
        raise ValueError("Codex executable changed after capability discovery")
    subscription_authentication(home)
    checked_directory(workspace)
    confined_file(schema.parent, schema.name)
    if type(model) is not str or not model.strip():
        raise ValueError("Codex transport requires an explicit requested model")
    command = (
        inventory.executable,
        "exec",
        "--json",
        "--output-schema",
        str(schema),
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--model",
        model,
        "-",
    )
    result = supervise_process(
        wrap_command(command),
        directory=directory,
        cwd=workspace,
        environment={
            "PATH": "/usr/bin:/bin",
            "LANG": "C.UTF-8",
            "HOME": str(home),
            "CODEX_HOME": str(home),
        },
        nonce=nonce,
        stdin=prompt,
        timeout_seconds=timeout_seconds,
        max_output_bytes=max_output_bytes,
        on_launch=on_launch,
        cancelled=cancelled,
    )
    # supervise_process has already persisted raw stdout/stderr and its stop
    # receipt. A parse failure cannot erase or overwrite those bytes.
    try:
        text, resolved, usage = parse_events(result.stdout)
    except (ValueError, TypeError, UnicodeError):
        # Do not echo untrusted event content or authentication material in errors.
        return CodexExecution(
            result,
            None,
            None,
            MappingProxyType({}),
            "invalid_codex_events" if result.status == "completed" else None,
        )
    # A nonzero exit cannot complete a handoff, but it does not erase valid
    # host-reported usage or model metadata already present in the raw stream.
    return CodexExecution(
        result, text if result.status == "completed" else None, resolved, usage, None
    )
