"""Actual native-profile preparation without any worker/model/lease dispatch."""

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
from autoengineering.agents.records import HostSelection
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.cli import cli
from examples.agent_campaign.check_brokered_scheduler_fixture import snapshot
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL
from examples.agent_campaign.run import prepare


def exercise(output, *, executable, qualification_root, qualification_digest):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists():
        raise ValueError("conformance fixture requires a fresh output")
    profile = verify_native_profile(qualification_root, expected_digest=qualification_digest)
    inventory = inspect_brokered_codex(Path(executable))
    if inventory != profile.inventory or profile.model != OFFLINE_MODEL:
        raise ValueError("fixture inventory/model differs from pinned profile")
    output.mkdir(mode=0o700)
    durable_write(output / "fixture-source.py", Path(__file__).read_bytes())
    _, template = prepare(output / "inputs")
    template = replace(
        template,
        host=HostSelection("codex", "subscription", OFFLINE_MODEL, "2.1", qualification_digest),
    )
    durable_write(output / "inputs/codex-template.json", template.to_json().encode())
    config = output / "host.toml"
    durable_write(
        config,
        (
            'schema_version="1.0"\n'
            f'qualification_root="{Path(qualification_root).absolute()}"\n'
            f'qualification_digest="{qualification_digest}"\n'
            f'credential_path="{output / "never-open-lease.json"}"\n'
            'lease_id="offline-preparation"\n'
        ).encode(),
    )
    runner = CliRunner()
    before = snapshot(output / "inputs")
    print("Checking pinned conformance preparation without starting its runtime", flush=True)
    with (
        patch.object(
            BrokeredCodexHost,
            "invoke_supervised",
            side_effect=AssertionError("worker dispatch during preparation"),
        ),
        patch.object(
            CampaignController,
            "_physical_attempt",
            side_effect=AssertionError("model start during preparation"),
        ),
    ):
        result = runner.invoke(
            cli,
            [
                "agents",
                "conformance-prepare",
                str(output / "inputs/codex-template.json"),
                "--campaign",
                str(output / "inputs/campaign"),
                "--host-config",
                str(config),
                "--output",
                str(output / "proposal"),
                "--runtime-root",
                str(output / "runtime"),
            ],
        )
        durable_write(output / "prepare-output.json", result.stdout.encode())
        if result.exit_code != 0:
            raise ValueError("conformance preparation failed; output retained")
        status = unique_json(result.stdout)
        captured = snapshot(output / "proposal")
        inspect = runner.invoke(
            cli,
            [
                "agents",
                "conformance-inspect",
                str(output / "proposal"),
                "--expected-digest",
                status["preparation_digest"],
                "--host-config",
                str(config),
            ],
        )
        unchanged = captured == snapshot(output / "proposal") and before == snapshot(
            output / "inputs"
        )
    passed = (
        inspect.exit_code == 0
        and unchanged
        and not (output / "runtime").exists()
        and status["clock_started"] is False
        and status["execution_ready"] is True
        and status["missing_execution_handlers"] == []
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "qualification_stubbed": False,
        "qualification_digest": qualification_digest,
        "native_version": inventory.version,
        "native_sha256": inventory.sha256,
        "preparation_digest": status["preparation_digest"],
        "source_identity": template.source_identity,
        "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs_and_capture_unchanged": unchanged,
        "runtime_created": False,
        "clock_started": False,
        "worker_dispatches": 0,
        "scientific_starts": 0,
        "provider_calls": 0,
        "real_credentials_used": False,
        "execution_ready": False,
        "missing_execution_handlers": status["missing_execution_handlers"],
    }
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    print(f"Conformance preparation fixture: {receipt['status']}", flush=True)
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
