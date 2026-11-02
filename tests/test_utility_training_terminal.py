"""Actual failed registered fits retain charges and offline terminal evidence."""

import json
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.utility.campaign_costs import join_campaign_costs
from autoengineering.utility.training_terminal import TerminalTrainingEvidence
from test_utility_campaign_training_costs import setup, CELL


def terminal(controller):
    evaluation = controller.state().evaluations[0]
    ref = next(
        r
        for e in controller.store.replay().events
        for r in e.artifacts
        if r.sha256 == evaluation.provenance["training_terminal_record"]
    )
    return ref, TerminalTrainingEvidence.from_json(read_bytes(controller.store.root, ref).decode())


@pytest.mark.parametrize("recover", [False, True])
def test_actual_failed_fit_keeps_original_work_and_recovers_without_relaunch(
    tmp_path, monkeypatch, recover
):
    batch, controller = setup(tmp_path, monkeypatch, registered=True, cap=3, recover=recover)
    assert controller.state().evaluations[0].status == "model_failure"
    ref, evidence = terminal(controller)
    assert evidence.disposition == "captured" and evidence.fit is None
    assert evidence.intent is not None and evidence.result is not None
    costs = join_campaign_costs(batch, {"model": CELL})
    values = {r.resource: r.quantity for r in costs}
    assert values["campaign_process_starts"] == values["training_starts"] == 1
    assert values["training_routing_starts"] == values["training_routing_completions"] == 3
    assert values["training_completed_routing_days"] == 240
    assert values["training_elapsed"] > 0
    assert batch.report()["scientific_reservations_charged"] == 1
    before = batch.replay()
    controller.reconcile_batch()
    assert batch.replay() == before
    assert join_campaign_costs(batch, {"model": CELL}) == costs
    assert len(controller.state().budget.attempts) == 1
    assert ref.producer == controller.state().evaluations[0].attempt_id


@pytest.mark.parametrize("loss", ["missing", "corrupt"])
def test_stopped_worker_receipt_loss_stays_unknown_or_invalid(tmp_path, monkeypatch, loss):
    import autoengineering.campaign.controller as module

    original = module.supervise

    def authored_loss(command, **kwargs):
        result = original(command, **kwargs)
        assert result.status == "model_failure" and result.stopped
        job = json.loads(Path(command[-1]).read_text())
        path = Path(job["context"]["scratch_path"]) / "training-result.json"
        assert path.is_file()
        if loss == "missing":
            path.unlink()
        else:
            path.write_text("authored loss of receipt bytes")
        return result

    monkeypatch.setattr(module, "supervise", authored_loss)
    batch, controller = setup(tmp_path, monkeypatch, registered=True, cap=3)
    _, evidence = terminal(controller)
    if loss == "missing":
        values = {r.resource: r.quantity for r in join_campaign_costs(batch, {"model": CELL})}
        assert values["training_starts"] == 1
        assert values["training_routing_starts"] is None and values["training_elapsed"] is None
        assert evidence.disposition == "captured" and evidence.result is None
    else:
        assert evidence.disposition == "invalid" and evidence.result is not None
        assert (
            read_bytes(controller.store.root, evidence.result) == b"authored loss of receipt bytes"
        )
        with pytest.raises(ValueError, match="invalid"):
            join_campaign_costs(batch, {"model": CELL})
    assert batch.report()["scientific_reservations_charged"] == 1


def test_terminal_costs_relocate_without_scratch_sources_labels_or_execution(tmp_path, monkeypatch):
    batch, controller = setup(tmp_path, monkeypatch, registered=True, cap=3)
    expected = join_campaign_costs(batch, {"model": CELL})
    copied = tmp_path / "copied"
    shutil.copytree(batch.root, copied)
    campaign = copied / controller.store.root.relative_to(batch.root)
    shutil.rmtree(campaign / "bundle")
    shutil.rmtree(campaign / "jobs")
    script = """
import importlib.abc,json,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.agents.batch import BatchStore
from autoengineering.utility.campaign_costs import join_campaign_costs
import scipy.optimize,subprocess,socket,os
def forbidden(*args,**kwargs):raise AssertionError('execution attempted')
scipy.optimize.least_squares=scipy.optimize.minimize=subprocess.Popen=socket.socket=forbidden
root=Path(sys.argv[1]);allowed={p for p in root.rglob('*') if p.is_file()}
old=Path.open;old_os=os.open
def guarded(path,*args,**kwargs):
 if path not in allowed:raise AssertionError('ungranted read')
 return old(path,*args,**kwargs)
def guarded_os(path,flags,*args,**kwargs):
 if Path(path) not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):raise AssertionError('ungranted read/write')
 return old_os(path,flags,*args,**kwargs)
Path.open=guarded;os.open=guarded_os
print(json.dumps([r.to_dict() for r in join_campaign_costs(BatchStore(root),{'model':'1'*64})]))
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(copied)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert json.loads(process.stdout) == [r.to_dict() for r in expected]
    assert join_campaign_costs(BatchStore(copied), {"model": CELL}) == expected


def test_terminal_artifact_corruption_refuses_accounting(tmp_path, monkeypatch):
    batch, controller = setup(tmp_path, monkeypatch, registered=True, cap=3)
    ref, evidence = terminal(controller)
    expected = join_campaign_costs(batch, {"model": CELL})
    for artifact in (ref, *evidence.references()):
        path = controller.store.root / artifact.path
        raw = path.read_bytes()
        path.write_bytes(b"authored corruption")
        try:
            with pytest.raises(ValueError):
                join_campaign_costs(batch, {"model": CELL})
        finally:
            path.write_bytes(raw)
    assert join_campaign_costs(batch, {"model": CELL}) == expected


def test_successful_fit_cost_survives_a_later_model_failure(tmp_path, monkeypatch):
    import test_utility_hydrology_learned as models

    original = models.fixture

    def invalid_later_forcing(*args, **kwargs):
        site, profile, context, forcing, fitting, truth = original(*args, **kwargs)
        forcing["precip_mm"][-1] = -1.0
        return site, profile, context, forcing, fitting, truth

    monkeypatch.setattr(models, "fixture", invalid_later_forcing)
    batch, controller = setup(tmp_path, monkeypatch, registered=True)
    assert controller.state().evaluations[0].status == "model_failure"
    _, evidence = terminal(controller)
    assert evidence.disposition == "captured" and evidence.fit is not None
    costs = join_campaign_costs(batch, {"model": CELL})
    assert next(r.quantity for r in costs if r.resource == "training_starts") == 1
    assert next(r.quantity for r in costs if r.resource == "training_routing_completions") > 3


def test_recovery_refuses_conflicting_original_supervisor_proof(tmp_path, monkeypatch):
    import autoengineering.campaign.controller as module

    original = module.CampaignController._checkpoint
    saved = {}

    class AuthoredLoss(BaseException):
        pass

    def lost(self, target, state, reason, artifacts=()):
        if reason == "action_finished":
            saved["controller"] = self
            raise AuthoredLoss()
        return original(self, target, state, reason, artifacts)

    monkeypatch.setattr(module.CampaignController, "_checkpoint", lost)
    with pytest.raises(AuthoredLoss):
        setup(tmp_path, monkeypatch, registered=True, cap=3)
    monkeypatch.setattr(module.CampaignController, "_checkpoint", original)
    controller = saved["controller"]
    path = controller.store.root / "attempts/attempt-000001/supervisor-result.json"
    proof = json.loads(path.read_text())
    variants = [
        dict(proof, stopped=False),
        dict(proof, status="success"),
        dict(proof, elapsed_seconds=-1),
        dict(proof, identity=dict(proof["identity"], nonce="forged")),
        dict(proof, identity=dict(proof["identity"], pid=-1, pgid=-1)),
    ]
    monkeypatch.setattr(module, "supervise", lambda *_a, **_k: pytest.fail("recovery relaunched"))
    for value in variants:
        path.write_text(json.dumps(value))
        controller.recover()
        assert controller.state().budget.unresolved_attempts == 1
        assert not controller.state().evaluations
        assert len(controller.batch.replay().pending) == 1
    path.write_text(json.dumps(proof))
    controller.reconcile_batch()
    assert controller.state().budget.unresolved_attempts == 0
    assert len(controller.state().evaluations) == 1
    assert controller.batch.report()["scientific_reservations_charged"] == 1


@pytest.mark.parametrize("recover", [False, True])
def test_actual_timeout_keeps_unknown_unfinished_training_and_one_charge(
    tmp_path, monkeypatch, recover
):
    batch, controller = setup(tmp_path, monkeypatch, registered=True, timeout=0.1, recover=recover)
    assert controller.state().evaluations[0].status == "timeout"
    _, evidence = terminal(controller)
    assert evidence.disposition == "captured"
    costs = join_campaign_costs(batch, {"model": CELL})
    assert any(r.quantity is None and "training" in r.resource for r in costs)
    assert batch.report()["scientific_reservations_charged"] == 1
    assert len(controller.state().budget.attempts) == 1


def test_terminal_costs_cannot_borrow_permission_or_work_from_later_events(tmp_path, monkeypatch):
    from autoengineering.utility.campaign_costs import _campaign, _terminal_training
    from autoengineering.campaign.store import StoreError

    batch, controller = setup(tmp_path, monkeypatch, registered=True, cap=3)
    observation = next(iter(batch.replay().observations.values()))
    document = json.loads(read_bytes(batch.root, observation.evidence[0]))
    campaign = _campaign(batch, "model", document)
    evaluation = controller.state().evaluations[0]
    _, evidence = terminal(controller)
    for operation, missing in (
        ("action_reserved", evidence.grant),
        ("action_finished", evidence.result),
    ):
        index = next(
            i
            for i, event in enumerate(campaign.events)
            if event.operation == operation and missing in event.artifacts
        )
        original = campaign.events[index]
        altered = replace(original, artifacts=tuple(r for r in original.artifacts if r != missing))
        events = (*campaign.events[:index], altered, *campaign.events[index + 1 :], original)
        with pytest.raises(StoreError, match="original"):
            _terminal_training(replace(campaign, events=events), evaluation, CELL)
