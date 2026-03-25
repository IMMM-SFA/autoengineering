"""SCS Curve Number rainfall-runoff model.

A simple, widely-used method for estimating direct runoff from rainfall.
This is the "original" version that will be identified as improvable.
"""

import numpy as np


def scs_runoff(
    precip: np.ndarray,
    curve_number: float = 75.0,
    ia_ratio: float = 0.2,
) -> np.ndarray:
    """Compute runoff using the SCS Curve Number method.

    This is the standard SCS-CN method which assumes a fixed curve number.
    Known limitation: does not account for antecedent moisture conditions,
    leading to systematic bias during wet sequences.

    Args:
        precip: Daily precipitation array (mm/day).
        curve_number: SCS curve number (0-100).
        ia_ratio: Initial abstraction ratio (Ia = ia_ratio * S).

    Returns:
        Daily runoff array (mm/day).
    """
    # Maximum potential retention
    S = 25400.0 / curve_number - 254.0

    # Initial abstraction
    Ia = ia_ratio * S

    # Runoff (standard SCS equation)
    runoff = np.where(
        precip > Ia,
        (precip - Ia) ** 2 / (precip - Ia + S),
        0.0,
    )

    return runoff
