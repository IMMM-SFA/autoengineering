"""SCS Curve Number with Antecedent Moisture Condition adjustment.

Adjusts CN based on 5-day antecedent precipitation.
"""

import numpy as np


def scs_runoff_amc(
    precip: np.ndarray,
    precip_history: np.ndarray,
    curve_number: float = 75.0,
    amc_window: int = 5,
    dry_threshold: float = 12.7,
    wet_threshold: float = 27.9,
) -> np.ndarray:
    """Compute runoff with antecedent moisture condition adjustment.

    Args:
        precip: Daily excess rainfall (mm/day).
        precip_history: Full precipitation record for AMC calculation.
        curve_number: Base SCS curve number (AMC-II).
        amc_window: Days for antecedent calculation.
        dry_threshold: AMC-I threshold (mm).
        wet_threshold: AMC-III threshold (mm).

    Returns:
        Daily direct runoff (mm/day).
    """
    n = len(precip)
    runoff = np.zeros(n)

    for i in range(n):
        start = max(0, i - amc_window)
        antecedent = precip_history[start:i].sum() if i > 0 else 0.0

        if antecedent < dry_threshold:
            cn = 4.2 * curve_number / (10 - 0.058 * curve_number)
        elif antecedent > wet_threshold:
            cn = 23 * curve_number / (10 + 0.13 * curve_number)
        else:
            cn = curve_number

        cn = np.clip(cn, 1, 99)
        S = 25400.0 / cn - 254.0
        Ia = 0.2 * S

        if precip[i] > Ia:
            runoff[i] = (precip[i] - Ia) ** 2 / (precip[i] - Ia + S)

    return runoff
