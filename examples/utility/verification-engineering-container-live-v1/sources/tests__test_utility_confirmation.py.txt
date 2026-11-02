"""A complete immutable barrier is required before any private scoring path."""

from dataclasses import replace

import pytest

from autoengineering.campaign.store import StoreError
from autoengineering.utility.confirmation import (
    SelectionManifest,
    SelectedCell,
    freeze,
    read_manifest,
)
from autoengineering.utility.store import SuiteStore
from test_utility_contracts import suite
from test_utility_store import operation


def unattempted(spec):
    return SelectionManifest(
        "utility-selection-v1",
        spec.digest,
        spec.protocol_digest,
        [
            SelectedCell(
                c.digest, "not_attempted", None, None, None, "Required runtime unavailable"
            )
            for c in spec.cells
        ],
    )


def test_barrier_covers_entire_matrix_and_never_reopens(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    manifest = unattempted(spec)
    with pytest.raises(StoreError, match="complete ordered matrix"):
        freeze(store, replace(manifest, cells=manifest.cells[:1]))
    identity = freeze(store, manifest)
    assert freeze(store, manifest) == identity
    assert read_manifest(store.root, identity) == manifest
    with store.writer(), pytest.raises(StoreError):
        store.append(**operation(spec))
    with pytest.raises(StoreError, match="already frozen"):
        freeze(
            store,
            replace(
                manifest, cells=(replace(manifest.cells[0], reason="changed"), manifest.cells[1])
            ),
        )


def test_pending_work_cannot_be_hidden_as_not_attempted(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    with store.writer():
        store.append(**operation(spec))
    with pytest.raises(StoreError, match="attempted cell"):
        freeze(store, unattempted(spec))


@pytest.mark.parametrize("boundary", ["before_selection_freeze", "after_selection_freeze"])
def test_freeze_commit_interruption_is_idempotent(tmp_path, boundary):
    spec = suite()

    def fail(stage):
        if stage == boundary:
            raise RuntimeError("owner lost")

    store = SuiteStore.create(tmp_path / "suite", spec, fault=fail)
    manifest = unattempted(spec)
    with pytest.raises(RuntimeError):
        freeze(store, manifest)
    resumed = SuiteStore(store.root)
    identity = freeze(resumed, manifest)
    assert resumed.replay()["frozen"] == identity
    assert len(resumed.replay()["events"]) == 1


def test_manifest_tamper_blocks_replay(tmp_path):
    spec = suite()
    store = SuiteStore.create(tmp_path / "suite", spec)
    identity = freeze(store, unattempted(spec))
    path = store.root / f"artifacts/{identity}/selection.json"
    path.write_text(path.read_text().replace("Required runtime", "Different runtime"))
    with pytest.raises(StoreError, match="content changed"):
        SuiteStore(store.root).replay()


def test_finished_children_pin_barrier_evidence(tmp_path):
    from test_utility_controller import prepared, run_case
    from test_agent_batch import finish

    c, identity, first_cell, _, bindings = prepared(tmp_path)
    c.dispatch(identity, first_cell, run_case)
    second_cell = bindings[1].cell_digest
    c.dispatch(identity, second_cell, lambda child, case: finish(child, id=case))
    state = c.store.replay()
    cells = []
    for cell in c.store.spec.cells:
        attempt_id = "child-" + cell.digest[:48]
        terminal = next(
            e for e in state["events"] if e.operation == "finish" and e.attempt_id == attempt_id
        )
        cells.append(
            SelectedCell(
                cell.digest,
                "no_eligible_model",
                attempt_id,
                terminal.result_digest,
                None,
                "Authored no-candidate fixture",
            )
        )
    manifest = SelectionManifest(
        "utility-selection-v1", c.store.spec.digest, c.store.spec.protocol_digest, cells
    )
    result = freeze(c.store, manifest)
    assert c.store.replay()["frozen"] == result
    child, _ = c._child(identity)
    original = child.replay().finished["first"].evidence[0]
    (child.root / original.path).write_text("altered")
    with pytest.raises(ValueError):
        SuiteStore(c.store.root).replay()


def selected_suite(
    tmp_path,
    analysis_plan=None,
    *,
    source_metadata_padding=0,
    outcome_name="power",
    confirmation_active_time=0,
    all_selected=False,
    baseline_routes=False,
    suite_transform=None,
    before_selection=None,
    model_override=None,
    selected_configuration=None,
    outcome_contract_override=None,
):
    from dataclasses import replace
    from autoengineering.campaign.artifacts import reference, put_bytes
    from autoengineering.campaign.records import ModelSnapshot, PortContract
    from autoengineering.utility.controller import UtilityController, CaseBinding
    from test_agent_batch import specification, finish
    from test_utility_contracts import H

    (tmp_path / "source.py").write_text("# source\n")
    source = reference(tmp_path, "source.py", media_type="text/plain", producer="fixture")
    if source_metadata_padding:
        source = replace(source, metadata={"authored_padding": "x" * source_metadata_padding})
    model = ModelSnapshot(
        H,
        {"component": "supplied"},
        (source,),
        H,
        (),
        (PortContract("value", (), "W", "float", (), "scalar", H, None),),
    )
    model = model_override if model_override is not None else model
    configuration = {} if selected_configuration is None else selected_configuration
    spec = suite()
    from autoengineering.utility.outcomes import OutcomeSpec

    contract = outcome_contract_override or OutcomeSpec(
        "engineering-outcome-v1", outcome_name, "W", "minimize", "mean", H
    )
    outcome_name = contract.name
    spec = replace(
        spec,
        tasks=(
            replace(
                spec.tasks[0], candidate_digests=(model.digest,), outcome_digest=contract.digest
            ),
        ),
    )
    if baseline_routes:
        spec = replace(spec, routes=tuple(replace(r, kind="baseline") for r in spec.routes))
    if confirmation_active_time:
        from autoengineering.utility.contracts import ResourceCap

        budget = spec.budgets[0]
        spec = replace(
            spec,
            budgets=(
                replace(
                    budget,
                    confirmation_reserve=(
                        *budget.confirmation_reserve,
                        ResourceCap("active_time", "s", confirmation_active_time, "reservation"),
                    ),
                ),
            ),
        )
    if analysis_plan is not None:
        spec = replace(spec, analysis_digest=analysis_plan.digest)
    if suite_transform is not None:
        spec = suite_transform(spec)
    store = SuiteStore.create(tmp_path / "suite", spec)
    if before_selection is not None:
        before_selection(store)
    (store.root / "source.py").write_bytes((tmp_path / "source.py").read_bytes())
    snapshot = put_bytes(
        store.root,
        model.to_json().encode(),
        name="model.json",
        media_type="application/json",
        producer="fixture",
    )
    batch = specification()
    batch = replace(
        batch, cases=tuple(replace(case, configuration_digest=H) for case in batch.cases)
    )
    bindings = tuple(
        CaseBinding(cell.digest, case.id) for cell, case in zip(spec.cells, batch.cases)
    )
    controller = UtilityController(store)
    child = controller.prepare_batch(batch, bindings)
    first = spec.cells[0]

    from autoengineering.utility.confirmation import SelectedState
    from autoengineering.campaign.records import EvaluationRecord

    evaluation = EvaluationRecord(
        "selected-evaluation",
        model.digest,
        configuration,
        "success",
        {outcome_name: 1.0},
        (),
        (),
        "selection",
        "selected-attempt",
        0.0,
        {},
    )
    state = SelectedState("utility-selected-state-v1", model, configuration, evaluation)
    state_ref = put_bytes(
        store.root,
        state.to_json().encode(),
        name="selected-state.json",
        media_type="application/json",
        producer="fixture",
    )

    def select(child, case):
        from autoengineering.utility.confirmation import selected_artifact_evidence

        child.finish_case(
            case,
            "passed",
            (
                selected_artifact_evidence(child, snapshot, model.to_dict(), "model"),
                selected_artifact_evidence(child, state_ref, state.to_dict(), "selected_state"),
            ),
        )

    controller.dispatch(child.root.name, first.digest, select)
    controller.dispatch(
        child.root.name,
        spec.cells[1].digest,
        select if all_selected else lambda child, case: finish(child, id=case),
    )
    choices = []
    for i, cell in enumerate(spec.cells):
        attempt_id = "child-" + cell.digest[:48]
        event = next(
            e
            for e in store.replay()["events"]
            if e.operation == "finish" and e.attempt_id == attempt_id
        )
        choices.append(
            SelectedCell(
                cell.digest,
                "selected" if i == 0 or all_selected else "no_eligible_model",
                attempt_id,
                event.result_digest,
                snapshot if i == 0 or all_selected else None,
                "Authored selection fixture",
                state_ref if i == 0 or all_selected else None,
            )
        )
    manifest = SelectionManifest("utility-selection-v2", spec.digest, spec.protocol_digest, choices)
    freeze(store, manifest)
    assert store.replay()["frozen"] is not None
    return store, manifest, contract


def test_selected_snapshot_requires_child_attestation_and_frozen_candidate(tmp_path):
    store, _, _ = selected_suite(tmp_path)
    (store.root / "source.py").write_text("tampered source")
    with pytest.raises(ValueError):
        SuiteStore(store.root).replay()


def test_selected_parameters_must_match_evaluation_and_attested_state(tmp_path):
    from dataclasses import replace
    from autoengineering.campaign.artifacts import read_bytes
    from autoengineering.utility.confirmation import SelectedState

    store, manifest, _ = selected_suite(tmp_path)
    selected = manifest.cells[0]
    state = SelectedState.from_json(read_bytes(store.root, selected.selected_state).decode())
    with pytest.raises(ValueError, match="exact configuration"):
        replace(state, configuration={"changed": 1.0})
    with pytest.raises(ValueError, match="different scientific model"):
        replace(state, evaluation=replace(state.evaluation, model_id="other-model"))
    (store.root / selected.selected_state.path).write_text(
        state.to_json().replace('"configuration":{}', '"configuration":{"changed":1}')
    )
    with pytest.raises(ValueError):
        SuiteStore(store.root).replay()


def test_legacy_selected_manifests_cannot_omit_parameter_state():
    from autoengineering.campaign.records import ArtifactRef
    from test_utility_contracts import H

    artifact = ArtifactRef("model.json", H, 1, "application/json", "fixture", {})
    with pytest.raises(ValueError, match="parameter/evaluation"):
        SelectedCell(H, "selected", "attempt", H, artifact, "Unbound legacy fixture")


def test_large_selected_artifacts_seal_without_expanding_batch_receipts(tmp_path):
    from autoengineering.utility.controller import UtilityController

    store, manifest, _ = selected_suite(tmp_path, source_metadata_padding=70000)
    selected = manifest.cells[0]
    assert selected.model.size_bytes > 65536 and selected.selected_state.size_bytes > 65536
    state = store.replay()
    allocation, _ = state["attempts"][selected.attempt_id]
    child, bindings = UtilityController(store)._child(allocation.child_digest)
    case = next(b.case_id for b in bindings if b.cell_digest == selected.cell_digest)
    assert all(ref.size_bytes <= 65536 for ref in child.replay().finished[case].evidence)
    with pytest.raises(ValueError, match="schema v2"):
        replace(manifest, schema="utility-selection-v1")
    (store.root / selected.selected_state.path).write_text("tampered")
    with pytest.raises(ValueError):
        store.replay()


def test_large_selected_binding_requires_exact_kind_and_identity(tmp_path):
    from autoengineering.utility.confirmation import (
        has_selected_artifact_evidence,
        SelectedArtifactBinding,
    )
    from autoengineering.campaign.artifacts import put_bytes
    from types import SimpleNamespace

    (tmp_path / "artifacts").mkdir(mode=0o700)
    artifact = put_bytes(
        tmp_path, b"x" * 70000, name="large.json", media_type="application/json", producer="fixture"
    )
    proof = SelectedArtifactBinding("utility-selected-artifact-binding-v1", "model", artifact)
    receipt = put_bytes(
        tmp_path,
        proof.to_json().encode(),
        name="receipt.json",
        media_type="application/json",
        producer="fixture",
    )
    child = SimpleNamespace(root=tmp_path)
    assert has_selected_artifact_evidence(child, (receipt,), artifact, "model", allow_bindings=True)
    assert not has_selected_artifact_evidence(
        child, (receipt,), artifact, "selected_state", allow_bindings=True
    )
    assert not has_selected_artifact_evidence(
        child, (receipt,), replace(artifact, size_bytes=70001), "model", allow_bindings=True
    )
    assert not has_selected_artifact_evidence(
        child, (receipt,), artifact, "model", allow_bindings=False
    )


def test_selected_artifact_binding_refuses_mismatched_payload(tmp_path):
    from autoengineering.utility.confirmation import selected_artifact_evidence
    from autoengineering.campaign.artifacts import put_bytes
    from types import SimpleNamespace

    (tmp_path / "artifacts").mkdir(mode=0o700)
    artifact = put_bytes(
        tmp_path, b"x" * 70000, name="large.json", media_type="application/json", producer="fixture"
    )
    with pytest.raises(StoreError, match="differs"):
        selected_artifact_evidence(SimpleNamespace(), artifact, {"different": True}, "model")
