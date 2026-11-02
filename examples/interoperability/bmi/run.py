"""Installed direct/wrapped parity using the preserved scalar BMI reservoir."""
from __future__ import annotations

import argparse
from dataclasses import replace
from importlib.metadata import version
import json
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.bmi import BmiAdapter
from autoengineering.adapters.contracts import PrepareContext
from autoengineering.adapters.python import run_lifecycle
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ModelSnapshot, PortContract, TimeContract
from autoengineering.campaign.serialization import digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def run(output):
    from examples.local_models.bmi_chain import run_components
    from examples.local_models.bmi_components import LinearReservoirBmi

    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    protocol = json.loads((HERE / "protocol.json").read_text())
    time_axis = TimeContract(tuple(protocol["dates"]), "interval_mean", "P1D",
                             "proleptic_gregorian", "end", (False,) * 3, (True,) * 3)
    rate = PortContract("excess_water", ("time",), "mm d-1", "float", (), "scalar",
                        digest([]), time_axis)
    flow = replace(rate, name="flow")
    storage = replace(rate, name="reservoir_storage", units="mm",
                       time=replace(time_axis, semantics="instantaneous"))
    paths = ("examples/interoperability/bmi/run.py", "examples/interoperability/bmi/protocol.json",
             "examples/local_models/bmi_base.py", "examples/local_models/bmi_components.py",
             "examples/local_models/bmi_chain.py", "examples/local_models/kernels.py",
             "examples/leaf_river/models/pet_hamon.py",
             "examples/leaf_river/models/pet_hargreaves.py",
             "examples/leaf_river/models/soil_moisture.py")
    sources = tuple(reference(ROOT, p, media_type="text/plain", producer="bmi-parity") for p in paths)
    model = ModelSnapshot(digest({"component": "reservoir"}), {"reservoir": "local-bmi-v1"},
                          sources, digest({"bmipy": version("bmipy"), "numpy": version("numpy")}),
                          (rate,), (flow, storage))
    parameters = {"recession": protocol["recession"], "end_time": 3}
    ctx = PrepareContext(model, parameters, 17, str(output), ())
    (output / "manifest.json").write_text(json.dumps({"protocol": protocol,
        "context": ctx.to_dict(), "bmipy": version("bmipy")}, indent=2))
    forcing = {"excess_water": np.array(protocol["forcing"], dtype=float)}
    saved = forcing["excess_water"].copy()
    started = time.perf_counter()
    direct = run_components({"reservoir": LinearReservoirBmi(parameters)}, [],
                            {"reservoir": forcing}, 3)["reservoir"]
    wrapped = run_lifecycle(BmiAdapter(lambda c: LinearReservoirBmi(dict(c.parameters)),
                                       origin=protocol["origin"]), ctx, forcing,
                            model.inputs, model.outputs)
    for name in direct:
        np.testing.assert_array_equal(wrapped.outputs[name], direct[name])
    np.testing.assert_array_equal(forcing["excess_water"], saved)
    residual = saved * protocol["dt_days"] - wrapped.outputs["flow"] * protocol["dt_days"]
    residual -= np.diff(np.r_[0., wrapped.outputs["reservoir_storage"]])
    if np.max(np.abs(residual)) > protocol["conservation_atol_mm"]:
        raise ValueError("daily reservoir storage/flux conservation failed")
    np.savez(output / "outputs.npz", direct_flow=direct["flow"],
             direct_storage=direct["reservoir_storage"], **wrapped.outputs, residual_mm=residual)
    report = {"parity": "exact", "physical_starts": 2,
              "maximum_conservation_residual_mm": float(np.max(np.abs(residual))),
              "seconds": time.perf_counter() - started, "time_profile": "scalar_daily_end"}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
