"""Two bounded container checks recovered through the worker CLI.

Uses authored fake-host source and an existing pinned qualification. No provider,
registration, successor campaign or new scientific benchmark is executed.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from itertools import repeat
from pathlib import Path
import time

from click.testing import CliRunner

from autoengineering.agents.containers import DockerBoundary
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.interface import InterfaceSpec, InterfaceCase
from autoengineering.agents.preparation import SourcePreparation
from autoengineering.agents.qualification import verify_qualification
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.cli import cli
from examples.agent_campaign.check_generated_handoff_fixture import BASE, source_reply, worker
from examples.agent_campaign.fixture import agent_fixture
from examples.campaign_contracts.build_fixture import ROOT


def exercise(output: Path, qualification_root: Path, qualification_digest: str):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("preparation recovery fixture requires a fresh output directory")
    qualification = verify_qualification(qualification_root, expected_digest=qualification_digest)
    output.mkdir(mode=0o700)
    durable_write(
        output / "manifest.json",
        canonical_json(
            {
                "schema_version": "1.0",
                "purpose": "authored-source-cli-recovery-fixture",
                "maximum_container_starts": 2,
                "maximum_scientific_starts": 1,
                "maximum_fake_host_invocations": 12,
                "expected_fake_host_invocations": 4,
                "max_elapsed_seconds": 60,
                "provider_calls": 0,
                "human_approval_claimed": False,
                "qualification_digest": qualification_digest,
            }
        ).encode(),
    )
    began = time.monotonic()
    original = agent_fixture()
    spec = replace(
        original,
        name="source-recovery-authored-fixture",
        baseline=replace(original.baseline, adapter_id="linear-fixed", parameters={}),
        interventions=(replace(original.interventions[0], parameter_bounds={}),),
        execution=replace(
            original.execution,
            adapter_ids=("linear-fixed",),
            max_executions=1,
            timeout_seconds=15,
            termination_grace_seconds=2,
            kill_wait_seconds=2,
            active_deadline_seconds=60,
        ),
    )
    spec.to_yaml(output / "campaign.yaml")
    controller = CampaignController.create(output / "campaign.yaml", ROOT, output / "campaign")
    broker = worker(
        controller,
        output / "worker",
        name="source-recovery-workers",
        mode="generated",
        host=FakeHost(repeat(source_reply)),
    )
    print("Preparing a source proposal", flush=True)
    if broker.advance().state != "candidate_pending":
        raise ValueError("source recovery fixture did not stop before scientific admission")
    before_parent = {
        str(path.relative_to(controller.store.root)): path.read_bytes()
        for path in controller.store.root.rglob("*")
        if path.is_file()
    }
    interface = InterfaceSpec(
        "1.0",
        spec.baseline.model.inputs,
        spec.baseline.model.outputs,
        (
            InterfaceCase("first", {"forcing": 1.5}, {"prediction": 3.0}),
            InterfaceCase("second", {"forcing": 2.5}, {"prediction": 5.0}),
        ),
    )
    failed = False

    def fault(stage):
        nonlocal failed
        if (
            not failed
            and stage == "before_event_commit"
            and list((broker.store.root / "preparations").glob("*/interface/receipt.json"))
        ):
            failed = True
            raise OSError("fixture interruption before check acknowledgment")

    broker.store.fault = fault
    print("Saving interface checks before their worker acknowledgment", flush=True)
    manager = SourcePreparation(broker, qualification_root, qualification_digest)
    value = manager.prepare(baseline=BASE, specification=interface)
    broker.store.fault = lambda stage: None
    if value.state != "reconciliation_required":
        raise ValueError("fixture did not preserve the unacknowledged source checks")
    arguments = [
        "agents",
        "resume",
        str(broker.store.root),
        "--campaign",
        str(controller.store.root),
        "--max-new-evaluations",
        "0",
    ]
    missing = CliRunner().invoke(cli, arguments)
    if missing.exit_code != 4 or unique_json(missing.stdout)["pending_source_preparations"] != [
        value.id
    ]:
        raise ValueError("CLI did not retain pending checks without qualification evidence")
    print("Recovering saved source checks through the CLI", flush=True)
    result = CliRunner().invoke(cli, arguments + ["--qualification-root", str(qualification_root)])
    if result.exit_code != 0:
        raise ValueError(f"CLI preparation recovery failed: {result.output}")
    report = unique_json(result.stdout)
    if (
        report["status"] != "awaiting_trusted_admission"
        or report["pending_source_preparations"]
        or report["allowances"]["invocations_used"] != 4
        or report["allowances"]["interface_starts_reserved"] != 2
        or report["physical_work"]["attempts"] != 1
    ):
        raise ValueError("CLI recovery changed frozen allowances or the expected preparation state")
    after_parent = {
        str(path.relative_to(controller.store.root)): path.read_bytes()
        for path in controller.store.root.rglob("*")
        if path.is_file()
    }
    if after_parent != before_parent:
        raise ValueError("CLI source recovery mutated its originating scientific campaign")
    before = len(broker.store.replay().events)
    replay = CliRunner().invoke(cli, arguments)
    if replay.exit_code != 0 or len(broker.store.replay().events) != before:
        raise ValueError("completed source recovery changed journal or physical work")
    boundary = DockerBoundary(qualification.runtime)
    paths = list((broker.store.root / "preparations").glob("*/interface/case-*/container-id"))
    if len(paths) != 2:
        raise ValueError("source check count differs from the frozen fixture allowance")
    for path in paths:
        cid = path.read_text()
        response = boundary._metadata(
            path.parent, "inspect", "--format", "{{json .}}", cid, check=False
        )
        if (
            response.returncode != 1
            or response.stdout.strip()
            or response.stderr.decode().strip()
            not in (
                f"Error: No such object: {cid}",
                f"error: no such object: {cid}",
                f"Error response from daemon: No such container: {cid}",
            )
        ):
            raise ValueError("owned source-check container removal is unresolved")
    elapsed = time.monotonic() - began
    if elapsed > 60:
        raise ValueError("source recovery fixture exceeded its elapsed allowance")
    final = {
        "status": "passed",
        "container_starts": 2,
        "scientific_starts": 1,
        "fake_host_invocations": 4,
        "provider_calls": 0,
        "elapsed_seconds": elapsed,
        "new_calls_during_recovery": 0,
        "parent_campaign_unchanged": True,
        "preparation_state": broker.store.replay().preparations[value.id].state,
        "qualification_digest": qualification_digest,
        "owned_containers_removed": [path.read_text() for path in paths],
    }
    durable_write(output / "result.json", canonical_json(final).encode())
    durable_write(output / "recovered-report.json", result.stdout.encode())
    print(f"CLI preparation recovery fixture passed in {elapsed:.2f} seconds", flush=True)
    return final


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--qualification-digest", required=True)
    args = parser.parse_args()
    exercise(args.output, args.qualification_root, args.qualification_digest)


if __name__ == "__main__":
    main()
