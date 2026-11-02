"""Shared batch over actual pinned native clients and synthetic scientific work.

Only upstream replies are authored. No real lease or provider is used. This is
an accounting fixture, not the live conformance batch or measured-data pilot.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
from pathlib import Path
from unittest.mock import patch
import uuid

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.agents.broker import CampaignBroker
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.hosts.base import InvocationContext
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
from autoengineering.agents.hosts.native_profile import verify_native_profile
from autoengineering.agents.hosts.scripted import supplied_reply
from autoengineering.agents.records import HostSelection, ResourceLimits, TaskAssignment
from autoengineering.agents.report import evidence_report
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.check_brokered_scheduler_fixture import authored_stream, snapshot
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL
from examples.agent_campaign.run import prepare
from examples.campaign_contracts.build_fixture import ROOT


def exercise(output, *, executable, qualification_root, qualification_digest):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists():
        raise ValueError("batch fixture requires a fresh output directory")
    inventory = inspect_brokered_codex(Path(executable))
    profile = verify_native_profile(qualification_root, expected_digest=qualification_digest)
    if inventory != profile.inventory or profile.model != OFFLINE_MODEL:
        raise ValueError("batch fixture executable/model differs from native profile")
    output.mkdir(mode=0o700)
    durable_write(output / "fixture-source.py", Path(__file__).read_bytes())
    seed_controller, worker_spec = prepare(output / "preparation")
    worker_spec = replace(
        worker_spec,
        host=HostSelection("codex", "subscription", OFFLINE_MODEL, "2.1", qualification_digest),
    )
    configuration = HostConfiguration(
        Path(qualification_root).absolute(),
        qualification_digest,
        output / "no-real-credential",
        "offline-batch",
    )
    base_host = configuration.build(worker_spec)
    roles_digest = digest(
        {
            "worker": worker_spec.digest,
            "campaign": seed_controller.spec.digest,
            "reply": "supplied-authored",
            "fixture_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
    )
    text_digest = digest(
        {"prompt": "Return an empty object in handoff_json.", "reply": "authored-empty-object"}
    )
    limits = ResourceLimits(16, 12, 2, 1, 720, 30, 1048576, 65536)
    spec = BatchSpec(
        "1.0",
        "offline-batch-accounting",
        worker_spec.source_identity,
        worker_spec.environment_identity,
        worker_spec.host,
        base_host.capabilities(),
        configuration.digest,
        limits,
        2,
        (
            BatchCase("roles", "roles", roles_digest, 7, 2),
            BatchCase("text", "text", text_digest, 1, 0),
        ),
    )
    batch = BatchStore.create(output / "batch", spec)
    batch.start_case("roles", roles_digest)
    root = batch.root / "cases/roles"
    root.mkdir(mode=0o700)
    controller = BatchCampaignController.create(
        output / "preparation/scientific.yaml",
        ROOT,
        root / "campaign",
        batch=batch,
        case_id="roles",
    )
    worker = WorkerStore.create(root / "worker", worker_spec)
    calls = []

    def upstream(self, root, workspace, home, deadline, cancelled):
        def call(raw):
            calls.append({"case": self.case_id, "sha256": hashlib.sha256(raw).hexdigest()})
            if self.case_id == "text":
                return authored_stream(canonical_json({"handoff_json": "{}"}))
            prompt = unique_json(raw.decode())["input"][0]["content"][0]["text"]
            context = unique_json(prompt[prompt.index('{"approved_evidence"') :])
            task = TaskAssignment.from_dict(context["task"])
            reply = supplied_reply(task, prompt, context["invocation_id"])
            return authored_stream(canonical_json({"handoff_json": reply.raw_output}))

        return call

    print("Checking one shared batch over native roles and synthetic science", flush=True)
    with patch.object(BatchCodexHost, "_upstream", new=upstream):
        host = BatchCodexHost(configuration, batch, "roles")
        broker = CampaignBroker(controller, SerialScheduler(worker, host))
        broker.advance()
        roles = evidence_report(worker)
        if roles["status"] != "completed" or roles["physical_work"]["attempts"] != 2:
            raise ValueError("batch role/scientific fixture failed; evidence retained")
        batch.finish_case(
            "roles",
            "passed",
            (
                batch.evidence(
                    {
                        "worker_run": worker.spec.digest,
                        "campaign": controller.spec.digest,
                        "roles": roles["roles_ran"],
                        "scientific_attempts": [
                            a.to_dict() for a in controller.state().budget.attempts
                        ],
                        "outcome": roles["campaign_outcome"],
                    }
                ),
            ),
        )
        batch.start_case("text", text_digest)
        text_root = batch.root / "cases/text"
        text_root.mkdir(mode=0o700)
        text_host = BatchCodexHost(configuration, batch, "text")
        task = replace(next(iter(worker.replay().tasks.values())), id="direct-text", grants=())
        prompt = text_host.prepare_prompt(task, "Return an empty object in handoff_json.")
        result = text_host.invoke_supervised(
            task,
            prompt,
            InvocationContext(
                "direct-text",
                uuid.uuid4().hex,
                text_root / "direct-text",
                30,
                65536,
                lambda _: None,
                lambda: False,
            ),
        )
        if result.status != "completed" or result.raw_output != "{}" or not result.stop_verified:
            raise ValueError("batch direct native text case failed; evidence retained")
        batch.finish_case(
            "text",
            "passed",
            (
                batch.evidence(
                    {
                        "status": result.status,
                        "stop_verified": result.stop_verified,
                        "output": result.raw_output,
                    }
                ),
            ),
        )
        before = snapshot(output)
        broker.advance()
        reopened = BatchStore(batch.root, expected_digest=batch.digest)
        report = reopened.report()
        replay_unchanged = before == snapshot(output)
    passed = (
        report["status"] == "completed"
        and report["host_reservations_charged"] == 8
        and report["scientific_reservations_charged"] == 2
        and len(calls) == 8
        and replay_unchanged
        and not report["pending_reservations"]
        and report["transcript_bytes_charged"] <= limits.transcript_bytes
    )
    receipt = {
        "status": "passed" if passed else "failed",
        "batch_digest": batch.digest,
        "source_identity": worker_spec.source_identity,
        "native_version": inventory.version,
        "native_sha256": inventory.sha256,
        "qualification_digest": qualification_digest,
        "qualification_stubbed": False,
        "native_clients": 8,
        "authored_callbacks": len(calls),
        "synthetic_scientific_attempts": len(controller.state().budget.attempts),
        "transcript_bytes_charged": report["transcript_bytes_charged"],
        "roles": roles["roles_ran"],
        "replay_unchanged": replay_unchanged,
        "provider_calls": 0,
        "real_credentials_used": False,
        "live_conformance": "not_attempted",
    }
    durable_write(output / "batch-report.json", canonical_json(report).encode())
    durable_write(output / "receipt.json", canonical_json(receipt).encode())
    print(f"Batch accounting fixture: {receipt['status']}", flush=True)
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
