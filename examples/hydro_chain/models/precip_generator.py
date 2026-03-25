"""Stochastic precipitation generator.

Generates daily precipitation using a Poisson process for occurrence
and an exponential distribution for event depth.
"""

import numpy as np


def generate_precipitation(
    n_days: int = 365,
    mean_events_per_day: float = 0.3,
    mean_depth_mm: float = 10.0,
    seed: int | None = None,
) -> np.ndarray:
    """Generate a synthetic daily precipitation time series.

    Args:
        n_days: Number of days to simulate.
        mean_events_per_day: Probability of rain on any given day.
        mean_depth_mm: Mean depth of rainfall on wet days (mm).
        seed: Random seed for reproducibility.

    Returns:
        Array of daily precipitation (mm/day).
    """
    rng = np.random.default_rng(seed)

    # Determine wet/dry days (Bernoulli trials)
    wet_days = rng.random(n_days) < mean_events_per_day

    # Generate depths on wet days (exponential distribution)
    precip = np.zeros(n_days)
    n_wet = wet_days.sum()
    if n_wet > 0:
        precip[wet_days] = rng.exponential(mean_depth_mm, size=n_wet)

    return precip
