"""Calibrated streamflow routing: gamma unit hydrograph + tuned baseflow.

Improvement over fixed triangular UH: uses a gamma distribution shape
(more physically realistic) and better-tuned baseflow parameters.
"""

import numpy as np
from scipy.stats import gamma as gamma_dist


def gamma_uh(shape: float = 2.5, scale: float = 1.5, length: int = 15) -> np.ndarray:
    """Create a gamma-distribution unit hydrograph.

    The gamma distribution is widely used in hydrology for UH shapes
    because it naturally produces the characteristic rapid rise and
    gradual recession of observed hydrographs.

    Args:
        shape: Gamma shape parameter (controls peakedness).
        scale: Gamma scale parameter (controls spread).
        length: Total UH duration (days).

    Returns:
        Unit hydrograph ordinates (sums to 1.0).
    """
    t = np.arange(1, length + 1, dtype=float)
    uh = gamma_dist.pdf(t, a=shape, scale=scale)
    uh /= uh.sum()
    return uh


def route_streamflow_calibrated(
    direct_runoff: np.ndarray,
    gamma_shape: float = 2.5,
    gamma_scale: float = 1.5,
    uh_length: int = 15,
    k_base: float = 0.92,
    baseflow_init: float = 0.5,
    recharge_frac: float = 0.03,
    precip: np.ndarray | None = None,
) -> np.ndarray:
    """Route streamflow with a calibrated gamma UH and tuned baseflow.

    Args:
        direct_runoff: Daily direct runoff (mm/day).
        gamma_shape: Gamma distribution shape parameter.
        gamma_scale: Gamma distribution scale parameter.
        uh_length: Total UH duration (days).
        k_base: Baseflow recession coefficient.
        baseflow_init: Initial baseflow (mm/day).
        recharge_frac: Fraction of precipitation that becomes recharge.
        precip: Precipitation for recharge calculation.

    Returns:
        Total daily streamflow (mm/day).
    """
    n = len(direct_runoff)

    # Direct runoff routing with gamma UH
    uh = gamma_uh(gamma_shape, gamma_scale, uh_length)
    q_direct = np.convolve(direct_runoff, uh, mode="full")[:n]

    # Baseflow recession (better tuned)
    recharge_source = precip if precip is not None else direct_runoff
    q_base = np.zeros(n)
    q_base[0] = baseflow_init
    for i in range(1, n):
        q_base[i] = k_base * q_base[i - 1] + recharge_frac * recharge_source[i]

    return q_direct + q_base
