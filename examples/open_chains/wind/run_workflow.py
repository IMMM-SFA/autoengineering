"""Compare the original Horns Rev subset with bounded TOPFARM layout searches."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from py_wake.examples.data.hornsrev1 import wt16_x, wt16_y

from autoengineering.research.runner import run_component
from examples.open_chains.common import compare, output_directory, parser, write_json
from examples.open_chains.wind.models import feasible, wakes

HERE = Path(__file__).resolve().parent


def run_chain(system, x: np.ndarray, y: np.ndarray) -> dict:
    positions = run_component(system.get_component("layout"), {"x": x, "y": y})
    feasible(positions["x"], positions["y"], x, y)
    northing = run_component(system.get_component("northing"), {"value": positions["y"]})
    flow = run_component(system.get_component("wakes"), {**positions, **northing})
    energy = run_component(system.get_component("energy"), flow)
    return {**positions, **flow, **energy}


def main() -> None:
    args = parser(__doc__).parse_args()
    if args.fetch:
        print("Horns Rev site and turbine data ship with pinned py-wake; no download required.")
        return
    output = output_directory(HERE, args.output)
    count = 4 if args.smoke else 16
    x, y = np.asarray(wt16_x[:count]), np.asarray(wt16_y[:count])
    # Preserve the rectangular boundary even in smoke mode by choosing corner positions.
    if args.smoke:
        x, y = np.asarray(wt16_x[[0, 3, 12, 15]]), np.asarray(wt16_y[[0, 3, 12, 15]])

    def evaluate(system):
        arrays = run_chain(system, x, y)
        energy = float(arrays["total_gwh"][0])
        return (
            -energy,
            {
                "aep_gwh": energy,
                "inner_termination": ["not_run", "converged", "not_converged"][
                    int(arrays["optimizer_diagnostics"][0])
                ],
                "inner_wake_function_calls": int(arrays["optimizer_diagnostics"][1]),
                "inner_wake_gradient_calls": int(arrays["optimizer_diagnostics"][2]),
            },
            arrays,
        )

    def test(baseline, selected, destination):
        result = {}
        # Reuse frozen positions. Never reoptimize on the finer direction grid.
        for name in ["baseline", "selected"]:
            if name == "baseline":
                positions = {"x": x, "y": y}
            else:
                selection = __import__("json").loads((destination / "selection.json").read_text())
                with np.load(destination / f"{selection['id']}.npz") as saved:
                    positions = {"x": saved["x"], "y": saved["y"]}
            flow = wakes(**positions, direction_step=5)
            result[name + "_aep_gwh"] = float(flow[0].sum())
        result["gain_gwh"] = result["selected_aep_gwh"] - result["baseline_aep_gwh"]
        result["kind"] = "finer-grid sensitivity under the same wake model; not observations"
        write_json(destination / "grid-sensitivity.json", result)
        return result

    compare(
        HERE,
        output,
        evaluate,
        objective="negative annual energy (GWh)",
        evidence="Engineering design comparison under fixed NOJ wakes; no observed accuracy claim",
        packages=["autoengineering", "py-wake", "topfarm", "numpy"],
        context={
            "smoke": args.smoke,
            "turbines": len(x),
            "x": x.tolist(),
            "y": y.tolist(),
            "minimum_spacing_m": 320,
            "seed": 0,
            "wind_direction_step": 30,
            "wind_speeds_m_s": list(range(4, 26, 2)),
            "inner_optimizer": "deterministic SLSQP; internal wake calls are not outer trials",
        },
        test=test,
    )


if __name__ == "__main__":
    main()
