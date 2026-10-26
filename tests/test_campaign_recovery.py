"""Recover real interrupted broker processes without rewriting optimization ledgers."""

import json
import subprocess
import sys

from autoengineering.campaign.controller import CampaignController
from autoengineering.optimization import ObservationLedger
from examples.campaign_contracts.build_fixture import ROOT
from test_campaign_studies import calibrated_spec


CODE = """
import os,sys
from pathlib import Path
from autoengineering.campaign.controller import CampaignController
c = CampaignController.create(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
mode = sys.argv[4]
def fault(stage):
    p = c.store.replay()
    if not p.events:
        return
    last = p.events[-1]
    state = c.state(p)
    if mode == 'output' and stage == 'before_staging' and last.operation == 'action_reserved':
        os._exit(77)
    if mode == 'child' and stage == 'before_acknowledgment' and last.operation == 'action_finished' and state.budget.attempts[-1].child_action_id:
        os._exit(77)
c.store.fault = fault
c.advance()
"""


def test_saved_worker_result_before_campaign_commit_is_reused(tmp_path):
    path = ROOT / "examples/campaign_contracts/fixture.yaml"
    work = tmp_path / "campaign"
    process = subprocess.run(
        [sys.executable, "-c", CODE, str(path), str(ROOT), str(work), "output"]
    )
    assert process.returncode == 77
    controller = CampaignController.open(work)
    assert controller.state().budget.unresolved_attempts == 1
    assert controller.advance().state == "completed"
    assert len(controller.state().budget.attempts) == 2  # Baseline reused, one candidate start.
    assert controller.state().outcome == "accepted_candidate"
    assert controller.state().budget.unresolved_attempts == 0


def test_saved_fitting_result_before_child_ack_preserves_selection(tmp_path):
    path = tmp_path / "input.yaml"
    calibrated_spec().to_yaml(path)
    work = tmp_path / "campaign"
    process = subprocess.run([sys.executable, "-c", CODE, str(path), str(ROOT), str(work), "child"])
    assert process.returncode == 77
    controller = CampaignController.open(work)
    state = controller.state()
    assert len(state.budget.attempts) == 2
    assert state.budget.unresolved_attempts == 0
    assert controller.advance().state == "completed"
    assert len(controller.state().budget.attempts) == 5
    link = controller.state().studies[0]
    ledger = ObservationLedger(work / link.work_path / "observations.jsonl")
    entries = ledger.entries()
    assert len(entries) == 3
    assert all(result.status.value == "success" for _, result in entries)
    fitting = [item for item in controller.state().evaluations if item.split_id == "fitting"]
    assert len(fitting) == 3
    assert entries[0][1].outcomes["rmse"] == fitting[0].metrics["rmse"]


def test_unknown_child_attempt_keeps_allowance_when_child_recovers_zero_cost(tmp_path):
    path = tmp_path / "input.yaml"
    calibrated_spec().to_yaml(path)
    work = tmp_path / "campaign"
    code = CODE.replace(
        "if mode == 'child' and stage == 'before_acknowledgment' and last.operation == 'action_finished'",
        "if mode == 'child' and stage == 'before_acknowledgment' and last.operation == 'action_reserved'",
    )
    process = subprocess.run([sys.executable, "-c", code, str(path), str(ROOT), str(work), "child"])
    assert process.returncode == 77
    controller = CampaignController.open(work)
    assert controller.advance().state == "reconciliation_required"
    state = controller.state()
    unknown = state.budget.attempts[-1]
    assert unknown.uncertain_cost
    assert state.budget.unresolved_attempts == 1
    response = controller.request("review", {"reconcile_attempt_id": unknown.id})
    assert response.status == "ok"
    assert controller.advance().state == "completed"
    state = controller.state()
    entries = ObservationLedger(work / state.studies[0].work_path / "observations.jsonl").entries()
    assert entries[0][1].status.value == "infrastructure_failure"
    assert entries[0][1].cost == 0
    assert len(state.budget.attempts) == 5
    assert state.budget.attempts[1].uncertain_cost
    assert state.budget.attempts[1].measured_cost is None
    assert state.budget.confirmed_attempts == 4


def test_dead_supervisor_leaves_owned_group_uncertain_until_a_verified_stop(tmp_path, monkeypatch):
    import time
    import autoengineering.campaign.execution as execution

    code = """
from dataclasses import replace
from pathlib import Path
import sys
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.records import AttemptRecord
from autoengineering.campaign.execution import supervise
c = CampaignController.create(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
with c.store.writer():
    s = c.state()
    a = AttemptRecord('attempt-000001', 'fixed-baseline', 'launched', None, 'owned-test-nonce', None, None, True, None)
    b = s.budget.reserve('fixed-baseline', 1).start(a)
    c._checkpoint('evaluating', replace(s, budget=b, active_mode='fixed'), 'action_reserved')
    supervise((sys.executable, '-c', 'import time; time.sleep(30)'), root=c.store.root,
              attempt_id=a.id, campaign_id=c.spec.name, settings=c.spec.execution,
              cwd=Path.cwd(), launch_nonce=a.launch_nonce)
"""
    work = tmp_path / "campaign"
    parent = subprocess.Popen(
        [
            sys.executable,
            "-c",
            code,
            str(ROOT / "examples/campaign_contracts/fixture.yaml"),
            str(ROOT),
            str(work),
        ]
    )
    identity = None
    try:
        receipt = work / "attempts/attempt-000001/process.json"
        started = work / "attempts/attempt-000001/action-start.json"
        deadline = time.monotonic() + 10
        while not receipt.exists() or not started.exists():
            assert time.monotonic() < deadline
            assert parent.poll() is None
            time.sleep(0.02)
        identity = execution.ProcessIdentity(**json.loads(receipt.read_text()))
        parent.kill()
        parent.wait(timeout=5)
        controller = CampaignController.open(work)
        assert controller.advance().state == "reconciliation_required"
        assert execution.live_members(identity.pgid)
        controller.cancel("stop-orphan")
        with monkeypatch.context() as patcher:
            patcher.setattr(execution, "stop_recovered", lambda *args: False)
            assert controller.advance().state == "reconciliation_required"
            assert execution.live_members(identity.pgid)
        assert controller.advance().state == "completed"
        assert controller.state().outcome == "cancelled"
        assert not execution.live_members(identity.pgid)
        assert controller.state().budget.attempts[0].measured_cost is None
        assert controller.state().budget.attempts[0].uncertain_cost
        assert len(controller.state().budget.attempts) == 1
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=5)
        if identity is not None and execution.identity_matches(identity):
            execution.stop_recovered(identity, execution.ExecutionSpec(("test",)))


def test_duplicate_command_while_running_cannot_launch_a_second_attempt(tmp_path):
    import time
    from autoengineering.campaign.records import Request, Response
    from autoengineering.campaign.store import WriterBusy

    code = """
import json,subprocess,sys
from pathlib import Path
import autoengineering.campaign.controller as module
from autoengineering.campaign.controller import CampaignController
original = module.supervise
def delayed(command, **kwargs):
    delay = 'import subprocess,sys,time; time.sleep(2); sys.exit(subprocess.call(sys.argv[1:]))'
    return original((sys.executable, '-c', delay, *command), **kwargs)
module.supervise = delayed
c = CampaignController.create(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
print(c.request('evaluate', {'candidate_id':'baseline','mode':'fixed'}, request_id='same-command').to_json(), flush=True)
"""
    work = tmp_path / "campaign"
    parent = subprocess.Popen(
        [
            sys.executable,
            "-c",
            code,
            str(ROOT / "examples/campaign_contracts/fixture.yaml"),
            str(ROOT),
            str(work),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        ready = work / "attempts/attempt-000001/process.json"
        deadline = time.monotonic() + 10
        while not ready.exists():
            assert time.monotonic() < deadline and parent.poll() is None
            time.sleep(0.02)
        controller = CampaignController.open(work)
        request = Request(
            "1.0",
            controller.spec.name,
            "same-command",
            0,
            "evaluate",
            {"candidate_id": "baseline", "mode": "fixed"},
        )
        import pytest

        with pytest.raises(WriterBusy):
            controller.service.handle(request)
        stdout, stderr = parent.communicate(timeout=15)
        assert parent.returncode == 0, stderr
        first = Response.from_json(stdout.strip())
        assert controller.service.handle(request) == first
        assert len(controller.state().budget.attempts) == 1
        assert controller.state().budget.measured_cost == 1
    finally:
        if parent.poll() is None:
            parent.kill()
            parent.wait(timeout=5)
