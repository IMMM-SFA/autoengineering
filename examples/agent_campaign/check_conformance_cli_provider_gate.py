"""Actual native CLI run must reject an authored response as provider conformance.

Only the upstream response is authored. Run, startup receipt, failed verdict,
resume and status use the public commands and unmodified provider gate. No real
credential, provider or scientific evaluation is used.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import durable_write
from autoengineering.cli import cli
from examples.agent_campaign.check_brokered_scheduler_fixture import authored_stream, snapshot
from examples.agent_campaign.check_conformance_preparation import exercise as prepare_fixture


def exercise(output, *, executable, qualification_root, qualification_digest):
    output = Path(output).absolute()
    prepared = prepare_fixture(
        output,
        executable=executable,
        qualification_root=qualification_root,
        qualification_digest=qualification_digest,
    )
    args = [
        "agents",
        "conformance-run",
        str(output / "proposal"),
        "--expected-digest",
        prepared["preparation_digest"],
        "--host-config",
        str(output / "host.toml"),
    ]
    calls = []

    def upstream(self, *_):
        def callback(raw):
            calls.append(raw)
            return authored_stream(canonical_json({"handoff_json": '{"ack":"conformance"}'}))

        return callback

    print("Checking public native run and refusal of authored provider conformance", flush=True)
    with patch.object(BatchCodexHost, "_upstream", new=upstream):
        result = CliRunner().invoke(cli, args)
        if result.exit_code != 4:
            raise ValueError("CLI provider refusal fixture failed: " + result.stdout)
        report, startup = unique_json(result.stdout), unique_json(result.stderr)
        before = snapshot(output / "runtime")
        args[1] = "conformance-resume"
        args += ["--runtime-digest", startup["runtime_digest"], "--max-new-cases", "0"]
        replay = CliRunner().invoke(cli, args)
        status = CliRunner().invoke(
            cli,
            [
                "agents",
                "conformance-status",
                str(output / "runtime"),
                "--expected-digest",
                startup["runtime_digest"],
            ],
        )
        unchanged = snapshot(output / "runtime") == before
    verdict = report["case_verdicts"]["text"]
    passed = (
        startup["event"] == "conformance_runtime_created"
        and startup["runtime_digest"] == report["batch_digest"]
        and startup["preparation_digest"] == prepared["preparation_digest"]
        and report["case_results"] == {"text": "failed"}
        and verdict["host_status"] == "completed"
        and verdict["content_matches"]
        and not verdict["provider"]["verified"]
        and len(calls) == 1
        and report["host_reservations_charged"] == 1
        and report["scientific_reservations_charged"] == 0
        and replay.exit_code == 4
        and status.exit_code == 0
        and unique_json(replay.stdout) == unique_json(status.stdout) == report
        and unchanged
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "runtime_status": report["status"],
        "expected_rejection": "fixed_worker_response_proof_unavailable",
        "startup_receipt": startup,
        "qualification_digest": qualification_digest,
        "qualification_stubbed": False,
        "provider_gate_stubbed": False,
        "native_clients": 1,
        "authored_callbacks": len(calls),
        "provider_calls": 0,
        "scientific_starts": 0,
        "real_credentials_used": False,
        "replay_unchanged": unchanged,
        "live_conformance_complete": False,
    }
    durable_write(output / "runtime-startup.json", canonical_json(startup).encode())
    durable_write(output / "runtime-report.json", canonical_json(report).encode())
    durable_write(output / "cli-provider-gate-receipt.json", canonical_json(receipt).encode())
    print(f"CLI provider refusal fixture: {receipt['status']}", flush=True)
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
