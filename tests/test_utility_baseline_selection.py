"""Frozen baseline selection references retain one original scientific result."""

from dataclasses import replace

import pytest

from autoengineering.campaign.serialization import digest
from autoengineering.utility.store import SuiteStore
from autoengineering.utility.execution import ScriptedCoordinator
from autoengineering.utility.confirmation import freeze
from test_utility_execution import setup as execution_setup, OwnerLost
from test_utility_contracts import H


def baseline_setup(tmp_path, *, selection=True, repetitions=2):
    from autoengineering.utility.contracts import BaselineReuseGroup, BaselineReusePolicy
    from autoengineering.campaign.spec import CampaignSpec
    from autoengineering.campaign.artifacts import read_bytes
    from autoengineering.utility.routes import RoutePlan, TaskRoute

    old, original, source = execution_setup(tmp_path)
    recipe = replace(original.routes.task_routes[0].recipe, kind="baseline")
    route_plan = RoutePlan(
        "utility-routes-v1",
        tuple(TaskRoute("task", name, recipe) for name in ("reference-a", "reference-b")),
        repetitions,
        17,
        {"task": H},
    )
    plan = replace(original, routes=route_plan)
    budget = old.spec.budgets[0]
    budget = replace(
        budget,
        caps=tuple(replace(c, limit=10000) if c.name == "active_time" else c for c in budget.caps),
    )
    routes, cells = route_plan.expand(old.spec.tasks, (budget,))
    campaign = CampaignSpec.from_json(read_bytes(source, plan.campaigns[0].specification).decode())
    group = BaselineReuseGroup(
        tuple(c.digest for c in cells),
        cells[0].digest,
        campaign.baseline.model.digest,
        digest(dict(campaign.baseline.parameters)),
        H,
        tuple(1 / len(cells) for _ in cells),
    )
    kwargs = {"selection_reuse": "frozen_reference"} if selection else {}
    policy = BaselineReusePolicy(
        "utility-baseline-reuse-v2" if selection else "utility-baseline-reuse-v1",
        plan.digest,
        (group,),
        **kwargs,
    )
    spec = replace(
        old.spec,
        schema="utility-suite-v2",
        routes=routes,
        cells=cells,
        budgets=(budget,),
        protocol_digest=policy.digest,
        baseline_reuse=policy,
    )
    return SuiteStore.create(tmp_path / "reference-suite", spec), plan, source


def science_reservations(store):
    from autoengineering.utility.controller import UtilityController

    runtime = UtilityController(store)
    children = {
        a.child_digest for a, _ in store.replay()["attempts"].values() if a.phase == "selection"
    }
    return [
        r
        for identity in children
        for r in runtime._child(identity)[0].replay().reservations.values()
        if r.resource == "science"
    ]


def test_one_scientific_reference_and_complete_verified_selection(tmp_path):
    store, plan, source = baseline_setup(tmp_path)
    coordinator = ScriptedCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 4
    assert len(science_reservations(store)) == 1
    assert (
        store.replay()["phase_used"][("fixed_evaluations", "selection", "scientific_starts")] == 1
    )
    manifest = coordinator.selection_manifest()
    assert all(c.status == "selected" for c in manifest.cells)
    assert len({c.selected_state.sha256 for c in manifest.cells}) == 1
    freeze(store, manifest)
    before = store.replay()["head"]
    assert coordinator.run()["completed_this_call"] == 0
    assert store.replay()["head"] == before


@pytest.mark.parametrize(
    "boundary", ["baseline_reference_evidence_saved", "baseline_reference_case_finished"]
)
def test_follower_resume_uses_original_reference_without_rescoring(tmp_path, boundary):
    store, plan, source = baseline_setup(tmp_path)

    def fault(point):
        if point == boundary:
            raise OwnerLost()

    with pytest.raises(OwnerLost):
        ScriptedCoordinator(store, plan, source, fault=fault).run()
    assert len(science_reservations(store)) == 1
    resumed = ScriptedCoordinator(SuiteStore(store.root), plan, source)
    assert resumed.run()["finished_cells"] == 4
    freeze(store, resumed.selection_manifest())
    assert len(science_reservations(store)) == 1


def test_confirmation_only_policy_does_not_enable_selection_reuse(tmp_path):
    store, plan, source = baseline_setup(tmp_path, selection=False)
    ScriptedCoordinator(store, plan, source).run()
    assert len(science_reservations(store)) == 4


def test_reference_batch_requires_new_version_and_cannot_reserve_work(tmp_path):
    from autoengineering.agents.batch import BatchCase, BatchStore
    from test_agent_batch import specification, reservation

    reference = BatchCase("reference", "reference", H, 0, 0)
    with pytest.raises(ValueError):
        replace(specification(), cases=(reference,))
    spec = replace(specification(), schema_version="1.1", cases=(reference,), scientific_starts=0)
    batch = BatchStore.create(tmp_path / "metadata", spec, clock=lambda: 100)
    batch.start_case("reference", H)
    for kind in ("host", "science"):
        with pytest.raises(ValueError):
            batch.reserve(reservation(case="reference", resource=kind))


def test_reference_crosses_child_batch_boundary_without_new_science(tmp_path):
    store, plan, source = baseline_setup(tmp_path, repetitions=17)
    coordinator = ScriptedCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 34
    assert len(science_reservations(store)) == 1
    freeze(store, coordinator.selection_manifest())
    children = {a.child_digest for a, _ in store.replay()["attempts"].values()}
    assert len(children) == 2


def test_selection_cost_keeps_one_physical_receipt_and_unknown_copy_overhead(tmp_path):
    from autoengineering.utility.report import accounting_report

    store, plan, source = baseline_setup(tmp_path)
    coordinator = ScriptedCoordinator(store, plan, source)
    coordinator.run()
    freeze(store, coordinator.selection_manifest())
    report = accounting_report(store)
    assert not report["evidence_blockers"]
    science = [r for r in report["receipts"] if r["resource"] == "campaign_process_starts"]
    assert len(science) == 1 and science[0]["quantity"] == 1
    assert len(science[0]["cell_digests"]) == 4 and sum(science[0]["allocation"]) == 1
    copies = [r for r in report["receipts"] if r["resource"] == "baseline_reference_copy_duration"]
    assert len(copies) == 3 and all(r["quantity"] is None for r in copies)
    assert report["complete_cost_evidence"] is False


def test_frozen_reference_allocation_distributes_original_training_once(tmp_path):
    from autoengineering.utility.baseline_selection import allocate_selection_costs
    from autoengineering.utility.costs import CostRecord

    store, _, _ = baseline_setup(tmp_path)
    group = store.spec.baseline_reuse.groups[0]
    original = CostRecord(
        "authored-training",
        H,
        "training",
        "training_starts",
        "count",
        1.0,
        (group.source_cell_digest,),
        (1.0,),
    )
    records = allocate_selection_costs(store, (original,))
    assert len(records) == 1 and records[0].receipt_id == original.receipt_id
    assert records[0].quantity == 1.0
    assert records[0].cell_digests == group.cell_digests
    assert records[0].allocation == group.allocation
    assert sum(records[0].allocation) == 1.0
    assert allocate_selection_costs(store, records) == records


def test_wrong_defaults_or_reversed_source_refuse_before_dispatch(tmp_path):
    store, plan, source = baseline_setup(tmp_path)
    policy = store.spec.baseline_reuse
    group = policy.groups[0]
    wrong = replace(policy, groups=(replace(group, configuration_digest="3" * 64),))
    spec = replace(store.spec, protocol_digest=wrong.digest, baseline_reuse=wrong)
    fresh = SuiteStore.create(tmp_path / "wrong-defaults", spec)
    with pytest.raises(ValueError):
        ScriptedCoordinator(fresh, plan, source)
    assert not fresh.replay()["attempts"]
    with pytest.raises(ValueError):
        backwards = replace(
            policy, groups=(replace(group, source_cell_digest=group.cell_digests[-1]),)
        )
        replace(store.spec, protocol_digest=backwards.digest, baseline_reuse=backwards)


def test_forged_self_consistent_reference_cannot_finish_or_freeze(tmp_path):
    from autoengineering.utility.baseline_selection import BaselineSelectionReference
    from autoengineering.utility.confirmation import selected_artifact_evidence, SelectedState
    from autoengineering.campaign.records import ArtifactRef, ModelSnapshot
    from autoengineering.campaign.artifacts import read_bytes
    from autoengineering.campaign.serialization import unique_json

    store, plan, source = baseline_setup(tmp_path)
    coordinator = ScriptedCoordinator(store, plan, source)
    coordinator.run(max_new_cells=1)
    first = store.spec.cells[0]
    original = coordinator.runtime.verify_result("child-" + first.digest[:48])
    child, _ = coordinator.runtime._child(original["child_digest"])
    summaries = [
        unique_json(read_bytes(child.root, ArtifactRef.from_dict(r)).decode())
        for r in original["case_result"]["evidence"]
    ]
    summary = next(r for r in summaries if isinstance(r, dict) and r.get("profile") == plan.schema)
    chosen = summary["selection"]
    target = store.spec.cells[1]
    allocation = store.replay()["attempts"]["child-" + target.digest[:48]][0]

    def forge(batch, case):
        proof = BaselineSelectionReference(
            "utility-baseline-selection-reference-v1",
            store.spec.digest,
            store.spec.baseline_reuse.digest,
            first.digest,
            target.digest,
            "0" * 64,
        )
        artifacts = []
        for kind, record_type in (("model", ModelSnapshot), ("selected_state", SelectedState)):
            ref = ArtifactRef.from_dict(chosen[kind])
            value = record_type.from_json(read_bytes(store.root, ref).decode())
            artifacts.append(selected_artifact_evidence(batch, ref, value.to_dict(), kind))
        data = batch.evidence(
            {
                "profile": plan.schema,
                "cell": target.digest,
                "selection": chosen,
                "baseline_reference": proof.to_dict(),
            }
        )
        batch.finish_case(case, "passed", (data, *artifacts))

    with pytest.raises(ValueError):
        coordinator.runtime.dispatch(allocation.child_digest, target.digest, forge)
    assert len(science_reservations(store)) == 1
    with pytest.raises(ValueError):
        coordinator.runtime.reconcile(allocation.child_digest, target.digest)
    with pytest.raises(ValueError):
        coordinator.selection_manifest()


def test_engineering_reference_seals_common_state_and_confirms_once(tmp_path):
    from test_utility_engineering_execution import setup
    from autoengineering.utility.engineering_execution import ScriptedEngineeringCoordinator
    from autoengineering.utility.contracts import (
        ScoredTaskSpec,
        BaselineReuseGroup,
        BaselineReusePolicy,
        ResourceCap,
    )
    from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService, PublicScore
    from autoengineering.utility.baseline_execution import frozen_baseline_allocations

    old, original, source = setup(tmp_path, kinds=("baseline",))
    campaign = original.campaigns[0].campaign
    rules = campaign.execution.study.rules
    outcome = next(o for o in rules.outcomes if o.name == rules.primary_metric)
    task = ScoredTaskSpec.from_dict(
        old.spec.tasks[0].to_dict()
        | {"schema": "utility-task-scoring-v2", "scoring_outcome_digest": outcome.digest}
    )
    plan = replace(original, routes=replace(original.routes, repetitions=2))
    budget = replace(
        old.spec.budgets[0],
        caps=tuple(
            replace(c, limit=4000) if c.name == "active_time" else c
            for c in old.spec.budgets[0].caps
        ),
    )
    routes, cells = plan.routes.expand((task,), (budget,))
    group = BaselineReuseGroup(
        tuple(c.digest for c in cells),
        cells[0].digest,
        campaign.model.digest,
        digest(dict(campaign.baseline_configuration)),
        H,
        (0.5, 0.5),
    )
    policy = BaselineReusePolicy(
        "utility-baseline-reuse-v2", plan.digest, (group,), selection_reuse="frozen_reference"
    )
    spec = replace(
        old.spec,
        schema="utility-suite-v2",
        tasks=(task,),
        budgets=(budget,),
        routes=routes,
        cells=cells,
        protocol_digest=policy.digest,
        baseline_reuse=policy,
    )
    store = SuiteStore.create(tmp_path / "engineering-reference", spec)
    coordinator = ScriptedEngineeringCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 2
    assert len(science_reservations(store)) == len(campaign.execution.scenarios)
    manifest = coordinator.selection_manifest()
    assert len({c.selected_state.sha256 for c in manifest.cells}) == 1
    sealed = freeze(store, manifest)
    selected = manifest.cells[0]
    grant = ConfirmationGrant(
        spec.digest,
        selected.cell_digest,
        task.partition_digest,
        H,
        outcome.digest,
        selected.model.sha256,
        sealed,
        (ResourceCap("scientific_starts", "count", 1, "reservation"),),
    )
    calls = []

    def authored_score(*_):
        calls.append(1)
        return PublicScore("success", outcome.name, outcome.units, 3.0, True)

    service = ConfirmationService(store, authored_score, scorer_digest=H, outcome_contract=outcome)
    receipt = service.confirm(grant)
    assert service.confirm(grant) == receipt and calls == [1]
    assert len(frozen_baseline_allocations(store)) == 1


def test_cli_runs_resumes_and_freezes_reference_suite(tmp_path):
    import json
    from click.testing import CliRunner
    from autoengineering.cli import cli

    store, plan, source = baseline_setup(tmp_path)
    path = tmp_path / "reference-plan.json"
    path.write_text(plan.to_json())
    args = [str(store.root), str(path), "--source-root", str(source), "--scripted-development"]
    runner = CliRunner()
    first = runner.invoke(cli, ["utility", "run", *args, "--max-new-cells", "1"])
    assert first.exit_code == 0, first.output
    resumed = runner.invoke(cli, ["utility", "resume", *args])
    assert resumed.exit_code == 0, resumed.output
    assert json.loads(resumed.output)["finished_cells"] == 4
    from autoengineering.utility.execution import ScriptedCoordinator

    manifest = ScriptedCoordinator(store, plan, source).selection_manifest()
    selected = tmp_path / "selection.json"
    selected.write_text(manifest.to_json())
    result = runner.invoke(cli, ["utility", "freeze", str(store.root), str(selected)])
    assert result.exit_code == 0, result.output
    assert len(science_reservations(store)) == 1


def test_legacy_policy_bytes_and_unknown_new_selection_mode_remain_strict(tmp_path):
    from autoengineering.utility.contracts import BaselineReusePolicy

    store, _, _ = baseline_setup(tmp_path, selection=False)
    policy = store.spec.baseline_reuse
    raw = policy.to_json()
    assert "selection_reuse" not in raw
    assert BaselineReusePolicy.from_json(raw).to_json() == raw
    with pytest.raises(ValueError):
        BaselineReusePolicy.from_dict(policy.to_dict() | {"selection_reuse": "none"})
    with pytest.raises(ValueError):
        replace(policy, schema="utility-baseline-reuse-v2")
