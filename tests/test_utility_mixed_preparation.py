"""Real exposed task preparation produces a frozen proposal without dispatch."""

from pathlib import Path
import importlib.util
import os

import pytest

CACHE = os.environ.get("UTILITY_SOLAR_CACHE")
pytestmark = pytest.mark.skipif(
    not CACHE or importlib.util.find_spec("pvlib") is None,
    reason="requires explicit verified exposed OEDI cache and optional pvlib",
)


def test_three_family_preparation_is_source_closed_and_starts_nothing(tmp_path, monkeypatch):
    from examples.utility.rehearse_mixed import prepare
    from autoengineering.utility.mixed_execution import ScriptedMixedPlan
    from autoengineering.utility.engineering_execution import TaskEngineeringCampaign
    from autoengineering.campaign.artifacts import read_bytes

    pytest.importorskip("pvlib")  # Dependency import may inspect the CPU through uname.
    import platform

    platform.platform()  # Cache dependency metadata before denying all process dispatch.

    def denied(*args, **kwargs):
        raise AssertionError("Preparation attempted process or network dispatch")

    monkeypatch.setattr("subprocess.Popen", denied)
    monkeypatch.setattr("socket.socket", denied)
    output, source, plan, store = prepare(tmp_path / "prepared", Path(CACHE))
    assert ScriptedMixedPlan.from_json(plan.to_json()) == plan
    assert {t.family for t in store.spec.tasks} == {"hydrology", "solar", "engineering"}
    assert len(store.spec.cells) == 21 and len(store.spec.child_batches()) == 1
    assert len(store.spec.routes) == 7
    assert not store.replay()["attempts"] and store.replay()["frozen"] is None
    permitted = {ref.path for ref in (*plan.source_inventory, plan.lock)}
    actual = {str(p.relative_to(source)) for p in source.rglob("*") if p.is_file()}
    assert actual == permitted
    for ref in (*plan.source_inventory, plan.lock):
        read_bytes(source, ref)
    for task in plan.campaigns:
        if isinstance(task, TaskEngineeringCampaign):
            assert task.campaign.execution.schema.endswith("v2")
            assert task.campaign.execution.sources == plan.source_inventory
        else:
            assert task.campaign.confirmation.mode == "disabled"
            assert all(d.prior_exposure == "exposed" for d in task.campaign.data)
            assert task.campaign.provenance.environment_lock == plan.lock
            # Qualify the exact JSON boundary used by the mixed coordinator.
            from autoengineering.campaign.controller import CampaignController

            path = output / (task.task_id + "-input.json")
            path.write_text(task.campaign.to_json())
            controller = CampaignController.create(
                path, source, output / (task.task_id + "-controller")
            )
            assert controller.spec == task.campaign
            assert not controller.state().budget.attempts
    with pytest.raises(ValueError, match="absent"):
        prepare(output, Path(CACHE))
    assert not store.replay()["attempts"]
