"""Versioned time and unit declarations for the measured-input solar chain."""
from importlib.metadata import version
from pathlib import Path

import numpy as np

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ModelSnapshot, PortContract, SubdailyTimeContract
from autoengineering.campaign.serialization import digest
from examples.open_chains.solar.run_workflow import AIR, POA, WIND

ROOT = Path(__file__).resolve().parents[3]
BASELINE = {"method": "faiman_prilliman", "u0": 25., "u1": 6.84, "dc_loss_scale": 1.}


def forcing(data):
    return {"poa": data[POA].to_numpy(), "ambient": data[AIR].to_numpy(),
            "wind": data[WIND].to_numpy(), "timestamp": data.index.as_unit("ns").asi8}


def context(data, parameters, scratch):
    utc = data.index.tz_convert("UTC").as_unit("ns")
    dates = tuple(utc.strftime("%Y-%m-%dT%H:%M:%SZ"))
    segment = np.cumsum(np.r_[True, np.diff(utc.asi8) != 300_000_000_000])
    warmup = []
    offset = 0
    for i, group in enumerate(segment):
        if i == 0 or group != segment[i - 1]:
            offset = i
        warmup.append(i - offset < 4)
    time = SubdailyTimeContract("2.0", dates, "instantaneous", "PT5M", "proleptic_gregorian",
                               "instant", "UTC", "restart_state", tuple(warmup),
                               tuple(bool(v) for v in data["score"]))

    def port(name, units, family="float"):
        return PortContract(name, ("time",), units, family, (), "point", digest(dates), time)

    inputs = (port("poa", "W m-2"), port("ambient", "degC"), port("wind", "m s-1"),
              port("timestamp", "ns since 1970-01-01 UTC", "integer"))
    outputs = (port("prediction", "kW"), port("module_temperature", "degC"))
    sources = tuple(reference(ROOT, path, media_type="text/plain", producer="solar-fixture")
                    for path in ("examples/interoperability/solar/model.py",
                                 "examples/interoperability/solar/fixture.py",
                                 "examples/interoperability/solar/protocol.json",
                                 "examples/open_chains/solar/models.py"))
    model = ModelSnapshot(digest({"chain": "measured-poa-cec-sandia"}),
                          {"solar": "pvlib-oedi-v1"}, sources,
                          digest({p: version(p) for p in ("pvlib", "numpy", "pandas")}),
                          inputs, outputs)
    return PrepareContext(model, parameters, 17, str(scratch), ())
