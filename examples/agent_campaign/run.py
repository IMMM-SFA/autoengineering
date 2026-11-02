"""Offline scripted campaign example. No live host or generated code is executed."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoengineering.agents.broker import workflow_broker
from autoengineering.agents.hosts.scripted import scripted_host
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.records import AgentRunSpec, HostSelection, ResourceLimits
from autoengineering.agents.report import evidence_report
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.fixture import agent_fixture
from examples.campaign_contracts.build_fixture import ROOT


def prepare(output: Path, *, workflow_route="four_role"):
    output = Path(output).absolute()
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise ValueError("example requires a fresh output directory")
    # Validate ancestors before writing even the specification.
    for path in (*reversed(output.parents), output):
        if path.is_symlink():
            raise ValueError("example output contains a symlink")
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    output.chmod(0o700)
    checked_directory(output)
    specification = output / "scientific.yaml"
    agent_fixture().to_yaml(specification)
    controller = CampaignController.create(specification, ROOT, output / "campaign")
    identity = json.loads((controller.store.root / "identity.json").read_text())
    spec = AgentRunSpec(
        "1.0",
        "scripted-worker",
        controller.spec.name,
        identity["scientific_identity"],
        HostSelection("fake", "none", "scripted", "1.0"),
        template_digests(),
        ("linear-v2",),
        POLICY_DIGEST,
        ResourceLimits(20, 16, 4, 2, 300, 30, 262144, 1048576),
        host_source_identity(),
        host_environment_identity(),
        "supplied",
    )
    if workflow_route == "single_agent":
        from autoengineering.agents.single_agent import single_agent_spec

        spec = single_agent_spec(spec, run_id="scripted-single-agent")
    elif workflow_route != "four_role":
        raise ValueError("unsupported workflow route")
    durable_write(output / "agent-run.json", spec.to_json().encode())
    return controller, spec


def run(output: Path, *, workflow_route="four_role"):
    controller, spec = prepare(output, workflow_route=workflow_route)
    store = WorkerStore.create(output / "worker", spec)
    broker = workflow_broker(controller, SerialScheduler(store, scripted_host(workflow_route)))
    broker.advance()
    return evidence_report(store)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument(
        "--workflow-route", choices=("four_role", "single_agent"), default="four_role"
    )
    args = parser.parse_args()
    if args.prepare_only:
        _, spec = prepare(args.output, workflow_route=args.workflow_route)
        print(canonical_json({"status": "prepared", "run_digest": spec.digest}))
    else:
        print(canonical_json(run(args.output, workflow_route=args.workflow_route)))


if __name__ == "__main__":
    main()
