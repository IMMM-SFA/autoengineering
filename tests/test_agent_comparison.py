"""Frozen three-route synthetic comparison, ordering, shared science and recovery."""

from dataclasses import replace
from itertools import repeat
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from autoengineering.agents.hosts.base import HostResult
from autoengineering.agents.batch import BatchStore
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.hosts.scripted import supplied_reply, single_supplied_reply
from autoengineering.agents.records import CandidateBrief, NextStep, RoleHandoff, WorkerInvocation
from autoengineering.agents.scheduler import SerialScheduler
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.store import WriterBusy
from examples.agent_campaign import comparison as comp
from examples.agent_campaign import prepare_leafriver as leaf
from examples.agent_campaign import synthetic_comparison as synthetic


def snapshot(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    base = tmp_path_factory.mktemp("matched-driver")
    parent = leaf.prepare(base / "leaf")
    with pytest.MonkeyPatch.context() as patch:
        import subprocess
        from examples.campaign_contracts.hydrology import HydrologyAdapter

        def forbidden(*args, **kwargs):
            raise AssertionError("preparation attempted execution")

        patch.setattr(subprocess, "Popen", forbidden)
        patch.setattr(CampaignController, "create", forbidden)
        patch.setattr(HydrologyAdapter, "prepare", forbidden)
        plan = synthetic.prepare(
            base / "leaf",
            leaf_digest=parent.digest,
            output=base / "proposal",
            runtime_root=base / "runtime",
        )
        assert comp.load(base / "proposal", expected_digest=plan.digest) == plan
    return base / "proposal", plan


def fork(prepared, tmp_path):
    original, plan = prepared
    root = tmp_path / "proposal"
    shutil.copytree(original, root)
    plan = replace(plan, runtime_root=str(tmp_path / "runtime"))
    (root / "comparison.json").write_text(plan.to_json())
    return root, plan


def test_preparation_captures_only_synthetic_data_and_fixed_allowances(prepared):
    root, plan = prepared
    assert comp.ComparisonPreparation.from_json(plan.to_json()) == plan
    assert [c.id for c in plan.cases] == list(leaf.ROUTES)
    assert [c.worker.workflow_route for c in plan.cases] == [
        "four_role",
        "single_agent",
        "four_role",
    ]
    assert all(c.worker.limits == leaf.LIVE_LIMITS for c in plan.cases)
    assert all(c.host_invocations == 0 and c.scientific_starts == 38 for c in plan.batch.cases)
    assert plan.batch.scientific_starts == 114
    assert not Path(plan.runtime_root).exists()
    assert not any("/data/" in r.path or "/profile/" in r.path for r in plan.inputs)
    for case in plan.cases:
        spec = CampaignSpec.from_yaml(root / case.scientific.path)
        assert spec.scientific_scope == synthetic.SCOPE
        assert all(p.grid_id == synthetic.GRID for p in spec.baseline.model.inputs)
        assert all(d.prior_exposure == "exposed" for d in spec.data)
        assert spec.baseline.model.inputs[0].time.dates[0] == "2001-01-01"
    before = snapshot(root)
    assert comp.load(root, expected_digest=plan.digest) == plan
    assert snapshot(root) == before


@pytest.mark.parametrize("change", ["pin", "driver", "input", "seed", "allowance", "runtime"])
def test_changed_bindings_fail_before_runtime_creation(prepared, tmp_path, change):
    root, plan = fork(prepared, tmp_path)
    pin = plan.digest
    if change == "pin":
        pin = "0" * 64
    elif change == "driver":
        (root / plan.driver_sources[0].path).write_bytes(b"changed")
    elif change == "input":
        (root / plan.inputs[0].path).write_bytes(b"changed")
    elif change == "runtime":
        Path(plan.runtime_root).mkdir(mode=0o700)
    elif change == "allowance":
        value = plan.to_dict()
        value["batch"]["scientific_starts"] = 115
        (root / "comparison.json").write_text(canonical_json(value))
        pin = digest(value)
    else:
        case = plan.cases[0]
        spec = CampaignSpec.from_yaml(root / case.scientific.path)
        replace(spec, seed=18).to_yaml(root / case.scientific.path)
        case = replace(
            case,
            scientific=reference(
                root,
                case.scientific.path,
                media_type="application/yaml",
                producer="comparison-preparation",
            ),
        )
        plan = replace(
            plan,
            cases=(case, *plan.cases[1:]),
            batch=replace(plan.batch, cases=comp.batch_cases((case, *plan.cases[1:]))),
        )
        (root / "comparison.json").write_text(plan.to_json())
        pin = plan.digest
    with pytest.raises((ValueError, OSError)):
        comp.Runtime.create(root, expected_digest=pin)


@pytest.mark.parametrize("route", ["four_role", "single_agent"])
@pytest.mark.parametrize("mistake", ["id", "order", "freeze", "eligibility"])
def test_order_and_early_freeze_errors_consume_repairs_before_fitting(
    prepared, tmp_path, route, mistake
):
    root, plan = prepared
    case = next(c for c in plan.cases if c.id == route)
    controller = CampaignController.create(
        root / case.scientific.path,
        root / "captured_source",
        tmp_path / "campaign",
        max_new_evaluations=1,
    )
    worker = WorkerStore.create(tmp_path / "worker", case.worker)
    base = single_supplied_reply if route == "single_agent" else supplied_reply
    altered = []

    def reply(task, prompt, invocation_id):
        result = base(task, prompt, invocation_id)
        handoff = RoleHandoff.from_json(result.raw_output)
        if isinstance(handoff.output, CandidateBrief):
            envelope = json.loads(prompt[prompt.index('{"approved_evidence"') :])
            summary = json.loads(envelope["approved_evidence"][0]["content"])
            policy = summary["comparison_policy"]
            assert policy["next_proposal_candidate_id"] == comp.CANDIDATES[0]
            assert policy["proposed_candidate_ids"] == []
            assert policy["baseline_counts_as_proposal"] is False
            assert summary["evaluations"]  # The evaluated baseline has not consumed a proposal.
            properties = envelope["output_contract"]["schema"]["$defs"]["CandidateBrief"][
                "properties"
            ]
            assert properties["candidate_id"]["const"] == comp.CANDIDATES[0]
            assert "after proposal" in properties["eligibility_gaps"]["description"]
        if not altered and (
            (mistake == "freeze" and task.role in ("orchestrator", "single_agent"))
            or isinstance(handoff.output, CandidateBrief)
        ):
            if mistake == "freeze":
                handoff = replace(
                    handoff,
                    output=NextStep("freeze", None, "Authored early freeze"),
                    proposed_next_action="freeze",
                )
            else:
                brief = handoff.output
                brief = (
                    replace(brief, candidate_id="unfair-id")
                    if mistake == "id"
                    else replace(brief, eligibility_gaps=("source prerequisite absent",))
                    if mistake == "eligibility"
                    else replace(brief, implementation_id="hargreaves-v1")
                )
                handoff = replace(handoff, output=brief)
            altered.append(invocation_id)
        return replace(result, raw_output=handoff.to_json())

    host = FakeHost(repeat(reply))
    broker_type = (
        comp.MatchedSingleAgentBroker if route == "single_agent" else comp.MatchedFourRoleBroker
    )
    broker_type(controller, SerialScheduler(worker, host)).advance()
    calls = worker.replay().invocations
    assert len(altered) == 1 and calls[altered[0]].state == "invalid_output"
    assert len(controller.state().budget.attempts) == 1
    assert [p.id for p in controller.state().proposals] == [comp.CANDIDATES[0]]
    assert controller.state().proposals[0].implementation_id == "hamon-v1"
    assert worker.replay().repairs_used == 1


def test_runtime_lock_rejects_competing_driver_before_science(prepared, tmp_path):
    root, plan = fork(prepared, tmp_path)
    runtime = comp.Runtime.create(root, expected_digest=plan.digest)
    other = comp.Runtime.open(
        root, expected_digest=plan.digest, runtime_digest=runtime.batch.digest
    )
    with runtime.batch._lock(".comparison-operation.lock"):
        with pytest.raises(WriterBusy):
            other.advance()
    assert runtime.batch.report()["scientific_reservations_charged"] == 0


def test_completed_worker_ack_recovers_without_repeating_the_call(prepared, tmp_path, monkeypatch):
    root, plan = fork(prepared, tmp_path)
    runtime = comp.Runtime.create(root, expected_digest=plan.digest)
    commit = WorkerStore.commit
    lost = []

    def losing(self, value):
        result = commit(self, value)
        if isinstance(value, WorkerInvocation) and value.state == "completed" and not lost:
            lost.append(value.id)
            raise RuntimeError("authored committed worker acknowledgment loss")
        return result

    monkeypatch.setattr(WorkerStore, "commit", losing)
    with pytest.raises(RuntimeError, match="acknowledgment loss"):
        runtime.advance(max_new_evaluations=1)
    monkeypatch.setattr(WorkerStore, "commit", commit)
    before = WorkerStore(runtime.batch.root / "cases/scripted/worker").replay()
    assert before.invocations[lost[0]].state == "completed"
    physical_calls = []
    invoke = FakeHost.invoke

    def spy(self, task, prompt, **kwargs):
        physical_calls.append(kwargs["invocation_id"])
        return invoke(self, task, prompt, **kwargs)

    monkeypatch.setattr(FakeHost, "invoke", spy)
    recovered = comp.Runtime.open(
        root, expected_digest=plan.digest, runtime_digest=runtime.batch.digest
    )
    recovered.advance(max_new_cases=1, max_new_evaluations=1)
    assert lost[0] not in physical_calls
    assert recovered.batch.report()["scientific_reservations_charged"] == 2


def test_full_three_route_accounting_pause_replay_and_reports(
    prepared, tmp_path, monkeypatch, capsys
):
    root, plan = fork(prepared, tmp_path)
    runtime = comp.Runtime.create(root, expected_digest=plan.digest)
    first = runtime.advance(max_new_cases=1, max_new_evaluations=1)
    assert first["scientific_reservations_charged"] == 1 and first["active_case"] == "scripted"
    assert not first["route_verdicts"]
    old_clock = runtime.batch.created_at
    original_control = snapshot(runtime.batch.root / "cases/scripted/artifacts")
    runtime = comp.Runtime.open(
        root, expected_digest=plan.digest, runtime_digest=runtime.batch.digest
    )
    first = runtime.advance(max_new_cases=1)
    assert first["case_results"] == {"scripted": "passed"}
    assert first["scientific_reservations_charged"] == 38
    assert snapshot(runtime.batch.root / "cases/scripted/artifacts") == original_control
    final = runtime.advance()
    assert final["status"] == "completed" and not final["pending_reservations"]
    assert final["created_at"] == old_clock and final["scientific_reservations_charged"] == 114
    assert final["host_reservations_charged"] == 0 and not final["live_comparison_complete"]
    assert final["native_worker_interruption"] == "not_attempted"
    verdicts = final["route_verdicts"]
    assert [verdicts[r]["logical_host_calls"] for r in leaf.ROUTES] == [13, 7, 13]
    for value in verdicts.values():
        assert value["passed"] and value["scientific_starts"] == 38
        assert value["candidate_order"] == list(comp.CANDIDATES)
        assert value["confirmation"] == "confirmation_not_attempted"
        assert value["physical_provider_calls"] == 0
        assert (
            value["invalid_candidate_control"]["reason"] == "candidate topology/interface differs"
        )
        assert value["invalid_candidate_control"]["scientific_starts"] == 0
        assert len(value["comparison_and_diagnostic_evaluations"]) == 6
    for route in leaf.ROUTES:
        worker = WorkerStore(runtime.batch.root / "cases" / route / "worker")
        proposals = []
        for call in worker.replay().invocations.values():
            if call.normalized_output is None:
                continue
            handoff = RoleHandoff.from_json(read_bytes(worker.root, call.normalized_output).decode())
            if not isinstance(handoff.output, CandidateBrief):
                continue
            prompt = read_bytes(worker.root, call.prompt).decode()
            envelope = json.loads(prompt[prompt.index('{"approved_evidence"') :])
            policy = json.loads(envelope["approved_evidence"][0]["content"])["comparison_policy"]
            assert policy["proposed_candidate_ids"] == proposals
            assert policy["next_proposal_candidate_id"] == handoff.output.candidate_id
            proposals.append(handoff.output.candidate_id)
        assert proposals == list(comp.CANDIDATES)
    evidence = [verdicts[r]["scientific_evidence"] for r in leaf.ROUTES]
    for field in ("selected_configuration", "objective_value", "outcome"):
        assert evidence[0][field] == evidence[1][field] == evidence[2][field]
    before = snapshot(runtime.batch.root)
    monkeypatch.setattr(
        "sys.argv",
        [
            "comparison",
            "resume",
            "--preparation",
            str(root),
            "--preparation-digest",
            runtime.pin,
            "--runtime-digest",
            runtime.batch.digest,
        ],
    )
    assert comp.main() == 0
    cli = capsys.readouterr()
    assert json.loads(cli.out) == final
    assert json.loads(cli.err.splitlines()[-1])["execution_delta"] == {
        "scientific_reservations_added": 0,
        "logical_invocations_added": 0,
        "finished_verdicts_reused": 3,
    }

    def forbidden(*args, **kwargs):
        raise AssertionError("replay attempted new work or private arrays")

    monkeypatch.setattr(FakeHost, "invoke", forbidden)
    monkeypatch.setattr("numpy.load", forbidden)
    assert comp.report(runtime.batch, runtime.pin) == final
    assert runtime.advance() == final
    assert snapshot(runtime.batch.root) == before
    for what in ("receipt", "input"):
        copy = tmp_path / f"corrupt-{what}"
        shutil.copytree(runtime.batch.root, copy)
        control_path = copy / "cases/scripted/invalid-interface.json"
        control = json.loads(control_path.read_text())
        target = (
            control_path
            if what == "receipt"
            else copy / "cases/scripted" / control["invalid_snapshot"]["path"]
        )
        target.write_bytes(b"changed")
        with pytest.raises((ValueError, OSError)):
            comp.report(BatchStore(copy, expected_digest=runtime.batch.digest), runtime.pin)


@pytest.mark.parametrize("route", ["four_role", "single_agent"])
def test_explicit_stop_is_preserved_without_repair(prepared, tmp_path, route):
    root, plan = prepared
    case = next(c for c in plan.cases if c.id == route)
    controller = CampaignController.create(
        root / case.scientific.path,
        root / "captured_source",
        tmp_path / "campaign",
        max_new_evaluations=1,
    )
    worker = WorkerStore.create(tmp_path / "worker", case.worker)

    def stop(task, prompt, invocation_id):
        output = RoleHandoff(
            "1.2" if route == "single_agent" else "1.0",
            f"stop-{invocation_id}",
            task.id,
            invocation_id,
            task.role,
            task.campaign_revision,
            "complete",
            NextStep("stop", None, "Authored deliberate stop"),
            (),
            (),
            "stop",
        )
        return HostResult("completed", output.to_json(), None, {}, 0)

    host = FakeHost(repeat(stop))
    cls = comp.MatchedSingleAgentBroker if route == "single_agent" else comp.MatchedFourRoleBroker
    from autoengineering.agents.broker import WorkflowStopped

    with pytest.raises(WorkflowStopped):
        cls(controller, SerialScheduler(worker, host)).advance()
    assert len(host.calls) == 1 and worker.replay().repairs_used == 0
    assert list(worker.replay().invocations.values())[0].state == "completed"
    assert len(controller.state().budget.attempts) == 1
    assert not controller.state().proposals


def test_unresolved_worker_is_visible_and_blocks_further_calls(prepared, tmp_path):
    root, plan = fork(prepared, tmp_path)
    runtime = comp.Runtime.create(root, expected_digest=plan.digest)
    case = plan.cases[0]
    runtime.batch.start_case(case.id, case.configuration_digest)
    host = FakeHost(
        repeat(HostResult("reconciliation_required", "", None, {}, None, stop_verified=False))
    )
    assert runtime._case(case, max_new_evaluations=1, host=host) is None
    value = comp.report(runtime.batch, runtime.pin)
    assert value["status"] == "reconciliation_required"
    assert value["active_worker_report"]["pending_invocations"]
    assert len(host.calls) == 1 and value["scientific_reservations_charged"] == 1
    before = snapshot(runtime.batch.root)
    from autoengineering.campaign.store import StoreError

    with pytest.raises(StoreError, match="unresolved"):
        runtime._case(case, max_new_evaluations=1, host=host)
    assert len(host.calls) == 1
    assert snapshot(runtime.batch.root) == before


def test_changed_negative_control_receipt_is_not_reexecuted(prepared, tmp_path):
    root, plan = fork(prepared, tmp_path)
    runtime = comp.Runtime.create(root, expected_digest=plan.digest)
    runtime.advance(max_new_cases=1, max_new_evaluations=1)
    path = runtime.batch.root / "cases/scripted/invalid-interface.json"
    receipt = json.loads(path.read_text())
    receipt["host_calls"] = 99
    path.write_text(json.dumps(receipt))
    from autoengineering.campaign.store import StoreError

    with pytest.raises(StoreError, match="control changed"):
        runtime.advance(max_new_cases=1, max_new_evaluations=1)
    assert runtime.batch.report()["scientific_reservations_charged"] == 1


def test_invalid_cli_pause_does_not_start_a_runtime(prepared, tmp_path, monkeypatch):
    root, plan = fork(prepared, tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "comparison",
            "run",
            "--preparation",
            str(root),
            "--preparation-digest",
            plan.digest,
            "--max-new-evaluations",
            "0",
        ],
    )
    with pytest.raises(SystemExit) as error:
        comp.main()
    assert error.value.code == 2 and not Path(plan.runtime_root).exists()
