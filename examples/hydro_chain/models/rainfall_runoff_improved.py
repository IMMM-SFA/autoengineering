"""Improved SCS Curve Number model with antecedent moisture correction.

This version adjusts the curve number based on 5-day antecedent precipitation,
addressing the known bias of the standard SCS-CN method during wet sequences.
"""

import numpy as np


def scs_runoff_amc(
    precip: np.ndarray,
    curve_number: float = 75.0,
    ia_ratio: float = 0.2,
    amc_window: int = 5,
    dry_threshold: float = 12.7,
    wet_threshold: float = 27.9,
) -> np.ndarray:
    """Compute runoff using SCS-CN with Antecedent Moisture Condition adjustment.

    Adjusts CN based on the 5-day antecedent precipitation:
    - AMC-I (dry): CN reduced for dry conditions
    - AMC-II (normal): CN unchanged
    - AMC-III (wet): CN increased for wet conditions

    Args:
        precip: Daily precipitation array (mm/day).
        curve_number: Base SCS curve number (AMC-II condition).
        ia_ratio: Initial abstraction ratio.
        amc_window: Number of preceding days for AMC calculation.
        dry_threshold: AMC-I threshold (mm in window).
        wet_threshold: AMC-III threshold (mm in window).

    Returns:
        Daily runoff array (mm/day).
    """
    n = len(precip)
    runoff = np.zeros(n)

    for i in range(n):
        # Compute antecedent precipitation
        start = max(0, i - amc_window)
        antecedent = precip[start:i].sum() if i > 0 else 0.0

        # Adjust CN based on AMC
        if antecedent < dry_threshold:
            # AMC-I (dry) — Hawkins (1985) conversion
            cn = 4.2 * curve_number / (10 - 0.058 * curve_number)
        elif antecedent > wet_threshold:
            # AMC-III (wet)
            cn = 23 * curve_number / (10 + 0.13 * curve_number)
        else:
            # AMC-II (normal)
            cn = curve_number

        cn = np.clip(cn, 1, 99)

        # Standard SCS equation with adjusted CN
        S = 25400.0 / cn - 254.0
        Ia = ia_ratio * S

        if precip[i] > Ia:
            runoff[i] = (precip[i] - Ia) ** 2 / (precip[i] - Ia + S)

    return runoff
