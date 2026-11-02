"""Save a bounded coupled-engineering development rehearsal, without agents."""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from examples.utility.engineering import ROOT, adapter, context, direct, native_design


def run(output):
    output = Path(output)
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    started = time.perf_counter()
    sources = ("examples/utility/engineering.py", "examples/utility/rehearse_engineering.py",
               "src/autoengineering/utility/outcomes.py", "src/autoengineering/adapters/openmdao.py",
               "src/autoengineering/adapters/python.py", "examples/interoperability/circuit/model.py",
               "examples/interoperability/circuit/fixture.py", "pixi.lock")
    manifest = {"purpose": "exposed development rehearsal; not independent confirmation",
                "sources": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources},
                "versions": {p: version(p) for p in ("openmdao", "numpy", "scipy")},
                "grounds_V": [-.05, 0., .05], "baseline_current_A": .05,
                "development_voltage_minimum_V": .62, "native_max_solves": 40,
                "native_max_iterations": 20,
                "parity_rtol": 1e-10, "parity_atol": 1e-12}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    receipts = []
    for ground in manifest["grounds_V"]:
        before = time.perf_counter()
        reference = direct(.05, ground, output)
        receipts.append({"kind": "direct", "ground_V": ground, "result": reference,
                         "seconds": time.perf_counter() - before})
        (output / f"attempt-{len(receipts):03d}.json").write_text(json.dumps(receipts[-1], indent=2))
        ctx = context(.05, output)
        wrapped = run_lifecycle(adapter(), ctx, {"ground_voltage": np.array(ground)},
                                ctx.model.inputs, ctx.model.outputs)
        actual = {n: float(v) for n, v in wrapped.outputs.items()}
        receipts.append({"kind": "wrapped", "ground_V": ground, "outputs": actual,
                         "work": {n: float(v) for n, v in wrapped.diagnostics.items()},
                         "seconds": wrapped.elapsed_seconds})
        (output / f"attempt-{len(receipts):03d}.json").write_text(json.dumps(receipts[-1], indent=2))
        for name, value in actual.items():
            np.testing.assert_allclose(value, reference["outputs"][name], rtol=1e-10, atol=1e-12)
    native = native_design(manifest["grounds_V"], .62, output)
    (output / "native.json").write_text(json.dumps(native, indent=2) + "\n")
    result = {"status": "development_parity_passed", "parity_physical_solves": len(receipts),
              "native_physical_solves": native["physical_solves"],
              "total_physical_solves": len(receipts) + native["physical_solves"],
              "native_feasible": native["feasible"], "native_success": native["driver_success"],
              "elapsed_seconds": time.perf_counter()-started,
              "utility_verdict": "not_attempted",
              "cost_limits": "Native derivative counters are cumulative snapshots; do not sum them"}
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
