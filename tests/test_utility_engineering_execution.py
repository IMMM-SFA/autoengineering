"""Versioned engineering plans reuse parent/child recovery and suite barriers."""

from dataclasses import replace

import pytest

from autoengineering.agents.identity import host_environment_identity
from autoengineering.agents.records import ResourceLimits
from autoengineering.agents.scheduler import template_digests
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.contracts import BudgetSpec, ResourceCap
from autoengineering.utility.engineering_broker import (
    engineering_grant_identity,
    engineering_recipe_identity,
)
from autoengineering.utility.engineering_execution import (
    ScriptedEngineeringPlan,
    TaskEngineeringCampaign,
    ScriptedEngineeringCoordinator,
    case_scoped_campaign,
    engineering_runtime_identity,
)
from autoengineering.utility.mechanical import mechanism_identity
from autoengineering.utility.routes import (
    ScientificGrant,
    HostGrant,
    RoleAllowance,
    RouteRecipe,
    RoutePlan,
    TaskRoute,
    conventional_recipe,
    single_agent_recipe,
    role_removals,
)
from autoengineering.utility.store import SuiteStore
from test_utility_contracts import suite, H
from test_utility_engineering_native import native_campaign
from test_utility_routes import full


def setup(tmp_path, kinds=("baseline", "conventional")):
    original, batch = native_campaign(tmp_path)
    campaign = case_scoped_campaign(original.spec)
    source = original.executor.source_root
    worker = ResourceLimits(24, 24, 0, 0, 150.0, 10.0, 2097152, 1048576)
    child = ResourceLimits(168, 168, 0, 0, 400.0, 10.0, 16777216, 1048576)
    provisional = RoutePlan(
        "utility-routes-v1", (TaskRoute("task", "full", full()),), 1, 17, {"task": H}
    )
    plan = ScriptedEngineeringPlan(
        "utility-scripted-engineering-v1",
        provisional,
        (TaskEngineeringCampaign("task", campaign),),
        campaign.execution.sources,
        campaign.execution.lock,
        worker,
        child,
        engineering_runtime_identity(),
    )
    common = engineering_grant_identity(campaign)
    grant = ScientificGrant(
        common["candidates"],
        common["partition_digest"],
        common["search_bounds_digest"],
        common["acceptance_digest"],
        plan.research_corpus_digest,
        host_environment_identity(),
        None,
    )
    parent = suite()
    caps = tuple(
        ResourceCap(name, unit, value, "reservation")
        for name, unit, value in (
            ("scientific_starts", "count", campaign.scientific_starts * len(kinds) + 2),
            ("host_invocations", "count", 24 * len(kinds)),
            ("training_starts", "count", 0),
            ("active_time", "s", 400.0 * len(kinds)),
        )
    )
    budget = BudgetSpec(
        "fixed_evaluations", caps, (ResourceCap("scientific_starts", "count", 2, "reservation"),)
    )
    recipe = RouteRecipe(
        "multi_agent",
        grant,
        HostGrant(
            plan.host_configuration_digest,
            "scripted",
            "scripted-1.0",
            plan.host_permissions_digest,
            24,
        ),
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
        engineering_recipe_identity(campaign),
        caps,
    )
    conventional = conventional_recipe(
        recipe, numerical_recipe_digest=recipe.numerical_recipe_digest
    )
    variants = (
        replace(conventional, kind="baseline"),
        conventional,
        single_agent_recipe(
            recipe, prompt_digest=template_digests("single_agent")["single_agent"], maximum_calls=24
        ),
        recipe,
        *role_removals(
            recipe,
            {
                role: mechanism_identity(role)
                for role in ("investigator", "implementer", "reviewer")
            },
        ),
    )
    route_plan = RoutePlan(
        "utility-routes-v1",
        tuple(TaskRoute("task", r.kind, r) for r in variants if r.kind in kinds),
        1,
        17,
        {"task": grant.partition_digest},
    )
    plan = replace(plan, routes=route_plan)
    tasks = (
        replace(
            parent.tasks[0],
            candidate_digests=grant.candidates,
            partition_digest=grant.partition_digest,
            outcome_digest=grant.acceptance_digest,
        ),
    )
    routes, cells = plan.routes.expand(tasks, (budget,))
    parent = replace(
        parent,
        tasks=tasks,
        routes=routes,
        cells=cells,
        budgets=(budget,),
        source_digest=digest([r.to_dict() for r in plan.source_inventory]),
        lock_digest=plan.lock.sha256,
        protocol_digest=plan.digest,
    )
    store = SuiteStore.create(tmp_path / "suite", parent)
    return store, plan, source


def test_engineering_plan_executes_cells_and_exports_exact_suite_selection(tmp_path):
    store, plan, source = setup(tmp_path)
    assert ScriptedEngineeringPlan.from_json(plan.to_json()) == plan
    coordinator = ScriptedEngineeringCoordinator(store, plan, source)
    first = coordinator.run(max_new_cells=1)
    assert first["finished_cells"] == 1
    resumed = ScriptedEngineeringCoordinator(SuiteStore(store.root), plan, source)
    assert resumed.run()["finished_cells"] == 2
    events = len(store.replay()["events"])
    assert resumed.run()["completed_this_call"] == 0
    assert len(store.replay()["events"]) == events
    manifest = resumed.selection_manifest()
    assert all(c.status == "selected" and c.selected_state for c in manifest.cells)
    from autoengineering.utility.confirmation import freeze

    frozen = freeze(store, manifest)
    assert store.replay()["frozen"] == frozen
    assert resumed.run()["completed_this_call"] == 0


class OwnerLost(BaseException):
    pass


@pytest.mark.parametrize("kind", ["baseline", "conventional", "multi_agent"])
def test_saved_engineering_response_resumes_original_scientific_work(tmp_path, kind):
    store, plan, source = setup(tmp_path, (kind,))

    def lost(stage):
        if stage == "engineering_scientific_response_saved":
            raise OwnerLost()

    coordinator = ScriptedEngineeringCoordinator(store, plan, source, fault=lost)
    with pytest.raises(OwnerLost):
        coordinator.run()
    allocation, status = next(iter(store.replay()["attempts"].values()))
    assert status == "started"
    child, _ = coordinator.runtime._child(allocation.child_digest)
    original_ids = set(child.replay().reservations)
    assert len(original_ids) == 2 and not child.replay().pending
    resumed = ScriptedEngineeringCoordinator(SuiteStore(store.root), plan, source)
    assert resumed.run()["finished_cells"] == 1
    physical = child.replay()
    assert original_ids <= set(physical.reservations)
    assert sum(r.resource == "science" for r in physical.reservations.values()) == (
        2 if kind == "baseline" else 9
    )


def test_plan_or_source_change_refuses_before_parent_dispatch(tmp_path):
    store, plan, source = setup(tmp_path)
    with pytest.raises(StoreError, match="protocol"):
        ScriptedEngineeringCoordinator(
            store,
            replace(plan, worker_limits=replace(plan.worker_limits, max_invocations=23)),
            source,
        )
    (source / "scenario_fixture.py").write_text("changed")
    with pytest.raises(ValueError):
        ScriptedEngineeringCoordinator(store, plan, source)
    assert not store.replay()["attempts"]


def test_public_cli_runs_and_resumes_engineering_plan_without_sealing(tmp_path):
    import json
    from click.testing import CliRunner
    from autoengineering.cli import cli

    store, plan, source = setup(tmp_path)
    path = tmp_path / "engineering-plan.json"
    path.write_text(plan.to_json())
    common = [str(store.root), str(path), "--source-root", str(source), "--scripted-development"]
    runner = CliRunner()
    first = runner.invoke(cli, ["utility", "run", *common, "--max-new-cells", "1"])
    assert first.exit_code == 0, first.output
    assert runner.invoke(cli, ["utility", "run", *common]).exit_code == 2
    resumed = runner.invoke(cli, ["utility", "resume", *common])
    assert resumed.exit_code == 0, resumed.output
    result = json.loads(resumed.output)
    assert result["finished_cells"] == 2 and result["selection_proposal"]["sha256"]
    assert store.replay()["frozen"] is None
    again = runner.invoke(cli, ["utility", "resume", *common])
    assert again.exit_code == 0 and json.loads(again.output)["completed_this_call"] == 0


def test_runtime_drift_and_legacy_execution_refuse_before_dispatch(tmp_path):
    store, plan, source = setup(tmp_path)
    with pytest.raises(StoreError, match="environment"):
        ScriptedEngineeringCoordinator(store, replace(plan, runtime_identity="0" * 64), source)
    from autoengineering.utility.engineering_process import execution_identity

    campaign = plan.campaigns[0].campaign
    e = campaign.execution
    identity = execution_identity(
        e.entrypoint, e.sources, e.lock, e.scenarios, e.timeout_seconds, e.output_bytes
    )
    legacy = replace(
        e,
        schema="utility-engineering-execution-v1",
        study=replace(e.study, source_identity=identity),
    )
    old = replace(campaign, execution=legacy, native=replace(campaign.native, execution=legacy))
    with pytest.raises(ValueError, match="case-scoped"):
        replace(plan, campaigns=(TaskEngineeringCampaign("task", old),))
    assert not store.replay()["attempts"]


def test_grouped_permissions_and_native_jobs_are_case_scoped(tmp_path):
    store, plan, source = setup(tmp_path, ("conventional", "single_agent"))
    coordinator = ScriptedEngineeringCoordinator(store, plan, source)
    coordinator.run()
    allocation = next(iter(store.replay()["attempts"].values()))[0]
    child, bindings = coordinator.runtime._child(allocation.child_digest)
    state = child.replay()
    assert len(bindings) == 2
    assert sum(r.resource == "science" for r in state.reservations.values()) == 18
    assert len([r for r in state.reservations.values() if r.id.startswith("native-")]) == 2
    for binding in bindings:
        assert (
            sum(
                r.resource == "science" and r.case_id == binding.case_id
                for r in state.reservations.values()
            )
            == 9
        )


def test_cli_pending_scenarios_require_explicit_original_request_continuation(tmp_path):
    from click.testing import CliRunner
    from autoengineering.cli import cli

    store, plan, source = setup(tmp_path, ("baseline",))
    path = tmp_path / "plan.json"
    path.write_text(plan.to_json())
    common = [str(store.root), str(path), "--source-root", str(source), "--scripted-development"]
    runner = CliRunner()
    assert runner.invoke(cli, ["utility", "run", *common, "--max-new-cells", "0"]).exit_code == 0

    def lost(stage):
        if stage == "engineering_scenario_observed":
            raise OwnerLost()

    coordinator = ScriptedEngineeringCoordinator(store, plan, source, fault=lost)
    with pytest.raises(OwnerLost):
        coordinator.run()
    allocation = next(iter(store.replay()["attempts"].values()))[0]
    child, _ = coordinator.runtime._child(allocation.child_digest)
    assert len(child.replay().reservations) == 1
    default = runner.invoke(cli, ["utility", "resume", *common])
    assert default.exit_code == 2 and len(child.replay().reservations) == 1
    continued = runner.invoke(cli, ["utility", "resume", *common, "--continue-pending-scenarios"])
    assert continued.exit_code == 0, continued.output
    assert len(child.replay().reservations) == 2


def test_archive_interruption_reuses_finished_science_without_reexecution(tmp_path):
    store, plan, source = setup(tmp_path, ("baseline",))

    def lost(stage):
        if stage == "engineering_selection_archived":
            raise OwnerLost()

    coordinator = ScriptedEngineeringCoordinator(store, plan, source, fault=lost)
    with pytest.raises(OwnerLost):
        coordinator.run()
    allocation = next(iter(store.replay()["attempts"].values()))[0]
    child, _ = coordinator.runtime._child(allocation.child_digest)
    before = set(child.replay().reservations)
    resumed = ScriptedEngineeringCoordinator(SuiteStore(store.root), plan, source)
    assert resumed.run()["finished_cells"] == 1
    assert set(child.replay().reservations) == before
    from autoengineering.utility.confirmation import freeze

    freeze(store, resumed.selection_manifest())
