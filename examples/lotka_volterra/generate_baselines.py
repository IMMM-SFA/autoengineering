"""Generate baseline data using the Type II (realistic) model as truth."""

import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).parent))

from models.predation_type2 import type2_predation
from models.predator_dynamics import predator_growth
from models.prey_growth import logistic_growth

BASELINE_DIR = Path(__file__).parent / "baselines"
T_SPAN = (0, 200)
T_EVAL = np.linspace(0, 200, 2000)
Y0 = [40.0, 9.0]  # initial prey, predator


def rhs_type2(t, y):
    N, P = y
    growth = logistic_growth(N)
    predation = type2_predation(N, P)
    dN = growth - predation
    dP = predator_growth(predation, P)
    return [dN, dP]


def main():
    BASELINE_DIR.mkdir(exist_ok=True)

    sol = solve_ivp(rhs_type2, T_SPAN, Y0, t_eval=T_EVAL, method="RK45", rtol=1e-8)

    np.save(BASELINE_DIR / "t_baseline.npy", sol.t)
    np.save(BASELINE_DIR / "prey_baseline.npy", sol.y[0])
    np.save(BASELINE_DIR / "predator_baseline.npy", sol.y[1])

    print(f"Baselines generated in {BASELINE_DIR}/")
    print(f"  Time: {T_SPAN[0]}-{T_SPAN[1]}, {len(sol.t)} points")
    print(f"  Prey: mean={sol.y[0].mean():.1f}, range=[{sol.y[0].min():.1f}, {sol.y[0].max():.1f}]")
    print(f"  Predator: mean={sol.y[1].mean():.1f}, range=[{sol.y[1].min():.1f}, {sol.y[1].max():.1f}]")


if __name__ == "__main__":
    main()
