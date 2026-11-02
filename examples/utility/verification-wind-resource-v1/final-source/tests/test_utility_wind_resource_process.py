"""Explicit-resource native jobs retain source, budget and original replay bindings."""

from dataclasses import replace
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.agents.batch import BatchStore
from autoengineering.optimization import EvaluationAction
from autoengineering.campaign.store import StoreError
from autoengineering.utility.engineering_process import (
    EngineeringScenario,
    SupervisedEngineeringExecutor,
    execution_identity,
)
from examples.utility.wind_process import WindDriverSpec, SupervisedWindDriver, verify_report
from examples.utility.wind_proposal import WindNativeSpec
from examples.utility.wind_resource import RESOURCE_PATH
from examples.utility.wind_scenario import GEOMETRY_PATH
from test_utility_wind_process import setup as legacy_setup
from test_utility_wind_resource import resource, geometry

ROOT = Path(__file__).resolve().parents[1]


def setup(tmp_path, *, actual=False, fault=lambda _: None):
    old, batch, source = legacy_setup(tmp_path, iterations=5, timeout=20.0)
    (source / GEOMETRY_PATH).write_text(geometry().to_json())
    (source / RESOURCE_PATH).write_text(resource().to_json())
    (source / "pixi.lock").write_bytes((ROOT / "pixi.lock").read_bytes())
    fixture = source / "wind_fixture.py"
    fixture.write_text(
        fixture.read_text().replace(
            "utility-wind-native-proposal-v1", "utility-wind-native-proposal-v2"
        )
    )
    names = [r.path for r in old.spec.execution.sources]
    names += [
        old.spec.execution.lock.path,
        "pixi.lock",
        RESOURCE_PATH,
        "examples/utility/wind_resource.py",
        "examples/utility/wind_resource_scenario.py",
        "examples/open_chains/__init__.py",
        "examples/open_chains/wind/__init__.py",
        "examples/open_chains/wind/models.py",
    ]
    for name in names:
        if name.startswith("examples/"):
            path = source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
    refs = tuple(
        reference(source, name, media_type="text/plain", producer="authored-resource")
        for name in names
    )
    scenarios = (EngineeringScenario("supplied-resource", {"direction_step": 90.0}),)
    entrypoint = "examples.utility.wind_resource_scenario:execute"
    old_execution = old.spec.execution
    lock = reference(source, "pixi.lock", media_type="text/plain", producer="pixi")
    identity = execution_identity(
        entrypoint,
        refs,
        lock,
        scenarios,
        old_execution.timeout_seconds,
        old_execution.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        old_execution,
        lock=lock,
        entrypoint=entrypoint,
        sources=refs,
        scenarios=scenarios,
        study=replace(
            old_execution.study, source_identity=identity, scenario_ids=("supplied-resource",)
        ),
    )
    native = WindNativeSpec(
        "utility-wind-native-spec-v2", geometry(), 2 if actual else 5, 12, 4, resource().digest
    )
    spec = WindDriverSpec(
        "utility-wind-driver-v2",
        execution,
        native,
        "examples.utility.wind_process:run_driver" if actual else "wind_fixture:driver",
        20.0,
        32768,
    )
    # A new execution identity needs a fresh journal. Do not replace the legacy
    # fixture executor's already-bound execution metadata.
    batch = BatchStore.create(tmp_path / "resource-batch", batch.spec)
    batch.start_case("first", batch.spec.cases[0].configuration_digest)
    executor = SupervisedEngineeringExecutor(execution, batch, "first", source)
    return SupervisedWindDriver(spec, executor, fault=fault), batch, source


@pytest.mark.parametrize("lost_ack", [False, True])
def test_resource_driver_original_replay_and_bounded_observation(tmp_path, lost_ack):
    def fault(stage):
        if lost_ack and stage == "native_process_saved":
            raise RuntimeError("lost resource observation")

    driver, batch, _ = setup(tmp_path, fault=fault)
    if lost_ack:
        with pytest.raises(RuntimeError):
            driver.run()
        report = SupervisedWindDriver(driver.spec, driver.executor).run(recover_only=True)
    else:
        report = driver.run()
    assert report.status == "success" and report.stop_verified
    assert report.result.proposal.schema == "utility-wind-native-proposal-v2"
    assert report.result.proposal.specification.resource_digest == resource().digest
    verify_report(batch, "first", driver.spec, report)
    assert SupervisedWindDriver(driver.spec, driver.executor).run(recover_only=True) == report
    assert len(batch.replay().reservations) == len(batch.replay().observations) == 1
    assert not batch.replay().pending


def test_changed_resource_or_mixed_protocol_refuses_before_physical_start(tmp_path):
    driver, batch, source = setup(tmp_path)
    with pytest.raises(ValueError):
        replace(driver.spec, schema="utility-wind-driver-v1")
    with pytest.raises(ValueError):
        replace(driver.spec, execution=replace(driver.spec.execution, entrypoint="other:execute"))
    (source / RESOURCE_PATH).write_text("{}")
    with pytest.raises((ValueError, StoreError)):
        driver.run()
    assert not batch.replay().reservations


@pytest.mark.skipif(importlib.util.find_spec("topfarm") is None, reason="optional wind runtime")
def test_real_native_resource_objective_matches_fresh_resource_evaluation(tmp_path):
    driver, batch, _ = setup(tmp_path, actual=True)
    report = driver.run()
    assert report.status == "success" and report.result.proposal.configuration is not None
    for call in report.result.proposal.result.calls:
        if call.kind == "wake" and call.status == "completed":
            np.testing.assert_allclose(
                call.energy_gwh, np.sum(resource().evaluate(call.x, call.y)[0]), rtol=1e-10
            )
    assert any(c.kind == "gradient" for c in report.result.proposal.result.calls)
    before = len(batch.replay().reservations)
    assert SupervisedWindDriver(driver.spec, driver.executor).run(recover_only=True) == report
    assert len(batch.replay().reservations) == before
    action = EvaluationAction(
        "fresh-resource",
        report.result.proposal.configuration,
        "system",
        None,
        seed=17,
        suggested_by="resource-native-test",
    )
    fresh = driver.executor(action)
    assert fresh.evaluation.status == "success" and fresh.evaluation.eligible
    assert len(batch.replay().reservations) == before + 1
    assert driver.executor.recover_completed(action) == fresh
    assert len(batch.replay().reservations) == before + 1
