"""Standard SCS Curve Number rainfall-runoff model.

Fixed curve number, no antecedent moisture adjustment.
"""

import numpy as np


def scs_runoff(precip: np.ndarray, curve_number: float = 75.0) -> np.ndarray:
    """Compute direct runoff using the SCS Curve Number method.

    Args:
        precip: Daily excess rainfall (mm/day).
        curve_number: SCS curve number (0-100).

    Returns:
        Daily direct runoff (mm/day).
    """
    S = 25400.0 / curve_number - 254.0
    Ia = 0.2 * S

    runoff = np.where(
        precip > Ia,
        (precip - Ia) ** 2 / (precip - Ia + S),
        0.0,
    )
    return runoff
