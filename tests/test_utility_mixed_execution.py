"""Mixed suites retain task-specific executors and one selection barrier."""

from dataclasses import replace

import pytest

from autoengineering.agents.identity import host_environment_identity
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.store import StoreError
from autoengineering.utility.engineering_execution import TaskEngineeringCampaign
from autoengineering.utility.execution import campaign_recipe_identity
from autoengineering.utility.mixed_execution import (
    ScriptedMixedPlan,
    ScriptedMixedCoordinator,
    TaskPredictionCampaign,
)
from autoengineering.utility.routes import RoutePlan, TaskRoute
from autoengineering.utility.store import SuiteStore
from test_utility_engineering_execution import setup as engineering_setup
from test_utility_execution import setup as prediction_setup


def setup(tmp_path, kind="baseline"):
    eng_root, pred_root = tmp_path / "eng", tmp_path / "pred"
    eng_root.mkdir(mode=0o700)
    pred_root.mkdir(mode=0o700)
    es, ep, source = engineering_setup(eng_root, kinds=(kind,))
    ps, pp, pred_source = prediction_setup(pred_root)
    prediction = CampaignSpec.from_json(
        read_bytes(pred_source, pp.campaigns[0].specification).decode()
    )
    refs = {r.path: r for r in ep.source_inventory}
    for ref in (*pp.source_inventory, pp.lock):
        target = source / ref.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(read_bytes(pred_source, ref))
        refs[ref.path] = ref
    (source / ep.lock.path).unlink()
    refs.pop(ep.lock.path, None)
    inventory = tuple(refs.values())
    eng = ep.campaigns[0].campaign
    from autoengineering.utility.engineering_process import execution_identity

    old = eng.execution
    identity = execution_identity(
        old.entrypoint,
        inventory,
        pp.lock,
        old.scenarios,
        old.timeout_seconds,
        old.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        old, sources=inventory, lock=pp.lock, study=replace(old.study, source_identity=identity)
    )
    eng = replace(eng, execution=execution, native=replace(eng.native, execution=execution))
    plan = ScriptedMixedPlan(
        "utility-scripted-mixed-v1",
        ep.routes,
        (
            TaskEngineeringCampaign("engineering", eng),
            TaskPredictionCampaign("prediction", prediction),
        ),
        inventory,
        pp.lock,
        ep.worker_limits,
        ep.batch_limits,
        ep.runtime_identity,
    )
    rows = []
    for name, recipe in (
        ("engineering", ep.routes.task_routes[0].recipe),
        ("prediction", pp.routes.task_routes[1 if kind == "multi_agent" else 0].recipe),
    ):
        grant = replace(
            recipe.scientific_grant,
            research_corpus_digest=plan.research_corpus_digest,
            hardware_digest=host_environment_identity(),
        )
        if name == "engineering":
            from autoengineering.utility.engineering_broker import (
                engineering_grant_identity,
                engineering_recipe_identity,
            )

            grant = replace(grant, **engineering_grant_identity(eng))
            numerical = engineering_recipe_identity(eng)
        else:
            numerical = campaign_recipe_identity(prediction)
        if recipe.host:
            recipe = replace(
                recipe,
                host=replace(
                    recipe.host,
                    host_profile_digest=plan.host_configuration_digest,
                    permissions_digest=plan.host_permissions_digest,
                ),
            )
        rows.append(
            TaskRoute(
                name,
                kind,
                replace(
                    recipe,
                    kind=kind,
                    scientific_grant=grant,
                    numerical_recipe_digest=numerical,
                ),
            )
        )
    tasks = tuple(
        replace(
            (es if name == "engineering" else ps).spec.tasks[0],
            task_id=name,
            family="engineering" if name == "engineering" else "hydrology",
            candidate_digests=row.recipe.scientific_grant.candidates,
            partition_digest=row.recipe.scientific_grant.partition_digest,
            outcome_digest=row.recipe.scientific_grant.acceptance_digest,
        )
        for name, row in zip(("engineering", "prediction"), rows)
    )
    routes = RoutePlan(
        "utility-routes-v1", tuple(rows), 1, 17, {t.task_id: t.partition_digest for t in tasks}
    )
    plan = replace(plan, routes=routes)
    budgets = tuple(
        replace(b, caps=tuple(replace(c, limit=c.limit * 3) for c in b.caps))
        for b in es.spec.budgets
    )
    rs, cells = routes.expand(tasks, budgets)
    spec = replace(
        es.spec,
        tasks=tasks,
        routes=rs,
        cells=cells,
        budgets=budgets,
        protocol_digest=plan.digest,
        source_digest=digest([r.to_dict() for r in inventory]),
        lock_digest=pp.lock.sha256,
    )
    return SuiteStore.create(tmp_path / "mixed", spec), plan, source


def test_mixed_parent_runs_both_executors_and_freezes_one_manifest(tmp_path, monkeypatch):
    store, plan, source = setup(tmp_path)
    assert ScriptedMixedPlan.from_json(plan.to_json()) == plan
    first = ScriptedMixedCoordinator(store, plan, source).run(max_new_cells=1)
    assert first["finished_cells"] == 1
    coordinator = ScriptedMixedCoordinator(SuiteStore(store.root), plan, source)
    result = coordinator.run()
    assert result["finished_cells"] == 2 and result["utility_verdict"] == "not_attempted"
    assert coordinator.run()["completed_this_call"] == 0
    manifest = coordinator.selection_manifest()
    assert {c.cell_digest for c in manifest.cells} == {c.digest for c in store.spec.cells}
    assert all(c.status == "selected" for c in manifest.cells)
    from autoengineering.utility.confirmation import freeze

    assert freeze(store, manifest) == store.replay()["frozen"]
    import builtins
    import importlib
    import io
    import os
    from pathlib import Path
    from autoengineering.utility.confirmation import validate_manifest

    original_import, original_read = importlib.import_module, Path.read_bytes

    def denied(*args, **kwargs):
        raise AssertionError("Offline reader attempted physical or network dispatch")

    def guarded_import(name, *args, **kwargs):
        if name.startswith(("scenario_fixture", "examples.campaign_contracts")):
            raise AssertionError("Offline reader imported a scientific model")
        return original_import(name, *args, **kwargs)

    def archived_only(path):
        if path.is_relative_to(source):
            raise AssertionError("Offline reader accessed original captured sources")
        return original_read(path)

    def guarded_open(original):
        def opened(path, *args, **kwargs):
            if not isinstance(path, int) and Path(os.fsdecode(path)).absolute().is_relative_to(
                source
            ):
                raise AssertionError("Offline reader opened original captured sources")
            return original(path, *args, **kwargs)

        return opened

    with monkeypatch.context() as guard:
        guard.setattr(os, "open", guarded_open(os.open))
        guard.setattr(builtins, "open", guarded_open(builtins.open))
        guard.setattr(io, "open", guarded_open(io.open))
        guard.setattr("subprocess.Popen", denied)
        guard.setattr("socket.socket", denied)
        guard.setattr(importlib, "import_module", guarded_import)
        guard.setattr(Path, "read_bytes", archived_only)
        state = store.replay()
        validate_manifest(store, manifest, state["attempts"], state["events"])
        for selected in manifest.cells:
            coordinator.runtime.verify_result(selected.attempt_id)


def test_mixed_rejects_task_outcome_before_allocation(tmp_path):
    store, plan, source = setup(tmp_path)
    changed = replace(
        store.spec,
        tasks=tuple(
            replace(t, outcome_digest="9" * 64) if t.task_id == "prediction" else t
            for t in store.spec.tasks
        ),
    )
    bad = SuiteStore.create(tmp_path / "wrong-outcome", changed)
    with pytest.raises(StoreError, match="outcome"):
        ScriptedMixedCoordinator(bad, plan, source)
    assert bad.replay()["attempts"] == {}


def test_mixed_cli_resume_preserves_plan_and_exports_shared_proposal(tmp_path):
    import json
    from click.testing import CliRunner
    from autoengineering.cli import cli

    store, plan, source = setup(tmp_path)
    path = tmp_path / "execution.json"
    path.write_text(plan.to_json())
    common = [str(store.root), str(path), "--source-root", str(source), "--scripted-development"]
    runner = CliRunner()
    first = runner.invoke(cli, ["utility", "run", *common, "--max-new-cells", "1"])
    assert first.exit_code == 0, first.output
    resumed = runner.invoke(cli, ["utility", "resume", *common])
    assert resumed.exit_code == 0, resumed.output
    assert json.loads(resumed.output)["finished_cells"] == 2
    assert json.loads(resumed.output)["selection_proposal"]["sha256"]
    assert store.replay()["frozen"] is None


def test_mixed_plan_rejects_changed_prediction_lock(tmp_path):
    _, plan, _ = setup(tmp_path)
    prediction = plan.campaigns[1]
    changed = replace(
        prediction.campaign,
        provenance=replace(
            prediction.campaign.provenance, environment_lock=replace(plan.lock, sha256="8" * 64)
        ),
    )
    with pytest.raises(ValueError, match="lock"):
        replace(plan, campaigns=(plan.campaigns[0], replace(prediction, campaign=changed)))


def test_mixed_changed_prediction_bytes_reject_before_allocation(tmp_path):
    store, plan, source = setup(tmp_path)
    data = plan.campaigns[1].campaign.data[0].artifact
    (source / data.path).write_bytes(b"changed")
    with pytest.raises((ValueError, StoreError)):
        ScriptedMixedCoordinator(store, plan, source)
    assert store.replay()["attempts"] == {}


def test_mixed_agent_routes_use_both_existing_brokers(tmp_path):
    store, plan, source = setup(tmp_path, kind="multi_agent")
    coordinator = ScriptedMixedCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 2
    assert all(c.status == "selected" for c in coordinator.selection_manifest().cells)
    assert store.replay()["role_invocations"]


@pytest.mark.parametrize(
    "stage", ["engineering_scientific_response_saved", "scripted_scientific_response_saved"]
)
def test_mixed_resume_after_original_response_preserves_reservations(tmp_path, stage):
    store, plan, source = setup(tmp_path)

    class OwnerLost(BaseException):
        pass

    def lost(current):
        if current == stage:
            raise OwnerLost()

    coordinator = ScriptedMixedCoordinator(store, plan, source, fault=lost)
    with pytest.raises(OwnerLost):
        coordinator.run()
    state = store.replay()
    allocation = next(a for a, status in state["attempts"].values() if status == "started")
    child, _ = coordinator.runtime._child(allocation.child_digest)
    original = set(child.replay().reservations)
    assert original
    resumed = ScriptedMixedCoordinator(SuiteStore(store.root), plan, source)
    assert resumed.run()["finished_cells"] == 2
    assert original <= set(child.replay().reservations)
    finished = len(child.replay().reservations)
    assert finished == 3  # Two engineering scenarios and one prediction, with no repeated starts.
    assert resumed.run()["completed_this_call"] == 0
    assert len(child.replay().reservations) == finished


@pytest.mark.parametrize("change", ["runtime", "private", "wind", "catalogue", "corpus"])
def test_mixed_grant_and_scope_changes_stop_before_allocation(tmp_path, change):
    store, plan, source = setup(tmp_path)
    spec = store.spec
    if change == "runtime":
        plan = replace(plan, runtime_identity="7" * 64)
    elif change == "private":
        task = plan.campaigns[1]
        data = tuple(replace(d, prior_exposure="unexposed") for d in task.campaign.data)
        plan = replace(
            plan,
            campaigns=(
                plan.campaigns[0],
                replace(task, campaign=replace(task.campaign, data=data)),
            ),
        )
    elif change in ("wind", "catalogue"):
        spec = replace(
            spec,
            tasks=tuple(
                replace(
                    t,
                    **(
                        {"family": "wind"}
                        if change == "wind"
                        else {"candidate_digests": ("7" * 64,)}
                    ),
                )
                if t.task_id == "prediction"
                else t
                for t in spec.tasks
            ),
        )
    else:
        routes = tuple(
            replace(
                row,
                recipe=replace(
                    row.recipe,
                    scientific_grant=replace(
                        row.recipe.scientific_grant, research_corpus_digest="7" * 64
                    ),
                ),
            )
            if row.task_id == "prediction"
            else row
            for row in plan.routes.task_routes
        )
        plan = replace(plan, routes=replace(plan.routes, task_routes=routes))
    if change == "catalogue":
        rows = tuple(
            replace(
                row,
                recipe=replace(
                    row.recipe,
                    scientific_grant=replace(row.recipe.scientific_grant, candidates=("7" * 64,)),
                ),
            )
            if row.task_id == "prediction"
            else row
            for row in plan.routes.task_routes
        )
        plan = replace(plan, routes=replace(plan.routes, task_routes=rows))
    routes, cells = plan.routes.expand(spec.tasks, spec.budgets)
    spec = replace(spec, protocol_digest=plan.digest, routes=routes, cells=cells)
    changed = SuiteStore.create(tmp_path / "rejected", spec)
    with pytest.raises(StoreError):
        ScriptedMixedCoordinator(changed, plan, source)
    assert changed.replay()["attempts"] == {}
