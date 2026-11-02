"""Callback proposals enter shared campaigns without synthetic solver diagnostics."""

from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ModelSnapshot, PortContract
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.callback_native import (
    CallbackCall,
    CallbackDriverSpec,
    CallbackDriverResult,
    CallbackDriverReport,
    SupervisedCallbackDriver,
    validate_callback_result,
)
from autoengineering.utility.engineering_campaign import (
    EngineeringCallbackCampaignSpec,
    EngineeringCampaign,
)
from autoengineering.utility.engineering_execution import TaskEngineeringCampaign
from autoengineering.utility.engineering_native import native_cost_records, verify_native_report
from autoengineering.utility.engineering_process import (
    SupervisedEngineeringExecutor,
    execution_identity,
)
from test_utility_engineering_campaign import request
from test_utility_engineering_process import setup as execution_setup

FIXTURE = """
def callback(job):
    import time
    import json
    from autoengineering.utility.callback_native import CallbackCall, CallbackDriverResult
    mode = json.loads(job.specification.options_json)["mode"]
    if mode == "timeout":
        time.sleep(60)
    if mode == "error":
        raise RuntimeError("PRIVATE-CALLBACK-CANARY")
    calls = (CallbackCall("wake", 1, "completed", {"x": .9}, {"power": 1.}, {"power":"W"}),
             CallbackCall("gradient", 1, "completed", {"x": .9}, {}, {}))
    if mode == "overflow":
        calls += tuple(CallbackCall("wake", i, "completed", {"x": .9}, {}, {}) for i in (2,3))
    failed = mode == "exhausted"
    return CallbackDriverResult("utility-callback-result-v1", job.digest,
        "budget_exhausted" if failed else "converged", not failed, not failed,
        {"x": .9}, None if failed else {"x": .9}, calls, job.specification.callback_limits)
"""


def setup(tmp_path, mode="success", *, timeout=6.0, fault=lambda _: None):
    batch, execution, source = execution_setup(tmp_path)
    path = source / "scenario_fixture.py"
    path.write_text(path.read_text() + FIXTURE)
    refs = tuple(
        reference(source, r.path, media_type=r.media_type, producer=r.producer)
        for r in execution.sources
    )
    identity = execution_identity(
        execution.entrypoint,
        refs,
        execution.lock,
        execution.scenarios,
        execution.timeout_seconds,
        execution.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        execution,
        schema="utility-engineering-execution-v2",
        sources=refs,
        study=replace(execution.study, source_identity=identity),
    )
    spec = CallbackDriverSpec(
        "utility-callback-driver-v1",
        execution,
        "scenario_fixture:callback",
        canonical_json({"mode": mode}),
        {"wake": 2, "gradient": 2},
        timeout,
        32768,
    )
    executor = SupervisedEngineeringExecutor(execution, batch, "first", source)
    return SupervisedCallbackDriver(spec, executor, fault=fault), batch, source


def test_callback_original_process_receipt_recovery_and_costs(tmp_path, monkeypatch):
    driver, batch, _ = setup(tmp_path)
    report = driver.run()
    assert report.status == "success" and report.result.configuration == {"x": 0.9}
    assert CallbackDriverReport.from_json(report.to_json()) == report
    assert driver.run(recover_only=True) == report
    assert len(batch.replay().reservations) == 1 and not batch.replay().pending

    def denied(*args, **kwargs):
        raise AssertionError("offline verifier dispatched work")

    monkeypatch.setattr("subprocess.Popen", denied)
    verify_native_report(batch, "first", driver.spec, report)
    records = {r.resource: r.quantity for r in native_cost_records(report, "0" * 64)}
    assert records["native_driver_process_starts"] == 1
    assert records["native_wake_callbacks_attempted"] == 1
    assert records["native_gradient_callbacks_completed"] == 1
    assert not any("residual" in n or "inner_model" in n for n in records)
    assert "PRIVATE-CALLBACK-CANARY" not in report.to_json()


@pytest.mark.parametrize(
    "mode,status",
    [
        ("timeout", "timeout"),
        ("error", "model_failure"),
        ("overflow", "model_failure"),
        ("exhausted", "model_failure"),
    ],
)
def test_callback_failures_keep_original_charge_and_unknown_work(tmp_path, mode, status):
    driver, batch, _ = setup(tmp_path, mode, timeout=0.05 if mode == "timeout" else 6.0)
    report = driver.run()
    assert report.status == status and report.stop_verified
    assert driver.run(recover_only=True) == report
    verify_native_report(batch, "first", driver.spec, report)
    assert len(batch.replay().reservations) == 1 and not batch.replay().pending
    if mode == "exhausted":
        assert report.result.configuration is None and len(report.result.calls) == 2
    else:
        assert report.result is None
        costs = {r.resource: r.quantity for r in native_cost_records(report, "0" * 64)}
        assert costs["native_callback_entries"] is None


def test_callback_saved_process_recovers_without_another_launch(tmp_path):
    def lost(stage):
        if stage == "native_process_saved":
            raise RuntimeError("owner lost")

    driver, batch, _ = setup(tmp_path, fault=lost)
    with pytest.raises(RuntimeError, match="owner lost"):
        driver.run()
    assert len(batch.replay().pending) == 1
    report = SupervisedCallbackDriver(driver.spec, driver.executor).run(recover_only=True)
    assert report.status == "success" and len(batch.replay().reservations) == 1


def test_callback_spec_and_trace_reject_changed_caps_options_indices_and_unresolved(tmp_path):
    driver, _, _ = setup(tmp_path)
    with pytest.raises(ValueError):
        replace(driver.spec, options_json='{"mode": "success"}')
    with pytest.raises(ValueError):
        replace(driver.spec, callback_limits={"wake": 128, "gradient": 1})
    call = CallbackCall("wake", 1, "completed", {}, {"energy": 1.0}, {"energy": "GWh"})
    with pytest.raises(ValueError):
        replace(call, status="failed")
    result = CallbackDriverResult(
        "utility-callback-result-v1",
        driver.job.digest,
        "converged",
        True,
        True,
        {"x": 0.9},
        {"x": 0.9},
        (call,),
        driver.spec.callback_limits,
    )
    with pytest.raises(ValueError, match="indices"):
        replace(result, calls=(call, call))
    with pytest.raises(ValueError, match="resolved"):
        replace(result, calls=(replace(call, status="started", outputs={}, output_units={}),))
    with pytest.raises(ValueError, match="caps"):
        validate_callback_result(
            driver.spec, driver.job, replace(result, callback_limits={"wake": 3})
        )
    with pytest.raises(ValueError):
        validate_callback_result(
            driver.spec,
            driver.job,
            replace(result, configuration={"x": 2.0}, final_configuration={"x": 2.0}),
        )


def campaign_setup(tmp_path):
    driver, original, source = setup(tmp_path)
    execution = driver.spec.execution
    ref = next(r for r in execution.sources if r.path == "scenario_fixture.py")
    port = PortContract("power", (), "W", "float", (), "scalar", digest({"grid": "scalar"}), None)
    model = ModelSnapshot(
        digest({"callback": "authored"}),
        {"fixture": "1"},
        (ref,),
        execution.lock.sha256,
        (),
        (port,),
    )
    spec = EngineeringCallbackCampaignSpec(
        "utility-engineering-campaign-v3",
        "callback-campaign",
        execution,
        model,
        {"x": 0.2},
        (),
        16,
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
    batch = BatchStore.create(tmp_path / "campaign-batch", batch_spec)
    batch.start_case("first", batch.spec.cases[0].configuration_digest)
    runner = SupervisedEngineeringExecutor(execution, batch, "first", source)
    campaign = EngineeringCampaign.create(tmp_path / "callback-campaign", spec, runner)
    return campaign, batch, source


def test_callback_campaign_requires_fresh_checks_before_selection(tmp_path):
    campaign, batch, _ = campaign_setup(tmp_path)
    task = TaskEngineeringCampaign("wind", campaign.spec)
    assert TaskEngineeringCampaign.from_json(task.to_json()) == task
    assert EngineeringCallbackCampaignSpec.from_json(campaign.spec.to_json()) == campaign.spec
    for candidate, mode in (("baseline", "fixed"), ("native", "native")):
        response = campaign.handle(
            request(campaign, "evaluate", {"candidate_id": candidate, "mode": mode}, id=candidate)
        )
        assert response.status == "ok"
    state = campaign.state()
    assert len(state["native_reports"]) == 1 and len(state["evaluations"]) == 2
    assert len(batch.replay().reservations) == 5  # baseline 2, native 1, fresh 2
    campaign.handle(request(campaign, "review"))
    campaign.handle(request(campaign, "freeze"))
    reopened = EngineeringCampaign(campaign.store.root, batch)
    assert reopened.state()["selected"] == campaign.state()["selected"]
    assert reopened.state()["decision"].outcome == "retain_baseline"


def test_callback_verifier_rejects_changed_original_output(tmp_path):
    driver, batch, _ = setup(tmp_path)
    report = driver.run()
    path = driver.directory / "process/stdout.bin"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises((StoreError, ValueError)):
        verify_native_report(batch, "first", driver.spec, report)


def test_callback_wind_task_runs_shared_baseline_conventional_and_balanced_agent(tmp_path):
    from examples.utility.rehearse_engineering_plan import build_plan
    from autoengineering.utility.engineering_execution import (
        ScriptedEngineeringPlan,
        ScriptedEngineeringCoordinator,
    )

    campaign, _, source = campaign_setup(tmp_path)
    output = tmp_path / "route-plan"
    output.mkdir()
    _, _, plan, store = build_plan(output, source, campaign.spec, task_id="wind", family="wind")
    assert ScriptedEngineeringPlan.from_json(plan.to_json()) == plan
    assert store.spec.tasks[0].family == "wind"
    coordinator = ScriptedEngineeringCoordinator(store, plan, source)
    result = coordinator.run(max_new_cells=3)
    assert result["finished_cells"] == 3
    state = store.replay()
    assert sum(status == "finished" for _, status in state["attempts"].values()) == 3
    kinds = {r.route_id: r.kind for r in store.spec.routes}
    cells = {c.digest: c for c in store.spec.cells}
    finished_kinds = {
        kinds[cells[a.cell_digest].route_id]
        for a, status in state["attempts"].values()
        if status == "finished"
    }
    assert {"baseline", "conventional"} <= finished_kinds
    assert len(finished_kinds) == 3
    assert finished_kinds - {"baseline", "conventional"} <= {
        "single_agent",
        "multi_agent",
        "no_reviewer",
        "no_investigator",
        "no_implementer",
    }
    assert not state["confirmation_accesses"] and state["frozen"] is None
    for attempt, (allocation, status) in state["attempts"].items():
        if status == "finished":
            coordinator.runtime.verify_result(attempt)
