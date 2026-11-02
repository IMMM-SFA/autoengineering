"""Shared science reservations over the original trusted scalar campaign."""

from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchCase, BatchStore
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.campaign.store import StoreError
from examples.agent_campaign.fixture import agent_fixture
from examples.campaign_contracts.build_fixture import ROOT
from test_agent_batch import H, specification


def fixture(tmp_path, *, science=2):
    tmp_path.chmod(0o700)
    spec = replace(
        specification(science=science), cases=(BatchCase("model", "comparison", H, 0, science),)
    )
    batch = BatchStore.create(tmp_path / "batch", spec)
    batch.start_case("model", H)
    root = batch.root / "cases/model"
    root.mkdir(mode=0o700)
    source = root / "scientific.yaml"
    agent_fixture().to_yaml(source)
    controller = BatchCampaignController.create(
        source, ROOT, root / "campaign", batch=batch, case_id="model"
    )
    return batch, controller


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_actual_scientific_decision_and_replay_preserve_shared_start_count(tmp_path):
    batch, controller = fixture(tmp_path)
    assert controller.advance().state == "completed"
    assert controller.state().outcome == "accepted_candidate"
    assert len(controller.state().budget.attempts) == 2
    assert batch.report()["scientific_reservations_charged"] == 2 and not batch.replay().pending
    before = snapshot(batch.root)
    assert controller.advance().state == "completed"
    assert before == snapshot(batch.root)


def test_reopening_controller_cannot_reset_batch_scientific_allowance(tmp_path):
    batch, controller = fixture(tmp_path, science=1)
    controller.remaining = 1
    controller.advance()
    assert len(controller.state().budget.attempts) == 1
    other = BatchCampaignController.open(
        controller.store.root, batch=batch, case_id="model", max_new_evaluations=2
    )
    with pytest.raises(StoreError, match="allowance exhausted"):
        other.advance()
    assert len(other.state().budget.attempts) == 1
    assert batch.report()["scientific_reservations_charged"] == 1


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_observation_fault_recovers_without_another_scientific_start(tmp_path, stage):
    batch, controller = fixture(tmp_path)

    def fault(point):
        if point == stage and controller.state().evaluations:
            raise RuntimeError("authored science batch acknowledgment loss")

    batch.fault = fault
    controller.remaining = 1
    # The campaign marks its existing attempt uncertain when the outer observer
    # loses its acknowledgment. No later physical work is permitted by the batch.
    try:
        controller.advance()
    except RuntimeError:
        pass
    assert len(controller.state().budget.attempts) == 1
    batch.fault = lambda _: None
    before = snapshot(controller.store.root / "attempts")
    reopened = BatchCampaignController.open(controller.store.root, batch=batch, case_id="model")
    reopened.reconcile_batch()
    assert len(reopened.state().budget.attempts) == 1
    assert not batch.replay().pending
    assert snapshot(controller.store.root / "attempts") == before
