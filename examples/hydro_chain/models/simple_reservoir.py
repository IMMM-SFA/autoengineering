"""Simple mass-balance reservoir with linear release rule.

A minimal reservoir model that demonstrates storage routing.
"""

import numpy as np


def simulate_reservoir(
    inflow: np.ndarray,
    capacity_mm: float = 200.0,
    release_coefficient: float = 0.1,
    initial_storage: float = 50.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Simulate a simple reservoir with a linear release rule.

    Release = release_coefficient * storage (capped at storage).
    Overflow occurs when storage exceeds capacity.

    Args:
        inflow: Daily inflow array (mm/day).
        capacity_mm: Maximum storage capacity (mm).
        release_coefficient: Fraction of storage released per day.
        initial_storage: Starting storage level (mm).

    Returns:
        Tuple of (release, storage) arrays.
    """
    n = len(inflow)
    release = np.zeros(n)
    storage = np.zeros(n)

    s = initial_storage
    for i in range(n):
        # Add inflow
        s += inflow[i]

        # Compute release (linear rule)
        r = release_coefficient * s

        # Handle overflow
        if s > capacity_mm:
            overflow = s - capacity_mm
            r += overflow
            s = capacity_mm

        # Apply release
        s -= r
        s = max(s, 0.0)

        release[i] = r
        storage[i] = s

    return release, storage
