"""Compare HOPP dispatch policies with fixed hardware and cached resources."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from autoengineering.research.runner import run_component
from examples.open_chains.common import (
    compare,
    fetch_sources,
    output_directory,
    parser,
    verify_sources,
)
from examples.open_chains.hybrid.models import check_physics

HERE = Path(__file__).resolve().parent


def run_chain(system, smoke: bool = False, validate: bool = True) -> dict:
    plant = run_component(system.get_component("dispatch"), {"smoke_flag": np.array([int(smoke)])})
    tariff = run_component(system.get_component("tariff"), {"value": plant["price"]})
    cash = run_component(system.get_component("revenue"), {**plant, **tariff})
    arrays = {**plant, **cash}
    if validate:
        check_physics(arrays)
    return arrays


def main() -> None:
    args = parser(__doc__).parse_args()
    if args.fetch:
        fetch_sources(HERE)
        return
    inputs = verify_sources(HERE)
    output = output_directory(HERE, args.output)

    def evaluate(system):
        arrays = run_chain(system, args.smoke, validate=False)
        feasible, reason = True, None
        try:
            check_physics(arrays)
        except ValueError as error:
            feasible, reason = False, str(error)
        revenue = float(np.sum(arrays["revenue_usd"]))
        return (
            -revenue,
            {
                "revenue_usd": revenue,
                "feasible": feasible,
                "infeasibility": reason,
                "minimum_soc_percent": float(arrays["soc"].min()),
                "maximum_soc_percent": float(arrays["soc"].max()),
                "export_mwh": float(arrays["grid_kw"].sum() / 1000),
                "final_soc_percent": float(arrays["soc"][-1]),
                "battery_throughput_mwh": float(np.abs(arrays["battery_kw"]).sum() / 1000),
            },
            arrays,
        )

    compare(
        HERE,
        output,
        evaluate,
        objective="negative energy revenue (USD)",
        evidence="HOPP design scenario, not observed accuracy; "
        + ("first-five-day smoke check" if args.smoke else "one-year resource simulation"),
        packages=["autoengineering", "HOPP", "NREL-PySAM", "pyomo", "numpy"],
        context={
            "inputs": inputs,
            "smoke": args.smoke,
            "resource_year": 2012,
            "price_scenario_year": 2015,
            "seed": 0,
            "interval_hours": 1,
            "forecast_assumption": "perfect knowledge of each next 24 hours",
            "objective_limit": "gross energy revenue; no capital/degradation costs, "
            "no terminal SOC salvage value; report final SOC",
        },
    )


if __name__ == "__main__":
    main()
