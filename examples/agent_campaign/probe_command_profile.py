"""Offline macOS command-filesystem probe using the installed Codex sandbox.

This does not qualify a host, service egress, real authentication or a model.
All CLI process-tree networking is denied externally. Only synthetic canaries
and this public probe source are read. No user configuration is changed.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sys
import time
import uuid

from autoengineering.agents.hosts.codex import inspect_codex
from autoengineering.agents.process import supervise_process
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write

OUTER_POLICY = "(version 1)\n(allow default)\n(deny network*)\n"


def command_passed(result, command, *, readable, public, secret):
    expected_diagnostic = f"{Path(command[0]).name}: {command[-1]}: ".encode()
    denied = (
        result.returncode == 1
        and result.stderr.startswith(expected_diagnostic)
        and any(
            message in result.stderr
            for message in (b"Operation not permitted", b"Permission denied")
        )
    )
    return (
        result.stopped
        and not result.truncated
        and (
            result.returncode == 0 and result.stdout == public
            if readable
            else denied
            and secret not in result.stdout + result.stderr
            and public not in result.stdout + result.stderr
        )
    )


def exercise(output: Path):
    if sys.platform != "darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        raise ValueError("command profile probe currently requires macOS")
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("command profile probe requires a fresh output directory")
    executable = shutil.which("codex")
    if executable is None:
        raise ValueError("installed Codex executable is unavailable")
    inventory = inspect_codex(Path(executable))
    output.mkdir(mode=0o700)
    for name in ("workspace", "private", "home", "receipts"):
        (output / name).mkdir(mode=0o700)
    workspace, private, home = (output / name for name in ("workspace", "private", "home"))
    public = f"public-{uuid.uuid4().hex}\n".encode()
    secret = f"synthetic-private-{uuid.uuid4().hex}\n".encode()
    durable_write(workspace / "brief.txt", public)
    durable_write(private / "labels.txt", secret)
    durable_write(home / "synthetic-credential.txt", secret)
    (workspace / "linked-private.txt").symlink_to(private / "labels.txt")
    # Exact paths and no legacy sandbox_mode setting. The network rule is
    # intentionally supplemented by an outer deny for *all* CLI processes.
    config = (
        'default_permissions = "part3-host-probe"\n'
        "[permissions.part3-host-probe.filesystem]\n"
        '":root" = "deny"\n'
        '":minimal" = "read"\n'
        '":tmpdir" = "deny"\n'
        '":slash_tmp" = "deny"\n'
        f'{json.dumps(str(workspace))} = "read"\n'
        "[permissions.part3-host-probe.network]\n"
        "enabled = false\n"
    )
    durable_write(home / "config.toml", config.encode())
    durable_write(output / "outer.sb", OUTER_POLICY.encode())
    probe_raw = Path(__file__).read_bytes()
    durable_write(output / "probe-source.py", probe_raw)
    manifest = {
        "schema_version": "1.0",
        "purpose": "native-command-filesystem-probe",
        "host_qualified": False,
        "network_policy_qualified": False,
        "platform": platform.platform(),
        "inventory": asdict(inventory),
        "maximum_commands": 6,
        "seconds_per_command": 5,
        "maximum_elapsed_seconds": 45,
        "provider_calls": 0,
        "real_credentials_used": False,
        "profile_sha256": hashlib.sha256(config.encode()).hexdigest(),
        "outer_policy_sha256": hashlib.sha256(OUTER_POLICY.encode()).hexdigest(),
        "probe_sha256": hashlib.sha256(probe_raw).hexdigest(),
    }
    durable_write(output / "manifest.json", canonical_json(manifest).encode())
    environment = {
        "HOME": str(home),
        "CODEX_HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "TMPDIR": str(private),
    }
    cases = (
        ("approved_brief", ("/bin/cat", str(workspace / "brief.txt")), True),
        ("private_labels", ("/bin/cat", str(private / "labels.txt")), False),
        ("credential_canary", ("/bin/cat", str(home / "synthetic-credential.txt")), False),
        ("checkout_source", ("/bin/cat", str(Path(__file__).resolve())), False),
        ("symlink_escape", ("/bin/cat", str(workspace / "linked-private.txt")), False),
        ("workspace_write", ("/usr/bin/touch", str(workspace / "forbidden-write")), False),
    )
    began, records = time.monotonic(), []
    for name, command, readable in cases:
        if records and not records[0]["passed"]:
            records.append(
                {"name": name, "passed": False, "reason": "approved_baseline_failed_not_attempted"}
            )
            continue
        print(f"Checking {name}", flush=True)
        args = (
            "/usr/bin/sandbox-exec",
            "-f",
            str(output / "outer.sb"),
            inventory.executable,
            "sandbox",
            "--permission-profile",
            "part3-host-probe",
            "--include-managed-config",
            "--",
            *command,
        )
        result = supervise_process(
            args,
            directory=output / "receipts" / name,
            cwd=workspace,
            environment=environment,
            nonce=uuid.uuid4().hex,
            stdin=b"",
            timeout_seconds=5,
            max_output_bytes=65536,
            on_launch=lambda identity, case_name=name: durable_write(
                output / "receipts" / f"{case_name}-owner.json", canonical_json(identity).encode()
            ),
        )
        bounded = not result.truncated
        # A setup/compile error must never count as a denied-read pass.
        passed = command_passed(result, command, readable=readable, public=public, secret=secret)
        record = {
            "name": name,
            "passed": passed,
            "returncode": result.returncode,
            "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
            "output_bounded": bounded,
            "stopped": result.stopped,
            "process_status": result.status,
        }
        records.append(record)
        if not result.stopped:
            break
    elapsed = time.monotonic() - began
    passed = (
        len(records) == 6
        and all(record["passed"] for record in records)
        and elapsed <= 45
        and not (workspace / "forbidden-write").exists()
    )
    receipt = {
        **manifest,
        "status": "command_profile_passed" if passed else "failed",
        "elapsed_seconds": elapsed,
        "checks": records,
        "remaining_gates": [
            "client_service_egress",
            "tool_surfaces",
            "credential_separation",
            "host_lifecycle_qualification",
            "authorized_live_conformance",
        ],
    }
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    print(f"Command filesystem probe: {receipt['status']} in {elapsed:.2f} seconds", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    return 0 if exercise(args.output)["status"] == "command_profile_passed" else 4


if __name__ == "__main__":
    raise SystemExit(main())
