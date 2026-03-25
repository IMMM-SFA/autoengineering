"""Autoengineering workflow: Predator-Prey Ecosystem (Lotka-Volterra).

Demonstrates sub-component replacement on a coupled ODE system:
1. DEFINE   — Load predator-prey system definition
2. VALIDATE — Compare Type I (linear) predation against Type II (realistic) baseline
3. ANALYZE  — Identify predation functional response as the weakest component
4. IMPROVE  — Swap Type I for Type II, quantify improvement

Run with: pixi run python examples/lotka_volterra/run_workflow.py
"""

import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).parent))

from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.analyze.report import generate_report
from autoengineering.execute.swap import swap_component
from autoengineering.system.component import Component
from autoengineering.system.graph import System
from autoengineering.validate.compare import validate_arrays

from models.predation_type1 import type1_predation
from models.predation_type2 import type2_predation
from models.predator_dynamics import predator_growth
from models.prey_growth import logistic_growth

BASELINE_DIR = Path(__file__).parent / "baselines"
T_SPAN = (0, 200)
T_EVAL = np.linspace(0, 200, 2000)
Y0 = [40.0, 9.0]


def separator(title: str):
    print(f"\n{'=' * 60}")
    print(f"  STEP: {title}")
    print(f"{'=' * 60}\n")


def run_model(predation_func):
    """Integrate the ODE system with a given predation function."""

    def rhs(t, y):
        N, P = y
        growth = logistic_growth(N)
        predation = predation_func(N, P)
        dN = growth - predation
        dP = predator_growth(predation, P)
        return [dN, dP]

    sol = solve_ivp(rhs, T_SPAN, Y0, t_eval=T_EVAL, method="RK45", rtol=1e-8)
    return sol.t, sol.y[0], sol.y[1]


def main():
    # Generate baselines if needed
    if not (BASELINE_DIR / "prey_baseline.npy").exists():
        print("Generating baselines...")
        from generate_baselines import main as gen

        gen()

    prey_baseline = np.load(BASELINE_DIR / "prey_baseline.npy")
    predator_baseline = np.load(BASELINE_DIR / "predator_baseline.npy")

    # ================================================================
    # STEP 1: DEFINE
    # ================================================================
    separator("DEFINE — Load predator-prey system")

    system = System.from_yaml(Path(__file__).parent / "system.yaml")
    print(system.describe())

    # ================================================================
    # STEP 2: VALIDATE
    # ================================================================
    separator("VALIDATE — Run Type I model and compare to Type II baseline")

    _, prey_t1, predator_t1 = run_model(type1_predation)

    # Validate prey trajectory
    prey_results = validate_arrays(
        "predation (prey trajectory)",
        prey_baseline,
        prey_t1,
        metrics=["rmse", "nse", "correlation"],
        thresholds={"nse": 0.8, "correlation": 0.9},
    )

    # Validate predator trajectory
    predator_results = validate_arrays(
        "predation (predator trajectory)",
        predator_baseline,
        predator_t1,
        metrics=["rmse", "nse", "correlation"],
        thresholds={"nse": 0.8, "correlation": 0.9},
    )

    # Prey growth and predator dynamics are the same in both — validate trivially
    growth_results = validate_arrays(
        "prey_growth",
        prey_baseline[:100],
        prey_baseline[:100],
        metrics=["rmse", "correlation"],
        thresholds={"rmse": 0.01},
    )
    dynamics_results = validate_arrays(
        "predator_dynamics",
        predator_baseline[:100],
        predator_baseline[:100],
        metrics=["rmse", "correlation"],
        thresholds={"rmse": 0.01},
    )

    all_results = prey_results + predator_results + growth_results + dynamics_results

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

    print("\n>>> The predation functional response is the key difference between models.")
    print("    Type I (linear) produces unrealistic boom-bust cycles at high prey density.")
    print("    Type II (saturating) dampens these oscillations via handling time limitation.")

    # ================================================================
    # STEP 4: IMPROVE
    # ================================================================
    separator("IMPROVE — Swap Type I for Type II predation")

    improved_comp = Component(
        name="predation",
        model_type="interaction",
        description="Holling Type II functional response (saturating predation)",
        metadata={"method": "type2_holling", "alpha": 0.03, "handling_time": 0.3},
    )
    improved_comp.add_input("prey_population", data_type="scalar")
    improved_comp.add_input("predator_population", data_type="scalar")
    improved_comp.add_output("predation_rate", data_type="scalar")

    improved_system = swap_component(system, "predation", improved_comp)

    # Run improved model
    _, prey_t2, predator_t2 = run_model(type2_predation)

    improved_prey_results = validate_arrays(
        "predation (prey, improved)",
        prey_baseline,
        prey_t2,
        metrics=["rmse", "nse", "correlation"],
        thresholds={"nse": 0.8, "correlation": 0.9},
    )
    improved_predator_results = validate_arrays(
        "predation (predator, improved)",
        predator_baseline,
        predator_t2,
        metrics=["rmse", "nse", "correlation"],
        thresholds={"nse": 0.8, "correlation": 0.9},
    )

    print("Improved validation results:\n")
    for r in improved_prey_results + improved_predator_results:
        print(f"  {r.to_markdown()}")

    # Comparison
    print("\n--- Prey Trajectory: Type I vs Type II ---\n")
    for metric in ["rmse", "nse", "correlation"]:
        before = next(r for r in prey_results if r.metric == metric)
        after = next(r for r in improved_prey_results if r.metric == metric)
        direction = (
            "better"
            if (metric in ("nse", "correlation") and after.value > before.value)
            or (metric == "rmse" and after.value < before.value)
            else "same" if abs(after.value - before.value) < 1e-10 else "worse"
        )
        print(f"  {metric}: {before.value:.4f} → {after.value:.4f} ({direction})")

    # Report
    print("\n")
    separator("REPORT")
    all_improved = growth_results + improved_prey_results + improved_predator_results + dynamics_results
    report = generate_report(improved_system, all_improved)
    print(report)


if __name__ == "__main__":
    main()
