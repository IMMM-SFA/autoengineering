"""CLI source recovery must not dispatch or extend a frozen scientific campaign."""

import json

from click.testing import CliRunner
import pytest

from autoengineering.agents.store import WorkerStore
from autoengineering.cli import cli
from test_agent_interface import run as run
from test_agent_preparation import prepared as prepared, prepare, recovered_physical


def resume(p, *, qualification=True):
    arguments = [
        "agents",
        "resume",
        str(p.broker.store.root),
        "--campaign",
        str(p.broker.controller.store.root),
        "--max-new-evaluations",
        "0",
    ]
    if qualification:
        arguments += ["--qualification-root", str(p.manager.qualification_root)]
    return CliRunner().invoke(cli, arguments)


def interrupt_checks(p):
    failed = False
    store = p.broker.store

    def fault(stage):
        nonlocal failed
        if (
            stage == "before_event_commit"
            and not failed
            and list((store.root / "preparations").glob("*/interface/receipt.json"))
        ):
            failed = True
            raise OSError("lost interface acknowledgment")

    store.fault = fault
    value = prepare(p)
    store.fault = lambda stage: None
    assert value.state == "reconciliation_required"
    return value


def forbid_new_work(monkeypatch):
    from autoengineering.agents.hosts.fake import FakeHost
    from autoengineering.agents.containers import DockerBoundary
    from autoengineering.campaign.controller import CampaignController

    def forbidden(*args, **kwargs):
        pytest.fail("source recovery cannot dispatch a host or launch new physical work")

    monkeypatch.setattr(FakeHost, "invoke", forbidden)
    monkeypatch.setattr(DockerBoundary, "run_qualified", forbidden)
    monkeypatch.setattr(CampaignController, "_physical", forbidden)


def test_cli_recovers_saved_source_checks_without_new_calls_or_parent_events(prepared, monkeypatch):
    value = interrupt_checks(prepared)
    recovered_physical(monkeypatch)
    forbid_new_work(monkeypatch)
    parent = prepared.broker.controller
    before = {
        str(path.relative_to(parent.store.root)): path.read_bytes()
        for path in parent.store.root.rglob("*")
        if path.is_file()
    }
    result = resume(prepared)
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "awaiting_trusted_admission"
    assert report["pending_source_preparations"] == []
    assert report["allowances"]["invocations_used"] == 4
    assert report["allowances"]["interface_starts_reserved"] == 2
    assert report["physical_work"]["attempts"] == 1
    assert prepared.broker.store.replay().preparations[value.id].state == "checked"
    assert len(prepared.run.calls) == 2
    assert before == {
        str(path.relative_to(parent.store.root)): path.read_bytes()
        for path in parent.store.root.rglob("*")
        if path.is_file()
    }
    saved_events = len(prepared.broker.store.replay().events)
    repeated = resume(prepared, qualification=False)
    assert repeated.exit_code == 0, repeated.output
    assert len(WorkerStore(prepared.broker.store.root).replay().events) == saved_events


def test_missing_qualification_leaves_pending_state_and_reports_required_input(
    prepared, monkeypatch
):
    value = interrupt_checks(prepared)
    forbid_new_work(monkeypatch)
    before = len(prepared.broker.store.replay().events)
    result = resume(prepared, qualification=False)
    assert result.exit_code == 4, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "reconciliation_required"
    assert report["pending_source_preparations"] == [value.id]
    assert "--qualification-root" in report["workflow_stop"]
    assert len(prepared.broker.store.replay().events) == before
    status = CliRunner().invoke(cli, ["agents", "status", str(prepared.broker.store.root)])
    assert json.loads(status.stdout)["pending_source_preparations"] == [value.id]


def test_wrong_qualification_does_not_change_the_stored_pin(prepared, monkeypatch):
    import autoengineering.agents.preparation as module

    value = interrupt_checks(prepared)
    forbid_new_work(monkeypatch)
    original = prepared.broker.store.replay().preparations[value.id]

    def reject(*args, **kwargs):
        raise ValueError("qualification receipt differs from the trusted digest")

    monkeypatch.setattr(module, "verify_qualification", reject)
    result = resume(prepared)
    assert result.exit_code == 4, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "reconciliation_required"
    assert "trusted digest" in report["workflow_stop"]
    assert prepared.broker.store.replay().preparations[value.id] == original


def test_unresolved_owned_stop_remains_pending_and_keeps_its_allowance(prepared, monkeypatch):
    import autoengineering.agents.preparation as module

    value = interrupt_checks(prepared)
    forbid_new_work(monkeypatch)

    def unresolved(*args, **kwargs):
        raise ValueError("container ownership inspection remains unresolved")

    monkeypatch.setattr(module, "reconcile_container", unresolved)
    result = resume(prepared)
    assert result.exit_code == 4, result.output
    report = json.loads(result.stdout)
    assert report["pending_source_preparations"] == [value.id]
    assert report["allowances"]["interface_starts_reserved"] == 2
    assert report["allowances"]["invocations_used"] == 4
    assert len(prepared.run.calls) == 2


def test_interrupted_intent_is_retired_without_repeating_interface_work(prepared, monkeypatch):
    store = prepared.broker.store

    def fault(stage):
        if stage == "after_event_commit" and any(
            v.state == "checking" for v in store.replay().preparations.values()
        ):
            raise OSError("interrupted before first check")

    store.fault = fault
    with pytest.raises(OSError):
        prepare(prepared)
    store.fault = lambda stage: None
    forbid_new_work(monkeypatch)
    result = resume(prepared)
    assert result.exit_code == 4, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "stopped"
    assert report["pending_source_preparations"] == []
    assert report["source_preparations"][0]["reason"] == "interrupted_before_checks_not_repeated"
    assert report["allowances"]["interface_starts_reserved"] == 2
    assert not prepared.run.calls


def test_source_recovery_does_not_require_original_scientific_source_availability(
    prepared, monkeypatch
):
    interrupt_checks(prepared)
    recovered_physical(monkeypatch)
    forbid_new_work(monkeypatch)
    identity_path = prepared.broker.controller.store.root / "identity.json"
    # The digest remains unchanged. Only the original location is offline.
    identity = json.loads(identity_path.read_text())
    identity["source_root"] = str(prepared.root / "offline-original-source")
    identity_path.write_text(json.dumps(identity))
    result = resume(prepared)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == "awaiting_trusted_admission"
    assert prepared.broker.controller.store.replay().state == "candidate_pending"


def test_checked_preparation_replay_needs_no_qualification_or_new_calls(prepared, monkeypatch):
    value = prepare(prepared)
    forbid_new_work(monkeypatch)
    before = {
        str(path.relative_to(prepared.broker.store.root)): path.read_bytes()
        for path in prepared.broker.store.root.rglob("*")
        if path.is_file()
    }
    result = resume(prepared, qualification=False)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["status"] == "awaiting_trusted_admission"
    assert before == {
        str(path.relative_to(prepared.broker.store.root)): path.read_bytes()
        for path in prepared.broker.store.root.rglob("*")
        if path.is_file()
    }
    assert prepared.broker.store.replay().preparations[value.id] == value


def capture_only(p):
    store = p.broker.store

    def fault(stage):
        if stage == "after_event_commit" and any(
            v.state == "captured" for v in store.replay().preparations.values()
        ):
            raise OSError("interrupted after capture")

    store.fault = fault
    with pytest.raises(OSError):
        prepare(p)
    store.fault = lambda stage: None
    assert not p.run.calls


def test_resume_can_start_provably_unlaunched_checks_within_the_original_allowance(
    prepared, monkeypatch
):
    from autoengineering.agents.hosts.fake import FakeHost
    from autoengineering.campaign.controller import CampaignController

    capture_only(prepared)

    def forbidden(*args, **kwargs):
        pytest.fail("captured-source resume cannot launch host or scientific work")

    monkeypatch.setattr(FakeHost, "invoke", forbidden)
    monkeypatch.setattr(CampaignController, "_physical", forbidden)
    result = resume(prepared)
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "awaiting_trusted_admission"
    assert report["allowances"]["interface_starts_reserved"] == 2
    assert len(prepared.run.calls) == 2
    assert report["physical_work"]["attempts"] == 1
    assert resume(prepared).exit_code == 0
    assert len(prepared.run.calls) == 2


def test_cancelled_capture_does_not_start_checks_when_cli_resumes(prepared, monkeypatch):
    capture_only(prepared)
    prepared.broker.store.request_cancel()
    forbid_new_work(monkeypatch)
    result = resume(prepared)
    assert result.exit_code == 4, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "cancel_queued"
    assert report["pending_source_preparations"] == []
    assert report["allowances"]["interface_starts_reserved"] == 0
    assert not prepared.run.calls
