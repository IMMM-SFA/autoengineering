"""Save native wind development outcomes including a deliberate budget stop."""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from examples.utility.wind import ROOT, WindTask
from examples.utility.wind_native import native_layout


def run(output):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    started = time.perf_counter()
    from py_wake.examples.data.hornsrev1 import wt16_x, wt16_y
    corners = [0, 3, 12, 15]
    positions = np.asarray(wt16_x)[corners], np.asarray(wt16_y)[corners]
    paths = ("examples/utility/wind.py", "examples/utility/wind_native.py",
             "examples/utility/rehearse_wind.py", "examples/open_chains/wind/models.py", "pixi.lock")
    manifest = {"purpose": "exposed development layout; no independent weather confirmation",
                "sources": {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
                "versions": {p: version(p) for p in ("py-wake", "topfarm", "numpy")},
                "x_m": positions[0].tolist(), "y_m": positions[1].tolist(),
                "max_iterations": 2, "max_wake_calls": 12, "max_gradient_calls": 4,
                "budget_control": {"max_wake_calls": 1, "max_gradient_calls": 1},
                "final_layout_evaluation_cap": 2, "direction_grid_degrees": 30}
    (output/"manifest.json").write_text(json.dumps(manifest, indent=2)+'\n')
    native = native_layout(positions, max_iterations=2, max_wake_calls=12, max_gradient_calls=4)
    (output/"native.json").write_text(native.to_json()+'\n')
    stopped = native_layout(positions, max_iterations=20, max_wake_calls=1, max_gradient_calls=1)
    (output/"budget-control.json").write_text(stopped.to_json()+'\n')
    evaluations = []
    if native.feasible:
        task = WindTask({"baseline": positions, "native": (native.x, native.y)}, positions)
        for name in ("baseline", "native"):
            ctx = task.context(name, output)
            value = run_lifecycle(task.adapter(), ctx, {}, (), ctx.model.outputs)
            receipt = {"layout": name, "outputs": {n: float(v) for n, v in value.outputs.items()},
                       "seconds": value.elapsed_seconds, "context": ctx.to_dict()}
            (output/f"evaluation-{name}.json").write_text(json.dumps(receipt, indent=2)+'\n')
            evaluations.append(receipt)
    summary = {"native_status": native.status, "native_feasible": native.feasible,
               "wake_calls": sum(c.kind == "wake" for c in native.calls),
               "gradient_calls": sum(c.kind == "gradient" for c in native.calls),
               "budget_control_status": stopped.status,
               "budget_control_wake_calls": sum(c.kind == "wake" for c in stopped.calls),
               "budget_control_gradient_calls": sum(c.kind == "gradient" for c in stopped.calls),
               "final_layout_evaluations": len(evaluations),
               "elapsed_seconds": time.perf_counter()-started, "utility_verdict": "not_attempted",
               "cost_limits": "Gradient callbacks include differentiated wake work; keep units separate"}
    (output/"summary.json").write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    run(parser.parse_args().output)
