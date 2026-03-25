"""Lotka-Volterra Type I functional response (linear predation).

Known weakness: predation rate increases linearly without bound as prey
density increases, which is unrealistic — real predators have handling
time and satiate.
"""


def type1_predation(N: float, P: float, alpha: float = 0.03) -> float:
    """Type I functional response: linear predation.

    predation_rate = alpha * N * P

    Args:
        N: Prey population.
        P: Predator population.
        alpha: Attack rate coefficient.

    Returns:
        Total predation rate (prey consumed per time unit).
    """
    return alpha * N * P
