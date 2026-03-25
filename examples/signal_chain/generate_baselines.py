"""Generate baseline data for the signal chain example.

Uses the clean (noise-free) sine wave as the ideal filtered output,
and computes ideal threshold crossings from it.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from models.signal_generator import generate_signal
from models.threshold_detector import detect_crossings

BASELINE_DIR = Path(__file__).parent / "baselines"


def main():
    BASELINE_DIR.mkdir(exist_ok=True)

    t, noisy, clean = generate_signal()

    # The clean sine IS the ideal filtered output
    np.save(BASELINE_DIR / "signal_baseline.npy", noisy)
    np.save(BASELINE_DIR / "filtered_baseline.npy", clean)

    # Ideal crossings from clean signal
    events_baseline = detect_crossings(clean, threshold=0.0)
    np.save(BASELINE_DIR / "events_baseline.npy", events_baseline)

    print(f"Baselines generated in {BASELINE_DIR}/")
    print(f"  Signal: {len(noisy)} samples, freq=0.05")
    print(f"  Ideal crossings: {int(events_baseline.sum())} events")


if __name__ == "__main__":
    main()
