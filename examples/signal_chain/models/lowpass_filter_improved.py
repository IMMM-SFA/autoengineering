"""Exponential moving average filter — improved low-pass with less lag."""

import numpy as np


def ema_filter(signal: np.ndarray, alpha: float = 0.15) -> np.ndarray:
    """Apply an exponential moving average filter.

    Much less phase lag than a wide moving average while still providing
    good noise reduction. The alpha parameter controls the tradeoff.

    Args:
        signal: Input signal array.
        alpha: Smoothing factor (0 < alpha <= 1). Higher = less smoothing, less lag.

    Returns:
        Filtered signal (same length as input).
    """
    n = len(signal)
    filtered = np.zeros(n)
    filtered[0] = signal[0]
    for i in range(1, n):
        filtered[i] = alpha * signal[i] + (1 - alpha) * filtered[i - 1]
    return filtered
