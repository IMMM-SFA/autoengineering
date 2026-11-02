"""Authored supervised routing tests fitting boundaries and frozen inference."""

from dataclasses import replace
from datetime import date, timedelta
import json
import math
from pathlib import Path

import numpy as np
import pytest

from autoengineering.adapters.python import run_lifecycle
from examples.leaf_river.models.pet_hamon import hamon_pet
from examples.leaf_river.models.soil_moisture import soil_bucket
from examples.utility.hydrology import physical_checks
from examples.utility.hydrology_learned import (
    LearnedRoutingAdapter,
    RoutingTrainingProfile,
    context,
    load_training,
)
from examples.utility.hydrology_site import HydrologySite


def fixture(tmp_path, cap=120):
    site = HydrologySite("utility-hydrology-site-v1", "authored", "basin", 40.0, 10.0)
    dates = tuple((date(2000, 1, 1) + timedelta(days=i)).isoformat() for i in range(120))
    profile = RoutingTrainingProfile(dates[:80], 10, (False,) * 10 + (True,) * 70, cap)
    scratch = tmp_path / "training"
    scratch.mkdir(mode=0o700)
    ctx = context(
        site,
        profile,
        dates,
        {"capacity": 100.0, "pet": "hamon"},
        scratch,
        warmup_mask=(True,) * 10 + (False,) * 110,
        scoring_mask=(False,) * 80 + (True,) * 40,
    )
    rng = np.random.default_rng(17)
    rain = rng.uniform(0.0, 70.0, 120)
    rain[::3] = 0.0
    forcing = {
        "precip_mm": rain,
        "tmean_c": np.full(120, 15.0),
        "tmin_c": np.full(120, 10.0),
        "tmax_c": np.full(120, 20.0),
        "day_of_year": np.arange(1, 121),
    }
    pet = hamon_pet(forcing["tmean_c"], forcing["day_of_year"], latitude=40.0)
    _, excess, _ = soil_bucket(rain, pet, 100.0, 50.0)
    truth, store = [], 0.0
    for water in excess:
        store += water
        q = store / (1 + math.exp(-(-1.3 + 1.1 * math.log1p(store / 100.0))))
        store -= q
        truth.append(q)
    mask = np.asarray(profile.valid_mask)
    data = {k: v[:80].copy() for k, v in forcing.items()} | {
        "labels": np.where(mask, np.asarray(truth[:80]), 0.0),
        "mask": mask,
    }
    return site, profile, ctx, forcing, data, np.asarray(truth)


def fit(site, profile, ctx, forcing, data):
    return run_lifecycle(
        LearnedRoutingAdapter(site, profile),
        ctx,
        forcing,
        ctx.model.inputs,
        ctx.model.outputs,
        fitting_data=data,
    )


def test_fits_supervised_routing_with_conservative_states_and_saved_cost(tmp_path):
    site, profile, ctx, forcing, data, truth = fixture(tmp_path)
    before = {k: v.copy() for k, v in data.items()}
    result = fit(site, profile, ctx, forcing, data)
    frozen = load_training(ctx.scratch_path, result.training.artifact)
    np.testing.assert_allclose(frozen.fit.coefficients, [-1.3, 1.1], atol=1e-6)
    np.testing.assert_allclose(result.outputs["prediction"][80:], truth[80:], atol=1e-6)
    assert all(c.status == "pass" for c in physical_checks(result.outputs, forcing, ctx.parameters))
    assert result.training.status == "trained"
    assert result.training.cost == frozen.fit.routing_rollouts
    assert 3 <= result.training.cost <= profile.max_rollouts
    assert frozen.fit.simulated_days == frozen.fit.routing_rollouts * 80
    receipt = json.loads((Path(ctx.scratch_path) / "training-result.json").read_bytes())
    assert receipt["status"] == "trained"
    assert receipt["routing_rollouts"] == result.training.cost
    assert receipt["partial_routing_work_unknown"] is False
    assert receipt["flux_preparation_runs"] == 1
    assert receipt["training_seconds"] >= frozen.fit.training_seconds >= 0
    for name in data:
        np.testing.assert_array_equal(data[name], before[name])


def test_frozen_inference_uses_no_labels_or_optimizer_and_replays_identically(
    tmp_path, monkeypatch
):
    import scipy.optimize

    site, profile, ctx, forcing, data, _ = fixture(tmp_path)
    trained = fit(site, profile, ctx, forcing, data)
    frozen = load_training(ctx.scratch_path, trained.training.artifact)

    def forbidden(*args, **kwargs):
        raise AssertionError("inference retrained")

    monkeypatch.setattr(scipy.optimize, "least_squares", forbidden)
    monkeypatch.setattr(LearnedRoutingAdapter, "_fit", forbidden)
    for _ in range(2):
        result = run_lifecycle(
            LearnedRoutingAdapter(site, profile, frozen),
            ctx,
            forcing,
            ctx.model.inputs,
            ctx.model.outputs,
        )
        assert result.training.status == "not_applicable" and result.training.cost is None
        assert result.training.artifact == frozen.artifact
        for name in trained.outputs:
            np.testing.assert_array_equal(result.outputs[name], trained.outputs[name])
    with pytest.raises(ValueError, match="cannot consume"):
        run_lifecycle(
            LearnedRoutingAdapter(site, profile, frozen),
            ctx,
            forcing,
            ctx.model.inputs,
            ctx.model.outputs,
            fitting_data=data,
        )


@pytest.mark.parametrize(
    "change", ["selection_labels", "warmup_label", "mask", "extra", "nonfinite"]
)
def test_training_accepts_only_the_declared_fitting_prefix(tmp_path, change):
    from pathlib import Path

    site, profile, ctx, forcing, data, _ = fixture(tmp_path)
    if change == "selection_labels":
        data = data | {"labels": np.ones(120)}
    elif change == "warmup_label":
        data["labels"][0] = 876543.210987
    elif change == "mask":
        data["mask"][-1] = False
    elif change == "extra":
        data["selection"] = np.ones(80)
    else:
        data["labels"][-1] = float("nan")
    with pytest.raises(ValueError) as error:
        fit(site, profile, ctx, forcing, data)
    assert "876543" not in str(error.value)
    receipt = json.loads((Path(ctx.scratch_path) / "training-result.json").read_bytes())
    assert receipt["status"] == "failed" and receipt["routing_rollouts"] == 0
    assert receipt["trained_artifact"] is None


def test_failed_budget_retains_work_and_refuses_another_start(tmp_path):
    from pathlib import Path

    site, profile, ctx, forcing, data, _ = fixture(tmp_path, cap=3)
    with pytest.raises(ValueError, match="training failed"):
        fit(site, profile, ctx, forcing, data)
    root = Path(ctx.scratch_path)
    original = (root / "training-result.json").read_bytes()
    receipt = json.loads(original)
    assert receipt["routing_rollouts"] == receipt["completed_routing_rollouts"] == 3
    assert receipt["reserved_routing_days"] == receipt["completed_routing_days"] == 240
    assert receipt["trained_artifact"] is None
    with pytest.raises(FileExistsError):
        fit(site, profile, ctx, forcing, data)
    assert (root / "training-result.json").read_bytes() == original


def test_partial_route_failure_is_charged_and_does_not_invent_completed_days(tmp_path, monkeypatch):
    from pathlib import Path
    import examples.utility.hydrology_learned as module

    site, profile, ctx, forcing, data, _ = fixture(tmp_path)

    def interrupted(*args):
        assert (Path(ctx.scratch_path) / "training-intent.json").is_file()
        raise RuntimeError("PRIVATE-ERROR-CANARY")

    monkeypatch.setattr(module, "_route", interrupted)
    with pytest.raises(ValueError, match="^learned routing training failed$"):
        fit(site, profile, ctx, forcing, data)
    raw = (Path(ctx.scratch_path) / "training-result.json").read_bytes()
    receipt = json.loads(raw)
    assert b"PRIVATE-ERROR-CANARY" not in raw
    assert receipt["routing_rollouts"] == 1 and receipt["completed_routing_rollouts"] == 0
    assert receipt["partial_routing_work_unknown"] is True
    assert receipt["completed_routing_days"] == 0


def test_inference_requires_unchanged_prefix_model_seed_and_artifact(tmp_path):
    from pathlib import Path

    site, profile, ctx, forcing, data, _ = fixture(tmp_path)
    trained = fit(site, profile, ctx, forcing, data)
    frozen = load_training(ctx.scratch_path, trained.training.artifact)
    altered = dict(forcing) | {"precip_mm": forcing["precip_mm"].copy()}
    altered["precip_mm"][0] += 1
    with pytest.raises(ValueError, match="prefix drivers"):
        run_lifecycle(
            LearnedRoutingAdapter(site, profile, frozen),
            ctx,
            altered,
            ctx.model.inputs,
            ctx.model.outputs,
        )
    for bad in (
        replace(ctx, seed=18),
        replace(ctx, parameters={"capacity": 101.0, "pet": "hamon"}),
    ):
        with pytest.raises(ValueError, match="another model"):
            run_lifecycle(
                LearnedRoutingAdapter(site, profile, frozen),
                bad,
                forcing,
                bad.model.inputs,
                bad.model.outputs,
            )
    root = tmp_path / "corrupt"
    path = root / frozen.artifact.path
    path.parent.mkdir(parents=True)
    path.write_bytes((Path(ctx.scratch_path) / frozen.artifact.path).read_bytes() + b" ")
    with pytest.raises(ValueError):
        load_training(root, frozen.artifact)


def test_inference_can_extend_history_without_retraining(tmp_path):
    site, profile, ctx, forcing, data, _ = fixture(tmp_path)
    trained = fit(site, profile, ctx, forcing, data)
    frozen = load_training(ctx.scratch_path, trained.training.artifact)
    # A shorter development axis and a longer inference axis share the same fit.
    short = context(
        site,
        profile,
        ctx.model.inputs[0].time.dates[:90],
        dict(ctx.parameters),
        ctx.scratch_path,
        warmup_mask=(True,) * 10 + (False,) * 80,
        scoring_mask=(False,) * 80 + (True,) * 10,
    )
    result = run_lifecycle(
        LearnedRoutingAdapter(site, profile, frozen),
        short,
        {k: v[:90] for k, v in forcing.items()},
        short.model.inputs,
        short.model.outputs,
    )
    for name in ("prediction", "soil", "reservoir", "aet", "pet"):
        np.testing.assert_array_equal(result.outputs[name], trained.outputs[name][:90])


def test_uninformative_fitting_data_refuses_an_unidentified_model(tmp_path):
    from pathlib import Path

    site, profile, ctx, forcing, data, _ = fixture(tmp_path)
    data["precip_mm"][:] = 0.0
    data["labels"][:] = 0.0
    with pytest.raises(ValueError, match="training failed"):
        fit(site, profile, ctx, forcing, data)
    receipt = json.loads((Path(ctx.scratch_path) / "training-result.json").read_bytes())
    assert receipt["status"] == "failed" and receipt["trained_artifact"] is None


def test_profile_requires_usable_labels_and_a_bounded_daily_axis(tmp_path):
    _, profile, _, _, _, _ = fixture(tmp_path)
    for change in (
        {"valid_mask": (False,) * 80},
        {"warmup_rows": 80},
        {"max_rollouts": 1001},
        {"fitting_dates": (*profile.fitting_dates[:-1], "2000-12-31")},
    ):
        with pytest.raises(ValueError):
            replace(profile, **change)


def test_unresolved_training_intent_never_restarts_fitting(tmp_path, monkeypatch):
    site, profile, ctx, forcing, data, _ = fixture(tmp_path)
    path = Path(ctx.scratch_path) / "training-intent.json"
    raw = b'{"original_start":"unresolved"}'
    path.write_bytes(raw)

    def forbidden(*args, **kwargs):
        raise AssertionError("unresolved training restarted")

    monkeypatch.setattr(LearnedRoutingAdapter, "_fit", forbidden)
    with pytest.raises(FileExistsError):
        fit(site, profile, ctx, forcing, data)
    assert path.read_bytes() == raw
    assert not (Path(ctx.scratch_path) / "training-result.json").exists()


def test_prepared_training_excludes_selection_and_reserved_labels(tmp_path):
    from examples.utility.hydrology_partitions import (
        DailyHydrologyPlan,
        DailyHydrologyRow,
        DailyWindow,
        prepare,
    )
    from examples.utility.hydrology_learned import prepared_training

    _, _, ctx, forcing, _, truth = fixture(tmp_path)
    dates = ctx.model.inputs[0].time.dates
    plan = DailyHydrologyPlan(
        "utility-daily-hydrology-preparation-v1",
        "authored",
        "basin",
        "1" * 64,
        10.0,
        40.0,
        tuple(
            DailyWindow(role, dates[start], dates[end])
            for role, start, end in (
                ("warmup", 0, 9),
                ("fitting", 10, 79),
                ("selection", 80, 99),
                ("confirmation", 100, 119),
            )
        ),
        ("A",),
    )
    factor = 0.3048**3 * 86400 * 1000 / (10.0 * 1e6)
    rows = [
        DailyHydrologyRow(
            day, float(forcing["precip_mm"][i]), 10.0, 20.0, float(truth[i] / factor), "A"
        )
        for i, day in enumerate(dates)
    ]
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    prepare(plan, rows, public, private)
    document = json.loads((public / "forcing.json").read_bytes())
    fitting = json.loads((public / "fitting.json").read_bytes())
    site, profile, learned_ctx, inputs, training = prepared_training(
        plan, document, fitting, dict(ctx.parameters), ctx.scratch_path, max_rollouts=120
    )
    assert len(inputs["precip_mm"]) == 100 and len(training["labels"]) == 80
    assert len(profile.fitting_dates) == 80
    assert all(not value.flags.writeable for value in training.values())
    result = fit(site, profile, learned_ctx, inputs, training)
    np.testing.assert_allclose(result.outputs["prediction"][80:], truth[80:100], atol=1e-6)
    for wrong in (
        json.loads((public / "selection.json").read_bytes()),
        json.loads((private / "labels.json").read_bytes()),
    ):
        with pytest.raises(ValueError):
            prepared_training(
                plan, document, wrong, dict(ctx.parameters), ctx.scratch_path, max_rollouts=120
            )


def test_used_and_closed_inference_handles_refuse(tmp_path):
    site, profile, ctx, forcing, data, _ = fixture(tmp_path)
    trained = fit(site, profile, ctx, forcing, data)
    frozen = load_training(ctx.scratch_path, trained.training.artifact)
    adapter = LearnedRoutingAdapter(site, profile, frozen)
    handle = adapter.prepare(ctx)
    adapter.run(handle, forcing)
    with pytest.raises(ValueError, match="fresh handle"):
        adapter.run(handle, forcing)
    adapter.cleanup(handle)
    with pytest.raises(ValueError, match="closed"):
        adapter.run(handle, forcing)
