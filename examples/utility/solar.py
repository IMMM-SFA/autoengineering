"""Measured-POA solar development profile reusing the preserved equipment model."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from autoengineering.campaign.acceptance import DEFAULT_CHECKS, CheckContext
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.spec import CheckSpec

ROOT = Path(__file__).resolve().parents[2]


def load_development(cache):
    from examples.interoperability.solar.data import load
    return load(cache)  # Only the exposed June 1-7, 2018 protocol; no fetch.


def adapter():
    from examples.interoperability.solar.model import adapter as supplied
    return supplied()


def context(data, parameters, scratch):
    from examples.interoperability.solar.fixture import context as supplied
    ctx = supplied(data, parameters, scratch)
    source = reference(ROOT, "examples/utility/solar.py", media_type="text/plain",
                       producer="utility-solar")
    return replace(ctx, model=replace(ctx.model, source_bundle=(*ctx.model.source_bundle, source)))


def physical_checks(outputs, forcing, parameters):
    import pvlib
    inverter = pvlib.pvsystem.retrieve_sam("cecinverter")["TMEIC__PVL_L1833GRM"]
    ctx = CheckContext(outputs, forcing, parameters)
    specs = (CheckSpec("finite", "1", True, "outputs", {}),
             CheckSpec("solar_physical", "1", True, "outputs", {
                 "capacity_kw": float(inverter.Paco)/1000,
                 "standby_floor_kw": -float(inverter.Pnt)/1000}))
    return tuple(DEFAULT_CHECKS.evaluate(spec, ctx) for spec in specs)


def primary_loss(data, outputs):
    from examples.open_chains.solar.run_workflow import POWER
    mask = data["score"].to_numpy(dtype=bool)
    if not mask.any():
        return {"status": "insufficient_data", "rmse_kw": None, "scored_rows": 0}
    observed = data[POWER].to_numpy()[mask]
    predicted = np.asarray(outputs["prediction"])[mask]
    if not np.isfinite(observed).all() or not np.isfinite(predicted).all():
        return {"status": "insufficient_data", "rmse_kw": None, "scored_rows": int(mask.sum())}
    return {"status": "success", "rmse_kw": float(np.sqrt(np.mean((predicted-observed)**2))),
            "scored_rows": int(mask.sum())}
