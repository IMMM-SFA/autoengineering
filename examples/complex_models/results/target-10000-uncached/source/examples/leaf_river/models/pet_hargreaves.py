"""Hargreaves PET estimation method.

Improvement over Hamon: uses diurnal temperature range (Tmax - Tmin) as a
proxy for solar radiation, producing better summer PET estimates.

Reference: Hargreaves, G.H. and Samani, Z.A. (1985). Reference Crop
Evapotranspiration from Temperature. Applied Engineering in Agriculture,
1(2):96-99.
"""

import numpy as np


def extraterrestrial_radiation(doy: np.ndarray, latitude: float = 31.7) -> np.ndarray:
    """Compute daily extraterrestrial radiation (Ra) in mm/day equivalent.

    Uses FAO-56 equations for solar geometry.
    """
    lat_rad = np.radians(latitude)
    # Solar constant
    Gsc = 0.0820  # MJ m-2 min-1

    # Inverse relative distance Earth-Sun
    dr = 1 + 0.033 * np.cos(2 * np.pi / 365 * doy)

    # Solar declination
    delta = 0.409 * np.sin(2 * np.pi / 365 * doy - 1.39)

    # Sunset hour angle
    ws = np.arccos(-np.tan(lat_rad) * np.tan(delta))

    # Extraterrestrial radiation (MJ/m2/day)
    Ra = (24 * 60 / np.pi) * Gsc * dr * (
        ws * np.sin(lat_rad) * np.sin(delta)
        + np.cos(lat_rad) * np.cos(delta) * np.sin(ws)
    )

    # Convert MJ/m2/day to mm/day (using latent heat of vaporization ≈ 2.45 MJ/kg)
    return Ra / 2.45


def hargreaves_pet(
    tmean: np.ndarray,
    tmax: np.ndarray,
    tmin: np.ndarray,
    doy: np.ndarray,
    latitude: float = 31.7,
) -> np.ndarray:
    """Estimate PET using the Hargreaves-Samani method.

    PET = 0.0023 * Ra * (T + 17.8) * sqrt(Tmax - Tmin)

    Args:
        tmean: Mean daily temperature (Celsius).
        tmax: Maximum daily temperature (Celsius).
        tmin: Minimum daily temperature (Celsius).
        doy: Day of year (1-366).
        latitude: Latitude in degrees.

    Returns:
        Daily PET in mm/day.
    """
    Ra = extraterrestrial_radiation(doy, latitude)

    # Temperature range (clamp to avoid negative sqrt)
    td = np.maximum(tmax - tmin, 0.0)

    pet = 0.0023 * Ra * (tmean + 17.8) * np.sqrt(td)

    # Clamp negative values
    pet = np.maximum(pet, 0.0)

    return pet
