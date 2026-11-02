"""Verify cached-byte and direct/wrapped parity, without optimizer or downloads."""
import argparse
import json
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from autoengineering.system.graph import System
from examples.open_chains.solar.run_workflow import POWER, run_chain
from .data import load
from .fixture import BASELINE, ROOT, context, forcing
from .model import adapter


def run(cache, output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    started = time.perf_counter()
    data, inventory = load(cache)
    ctx = context(data, BASELINE, output)
    protocol = json.loads((Path(__file__).parent / "protocol.json").read_text())
    manifest = {"protocol": protocol, "data": inventory, "context": ctx.to_dict()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    reference = run_chain(System.from_yaml(ROOT / "examples/open_chains/solar/system.yaml"), data)
    wrapped = run_lifecycle(adapter(), ctx, forcing(data), ctx.model.inputs, ctx.model.outputs)
    pairs = {"prediction": "ac_kw", "module_temperature": "module_temperature"}
    for name, source in pairs.items():
        np.testing.assert_allclose(wrapped.outputs[name], reference[source],
                                   atol=protocol["output_atol_kw"], rtol=protocol["output_rtol"])
    mask = data["score"].to_numpy()
    error = wrapped.outputs["prediction"][mask] - data[POWER].to_numpy()[mask]
    np.savez_compressed(output / "outputs.npz", **wrapped.outputs,
                        direct_ac_kw=reference["ac_kw"], scoring_mask=mask)
    report = {"rows": len(data), "scored_rows": int(mask.sum()),
              "power_rmse_kw": float(np.sqrt(np.mean(error**2))),
              "parity": "passed", "physical_starts": 2,
              "seconds": time.perf_counter() - started,
              "confirmation": "not_attempted", "energy": "not_reported"}
    (output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.cache, args.output)
