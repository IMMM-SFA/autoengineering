"""HOPP's coupled renewable generation, storage dispatch and grid simulation."""

from __future__ import annotations

from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SOLAR = "35.2018863_-101.945027_psmv3_60_2012.csv"
WIND = "35.2018863_-101.945027_windtoolkit_2012_60min_80m_100m.srw"
PRICES = "pricing-data-2015-IronMtn-002_factors.csv"


def configuration(method: str, smoke: bool = False, soc_margin: float = 0.0) -> dict:
    """Fixed hardware from HOPP example 03; only the dispatch policy changes."""
    return {
        "name": "HOPP wind solar battery dispatch comparison",
        "site": {
            "data": {
                "lat": 35.2018863,
                "lon": -101.945027,
                "elev": 1099,
                "year": 2012,
                "tz": -6,
                "site_boundaries": {
                    "verts": [
                        [3.06, 288.87],
                        [0, 1084.03],
                        [1784.05, 1084.24],
                        [1794.09, 999.64],
                        [1494.34, 950.97],
                        [712.64, 262.8],
                        [1216.98, 272.36],
                        [1217.76, 151.62],
                        [708.14, 0],
                    ]
                },
            },
            "solar_resource_file": str(HERE / "data" / SOLAR),
            "wind_resource_file": str(HERE / "data" / WIND),
            "grid_resource_file": str(HERE / "data" / PRICES),
            "solar": True,
            "wind": True,
            "wave": False,
            "hub_height": 97.0,
        },
        "technologies": {
            "pv": {"system_capacity_kw": 50000, "dc_degradation": [0]},
            "wind": {"num_turbines": 10, "turbine_rating_kw": 5000},
            "battery": {
                "system_capacity_kwh": 80000,
                "system_capacity_kw": 20000,
                "minimum_SOC": 10,
                "maximum_SOC": 90 - soc_margin,
                "initial_SOC": 10,
            },
            "grid": {"interconnect_kw": 50000, "ppa_price": 0.04},
        },
        "config": {
            "dispatch_options": {
                "battery_dispatch": method,
                "solver": "cbc",
                "grid_charging": False,
                "include_lifecycle_count": False,
                "n_look_ahead_periods": 24,
                "n_roll_periods": 24,
                "is_test_start_year": smoke,
            }
        },
    }


def dispatch(
    smoke_flag: np.ndarray, method: str = "one_cycle_heuristic", soc_margin: float = 0.0
) -> tuple:
    """Keep the coupled solver inside HOPP, expose its actual component outputs."""
    from hopp.simulation import HoppInterface

    smoke = bool(smoke_flag[0])
    interface = HoppInterface(configuration(method, smoke, soc_margin))
    interface.simulate_power(project_life=1)
    plant = interface.system
    n = 120 if smoke else plant.site.n_timesteps
    pv = np.asarray(plant.pv.generation_profile[:n])
    wind = np.asarray(plant.wind.generation_profile[:n])
    battery = np.asarray(plant.battery.generation_profile[:n])
    grid = np.asarray(plant.grid.generation_profile[:n])
    soc = np.asarray(plant.battery.outputs.SOC[:n])
    price = np.asarray(plant.site.elec_prices.data[:n]) * 0.04
    return pv, wind, battery, grid, soc, price


def revenue(grid_kw: np.ndarray, price: np.ndarray) -> np.ndarray:
    """Hourly revenue in USD, without claiming plant NPV or economic optimality."""
    return grid_kw * price


def check_physics(arrays: dict) -> None:
    lengths = {len(value) for value in arrays.values()}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) not in {120, 8760}:
        raise ValueError("Hybrid outputs must share 120 or 8760 hourly steps")
    if arrays["grid_kw"].min() < -1:
        raise ValueError("Grid import exceeds 1 kW numerical tolerance with grid charging disabled")
    for key, value in arrays.items():
        if not np.isfinite(value).all():
            raise ValueError(f"Nonfinite hybrid output: {key}")
    if np.max(arrays["grid_kw"]) > 50000 + 1:
        raise ValueError("Grid export limit exceeded")
    if np.max(np.abs(arrays["battery_kw"])) > 20000 + 100:
        raise ValueError("Battery power limit exceeded")
    if np.min(arrays["soc"]) < 9 or np.max(arrays["soc"]) > 91:
        raise ValueError(
            f"Battery SOC screening range [9, 91] exceeded: [{arrays['soc'].min()}, {arrays['soc'].max()}]"
        )
    if np.any(arrays["grid_kw"] > arrays["pv_kw"] + arrays["wind_kw"] + arrays["battery_kw"] + 1):
        raise ValueError("Grid output exceeds available generation")
