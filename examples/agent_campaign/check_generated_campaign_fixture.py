"""Bounded authored registration and deterministic generated-backend campaign.

This fixture tests plumbing with public scalar values. It makes no claim about
human approval, a live worker, independent confirmation or scientific utility.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import time

from autoengineering.adapters.registration import load_registration
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.identity import scientific_source_paths
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.check_registration_fixture import exercise as register_fixture
from examples.campaign_contracts.build_fixture import ROOT, fixture


def specification(registration_root: Path, identity: str, source: Path):
    """Freeze a fresh private profile, including the exact registered source refs."""
    registration, generated = load_registration(registration_root, expected_identity=identity)
    source.mkdir(mode=0o700)
    original = fixture()
    engine = tuple(
        reference(ROOT, name, media_type="application/octet-stream", producer="author")
        for name in (
            "examples/campaign_contracts/fixture_model.py",
            *scientific_source_paths(version="2"),
        )
    )
    for root, refs in (
        (
            ROOT,
            (
                original.baseline.system,
                original.provenance.environment_lock,
                *engine,
                *(data.artifact for data in original.data),
            ),
        ),
        (registration_root, generated),
    ):
        for ref in refs:
            path = source / ref.path
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            durable_write(path, read_bytes(root, ref))
    # A separate authored comparison fixture. This does not alter the checked
    # contract fixture, an old campaign or a scientific benchmark criterion.
    durable_write(source / "comparison-authored.json", b'{"prediction":4.0}')
    comparison = reference(
        source, "comparison-authored.json", media_type="application/json", producer="fixture"
    )
    sources = (*engine, *generated)
    return replace(
        original,
        name="generated-backend-authored-fixture",
        scientific_scope="Authored scalar container/controller integration fixture",
        source_bundle="scientific-isolated-v2",
        baseline=replace(
            original.baseline,
            adapter_id="linear-fixed",
            parameters={},
            model=replace(original.baseline.model, source_bundle=sources),
        ),
        provenance=replace(original.provenance, sources=sources),
        data=tuple(
            replace(data, artifact=comparison) if data.role == "comparison" else data
            for data in original.data
        ),
        interventions=(
            replace(
                original.interventions[0],
                implementation_ids=("linear-v1", registration.adapter_id),
                parameter_bounds={},
            ),
        ),
        execution=replace(
            original.execution,
            adapter_ids=("linear-fixed", registration.adapter_id),
            max_executions=2,
            timeout_seconds=15,
            termination_grace_seconds=2,
            kill_wait_seconds=2,
            active_deadline_seconds=60,
        ),
    )


INTERRUPTED = """
import os, sys
from pathlib import Path
from autoengineering.campaign.controller import CampaignController
c = CampaignController.create(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
def fault(stage):
    p = c.store.replay()
    s = c.state(p)
    if (stage == 'before_staging' and p.events and p.events[-1].operation == 'action_reserved'
        and s.budget.attempts[-1].id == 'attempt-000002'):
        os._exit(77)
c.store.fault = fault
c.advance()
"""


def exercise(output: Path, qualification_root: Path, qualification_digest: str):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("generated campaign fixture requires a fresh output directory")
    output.mkdir(mode=0o700)
    durable_write(
        output / "manifest.json",
        canonical_json(
            {
                "schema_version": "1.0",
                "purpose": "authored-generated-campaign-fixture",
                "maximum_container_starts": 5,
                "maximum_scientific_starts": 2,
                "max_elapsed_seconds": 90,
                "provider_calls": 0,
                "human_approval_claimed": False,
                "live_generated_worker": False,
                "qualification_digest": qualification_digest,
            }
        ).encode(),
    )
    began = time.monotonic()
    registered = register_fixture(
        output / "registration-fixture", qualification_root, qualification_digest
    )
    if registered["status"] != "pass":
        raise ValueError("authored registration fixture failed")
    spec = specification(
        output / "registration-fixture/registration",
        registered["registration_identity"],
        output / "source",
    )
    spec.to_yaml(output / "campaign.yaml")
    print("Running the authored generated-backend campaign", flush=True)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            INTERRUPTED,
            str(output / "campaign.yaml"),
            str(output / "source"),
            str(output / "campaign"),
        ],
        stdin=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    if child.returncode != 77:
        raise ValueError("generated fixture did not interrupt before candidate result commit")
    controller = CampaignController.open(output / "campaign")
    if (
        controller.state().budget.unresolved_attempts != 1
        or len(controller.state().budget.attempts) != 2
    ):
        raise ValueError("interrupted generated attempt was incorrectly classified")
    if controller.advance().state != "completed":
        raise ValueError("generated campaign did not complete; inspect its retained journal")
    state = controller.state()
    if (
        state.outcome != "accepted_candidate"
        or len(state.budget.attempts) != 2
        or state.budget.cost_is_uncertain
    ):
        raise ValueError("generated campaign did not preserve expected outcome and accounting")
    selected = state.evaluations[-1]
    if selected.metrics["rmse"] != 0 or "isolated_execution_record" not in selected.provenance:
        raise ValueError("generated evaluation lacks its source-bound inner execution receipt")
    binding = unique_json(
        (controller.store.root / "attempts/attempt-000002/container-launch.json").read_text()
    )
    execution = controller.store.root / binding["execution_path"]
    physical = unique_json((execution / "result.json").read_text())
    if physical["stopped"] is not True or physical["status"] != "success":
        raise ValueError("generated campaign did not stop its owned container")
    count = len(state.budget.attempts)
    reopened = CampaignController.open(controller.store.root)
    if reopened.advance().state != "completed" or len(reopened.state().budget.attempts) != count:
        raise ValueError("completed campaign resume changed physical attempt count")
    elapsed = time.monotonic() - began
    if elapsed > 90:
        raise ValueError("generated campaign fixture exceeded its elapsed allowance")
    result = {
        "status": "passed",
        "container_starts": registered["container_starts"] + 1,
        "scientific_starts": count,
        "provider_calls": 0,
        "elapsed_seconds": elapsed,
        "outcome": state.outcome,
        "registration_identity": registered["registration_identity"],
        "inner_execution_record": selected.provenance["isolated_execution_record"],
        "confirmation": state.confirmation,
        "interruption": "saved-container-and-native-result-before-campaign-commit",
        "candidate_reused_without_new_execution": True,
    }
    durable_write(output / "result.json", canonical_json(result).encode())
    print(f"Generated campaign fixture passed in {elapsed:.2f} seconds", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qualification-root", type=Path, required=True)
    parser.add_argument("--qualification-digest", required=True)
    args = parser.parse_args()
    exercise(args.output, args.qualification_root, args.qualification_digest)


if __name__ == "__main__":
    main()
