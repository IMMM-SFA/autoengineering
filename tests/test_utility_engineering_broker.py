"""Engineering roles reuse worker grants and original scientific requests."""

from dataclasses import replace

import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from autoengineering.utility.engineering_process import SupervisedEngineeringExecutor
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.permissions import policy_digest
from autoengineering.agents.records import AgentRunSpec, HostSelection, ResourceLimits
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.engineering_broker import EngineeringBroker, run_engineering_recipe
from autoengineering.utility.execution import BatchScriptedHost
from test_utility_engineering_native import native_campaign


def setup(tmp_path, *, route="four_role", fault=lambda _: None):
    original, old_batch = native_campaign(tmp_path, fault=fault)
    batch_spec = replace(
        old_batch.spec,
        limits=replace(
            old_batch.spec.limits,
            max_invocations=30,
            max_tasks=30,
            max_repairs=0,
            repairs_per_task=0,
            elapsed_seconds=240.0,
            worker_seconds=10.0,
            transcript_bytes=4194304,
            workspace_bytes=1048576,
        ),
        cases=(replace(old_batch.spec.cases[0], host_invocations=30),),
    )
    batch = BatchStore.create(tmp_path / "broker-batch", batch_spec)
    batch.start_case("first", batch.spec.cases[0].configuration_digest)
    runner = SupervisedEngineeringExecutor(
        original.spec.execution, batch, "first", original.executor.source_root
    )
    campaign = EngineeringCampaign.create(
        tmp_path / "broker-campaign", original.spec, runner, fault=fault
    )
    limits = ResourceLimits(30, 30, 0, 0, 150.0, 10.0, 2097152, 1048576)
    spec = AgentRunSpec(
        "1.1" if route == "single_agent" else "1.0",
        "engineering-worker",
        campaign.spec.name,
        digest(campaign.identity),
        HostSelection("fake", "none", "scripted", "1.0"),
        template_digests(route),
        ("calibration", "native"),
        policy_digest(route),
        limits,
        host_source_identity(),
        host_environment_identity(),
        "supplied",
        route,
    )
    workers = WorkerStore.create(tmp_path / "worker", spec)
    host = BatchScriptedHost(batch, "first", route)
    return EngineeringBroker(campaign, SerialScheduler(workers, host)), campaign, batch


@pytest.mark.parametrize("route,expected", [("four_role", 15), ("single_agent", 8)])
def test_engineering_roles_complete_native_and_numerical_choices_without_repeating_work(
    tmp_path, route, expected
):
    broker, campaign, batch = setup(tmp_path, route=route)
    state = broker.advance()
    assert state["projection"].state == "selection_frozen"
    assert len(state["evaluations"]) == 4 and len(state["native_reports"]) == 1
    assert state["selected"].configuration == {"x": 0.2}
    physical = batch.replay()
    assert len([r for r in physical.reservations.values() if r.resource == "science"]) == 9
    assert len([r for r in physical.reservations.values() if r.resource == "host"]) == expected
    worker = broker.store.replay()
    assert len(worker.invocations) == expected and not worker.pending
    assert {t.role for t in worker.tasks.values()} == (
        {"single_agent"}
        if route == "single_agent"
        else {"orchestrator", "investigator", "implementer", "reviewer"}
    )
    assert broker.advance()["selected"] == state["selected"]
    assert len(batch.replay().reservations) == len(physical.reservations)


@pytest.mark.parametrize("kind,science", [("baseline", 2), ("conventional", 9)])
def test_non_agent_recipes_preserve_original_envelopes_and_include_native(tmp_path, kind, science):
    campaign, batch = native_campaign(tmp_path)
    state = run_engineering_recipe(campaign, kind)
    assert state["projection"].state == "selection_frozen"
    assert len(batch.replay().reservations) == science
    assert len(state["native_reports"]) == (1 if kind == "conventional" else 0)
    assert run_engineering_recipe(campaign, kind)["selected"] == state["selected"]
    assert len(batch.replay().reservations) == science


def test_engineering_broker_refuses_changed_catalogue_before_science(tmp_path):
    broker, campaign, batch = setup(tmp_path)
    spec = replace(broker.store.spec, permitted_interventions=("calibration",))
    other = WorkerStore.create(tmp_path / "other-worker", spec)
    with pytest.raises(StoreError, match="catalogue"):
        EngineeringBroker(campaign, SerialScheduler(other, broker.scheduler.host))
    assert not batch.replay().reservations


def test_cancelled_engineering_controller_denies_new_science_without_waiting_for_writer(tmp_path):
    broker, campaign, batch = setup(tmp_path)
    with campaign.store.writer():
        result = campaign.cancel("cancel-independent")
    assert result == {
        "request_id": "cancel-independent",
        "campaign_id": campaign.spec.name,
        "operation": "cancel",
    }
    assert campaign.cancel("cancel-independent") == result
    from test_utility_engineering_campaign import request

    response = campaign.handle(
        request(campaign, "evaluate", {"candidate_id": "baseline", "mode": "fixed"})
    )
    assert response.error == "invalid_transition" and not batch.replay().reservations


def assigned_ablation(tmp_path, omitted):
    from autoengineering.agents.batch import BatchCase, BatchSpec
    from autoengineering.agents.hosts.scripted import scripted_host
    from autoengineering.utility.controller import UtilityController, CaseBinding
    from autoengineering.utility.engineering_broker import (
        engineering_grant_identity,
        engineering_recipe_identity,
        paired_engineering_spec,
    )
    from autoengineering.utility.mechanical import mechanism_identity
    from autoengineering.utility.role_host import RoleBoundHost
    from autoengineering.utility.routes import (
        ScientificGrant,
        HostGrant,
        RoleAllowance,
        RouteRecipe,
        TaskRoute,
        RoutePlan,
        role_removals,
    )
    from autoengineering.utility.store import SuiteStore
    from test_utility_contracts import suite, H

    original, old_batch = native_campaign(tmp_path)
    model_spec = original.spec
    limits = ResourceLimits(30, 30, 0, 0, 180.0, 10.0, 4194304, 1048576)
    profile = digest({"profile": "scripted-engineering-test", "limits": limits.to_dict()})
    common = engineering_grant_identity(model_spec)
    grant = ScientificGrant(
        common["candidates"],
        common["partition_digest"],
        common["search_bounds_digest"],
        common["acceptance_digest"],
        H,
        H,
        None,
    )
    full = RouteRecipe(
        "multi_agent",
        grant,
        HostGrant(profile, "scripted", "scripted-1.0", policy_digest("four_role"), 30),
        tuple(
            RoleAllowance(role, count, template_digests()[role])
            for role, count in (
                ("orchestrator", 8),
                ("investigator", 2),
                ("implementer", 2),
                ("reviewer", 3),
            )
        ),
        {},
        engineering_recipe_identity(model_spec),
        suite().budgets[0].caps,
    )
    variant = next(
        r
        for r in role_removals(
            full,
            {
                role: mechanism_identity(role)
                for role in ("investigator", "implementer", "reviewer")
            },
        )
        if r.kind == "no_" + omitted
    )
    parent = suite()
    tasks = (
        replace(
            parent.tasks[0],
            partition_digest=grant.partition_digest,
            candidate_digests=grant.candidates,
            outcome_digest=grant.acceptance_digest,
        ),
    )
    plan = RoutePlan(
        "utility-routes-v1", (TaskRoute("task", variant.kind, variant),), 1, 17, {"task": H}
    )
    routes, cells = plan.expand(tasks, parent.budgets)
    parent = replace(parent, tasks=tasks, routes=routes, cells=cells)
    model_spec = paired_engineering_spec(model_spec, cells[0].seed)
    store = SuiteStore.create(tmp_path / "suite", parent)
    runtime = UtilityController(store)
    case = BatchCase(
        "assigned", "comparison", routes[0].configuration_digest, 30, model_spec.scientific_starts
    )
    spec = BatchSpec(
        "1.0",
        "engineering-ablation",
        host_source_identity(),
        host_environment_identity(),
        HostSelection("fake", "none", "scripted", "1.0"),
        scripted_host().capabilities(),
        profile,
        limits,
        model_spec.scientific_starts,
        (case,),
    )
    child = runtime.prepare_batch(spec, (CaseBinding(cells[0].digest, case.id),))
    saved = {}

    def run(batch, case_id):
        root = batch.root / "cases" / case_id
        root.mkdir(mode=0o700, exist_ok=True)
        executor = SupervisedEngineeringExecutor(
            model_spec.execution, batch, case_id, original.executor.source_root
        )
        campaign = EngineeringCampaign.create(root / "engineering", model_spec, executor)
        worker_spec = AgentRunSpec(
            "1.0",
            "assigned-worker",
            campaign.spec.name,
            digest(campaign.identity),
            spec.host,
            template_digests(),
            ("calibration", "native"),
            policy_digest("four_role"),
            limits,
            host_source_identity(),
            host_environment_identity(),
            "supplied",
        )
        workers = WorkerStore.create(root / "worker", worker_spec)
        host = RoleBoundHost(
            store,
            batch,
            cells[0].digest,
            plan,
            BatchScriptedHost(batch, case_id, "four_role"),
            templates={r.role: r.prompt_digest for r in variant.roles},
        )
        broker = EngineeringBroker(
            campaign,
            SerialScheduler(workers, host),
            suite_store=store,
            plan=plan,
            cell_digest=cells[0].digest,
        )
        saved.update(broker=broker, campaign=campaign)
        final = broker.advance()
        batch.finish_case(
            case_id,
            "passed",
            (
                batch.evidence(
                    {"campaign": campaign.spec.digest, "selection": final["selected"].to_dict()}
                ),
            ),
        )

    runtime.dispatch(child.root.name, cells[0].digest, run)
    return store, child, saved, omitted


@pytest.mark.parametrize(
    "role,expected", [("investigator", 13), ("implementer", 13), ("reviewer", 12)]
)
def test_engineering_ablations_use_registered_mechanisms_without_omitted_host_calls(
    tmp_path, role, expected
):
    store, child, saved, omitted = assigned_ablation(tmp_path, role)
    state = store.replay()
    assert len(state["mechanical_steps"]) == (3 if role == "reviewer" else 2)
    worker = saved["broker"].store.replay()
    assert omitted not in {task.role for task in worker.tasks.values()}
    assert len(worker.invocations) == expected
    assert len([r for r in child.replay().reservations.values() if r.resource == "science"]) == 9
    assert saved["campaign"].state()["selected"].configuration == {"x": 0.2}
    assert sum(state["role_counts"].values()) == expected
    assert (
        state["used"][("fixed_evaluations", "host_invocations")] == 30
    )  # Omitted budget is not redistributed or refunded.


def test_broker_reconciles_saved_scientific_response_without_another_start(tmp_path):
    class OwnerLost(BaseException):
        pass

    def lost(stage):
        if stage == "engineering_campaign_result_ready":
            raise OwnerLost()

    broker, campaign, batch = setup(tmp_path, fault=lost)
    with pytest.raises(OwnerLost):
        broker.advance()
    assert len(batch.replay().reservations) == 2
    assert any(a.state == "reserved" for a in broker.store.replay().actions.values())
    reopened = EngineeringCampaign(campaign.store.root, batch, executor=campaign.executor)
    runner = EngineeringBroker(
        reopened, SerialScheduler(WorkerStore(broker.store.root), broker.scheduler.host)
    )
    runner.advance()
    assert sum(r.resource == "science" for r in batch.replay().reservations.values()) == 9
    assert not any(a.state == "reserved" for a in runner.store.replay().actions.values())


def test_broker_cannot_start_after_worker_deadline(tmp_path):
    from autoengineering.agents.broker import WorkflowStopped

    broker, campaign, batch = setup(tmp_path)
    started = broker.store.replay().started_at
    broker.scheduler.clock = lambda: started + 200.0
    with pytest.raises(WorkflowStopped, match="deadline exhausted"):
        broker.advance()
    assert campaign._cancelled() and broker.scheduler._cancelled()
    assert not batch.replay().reservations


def test_worker_configuration_override_is_rejected_before_candidate_science(tmp_path):
    import dataclasses
    from itertools import repeat
    from autoengineering.agents.hosts.fake import FakeHost
    from autoengineering.agents.hosts.scripted import supplied_reply
    from autoengineering.agents.records import RoleHandoff
    from autoengineering.agents.broker import WorkflowStopped

    broker, campaign, batch = setup(tmp_path)

    def override(task, prompt, invocation_id):
        result = supplied_reply(task, prompt, invocation_id)
        if task.role == "implementer":
            value = RoleHandoff.from_json(result.raw_output)
            value = dataclasses.replace(
                value, output=dataclasses.replace(value.output, parameters={"x": 99.0})
            )
            result = dataclasses.replace(result, raw_output=value.to_json())
        return result

    broker.scheduler.host.delegate = FakeHost(repeat(override))
    with pytest.raises(WorkflowStopped, match="repair allowance exhausted"):
        broker.advance()
    assert sum(r.resource == "science" for r in batch.replay().reservations.values()) == 2
    assert any(v.state == "invalid_output" for v in broker.store.replay().invocations.values())


def test_advisory_review_stop_remains_a_completed_handoff(tmp_path):
    import dataclasses
    from itertools import repeat
    from autoengineering.agents.hosts.fake import FakeHost
    from autoengineering.agents.hosts.scripted import supplied_reply
    from autoengineering.agents.records import RoleHandoff
    from autoengineering.agents.broker import WorkflowStopped

    broker, campaign, batch = setup(tmp_path)

    def stop(task, prompt, invocation_id):
        result = supplied_reply(task, prompt, invocation_id)
        if task.role == "reviewer":
            value = RoleHandoff.from_json(result.raw_output)
            value = dataclasses.replace(
                value, output=dataclasses.replace(value.output, recommendation="stop")
            )
            result = dataclasses.replace(result, raw_output=value.to_json())
        return result

    broker.scheduler.host.delegate = FakeHost(repeat(stop))
    with pytest.raises(WorkflowStopped, match="advisory review stopped"):
        broker.advance()
    reviewers = [
        v
        for v in broker.store.replay().invocations.values()
        if broker.store.replay().tasks[v.task_id].role == "reviewer"
    ]
    assert len(reviewers) == 1 and reviewers[0].state == "completed"
    assert campaign.state()["selected"] is None


def test_native_supervisor_observes_cancellation_and_retains_unknown_inner_work(tmp_path):
    from test_utility_engineering_native import setup as native_setup

    driver, batch, source = native_setup(tmp_path, iterations=1, timeout=5.0)
    driver.executor.cancelled = lambda: (driver.directory / "process/process.json").exists()
    report = driver.run()
    assert report.process_status == "cancelled" and report.stop_verified
    assert report.result is None and len(batch.replay().reservations) == 1
    assert driver.run(recover_only=True) == report


def test_engineering_summary_carries_frozen_domain_scenarios_units_and_recipe_limits(tmp_path):
    broker, campaign, batch = setup(tmp_path)
    summary = broker.summary()
    assert summary["parameter_domain"] == campaign.spec.execution.study.run.search_space.to_dict()
    assert summary["scenarios"] == [s.to_dict() for s in campaign.spec.execution.scenarios]
    assert summary["native_recipe"]["max_model_solves"] == campaign.spec.native.max_model_solves
    assert (
        summary["numerical_recipe"]["paired_seed"] == campaign.spec.execution.study.run.study.seed
    )
    assert summary["interface"]["outputs"][0]["units"] == "W"
    assert not batch.replay().reservations


def test_broker_partial_scientific_request_requires_explicit_continuation(tmp_path):
    broker, campaign, batch = setup(tmp_path)

    def lost(stage):
        if stage == "engineering_scenario_observed":
            raise RuntimeError("partial original baseline")

    campaign.executor.fault = lost
    with pytest.raises(RuntimeError, match="partial original baseline"):
        broker.advance()
    assert sum(r.resource == "science" for r in batch.replay().reservations.values()) == 1
    runner = SupervisedEngineeringExecutor(
        campaign.spec.execution, batch, "first", campaign.executor.source_root
    )
    reopened = EngineeringCampaign(campaign.store.root, batch, executor=runner)
    resumed = EngineeringBroker(
        reopened, SerialScheduler(WorkerStore(broker.store.root), broker.scheduler.host)
    )
    with pytest.raises(StoreError, match="undispatched"):
        resumed.advance()
    assert sum(r.resource == "science" for r in batch.replay().reservations.values()) == 1
    final = resumed.advance(resume_scenarios=True)
    assert final["projection"].state == "selection_frozen"
    assert sum(r.resource == "science" for r in batch.replay().reservations.values()) == 9
