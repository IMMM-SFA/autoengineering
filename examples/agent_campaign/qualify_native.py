"""Build an offline native boundary profile from actual local probes.

This runs no real model, opens no existing auth cache and grants no live-call
authority. The exact executable must be supplied. It needs existing Apple
command line tools, and never changes the user's CLI selection or installation.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
from pathlib import Path
import socket
import time
import uuid

from autoengineering.agents.hosts.base import InvocationContext
from autoengineering.agents.hosts.codex_brokered import (
    WrappedCommand,
    execute_brokered_codex,
    inspect_brokered_codex,
    recover_brokered_transport,
)
from autoengineering.agents.hosts.native_canaries import (
    probe_native_policy,
    recover_native_policy_probe,
)
from autoengineering.agents.hosts.native_policy import render_native_policy
from autoengineering.agents.hosts.native_profile import (
    INDEX_VERSION,
    OBSERVATIONS,
    VERSION,
    boundary_source_identity,
    native_runtime,
    verify_native_profile,
)
from autoengineering.agents.hosts.model_catalog import read_model_catalog, validate_model_catalog
from autoengineering.agents.hosts.text_endpoint import TextEndpoint
from autoengineering.agents.hosts.text_exchange import TextExchange
from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.process import recover_watchdog_stop
from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.check_brokered_codex_fixture import exercise as native_case
from examples.agent_campaign.check_owned_codex_death_fixture import exercise as death_case
from examples.agent_campaign.probe_external_codex import (
    OFFLINE_MODEL,
    OFFLINE_SCHEMA,
    response_stream,
)
from examples.agent_campaign.subscription_fixture import TOKEN, ACCOUNT, REFRESH_TOKEN, ID_TOKEN

LIMITS = {"max_worker_seconds": 30, "max_output_bytes": 65536, "max_workspace_bytes": 65536}


def record(root, name):
    path = confined_file(root, name)
    if path.stat().st_size > 65536:
        raise ValueError("qualification input exceeds size limit")
    return unique_json(path.read_text())


def snapshot(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def output_bound(root, inventory, model=OFFLINE_MODEL, model_catalog=None):
    root.mkdir(mode=0o700)
    for name in ("workspace", "home"):
        (root / name).mkdir(mode=0o700)
    schema = root / "workspace/schema.json"
    durable_write(schema, canonical_json(OFFLINE_SCHEMA).encode())
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream(model=model)

    def wrap(command, endpoint):
        policy = root / "transport/policy.sb"
        durable_write(
            policy,
            render_native_policy(
                root / "workspace", root / "home", Path(inventory.executable), endpoint.port
            ).encode(),
        )
        return WrappedCommand(("/usr/bin/sandbox-exec", "-f", str(policy), *command), policy)

    execution = execute_brokered_codex(
        inventory,
        model_catalog=model_catalog,
        model=model,
        schema=schema,
        workspace=root / "workspace",
        home=root / "home",
        prompt=b"Return the requested JSON only.",
        context=InvocationContext(
            "qualification-output",
            uuid.uuid4().hex,
            root / "transport",
            15,
            128,
            lambda _: None,
            lambda: False,
        ),
        upstream=upstream,
        boundary_identity=boundary_source_identity(),
        wrap_command=wrap,
        owned_native=True,
    )
    before = snapshot(root)
    recovered = recover_brokered_transport(execution.root)
    stopped = recover_watchdog_stop(execution.root / "client")
    value = {
        "output_limit_enforced": recovered.native.status == "output_limit"
        and recovered.native.truncated
        and len(recovered.native.stdout) + len(recovered.native.stderr) <= 128,
        "stopped": recovered.host_result.stop_verified and stopped["stopped"],
        "replay_unchanged": before == snapshot(root),
        "authored_callbacks": len(calls),
        "provider_calls": 0,
    }
    durable_write(root / "receipt.json", canonical_json(value).encode())
    return value


def input_bound(root, inventory, model=OFFLINE_MODEL, model_catalog=None):
    root.mkdir(mode=0o700)
    for name in ("workspace", "home"):
        (root / name).mkdir(mode=0o700)
    durable_write(root / "workspace/schema.json", b" " * (LIMITS["max_workspace_bytes"] + 1))
    launched = []
    try:
        execute_brokered_codex(
            inventory,
            model_catalog=model_catalog,
            model=model,
            schema=root / "workspace/schema.json",
            workspace=root / "workspace",
            home=root / "home",
            prompt=b"bounded input probe",
            context=InvocationContext(
                "qualification-input",
                uuid.uuid4().hex,
                root / "transport",
                1,
                65536,
                launched.append,
                lambda: False,
            ),
            upstream=lambda _: (_ for _ in ()).throw(AssertionError("oversized input dispatched")),
            boundary_identity=boundary_source_identity(),
            wrap_command=lambda *_: (_ for _ in ()).throw(
                AssertionError("oversized input wrapped")
            ),
            owned_native=True,
        )
    except ValueError as exc:
        rejected = str(exc) == "output schema exceeds size limit"
    else:
        rejected = False
    value = {
        "oversized_schema_rejected": rejected,
        "native_starts": len(launched),
        "transport_absent": not (root / "transport").exists(),
    }
    durable_write(root / "receipt.json", canonical_json(value).encode())
    return value


def read_bound(root, model=OFFLINE_MODEL):
    root.mkdir(mode=0o700)
    exchange = TextExchange.create(
        root / "exchange",
        invocation_id="qualification-read",
        requested_model=model,
        approved_prompt="read deadline probe",
        output_schema=OFFLINE_SCHEMA,
    )
    calls = []
    endpoint = TextEndpoint(
        exchange,
        lambda raw: calls.append(raw) or response_stream(model=model),
        directory=root / "endpoint",
        route_nonce="a" * 32,
        request_seconds=0.1,
    )
    payload = canonical_json(
        {
            "model": model,
            "stream": True,
            "input": [
                {
                    "role": "user",
                    "type": "message",
                    "content": [{"type": "input_text", "text": "read deadline probe"}],
                }
            ],
        }
    ).encode()
    try:
        with socket.create_connection(("127.0.0.1", endpoint.port), timeout=1) as connection:
            connection.sendall(
                f"POST /{'a' * 32}/v1/responses HTTP/1.1\r\nHost: 127.0.0.1:{endpoint.port}\r\nContent-Length: {len(payload)}\r\nConnection: close\r\n\r\n".encode()
            )
            for byte in payload[:12]:
                try:
                    connection.sendall(bytes((byte,)))
                except OSError:
                    break
                time.sleep(0.03)
            response = connection.recv(4096)
    finally:
        stopped = endpoint.close()
    events = [
        record(root / "endpoint/events", path.name)["event"]
        for path in sorted((root / "endpoint/events").glob("*.json"))
    ]
    value = {
        "read_deadline_enforced": "client_read_deadline" in events and b"408" in response,
        "upstream_calls": len(calls),
        "dispatch_absent": not (exchange.root / "dispatch.json").exists(),
        "stop": asdict(stopped),
    }
    durable_write(root / "receipt.json", canonical_json(value).encode())
    return value


def client_credentials_absent(case):
    used = 0
    secrets = tuple(secret.encode() for secret in (TOKEN, ACCOUNT, REFRESH_TOKEN, ID_TOKEN))
    overlap = max(map(len, secrets)) - 1
    for tree in (case / "home", case / "workspace", case / "transport"):
        for path in tree.rglob("*"):
            if not path.is_file():
                continue
            path = confined_file(tree, str(path.relative_to(tree)))
            used += path.stat().st_size
            if used > 16777216:
                raise ValueError("client scan exceeds qualification bound")
            tail = b""
            with path.open("rb") as stream:
                while chunk := stream.read(65536):
                    raw = tail + chunk
                    if any(secret in raw for secret in secrets):
                        return False
                    tail = raw[-overlap:]
    return True


def qualify(output, executable, *, model=OFFLINE_MODEL, model_catalog=None):
    output = Path(output).absolute()
    checked_directory(output.parent)
    inventory = inspect_brokered_codex(Path(executable))
    runtime, source = native_runtime(), host_source_identity()
    if runtime["platform"] != "darwin" or runtime["machine"] != "arm64":
        raise ValueError("native qualification supports only macOS ARM64")
    if model_catalog is not None:
        validate_model_catalog(model_catalog, model)
    output.mkdir(mode=0o700)
    if model_catalog is not None:
        durable_write(output / "model-catalog.json", model_catalog)
    (output / "artifacts").mkdir(mode=0o700)
    durable_write(output / "qualifier-source.py", Path(__file__).read_bytes())
    print("Checking native policy permissions", flush=True)
    canary = probe_native_policy(output / "permissions")
    canary_pin = hashlib.sha256((output / "permissions/receipt.json").read_bytes()).hexdigest()
    recover_native_policy_probe(output / "permissions", expected_digest=canary_pin)
    if canary["status"] != "passed":
        raise ValueError("native permission gate failed; evidence is retained")
    receipts, executions = {}, {}
    for scenario in ("text", "tool", "lost_ack", "timeout", "cancel"):
        print(f"Checking native {scenario}", flush=True)
        case = output / scenario
        receipts[scenario] = native_case(
            case,
            scenario=scenario,
            process_upstream=True,
            owned_native=True,
            subscription_fixture=True,
            executable=Path(inventory.executable),
            strict_native_policy=True,
            model=model,
            model_catalog=model_catalog,
        )
        execution = recover_brokered_transport(case / "transport")
        executions[scenario] = execution
        endpoint = record(case / "transport/endpoint", "endpoint.json")
        manifest = record(case / "transport", "transport.json")
        policy = read_bytes(
            case / "transport",
            ArtifactRef.from_dict(manifest["boundary_policy"]["artifact"]),
            max_bytes=65536,
        )
        if (
            receipts[scenario]["status"] != "passed"
            or manifest["inventory"] != unique_json(canonical_json(asdict(inventory)))
            or manifest["requested_model"] != model
            or policy
            != render_native_policy(
                case / "workspace", case / "home", Path(inventory.executable), endpoint["port"]
            ).encode()
        ):
            raise ValueError("native case differs from qualification scope")
    print("Checking native owner death and byte/time bounds", flush=True)
    death = death_case(
        output / "death",
        executable=Path(inventory.executable),
        strict_native_policy=True,
        model=model,
        model_catalog=None if model_catalog is None else output / "model-catalog.json",
    )
    for child in ("fixture/transport/client", "fixture/upstream-process/process"):
        recover_watchdog_stop(output / "death" / child)
    out, inp, read = (
        output_bound(output / "output-bound", inventory, model, model_catalog),
        input_bound(output / "input-bound", inventory, model, model_catalog),
        read_bound(output / "read-bound", model),
    )
    observations = {
        "preferences": {name: canary["observed"][name] for name in OBSERVATIONS["preferences"]},
        "filesystem": {
            "private_read_denied": canary["observed"]["private_read_denied"],
            "checkout_read_denied": canary["observed"]["checkout_read_denied"],
            "evaluator_read_denied": canary["observed"]["evaluator_read_denied"],
            "write_outside_denied": canary["observed"]["outside_write_denied"],
            "allowed_read_succeeded": canary["observed"]["allowed_read_succeeded"],
        },
        "symlinks": {
            "read_escape_denied": canary["observed"]["symlink_read_denied"],
            "write_escape_denied": canary["observed"]["symlink_write_denied"],
        },
        "network": {name: canary["observed"][name] for name in OBSERVATIONS["network"]},
        "tools": {
            "forbidden_response_rejected": executions["tool"].exchange_result.reason
            == "forbidden_response_item",
            "native_tool_executions": sum(
                1
                for line in executions["tool"].native.stdout.splitlines()
                if isinstance((event := unique_json(line.decode())), dict)
                and event.get("type") in {"item.started", "item.completed"}
                and event.get("item", {}).get("type") not in {"agent_message", "reasoning"}
            ),
        },
        "credentials": {
            "process_environment_unavailable_to_client": canary["observed"][
                "process_environment_read_denied"
            ],
            "cache_unavailable_to_client": canary["observed"]["cache_read_denied"],
            "lease_unavailable_to_client": canary["observed"]["lease_read_denied"],
            "no_secret_in_client_artifacts": all(
                client_credentials_absent(output / scenario) for scenario in receipts
            ),
        },
        "lifecycle": {
            "timeout_stopped": executions["timeout"].host_result.status == "timeout"
            and executions["timeout"].host_result.stop_verified,
            "cancel_stopped": executions["cancel"].host_result.status == "cancelled"
            and executions["cancel"].host_result.stop_verified,
            "parent_death_stopped": death["status"] == "passed"
            and all(item["group_absent"] and item["stopped"] for item in death["processes"]),
            "replay_no_relaunch": all(value["replay_unchanged"] for value in receipts.values())
            and out["replay_unchanged"],
            "missing_completion_not_success": death["recovery_refused_missing_completion"],
        },
        "bounds": {
            "output_limit_enforced": out["output_limit_enforced"] and out["stopped"],
            "read_deadline_enforced": read["read_deadline_enforced"]
            and read["upstream_calls"] == 0
            and read["dispatch_absent"]
            and all(
                read["stop"][name]
                for name in ("listener_closed", "handler_stopped", "upstream_callback_stopped")
            ),
            "workspace_limit_enforced": inp["oversized_schema_rejected"]
            and inp["native_starts"] == 0
            and inp["transport_absent"]
            and canary["observed"]["workspace_write_denied"],
        },
        "native": {
            "client_started": executions["text"].native.identity is not None,
            "text_roundtrip": executions["text"].host_result.status == "completed"
            and executions["text"].host_result.raw_output == '{"ok":true}',
            "client_stopped": executions["text"].host_result.stop_verified,
        },
    }
    if source != host_source_identity() or runtime != native_runtime():
        raise ValueError("qualification source/runtime changed during probes")
    bindings = {
        "source_identity": source,
        "runtime_identity": digest(runtime),
        "inventory_identity": digest(asdict(inventory)),
        "boundary_source_identity": boundary_source_identity(),
        "limits": LIMITS,
    }
    roots = [
        output / "permissions",
        output / "read-bound",
        output / "output-bound/transport",
        output / "input-bound/workspace",
        output / "death/fixture/transport",
        output / "death/fixture/upstream-process",
        *(output / scenario / "transport" for scenario in receipts),
        *(output / scenario / "subscription" for scenario in receipts),
        *(output / scenario / "fixture-source.py" for scenario in receipts),
        output / "death/fixture-source.py",
        output / "qualifier-source.py",
    ]
    files = {}
    for scope in roots:
        for path in [scope] if scope.is_file() else scope.rglob("*"):
            if (
                path.is_symlink()
                or not path.is_file()
                or path.is_relative_to(output / "permissions/private")
                or path.is_relative_to(output / "permissions/home")
            ):
                continue
            path = confined_file(output, str(path.relative_to(output)))
            if path.stat().st_size > 1048576:
                raise ValueError("raw qualification file exceeds limit")
            name = str(path.relative_to(output))
            files[name] = ArtifactRef(
                name,
                hashlib.sha256(path.read_bytes()).hexdigest(),
                path.stat().st_size,
                "application/octet-stream",
                "native-qualifier",
                {},
            )
    index = {
        "version": INDEX_VERSION,
        "bindings": bindings,
        "files": [ref.to_dict() for _, ref in sorted(files.items())],
        "total_bytes": sum(ref.size_bytes for ref in files.values()),
    }
    if not 0 < len(files) <= 1024 or index["total_bytes"] > 67108864:
        raise ValueError("raw qualification index exceeds limit")
    index_ref = replace(
        put_bytes(
            output,
            canonical_json(index).encode(),
            name="raw-evidence-index.json",
            media_type="application/json",
            producer="native-qualifier",
        ),
        metadata={"kind": INDEX_VERSION},
    )
    # Raw artifacts are bounded copies of measured records and reviewed probe
    # source, not synthetic assertions standing in for executed checks.
    evidence = [index_ref.to_dict()]
    for name in (
        "qualifier-source.py",
        "permissions/receipt.json",
        *(f"{scenario}/receipt.json" for scenario in receipts),
        "death/receipt.json",
        "output-bound/receipt.json",
        "input-bound/receipt.json",
        "read-bound/receipt.json",
    ):
        path = confined_file(output, name)
        if path.stat().st_size > 1048576:
            raise ValueError("qualification artifact exceeds limit")
        evidence.append(
            put_bytes(
                output,
                path.read_bytes(),
                name=path.name,
                media_type="application/octet-stream",
                producer="native-qualifier",
            ).to_dict()
        )
    checks = {}
    for name, expected in OBSERVATIONS.items():
        report = {
            "version": VERSION,
            "name": name,
            "status": "passed"
            if canonical_json(observations[name]) == canonical_json(expected)
            else "failed",
            "bindings": bindings,
            "observed": observations[name],
            "evidence": evidence,
        }
        checks[name] = put_bytes(
            output,
            canonical_json(report).encode(),
            name=name + ".json",
            media_type="application/json",
            producer="native-qualifier",
        ).to_dict()
    passed = all(
        canonical_json(observations[name]) == canonical_json(expected)
        for name, expected in OBSERVATIONS.items()
    )
    manifest = {
        "version": VERSION,
        "status": "qualified" if passed else "failed",
        "source_identity": source,
        "runtime": runtime,
        "boundary_source_identity": boundary_source_identity(),
        "inventory": asdict(inventory),
        "model": model,
        "limits": LIMITS,
        "checks": checks,
        "provider_calls": 0,
        "scientific_calls": 0,
    }
    if model_catalog is not None:
        manifest["model_catalog"] = put_bytes(
            output,
            model_catalog,
            name="model-catalog.json",
            media_type="application/json",
            producer="native-qualifier",
        ).to_dict()
    raw = canonical_json(manifest).encode()
    durable_write(output / "qualification.json", raw)
    pin = hashlib.sha256(raw).hexdigest()
    if passed:
        verify_native_profile(output, expected_digest=pin)
    durable_write(
        output / "summary.json",
        canonical_json(
            {
                "status": manifest["status"],
                "qualification_digest": pin,
                "provider_calls": 0,
                "real_credentials_used": False,
                "live_conformance": "not_attempted",
            }
        ).encode(),
    )
    print(f"Offline native boundary: {manifest['status']}; digest {pin}", flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--model", default=OFFLINE_MODEL)
    parser.add_argument("--model-catalog", type=Path)
    args = parser.parse_args()
    return (
        0
        if qualify(
            args.output,
            args.executable,
            model=args.model,
            model_catalog=None
            if args.model_catalog is None
            else read_model_catalog(args.model_catalog, args.model),
        )["status"]
        == "qualified"
        else 4
    )


if __name__ == "__main__":
    raise SystemExit(main())
