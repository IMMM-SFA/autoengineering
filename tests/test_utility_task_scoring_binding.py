"""Selection acceptance and confirmation outcome are distinct frozen contracts."""

from dataclasses import replace

import pytest

from autoengineering.utility.contracts import ResourceCap, TaskSpec, UtilitySuiteSpec
from autoengineering.utility.scoring import ConfirmationGrant, ConfirmationService, PublicScore
from test_utility_confirmation import selected_suite
from test_utility_contracts import H, suite


def prepared(tmp_path):
    from autoengineering.utility.contracts import ScoredTaskSpec
    from autoengineering.utility.outcomes import OutcomeSpec

    contract = OutcomeSpec("engineering-outcome-v1", "power", "W", "minimize", "mean", H)

    def transform(spec):
        task = spec.tasks[0]
        scored = ScoredTaskSpec.from_dict(
            task.to_dict()
            | {
                "schema": "utility-task-scoring-v2",
                "outcome_digest": H,
                "scoring_outcome_digest": contract.digest,
            }
        )
        return replace(spec, tasks=(scored,))

    store, manifest, actual = selected_suite(tmp_path, suite_transform=transform)
    assert actual == contract
    grant = ConfirmationGrant(
        store.spec.digest,
        manifest.cells[0].cell_digest,
        store.spec.tasks[0].partition_digest,
        H,
        contract.digest,
        manifest.cells[0].model.sha256,
        store.replay()["frozen"],
        (ResourceCap("scientific_starts", "count", 1, "reservation"),),
    )
    return store, grant, contract


def test_distinct_acceptance_and_outcome_confirm_without_relabeling(tmp_path):
    store, grant, contract = prepared(tmp_path)
    calls = []

    def scorer(*_):
        calls.append(1)
        return PublicScore("success", "power", "W", 3.0, True)

    service = ConfirmationService(store, scorer, scorer_digest=H, outcome_contract=contract)
    receipt = service.confirm(grant)
    assert receipt.score.value == 3 and calls == [1]
    assert store.spec.tasks[0].outcome_digest == H
    assert store.spec.tasks[0].scoring_outcome_digest == contract.digest != H
    assert service.confirm(grant) == receipt and calls == [1]


def test_legacy_task_and_suite_shape_and_digest_remain_exact():
    original = suite()
    raw = original.to_json()
    assert UtilitySuiteSpec.from_json(raw).to_json() == raw
    assert "scoring_outcome_digest" not in raw and '"schema":"utility-task' not in raw
    with pytest.raises(ValueError):
        TaskSpec.from_dict(original.tasks[0].to_dict() | {"scoring_outcome_digest": H})


def test_versioned_task_dispatch_and_nested_roundtrip(tmp_path):
    from autoengineering.utility.contracts import ScoredTaskSpec

    store, _, _ = prepared(tmp_path)
    task = store.spec.tasks[0]
    assert isinstance(TaskSpec.from_json(task.to_json()), ScoredTaskSpec)
    assert UtilitySuiteSpec.from_json(store.spec.to_json()) == store.spec
    changed = replace(task, scoring_outcome_digest="3" * 64)
    successor = replace(store.spec, tasks=(changed,))
    assert successor.digest != store.spec.digest
    from autoengineering.utility.store import SuiteStore

    with pytest.raises(ValueError):
        SuiteStore(store.root, expected=successor)


@pytest.mark.parametrize("kind", ["old_acceptance", "different_scoring"])
def test_wrong_grant_outcome_refuses_before_access(tmp_path, kind):
    store, grant, contract = prepared(tmp_path)
    changed = replace(grant, outcome_digest=H if kind == "old_acceptance" else "3" * 64)
    calls = []
    service = ConfirmationService(
        store, lambda *_: calls.append(1), scorer_digest=H, outcome_contract=contract
    )
    before = store.replay()["head"]
    with pytest.raises(ValueError):
        service.confirm(changed)
    assert not calls and store.replay()["head"] == before
    assert not store.replay()["confirmation_accesses"]


def test_executed_engineering_selection_reaches_distinct_confirmation_contract(tmp_path):
    from autoengineering.utility.contracts import ScoredTaskSpec
    from autoengineering.utility.engineering_execution import ScriptedEngineeringCoordinator
    from autoengineering.utility.confirmation import freeze
    from autoengineering.utility.store import SuiteStore
    from test_utility_engineering_execution import setup

    original, plan, source = setup(tmp_path, kinds=("baseline",))
    rules = plan.campaigns[0].campaign.execution.study.rules
    outcome = next(o for o in rules.outcomes if o.name == rules.primary_metric)
    legacy = original.spec.tasks[0]
    assert legacy.outcome_digest == rules.digest != outcome.digest
    task = ScoredTaskSpec.from_dict(
        legacy.to_dict()
        | {
            "schema": "utility-task-scoring-v2",
            "scoring_outcome_digest": outcome.digest,
        }
    )
    store = SuiteStore.create(tmp_path / "scored-suite", replace(original.spec, tasks=(task,)))
    coordinator = ScriptedEngineeringCoordinator(store, plan, source)
    assert coordinator.run()["finished_cells"] == 1
    manifest = coordinator.selection_manifest()
    assert manifest.cells[0].status == "selected"
    frozen = freeze(store, manifest)
    selected = manifest.cells[0]
    grant = ConfirmationGrant(
        store.spec.digest,
        selected.cell_digest,
        task.partition_digest,
        H,
        outcome.digest,
        selected.model.sha256,
        frozen,
        (ResourceCap("scientific_starts", "count", 1, "reservation"),),
    )
    calls = []

    def authored_score(*_):
        calls.append(1)
        return PublicScore("success", outcome.name, outcome.units, 3.0, True)

    receipt = ConfirmationService(
        store, authored_score, scorer_digest=H, outcome_contract=outcome
    ).confirm(grant)
    assert receipt.score.outcome == outcome.name and receipt.score.units == outcome.units
    assert calls == [1] and store.spec.tasks[0].outcome_digest == rules.digest


def test_new_task_schema_requires_its_explicit_scoring_binding():
    legacy = suite().tasks[0].to_dict()
    with pytest.raises(ValueError):
        TaskSpec.from_dict(legacy | {"schema": "utility-task-scoring-v2"})
    with pytest.raises(ValueError):
        TaskSpec.from_dict(legacy | {"schema": "unknown-task", "scoring_outcome_digest": H})
