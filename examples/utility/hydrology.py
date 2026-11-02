"""Exposed Leaf River development profile with explicit daily stores and fluxes."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.campaign.acceptance import DEFAULT_CHECKS, CheckContext
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ModelSnapshot, PortContract, TimeContract
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.spec import CheckSpec
from examples.campaign_contracts.hydrology import HydrologyAdapter, SOURCES

ROOT = Path(__file__).resolve().parents[2]
BASELINE = {"capacity": 100., "recession": .7, "pet": "hamon"}
INPUTS = {"precip_mm": ("mm", "interval_total"), "tmean_c": ("degC", "interval_mean"),
          "tmax_c": ("degC", "instantaneous"), "tmin_c": ("degC", "instantaneous"),
          "day_of_year": ("day", "instantaneous")}


def development_data():
    from examples.campaign_contracts.build_profile import audit_cache
    data = audit_cache()
    return data[data.date < "2020-01-01"].copy()


def forcing(data):
    result = {name: data[name].to_numpy(copy=True) for name in INPUTS if name != "day_of_year"}
    result["day_of_year"] = pd.to_datetime(data.date).dt.dayofyear.to_numpy()
    return result


def context(data, parameters, scratch):
    dates = tuple(pd.to_datetime(data.date).dt.strftime("%Y-%m-%d"))
    time = TimeContract(dates, "interval_mean", "P1D", "proleptic_gregorian", "start",
                        tuple(data.split == "warmup"), tuple(data.split != "warmup"))

    def port(name, units, semantics="interval_mean", scalar=False):
        support = None if scalar else replace(time, semantics=semantics,
                          timestamp="end" if name in ("soil", "reservoir") else "start")
        return PortContract(name, () if scalar else ("time",), units, "numeric", (),
                            "leaf-river-02472000", digest(["02472000", 1947.7]), support)

    inputs = tuple(port(name, units, semantics) for name, (units, semantics) in INPUTS.items())
    outputs = tuple(port(name, units, semantics) for name, units, semantics in (
        ("prediction", "mm/day", "interval_mean"), ("aet", "mm/day", "interval_mean"),
        ("pet", "mm/day", "interval_mean"), ("soil", "mm", "instantaneous"),
        ("reservoir", "mm", "instantaneous"))) + tuple(
            port(name, "mm", scalar=True) for name in ("initial_soil", "initial_reservoir"))
    paths = (*SOURCES, "examples/utility/hydrology.py")
    refs = tuple(reference(ROOT, path, media_type="text/plain", producer="utility-hydrology")
                 for path in paths)
    model = ModelSnapshot(digest({"model": "daily-bucket-reservoir-v1"}),
                          {"pet": parameters["pet"], "soil": "bucket-v1", "routing": "linear-v1"},
                          refs, reference(ROOT, "pixi.lock", media_type="text/plain",
                                          producer="pixi").sha256, inputs, outputs)
    return PrepareContext(model, parameters, 17, str(scratch), ())


def adapter():
    return HydrologyAdapter()


def physical_checks(outputs, inputs, parameters):
    ctx = CheckContext(outputs, inputs, parameters)
    return tuple(DEFAULT_CHECKS.evaluate(CheckSpec(name, "1", True, "outputs", {}), ctx)
                 for name in ("finite", "nonnegative", "soil_capacity", "daily_balance"))


def learned_candidate_admission():
    # Prediction-only regressors cannot satisfy the required state/flux contract.
    return {"status": "unsupported_capability",
            "reason": "No admitted trained candidate with causal preprocessing and conservative stores/fluxes",
            "training_started": False}
