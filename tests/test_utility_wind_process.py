"""Owned wind driver jobs retain callback types and original recovery evidence."""

from dataclasses import replace
from pathlib import Path

import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.store import StoreError
from autoengineering.optimization import ContinuousParameter, ObjectiveSpec, SearchSpace
from autoengineering.utility.engineering_process import (
    EngineeringScenario,
    SupervisedEngineeringExecutor,
    execution_identity,
)
from examples.utility.wind_parameters import WindGeometry
from examples.utility.wind_process import (
    SupervisedWindDriver,
    WindDriverSpec,
    WindDriverReport,
    verify_report,
)
from examples.utility.wind_proposal import WindNativeSpec
from examples.utility.wind_scenario import GEOMETRY_PATH, rules
from test_utility_engineering_process import setup as process_setup

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = """
def driver(job):
    import time
    from examples.utility.wind_native import NativeCall, NativeWindResult
    from examples.utility.wind_proposal import WindNativeProposal
    from examples.utility.wind_process import WindDriverResult
    spec = job.specification.native
    if spec.maximum_iterations == 1:
        time.sleep(60)
    if spec.maximum_iterations == 2:
        raise RuntimeError("PRIVATE-WIND-CANARY")
    x, y = spec.geometry.x, spec.geometry.y
    exhausted = spec.maximum_iterations == 3
    calls = (NativeCall("wake", 1, "completed", x, y, 1.0),
             NativeCall("gradient", 1, "failed", x, y, None))
    raw = NativeWindResult("budget_exhausted" if exhausted else "not_converged",
        False, not exhausted, x, y, calls, spec.maximum_wake_calls,
        spec.maximum_gradient_calls, spec.maximum_iterations)
    proposal = WindNativeProposal("utility-wind-native-proposal-v1", spec, raw)
    return WindDriverResult("utility-wind-driver-result-v1", job.digest, proposal)
"""


def setup(tmp_path, *, iterations=5, timeout=8.0, fault=lambda _: None):
    batch, execution, source = process_setup(tmp_path)
    geometry = WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0))
    names = [r.path for r in execution.sources]
    names += [
        "examples/utility/" + n
        for n in (
            "__init__.py",
            "wind.py",
            "wind_native.py",
            "wind_parameters.py",
            "wind_scenario.py",
            "wind_proposal.py",
            "wind_process.py",
        )
    ]
    for name in names:
        if name.startswith("examples/"):
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
    (source / "inputs").mkdir()
    (source / GEOMETRY_PATH).write_text(geometry.to_json())
    (source / "wind_fixture.py").write_text(FIXTURE)
    names += [GEOMETRY_PATH, "wind_fixture.py"]
    refs = tuple(
        reference(source, n, media_type="text/plain", producer="authored-fixture") for n in names
    )
    run = replace(
        execution.study.run,
        study=replace(
            execution.study.run.study, objective=ObjectiveSpec("annual_energy", "maximize")
        ),
        search_space=SearchSpace(
            tuple(ContinuousParameter(n, *b) for n, b in geometry.bounds.items())
        ),
    )
    scenarios = (EngineeringScenario("bundled-distribution", {"direction_step": 30.0}),)
    identity = execution_identity(
        execution.entrypoint,
        refs,
        execution.lock,
        scenarios,
        execution.timeout_seconds,
        execution.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        execution,
        schema="utility-engineering-execution-v2",
        sources=refs,
        scenarios=scenarios,
        study=replace(
            execution.study,
            run=run,
            rules=rules(),
            scenario_ids=(scenarios[0].scenario_id,),
            source_identity=identity,
        ),
    )
    spec = WindDriverSpec(
        "utility-wind-driver-v1",
        execution,
        WindNativeSpec("utility-wind-native-spec-v1", geometry, iterations, 12, 4),
        "wind_fixture:driver",
        timeout,
        32768,
    )
    executor = SupervisedEngineeringExecutor(execution, batch, "first", source)
    return SupervisedWindDriver(spec, executor, fault=fault), batch, source


def test_original_wind_process_recovery_has_no_new_charge(tmp_path):
    driver, batch, _ = setup(tmp_path)
    report = driver.run()
    assert report.status == "success"
    assert report.result.proposal.eligibility == "fresh_evaluation_required"
    assert report.result.proposal.work["wake"]["completed"] == 1
    assert report.result.proposal.work["gradient"]["failed"] == 1
    assert WindDriverReport.from_json(report.to_json()) == report
    assert SupervisedWindDriver(driver.spec, driver.executor).run(recover_only=True) == report
    verify_report(batch, "first", driver.spec, report)
    assert len(batch.replay().reservations) == len(batch.replay().observations) == 1
    assert not batch.replay().pending


def test_wind_saved_process_is_recovered_before_observation(tmp_path):
    def lost(stage):
        if stage == "native_process_saved":
            raise RuntimeError("owner lost")

    driver, batch, _ = setup(tmp_path, fault=lost)
    with pytest.raises(RuntimeError, match="owner lost"):
        driver.run()
    assert len(batch.replay().pending) == 1
    report = SupervisedWindDriver(driver.spec, driver.executor).run(recover_only=True)
    assert report.status == "success" and len(batch.replay().reservations) == 1
    assert not batch.replay().pending


@pytest.mark.parametrize(
    "iterations, status", [(1, "timeout"), (2, "model_failure"), (3, "model_failure")]
)
def test_wind_failure_is_stopped_charged_and_not_retried(tmp_path, iterations, status):
    driver, batch, _ = setup(
        tmp_path, iterations=iterations, timeout=0.05 if iterations == 1 else 8.0
    )
    report = driver.run()
    assert report.status == status and report.stop_verified
    assert driver.run(recover_only=True) == report
    assert len(batch.replay().reservations) == 1 and not batch.replay().pending
    if iterations == 3:
        assert report.result.proposal.configuration is None
        assert report.result.proposal.work["gradient"]["failed"] == 1
    assert "PRIVATE-WIND-CANARY" not in report.to_json()


def test_wind_reserved_without_launch_does_not_get_a_retry(tmp_path):
    def lost(stage):
        if stage == "native_reserved":
            raise RuntimeError("before launch")

    driver, batch, _ = setup(tmp_path, fault=lost)
    with pytest.raises(RuntimeError, match="before launch"):
        driver.run()
    with pytest.raises(StoreError):
        SupervisedWindDriver(driver.spec, driver.executor).run(recover_only=True)
    assert len(batch.replay().reservations) == len(batch.replay().pending) == 1


def test_changed_wind_source_is_rejected_before_reservation(tmp_path, monkeypatch):
    driver, batch, source = setup(tmp_path)

    def denied(*args, **kwargs):
        raise AssertionError("changed source launched work")

    monkeypatch.setattr("autoengineering.utility.engineering_native.supervise_process", denied)
    (source / GEOMETRY_PATH).write_text("changed")
    with pytest.raises((StoreError, ValueError)):
        driver.run()
    assert not batch.replay().reservations


def test_callback_costs_do_not_invent_inner_work_or_unknown_counts(tmp_path):
    from examples.utility.wind_process import cost_records

    driver, batch, _ = setup(tmp_path)
    report = driver.run()
    costs = {r.resource: r.quantity for r in cost_records(report, "0" * 64)}
    assert costs["wind_native_process_starts"] == 1
    assert costs["wind_native_wake_callbacks_attempted"] == 1
    assert costs["wind_native_gradient_callbacks_failed"] == 1
    assert not any("inner" in name or "residual" in name for name in costs)
    unknown = {
        r.resource: r.quantity
        for r in cost_records(replace(report, status="model_failure", result=None), "0" * 64)
    }
    assert unknown["wind_native_wake_callbacks_attempted"] is None
    verify_report(batch, "first", driver.spec, report)
    with pytest.raises(StoreError):
        verify_report(
            batch, "first", driver.spec, replace(report, reservation_id="unknown-original")
        )


def test_false_job_or_cap_result_is_not_accepted(tmp_path):
    from examples.utility.wind_process import validate_result

    driver, _, _ = setup(tmp_path)
    report = driver.run()
    with pytest.raises(ValueError, match="job"):
        validate_result(driver.job, replace(report.result, job_digest="f" * 64))
    proposal = report.result.proposal
    changed = replace(proposal.specification, maximum_wake_calls=13)
    changed_raw = replace(proposal.result, maximum_wake_calls=13)
    altered = replace(proposal, specification=changed, result=changed_raw)
    with pytest.raises(ValueError, match="limits"):
        validate_result(driver.job, replace(report.result, proposal=altered))


def test_offline_wind_report_rejects_changed_original_stdout(tmp_path):
    driver, batch, _ = setup(tmp_path)
    report = driver.run()
    path = driver.directory / "process/stdout.bin"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises((StoreError, ValueError)):
        verify_report(batch, "first", driver.spec, report)
    assert len(batch.replay().reservations) == 1
