"""Real registered training through shared scripted route selection and freezing."""

from dataclasses import replace

import pytest

from autoengineering.agents.records import ResourceLimits
from autoengineering.agents.scheduler import template_digests
from autoengineering.campaign.artifacts import reference, read_bytes
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.confirmation import TrainedSelectedState, read_selected_state, freeze
from autoengineering.utility.contracts import ResourceCap
from autoengineering.utility.controller import CaseBinding
from autoengineering.utility.execution import (
    ScriptedCoordinator,
    ScriptedExecutionPlan,
    TaskCampaign,
    campaign_recipe_identity,
)
from autoengineering.utility.report import accounting_report
from autoengineering.utility.routes import (
    ScientificGrant,
    RoutePlan,
    TaskRoute,
    conventional_recipe,
    single_agent_recipe,
)
from autoengineering.utility.store import SuiteStore
from test_utility_campaign_training_costs import setup as campaign_setup
from test_utility_contracts import suite, H
from test_utility_routes import full


def setup(
    tmp_path, monkeypatch, *, cap=120, routes=("baseline", "conventional", "single", "multi")
):
    _, controller = campaign_setup(tmp_path, monkeypatch, registered=True, run=False, cap=cap)
    source = controller.bundle
    campaign = replace(
        controller.spec, execution=replace(controller.spec.execution, max_executions=1)
    )
    (source / "campaign.json").write_text(campaign.to_json())
    campaign_ref = reference(
        source, "campaign.json", media_type="application/json", producer="author"
    )
    refs = {
        r.path: r
        for r in (
            *campaign.provenance.sources,
            campaign.baseline.system,
            campaign.provenance.environment_lock,
            *(d.artifact for d in campaign.data),
        )
    }
    inventory = tuple(refs.values())
    worker = ResourceLimits(20, 16, 0, 0, 120, 30, 1048576, 1048576)
    batch = ResourceLimits(40, 16, 0, 0, 180, 30, 2097152, 1048576)
    grant = ScientificGrant(
        (campaign.baseline.model.digest,),
        digest([d.to_dict() for d in campaign.data]),
        digest([i.to_dict() for i in campaign.interventions]),
        campaign.acceptance.digest,
        H,
        H,
        campaign.baseline.model.implementations["training"],
    )
    caps = tuple(
        replace(c, limit=100)
        if c.name == "training_starts"
        else replace(c, limit=2000)
        if c.name == "active_time"
        else c
        for c in suite().budgets[0].caps
    ) + (ResourceCap("training_routing_starts", "count", 100 * cap, "reservation"),)
    recipe = replace(
        full(),
        scientific_grant=grant,
        limits=caps,
        numerical_recipe_digest=campaign_recipe_identity(campaign),
        host=replace(
            full().host,
            model="scripted",
            version="scripted-1.0",
            host_profile_digest=digest(
                {"profile": "scripted-supplied-v1", "worker_limits": worker.to_dict()}
            ),
        ),
        roles=tuple(replace(r, prompt_digest=template_digests()[r.role]) for r in full().roles),
    )
    choices = {
        "baseline": replace(recipe, kind="baseline", host=None, roles=()),
        "conventional": conventional_recipe(
            recipe, numerical_recipe_digest=campaign_recipe_identity(campaign)
        ),
        "single": single_agent_recipe(
            recipe, prompt_digest=template_digests("single_agent")["single_agent"], maximum_calls=16
        ),
        "multi": recipe,
    }
    task = replace(
        suite().tasks[0],
        family="hydrology",
        candidate_digests=grant.candidates,
        partition_digest=grant.partition_digest,
        outcome_digest=campaign.acceptance.digest,
        required_capabilities=("frozen_trained_inference",),
    )
    budget = replace(suite().budgets[0], caps=caps)
    route_plan = RoutePlan(
        "utility-routes-v1",
        tuple(TaskRoute("task", name, choices[name]) for name in routes),
        1,
        17,
        {"task": H},
    )
    expanded, cells = route_plan.expand((task,), (budget,))
    plan = ScriptedExecutionPlan(
        "utility-scripted-development-v1",
        route_plan,
        (TaskCampaign("task", campaign_ref),),
        inventory,
        campaign.provenance.environment_lock,
        worker,
        batch,
    )
    spec = replace(
        suite(),
        tasks=(task,),
        budgets=(budget,),
        routes=expanded,
        cells=cells,
        protocol_digest=plan.digest,
        source_digest=digest([r.to_dict() for r in inventory]),
        lock_digest=plan.lock.sha256,
    )
    return SuiteStore.create(tmp_path / "trained-suite", spec), plan, source


def test_all_scripted_routes_archive_the_exact_fit_and_freeze_without_retraining(
    tmp_path, monkeypatch
):
    store, plan, source = setup(tmp_path, monkeypatch)
    coordinator = ScriptedCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 4
    manifest = coordinator.selection_manifest()
    cells = {c.digest: c for c in store.spec.cells}
    for cell in manifest.cells:
        assert cell.status == "selected"
        bound = read_selected_state(store.root, cell.selected_state)
        assert isinstance(bound, TrainedSelectedState)
        assert bound.evaluation.provenance["execution_seed"] == str(cells[cell.cell_digest].seed)
        for ref in bound.training.references():
            read_bytes(store.root, ref)
    state = store.replay()
    regime = store.spec.budgets[0].regime
    assert state["phase_used"][(regime, "selection", "training_starts")] == 4
    assert state["phase_used"][(regime, "selection", "training_routing_starts")] == 480
    report = accounting_report(store)
    assert not report["evidence_blockers"]
    starts = [r for r in report["receipts"] if r["resource"] == "training_starts"]
    assert len(starts) == 4 and sum(r["quantity"] for r in starts) == 4
    monkeypatch.setattr("subprocess.Popen", lambda *_a, **_k: pytest.fail("freeze executed"))
    assert freeze(store, manifest) == store.replay()["frozen"]
    assert coordinator.run()["completed_this_call"] == 0


def test_failed_training_produces_no_selected_state_but_keeps_work(tmp_path, monkeypatch):
    store, plan, source = setup(tmp_path, monkeypatch, cap=3, routes=("conventional",))
    coordinator = ScriptedCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 1
    cell = coordinator.selection_manifest().cells[0]
    assert cell.status == "no_eligible_model" and cell.selected_state is None
    report = accounting_report(store)
    assert not report["evidence_blockers"]
    assert (
        next(r["quantity"] for r in report["receipts"] if r["resource"] == "training_starts") == 1
    )


def test_legacy_binding_bytes_and_zero_training_reservations_are_preserved():
    binding = CaseBinding(H, "case")
    assert binding.to_dict() == {"cell_digest": H, "case_id": "case"}
    assert CaseBinding.from_json(binding.to_json()) == binding
    with pytest.raises(ValueError):
        CaseBinding(H, "case", 1, 0)


def test_missing_training_budget_refuses_before_science(tmp_path, monkeypatch):
    store, plan, source = setup(tmp_path, monkeypatch, routes=("conventional",))
    budget = replace(
        store.spec.budgets[0],
        caps=tuple(
            replace(c, limit=0) if c.name == "training_starts" else c
            for c in store.spec.budgets[0].caps
        ),
    )
    # Budgets participate in cell identity, so freeze a fresh matching matrix.
    routes, cells = plan.routes.expand(store.spec.tasks, (budget,))
    fresh = SuiteStore.create(
        tmp_path / "no-training", replace(store.spec, budgets=(budget,), routes=routes, cells=cells)
    )
    monkeypatch.setattr(
        "subprocess.Popen", lambda *_a, **_k: pytest.fail("unreserved training launched")
    )
    with pytest.raises(StoreError, match="budget"):
        ScriptedCoordinator(fresh, plan, source).run()
    assert not fresh.replay()["attempts"]


def test_resume_after_saved_scientific_response_never_retrains(tmp_path, monkeypatch):
    import autoengineering.campaign.controller as module

    store, plan, source = setup(tmp_path, monkeypatch, routes=("baseline",))

    class AuthoredLoss(BaseException):
        pass

    def fault(stage):
        if stage == "scripted_scientific_response_saved":
            raise AuthoredLoss()

    with pytest.raises(AuthoredLoss):
        ScriptedCoordinator(store, plan, source, fault=fault).run()
    monkeypatch.setattr(module, "supervise", lambda *_a, **_k: pytest.fail("resume retrained"))
    coordinator = ScriptedCoordinator(SuiteStore(store.root), plan, source)
    assert coordinator.run()["finished_cells"] == 1
    assert isinstance(
        read_selected_state(store.root, coordinator.selection_manifest().cells[0].selected_state),
        TrainedSelectedState,
    )
    report = accounting_report(store)
    assert len([r for r in report["receipts"] if r["resource"] == "training_starts"]) == 1


def test_frozen_baseline_followers_reuse_one_fit_with_original_seed_and_cost(tmp_path, monkeypatch):
    from autoengineering.campaign.spec import CampaignSpec
    from autoengineering.utility.contracts import BaselineReuseGroup, BaselineReusePolicy

    original, plan, source = setup(tmp_path, monkeypatch, routes=("baseline",))
    plan = replace(plan, routes=replace(plan.routes, repetitions=2))
    routes, cells = plan.routes.expand(original.spec.tasks, original.spec.budgets)
    campaign = CampaignSpec.from_json(read_bytes(source, plan.campaigns[0].specification).decode())
    group = BaselineReuseGroup(
        tuple(c.digest for c in cells),
        cells[0].digest,
        campaign.baseline.model.digest,
        digest(dict(campaign.baseline.parameters)),
        H,
        (0.5, 0.5),
    )
    policy = BaselineReusePolicy(
        "utility-baseline-reuse-v2", plan.digest, (group,), selection_reuse="frozen_reference"
    )
    store = SuiteStore.create(
        tmp_path / "shared-fit",
        replace(
            original.spec,
            schema="utility-suite-v2",
            routes=routes,
            cells=cells,
            baseline_reuse=policy,
            protocol_digest=policy.digest,
        ),
    )
    coordinator = ScriptedCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 2
    manifest = coordinator.selection_manifest()
    assert len({c.selected_state.sha256 for c in manifest.cells}) == 1
    assert cells[0].seed != cells[1].seed
    freeze(store, manifest)
    regime = store.spec.budgets[0].regime
    assert store.replay()["phase_used"][(regime, "selection", "training_starts")] == 1
    report = accounting_report(store)
    assert not report["evidence_blockers"]
    starts = [r for r in report["receipts"] if r["resource"] == "training_starts"]
    assert len(starts) == 1 and starts[0]["quantity"] == 1
    assert set(starts[0]["cell_digests"]) == {c.digest for c in cells}
    assert starts[0]["allocation"] == [0.5, 0.5]


def test_mixed_engineering_and_trained_prediction_share_the_existing_barrier(tmp_path, monkeypatch):
    import test_utility_mixed_execution as fixtures
    from autoengineering.utility.mixed_execution import ScriptedMixedCoordinator

    monkeypatch.setattr(
        fixtures, "prediction_setup", lambda root: setup(root, monkeypatch, routes=("baseline",))
    )
    original, plan, source = fixtures.setup(tmp_path)
    budgets = tuple(
        replace(
            budget,
            caps=tuple(
                replace(c, limit=2) if c.name == "training_starts" else c for c in budget.caps
            )
            + (ResourceCap("training_routing_starts", "count", 120, "reservation"),),
        )
        for budget in original.spec.budgets
    )
    routes, cells = plan.routes.expand(original.spec.tasks, budgets)
    store = SuiteStore.create(
        tmp_path / "mixed-trained",
        replace(original.spec, budgets=budgets, routes=routes, cells=cells),
    )
    coordinator = ScriptedMixedCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 2
    manifest = coordinator.selection_manifest()
    assert all(c.status == "selected" for c in manifest.cells)
    states = [read_selected_state(store.root, c.selected_state) for c in manifest.cells]
    assert sum(isinstance(state, TrainedSelectedState) for state in states) == 1
    freeze(store, manifest)
    report = accounting_report(store)
    assert not report["evidence_blockers"]
    assert len([r for r in report["receipts"] if r["resource"] == "training_starts"]) == 1


@pytest.mark.parametrize("change", ["profile", "inner_cap", "capability"])
def test_training_grant_and_bounds_refuse_before_dispatch(tmp_path, monkeypatch, change):
    original, plan, source = setup(tmp_path, monkeypatch, routes=("conventional",))
    tasks = original.spec.tasks
    row = plan.routes.task_routes[0]
    if change == "profile":
        row = replace(
            row,
            recipe=replace(
                row.recipe,
                scientific_grant=replace(row.recipe.scientific_grant, training_profile_digest=None),
            ),
        )
    elif change == "inner_cap":
        row = replace(
            row,
            recipe=replace(
                row.recipe,
                limits=tuple(c for c in row.recipe.limits if c.name != "training_routing_starts"),
            ),
        )
    else:
        tasks = (replace(tasks[0], required_capabilities=()),)
    plan = replace(plan, routes=replace(plan.routes, task_routes=(row,)))
    routes, cells = plan.routes.expand(tasks, original.spec.budgets)
    store = SuiteStore.create(
        tmp_path / "refused-training",
        replace(
            original.spec, tasks=tasks, routes=routes, cells=cells, protocol_digest=plan.digest
        ),
    )
    monkeypatch.setattr(
        "autoengineering.campaign.controller.supervise",
        lambda *_a, **_k: pytest.fail("ungranted science launched"),
    )
    with pytest.raises(StoreError):
        ScriptedCoordinator(store, plan, source).run()
    assert not store.replay()["attempts"]
