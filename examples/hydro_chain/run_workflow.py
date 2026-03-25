"""Autoengineering workflow demonstration: Simple Hydrology Chain.

This script walks through the complete 4-step autoengineering workflow:

1. DEFINE   — Load the system definition and inspect its structure
2. VALIDATE — Run each component and compare against baselines
3. ANALYZE  — Identify the weakest component and rank improvement opportunities
4. IMPROVE  — Swap in an improved component and quantify the improvement

Run with: pixi run python examples/hydro_chain/run_workflow.py
"""

import sys
from pathlib import Path

import numpy as np

# Add example directory to path for model imports
sys.path.insert(0, str(Path(__file__).parent))

from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.analyze.report import generate_report
from autoengineering.execute.swap import swap_component
from autoengineering.system.component import Component
from autoengineering.system.graph import System
from autoengineering.validate.compare import validate_arrays

from models.precip_generator import generate_precipitation
from models.rainfall_runoff import scs_runoff
from models.rainfall_runoff_improved import scs_runoff_amc
from models.simple_reservoir import simulate_reservoir

BASELINE_DIR = Path(__file__).parent / "baselines"
SEED = 42
N_DAYS = 730


def separator(title: str):
    print(f"\n{'=' * 60}")
    print(f"  STEP: {title}")
    print(f"{'=' * 60}\n")


def main():
    # ----------------------------------------------------------------
    # Step 0: Generate baselines (if not already present)
    # ----------------------------------------------------------------
    if not (BASELINE_DIR / "precip_baseline.npy").exists():
        print("Generating baselines...")
        from generate_baselines import main as gen_baselines
        gen_baselines()

    # Load baselines
    precip_baseline = np.load(BASELINE_DIR / "precip_baseline.npy")
    runoff_baseline = np.load(BASELINE_DIR / "runoff_baseline.npy")
    release_baseline = np.load(BASELINE_DIR / "release_baseline.npy")

    # ================================================================
    # STEP 1: DEFINE — Load and inspect the system
    # ================================================================
    separator("DEFINE — Load and inspect the system")

    system = System.from_yaml(Path(__file__).parent / "system.yaml")
    print(system.describe())
    print()

    # ================================================================
    # STEP 2: VALIDATE — Run components and compare to baselines
    # ================================================================
    separator("VALIDATE — Run components and compare to baselines")

    # Run the standard models with the same precipitation input
    precip = generate_precipitation(n_days=N_DAYS, seed=SEED)
    runoff_standard = scs_runoff(precip, curve_number=75)
    release_standard, storage_standard = simulate_reservoir(runoff_standard)

    # Validate precipitation generator (should match perfectly — same seed)
    precip_results = validate_arrays(
        "precip_generator", precip_baseline, precip,
        metrics=["rmse", "bias", "correlation"],
        thresholds={"rmse": 0.01, "correlation": 0.99},
    )

    # Validate rainfall-runoff (standard vs improved baseline)
    runoff_results = validate_arrays(
        "rainfall_runoff", runoff_baseline, runoff_standard,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"rmse": 0.5, "nse": 0.8, "kge": 0.8},
    )

    # Validate reservoir
    release_results = validate_arrays(
        "reservoir", release_baseline, release_standard,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"rmse": 0.3, "nse": 0.8, "kge": 0.8},
    )

    all_results = precip_results + runoff_results + release_results

    for r in all_results:
        print(r.to_markdown())

    # ================================================================
    # STEP 3: ANALYZE — Identify improvement opportunities
    # ================================================================
    separator("ANALYZE — Identify improvement opportunities")

    ranked = rank_opportunities(all_results)
    print("Components ranked by improvement potential:\n")
    for i, opp in enumerate(ranked, 1):
        print(f"  {i}. {opp['component']} (score: {opp['score']}) — {opp['summary']}")

    if ranked and ranked[0]["score"] > 0:
        target = ranked[0]["component"]
        print(f"\n>>> Priority target for improvement: {target}")
    else:
        print("\nAll components are performing well!")
        return

    # ================================================================
    # STEP 4: IMPROVE — Swap and re-validate
    # ================================================================
    separator("IMPROVE — Swap in improved component and re-validate")

    # Create the improved component definition
    improved_comp = Component(
        name="rainfall_runoff",
        model_type="transform",
        description="SCS-CN with Antecedent Moisture Condition adjustment",
        metadata={"method": "scs_curve_number_amc", "curve_number": 75},
    )
    improved_comp.add_input("daily_precip", data_type="timeseries")
    improved_comp.add_output("daily_runoff", data_type="timeseries")

    # Swap in the improved system
    improved_system = swap_component(system, "rainfall_runoff", improved_comp)
    print(f"Swapped component. New system: {improved_system}")
    print()

    # Run the improved model
    runoff_improved = scs_runoff_amc(precip, curve_number=75)
    release_improved, _ = simulate_reservoir(runoff_improved)

    # Re-validate
    improved_runoff_results = validate_arrays(
        "rainfall_runoff (improved)", runoff_baseline, runoff_improved,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"rmse": 0.5, "nse": 0.8, "kge": 0.8},
    )
    improved_release_results = validate_arrays(
        "reservoir (with improved runoff)", release_baseline, release_improved,
        metrics=["rmse", "bias", "nse", "kge"],
        thresholds={"rmse": 0.3, "nse": 0.8, "kge": 0.8},
    )

    print("Improved validation results:\n")
    for r in improved_runoff_results + improved_release_results:
        print(f"  {r.to_markdown()}")

    # Compare before/after
    print("\n--- Comparison: Before vs After ---\n")
    for metric in ["rmse", "nse", "kge"]:
        before = next(r for r in runoff_results if r.metric == metric)
        after = next(r for r in improved_runoff_results if r.metric == metric)
        delta = after.value - before.value
        direction = "better" if (metric in ("nse", "kge") and delta > 0) or (metric == "rmse" and delta < 0) else "worse"
        print(f"  {metric}: {before.value:.4f} → {after.value:.4f} ({direction})")

    # Generate final report
    print("\n")
    separator("REPORT — Full analysis report")
    all_improved = precip_results + improved_runoff_results + improved_release_results
    report = generate_report(improved_system, all_improved)
    print(report)


if __name__ == "__main__":
    main()
