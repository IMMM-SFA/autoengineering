"""Exercise malformed/repair transport with actual native CLI and authored replies.

The provider proof and zero-work case prefix are explicitly stubbed. This only
checks local native transport, parser, repair and recovery integration. No real
credential or provider is used. It does not establish live conformance.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.agents.conformance_runtime import ConformanceRuntime, MALFORMED_OUTPUT
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.records import NextStep, RoleHandoff, TaskAssignment
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json, unique_json
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
    configuration = HostConfiguration.from_file(output / "host.toml")
    runtime = ConformanceRuntime.create(
        output / "proposal",
        expected_digest=prepared["preparation_digest"],
        configuration=configuration,
    )
    # These cases do not run. Their authored markers isolate the final handler.
    # The normal driver still stops before the missing owner-loss implementation.
    role_root = runtime.batch.root / "cases/roles/worker"
    role_root.parent.mkdir(mode=0o700, parents=True)
    empty_worker = WorkerStore.create(role_root, runtime.plan.worker)
    for case in runtime.plan.batch.cases[:-1]:
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
    requests = []

    def upstream(self, *_):
        def callback(raw):
            requests.append(raw)
            prompt = unique_json(raw.decode())["input"][0]["content"][0]["text"]
            context = unique_json(prompt[prompt.index('{"approved_evidence"') :])
            task = TaskAssignment.from_dict(context["task"])
            inner = (
                canonical_json(MALFORMED_OUTPUT)
                if context["repair"] is None
                else RoleHandoff(
                    "1.0",
                    "handoff-" + context["invocation_id"],
                    task.id,
                    context["invocation_id"],
                    task.role,
                    task.campaign_revision,
                    "complete",
                    NextStep("stop", None, "Authored repair"),
                    (),
                    (),
                    "stop",
                ).to_json()
            )
            return authored_stream(canonical_json({"handoff_json": inner}))

        return callback

    def provider_stub(self, *_):
        return {
            "verified": True,
            "unit_attestation_only": True,
            "evidence": self.batch.evidence(
                {
                    "kind": "authored_provider_proof_stub",
                    "real_provider": False,
                }
            ).to_dict(),
        }

    print(
        "Checking actual native malformed/repair transport with authored provider stubs", flush=True
    )
    with (
        patch.object(BatchCodexHost, "_upstream", new=upstream),
        patch.object(ConformanceRuntime, "_provider_evidence", new=provider_stub),
    ):
        report = runtime.advance()
        before = snapshot(runtime.batch.root)
        reopened = ConformanceRuntime.open(
            output / "proposal",
            expected_digest=prepared["preparation_digest"],
            configuration=configuration,
            runtime_digest=runtime.batch.digest,
        )
        replay = reopened.advance()
        unchanged = before == snapshot(runtime.batch.root)
    proof = report["case_verdicts"]["malformed"]
    worker = WorkerStore(runtime.batch.root / "cases/malformed/worker")
    first, second = worker.replay().invocations.values()
    preserved = (
        unique_json(read_bytes(worker.root, first.final_response).decode()) == MALFORMED_OUTPUT
        and first.parse_failure is not None
        and first.normalized_output is None
        and second.normalized_output is not None
    )
    passed = (
        proof["passed"]
        and preserved
        and len(requests) == 2
        and report["host_reservations_charged"] == 2
        and report["scientific_reservations_charged"] == 0
        and proof["repairs_used"] == 1
        and unchanged
        and replay == report
        and not report["live_conformance_complete"]
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "scope": "offline_native_malformed_repair_only",
        "case_prefix_stubbed": True,
        "case_prefix_executed": False,
        "provider_proof_stubbed": True,
        "qualification_stubbed": False,
        "qualification_digest": qualification_digest,
        "preparation_digest": prepared["preparation_digest"],
        "batch_digest": runtime.batch.digest,
        "native_clients": 2,
        "authored_callbacks": len(requests),
        "repairs": 1,
        "scientific_starts": 0,
        "real_credentials_used": False,
        "provider_calls": 0,
        "invalid_output_and_repair_preserved": preserved,
        "replay_unchanged": unchanged,
        "live_conformance_complete": False,
    }
    durable_write(output / "runtime-report.json", canonical_json(report).encode())
    durable_write(output / "malformed-fixture-receipt.json", canonical_json(receipt).encode())
    print(f"Malformed transport fixture: {receipt['status']}", flush=True)
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
