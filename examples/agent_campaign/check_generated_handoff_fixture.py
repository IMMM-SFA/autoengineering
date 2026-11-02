"""Bounded fake-host source handoff, trusted review and linked campaign fixture.

Public authored values test integration. This is not live model generation,
human author approval, independent confirmation or a scientific benefit claim.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from itertools import repeat
from pathlib import Path
import time

from autoengineering.adapters.registration import AdmissionReview
from autoengineering.agents.broker import CampaignBroker
from autoengineering.agents.containers import DockerBoundary
from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.hosts.scripted import scripted_host, supplied_reply
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.interface import InterfaceSpec, InterfaceCase, InterfaceReceipt
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.preparation import SourcePreparation
from autoengineering.agents.qualification import verify_qualification
from autoengineering.agents.records import (
    AgentRunSpec,
    HostSelection,
    ResourceLimits,
    RoleHandoff,
    SourceDraft,
)
from autoengineering.agents.report import evidence_report, render_report
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.store import WorkerStore
from autoengineering.agents.workspaces import SourceCapture
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.agent_campaign.fixture import agent_fixture
from examples.campaign_contracts.build_fixture import ROOT

BASE = b'def predict(inputs):\n return {"prediction":inputs["forcing"]}\n'
SOURCE = b'def predict(inputs):\n return {"prediction":inputs["forcing"]*2.0}\n'


def source_reply(task, prompt, invocation_id):
    if task.expected_schema != "role-handoff-1.1":
        return supplied_reply(task, prompt, invocation_id)
    envelope = unique_json(prompt[prompt.index('{"approved_evidence"') :])
    evidence = envelope["approved_evidence"][0]
    context = unique_json(evidence["content"])["submitted_handoff"]
    draft = SourceDraft(
        context["proposal"]["id"],
        context["base_snapshot"],
        {"adapter.py": SOURCE.decode()},
        ("python-stdlib", "math"),
        (evidence["id"],),
    )
    handoff = RoleHandoff(
        "1.1",
        f"source-{invocation_id}",
        task.id,
        invocation_id,
        task.role,
        task.campaign_revision,
        "complete",
        draft,
        (evidence["id"],),
        (),
        "configure",
    )
    return HostResult("completed", handoff.to_json(), None, {"total_tokens": None}, 0)


def worker(controller, root, *, name, mode, host):
    identity = unique_json((controller.store.root / "identity.json").read_text())[
        "scientific_identity"
    ]
    implementations = tuple(
        implementation
        for item in controller.spec.interventions
        for implementation in item.implementation_ids
        if implementation != controller.spec.baseline.model.implementations[item.target]
    )
    spec = AgentRunSpec(
        "1.0",
        name,
        controller.spec.name,
        identity,
        HostSelection("fake", "none", "scripted", "1.0"),
        template_digests(),
        implementations,
        POLICY_DIGEST,
        ResourceLimits(12, 10, 2, 1, 90, 10, 1048576, 1048576),
        host_source_identity(),
        host_environment_identity(),
        mode,
    )
    store = WorkerStore.create(root, spec)
    return CampaignBroker(controller, SerialScheduler(store, host))


def exercise(output: Path, qualification_root: Path, qualification_digest: str):
    output = Path(output).absolute()
    checked_directory(output.parent)
    if output.exists() or output.is_symlink():
        raise ValueError("source handoff fixture requires a fresh output directory")
    qualification = verify_qualification(qualification_root, expected_digest=qualification_digest)
    output.mkdir(mode=0o700)
    durable_write(
        output / "manifest.json",
        canonical_json(
            {
                "schema_version": "1.0",
                "purpose": "authored-fake-generated-handoff-fixture",
                "maximum_container_starts": 3,
                "maximum_scientific_starts": 3,
                "maximum_fake_host_invocations": 24,
                "expected_fake_host_invocations": 11,
                "max_elapsed_seconds": 120,
                "provider_calls": 0,
                "human_approval_claimed": False,
                "live_generated_worker": False,
                "qualification_digest": qualification_digest,
            }
        ).encode(),
    )
    began = time.monotonic()
    initial = agent_fixture()
    source = output / "origin-source"
    source.mkdir(mode=0o700)
    refs = (
        initial.baseline.system,
        initial.provenance.environment_lock,
        *initial.provenance.sources,
        *(data.artifact for data in initial.data),
    )
    for ref in refs:
        target = source / ref.path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        durable_write(target, read_bytes(ROOT, ref))
    # Separate public authored comparison, without changing checked fixture bytes.
    durable_write(source / "comparison-authored.json", b'{"prediction":4.0}')
    comparison = reference(
        source, "comparison-authored.json", media_type="application/json", producer="fixture"
    )
    initial = replace(
        initial,
        name="source-origin-authored-fixture",
        baseline=replace(initial.baseline, adapter_id="linear-fixed", parameters={}),
        data=tuple(
            replace(data, artifact=comparison) if data.role == "comparison" else data
            for data in initial.data
        ),
        interventions=(replace(initial.interventions[0], parameter_bounds={}),),
        execution=replace(
            initial.execution,
            adapter_ids=("linear-fixed",),
            max_executions=1,
            timeout_seconds=15,
            termination_grace_seconds=2,
            kill_wait_seconds=2,
            active_deadline_seconds=60,
        ),
    )
    initial.to_yaml(output / "origin.yaml")
    parent = CampaignController.create(output / "origin.yaml", source, output / "origin")
    broker = worker(
        parent,
        output / "origin-workers",
        name="source-workers",
        mode="generated",
        host=FakeHost(repeat(source_reply)),
    )
    print("Preparing the originating proposal", flush=True)
    if broker.advance().state != "candidate_pending":
        raise ValueError("source origin did not stop before implementation admission")
    head = parent.store.replay().head_hash
    interface = InterfaceSpec(
        "1.0",
        initial.baseline.model.inputs,
        initial.baseline.model.outputs,
        (
            InterfaceCase("first", {"forcing": 1.5}, {"prediction": 3.0}),
            InterfaceCase("second", {"forcing": 2.5}, {"prediction": 5.0}),
        ),
    )
    print("Capturing and checking the fake-host source response", flush=True)
    manager = SourcePreparation(broker, qualification_root, qualification_digest)
    prepared = manager.prepare(baseline=BASE, specification=interface)
    if prepared.state != "checked":
        raise ValueError(f"source checks ended as {prepared.state}; evidence retained")
    capture = SourceCapture.from_json(read_bytes(broker.store.root, prepared.capture).decode())
    checked = InterfaceReceipt.from_json(read_bytes(broker.store.root, prepared.interface).decode())
    review = AdmissionReview(
        "1.0",
        "response",
        capture.digest,
        checked.digest,
        qualification_digest,
        {},
        "fixture-caller",
        "Authored fixture approval, not human author review",
        "approve",
    )
    registration = manager.register(
        prepared.id,
        review=review,
        trusted_review_digest=review.digest,
        output=output / "registration",
    )
    print("Creating the separately budgeted successor campaign", flush=True)
    successor = manager.fork(
        prepared.id,
        registration_root=output / "registration",
        name="linked-source-authored-fixture",
        execution=replace(
            initial.execution,
            adapter_ids=("linear-fixed", registration.adapter_id),
            max_executions=2,
        ),
        output=output / "successor",
    )
    if successor.state().budget.attempts or parent.store.replay().head_hash != head:
        raise ValueError("source fork executed work or mutated its originating campaign")
    following = worker(
        successor,
        output / "successor-workers",
        name="successor-workers",
        mode="supplied",
        host=scripted_host(),
    )
    print("Evaluating and independently reviewing the registered source", flush=True)
    if (
        following.advance().state != "completed"
        or following.controller.state().outcome != "accepted_candidate"
    ):
        raise ValueError("successor did not complete the authored four-role workflow")
    if parent.store.replay().head_hash != head or len(parent.state().budget.attempts) != 1:
        raise ValueError("successor execution changed its originating campaign")
    reviewers = [
        prompt for _, task, prompt in following.scheduler.host.calls if task.role == "reviewer"
    ]
    if len(reviewers) != 1:
        raise ValueError("successor did not use one independent review invocation")
    envelope = unique_json(reviewers[0][reviewers[0].index('{"approved_evidence"') :])
    review_context = unique_json(envelope["approved_evidence"][0]["content"])["submitted_handoff"]
    submitted = review_context.get("registered_implementation", {})
    if (
        submitted.get("source_text") != SOURCE.decode()
        or submitted.get("interface_receipt") != checked.to_dict()
    ):
        raise ValueError("independent reviewer did not receive the exact source and check context")
    if str(parent.store.root) in reviewers[0] or str(successor.store.root) in reviewers[0]:
        raise ValueError("independent review exposed a private campaign path")
    before = len(following.controller.state().budget.attempts)
    following.advance()
    manager.fork(
        prepared.id,
        registration_root=output / "registration",
        name="linked-source-authored-fixture",
        execution=replace(
            initial.execution,
            adapter_ids=("linear-fixed", registration.adapter_id),
            max_executions=2,
        ),
        output=output / "successor",
    )
    if len(following.controller.state().budget.attempts) != before:
        raise ValueError("completed replay launched replacement work")
    boundary = DockerBoundary(qualification.runtime)
    paths = list((broker.store.root / "preparations").glob("*/interface/case-*/container-id"))
    paths += list(
        (successor.store.root / "jobs").glob("*-scratch/isolated-*/execution/container-id")
    )
    if len(paths) != 3:
        raise ValueError("fixture container count differs from its reserved allowance")
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
            raise ValueError("fixture owned-container removal is unresolved")
    reports = {}
    for label, value in (("origin", broker), ("successor", following)):
        report = evidence_report(value.store)
        reports[label] = report
        durable_write(output / f"{label}-report.json", canonical_json(report).encode())
        durable_write(output / f"{label}-report.md", render_report(report).encode())
    calls = sum(len(value.scheduler.host.calls) for value in (broker, following))
    attempts = len(parent.state().budget.attempts) + len(successor.state().budget.attempts)
    elapsed = time.monotonic() - began
    if calls != 11 or attempts != 3 or elapsed > 120:
        raise ValueError("source handoff fixture exceeded or changed its frozen allowances")
    result = {
        "status": "passed",
        "provider_calls": 0,
        "fake_host_invocations": calls,
        "scientific_starts": attempts,
        "container_starts": len(paths),
        "elapsed_seconds": elapsed,
        "origin_head_unchanged": True,
        "origin_state": parent.store.replay().state,
        "source_handoff_version": "1.1",
        "preparation_id": prepared.id,
        "registration_identity": registration.digest,
        "successor_identity": broker.store.replay().preparations[prepared.id].successor_identity,
        "successor_outcome": successor.state().outcome,
        "successor_confirmation": successor.state().confirmation,
        "owned_containers_removed": [path.read_text() for path in paths],
    }
    durable_write(output / "result.json", canonical_json(result).encode())
    print(f"Generated handoff fixture passed in {elapsed:.2f} seconds", flush=True)
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
