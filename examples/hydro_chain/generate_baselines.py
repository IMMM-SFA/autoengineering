"""Generate baseline data for the hydro chain example.

Uses the improved rainfall-runoff model as the "truth" to generate baselines.
The standard model will then be validated against these baselines, revealing
its systematic biases.
"""

import sys
from pathlib import Path

import numpy as np

# Add models to path
sys.path.insert(0, str(Path(__file__).parent))

from models.precip_generator import generate_precipitation
from models.rainfall_runoff_improved import scs_runoff_amc
from models.simple_reservoir import simulate_reservoir

BASELINE_DIR = Path(__file__).parent / "baselines"
SEED = 42
N_DAYS = 730  # 2 years


def main():
    BASELINE_DIR.mkdir(exist_ok=True)

    # Generate "true" precipitation
    precip = generate_precipitation(n_days=N_DAYS, seed=SEED)
    np.save(BASELINE_DIR / "precip_baseline.npy", precip)

    # Generate "true" runoff using the improved model (our reference)
    runoff_true = scs_runoff_amc(precip, curve_number=75)
    np.save(BASELINE_DIR / "runoff_baseline.npy", runoff_true)

    # Generate "true" reservoir outputs
    release_true, storage_true = simulate_reservoir(runoff_true)
    np.save(BASELINE_DIR / "release_baseline.npy", release_true)
    np.save(BASELINE_DIR / "storage_baseline.npy", storage_true)

    print(f"Baselines generated in {BASELINE_DIR}/")
    print(f"  Precipitation: {N_DAYS} days, {(precip > 0).sum()} wet days, mean={precip[precip > 0].mean():.1f} mm")
    print(f"  Runoff: mean={runoff_true.mean():.2f} mm/day")
    print(f"  Reservoir release: mean={release_true.mean():.2f} mm/day")


if __name__ == "__main__":
    main()
