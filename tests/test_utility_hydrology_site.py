"""Authored basin forcing exercises latitude, conservation and partition boundaries."""

from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json

import numpy as np
import pytest

from autoengineering.adapters.python import run_lifecycle
from examples.leaf_river.models.pet_hamon import hamon_pet
from examples.leaf_river.models.pet_hargreaves import hargreaves_pet
from examples.utility.hydrology import BASELINE, physical_checks
from examples.utility.hydrology_site import (
    HydrologySite,
    SiteHydrologyAdapter,
    context,
    prepared_development,
)


def fixture(tmp_path, family="hamon"):
    site = HydrologySite("utility-hydrology-site-v1", "authored", "authored-basin", 45.0, 123.0)
    dates = [(date(2000, 6, 1) + timedelta(days=i)).isoformat() for i in range(12)]
    parameters = BASELINE | {"pet": family}
    ctx = context(
        site,
        dates,
        parameters,
        tmp_path,
        warmup_mask=[True] * 2 + [False] * 10,
        scoring_mask=[False] * 2 + [True] * 10,
    )
    forcing = {
        "precip_mm": np.array([100.0, 0.0, 30.0, 60.0] * 3),
        "tmean_c": np.full(12, 20.0),
        "tmin_c": np.full(12, 10.0),
        "tmax_c": np.full(12, 30.0),
        "day_of_year": np.arange(153, 165),
    }
    return site, ctx, forcing


@pytest.mark.parametrize("family", ["hamon", "hargreaves"])
def test_site_latitude_and_independent_daily_balance(tmp_path, family):
    site, ctx, forcing = fixture(tmp_path, family)
    before = {name: value.copy() for name, value in forcing.items()}
    result = run_lifecycle(
        SiteHydrologyAdapter(site), ctx, forcing, ctx.model.inputs, ctx.model.outputs
    )
    args = (
        (forcing["tmean_c"], forcing["day_of_year"])
        if family == "hamon"
        else (forcing["tmean_c"], forcing["tmax_c"], forcing["tmin_c"], forcing["day_of_year"])
    )
    function = hamon_pet if family == "hamon" else hargreaves_pet
    expected_pet = function(*args, latitude=site.latitude_deg)
    np.testing.assert_allclose(result.outputs["pet"], expected_pet, rtol=1e-13)
    assert not np.allclose(result.outputs["pet"], function(*args))
    # Independent scalar recurrence checks stores as well as the exposed fluxes.
    soil, reservoir = 50.0, 0.0
    for i, (precip, pet) in enumerate(zip(forcing["precip_mm"], expected_pet)):
        soil += precip
        aet = min(pet * min(soil / 100.0, 1.0), soil)
        soil -= aet
        reservoir += max(soil - 100.0, 0.0)
        soil = min(soil, 100.0)
        discharge = 0.3 * reservoir
        reservoir -= discharge
        for name, value in (
            ("soil", soil),
            ("reservoir", reservoir),
            ("aet", aet),
            ("prediction", discharge),
        ):
            assert result.outputs[name][i] == pytest.approx(value, abs=1e-12)
    assert all(
        check.status == "pass" for check in physical_checks(result.outputs, forcing, ctx.parameters)
    )
    assert result.training.status == "not_applicable"
    np.testing.assert_allclose(result.diagnostics["final_stores"], [soil, reservoir])
    for name in forcing:
        np.testing.assert_array_equal(forcing[name], before[name])
    assert dict(ctx.parameters) == BASELINE | {"pet": family}


@pytest.mark.parametrize(
    "change",
    [{"area_km2": 0.0}, {"latitude_deg": 80.0}, {"latitude_deg": True}, {"area_km2": float("nan")}],
)
def test_invalid_site_metadata(change):
    with pytest.raises((ValueError, TypeError)):
        HydrologySite.from_dict(
            {
                "schema": "utility-hydrology-site-v1",
                "source_id": "authored",
                "site_id": "basin",
                "latitude_deg": 40.0,
                "area_km2": 1.0,
            }
            | change
        )


def test_fresh_handles_replay_and_used_or_closed_handles_refuse(tmp_path):
    site, ctx, forcing = fixture(tmp_path)
    adapter = SiteHydrologyAdapter(site)
    handle = adapter.prepare(ctx)
    first = adapter.run(handle, forcing)
    with pytest.raises(ValueError, match="cannot run twice"):
        adapter.run(handle, forcing)
    second = adapter.run(adapter.prepare(ctx), forcing)
    for name in first:
        np.testing.assert_array_equal(first[name], second[name])
    adapter.cleanup(handle)
    with pytest.raises(ValueError, match="closed"):
        adapter.run(handle, forcing)


@pytest.mark.parametrize("change", ["site", "units", "timing", "implementation"])
def test_metadata_mismatch_refuses_before_physics(tmp_path, monkeypatch, change):
    import examples.utility.hydrology_site as module

    site, ctx, forcing = fixture(tmp_path)
    model = ctx.model
    if change == "site":
        site = replace(site, latitude_deg=44.0)
    elif change == "units":
        model = replace(model, inputs=(replace(model.inputs[0], units="mm/day"), *model.inputs[1:]))
    elif change == "timing":
        model = replace(
            model,
            inputs=(
                replace(
                    model.inputs[0], time=replace(model.inputs[0].time, semantics="interval_mean")
                ),
                *model.inputs[1:],
            ),
        )
    else:
        model = replace(model, implementations=dict(model.implementations) | {"routing": "other"})

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid metadata reached science")

    monkeypatch.setattr(module, "hamon_pet", forbidden)
    adapter = SiteHydrologyAdapter(site)
    with pytest.raises(ValueError):
        adapter.run(adapter.prepare(replace(ctx, model=model)), forcing)


@pytest.mark.parametrize(
    "name,value",
    [("precip_mm", -1.0), ("tmean_c", 50.0), ("day_of_year", 1.0), ("tmax_c", float("nan"))],
)
def test_invalid_forcing_refuses_before_physics(tmp_path, monkeypatch, name, value):
    import examples.utility.hydrology_site as module

    site, ctx, forcing = fixture(tmp_path)
    forcing[name] = np.full(12, value)

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid forcing reached science")

    monkeypatch.setattr(module, "hamon_pet", forbidden)
    adapter = SiteHydrologyAdapter(site)
    with pytest.raises(ValueError):
        adapter.run(adapter.prepare(ctx), forcing)


def test_preparation_bridge_replays_development_only(tmp_path, monkeypatch):
    from examples.utility.hydrology_partitions import (
        DailyHydrologyPlan,
        DailyHydrologyRow,
        DailyWindow,
        prepare,
    )
    from pathlib import Path

    dates = ["2000-02-27", "2000-02-28", "2000-02-29", "2000-03-01"]
    plan = DailyHydrologyPlan(
        "utility-daily-hydrology-preparation-v1",
        "authored",
        "basin",
        "1" * 64,
        123.0,
        45.0,
        tuple(
            DailyWindow(role, day, day)
            for role, day in zip(("warmup", "fitting", "selection", "confirmation"), dates)
        ),
        ("A",),
    )
    rows = [DailyHydrologyRow(day, 100.0, 10.0, 20.0, 1.0, "A") for day in dates]
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    manifest = prepare(plan, rows, public, private)
    raw = (public / "forcing.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == manifest["files"]["forcing.json"]
    document = json.loads(raw)
    reserved = json.loads((private / "forcing.json").read_bytes())
    read = Path.open

    def guarded(path, *args, **kwargs):
        if private in path.parents or path.name in ("fitting.json", "selection.json"):
            raise AssertionError("adapter attempted a private or label read")
        return read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    for role, mask in (("fitting", (False, True, False)), ("selection", (False, False, True))):
        site, ctx, forcing = prepared_development(plan, document, BASELINE, tmp_path, role=role)
        assert ctx.model.inputs[0].time.scoring_mask == mask
        assert ctx.model.inputs[0].time.warmup_mask == (True, False, False)
        assert site.latitude_deg == 45.0 and site.area_km2 == 123.0
        assert set(forcing) == set(document) - {"dates"}
        assert all(not value.flags.writeable for value in forcing.values())
        result = run_lifecycle(
            SiteHydrologyAdapter(site), ctx, forcing, ctx.model.inputs, ctx.model.outputs
        )
        assert all(
            check.status == "pass" for check in physical_checks(result.outputs, forcing, BASELINE)
        )
    for bad in (
        reserved,
        document | {"labels": [1.0, 2.0, 3.0]},
        document | {"tmean_c": [16.0] * 3},
    ):
        with pytest.raises(ValueError):
            prepared_development(plan, bad, BASELINE, tmp_path, role="selection")
    with pytest.raises(ValueError):
        prepared_development(plan, document, BASELINE, tmp_path, role="confirmation")


def test_site_metadata_changes_snapshot_identity(tmp_path):
    site, ctx, _ = fixture(tmp_path)
    for change in ({"area_km2": 124.0}, {"latitude_deg": 44.0}, {"site_id": "other-basin"}):
        other = context(
            replace(site, **change),
            ctx.model.inputs[0].time.dates,
            BASELINE,
            tmp_path,
            warmup_mask=ctx.model.inputs[0].time.warmup_mask,
            scoring_mask=ctx.model.inputs[0].time.scoring_mask,
        )
        assert other.model.digest != ctx.model.digest
        assert other.model.graph_digest != ctx.model.graph_digest
