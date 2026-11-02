"""Bounded Claude Code transport primitive, not an admitted scheduler host.

Primary protocol references:
https://code.claude.com/docs/en/headless
https://code.claude.com/docs/en/cli-reference
https://platform.claude.com/docs/en/api/rate-limits

A trusted caller must supply an independently qualified OS wrapper and credential
helper. This module grants no live authority and never reads credential material.
Existing HostSelection records and scheduler admission remain unchanged.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
import hashlib
import math
from pathlib import Path
import re
import shlex
import subprocess
import sys
from types import MappingProxyType

from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory
from ..process import ProcessResult, recover_completed_process, supervise_process

VERSION = "claude-bare-transport-1.1"
SUPPORTED_VERSION = "2.1.310 (Claude Code)"
REQUIRED_FLAGS = (
    "--print",
    "--bare",
    "--output-format",
    "--input-format",
    "--json-schema",
    "--model",
    "--tools",
    "--disable-slash-commands",
    "--strict-mcp-config",
    "--mcp-config",
    "--setting-sources",
    "--settings",
    "--no-session-persistence",
    "--permission-mode",
    "--max-budget-usd",
)


def _hash(path: Path, limit: int) -> str:
    path = confined_file(path.parent, path.name)
    if not 0 < path.stat().st_size <= limit:
        raise ValueError("Claude transport file exceeds its bound")
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


@dataclass(frozen=True)
class ClaudeInventory:
    executable: str
    sha256: str
    version: str
    supported_flags: tuple[str, ...]


def inspect_claude(executable: Path) -> ClaudeInventory:
    """Version/help only. No authentication probe, prompt, login or update."""
    path = Path(executable).resolve(strict=True)
    before = _hash(path, 512 * 1024 * 1024)
    outputs = []
    for args in (("--version",), ("--help",)):
        result = subprocess.run(
            (str(path), *args),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=5,
            check=False,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        if result.returncode or len(result.stdout) > 65536 or len(result.stderr) > 65536:
            raise ValueError("Claude capability probe failed")
        outputs.append(result.stdout.decode("utf-8"))
    if (
        outputs[0].strip() != SUPPORTED_VERSION
        or not all(
            re.search(r"(?<![\w-])" + re.escape(flag) + r"(?=[\s,=]|$)", outputs[1])
            for flag in REQUIRED_FLAGS
        )
        or _hash(path, 512 * 1024 * 1024) != before
    ):
        raise ValueError("Claude executable version or capabilities are unsupported")
    return ClaudeInventory(str(path), before, SUPPORTED_VERSION, REQUIRED_FLAGS)


@dataclass(frozen=True)
class ClaudeResult:
    text: str | None
    reported_models: tuple[str, ...]
    usage: Mapping[str, int | None]
    estimated_cost_usd: float | None
    rejection: str | None

    def __post_init__(self):
        object.__setattr__(self, "usage", MappingProxyType(dict(self.usage)))

    @property
    def billed_cost_usd(self):
        # The SDK total_cost_usd is a client-side estimate, not billing evidence.
        return None

    @property
    def resolved_model(self):
        return self.reported_models[0] if len(self.reported_models) == 1 else None


def parse_result(raw: bytes) -> ClaudeResult:
    """Parse one structured result. SDK costs are estimates. Missing token categories stay unknown.

    This is CLI JSON mode, not the streaming protocol. Subtype alone does not
    establish success. No plain-text fallback, requested-model substitution,
    session resume, or silent aggregation across reported models is permitted.
    """
    if type(raw) is not bytes or not 0 < len(raw) <= 65536:
        raise ValueError("Claude result exceeds parser bound")
    try:
        value = unique_json(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("invalid Claude result JSON") from None
    if not isinstance(value, dict) or value.get("type") != "result":
        raise ValueError("invalid Claude result envelope")
    supplied = value.get("usage")
    if supplied is not None and not isinstance(supplied, dict):
        raise ValueError("invalid Claude usage envelope")
    supplied = supplied or {}

    def count(name):
        number = supplied.get(name)
        if number is not None and (type(number) is not int or number < 0):
            raise ValueError("invalid Claude token count")
        return number

    uncached, cached, created, output = (
        count(name)
        for name in (
            "input_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
            "output_tokens",
        )
    )
    # Anthropic input_tokens excludes cache reads and writes. Do not omit them
    # from cross-host input totals or assume an absent category means zero.
    inputs = (
        sum((uncached, cached, created))
        if all(n is not None for n in (uncached, cached, created))
        else None
    )
    usage = {
        "input_tokens": inputs,
        "uncached_input_tokens": uncached,
        "cached_input_tokens": cached,
        "cache_creation_input_tokens": created,
        "output_tokens": output,
        "total_tokens": inputs + output if inputs is not None and output is not None else None,
        "reasoning_output_tokens": None,
    }
    models = value.get("modelUsage")
    if models is not None and (
        not isinstance(models, dict)
        or any(
            not re.fullmatch(r"claude-[A-Za-z0-9._-]{1,128}", name) or not isinstance(details, dict)
            for name, details in models.items()
        )
    ):
        raise ValueError("invalid Claude model metadata")
    cost = value.get("total_cost_usd")
    if cost is not None:
        try:
            valid_cost = type(cost) in (int, float) and math.isfinite(cost) and cost >= 0
        except OverflowError:
            valid_cost = False
        if not valid_cost:
            raise ValueError("invalid Claude reported cost estimate")
    reason = None
    if value.get("subtype") != "success" or value.get("is_error") is not False:
        reason = "claude_reported_failure"
    elif type(value.get("num_turns")) is not int or value["num_turns"] < 1:
        reason = "claude_incomplete_turn"
    elif value.get("stop_reason") not in (None, "end_turn"):
        reason = "claude_nonterminal_stop"
    elif value.get("permission_denials", []) != [] or value.get("errors", []) != []:
        reason = "claude_denied_or_failed_operation"
    tools = supplied.get("server_tool_use", {})
    if not isinstance(tools, dict) or any(type(n) is not int or n != 0 for n in tools.values()):
        reason = "claude_forbidden_tool_usage"
    payload = value.get("structured_output")
    if not isinstance(payload, dict) or not payload:
        reason = reason or "claude_missing_structured_output"
    text = None
    if reason is None:
        try:
            text = canonical_json(payload)
        except (ValueError, TypeError, RecursionError):
            reason = "claude_invalid_structured_output"
    return ClaudeResult(
        text,
        tuple(sorted(models or {})),
        usage,
        float(cost) if cost is not None else None,
        reason,
    )


@dataclass(frozen=True)
class ClaudeExecution:
    process: ProcessResult
    parsed: ClaudeResult | None
    error: str | None
    job_sha256: str


def _decode(process: ProcessResult, job_sha256: str, model: str, budget: float) -> ClaudeExecution:
    try:
        parsed = parse_result(process.stdout)
    except (ValueError, TypeError, OverflowError):
        return ClaudeExecution(process, None, "invalid_claude_result", job_sha256)
    error = parsed.rejection
    if parsed.reported_models != (model,):
        error = error or "claude_model_identity_mismatch"
    if parsed.estimated_cost_usd is not None and parsed.estimated_cost_usd > budget:
        error = error or "claude_estimated_budget_overrun"
    if (
        process.status != "completed"
        or process.returncode != 0
        or not process.stopped
        or process.truncated
    ):
        error = error or "claude_process_incomplete"
    if error:
        parsed = replace(parsed, text=None)
    return ClaudeExecution(process, parsed, error, job_sha256)


def execute_claude_transport(
    inventory: ClaudeInventory,
    *,
    model: str,
    schema: Path,
    helper: Path,
    helper_sha256: str,
    directory: Path,
    workspace: Path,
    home: Path,
    nonce: str,
    prompt: bytes,
    timeout_seconds: float,
    max_output_bytes: int,
    max_budget_usd: float,
    on_launch: Callable[[dict], None],
    wrap_command: Callable[[tuple[str, ...]], tuple[str, ...]],
    cancelled: Callable[[], bool] = lambda: False,
) -> ClaudeExecution:
    """Caller-owned primitive with an explicit OS wrapper and non-secret helper.

    The helper is trusted executable code, outside the worker workspace, not a
    credential file. Its code must contain no secret. Authentication material is
    supplied only inside that helper's admitted private scope. The caller must
    reserve this invocation before calling and retain the returned job digest.
    This primitive is deliberately not a production Host or scheduler entrypoint.
    """
    executable = Path(inventory.executable)
    if (
        inventory.version != SUPPORTED_VERSION
        or inventory.supported_flags != REQUIRED_FLAGS
        or _hash(executable, 512 * 1024 * 1024) != inventory.sha256
    ):
        raise ValueError("Claude executable changed or profile is unsupported")
    workspace, home = checked_directory(workspace), checked_directory(home)
    helper = confined_file(checked_directory(helper.parent), helper.name)
    if helper.is_relative_to(workspace.resolve()) or _hash(helper, 1048576) != helper_sha256:
        raise ValueError("Claude helper is unpinned or inside the worker workspace")
    if type(model) is not str or not re.fullmatch(r"claude-[A-Za-z0-9._-]{1,128}", model):
        raise ValueError("Claude requires a pinned model name, not an alias or flags")
    if (
        type(max_budget_usd) not in (float, int)
        or not math.isfinite(max_budget_usd)
        or max_budget_usd <= 0
    ):
        raise ValueError("Claude API budget must be positive finite USD")
    schema = confined_file(schema.parent, schema.name)
    if schema.stat().st_size > 16384:
        raise ValueError("Claude output schema exceeds bound")
    document = unique_json(schema.read_text())
    if not isinstance(document, dict) or document.get("type") != "object":
        raise ValueError("Claude needs an object output schema")
    # Pin the non-secret helper code inside the persisted command. The helper's
    # output goes to Claude's private authentication pipe, never the job environment.
    verifier = """import hashlib,os,stat,sys
p,expected=sys.argv[1:]
fd=os.open(p,os.O_RDONLY|getattr(os,'O_NOFOLLOW',0))
with os.fdopen(fd,'rb') as f:
    meta=os.fstat(f.fileno())
    if not stat.S_ISREG(meta.st_mode) or not 0<meta.st_size<=1048576:
        sys.exit(2)
    actual=hashlib.sha256(f.read(1048577)).hexdigest()
if actual!=expected:
    sys.exit(2)
os.execv(p,[p])
"""
    helper_command = shlex.join(
        (
            str(Path(sys.executable).resolve()),
            "-I",
            "-S",
            "-c",
            verifier,
            str(helper),
            helper_sha256,
        )
    )
    settings = canonical_json({"apiKeyHelper": helper_command, "disableAllHooks": True})
    command = (
        str(executable),
        "--print",
        "--bare",
        "--input-format",
        "text",
        "--output-format",
        "json",
        "--json-schema",
        canonical_json(document),
        "--model",
        model,
        "--tools=",
        "--disable-slash-commands",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--setting-sources=",
        "--settings",
        settings,
        "--no-session-persistence",
        "--permission-mode",
        "dontAsk",
        "--max-budget-usd",
        str(float(max_budget_usd)),
    )
    wrapped = wrap_command(command)
    if not isinstance(wrapped, tuple) or wrapped[-len(command) :] != command:
        raise ValueError("Claude boundary wrapper changed the bound command")
    process = supervise_process(
        wrapped,
        directory=directory,
        cwd=workspace,
        environment={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": str(home)},
        nonce=nonce,
        stdin=prompt,
        timeout_seconds=timeout_seconds,
        max_output_bytes=max_output_bytes,
        on_launch=on_launch,
        cancelled=cancelled,
        parent_watchdog=True,
    )
    return _decode(process, _hash(directory / "job.json", 1048576), model, max_budget_usd)


def recover_claude_transport(
    directory: Path,
    *,
    nonce: str,
    job_sha256: str,
    model: str,
    max_output_bytes: int,
) -> ClaudeExecution:
    """Read a completed original process only; never inspect a credential or relaunch.

    job_sha256 must come from the caller's immutable original binding. Reading an
    arbitrary changed job and using its new hash is not compatible recovery.
    """
    if (
        not re.fullmatch(r"[0-9a-f]{64}", job_sha256)
        or _hash(directory / "job.json", 1048576) != job_sha256
    ):
        raise ValueError("Claude recovery job differs from original binding")
    job = unique_json((directory / "job.json").read_text())
    command = job.get("command") if isinstance(job, dict) else None
    if (
        not isinstance(command, list)
        or command.count("--model") != 1
        or command.count("--max-budget-usd") != 1
    ):
        raise ValueError("Claude recovery command is incompatible")
    try:
        original_model = command[command.index("--model") + 1]
        budget = float(command[command.index("--max-budget-usd") + 1])
    except (IndexError, ValueError, TypeError):
        raise ValueError("Claude recovery command is incompatible") from None
    if original_model != model or not math.isfinite(budget) or budget <= 0:
        raise ValueError("Claude recovery model or budget changed")
    process = recover_completed_process(directory, nonce=nonce, max_output_bytes=max_output_bytes)
    return _decode(process, job_sha256, model, budget)
