"""Pinned native owner-loss case before credential preflight, with no provider.

Only the preceding case verdicts are authored zero-work markers. The owner-loss
handler, native profile, fixed subscription command, gates and stop proofs are
unmodified. No credential, model or scientific evaluation is used.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from click.testing import CliRunner

from autoengineering.agents.conformance_runtime import ConformanceRuntime
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import durable_write
from autoengineering.cli import cli
from examples.agent_campaign.check_brokered_scheduler_fixture import snapshot
from examples.agent_campaign.check_conformance_preparation import exercise as prepare_fixture


def exercise(output, *, executable, qualification_root, qualification_digest):
    output = Path(output).absolute()
    prepared = prepare_fixture(
        output,
        executable=executable,
        qualification_root=qualification_root,
        qualification_digest=qualification_digest,
    )
    configuration = HostConfiguration.from_file(output / "host.toml")
    runtime = ConformanceRuntime.create(
        output / "proposal",
        expected_digest=prepared["preparation_digest"],
        configuration=configuration,
    )
    role_root = runtime.batch.root / "cases/roles/worker"
    role_root.parent.mkdir(mode=0o700, parents=True)
    empty_worker = WorkerStore.create(role_root, runtime.plan.worker)
    for case in runtime.plan.batch.cases[:4]:
        runtime.batch.start_case(case.id, case.configuration_digest)
        runtime.batch.finish_case(
            case.id,
            "passed",
            (
                runtime.batch.evidence(
                    {
                        "unit_attestation_only": True,
                        "executed": False,
                        "worker_head": empty_worker.replay().events[-1].digest,
                    }
                ),
            ),
        )
    args = [
        "agents",
        "conformance-resume",
        str(output / "proposal"),
        "--expected-digest",
        prepared["preparation_digest"],
        "--runtime-digest",
        runtime.batch.digest,
        "--host-config",
        str(output / "host.toml"),
        "--max-new-cases",
        "1",
    ]
    print("Checking actual native owner loss before credential preflight", flush=True)
    result = CliRunner().invoke(cli, args)
    if result.exit_code != 0:
        raise ValueError("owner-loss CLI fixture failed: " + result.stdout)
    report = unique_json(result.stdout)
    before = snapshot(runtime.batch.root)
    args[-1] = "0"
    replay = CliRunner().invoke(cli, args)
    status = CliRunner().invoke(
        cli,
        [
            "agents",
            "conformance-status",
            str(runtime.batch.root),
            "--expected-digest",
            runtime.batch.digest,
        ],
    )
    unchanged = snapshot(runtime.batch.root) == before
    proof = report["case_verdicts"]["owner_loss"]
    observation = runtime.batch.report()["observations"][0]
    passed = (
        proof["passed"]
        and proof["intended_phase_exercised"]
        and proof["stop_verified"]
        and proof["credential_preflight"] == "not_started"
        and proof["host_status"] == "host_failure"
        and proof["usage"] == {}
        and proof["resolved_model"] is None
        and proof["elapsed_seconds"] is None
        and observation["transcript_bytes"] is None
        and report["host_reservations_charged"] == 1
        and report["scientific_reservations_charged"] == 0
        and not report["live_conformance_complete"]
        and unchanged
        and replay.exit_code == status.exit_code == 0
        and unique_json(replay.stdout) == unique_json(status.stdout) == report
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "scope": "native_owner_loss_before_credential_preflight_only",
        "case_prefix_stubbed": True,
        "case_prefix_executed": False,
        "owner_handler_stubbed": False,
        "qualification_stubbed": False,
        "fixed_upstream_worker_stubbed": False,
        "qualification_digest": qualification_digest,
        "preparation_digest": prepared["preparation_digest"],
        "batch_digest": runtime.batch.digest,
        "native_clients": 1,
        "provider_calls": 0,
        "scientific_starts": 0,
        "real_credentials_used": False,
        "credential_preflight": "not_started",
        "request_may_have_been_sent": False,
        "usage": "unknown",
        "native_elapsed_seconds": None,
        "transcript_ceiling_retained": observation["transcript_bytes"] is None,
        "replay_unchanged": unchanged,
        "live_conformance_complete": False,
    }
    durable_write(output / "runtime-report.json", canonical_json(report).encode())
    durable_write(output / "owner-fixture-receipt.json", canonical_json(receipt).encode())
    print(f"Owner-loss fixture: {receipt['status']}", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--qualification-digest", required=True)
    return 0 if exercise(**vars(parser.parse_args()))["status"] == "passed" else 4


if __name__ == "__main__":
    raise SystemExit(main())
