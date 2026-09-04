"""Deterministic functions for the function-network example."""

import numpy as np


def transform(driver, gain=1.0):
    """Scale the source driver."""
    return np.asarray(driver) * gain


def score(flow, target=4.0, offset=0.0):
    """Score flow relative to a target."""
    flow = np.asarray(flow)
    return 10.0 - (flow - target) ** 2 + offset
