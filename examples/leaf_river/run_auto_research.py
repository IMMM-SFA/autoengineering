"""Automated auto-research loop for the Leaf River chain.

This is the automated counterpart to ``run_workflow.py``. Where that script swaps
components and re-runs the chain by hand over two rounds, this one hands a list of
researched candidates (``candidates.yaml``) to ``auto_improve`` and lets the bounded
loop swap, execute, validate, and decide — reproducing the same improvement
trajectory (streamflow NSE ~0.23 -> ~0.39) with an auditable experiment tree,
evidence-first report, and provenance sidecar.

Run with: pixi run python examples/leaf_river/run_auto_research.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from autoengineering.research import auto_improve, load_candidates, write_report
from autoengineering.research.runner import run_component
from autoengineering.system.graph import System

from data.fetch_data import fetch_noaa_weather, fetch_usgs_streamflow
from models.soil_moisture import soil_bucket

HERE = Path(__file__).parent


def make_run_chain(system: System, drivers: dict[str, np.ndarray]):
    """Build a run_chain(system) for the Leaf River topology.

    The chain has glue arithmetic that is not itself a component (soil moisture is
    fixed; recharge = precip - actual_ET feeds routing's baseflow), so we hand-write
    the wiring but execute the *swappable* components (pet_estimator, rainfall_runoff,
    routing) through ``run_component`` — so whatever candidate got swapped in runs.

    ``drivers`` supplies the source arrays: precip, tmean, tmax, tmin, doy, precip_raw.
    """

    def run_chain(sys_to_run: System) -> dict[str, np.ndarray]:
        precip = drivers["precip"]

        # PET (swappable) — pass all possible inputs; run_component selects the ones
        # the current candidate declares.
        pet_comp = sys_to_run.get_component("pet_estimator")
        pet_inputs = {
            "tmean": drivers["tmean"],
            "tmax": drivers["tmax"],
            "tmin": drivers["tmin"],
            "doy": drivers["doy"],
        }
        pet = run_component(pet_comp, pet_inputs)["pet"]

        # Soil moisture (fixed, not a candidate) — glue arithmetic.
        actual_et, excess, _sm = soil_bucket(precip, pet)
        recharge = np.maximum(drivers["precip_raw"] - actual_et, 0.0)

        # Rainfall-runoff (swappable).
        rr_comp = sys_to_run.get_component("rainfall_runoff")
        rr_inputs = {"excess_rainfall": excess, "precip_raw": drivers["precip_raw"]}
        direct_runoff = run_component(rr_comp, rr_inputs)["direct_runoff"]

        # Routing (swappable).
        route_comp = sys_to_run.get_component("routing")
        route_inputs = {"direct_runoff": direct_runoff, "recharge": recharge}
        streamflow = run_component(route_comp, route_inputs)["streamflow"]

        return {
            "pet_estimator.pet": pet,
            "rainfall_runoff.direct_runoff": direct_runoff,
            "routing.streamflow": streamflow,
        }

    return run_chain


def main():
    # --- Data ---
    flow_df = fetch_usgs_streamflow()
    weather_df = fetch_noaa_weather()
    merged = pd.merge(flow_df, weather_df, on="date", how="inner").dropna()
    print(
        f"Data: {len(merged)} days "
        f"({merged['date'].min().date()} to {merged['date'].max().date()})"
    )

    drivers = {
        "precip": merged["precip_mm"].values,
        "precip_raw": merged["precip_mm"].values,
        "tmean": merged["tmean_c"].values,
        "tmax": merged["tmax_c"].values,
        "tmin": merged["tmin_c"].values,
        "doy": merged["date"].dt.dayofyear.values,
    }
    observed_flow = merged["flow_mm_day"].values

    # --- System + candidates ---
    system = System.from_yaml(HERE / "system.yaml")
    candidates = load_candidates(HERE / "candidates.yaml")
    run_chain = make_run_chain(system, drivers)

    # --- Bounded auto-research loop ---
    workdir = HERE / "outputs"
    tree = auto_improve(
        system,
        run_chain,
        observed_flow,
        validate_output="routing.streamflow",
        candidates=candidates,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"nse": 0.4, "kge": 0.4},
        max_iterations=20,
        workdir=workdir,
        slug="leaf-river",
    )

    print("\n" + tree.to_markdown() + "\n")

    baseline = tree.nodes[tree.root_id]
    best = tree.best()
    print(
        f"Streamflow NSE: baseline {baseline.metrics.get('nse'):.4f} "
        f"-> best {best.metrics.get('nse'):.4f}"
    )

    report_path, prov_path = write_report(tree, system, "leaf-river", workdir)
    print(f"\nReport:     {report_path}")
    print(f"Provenance: {prov_path}")


if __name__ == "__main__":
    main()
