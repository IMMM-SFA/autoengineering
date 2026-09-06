"""Measured-POA adaptation of pvlib's OEDI 9068 plant example.

Broadband POA is treated as effective irradiance. This conditional model excludes
tracking, shading, spectral and incidence-angle estimation; it is not an exact
reproduction of the satellite-driven upstream chain.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib


def temperature(
    poa: np.ndarray,
    ambient: np.ndarray,
    wind: np.ndarray,
    timestamp: np.ndarray,
    method: str = "faiman_prilliman",
    u0: float = 25.0,
    u1: float = 6.84,
) -> np.ndarray:
    """Return modeled module temperature in C on contiguous five-minute segments.

    Reset transient state at each missing-driver gap. The caller excludes the
    first 20 minutes of each segment from every candidate's scoring mask.
    """
    times = pd.to_datetime(timestamp, utc=True)
    if method == "faiman" or method == "faiman_prilliman":
        steady = pvlib.temperature.faiman(poa, ambient, wind, u0=u0, u1=u1)
    elif method == "sapm_module":
        steady = pvlib.temperature.sapm_module(poa, ambient, wind, a=-3.56, b=-0.075)
    else:
        raise ValueError(f"Unknown temperature method: {method}")
    if method != "faiman_prilliman":
        return np.asarray(steady)
    boundaries = np.flatnonzero(np.diff(times.asi8) != 300_000_000_000) + 1
    result = np.asarray(steady).copy()
    for segment in np.split(np.arange(len(times)), boundaries):
        if len(segment) < 5:
            continue
        values = pd.Series(steady[segment], index=times[segment])
        result[segment] = pvlib.temperature.prilliman(
            values,
            pd.Series(wind[segment], index=times[segment]),
            unit_mass=12 / 0.72,
        ).to_numpy()
    return result


def dc_power(
    poa: np.ndarray, module_temperature: np.ndarray, delta_t: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """CEC single-diode model, with explicit module-to-cell temperature assumption.

    delta_t=0 follows the upstream Faiman treatment. No cell-temperature
    observation is claimed from a back-of-module sensor.
    """
    module = pvlib.pvsystem.retrieve_sam("cecmod")["First_Solar__Inc__FS_4117_3"]
    cell = pvlib.temperature.sapm_cell_from_module(module_temperature, poa, delta_t)
    parameters = pvlib.pvsystem.calcparams_cec(
        poa,
        cell,
        module.alpha_sc,
        module.a_ref,
        module.I_L_ref,
        module.I_o_ref,
        module.R_sh_ref,
        module.R_s,
        module.Adjust,
    )
    dc = pvlib.pvsystem.singlediode(*parameters, method="lambertw")
    # Explicit upstream PVWatts losses, excluding shading and availability.
    factor = 1 - pvlib.pvsystem.pvwatts_losses(shading=0, availability=0) / 100
    return np.asarray(dc["p_mp"]) * 15 * 1344 * factor, np.asarray(dc["v_mp"]) * 15


def inverter(p_dc: np.ndarray, v_dc: np.ndarray) -> np.ndarray:
    parameters = pvlib.pvsystem.retrieve_sam("cecinverter")["TMEIC__PVL_L1833GRM"]
    return np.asarray(pvlib.inverter.sandia(v_dc, p_dc, parameters)) / 1000
