"""Autoengineering workflow: Leaf River Hydrology Chain.

Demonstrates the full 4-step workflow on a real watershed using publicly
available USGS streamflow and NOAA weather data. Shows both full model swaps
(PET method) and sub-component improvement (runoff AMC adjustment).

Run with: pixi run python examples/leaf_river/run_workflow.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.analyze.report import generate_report
from autoengineering.execute.swap import swap_component
from autoengineering.system.component import Component
from autoengineering.system.graph import System
from autoengineering.validate.compare import validate_arrays

from data.fetch_data import fetch_noaa_weather, fetch_usgs_streamflow
from models.pet_hamon import hamon_pet
from models.pet_hargreaves import hargreaves_pet
from models.routing import route_streamflow
from models.routing_calibrated import route_streamflow_calibrated
from models.scs_runoff import scs_runoff
from models.scs_runoff_amc import scs_runoff_amc
from models.soil_moisture import soil_bucket


def separator(title: str):
    print(f"\n{'=' * 60}")
    print(f"  STEP: {title}")
    print(f"{'=' * 60}\n")


def run_chain(precip, pet, precip_raw):
    """Run the full model chain: soil → runoff → routing."""
    aet, excess, sm = soil_bucket(precip, pet)
    direct_runoff = scs_runoff(excess)
    # Use effective recharge (precip - AET) so PET changes propagate to baseflow
    recharge = np.maximum(precip_raw - aet, 0.0)
    streamflow = route_streamflow(direct_runoff, precip=recharge)
    return aet, excess, sm, direct_runoff, streamflow


def run_chain_improved_pet(precip, tmean, tmax, tmin, doy):
    """Run chain with Hargreaves PET (Round 1 improvement)."""
    pet = hargreaves_pet(tmean, tmax, tmin, doy)
    aet, excess, sm = soil_bucket(precip, pet)
    direct_runoff = scs_runoff(excess)
    recharge = np.maximum(precip - aet, 0.0)
    streamflow = route_streamflow(direct_runoff, precip=recharge)
    return pet, aet, excess, sm, direct_runoff, streamflow


def run_chain_improved_all(precip, tmean, tmax, tmin, doy, precip_raw):
    """Run chain with Hargreaves PET + AMC runoff + calibrated routing (Round 2)."""
    pet = hargreaves_pet(tmean, tmax, tmin, doy)
    aet, excess, sm = soil_bucket(precip, pet)
    direct_runoff = scs_runoff_amc(excess, precip_raw)
    recharge = np.maximum(precip_raw - aet, 0.0)
    streamflow = route_streamflow_calibrated(direct_runoff, precip=recharge)
    return pet, aet, excess, sm, direct_runoff, streamflow


def main():
    # ================================================================
    # STEP 0: FETCH DATA
    # ================================================================
    separator("FETCH DATA — Download USGS/NOAA observations")

    flow_df = fetch_usgs_streamflow()
    weather_df = fetch_noaa_weather()

    # Align dates
    merged = pd.merge(flow_df, weather_df, on="date", how="inner").dropna()
    print(f"Data: {len(merged)} days ({merged['date'].min().date()} to {merged['date'].max().date()})")
    print(f"  Mean precip: {merged['precip_mm'].mean():.1f} mm/day")
    print(f"  Mean streamflow: {merged['flow_mm_day'].mean():.2f} mm/day")
    print(f"  Mean temp: {merged['tmean_c'].mean():.1f} C")

    # Extract arrays
    precip = merged["precip_mm"].values
    tmean = merged["tmean_c"].values
    tmax = merged["tmax_c"].values
    tmin = merged["tmin_c"].values
    observed_flow = merged["flow_mm_day"].values
    doy = merged["date"].dt.dayofyear.values

    # ================================================================
    # STEP 1: DEFINE
    # ================================================================
    separator("DEFINE — Load system definition")

    system = System.from_yaml(Path(__file__).parent / "system.yaml")
    print(system.describe())

    # ================================================================
    # STEP 2: VALIDATE — Run baseline chain
    # ================================================================
    separator("VALIDATE — Run baseline chain and compare to observed")

    # Run baseline chain
    pet_hamon_vals = hamon_pet(tmean, doy)
    aet, excess, sm, direct_runoff, sim_flow = run_chain(precip, pet_hamon_vals, precip)

    # Validate final streamflow against observed
    routing_results = validate_arrays(
        "routing",
        observed_flow,
        sim_flow,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"nse": 0.4, "kge": 0.4},
    )

    # Validate PET: compare Hamon vs Hargreaves as reference
    pet_harg_ref = hargreaves_pet(tmean, tmax, tmin, doy)
    pet_results = validate_arrays(
        "pet_estimator",
        pet_harg_ref,
        pet_hamon_vals,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"nse": 0.8, "kge": 0.8},
    )

    # Validate rainfall-runoff: compare to a simple partition of observed
    # (observed flow - estimated baseflow ≈ direct runoff)
    obs_baseflow = np.minimum(observed_flow, np.percentile(observed_flow, 30))
    obs_direct = np.maximum(observed_flow - obs_baseflow, 0)
    runoff_results = validate_arrays(
        "rainfall_runoff",
        obs_direct,
        direct_runoff,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"nse": 0.3, "kge": 0.3},
    )

    # Soil moisture: validate excess rainfall pattern
    sm_results = validate_arrays(
        "soil_moisture",
        precip,
        excess,
        metrics=["rmse", "correlation"],
        thresholds={"correlation": 0.5},
    )

    all_results = pet_results + sm_results + runoff_results + routing_results

    print("Validation results (baseline chain):\n")
    for r in all_results:
        print(f"  {r.to_markdown()}")

    # ================================================================
    # STEP 3: ANALYZE
    # ================================================================
    separator("ANALYZE — Identify improvement opportunities")

    ranked = rank_opportunities(all_results)
    print("Components ranked by improvement potential:\n")
    for i, opp in enumerate(ranked, 1):
        print(f"  {i}. {opp['component']} (score: {opp['score']}) — {opp['summary']}")

    # ================================================================
    # STEP 4: IMPROVE
    # ================================================================

    # --- Round 1: Swap PET method (full model replacement) ---
    separator("IMPROVE Round 1 — Swap PET: Hamon → Hargreaves")

    improved_pet_comp = Component(
        name="pet_estimator",
        model_type="evapotranspiration",
        description="Hargreaves PET using Tmax/Tmin for better summer estimates",
        metadata={"method": "hargreaves"},
    )
    improved_pet_comp.add_input("tmean", data_type="timeseries")
    improved_pet_comp.add_output("pet", data_type="timeseries")

    system_r1 = swap_component(system, "pet_estimator", improved_pet_comp)

    pet_r1, aet_r1, excess_r1, sm_r1, runoff_r1, flow_r1 = run_chain_improved_pet(
        precip, tmean, tmax, tmin, doy
    )

    r1_flow_results = validate_arrays(
        "routing (R1)",
        observed_flow,
        flow_r1,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"nse": 0.4, "kge": 0.4},
    )

    print("Round 1 streamflow results (Hargreaves PET):\n")
    for r in r1_flow_results:
        print(f"  {r.to_markdown()}")

    # --- Round 2: Also swap runoff method + calibrated routing ---
    separator("IMPROVE Round 2 — Also swap runoff (AMC) + calibrated routing")

    improved_runoff_comp = Component(
        name="rainfall_runoff",
        model_type="transform",
        description="SCS-CN with antecedent moisture condition adjustment",
        metadata={"method": "scs_cn_amc"},
    )
    improved_runoff_comp.add_input("excess_rainfall", data_type="timeseries")
    improved_runoff_comp.add_output("direct_runoff", data_type="timeseries")

    improved_routing_comp = Component(
        name="routing",
        model_type="routing",
        description="Gamma UH + calibrated baseflow recession",
        metadata={"method": "gamma_uh_calibrated"},
    )
    improved_routing_comp.add_input("direct_runoff", data_type="timeseries")
    improved_routing_comp.add_output("streamflow", data_type="timeseries")

    system_r2 = swap_component(system_r1, "rainfall_runoff", improved_runoff_comp)
    system_r2 = swap_component(system_r2, "routing", improved_routing_comp)

    pet_r2, aet_r2, excess_r2, sm_r2, runoff_r2, flow_r2 = run_chain_improved_all(
        precip, tmean, tmax, tmin, doy, precip
    )

    r2_flow_results = validate_arrays(
        "routing (R2)",
        observed_flow,
        flow_r2,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"nse": 0.4, "kge": 0.4},
    )

    print("Round 2 streamflow results (Hargreaves + AMC + calibrated routing):\n")
    for r in r2_flow_results:
        print(f"  {r.to_markdown()}")

    # --- Comparison table ---
    print("\n--- Streamflow Comparison: Baseline → R1 → R2 ---\n")
    print(f"  {'Metric':<12} {'Baseline':>10} {'Round 1':>10} {'Round 2':>10}")
    print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10}")
    for metric in ["rmse", "nse", "kge"]:
        v0 = next(r for r in routing_results if r.metric == metric).value
        v1 = next(r for r in r1_flow_results if r.metric == metric).value
        v2 = next(r for r in r2_flow_results if r.metric == metric).value
        print(f"  {metric:<12} {v0:>10.4f} {v1:>10.4f} {v2:>10.4f}")

    # --- Final report ---
    print("\n")
    separator("REPORT — Full analysis of improved system")

    all_r2 = (
        validate_arrays("pet_estimator (hargreaves)", pet_harg_ref, pet_r2, metrics=["rmse", "nse"])
        + validate_arrays("soil_moisture (R2)", precip, excess_r2, metrics=["rmse", "correlation"])
        + validate_arrays("rainfall_runoff (AMC)", obs_direct, runoff_r2, metrics=["rmse", "nse"])
        + r2_flow_results
    )
    report = generate_report(system_r2, all_r2)
    print(report)


if __name__ == "__main__":
    main()
