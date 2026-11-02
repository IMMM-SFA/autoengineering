"""Actual pinned native profile through CLI run/resume, with authored replies only.

This reads no real credential and makes no provider call. Only the upstream
callback is substituted. Native qualification, policy, CLI and journal are real.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from autoengineering.agents.hosts.brokered_host import BrokeredCodexHost
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
from autoengineering.agents.hosts.native_profile import verify_native_profile
from autoengineering.agents.hosts.scripted import supplied_reply
from autoengineering.agents.records import HostSelection, TaskAssignment
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.cli import cli
from examples.agent_campaign.check_brokered_scheduler_fixture import authored_stream, snapshot
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL
from examples.agent_campaign.run import prepare


def exercise(output, *, executable, qualification_root, qualification_digest):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists():
        raise ValueError("configured CLI fixture requires a fresh directory")
    inventory = inspect_brokered_codex(Path(executable))
    profile = verify_native_profile(qualification_root, expected_digest=qualification_digest)
    if inventory != profile.inventory or profile.model != OFFLINE_MODEL:
        raise ValueError("fixture executable/model differs from pinned native profile")
    _, spec = prepare(output)
    spec = replace(
        spec,
        host=HostSelection("codex", "subscription", OFFLINE_MODEL, "2.1", qualification_digest),
    )
    durable_write(output / "configured-run.json", spec.to_json().encode())
    config = output / "host.toml"
    # Metadata only. The callback below never starts a credential worker.
    durable_write(
        config,
        (
            'schema_version = "1.0"\n'
            f'qualification_root = "{Path(qualification_root).absolute()}"\n'
            f'qualification_digest = "{qualification_digest}"\n'
            f'credential_path = "{output / "no-real-credential"}"\n'
            'lease_id = "offline-cli-fixture"\n'
        ).encode(),
    )
    requests = []

    def upstream(self, root, workspace, home, deadline, cancelled):
        def call(raw):
            requests.append(hashlib.sha256(raw).hexdigest())
            prompt = unique_json(raw.decode())["input"][0]["content"][0]["text"]
            context = unique_json(prompt[prompt.index('{"approved_evidence"') :])
            task = TaskAssignment.from_dict(context["task"])
            reply = supplied_reply(task, prompt, context["invocation_id"])
            return authored_stream(canonical_json({"handoff_json": reply.raw_output}))

        return call

    common = ["--campaign", str(output / "campaign"), "--host-config", str(config)]
    runner = CliRunner()
    print("Checking actual pinned native boundary through CLI run/resume", flush=True)
    with patch.object(BrokeredCodexHost, "_upstream", new=upstream):
        validated = runner.invoke(
            cli, ["agents", "validate", str(output / "configured-run.json"), *common]
        )
        if validated.exit_code != 0 or requests:
            raise ValueError("configured CLI validation failed or dispatched a callback")
        result = runner.invoke(
            cli,
            [
                "agents",
                "run",
                str(output / "configured-run.json"),
                *common,
                "--workdir",
                str(output / "worker"),
            ],
        )
        durable_write(output / "run-output.json", result.stdout.encode())
        if result.exit_code != 0:
            raise ValueError("configured CLI run failed; output retained")
        report = unique_json(result.stdout)
        before = snapshot(output)
        resumed = runner.invoke(cli, ["agents", "resume", str(output / "worker"), *common])
        unchanged = before == snapshot(output)
        if resumed.exit_code != 0:
            raise ValueError("configured CLI replay failed")
    projection = WorkerStore(output / "worker").replay()
    passed = (
        report["status"] == "completed"
        and len(requests) == len(projection.invocations) == 7
        and report["physical_work"]["attempts"] == 2
        and unchanged
        and projection.events[1].record == projection.host_configuration
        and report["host_configuration"] == projection.host_configuration.to_dict()
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "qualification_stubbed": False,
        "qualification_digest": qualification_digest,
        "native_version": inventory.version,
        "native_sha256": inventory.sha256,
        "host_source_identity": spec.source_identity,
        "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "native_clients": len(projection.invocations),
        "authored_callbacks": len(requests),
        "roles": report["roles_ran"],
        "synthetic_scientific_attempts": 2,
        "replay_unchanged": unchanged,
        "host_configuration": projection.host_configuration.to_dict(),
        "real_credentials_used": False,
        "provider_calls": 0,
        "live_conformance": "not_attempted",
    }
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    print(f"Configured CLI: {receipt['status']}", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--qualification-digest", required=True)
    args = parser.parse_args()
    return 0 if exercise(**vars(args))["status"] == "passed" else 4


if __name__ == "__main__":
    raise SystemExit(main())
