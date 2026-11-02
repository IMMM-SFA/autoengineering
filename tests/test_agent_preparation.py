"""Source-response handoffs and trusted forks without live providers or Docker."""

from dataclasses import replace
from itertools import repeat
import json
from types import SimpleNamespace

import pytest

from autoengineering.agents.broker import CampaignBroker
from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.hosts.scripted import supplied_reply
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.preparation import SourcePreparation
from autoengineering.agents.records import (
    ResourceLimits,
    SourceDraft,
    RoleHandoff,
    ImplementationBundle,
)
from autoengineering.agents.report import evidence_report
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.store import WorkerStore
from autoengineering.adapters.registration import AdmissionReview
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.store import StoreError
from examples.agent_campaign.fixture import agent_fixture
from examples.campaign_contracts.build_fixture import ROOT
from test_agent_contracts import run_spec
from test_agent_interface import run as run, SOURCE

BASE = b'def predict(inputs):\n return {"prediction": inputs["forcing"]}\n'


@pytest.fixture
def prepared(run, tmp_path, monkeypatch):
    import autoengineering.agents.interface as interface
    import autoengineering.agents.preparation as preparation

    q = run.options["qualification_root"]
    q.mkdir(mode=0o700)
    for name in ("manifest.json", "qualification.json"):
        (q / name).write_text("{}")
    monkeypatch.setattr(preparation, "verify_qualification", interface.verify_qualification)
    original = agent_fixture()
    spec = replace(
        original,
        baseline=replace(original.baseline, adapter_id="linear-fixed", parameters={}),
        execution=replace(original.execution, adapter_ids=("linear-fixed",)),
        interventions=(replace(original.interventions[0], parameter_bounds={}),),
    )
    path = tmp_path / "origin.yaml"
    spec.to_yaml(path)
    controller = CampaignController.create(path, ROOT, tmp_path / "origin")
    identity = json.loads((controller.store.root / "identity.json").read_text())[
        "scientific_identity"
    ]
    worker = replace(
        run_spec(),
        campaign_id=spec.name,
        campaign_identity=identity,
        permitted_interventions=("linear-v2",),
        role_templates=template_digests(),
        tool_policy_digest=POLICY_DIGEST,
        source_identity=host_source_identity(),
        environment_identity=host_environment_identity(),
        execution_mode="generated",
        limits=ResourceLimits(20, 16, 4, 2, 300, 30, 1048576, 1048576),
    )
    behavior = {"source": SOURCE, "base": None, "evidence": None}

    def reply(task, prompt, invocation_id):
        if task.role != "implementer":
            return supplied_reply(task, prompt, invocation_id)
        envelope = json.loads(prompt[prompt.index('{"approved_evidence"') :])
        evidence = envelope["approved_evidence"][0]
        context = json.loads(evidence["content"])["submitted_handoff"]
        draft = SourceDraft(
            context["proposal"]["id"],
            behavior["base"] or context["base_snapshot"],
            {"adapter.py": behavior["source"].decode()},
            ("python-stdlib", "math"),
            (behavior["evidence"] or evidence["id"],),
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
        return HostResult("completed", handoff.to_json(), None, {}, 0)

    host = FakeHost(repeat(reply))
    store = WorkerStore.create(tmp_path / "worker", worker)
    broker = CampaignBroker(controller, SerialScheduler(store, host))
    assert broker.advance().state == "candidate_pending"
    manager = SourcePreparation(broker, q, run.options["qualification_digest"])
    return SimpleNamespace(
        broker=broker, manager=manager, run=run, behavior=behavior, root=tmp_path
    )


def prepare(p):
    return p.manager.prepare(baseline=BASE, specification=p.run.spec)


def review_for(p, value):
    from autoengineering.agents.workspaces import SourceCapture
    from autoengineering.agents.interface import InterfaceReceipt

    capture = SourceCapture.from_json(read_bytes(p.broker.store.root, value.capture).decode())
    interface = InterfaceReceipt.from_json(
        read_bytes(p.broker.store.root, value.interface).decode()
    )
    return AdmissionReview(
        "1.0",
        "response",
        capture.digest,
        interface.digest,
        p.run.options["qualification_digest"],
        {},
        "unit-test-caller",
        "Separate fixture approval of captured source and actual checks",
        "approve",
    )


def register(p):
    value = prepare(p)
    review = review_for(p, value)
    root = p.root / "registered"
    registration = p.manager.register(
        value.id, review=review, trusted_review_digest=review.digest, output=root
    )
    return value, review, root, registration


def recovered_physical(monkeypatch):
    import autoengineering.agents.preparation as module
    from autoengineering.agents.container_recovery import ContainerRecovery
    from autoengineering.campaign.serialization import digest

    def reconcile(root, **kwargs):
        result = json.loads((root / "result.json").read_text())
        return ContainerRecovery(
            result["container_id"],
            result["nonce"],
            result["intent_digest"],
            True,
            True,
            False,
            digest(result),
            result["status"],
            (root / "stdout.bin").read_bytes(),
        )

    monkeypatch.setattr(module, "reconcile_container", reconcile)


def test_source_handoff_is_captured_checked_and_never_self_admitted(prepared):
    p = prepared
    parent = p.broker.controller
    head, spec = parent.store.replay().head_hash, parent.spec
    assert evidence_report(p.broker.store)["status"] == "awaiting_source_preparation"
    value = prepare(p)
    assert value.state == "checked" and value.admission is None
    assert value.registration_identity is None
    bundle = ImplementationBundle.from_json(read_bytes(p.broker.store.root, value.bundle).decode())
    assert bundle.admitted_identity is None
    assert len(bundle.interface_results) == 1 and bundle.execution_boundary_receipt
    assert parent.store.replay().head_hash == head and parent.spec == spec
    assert len(parent.state().budget.attempts) == 1 and not parent.state().snapshots
    assert len(p.broker.scheduler.host.calls) == 4 and len(p.run.calls) == 2
    report = evidence_report(p.broker.store)
    assert report["status"] == "awaiting_trusted_admission"
    assert report["allowances"]["interface_starts_reserved"] == 2
    before = len(p.broker.store.replay().events)
    assert prepare(p) == value
    assert len(p.broker.store.replay().events) == before
    assert len(p.run.calls) == 2 and len(p.broker.scheduler.host.calls) == 4
    for _, task, prompt in p.broker.scheduler.host.calls:
        assert str(parent.store.root) not in prompt
        assert str(p.manager.qualification_root) not in prompt
        assert "comparison.json" not in prompt


def test_invalid_source_is_captured_before_policy_failure_without_execution(prepared):
    p = prepared
    p.behavior["source"] = b'import os\ndef predict(inputs):\n return {"prediction":1.0}\n'
    value = prepare(p)
    assert value.state == "failed" and value.reason.startswith("source_policy:")
    assert value.capture is not None and value.interface is None and value.bundle is None
    assert not p.run.calls
    assert len(p.broker.controller.state().budget.attempts) == 1
    assert evidence_report(p.broker.store)["status"] == "stopped"


@pytest.mark.parametrize("field", ["base", "evidence"])
def test_fabricated_handoff_bindings_fail_with_bounded_repairs(prepared, field):
    prepared.behavior[field] = "0" * 64
    with pytest.raises(StoreError, match="repair"):
        prepare(prepared)
    assert not prepared.run.calls
    assert not prepared.broker.store.replay().preparations
    assert (
        len(
            [
                i
                for i in prepared.broker.store.replay().invocations.values()
                if i.state == "invalid_output"
            ]
        )
        == 3
    )


def test_preparation_config_cannot_change_on_replay(prepared):
    value = prepare(prepared)
    with pytest.raises(StoreError, match="configuration changed"):
        prepared.manager.prepare(baseline=BASE + b"\n", specification=prepared.run.spec)
    assert prepared.manager.check(value.id) == value
    assert len(prepared.run.calls) == 2


def test_cancellation_after_capture_prevents_interface_launch(prepared):
    store = prepared.broker.store

    def fault(stage):
        if stage == "after_event_commit" and store.replay().preparations:
            store.request_cancel()

    store.fault = fault
    value = prepare(prepared)
    assert value.state == "failed" and value.reason == "cancelled_or_expired_before_checks"
    assert not prepared.run.calls
    assert len(prepared.broker.controller.state().budget.attempts) == 1


def test_interrupted_check_reservation_is_retired_without_a_start(prepared):
    store = prepared.broker.store

    def fault(stage):
        if stage == "after_event_commit" and any(
            v.state == "checking" for v in store.replay().preparations.values()
        ):
            raise OSError("interrupted after check intent")

    store.fault = fault
    with pytest.raises(OSError):
        prepare(prepared)
    store.fault = lambda stage: None
    value = next(iter(store.replay().preparations.values()))
    assert value.state == "checking" and not prepared.run.calls
    with pytest.raises(StoreError, match="source checks"):
        prepared.broker._coordinate("another", "investigator")
    resolved = prepared.manager.check(value.id)
    assert (
        resolved.state == "failed" and resolved.reason == "interrupted_before_checks_not_repeated"
    )
    assert not prepared.run.calls
    assert evidence_report(store)["allowances"]["interface_starts_reserved"] == 2


def test_saved_interface_receipt_recovers_without_new_host_or_container_calls(
    prepared, monkeypatch
):
    recovered_physical(monkeypatch)
    store = prepared.broker.store
    failed = False

    def fault(stage):
        nonlocal failed
        folders = list((store.root / "preparations").glob("*/interface/receipt.json"))
        if not failed and stage == "before_event_commit" and folders:
            failed = True
            raise OSError("lost check acknowledgment")

    store.fault = fault
    value = prepare(prepared)
    assert value.state == "reconciliation_required"
    store.fault = lambda stage: None
    assert prepared.manager.check(value.id).state == "checked"
    assert len(prepared.run.calls) == 2 and len(prepared.broker.scheduler.host.calls) == 4


def test_cancelled_partial_checks_stop_and_never_repeat_completed_cases(prepared, monkeypatch):
    from autoengineering.agents.containers import DockerBoundary

    recovered_physical(monkeypatch)
    original = DockerBoundary.run_qualified

    def cancel(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        prepared.broker.store.request_cancel()
        return result

    monkeypatch.setattr(DockerBoundary, "run_qualified", cancel)
    value = prepare(prepared)
    assert value.state == "reconciliation_required" and len(prepared.run.calls) == 1
    resolved = prepared.manager.check(value.id)
    assert resolved.state == "failed" and resolved.reason == "interrupted_checks_not_repeated"
    assert len(prepared.run.calls) == 1


def test_registration_requires_a_separate_pinned_review(prepared):
    value = prepare(prepared)
    review = review_for(prepared, value)
    with pytest.raises(StoreError, match="pinned approval"):
        prepared.manager.register(
            value.id,
            review=review,
            trusted_review_digest="0" * 64,
            output=prepared.root / "rejected",
        )
    assert not (prepared.root / "rejected").exists()
    assert prepared.broker.store.replay().preparations[value.id].state == "checked"


def test_registration_acknowledgment_recovers_without_rechecking_source(prepared):
    value = prepare(prepared)
    review = review_for(prepared, value)
    root = prepared.root / "registration"
    failed = False

    def fault(stage):
        nonlocal failed
        if (
            stage == "before_event_commit"
            and not failed
            and (root / "generated/registration.json").exists()
        ):
            failed = True
            raise OSError("lost admission acknowledgment")

    prepared.broker.store.fault = fault
    with pytest.raises(OSError):
        prepared.manager.register(
            value.id, review=review, trusted_review_digest=review.digest, output=root
        )
    prepared.broker.store.fault = lambda stage: None
    reg = prepared.manager.register(
        value.id, review=review, trusted_review_digest=review.digest, output=root
    )
    assert prepared.broker.store.replay().preparations[value.id].registration_identity == reg.digest
    assert len(prepared.run.calls) == 2


def test_fork_freezes_new_catalogue_budget_and_lineage_without_parent_mutation(prepared):
    value, review, registration_root, registration = register(prepared)
    parent = prepared.broker.controller
    before = {
        str(p.relative_to(parent.store.root)): p.read_bytes()
        for p in parent.store.root.rglob("*")
        if p.is_file()
    }
    execution = replace(
        parent.spec.execution,
        adapter_ids=(parent.spec.baseline.adapter_id, registration.adapter_id),
        max_executions=2,
    )
    successor = prepared.manager.fork(
        value.id,
        registration_root=registration_root,
        name="linked-fixture",
        execution=execution,
        output=prepared.root / "fork",
    )
    assert successor.spec.acceptance == parent.spec.acceptance
    assert successor.spec.data == parent.spec.data
    assert successor.spec.confirmation == parent.spec.confirmation
    assert successor.spec.execution.max_executions == 2
    assert not successor.state().budget.attempts
    assert successor.store.replay().state == "created"
    assert successor.spec.digest != parent.spec.digest
    link = json.loads((successor.bundle / "generated/origin.json").read_text())
    assert link["originating_campaign_identity"] == prepared.broker.store.spec.campaign_identity
    assert link["originating_proposal"]["id"] == value.candidate_id
    assert link["originating_physical_attempts"] == 1
    assert link["review_digest"] == review.digest
    assert link["registration_identity"] == registration.digest
    assert (
        prepared.manager.fork(
            value.id,
            registration_root=registration_root,
            name="linked-fixture",
            execution=execution,
            output=prepared.root / "fork",
        ).spec
        == successor.spec
    )
    after = {
        str(p.relative_to(parent.store.root)): p.read_bytes()
        for p in parent.store.root.rglob("*")
        if p.is_file()
    }
    assert before == after
    assert len(prepared.run.calls) == 2
    assert evidence_report(prepared.broker.store)["status"] == "successor_created"


def test_fork_requires_new_identity_and_explicit_execution_budget(prepared):
    value, _, root, registration = register(prepared)
    parent = prepared.broker.controller
    for name, execution in (
        (parent.spec.name, parent.spec.execution),
        ("new-campaign", parent.spec.execution),
    ):
        with pytest.raises(StoreError, match="new name|execution budget"):
            prepared.manager.fork(
                value.id,
                registration_root=root,
                name=name,
                execution=execution,
                output=prepared.root / "invalid-fork",
            )
    assert not (prepared.root / "invalid-fork").exists()


def test_fork_lost_acknowledgment_reuses_the_same_unexecuted_campaign(prepared):
    value, _, root, registration = register(prepared)
    parent = prepared.broker.controller
    execution = replace(
        parent.spec.execution,
        adapter_ids=(parent.spec.baseline.adapter_id, registration.adapter_id),
        max_executions=2,
    )
    output = prepared.root / "fork"
    failed = False

    def fault(stage):
        nonlocal failed
        if (
            stage == "before_event_commit"
            and not failed
            and (output / "fork-receipt.json").exists()
        ):
            failed = True
            raise OSError("lost fork acknowledgment")

    prepared.broker.store.fault = fault
    with pytest.raises(OSError):
        prepared.manager.fork(
            value.id,
            registration_root=root,
            name="linked-fixture",
            execution=execution,
            output=output,
        )
    saved = (output / "campaign/identity.json").read_bytes()
    prepared.broker.store.fault = lambda stage: None
    linked = prepared.manager.fork(
        value.id, registration_root=root, name="linked-fixture", execution=execution, output=output
    )
    assert (output / "campaign/identity.json").read_bytes() == saved
    assert not linked.state().budget.attempts
    assert len(prepared.run.calls) == 2
    assert prepared.broker.store.replay().preparations[value.id].state == "forked"


def test_unknown_interface_stop_retains_reservation_and_blocks_new_dispatch(prepared, monkeypatch):
    import autoengineering.agents.preparation as module

    prepared.broker.store.fault = lambda stage: (
        (_ for _ in ()).throw(OSError("interrupted intent"))
        if stage == "after_event_commit"
        and any(v.state == "checking" for v in prepared.broker.store.replay().preparations.values())
        else None
    )
    with pytest.raises(OSError):
        prepare(prepared)
    prepared.broker.store.fault = lambda stage: None
    value = next(iter(prepared.broker.store.replay().preparations.values()))
    # Produce the fixed saved artifacts as an injected interrupted executor.
    workspace, capture, config = prepared.manager._workspace(value)
    from autoengineering.agents.interface import check_interface

    check_interface(
        workspace,
        capture,
        config.specification,
        qualification_root=prepared.manager.qualification_root,
        qualification_digest=prepared.manager.qualification_digest,
        output=workspace.root.parent / "interface",
    )
    monkeypatch.setattr(
        module,
        "reconcile_container",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("ownership unresolved")),
    )
    uncertain = prepared.manager.check(value.id)
    assert uncertain.state == "reconciliation_required"
    assert prepared.manager.check(value.id) == uncertain
    assert len(prepared.run.calls) == 2
    assert evidence_report(prepared.broker.store)["allowances"]["interface_starts_reserved"] == 2
    with pytest.raises(StoreError, match="source checks"):
        prepared.broker._coordinate("new-dispatch", "investigator")


def test_registration_uses_captured_source_after_mutable_workspace_changes(prepared):
    value = prepare(prepared)
    workspace = prepared.broker.store.root / value.workspace
    (workspace / "candidate/adapter.py").write_text("different untested bytes")
    review = review_for(prepared, value)
    root = prepared.root / "registration"
    prepared.manager.register(
        value.id, review=review, trusted_review_digest=review.digest, output=root
    )
    assert (root / "generated/adapter.py").read_bytes() == SOURCE
    assert len(prepared.run.calls) == 2


def test_source_handoff_version_and_admission_claims_are_strict():
    draft = SourceDraft(
        "candidate",
        "a" * 64,
        {"adapter.py": SOURCE.decode()},
        ("python-stdlib", "math"),
        ("b" * 64,),
    )
    with pytest.raises(ValueError):
        SourceDraft.from_dict({**draft.to_dict(), "admitted_identity": "c" * 64})
    with pytest.raises(ValueError, match="version 1.1"):
        RoleHandoff(
            "1.0",
            "handoff",
            "task",
            "invocation",
            "implementer",
            1,
            "complete",
            draft,
            ("b" * 64,),
            (),
            "configure",
        )
    record = RoleHandoff(
        "1.1",
        "handoff",
        "task",
        "invocation",
        "implementer",
        1,
        "complete",
        draft,
        ("b" * 64,),
        (),
        "configure",
    )
    assert RoleHandoff.from_json(record.to_json()) == record


def test_fork_rejects_a_changed_origin_engine_before_writing_new_campaign_files(prepared):
    value, _, root, registration = register(prepared)
    parent = prepared.broker.controller
    sources = tuple(
        replace(ref, sha256="0" * 64)
        if ref.path == "src/autoengineering/campaign/runtime.py"
        else ref
        for ref in parent.spec.provenance.sources
    )
    parent.spec = replace(
        parent.spec,
        provenance=replace(parent.spec.provenance, sources=sources),
        baseline=replace(
            parent.spec.baseline, model=replace(parent.spec.baseline.model, source_bundle=sources)
        ),
    )
    execution = replace(
        parent.spec.execution,
        adapter_ids=(parent.spec.baseline.adapter_id, registration.adapter_id),
        max_executions=2,
    )
    with pytest.raises(ValueError, match="mismatch"):
        prepared.manager.fork(
            value.id,
            registration_root=root,
            name="changed-engine",
            execution=execution,
            output=prepared.root / "rejected-fork",
        )
    assert not (prepared.root / "rejected-fork").exists()


@pytest.mark.parametrize(
    "files", [{"../adapter.py": "pass"}, {"adapter.py": "pass", "test.sh": "echo nope"}]
)
def test_source_response_cannot_choose_paths_or_test_commands(files):
    with pytest.raises(ValueError, match="one adapter"):
        SourceDraft("candidate", "a" * 64, files, ("python-stdlib", "math"), ("b" * 64,))
