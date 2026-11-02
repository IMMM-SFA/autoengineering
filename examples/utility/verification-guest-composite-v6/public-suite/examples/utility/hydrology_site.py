"""Explicit nonpolar basin metadata for the supplied bucket/reservoir equations.

No observations enter the adapter. The historical Leaf River wrapper and its
31.7 degree PET defaults remain unchanged. This profile calls the same PET and
soil functions with the declared site latitude and preserves conservative stores.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path
from typing import Literal

import numpy as np

from autoengineering.adapters.contracts import PrepareContext, validate_arrays
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ModelSnapshot, PortContract, TimeContract
from autoengineering.campaign.serialization import Record, digest
from autoengineering.utility.contracts import identifier
from autoengineering.utility.exposure import iso_date
from examples.campaign_contracts.hydrology import Handle, HydrologyAdapter, SOURCES
from examples.leaf_river.models.pet_hamon import hamon_pet
from examples.leaf_river.models.pet_hargreaves import hargreaves_pet
from examples.leaf_river.models.soil_moisture import soil_bucket

INPUTS = {
    "precip_mm": ("mm", "interval_total"),
    "tmean_c": ("degC", "interval_mean"),
    "tmax_c": ("degC", "instantaneous"),
    "tmin_c": ("degC", "instantaneous"),
    "day_of_year": ("day", "instantaneous"),
}
OUTPUTS = {
    "prediction": ("mm/day", "interval_mean"),
    "aet": ("mm/day", "interval_mean"),
    "pet": ("mm/day", "interval_mean"),
    "soil": ("mm", "instantaneous"),
    "reservoir": ("mm", "instantaneous"),
}


@dataclass(frozen=True)
class HydrologySite(Record):
    schema: Literal["utility-hydrology-site-v1"]
    source_id: str
    site_id: str
    latitude_deg: float
    area_km2: float

    def _validate(self):
        identifier(self.source_id)
        identifier(self.site_id)
        if not -66 <= self.latitude_deg <= 66:
            raise ValueError("supplied PET geometry does not admit polar sites")
        if self.area_km2 <= 0:
            raise ValueError("site basin area must be positive")


def _graph(site):
    return digest({"profile": "site-bucket-reservoir-v1", "site": site.digest})


def context(site, dates, parameters, scratch, *, warmup_mask, scoring_mask, source_root=None):
    if not isinstance(site, HydrologySite) or set(parameters) != {"capacity", "recession", "pet"}:
        raise ValueError("site hydrology needs its site and three declared parameters")
    dates = tuple(dates)
    parsed = tuple(iso_date(value) for value in dates)
    if not 1 <= len(parsed) <= 20000 or any(
        b - a != timedelta(days=1) for a, b in zip(parsed, parsed[1:])
    ):
        raise ValueError("site hydrology needs contiguous daily dates")
    time = TimeContract(
        dates,
        "interval_mean",
        "P1D",
        "proleptic_gregorian",
        "start",
        tuple(warmup_mask),
        tuple(scoring_mask),
    )

    def port(name, units, semantics="interval_mean", scalar=False):
        support = (
            None
            if scalar
            else replace(
                time,
                semantics=semantics,
                timestamp="end" if name in ("soil", "reservoir") else "start",
            )
        )
        return PortContract(
            name,
            () if scalar else ("time",),
            units,
            "numeric",
            (),
            site.site_id,
            site.digest,
            support,
        )

    inputs = tuple(port(name, *value) for name, value in INPUTS.items())
    outputs = tuple(port(name, *value) for name, value in OUTPUTS.items()) + tuple(
        port(name, "mm", scalar=True) for name in ("initial_soil", "initial_reservoir")
    )
    root = Path(source_root) if source_root is not None else Path(__file__).resolve().parents[2]
    paths = (
        *SOURCES,
        "examples/utility/hydrology_site.py",
        "examples/utility/hydrology_partitions.py",
    )
    sources = tuple(
        reference(root, name, media_type="text/plain", producer="site-hydrology") for name in paths
    )
    lock = reference(root, "pixi.lock", media_type="text/plain", producer="pixi")
    model = ModelSnapshot(
        _graph(site),
        {
            "pet": parameters["pet"],
            "soil": "bucket-v1",
            "routing": "linear-v1",
            "site": site.digest,
        },
        sources,
        lock.sha256,
        inputs,
        outputs,
    )
    return PrepareContext(model, parameters, 17, str(scratch), ())


def _forcing(ctx, values):
    inputs = validate_arrays(values, ctx.model.inputs, ctx.model.inputs)
    if (
        (inputs["precip_mm"] < 0).any()
        or (inputs["tmin_c"] > inputs["tmean_c"]).any()
        or (inputs["tmean_c"] > inputs["tmax_c"]).any()
    ):
        raise ValueError("site hydrology forcing violates precipitation or temperature ordering")
    dates = ctx.model.inputs[0].time.dates
    if not np.array_equal(
        inputs["day_of_year"], [iso_date(value).timetuple().tm_yday for value in dates]
    ):
        raise ValueError("day-of-year forcing differs from the daily calendar")
    return inputs


@dataclass
class SiteHandle(Handle):
    consumed: bool = False


class SiteHydrologyAdapter(HydrologyAdapter):
    def __init__(self, site: HydrologySite):
        if not isinstance(site, HydrologySite):
            raise ValueError("site hydrology requires an immutable site record")
        self.site = site

    def prepare(self, ctx):
        original = super().prepare(ctx)
        return SiteHandle(original.context, original.soil, original.reservoir, original.closed)

    def validate(self, handle):
        super().validate(handle)
        model = handle.context.model
        if model.graph_digest != _graph(self.site) or any(
            (port.grid_id, port.coordinate_digest) != (self.site.site_id, self.site.digest)
            for port in (*model.inputs, *model.outputs)
        ):
            raise ValueError("hydrology model differs from its declared site")
        if {p.name: p.units for p in model.inputs} != {k: v[0] for k, v in INPUTS.items()}:
            raise ValueError("site hydrology input units differ")
        if {p.name: p.units for p in model.outputs} != (
            {k: v[0] for k, v in OUTPUTS.items()}
            | {"initial_soil": "mm", "initial_reservoir": "mm"}
        ):
            raise ValueError("site hydrology output units differ")
        time = model.inputs[0].time
        if not isinstance(time, TimeContract) or not 1 <= len(time.dates) <= 20000:
            raise ValueError("site hydrology requires its bounded daily clock")
        dates = [iso_date(value) for value in time.dates]
        if any(b - a != timedelta(days=1) for a, b in zip(dates, dates[1:])):
            raise ValueError("site hydrology requires contiguous daily dates")
        for port in (*model.inputs, *model.outputs):
            if port.name.startswith("initial_"):
                expected = None
            else:
                semantics = (INPUTS | OUTPUTS)[port.name][1]
                expected = replace(
                    time,
                    semantics=semantics,
                    timestamp="end" if port.name in ("soil", "reservoir") else "start",
                )
            if port.time != expected or port.dtype_family != "numeric" or port.coordinates:
                raise ValueError("site hydrology port timing or metadata differs")
        if dict(model.implementations) != {
            "pet": handle.context.parameters["pet"],
            "soil": "bucket-v1",
            "routing": "linear-v1",
            "site": self.site.digest,
        }:
            raise ValueError("site hydrology implementation differs from its parameters")

    def run(self, handle, forcing):
        self.validate(handle)
        if handle.consumed:
            raise ValueError(
                "site hydrology attempt cannot run twice; replay history in a fresh handle"
            )
        values = _forcing(handle.context, forcing)
        handle.consumed = True
        params = handle.context.parameters
        initial_soil, initial_reservoir = handle.soil, handle.reservoir
        if params["pet"] == "hamon":
            pet = hamon_pet(values["tmean_c"], values["day_of_year"], self.site.latitude_deg)
        else:
            pet = hargreaves_pet(
                values["tmean_c"],
                values["tmax_c"],
                values["tmin_c"],
                values["day_of_year"],
                self.site.latitude_deg,
            )
        if not np.isfinite(pet).all():
            raise ValueError("site PET produced nonfinite values")
        aet, excess, soil = soil_bucket(
            values["precip_mm"], pet, float(params["capacity"]), handle.soil
        )
        flow, reservoirs = [], []
        for value in excess:
            handle.reservoir += value
            discharge = (1 - float(params["recession"])) * handle.reservoir
            handle.reservoir -= discharge
            flow.append(discharge)
            reservoirs.append(handle.reservoir)
        if len(soil):
            handle.soil = float(soil[-1])
        return {
            "prediction": np.asarray(flow),
            "soil": soil,
            "reservoir": np.asarray(reservoirs),
            "aet": aet,
            "pet": pet,
            "initial_soil": np.asarray(initial_soil),
            "initial_reservoir": np.asarray(initial_reservoir),
        }


def prepared_development(plan, document, parameters, scratch, *, role, source_root=None):
    """Bridge an already verified development forcing artifact, without labels.

    The trusted caller verifies artifact hashes. Role masks identify dates only;
    label-quality masks remain with scoring. Reserved forcing is not accepted.
    """
    from examples.utility.hydrology_partitions import DailyHydrologyPlan

    if not isinstance(plan, DailyHydrologyPlan) or role not in ("fitting", "selection"):
        raise ValueError("site development bridge requires its plan and development role")
    if not isinstance(document, dict) or set(document) != {"dates", *INPUTS}:
        raise ValueError("development forcing must contain only dates and meteorology")
    start, end = iso_date(plan.windows[0].start), iso_date(plan.windows[2].end)
    expected = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    if document["dates"] != expected:
        raise ValueError("development forcing dates differ or include reserved dates")
    roles = [
        window.role
        for window in plan.windows[:3]
        for _ in range((iso_date(window.end) - iso_date(window.start)).days + 1)
    ]
    site = HydrologySite(
        "utility-hydrology-site-v1", plan.source_id, plan.site_id, plan.latitude_deg, plan.area_km2
    )
    ctx = context(
        site,
        expected,
        parameters,
        scratch,
        warmup_mask=[r == "warmup" for r in roles],
        scoring_mask=[r == role for r in roles],
        source_root=source_root,
    )
    forcing = _forcing(ctx, {name: np.asarray(document[name]) for name in INPUTS})
    if not np.array_equal(forcing["tmean_c"], (forcing["tmin_c"] + forcing["tmax_c"]) / 2):
        raise ValueError("development temperature differs from declared min/max midpoint")
    return site, ctx, forcing
