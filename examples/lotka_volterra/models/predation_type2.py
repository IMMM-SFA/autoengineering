"""Holling Type II functional response (saturating predation).

Improvement over Type I: includes handling time, so predation rate
saturates at high prey density. More realistic for most predator-prey
systems.
"""


def type2_predation(
    N: float, P: float, alpha: float = 0.03, h: float = 0.3
) -> float:
    """Type II functional response: saturating predation (Holling disc equation).

    predation_rate = alpha * N * P / (1 + alpha * h * N)

    At low N: behaves like Type I (linear).
    At high N: saturates at P / h (predator handling time limits intake).

    Args:
        N: Prey population.
        P: Predator population.
        alpha: Attack rate coefficient.
        h: Handling time per prey item.

    Returns:
        Total predation rate (prey consumed per time unit).
    """
    return alpha * N * P / (1.0 + alpha * h * N)
