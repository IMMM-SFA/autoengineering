"""Simple moving average low-pass filter.

Intentionally uses a wide window, causing significant lag — this is the
"baseline" filter that the autoengineering workflow will identify as improvable.
"""

import numpy as np


def moving_average_filter(signal: np.ndarray, window: int = 51) -> np.ndarray:
    """Apply a moving average filter.

    Uses a wide window (default 51) which smooths well but introduces
    significant phase lag — roughly window/2 samples of delay.

    Args:
        signal: Input signal array.
        window: Width of the moving average window.

    Returns:
        Filtered signal (same length as input).
    """
    kernel = np.ones(window) / window
    filtered = np.convolve(signal, kernel, mode="same")
    return filtered
