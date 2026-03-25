"""Autoengineering workflow: Signal Processing Chain.

Demonstrates the 4-step workflow on a simple signal processing pipeline:
1. DEFINE   — Load signal chain system definition
2. VALIDATE — Compare moving average filter against ideal (clean sine)
3. ANALYZE  — Identify the filter as the weakest component (lag)
4. IMPROVE  — Swap in EMA filter, quantify improvement

Run with: pixi run python examples/signal_chain/run_workflow.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.analyze.report import generate_report
from autoengineering.execute.swap import swap_component
from autoengineering.system.component import Component
from autoengineering.system.graph import System
from autoengineering.validate.compare import validate_arrays

from models.lowpass_filter import moving_average_filter
from models.lowpass_filter_improved import ema_filter
from models.signal_generator import generate_signal
from models.threshold_detector import detect_crossings

BASELINE_DIR = Path(__file__).parent / "baselines"


def separator(title: str):
    print(f"\n{'=' * 60}")
    print(f"  STEP: {title}")
    print(f"{'=' * 60}\n")


def main():
    # Generate baselines if needed
    if not (BASELINE_DIR / "filtered_baseline.npy").exists():
        print("Generating baselines...")
        from generate_baselines import main as gen

        gen()

    filtered_baseline = np.load(BASELINE_DIR / "filtered_baseline.npy")
    events_baseline = np.load(BASELINE_DIR / "events_baseline.npy")

    # ================================================================
    # STEP 1: DEFINE
    # ================================================================
    separator("DEFINE — Load and inspect the system")

    system = System.from_yaml(Path(__file__).parent / "system.yaml")
    print(system.describe())

    # ================================================================
    # STEP 2: VALIDATE
    # ================================================================
    separator("VALIDATE — Run components and compare to baselines")

    _, noisy, clean = generate_signal()

    # Run the moving average filter
    filtered_ma = moving_average_filter(noisy, window=51)
    events_ma = detect_crossings(filtered_ma, threshold=0.0)

    # Validate signal generator (noisy matches stored noisy — same seed)
    signal_baseline = np.load(BASELINE_DIR / "signal_baseline.npy")
    gen_results = validate_arrays(
        "signal_generator",
        signal_baseline,
        noisy,
        metrics=["rmse", "correlation"],
        thresholds={"rmse": 0.01, "correlation": 0.99},
    )

    # Validate filter against ideal (clean sine)
    # Note: KGE is unsuitable here because the baseline has mean ≈ 0 (sine wave)
    filter_results = validate_arrays(
        "lowpass_filter",
        filtered_baseline,
        filtered_ma,
        metrics=["rmse", "bias", "nse", "correlation"],
        thresholds={"rmse": 0.1, "nse": 0.9, "correlation": 0.95},
    )

    # Validate threshold detector
    detector_results = validate_arrays(
        "threshold_detector",
        events_baseline,
        events_ma,
        metrics=["rmse", "correlation"],
        thresholds={"rmse": 0.05},
    )

    all_results = gen_results + filter_results + detector_results

    for r in all_results:
        print(r.to_markdown())

    # ================================================================
    # STEP 3: ANALYZE
    # ================================================================
    separator("ANALYZE — Identify improvement opportunities")

    ranked = rank_opportunities(all_results)
    print("Components ranked by improvement potential:\n")
    for i, opp in enumerate(ranked, 1):
        print(f"  {i}. {opp['component']} (score: {opp['score']}) — {opp['summary']}")

    if ranked and ranked[0]["score"] > 0:
        target = ranked[0]["component"]
        print(f"\n>>> Priority target: {target}")
        print("    Reason: Moving average filter introduces phase lag proportional to window/2")
    else:
        print("\nAll components passing!")
        return

    # ================================================================
    # STEP 4: IMPROVE
    # ================================================================
    separator("IMPROVE — Swap in EMA filter and re-validate")

    improved_comp = Component(
        name="lowpass_filter",
        model_type="filter",
        description="Exponential moving average — less lag than moving average",
        metadata={"method": "ema", "alpha": 0.5},
    )
    improved_comp.add_input("raw_signal", data_type="timeseries")
    improved_comp.add_output("filtered_signal", data_type="timeseries")

    improved_system = swap_component(system, "lowpass_filter", improved_comp)

    # Run improved filter
    filtered_ema = ema_filter(noisy, alpha=0.5)
    events_ema = detect_crossings(filtered_ema, threshold=0.0)

    improved_filter_results = validate_arrays(
        "lowpass_filter (improved)",
        filtered_baseline,
        filtered_ema,
        metrics=["rmse", "bias", "nse", "correlation"],
        thresholds={"rmse": 0.1, "nse": 0.9, "correlation": 0.95},
    )
    improved_detector_results = validate_arrays(
        "threshold_detector (with EMA)",
        events_baseline,
        events_ema,
        metrics=["rmse", "correlation"],
        thresholds={"rmse": 0.05},
    )

    print("Improved validation results:\n")
    for r in improved_filter_results + improved_detector_results:
        print(f"  {r.to_markdown()}")

    # Comparison
    print("\n--- Filter Comparison: Moving Average vs EMA ---\n")
    for metric in ["rmse", "nse", "correlation"]:
        before = next((r for r in filter_results if r.metric == metric), None)
        after = next((r for r in improved_filter_results if r.metric == metric), None)
        if before and after:
            direction = (
                "better"
                if (metric in ("nse", "kge") and after.value > before.value)
                or (metric == "rmse" and after.value < before.value)
                else "worse"
            )
            print(f"  {metric}: {before.value:.4f} → {after.value:.4f} ({direction})")

    # Report
    print("\n")
    separator("REPORT")
    all_improved = gen_results + improved_filter_results + improved_detector_results
    report = generate_report(improved_system, all_improved)
    print(report)


if __name__ == "__main__":
    main()
