"""Logistic prey growth model."""


def logistic_growth(N: float, r: float = 1.0, K: float = 100.0) -> float:
    """Compute prey growth rate with carrying capacity.

    dN/dt (growth) = r * N * (1 - N/K)

    Args:
        N: Current prey population.
        r: Intrinsic growth rate.
        K: Carrying capacity.

    Returns:
        Growth rate contribution to dN/dt.
    """
    return r * N * (1.0 - N / K)
