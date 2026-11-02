"""Native outer jobs and inner model calls retain distinct evidence and budgets."""

from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.engineering_campaign import (
    EngineeringCampaign,
    EngineeringNativeCampaignSpec,
)
from autoengineering.utility.engineering_native import (
    NativeDriverSpec,
    SupervisedNativeDriver,
    native_cost_records,
    verify_native_report,
)
from autoengineering.utility.engineering_process import (
    SupervisedEngineeringExecutor,
    execution_identity,
)
from test_utility_engineering_campaign import request
from test_utility_engineering_process import setup as execution_setup

NATIVE = """
def native(job):
    from autoengineering.utility.engineering_native import NativeDriverResult, NativeSolveRecord, NativeSolverState
    import time
    if job.specification.max_iterations == 1:
        time.sleep(60)
    if job.specification.max_iterations == 2:
        raise RuntimeError("PRIVATE-NATIVE-CANARY")
    work = NativeSolverState(True,0.,1e-10,"A",2,5,1)
    records = (NativeSolveRecord("driver",None,"shared_problem_snapshot",work),)*2
    records += tuple(NativeSolveRecord("scenario",s.scenario_id,"independent_problem",work) for s in job.specification.execution.scenarios)
    return NativeDriverResult("utility-native-result-v2",job.digest,{"x":.9},job.specification.max_iterations != 3,records,work)
"""


def setup(tmp_path, *, iterations=10, timeout=5.0, fault=lambda _: None):
    original, execution, source = execution_setup(tmp_path)
    path = source / "scenario_fixture.py"
    path.write_text(path.read_text() + NATIVE)
    refs = tuple(
        reference(source, r.path, media_type=r.media_type, producer=r.producer)
        for r in execution.sources
    )
    execution = replace(
        execution,
        sources=refs,
        study=replace(
            execution.study,
            source_identity=execution_identity(
                execution.entrypoint,
                refs,
                execution.lock,
                execution.scenarios,
                execution.timeout_seconds,
                execution.output_bytes,
            ),
        ),
    )
    native = NativeDriverSpec(
        "utility-native-driver-v1",
        execution,
        "scenario_fixture:native",
        iterations,
        6,
        timeout,
        32768,
    )
    runner = SupervisedEngineeringExecutor(execution, original, "first", source)
    driver = SupervisedNativeDriver(native, runner, fault=fault)
    return driver, original, source


def test_native_process_and_inner_calls_are_separate_and_never_redispatched(tmp_path):
    driver, batch, source = setup(tmp_path)
    report = driver.run()
    assert report.status == "success" and len(report.result.solves) == 4
    assert len(batch.replay().reservations) == 1
    reopened = SupervisedNativeDriver(driver.spec, driver.executor)
    assert reopened.run(recover_only=True) == report
    assert len(batch.replay().reservations) == 1
    verify_native_report(batch, "first", driver.spec, report)
    records = native_cost_records(report, "0" * 64)
    assert {r.resource: r.quantity for r in records} == {
        "native_driver_process_starts": 1.0,
        "native_inner_model_calls": 4.0,
        "native_driver_derivative_calls": 1.0,
        "native_driver_final_solver_iterations": 2.0,
        "native_driver_final_component_calls": 5.0,
        "native_scenario_solver_iterations": 4.0,
        "native_scenario_component_calls": 10.0,
        "native_scenario_derivative_calls": 2.0,
    }


def test_native_saved_process_recovers_original_observation(tmp_path):
    def lost(stage):
        if stage == "native_process_saved":
            raise RuntimeError("lost after original process")

    driver, batch, source = setup(tmp_path, fault=lost)
    with pytest.raises(RuntimeError):
        driver.run()
    assert len(batch.replay().pending) == 1
    report = SupervisedNativeDriver(driver.spec, driver.executor).run(recover_only=True)
    assert report.status == "success" and not batch.replay().pending
    assert len(batch.replay().reservations) == 1


def test_unknown_native_start_stays_charged_and_cannot_retry(tmp_path):
    def lost(stage):
        if stage == "native_reserved":
            raise RuntimeError("before process")

    driver, batch, source = setup(tmp_path, fault=lost)
    with pytest.raises(RuntimeError):
        driver.run()
    with pytest.raises((ValueError, OSError)):
        SupervisedNativeDriver(driver.spec, driver.executor).run()
    assert len(batch.replay().reservations) == 1 and batch.replay().pending


@pytest.mark.parametrize(
    "iterations,timeout,status",
    [(1, 1.0, "timeout"), (2, 5.0, "model_failure"), (3, 5.0, "model_failure")],
)
def test_timeout_failure_and_unsuccessful_driver_preserve_unknown_inner_work(
    tmp_path, iterations, timeout, status
):
    driver, batch, source = setup(tmp_path, iterations=iterations, timeout=timeout)
    report = driver.run()
    assert report.status == status
    costs = {r.resource: r.quantity for r in native_cost_records(report, "0" * 64)}
    assert costs["native_driver_process_starts"] == 1
    assert costs["native_inner_model_calls"] == (4 if iterations == 3 else None)
    assert "PRIVATE-NATIVE-CANARY" not in (driver.directory / "process/stderr.bin").read_text()
    assert SupervisedNativeDriver(driver.spec, driver.executor).run(recover_only=True) == report


def test_changed_native_limits_do_not_reuse_another_original_job(tmp_path):
    driver, batch, source = setup(tmp_path)
    driver.run()
    different = SupervisedNativeDriver(replace(driver.spec, max_iterations=11), driver.executor)
    with pytest.raises(StoreError, match="undispatched"):
        different.run(recover_only=True)
    assert len(batch.replay().reservations) == 1


def native_campaign(tmp_path, *, iterations=10, fault=lambda _: None):
    driver, original, source = setup(tmp_path, iterations=iterations)
    # Build the model with the exact newly captured callback reference.
    from autoengineering.campaign.records import ModelSnapshot, PortContract

    execution = driver.spec.execution
    ref = next(r for r in execution.sources if r.path == "scenario_fixture.py")
    model = ModelSnapshot(
        digest({"model": "native-fixture"}),
        {"fixture": "1"},
        (ref,),
        execution.lock.sha256,
        (),
        (PortContract("power", (), "W", "float", (), "scalar", digest({"grid": "scalar"}), None),),
    )
    spec = EngineeringNativeCampaignSpec(
        "utility-engineering-campaign-v2",
        "native-tools",
        execution,
        model,
        {"x": 0.2},
        (),
        12,
        native=driver.spec,
    )
    batch_spec = replace(
        original.spec,
        scientific_starts=spec.scientific_starts,
        cases=(
            replace(original.spec.cases[0], scientific_starts=spec.scientific_starts),
            original.spec.cases[1],
        ),
    )
    batch = BatchStore.create(tmp_path / "native-campaign-batch", batch_spec)
    batch.start_case("first", batch.spec.cases[0].configuration_digest)
    runner = SupervisedEngineeringExecutor(execution, batch, "first", source)
    campaign = EngineeringCampaign.create(tmp_path / "native-campaign", spec, runner, fault=fault)
    return campaign, batch


def test_campaign_native_choice_gets_fresh_checks_and_exact_selection(tmp_path):
    campaign, batch = native_campaign(tmp_path)
    campaign.handle(
        request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="baseline")
    )
    response = campaign.handle(
        request(campaign, "evaluate", {"candidate_id": "native", "mode": "native"}, id="native")
    )
    assert response.result["execution_status"] == "success"
    state = campaign.state()
    assert len(state["evaluations"]) == 2 and len(state["native_reports"]) == 1
    assert state["evaluations"][-1].evaluation.configuration == {"x": 0.9}
    assert len(batch.replay().reservations) == 5  # baseline 2, native outer 1, fresh scenarios 2
    campaign.handle(request(campaign, "review"))
    campaign.handle(request(campaign, "freeze"))
    assert campaign.state()["decision"].outcome == "retain_baseline"  # Original 1 W minimum gain.
    assert EngineeringNativeCampaignSpec.from_json(campaign.spec.to_json()) == campaign.spec


def test_failed_native_driver_commits_failure_without_eligible_candidate(tmp_path):
    campaign, batch = native_campaign(tmp_path, iterations=3)
    campaign.handle(
        request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="baseline")
    )
    response = campaign.handle(
        request(campaign, "evaluate", {"candidate_id": "native", "mode": "native"}, id="native")
    )
    assert response.result["execution_status"] == "model_failure"
    assert len(campaign.state()["evaluations"]) == 1 and len(batch.replay().reservations) == 3
    campaign.handle(request(campaign, "review"))
    campaign.handle(request(campaign, "freeze"))
    assert campaign.state()["selected"].configuration == {"x": 0.2}


def test_native_source_closure_and_undeclared_input_refuse_before_reservation(tmp_path):
    driver, batch, source = setup(tmp_path)
    (source / "undeclared.py").write_text("raise RuntimeError('must not import')")
    with pytest.raises(StoreError, match="undeclared"):
        driver.run()
    assert not batch.replay().reservations


def test_empty_original_job_cannot_be_relaunched_under_a_new_permission(tmp_path):
    driver, batch, source = setup(tmp_path)
    (driver.directory / "job.json").write_text(driver.job.to_json())
    with pytest.raises(StoreError, match="unexplained"):
        driver.run()
    assert not batch.replay().reservations


def test_native_spec_rejects_missing_scenario_allowance_and_counter_scope(tmp_path):
    driver, batch, source = setup(tmp_path)
    with pytest.raises(ValueError):
        replace(driver.spec, max_model_solves=2)
    from autoengineering.utility.engineering_native import NativeSolverState, NativeSolveRecord

    state = NativeSolverState(True, 0.0, 1e-10, "A", 1, 1, 1)
    with pytest.raises(ValueError):
        NativeSolveRecord("driver", None, "independent_problem", state)
    with pytest.raises(ValueError):
        replace(state, converged=True, residual_norm=1.0)
    assert not batch.replay().reservations


def test_actual_native_circuit_recipe_enforces_inner_call_ceiling(tmp_path, monkeypatch):
    import importlib.util

    if importlib.util.find_spec("openmdao") is None:
        pytest.skip("optional OpenMDAO environment required")
    from examples.utility import engineering

    original_factory = engineering.factory
    actual = []

    def counted_factory(ctx):
        problem = original_factory(ctx)
        run = problem.model.run_solve_nonlinear

        def counted(*args, **kwargs):
            actual.append("model call")
            return run(*args, **kwargs)

        problem.model.run_solve_nonlinear = counted
        return problem

    monkeypatch.setattr(engineering, "factory", counted_factory)
    with pytest.raises(RuntimeError, match="solve budget exhausted"):
        engineering.native_design((-0.05, 0.0, 0.05), 0.62, tmp_path, max_solves=4)
    assert len(actual) == 1


def test_legacy_native_result_preserves_identity_without_invented_final_counters(tmp_path):
    from autoengineering.utility.engineering_native import NativeDriverResultV1, NativeDriverReport

    driver, batch, source = setup(tmp_path)
    current = driver.run()
    value = current.result
    legacy = NativeDriverResultV1(
        "utility-native-result-v1",
        value.job_digest,
        value.configuration,
        value.driver_success,
        value.solves,
    )
    report = replace(current, result=legacy)
    decoded = NativeDriverReport.from_json(report.to_json())
    assert decoded.digest == report.digest and decoded.result.schema == "utility-native-result-v1"
    costs = {r.resource: r.quantity for r in native_cost_records(decoded, "0" * 64)}
    assert costs["native_driver_derivative_calls"] is None
    assert costs["native_inner_model_calls"] == 4
    with pytest.raises(StoreError, match="original observed bytes"):
        verify_native_report(batch, "first", driver.spec, decoded)


def test_native_campaign_partial_followup_never_restarts_driver(tmp_path):
    def lost(stage):
        if stage == "native_observed":
            raise RuntimeError("after native job before fresh scenarios")

    campaign, batch = native_campaign(tmp_path, fault=lost)
    campaign.handle(
        request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"}, id="baseline")
    )
    original = request(
        campaign, "evaluate", {"candidate_id": "native", "mode": "native"}, id="native"
    )
    with pytest.raises(RuntimeError, match="after native job"):
        campaign.handle(original)
    assert len(batch.replay().reservations) == 3 and not batch.replay().pending
    reopened = EngineeringCampaign(campaign.store.root, batch, executor=campaign.executor)
    with pytest.raises(StoreError, match="undispatched"):
        reopened.handle(original)
    assert len(batch.replay().reservations) == 3
    assert reopened.handle(original, resume_scenarios=True).status == "ok"
    assert len(batch.replay().reservations) == 5
    assert len([r for r in batch.replay().reservations if r.startswith("native-")]) == 1
