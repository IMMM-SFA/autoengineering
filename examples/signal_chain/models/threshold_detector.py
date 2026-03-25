"""Threshold crossing detector — detects upward zero-crossings in a signal."""

import numpy as np


def detect_crossings(signal: np.ndarray, threshold: float = 0.0) -> np.ndarray:
    """Detect upward crossings of a threshold.

    Returns a binary array where 1 indicates the signal crossed upward
    through the threshold at that sample.

    Args:
        signal: Input signal array.
        threshold: Crossing threshold value.

    Returns:
        Binary event array (same length as input).
    """
    shifted = signal - threshold
    sign_changes = np.diff(np.sign(shifted))
    # Upward crossings: sign goes from negative to positive (change = +2)
    events = np.zeros(len(signal))
    events[1:] = (sign_changes > 0).astype(float)
    return events
