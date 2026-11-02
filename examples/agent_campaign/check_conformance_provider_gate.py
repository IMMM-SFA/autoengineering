"""Actual pinned native reply must fail conformance without fixed-provider proof.

Only the upstream callback is authored. A failed text verdict is the expected
result. No real credential or provider is used and no scientific model starts.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.agents.conformance_runtime import ConformanceRuntime
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import durable_write
from examples.agent_campaign.check_conformance_preparation import exercise as prepare_fixture
from examples.agent_campaign.check_brokered_scheduler_fixture import authored_stream, snapshot


def exercise(output, *, executable, qualification_root, qualification_digest):
    output = Path(output).absolute()
    prepared = prepare_fixture(
        output,
        executable=executable,
        qualification_root=qualification_root,
        qualification_digest=qualification_digest,
    )
    config = HostConfiguration.from_file(output / "host.toml")
    runtime = ConformanceRuntime.create(
        output / "proposal", expected_digest=prepared["preparation_digest"], configuration=config
    )
    callbacks = []

    def upstream(self, *_):
        def call(raw):
            callbacks.append(raw)
            return authored_stream(canonical_json({"handoff_json": '{"ack":"conformance"}'}))

        return call

    print("Checking refusal of authored reply as real provider conformance", flush=True)
    with patch.object(BatchCodexHost, "_upstream", new=upstream):
        report = runtime.advance()
        before = snapshot(runtime.batch.root)
        reopened = ConformanceRuntime.open(
            output / "proposal",
            expected_digest=prepared["preparation_digest"],
            configuration=config,
            runtime_digest=runtime.batch.digest,
        )
        replay = reopened.advance()
        unchanged = before == snapshot(runtime.batch.root)
    verdict = report["case_verdicts"]["text"]
    passed = (
        report["status"] == "failed"
        and report["case_results"] == {"text": "failed"}
        and verdict["host_status"] == "completed"
        and verdict["content_matches"]
        and verdict["provider"]["verified"] is False
        and len(callbacks) == 1
        and report["host_reservations_charged"] == 1
        and report["scientific_reservations_charged"] == 0
        and replay == report
        and unchanged
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "runtime_status": report["status"],
        "expected_rejection": "fixed_worker_response_proof_unavailable",
        "rejected_case": "text",
        "native_channel_completed": verdict["host_status"] == "completed",
        "batch_digest": runtime.batch.digest,
        "preparation_digest": prepared["preparation_digest"],
        "qualification_digest": qualification_digest,
        "qualification_stubbed": False,
        "native_clients": 1,
        "authored_callbacks": len(callbacks),
        "scientific_starts": 0,
        "provider_calls": 0,
        "real_credentials_used": False,
        "replay_unchanged": unchanged,
        "live_conformance_complete": False,
        "missing_execution_handlers": report["missing_execution_handlers"],
    }
    durable_write(output / "runtime-report.json", canonical_json(report).encode())
    durable_write(output / "provider-gate-receipt.json", canonical_json(receipt).encode())
    print(
        f"Provider conformance boundary: {receipt['status']} (runtime {report['status']})",
        flush=True,
    )
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
