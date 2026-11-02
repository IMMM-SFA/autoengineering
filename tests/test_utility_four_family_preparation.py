"""All exposed task families share one immutable prepared source/runtime profile."""

import importlib.util
import os
from pathlib import Path
import platform

import pytest

CACHE = os.environ.get("UTILITY_SOLAR_CACHE")
pytestmark = pytest.mark.skipif(
    not CACHE
    or any(importlib.util.find_spec(n) is None for n in ("pvlib", "py_wake", "openmdao", "optuna")),
    reason="requires common utility runtime and explicit verified solar cache",
)


def test_four_family_preparation_has_one_source_lock_and_no_dispatch(tmp_path, monkeypatch):
    import py_wake.examples.data.hornsrev1  # noqa: F401
    import pvlib  # noqa: F401
    from examples.utility.rehearse_mixed import prepare
    from autoengineering.utility.mixed_execution import ScriptedMixedPlan
    from autoengineering.utility.engineering_execution import TaskEngineeringCampaign
    from autoengineering.campaign.artifacts import read_bytes

    platform.platform()

    def denied(*args, **kwargs):
        raise AssertionError("preparation dispatched physical/network work")

    monkeypatch.setattr("subprocess.Popen", denied)
    monkeypatch.setattr("socket.socket", denied)
    monkeypatch.setattr("examples.utility.wind_parameters.WindGeometry.physical", denied)
    monkeypatch.setattr("examples.utility.wind_proposal.native_layout", denied)
    output, source, plan, store = prepare(tmp_path / "prepared", Path(CACHE), include_wind=True)
    assert ScriptedMixedPlan.from_json(plan.to_json()) == plan
    assert {t.family for t in store.spec.tasks} == {"hydrology", "solar", "engineering", "wind"}
    assert len(store.spec.cells) == 28 and len(store.spec.child_batches()) == 1
    assert not store.replay()["attempts"] and store.replay()["frozen"] is None
    permitted = {r.path for r in (*plan.source_inventory, plan.lock)}
    assert {str(p.relative_to(source)) for p in source.rglob("*") if p.is_file()} == permitted
    for ref in (*plan.source_inventory, plan.lock):
        read_bytes(source, ref)
    for task in plan.campaigns:
        if isinstance(task, TaskEngineeringCampaign):
            assert task.campaign.execution.sources == plan.source_inventory
            assert task.campaign.execution.lock == plan.lock
            assert task.campaign.native.execution == task.campaign.execution
            declared = {r.path: r for r in (*plan.source_inventory, plan.lock)}
            assert all(declared[r.path] == r for r in task.campaign.model.source_bundle)
        else:
            assert task.campaign.provenance.environment_lock == plan.lock
            assert task.campaign.confirmation.mode == "disabled"
    assert (output / "exposure.json").exists()
    with pytest.raises(ValueError, match="absent"):
        prepare(output, Path(CACHE), include_wind=True)


def test_circuit_implementation_label_tracks_actual_dependency(tmp_path):
    from importlib.metadata import version
    from examples.utility.engineering import context

    assert context(0.05, tmp_path).model.implementations["circuit"] == "openmdao-" + version(
        "openmdao"
    )
