"""Streamflow routing: triangular unit hydrograph + baseflow recession.

Known weakness: fixed triangular UH shape (not calibrated), and baseflow
recession coefficient is a rough estimate.
"""

import numpy as np


def triangular_uh(peak_time: int = 3, length: int = 10) -> np.ndarray:
    """Create a triangular unit hydrograph.

    Args:
        peak_time: Time to peak (days).
        length: Total UH duration (days).

    Returns:
        Unit hydrograph ordinates (sums to 1.0).
    """
    uh = np.zeros(length)
    for i in range(length):
        if i <= peak_time:
            uh[i] = i / peak_time
        else:
            uh[i] = (length - i) / (length - peak_time)
    uh = np.maximum(uh, 0)
    uh /= uh.sum()
    return uh


def route_streamflow(
    direct_runoff: np.ndarray,
    uh_peak: int = 3,
    uh_length: int = 10,
    k_base: float = 0.85,
    baseflow_init: float = 0.5,
    recharge_frac: float = 0.10,
    precip: np.ndarray | None = None,
) -> np.ndarray:
    """Route direct runoff through a unit hydrograph and add baseflow.

    Q_total = Q_direct (convolved with UH) + Q_baseflow
    Q_baseflow[t] = k_base * Q_baseflow[t-1] + recharge_frac * precip[t]

    Args:
        direct_runoff: Daily direct runoff (mm/day).
        uh_peak: Time to UH peak (days).
        uh_length: Total UH duration (days).
        k_base: Baseflow recession coefficient (0-1).
        baseflow_init: Initial baseflow (mm/day).
        recharge_frac: Fraction of excess that becomes recharge.
        precip: Precipitation for recharge calculation. If None, uses direct_runoff.

    Returns:
        Total daily streamflow (mm/day).
    """
    n = len(direct_runoff)

    # Direct runoff routing
    uh = triangular_uh(uh_peak, uh_length)
    q_direct = np.convolve(direct_runoff, uh, mode="full")[:n]

    # Baseflow recession
    recharge_source = precip if precip is not None else direct_runoff
    q_base = np.zeros(n)
    q_base[0] = baseflow_init
    for i in range(1, n):
        q_base[i] = k_base * q_base[i - 1] + recharge_frac * recharge_source[i]

    return q_direct + q_base
