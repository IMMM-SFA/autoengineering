"""Predator population dynamics."""


def predator_growth(
    predation_rate: float, P: float, e: float = 0.1, m: float = 0.3
) -> float:
    """Compute predator population change.

    dP/dt = e * predation_rate - m * P

    Args:
        predation_rate: Total prey consumed per time unit.
        P: Current predator population.
        e: Conversion efficiency (prey → predator biomass).
        m: Predator mortality rate.

    Returns:
        Rate of change of predator population.
    """
    return e * predation_rate - m * P
