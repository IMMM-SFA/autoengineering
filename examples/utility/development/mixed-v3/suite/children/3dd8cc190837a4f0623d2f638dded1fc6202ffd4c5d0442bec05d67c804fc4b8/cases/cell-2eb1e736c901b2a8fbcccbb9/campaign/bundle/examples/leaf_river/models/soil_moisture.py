"""Simple single-layer soil moisture bucket model.

A minimal water balance model that partitions precipitation into actual
evapotranspiration, soil moisture storage, and excess rainfall (which
becomes available for runoff).
"""

import numpy as np


def soil_bucket(
    precip: np.ndarray,
    pet: np.ndarray,
    field_capacity: float = 100.0,
    initial_sm: float = 50.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run a simple soil moisture bucket model.

    For each timestep:
    1. Add precipitation to soil
    2. Compute actual ET (limited by soil moisture availability)
    3. Remove excess above field capacity as potential runoff

    Args:
        precip: Daily precipitation (mm/day).
        pet: Daily potential evapotranspiration (mm/day).
        field_capacity: Maximum soil moisture storage (mm).
        initial_sm: Initial soil moisture (mm).

    Returns:
        Tuple of (actual_et, excess_rainfall, soil_moisture) arrays.
    """
    n = len(precip)
    actual_et = np.zeros(n)
    excess = np.zeros(n)
    sm_out = np.zeros(n)

    sm = initial_sm
    for i in range(n):
        # Add precipitation
        sm += precip[i]

        # Actual ET: linearly reduced when soil is dry
        if sm > 0 and pet[i] > 0:
            # Reduction factor: sm / field_capacity (linear)
            reduction = min(sm / field_capacity, 1.0)
            aet = min(pet[i] * reduction, sm)
        else:
            aet = 0.0

        sm -= aet
        actual_et[i] = aet

        # Excess above field capacity
        if sm > field_capacity:
            excess[i] = sm - field_capacity
            sm = field_capacity

        sm_out[i] = sm

    return actual_et, excess, sm_out
