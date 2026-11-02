"""Exercise the version 2 transport with installed Codex and authored responses.

No real authentication or provider connection is used. This is offline
conformance evidence, not production host or scientific qualification.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import threading
import time
import uuid

from autoengineering.agents.hosts.base import InvocationContext
from autoengineering.agents.hosts.command_upstream import (
    CommandUpstream,
    inspect_command_stop,
    recover_command_upstream,
)
from autoengineering.agents.hosts.codex_brokered import (
    WrappedCommand,
    capture_endpoint_stop,
    execute_brokered_codex,
    inspect_brokered_codex,
    recover_brokered_transport,
)
from autoengineering.agents.hosts.native_policy import render_native_policy
from autoengineering.campaign.serialization import canonical_json
from autoengineering.agents.process import read_completion, recover_watchdog_stop
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.probe_external_boundary import external_policy
from examples.agent_campaign.probe_external_codex import (
    OFFLINE_MODEL,
    OFFLINE_PROMPT,
    OFFLINE_SCHEMA,
)
from examples.agent_campaign.probe_external_codex import response_stream
from autoengineering.agents.hosts.model_catalog import read_model_catalog


def snapshot(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def exercise(
    output: Path,
    *,
    scenario: str = "text",
    process_upstream: bool = False,
    owned_native: bool = False,
    subscription_fixture: bool = False,
    executable: Path | None = None,
    strict_native_policy: bool = False,
    model: str = OFFLINE_MODEL,
    model_catalog: bytes | None = None,
):
    if sys.platform != "darwin" or scenario not in {
        "text",
        "tool",
        "lost_ack",
        "timeout",
        "cancel",
    }:
        raise ValueError("unsupported brokered fixture platform or scenario")
    if subscription_fixture and not (owned_native and process_upstream):
        raise ValueError("subscription fixture requires both owned profiles")
    if strict_native_policy and not owned_native:
        raise ValueError("strict native policy requires owned native supervision")
    if scenario == "cancel" and not subscription_fixture:
        raise ValueError("in-flight cancellation requires the authored subscription fixture")
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("brokered fixture requires a fresh output directory")
    explicit_executable = executable is not None
    executable = executable if explicit_executable else shutil.which("codex")
    if executable is None:
        raise ValueError("installed Codex executable is unavailable")
    inventory = inspect_brokered_codex(Path(executable))
    requirements = Path("/etc/codex/requirements.toml").resolve()
    if requirements.exists() or requirements.is_symlink():
        raise ValueError("fixture requires absent system requirements")
    output.mkdir(mode=0o700)
    for name in ("workspace", "home"):
        (output / name).mkdir(mode=0o700)
    workspace, home = output / "workspace", output / "home"
    schema = workspace / "schema.json"
    durable_write(schema, canonical_json(OFFLINE_SCHEMA).encode())
    durable_write(output / "fixture-source.py", Path(__file__).read_bytes())
    release = threading.Event()
    cancellation = threading.Event()
    calls = []
    process_callback = None
    subscription = None
    upstream_root = output / "upstream-process"
    subscription_stopped_before_release = False

    def upstream(raw):
        calls.append(hashlib.sha256(raw).hexdigest())
        durable_write(output / "upstream-request.bin", raw)
        if process_callback is not None:
            return process_callback(raw)
        if scenario == "timeout":
            if not release.wait(timeout=5):
                raise TimeoutError("authored response release expired")
        return response_stream(
            model=model, tool_command="touch forbidden-marker" if scenario == "tool" else None
        )

    def wrap(command, endpoint):
        policy = (
            render_native_policy(workspace, home, Path(inventory.executable), endpoint.port)
            if strict_native_policy
            else external_policy(workspace, home, Path(inventory.executable))
            + (
                '(allow user-preference-read (preference-domain "com.openai.codex"))\n'
                '(allow mach-lookup (global-name "com.apple.cfprefsd.agent") '
                '(global-name "com.apple.cfprefsd.daemon") (local-name "com.apple.cfprefsd.agent"))\n'
                '(allow ipc-posix-shm-read* (ipc-posix-name-prefix "apple.cfprefs."))\n'
                f'(allow network-outbound (remote ip "localhost:{endpoint.port}"))\n'
                f'(allow file-read* (literal "/etc") (literal {json.dumps(str(requirements))}))\n'
                "(allow file-read-metadata "
                + " ".join(f"(literal {json.dumps(str(p))})" for p in requirements.parents)
                + ")\n"
            )
        )
        path = output / "transport/external.sb"
        durable_write(path, policy.encode())
        return WrappedCommand(("/usr/bin/sandbox-exec", "-f", str(path), *command), path)

    def fault(stage):
        if scenario == "lost_ack" and stage == "before_outcome_commit":
            raise OSError("authored final acknowledgment loss")

    context = InvocationContext(
        "offline-brokered",
        uuid.uuid4().hex,
        output / "transport",
        (1.5 if subscription_fixture else 0.5) if scenario == "timeout" else 15,
        65536,
        lambda owner: durable_write(output / "native-owner.json", canonical_json(owner).encode()),
        cancellation.is_set,
    )
    if process_upstream:
        source = output / "authored-upstream.py"
        payload = output / "authored-response.bin"
        durable_write(
            payload,
            response_stream(
                model=model, tool_command="touch forbidden-marker" if scenario == "tool" else None
            ),
        )
        durable_write(
            source,
            (
                "from pathlib import Path\nimport sys,time\n"
                + ("time.sleep(20)\n" if scenario == "timeout" else "")
                + "Path(sys.argv[2]).write_bytes(Path(sys.argv[3]).read_bytes())\n"
            ).encode(),
        )
        process_callback = CommandUpstream(
            output / "upstream-process",
            command=(
                sys.executable,
                "-I",
                "-S",
                str(source),
                "{request}",
                "{response}",
                str(payload),
            ),
            source_files=(source, payload),
            deadline_monotonic=time.monotonic() + context.timeout_seconds,
            cancelled=context.cancelled,
        )
        if subscription_fixture:
            from examples.agent_campaign.subscription_fixture import AuthoredSubscriptionFixture

            subscription = AuthoredSubscriptionFixture(
                output,
                model=model,
                body=payload.read_bytes(),
                deadline=time.monotonic() + context.timeout_seconds,
                delay_response=scenario in {"timeout", "cancel"},
                cancelled=context.cancelled,
                on_request=cancellation.set if scenario == "cancel" else lambda: None,
            )
            process_callback = subscription
            upstream_root = subscription.attempt
    print(f"Checking brokered Codex {scenario}", flush=True)
    execution, lost_ack = None, False
    try:
        try:
            execution = execute_brokered_codex(
                inventory,
                model_catalog=model_catalog,
                model=model,
                schema=schema,
                workspace=workspace,
                home=home,
                prompt=OFFLINE_PROMPT.encode(),
                context=context,
                upstream=upstream,
                boundary_identity=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                wrap_command=wrap,
                fault=fault,
                owned_native=owned_native,
            )
        except OSError:
            if scenario != "lost_ack":
                raise
            lost_ack = True
            execution = recover_brokered_transport(output / "transport")
        pending_status = execution.host_result.status
    finally:
        release.set()
        if subscription is not None:
            subscription_stopped_before_release = subscription.public_audit()["upstream_stopped"]
            subscription.close()
    if scenario == "timeout":
        if execution.endpoint is not None:
            capture_endpoint_stop(execution.root, execution.endpoint, wait_seconds=2)
        execution = recover_brokered_transport(output / "transport")
    before = snapshot(execution.root)
    recovered = recover_brokered_transport(execution.root)
    unchanged = before == snapshot(execution.root)
    upstream_receipt = None
    upstream_stop_proof = None
    native_watchdog = recover_watchdog_stop(output / "transport/client") if owned_native else None
    if process_upstream:
        upstream_receipt = read_completion(upstream_root / "process")
        upstream_stop_proof = inspect_command_stop(upstream_root)
        recover_watchdog_stop(upstream_root / "process")
        if scenario not in {"timeout", "cancel"}:
            before_upstream = snapshot(upstream_root)
            assert recover_command_upstream(upstream_root) == payload.read_bytes()
            unchanged = unchanged and before_upstream == snapshot(upstream_root)
    expected = (
        "host_failure"
        if scenario == "tool"
        else "timeout"
        if scenario == "timeout"
        else "cancelled"
        if scenario == "cancel"
        else "completed"
    )
    result = recovered.host_result
    subscription_audit = None
    if subscription is not None:
        from examples.agent_campaign.subscription_fixture import (
            TOKEN,
            ACCOUNT,
            REFRESH_TOKEN,
            ID_TOKEN,
        )

        credential_safe = all(
            all(
                value.encode() not in path.read_bytes()
                for value in (TOKEN, ACCOUNT, REFRESH_TOKEN, ID_TOKEN)
            )
            for tree in (execution.root, home, workspace)
            for path in tree.rglob("*")
            if path.is_file()
        )
        subscription_audit = {
            **subscription.public_audit(),
            "upstream_stopped_before_server_release": subscription_stopped_before_release,
            "credentials_absent_from_client": credential_safe,
        }
    passed = (
        result.status == expected
        and result.stop_verified
        and len(calls) == 1
        and unchanged
        and (scenario != "lost_ack" or lost_ack)
        and (scenario != "cancel" or cancellation.is_set())
        and (
            scenario != "timeout" or process_upstream or pending_status == "reconciliation_required"
        )
        and (upstream_receipt is None or upstream_stop_proof["state"] == "verified_stopped")
        and (native_watchdog is None or native_watchdog["stopped"])
        and (
            subscription_audit is None
            or (
                subscription_audit["authored_http_requests"] == 1
                and subscription_audit["all_auth_valid"]
                and subscription_audit["upstream_stopped_before_server_release"]
                and subscription_audit["credentials_absent_from_client"]
                and subscription_audit["fixture_server_thread_stopped"]
                and subscription_audit["source_unchanged"]
                and subscription_audit["refresh_and_id_excluded_from_lease"]
            )
        )
        and (scenario != "tool" or recovered.exchange_result.reason == "forbidden_response_item")
    )
    receipt = {
        "schema_version": "1.0",
        "status": "passed" if passed else "failed",
        "scenario": scenario,
        "fixture_timeout_seconds": context.timeout_seconds,
        "upstream_process": process_upstream,
        "owned_native": owned_native,
        "strict_native_policy": strict_native_policy,
        "executable_selection": "explicit" if explicit_executable else "PATH",
        "subscription_fixture": subscription_audit,
        "native_watchdog_stopped": native_watchdog["stopped"] if native_watchdog else None,
        "upstream_process_status": upstream_receipt["status"] if upstream_receipt else None,
        "upstream_process_stopped": upstream_stop_proof["state"] == "verified_stopped"
        if upstream_stop_proof
        else None,
        "original_upstream_process_stopped": upstream_receipt["stopped"]
        if upstream_receipt
        else None,
        "upstream_stop_proof": upstream_stop_proof,
        "host_qualified": False,
        "real_credentials_used": False,
        "provider_calls": 0,
        "client_invocations": 1,
        "authored_upstream_callbacks": len(calls),
        "requested_catalog_model": model,
        "host_status": result.status,
        "pending_status": pending_status,
        "reported_by_authored_response": result.resolved_model,
        "authored_usage": dict(result.usage),
        "endpoint_stop": asdict(recovered.endpoint_stop),
        "native_status": recovered.native.status,
        "native_stopped": recovered.native.stopped,
        "lost_final_acknowledgment": lost_ack,
        "cancelled_after_authored_request": cancellation.is_set(),
        "replay_unchanged": unchanged,
        "inventory": asdict(inventory),
        "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    print(f"Brokered transport: {receipt['status']} ({result.status})", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--scenario", choices=("text", "tool", "lost_ack", "timeout", "cancel"), default="text"
    )
    parser.add_argument("--process-upstream", action="store_true")
    parser.add_argument("--owned-native", action="store_true")
    parser.add_argument("--subscription-fixture", action="store_true")
    parser.add_argument("--executable", type=Path)
    parser.add_argument("--strict-native-policy", action="store_true")
    parser.add_argument("--model", default=OFFLINE_MODEL)
    parser.add_argument("--model-catalog", type=Path)
    args = parser.parse_args()
    return (
        0
        if exercise(
            args.output,
            scenario=args.scenario,
            process_upstream=args.process_upstream,
            owned_native=args.owned_native,
            subscription_fixture=args.subscription_fixture,
            executable=args.executable,
            strict_native_policy=args.strict_native_policy,
            model=args.model,
            model_catalog=None
            if args.model_catalog is None
            else read_model_catalog(args.model_catalog, args.model),
        )["status"]
        == "passed"
        else 4
    )


if __name__ == "__main__":
    raise SystemExit(main())
