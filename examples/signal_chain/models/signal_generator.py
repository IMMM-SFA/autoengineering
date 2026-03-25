"""Stochastic signal generator: sine wave with Gaussian noise."""

import numpy as np


def generate_signal(
    n: int = 1000,
    freq: float = 0.05,
    amplitude: float = 1.0,
    noise_std: float = 0.3,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate a noisy sine wave.

    Args:
        n: Number of samples.
        freq: Frequency of the sine wave (cycles per sample).
        amplitude: Amplitude of the sine wave.
        noise_std: Standard deviation of additive Gaussian noise.
        seed: Random seed.

    Returns:
        Tuple of (t, noisy_signal, clean_signal).
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    clean = amplitude * np.sin(2 * np.pi * freq * t)
    noisy = clean + rng.normal(0, noise_std, n)
    return t, noisy, clean
