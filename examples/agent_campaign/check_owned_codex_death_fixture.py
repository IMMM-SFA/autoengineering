"""Kill an offline installed-CLI fixture supervisor during an authored request.

No provider or authentication is used. This records local process/socket death
and intentionally missing completion, not successful role or remote cancellation.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import socket
import subprocess
import sys
import time

from autoengineering.agents.hosts.codex_brokered import recover_brokered_transport
from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import recover_watchdog_stop
from autoengineering.campaign.execution import live_members
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write


def wait_for(path, parent=None, seconds=8):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            return unique_json(path.read_text())
        if parent is not None and parent.poll() is not None:
            raise ValueError("fixture supervisor ended before the death probe")
        time.sleep(0.005)
    raise ValueError("fixture observation deadline expired")


def exercise(
    output,
    *,
    executable: Path | None = None,
    strict_native_policy=False,
    model=None,
    model_catalog=None,
):
    root = Path(output).absolute()
    checked_directory(root.parent)
    root.mkdir(mode=0o700)
    durable_write(root / "fixture-source.py", Path(__file__).read_bytes())
    fixture = root / "fixture"
    print("Checking owned Codex supervisor death with an authored request", flush=True)
    extra = []
    if model is not None:
        extra.extend(("--model", model))
    if model_catalog is not None:
        extra.extend(("--model-catalog", str(model_catalog)))
    if executable is not None:
        extra.extend(("--executable", str(executable)))
    if strict_native_policy:
        extra.append("--strict-native-policy")
    with (root / "supervisor.log").open("xb") as log:
        parent = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "examples.agent_campaign.check_brokered_codex_fixture",
                "--output",
                str(fixture),
                "--scenario",
                "timeout",
                "--process-upstream",
                "--owned-native",
                *extra,
            ],
            stdout=log,
            stderr=log,
        )
        try:
            roots = [fixture / "transport/client", fixture / "upstream-process/process"]
            for process_root in roots:
                wait_for(process_root / "launch-gate.json", parent)
            endpoint = wait_for(fixture / "transport/endpoint/endpoint.json", parent)
            parent.kill()
            parent.wait(timeout=2)
            observations = []
            for process_root in roots:
                result = wait_for(process_root / "watchdog-result.json")
                identity = wait_for(process_root / "process.json")
                verified = recover_watchdog_stop(process_root)
                observations.append(
                    {
                        "process": str(process_root.relative_to(root)),
                        "reason": result["reason"],
                        "stopped": verified["stopped"],
                        "group_absent": not live_members(identity["pgid"]),
                        "completion_missing": not (process_root / "completion.json").exists(),
                    }
                )
            try:
                connection = socket.create_connection(
                    (endpoint["address"], endpoint["port"]), timeout=0.2
                )
            except OSError:
                listener_closed = True
            else:
                connection.close()
                listener_closed = False
            try:
                recover_brokered_transport(fixture / "transport")
            except ValueError:
                recovery_refused_missing_completion = True
            else:
                recovery_refused_missing_completion = False
            passed = (
                listener_closed
                and recovery_refused_missing_completion
                and all(
                    item["stopped"] and item["group_absent"] and item["completion_missing"]
                    for item in observations
                )
            )
            receipt = {
                "schema_version": "1.0",
                "status": "passed" if passed else "failed",
                "source_identity": host_source_identity(),
                "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "processes": observations,
                "listener_closed": listener_closed,
                "recovery_refused_missing_completion": recovery_refused_missing_completion,
                "client_invocations": 1,
                "authored_upstream_callbacks": 1,
                "provider_calls": 0,
                "real_credentials_used": False,
                "host_qualified": False,
                "strict_native_policy": strict_native_policy,
                "explicit_executable": str(executable) if executable is not None else None,
            }
            durable_write(root / "receipt.json", canonical_json(receipt).encode())
            print(f"Owned supervisor death: {receipt['status']}", flush=True)
            return receipt
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--strict-native-policy", action="store_true")
    args = parser.parse_args()
    return (
        0
        if exercise(
            args.output, executable=args.executable, strict_native_policy=args.strict_native_policy
        )["status"]
        == "passed"
        else 4
    )


if __name__ == "__main__":
    raise SystemExit(main())
