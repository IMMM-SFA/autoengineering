"""Runnable adapters for the routing models.

The routing functions take ``precip`` (the recharge series) as a keyword argument,
but the runnable contract passes declared inputs positionally. These thin wrappers
expose a clean ``(direct_runoff, recharge)`` signature so routing can be swapped as
a runnable component in the auto-research loop.
"""

import numpy as np

from models.routing import route_streamflow
from models.routing_calibrated import route_streamflow_calibrated


def route_baseline(direct_runoff: np.ndarray, recharge: np.ndarray) -> np.ndarray:
    """Triangular UH + baseflow recession (baseline routing)."""
    return route_streamflow(direct_runoff, precip=recharge)


def route_calibrated(direct_runoff: np.ndarray, recharge: np.ndarray) -> np.ndarray:
    """Gamma UH + calibrated baseflow recession (improved routing)."""
    return route_streamflow_calibrated(direct_runoff, precip=recharge)
