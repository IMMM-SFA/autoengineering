"""Actual registered routing workers and verified frozen inference."""

from dataclasses import replace
import json
from pathlib import Path

import numpy as np
import pytest

from autoengineering.adapters.contracts import TrainingArtifactBundle, TrainingResult
from autoengineering.agents.batch import BatchCase, BatchStore
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.campaign.artifacts import put_bytes, read_arrays, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.runtime import registry
from autoengineering.utility.campaign_costs import join_campaign_costs
from autoengineering.utility.confirmation import TrainedSelectedState, read_selected_state
from autoengineering.utility.trained_selection import RoutingSelectionArtifacts
from examples.utility.hydrology_runtime import ADAPTER_ID, PROFILE_PATH, RoutingRuntimeProfile
from test_utility_campaign_training_costs import setup, CELL
from test_agent_batch import specification


def selection(controller):
    evaluation = controller.state().evaluations[0]
    refs = tuple(r for e in controller.store.replay().events for r in e.artifacts)
    lifecycle = next(r for r in refs if r.sha256 == evaluation.provenance["lifecycle_record"])
    metadata = json.loads(read_bytes(controller.store.root, lifecycle))
    result = TrainingResult.from_dict(metadata["training"])
    bundle_ref = ArtifactRef.from_json(result.artifact.metadata["training_bundle"])
    bundle = TrainingArtifactBundle.from_json(
        read_bytes(controller.store.root, bundle_ref).decode()
    )
    by_name = {Path(r.path).name: r for r in bundle.companions}
    closure = RoutingSelectionArtifacts(
        "utility-routing-selection-artifacts-v1",
        bundle.primary,
        by_name["training-profile.json"],
        by_name["training-intent.json"],
        by_name["training-result.json"],
        bundle_ref,
        lifecycle,
    )
    return TrainedSelectedState(
        "utility-selected-state-v2",
        controller.spec.baseline.model,
        evaluation.configuration,
        evaluation,
        closure,
    )


@pytest.mark.parametrize("recover", [False, True])
def test_registered_worker_trains_and_retains_original_cost_without_helper_injection(
    tmp_path, monkeypatch, recover
):
    batch, controller = setup(tmp_path, monkeypatch, registered=True, recover=recover)
    assert controller.state().evaluations[0].status == "success"
    costs = join_campaign_costs(batch, {"model": CELL})
    assert next(r.quantity for r in costs if r.resource == "training_starts") == 1
    job = json.loads((controller.store.root / "jobs/attempt-000001.json").read_text())
    assert job["adapter_id"] == ADAPTER_ID and job["fitting_grant"]
    started = json.loads(
        (controller.store.root / "attempts/attempt-000001/action-start.json").read_text()
    )
    # Public selected-state verification works on a real registered worker's closure.
    bound = selection(controller)
    ref = put_bytes(
        controller.store.root,
        bound.to_json().encode(),
        name="selected-state.json",
        media_type="application/json",
        producer="author",
    )
    assert read_selected_state(controller.store.root, ref) == bound
    assert started["nonce"] == job["nonce"]
    assert (
        len(controller.state().budget.attempts)
        == batch.report()["scientific_reservations_charged"]
        == 1
    )


def frozen_campaign(tmp_path, original):
    source = tmp_path / "frozen-source"
    source.mkdir(mode=0o700)
    spec = original.spec
    for ref in (
        spec.baseline.system,
        spec.provenance.environment_lock,
        *spec.provenance.sources,
        *(d.artifact for d in spec.data),
    ):
        target = source / ref.path
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(read_bytes(original.bundle, ref))
    bound = selection(original)
    for ref in bound.training.references():
        target = source / ref.path
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.write_bytes(read_bytes(original.store.root, ref))
    selected = put_bytes(
        source,
        bound.to_json().encode(),
        name="selected-state.json",
        media_type="application/json",
        producer="author",
    )
    old = next(r for r in spec.provenance.sources if r.path == PROFILE_PATH)
    profile = RoutingRuntimeProfile.from_json(read_bytes(original.bundle, old).decode())
    (source / PROFILE_PATH).write_text(replace(profile, selected_state=selected).to_json())
    runtime = reference(source, PROFILE_PATH, media_type="application/json", producer="author")
    spec = replace(
        spec,
        schema_version="1.0",
        training=None,
        name="authored-frozen-routing",
        data=tuple(d for d in spec.data if d.role != "fitting"),
        provenance=replace(
            spec.provenance,
            sources=tuple(r for r in spec.provenance.sources if r.path != PROFILE_PATH)
            + (runtime, selected, *bound.training.references()),
        ),
    )
    spec.to_yaml(source / "campaign.yaml")
    batch = BatchStore.create(
        tmp_path / "frozen-batch",
        replace(specification(science=1), cases=(BatchCase("model", "comparison", CELL, 0, 1),)),
    )
    batch.start_case("model", CELL)
    parent = batch.root / "cases/model"
    parent.mkdir(mode=0o700)
    return batch, BatchCampaignController.create(
        source / "campaign.yaml", source, parent / "campaign", batch=batch, case_id="model"
    )


def test_registered_frozen_inference_reuses_verified_fit_without_training(tmp_path, monkeypatch):
    _, trained = setup(tmp_path, monkeypatch, registered=True)
    batch, frozen = frozen_campaign(tmp_path, trained)
    frozen.remaining = 1
    frozen.advance()
    assert frozen.state().evaluations[0].status == "success"
    training_outputs = read_arrays(trained.store.root, trained.state().evaluations[0].outputs[0])
    frozen_outputs = read_arrays(frozen.store.root, frozen.state().evaluations[0].outputs[0])
    for name, array in training_outputs.items():
        np.testing.assert_array_equal(frozen_outputs[name], array)
    job = json.loads((frozen.store.root / "jobs/attempt-000001.json").read_text())
    assert "fitting_grant" not in job and not job["context"]["permitted_data_ids"]
    scratch = Path(job["context"]["scratch_path"])
    assert not (scratch / "training-intent.json").exists()
    assert not (scratch / "training-result.json").exists()
    costs = join_campaign_costs(batch, {"model": CELL})
    assert not any(r.resource == "training_starts" for r in costs)
    assert next(r.quantity for r in costs if r.resource == "frozen_fit_inference_reuses") == 1
    assert (
        next(r.quantity for r in costs if r.resource == "unverified_training_preparation") is None
    )


def test_registered_profile_cannot_drop_fitting_permission_or_change_its_mask(
    tmp_path, monkeypatch
):
    _, controller = setup(tmp_path, monkeypatch, registered=True)
    spec = controller.spec
    with pytest.raises(ValueError, match="fitting permission"):
        registry(spec=replace(spec, schema_version="1.0", training=None), root=controller.bundle)
    data = next(d for d in spec.data if d.id == "fitting")
    clock = replace(data.ports[0].time, scoring_mask=(False,) * 11 + (True,) * 69)
    changed = replace(data, ports=(replace(data.ports[0], time=clock),))
    with pytest.raises(ValueError, match="fitting grant"):
        registry(
            spec=replace(spec, data=tuple(changed if d.id == data.id else d for d in spec.data)),
            root=controller.bundle,
        )


def test_frozen_runtime_requires_its_declared_original_closure(tmp_path, monkeypatch):
    from autoengineering.campaign.identity import verify_runtime_sources, SCIENTIFIC_CLOSURE
    from autoengineering.campaign.runtime import RUNTIME_ROOT

    _, trained = setup(tmp_path, monkeypatch, registered=True)
    _, frozen = frozen_campaign(tmp_path, trained)
    with pytest.raises(ValueError, match="fitting permission"):
        registry(
            spec=replace(
                frozen.spec,
                schema_version="1.1",
                training=trained.spec.training,
                data=trained.spec.data,
            ),
            root=frozen.bundle,
        )
    bound = selection(trained)
    missing = replace(
        frozen.spec,
        provenance=replace(
            frozen.spec.provenance,
            sources=tuple(r for r in frozen.spec.provenance.sources if r != bound.training.result),
        ),
    )
    with pytest.raises(ValueError, match="training closure"):
        registry(spec=missing, root=frozen.bundle)
    incomplete = replace(
        trained.spec,
        provenance=replace(
            trained.spec.provenance,
            sources=tuple(
                r
                for r in trained.spec.provenance.sources
                if r.path != "src/autoengineering/campaign/training.py"
            )
            + (
                reference(
                    RUNTIME_ROOT,
                    SCIENTIFIC_CLOSURE,
                    media_type="application/json",
                    producer="author",
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="engine source closure"):
        verify_runtime_sources(incomplete)
