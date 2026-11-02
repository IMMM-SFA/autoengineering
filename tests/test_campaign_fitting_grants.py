"""Fitting permission binds one original attempt and never grants other labels."""

from dataclasses import replace
import json
from pathlib import Path

import pytest

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.campaign.artifacts import read_arrays, put_bytes
from autoengineering.campaign.spec import CampaignSpec, TrainingSpec
from autoengineering.campaign.training import FittingGrant, worker_fitting_data
from autoengineering.utility.campaign_costs import join_campaign_costs
from test_utility_campaign_training_costs import setup, CELL


def test_worker_grant_checks_identity_and_reservation_before_reading_labels(tmp_path, monkeypatch):
    import autoengineering.campaign.training as module

    _, controller = setup(tmp_path, monkeypatch)
    job_path = controller.store.root / "jobs/attempt-000001.json"
    job = json.loads(job_path.read_text())
    context = PrepareContext.from_dict(job["context"])
    forcing = read_arrays(controller.bundle, controller._data("forcing").artifact)
    original = module.read_arrays
    reads = []

    def only_fitting(root, ref):
        assert ref == controller._data("fitting").artifact
        reads.append(ref)
        return original(root, ref)

    monkeypatch.setattr(module, "read_arrays", only_fitting)
    payload = worker_fitting_data(job_path, job, context, controller.bundle, forcing)
    assert len(reads) == 1
    assert len(payload["labels"]) == 80 and not payload["labels"][:10].any()
    assert set(payload) == set(forcing) | {"labels", "mask"}
    reads.clear()
    variants = [
        (dict(job, nonce="forged"), context),
        (dict(job, attempt_id="attempt-000999"), context),
        (dict(job, role="confirmation"), context),
        (dict(job, fitting_grant=None), context),
        (dict(job, adapter_id="linear"), context),
        (job, replace(context, seed=context.seed + 1)),
        (job, replace(context, permitted_data_ids=("comparison",))),
        (job, replace(context, parameters=dict(context.parameters) | {"capacity": 101.0})),
    ]
    for changed, ctx in variants:
        with pytest.raises(ValueError):
            worker_fitting_data(job_path, changed, ctx, controller.bundle, forcing)
        assert not reads

    # A newly hashed grant matching a forged job still lacks the original commit.
    from autoengineering.campaign.records import ArtifactRef
    from autoengineering.campaign.artifacts import read_bytes

    grant = FittingGrant.from_json(
        read_bytes(controller.store.root, ArtifactRef.from_dict(job["fitting_grant"])).decode()
    )
    forged = replace(grant, nonce="forged")
    ref = put_bytes(
        controller.store.root,
        forged.to_json().encode(),
        name="fitting-grant.json",
        media_type="application/json",
        producer=grant.attempt_id,
    )
    with pytest.raises(ValueError, match="original attempt reservation"):
        worker_fitting_data(
            job_path,
            dict(job, nonce="forged", fitting_grant=ref.to_dict()),
            replace(
                context,
                scratch_path=str(controller.store.root / "jobs" / f"{grant.attempt_id}-forged"),
            ),
            controller.bundle,
            forcing,
        )
    assert not reads


def test_two_actual_fits_keep_distinct_attempt_scratch_and_original_costs(tmp_path, monkeypatch):
    batch, controller = setup(tmp_path, monkeypatch, science=2)
    first = json.loads((controller.store.root / "jobs/attempt-000001.json").read_text())
    first_intent = Path(first["context"]["scratch_path"]) / "training-intent.json"
    saved = first_intent.read_bytes()
    with controller.store.writer():
        state = controller.state()
        state = replace(state, budget=state.budget.reserve("authored-second", 1))
        controller._checkpoint("evaluating", state, "authored_second_reservation")
        controller.remaining = 1
        base = controller.spec.baseline
        result = controller._physical_attempt(
            base.model.digest,
            base.model,
            base.adapter_id,
            base.parameters,
            "comparison",
            "authored-second",
        )
    assert result.status == "success"
    second = json.loads((controller.store.root / "jobs/attempt-000002.json").read_text())
    assert first["context"]["scratch_path"] != second["context"]["scratch_path"]
    assert first_intent.read_bytes() == saved
    costs = join_campaign_costs(batch, {"model": CELL})
    starts = [r for r in costs if r.resource == "training_starts"]
    assert len(starts) == 2 and sum(r.quantity for r in starts) == 2
    assert len({r.receipt_id for r in starts}) == 2
    assert batch.report()["scientific_reservations_charged"] == 2


def test_legacy_schema_keeps_exact_fields_and_cannot_request_training():
    from examples.campaign_contracts.build_fixture import fixture

    legacy = fixture()
    raw = legacy.to_dict()
    assert "training" not in raw
    assert CampaignSpec.from_dict(raw).to_dict() == raw
    with pytest.raises(ValueError):
        CampaignSpec.from_dict(dict(raw, training=None))
    with pytest.raises(ValueError):
        replace(legacy, training=TrainingSpec("daily-prefix-supervised-v1", ("linear",), "fitting"))
    with pytest.raises(ValueError):
        replace(legacy, schema_version="1.1")


def test_training_policy_rejects_nonfitting_and_unknown_exposure(tmp_path, monkeypatch):
    _, controller = setup(tmp_path, monkeypatch)
    spec = controller.spec
    assert CampaignSpec.from_json(spec.to_json()) == spec
    for role in ("comparison", "confirmation", "development_replay"):
        with pytest.raises(ValueError, match="exposed fitting"):
            replace(
                spec,
                data=tuple(replace(d, role=role) if d.id == "fitting" else d for d in spec.data),
            )
    for exposure in ("unknown", "unexposed"):
        with pytest.raises(ValueError, match="exposed fitting"):
            replace(
                spec,
                data=tuple(
                    replace(d, prior_exposure=exposure) if d.id == "fitting" else d
                    for d in spec.data
                ),
            )
