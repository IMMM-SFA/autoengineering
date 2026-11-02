"""Frozen scripted coordinator executes actual tiny supplied campaigns."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from autoengineering.agents.records import ResourceLimits
from autoengineering.agents.scheduler import template_digests
from autoengineering.campaign.artifacts import reference, read_bytes
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.execution import TaskCampaign, ScriptedExecutionPlan, ScriptedCoordinator, campaign_recipe_identity
from autoengineering.utility.routes import ScientificGrant, TaskRoute, RoutePlan, conventional_recipe
from autoengineering.utility.store import SuiteStore
from examples.agent_campaign.fixture import agent_fixture
from examples.campaign_contracts.build_fixture import ROOT
from test_utility_contracts import suite, H
from test_utility_routes import full


def setup(tmp_path):
    campaign = agent_fixture()
    campaign = replace(campaign, execution=replace(campaign.execution, max_executions=2))
    source = tmp_path / "captured"
    source.mkdir(mode=0o700)
    refs = {r.path: r for r in (*campaign.provenance.sources, campaign.baseline.system,
                                campaign.provenance.environment_lock, *(d.artifact for d in campaign.data))}
    for path in (ROOT / "src/autoengineering").rglob("*.py"):
        relative = str(path.relative_to(ROOT))
        refs[relative] = reference(ROOT, relative, media_type="text/plain", producer="capture")
    for ref in refs.values():
        destination = source / ref.path
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        destination.write_bytes(read_bytes(ROOT, ref))
    (source / "campaign.json").write_text(campaign.to_json())
    campaign_ref = reference(source, "campaign.json", media_type="application/json", producer="fixture")
    inventory = tuple(refs.values())
    worker = ResourceLimits(20, 16, 0, 0, 120, 30, 1048576, 1048576)
    batch = ResourceLimits(20, 16, 0, 0, 180, 30, 2097152, 1048576)
    host_config = digest({"profile": "scripted-supplied-v1", "worker_limits": worker.to_dict()})
    pool = tuple(dict.fromkeys((campaign.baseline.model.digest, *(s.model.digest for s in
        CampaignController.supplied_snapshots(SimpleNamespace(spec=campaign))))))
    grant = ScientificGrant(pool, digest([d.to_dict() for d in campaign.data]),
        digest([i.to_dict() for i in campaign.interventions]), campaign.acceptance.digest, H, H, None)
    recipe = replace(full(), scientific_grant=grant, numerical_recipe_digest=campaign_recipe_identity(campaign),
        host=replace(full().host, host_profile_digest=host_config, model="scripted", version="scripted-1.0"),
        roles=tuple(replace(r, prompt_digest=template_digests()[r.role]) for r in full().roles))
    spec = suite()
    tasks = (replace(spec.tasks[0], candidate_digests=pool, partition_digest=grant.partition_digest),)
    route_plan = RoutePlan("utility-routes-v1", (
        TaskRoute("task", "conventional", conventional_recipe(recipe, numerical_recipe_digest=campaign_recipe_identity(campaign))),
        TaskRoute("task", "multi", recipe)), 1, 17, {"task": H})
    routes, cells = route_plan.expand(tasks, spec.budgets)
    plan = ScriptedExecutionPlan("utility-scripted-development-v1", route_plan,
        (TaskCampaign("task", campaign_ref),), inventory, campaign.provenance.environment_lock, worker, batch)
    spec = replace(spec, tasks=tasks, routes=routes, cells=cells, protocol_digest=plan.digest,
                   source_digest=digest([r.to_dict() for r in inventory]), lock_digest=plan.lock.sha256)
    store = SuiteStore.create(tmp_path / "suite", spec)
    return store, plan, source


def test_scripted_coordinator_pauses_at_cell_boundary_and_resumes(tmp_path):
    store, plan, source = setup(tmp_path)
    coordinator = ScriptedCoordinator(store, plan, source)
    first = coordinator.run(max_new_cells=1)
    assert first["finished_cells"] == 1 and first["completed_this_call"] == 1
    resumed = ScriptedCoordinator(SuiteStore(store.root), plan, source)
    result = resumed.run()
    assert result["finished_cells"] == 2
    before = len(store.replay()["events"])
    assert resumed.run()["completed_this_call"] == 0
    assert len(store.replay()["events"]) == before
    assert result["utility_verdict"] == "not_attempted"
    from autoengineering.utility.confirmation import freeze
    manifest = resumed.selection_manifest()
    assert all(cell.status == "selected" and cell.selected_state for cell in manifest.cells)
    identity = freeze(store, manifest)
    assert store.replay()["frozen"] == identity


def test_changed_source_or_plan_rejects_before_dispatch(tmp_path):
    store, plan, source = setup(tmp_path)
    with pytest.raises(StoreError, match="protocol"):
        ScriptedCoordinator(store, replace(plan, worker_limits=replace(plan.worker_limits, max_invocations=19)), source)
    (source / plan.source_inventory[0].path).write_text("changed")
    with pytest.raises(ValueError):
        ScriptedCoordinator(store, plan, source)
    assert store.replay()["attempts"] == {}


def test_cli_run_resume_and_selection_proposal(tmp_path):
    import json
    from click.testing import CliRunner
    from autoengineering.cli import cli
    store, plan, source = setup(tmp_path)
    path = tmp_path / "execution.json"
    path.write_text(plan.to_json())
    common = [str(store.root), str(path), "--source-root", str(source), "--scripted-development"]
    runner = CliRunner()
    started = runner.invoke(cli, ["utility", "run", *common, "--max-new-cells", "1"])
    assert started.exit_code == 0, started.output
    assert json.loads(started.output)["completed_this_call"] == 1
    assert runner.invoke(cli, ["utility", "run", *common]).exit_code == 2
    resumed = runner.invoke(cli, ["utility", "resume", *common])
    assert resumed.exit_code == 0, resumed.output
    document = json.loads(resumed.output)
    assert document["finished_cells"] == 2
    assert document["selection_proposal"]["sha256"]
    again = runner.invoke(cli, ["utility", "resume", *common])
    assert again.exit_code == 0 and json.loads(again.output)["completed_this_call"] == 0
    assert store.replay()["frozen"] is None  # Review/seal remains explicit.


class OwnerLost(BaseException):
    pass


@pytest.mark.parametrize("route", ["conventional", "multi"])
def test_saved_scientific_response_resumes_without_repeating_physical_start(tmp_path, route):
    store, plan, source = setup(tmp_path)
    coordinator = ScriptedCoordinator(store, plan, source)
    first_route = store.spec.cells[0].route_id
    if first_route != route:
        coordinator.run(max_new_cells=1)

    def lose_owner(stage):
        assert stage == "scripted_scientific_response_saved"
        raise OwnerLost()

    coordinator.fault = lose_owner
    with pytest.raises(OwnerLost):
        coordinator.run(max_new_cells=1)
    state = store.replay()
    allocation, status = next((a, s) for a, s in state["attempts"].values() if s == "started")
    assert status == "started"
    child, bindings = coordinator.runtime._child(allocation.child_digest)
    binding = next(b for b in bindings if b.cell_digest == allocation.cell_digest)
    initial = [r.id for r in child.replay().reservations.values() if r.case_id == binding.case_id]
    assert len(initial) == 1 and not child.replay().pending
    parent_charge = dict(state["used"])
    reopened = ScriptedCoordinator(SuiteStore(store.root), plan, source)
    resumed = reopened.run(max_new_cells=1)
    assert resumed["completed_this_call"] == 1
    physical = [r for r in child.replay().reservations.values() if r.case_id == binding.case_id]
    science = [r for r in physical if r.resource == "science"]
    assert len(science) == 2
    assert science[0].id == initial[0]
    assert dict(store.replay()["used"]) == parent_charge
    assert reopened.run()["finished_cells"] == 2



@pytest.mark.parametrize("blocker", ["pending_host", "cancelled"])
def test_unresolved_or_cancelled_cell_blocks_resume(tmp_path, blocker):
    from autoengineering.agents.batch import PhysicalReservation
    store, plan, source = setup(tmp_path)
    coordinator = ScriptedCoordinator(store, plan, source)
    # Finish conventional cells before targeting the route with host permission.
    if store.spec.cells[0].route_id != "multi":
        coordinator.run(max_new_cells=1)

    def lose_owner(stage):
        raise OwnerLost()

    coordinator.fault = lose_owner
    with pytest.raises(OwnerLost):
        coordinator.run(max_new_cells=1)
    allocation = next(a for a, status in store.replay()["attempts"].values() if status == "started")
    child, bindings = coordinator.runtime._child(allocation.child_digest)
    binding = next(b for b in bindings if b.cell_digest == allocation.cell_digest)
    if blocker == "pending_host":
        child.reserve(PhysicalReservation("uncertain-host", binding.case_id, "host", H,
                                          "investigator", child.clock(), 1, 1, 128, 0))
        message = "physical work remains uncertain"
    else:
        with store.writer():
            store.append(request_id="suite-cancel", operation="cancel", attempt_id="suite-cancel",
                         cell_digest=store.spec.cells[0].digest, child_digest=store.spec.digest)
        message = "cancelled or frozen"
    before = tuple(child.replay().events)
    with pytest.raises(StoreError, match=message):
        ScriptedCoordinator(SuiteStore(store.root), plan, source).run()
    assert tuple(child.replay().events) == before
    assert len(child.replay().pending) == (1 if blocker == "pending_host" else 0)
