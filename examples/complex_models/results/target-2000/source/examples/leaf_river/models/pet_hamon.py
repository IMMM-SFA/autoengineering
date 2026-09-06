"""Hamon PET estimation method.

A simple temperature-based PET method that only requires mean daily temperature.
Known weakness: tends to underestimate summer PET because it ignores diurnal
temperature range and solar radiation variations.

Reference: Hamon, W.R. (1963). Computation of Direct Runoff Amounts from Storm
Rainfall. IASH Pub. 63:52-62.
"""

import numpy as np


def daylight_hours(doy: np.ndarray, latitude: float = 31.7) -> np.ndarray:
    """Compute daylight hours from day of year and latitude.

    Uses simple solar geometry approximation.
    """
    lat_rad = np.radians(latitude)
    # Solar declination
    declination = 0.4093 * np.sin(2 * np.pi / 365 * doy - 1.405)
    # Hour angle at sunset
    ws = np.arccos(-np.tan(lat_rad) * np.tan(declination))
    return 24 / np.pi * ws


def hamon_pet(tmean: np.ndarray, doy: np.ndarray, latitude: float = 31.7) -> np.ndarray:
    """Estimate PET using the Hamon method.

    PET = 0.55 * (D/12)^2 * e_sat(T) * 25.4

    Args:
        tmean: Mean daily temperature (Celsius).
        doy: Day of year (1-366).
        latitude: Latitude in degrees.

    Returns:
        Daily PET in mm/day.
    """
    D = daylight_hours(doy, latitude)

    # Saturated vapor density (Hamon's Pt term, inches/day)
    # Pt = 4.95 * exp(0.062 * T) / 100
    Pt = 4.95 * np.exp(0.062 * tmean) / 100.0

    # Hamon PET (mm/day) — convert from inches
    pet = 0.55 * (D / 12.0) ** 2 * Pt * 25.4

    # Clamp negative temps to zero PET
    pet = np.where(tmean > 0, pet, 0.0)

    return pet
