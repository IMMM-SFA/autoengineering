"""Offline four-role journal fixture using installed Codex and authored replies.

Qualification is stubbed unless an explicit pinned native profile is supplied.
Replies remain authored. This is not a real model run or independent science pilot.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
from dataclasses import replace
import hashlib
from pathlib import Path
import shutil
from unittest.mock import patch

from autoengineering.agents.broker import CampaignBroker
from autoengineering.agents.hosts import brokered_host as adapter
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
from autoengineering.agents.hosts.native_profile import (
    VerifiedNativeProfile,
    native_runtime,
    verify_native_profile,
)
from autoengineering.agents.hosts.scripted import supplied_reply
from autoengineering.agents.identity import host_source_identity
from autoengineering.agents.records import HostSelection, TaskAssignment
from autoengineering.agents.report import evidence_report
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL, response_stream
from examples.agent_campaign.run import prepare


def authored_stream(text):
    def replace_text(value):
        if isinstance(value, dict):
            return {key: replace_text(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace_text(item) for item in value]
        return text if value == '{"ok":true}' else value

    return (
        "\n".join(
            "data: " + canonical_json(replace_text(unique_json(line[6:])))
            if line.startswith("data: ")
            else line
            for line in response_stream().decode().split("\n")
        )
    ).encode()


def snapshot(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def exercise(
    output,
    *,
    executable: Path | None = None,
    qualification_root: Path | None = None,
    qualification_digest: str | None = None,
):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists():
        raise ValueError("scheduler fixture requires a fresh directory")
    if (qualification_root is None) != (qualification_digest is None):
        raise ValueError("qualification root and digest must be supplied together")
    explicit_executable = executable is not None
    executable = executable if explicit_executable else shutil.which("codex")
    if executable is None:
        raise ValueError("installed Codex is unavailable")
    inventory = inspect_brokered_codex(Path(executable))
    qualified = qualification_root is not None
    if qualified:
        profile = verify_native_profile(qualification_root, expected_digest=qualification_digest)
        if profile.inventory != inventory or profile.model != OFFLINE_MODEL:
            raise ValueError("explicit executable/model differs from pinned qualification")
    else:
        qualification_root, qualification_digest = output, "0" * 64
        profile = VerifiedNativeProfile(
            output, "0" * 64, inventory, OFFLINE_MODEL, 30, 65536, 65536, digest(native_runtime())
        )
    controller, spec = prepare(output)
    spec = replace(
        spec,
        host=HostSelection("codex", "subscription", OFFLINE_MODEL, "2.1", qualification_digest),
    )
    store = WorkerStore.create(output / "brokered-worker", spec)
    requests = []
    with (
        nullcontext()
        if qualified
        else patch.object(adapter, "verify_native_profile", return_value=profile)
    ):
        host = adapter.BrokeredCodexHost(
            qualification_root=qualification_root,
            qualification_digest=qualification_digest,
            credential_path=output / "no-real-credential",
            lease_id="offline-only",
            model=OFFLINE_MODEL,
        )

        def upstream(root, workspace, home, deadline, cancelled):
            def call(raw):
                requests.append(hashlib.sha256(raw).hexdigest())
                wire_prompt = unique_json(raw.decode())["input"][0]["content"][0]["text"]
                context = unique_json(wire_prompt[wire_prompt.index('{"approved_evidence"') :])
                task = TaskAssignment.from_dict(context["task"])
                reply = supplied_reply(task, wire_prompt, context["invocation_id"])
                return authored_stream(canonical_json({"handoff_json": reply.raw_output}))

            return call

        with patch.object(host, "_upstream", side_effect=upstream):
            broker = CampaignBroker(controller, SerialScheduler(store, host))
            print("Checking four-role brokered scheduler with authored replies", flush=True)
            broker.advance()
            report = evidence_report(store)
            before = snapshot(output)
            broker.advance()
            replay_unchanged = before == snapshot(output)
    invocations = store.replay().invocations
    roles = {value.role for value in store.replay().tasks.values()}
    passed = (
        report["status"] == "completed"
        and roles == {"orchestrator", "investigator", "implementer", "reviewer"}
        and len(requests) == len(invocations) == 7
        and replay_unchanged
    )
    receipt = {
        "schema_version": "1.0",
        "status": "passed" if passed else "failed",
        "host_qualified": qualified,
        "qualification_stubbed": not qualified,
        "qualification_digest": qualification_digest if qualified else None,
        "qualification_root": str(qualification_root) if qualified else None,
        "live_conformance": "not_attempted",
        "real_credentials_used": False,
        "provider_calls": 0,
        "native_clients": len(invocations),
        "authored_callbacks": len(requests),
        "replay_unchanged": replay_unchanged,
        "roles": sorted(roles),
        "synthetic_scientific_attempts": report["physical_work"]["attempts"],
        "source_identity": host_source_identity(),
        "inventory_sha256": inventory.sha256,
        "native_executable": inventory.executable,
        "native_version": inventory.version,
        "executable_selection": "explicit" if explicit_executable else "PATH",
        "native_requested_model": OFFLINE_MODEL,
        "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "production_dispatch_enabled": False,
        "campaign_outcome": report["campaign_outcome"],
    }
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    print(f"Brokered scheduler: {receipt['status']}", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--executable", type=Path, help="Explicit native CLI candidate, without changing PATH"
    )
    parser.add_argument("--qualification-root", type=Path)
    parser.add_argument("--qualification-digest")
    args = parser.parse_args()
    return (
        0
        if exercise(
            args.output,
            executable=args.executable,
            qualification_root=args.qualification_root,
            qualification_digest=args.qualification_digest,
        )["status"]
        == "passed"
        else 4
    )


if __name__ == "__main__":
    raise SystemExit(main())
