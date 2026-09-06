"""Small physical and empirical models evaluated against measured responses."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from autoengineering.optimization import (
    CategoricalParameter,
    ContinuousParameter,
    SearchSpace,
)

ROOT = Path(__file__).resolve().parent
DOMAINS = ("hydro", "solar", "copper")


def load_data(domain: str) -> pd.DataFrame:
    if domain not in DOMAINS:
        raise ValueError(f"Unknown domain: {domain}")
    return pd.read_csv(ROOT / "data" / f"{domain}.csv")


def _leaf_function(module: str, function: str):
    path = ROOT.parent / "leaf_river" / "models" / f"{module}.py"
    spec = importlib.util.spec_from_file_location(f"local_leaf_{module}", path)
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)
    return getattr(imported, function)


HAMON = _leaf_function("pet_hamon", "hamon_pet")
HARGREAVES = _leaf_function("pet_hargreaves", "hargreaves_pet")
BUCKET = _leaf_function("soil_moisture", "soil_bucket")


def hydro_model(data: pd.DataFrame, config: dict[str, Any]) -> dict[str, np.ndarray]:
    """PET, soil bucket, and one linear reservoir with an explicit water balance."""
    doy = pd.to_datetime(data.date).dt.dayofyear.to_numpy()
    if config["pet"] == "hamon":
        pet = HAMON(data.tmean_c.to_numpy(), doy)
    else:
        pet = HARGREAVES(
            data.tmean_c.to_numpy(), data.tmax_c.to_numpy(), data.tmin_c.to_numpy(), doy
        )
    capacity = float(config["capacity"])
    aet, excess, soil = BUCKET(data.precip_mm.to_numpy(), pet, capacity, capacity / 2)
    storage = 0.0
    flow, routed_storage = [], []
    recession = float(config["recession"])
    for value in excess:
        storage += value
        outflow = (1 - recession) * storage
        storage -= outflow
        flow.append(outflow)
        routed_storage.append(storage)
    # Delta storage plus ET plus discharge must equal precipitation each day.
    total_storage = soil + np.asarray(routed_storage)
    balance = (
        data.precip_mm.to_numpy()
        - aet
        - np.asarray(flow)
        - np.diff(np.r_[capacity / 2, total_storage])
    )
    return {
        "prediction": np.asarray(flow),
        "pet": pet,
        "soil": soil,
        "balance_residual": balance,
        "aet": aet,
    }


def solar_temperature(
    poa: np.ndarray, air: np.ndarray, *, model: str, heat_loss: float
) -> np.ndarray:
    """Ambient-only simplification or Ross steady-state temperature model."""
    if model == "ambient":
        return np.asarray(air).copy()
    from pvlib.temperature import ross

    # Ross: Tmodule = Tair + (NOCT - 20) * POA / 800.
    return ross(poa, air, noct=20 + 800 / heat_loss)


def solar_power(poa: np.ndarray, module: np.ndarray, *, loss: float) -> np.ndarray:
    """PVWatts DC and inverter conversion for the second 1910 kW inverter."""
    from pvlib.inverter import pvwatts
    from pvlib.pvsystem import pvwatts_dc

    # Fixed metadata: half of 4738 kW DC, gamma=-0.28 percent/C.
    # Cell/module equality is an explicit approximation in this small example.
    dc = pvwatts_dc(poa, module, pdc0=2369.0, gamma_pdc=-0.0028) * loss
    return pvwatts(dc, pdc0=1910.0 / 0.96, eta_inv_nom=0.96)


def solar_model(data: pd.DataFrame, config: dict[str, Any]) -> dict[str, np.ndarray]:
    poa, air = data.poa_w_m2.to_numpy(), data.air_c.to_numpy()
    temperature = solar_temperature(
        poa, air, model=config["temperature"], heat_loss=float(config["heat_loss"])
    )
    return {
        "prediction": solar_power(poa, temperature, loss=float(config["loss"])),
        "temperature": temperature,
    }


def copper_model(data: pd.DataFrame, config: dict[str, Any]) -> dict[str, np.ndarray]:
    """Fit polynomial or NIST rational regression on training observations only."""
    degree = 2 if config["model"] == "rational2" else 3
    x = data.temperature_k.to_numpy() / 800
    y = data.expansion.to_numpy()
    train = data.split.to_numpy() == "train"
    powers = np.polynomial.polynomial.polyvander(x, degree)
    ridge = float(config["ridge"])
    if config["model"] == "polynomial":
        coefficients = np.linalg.lstsq(
            np.vstack([powers[train], np.sqrt(ridge) * np.eye(degree + 1)]),
            np.r_[y[train], np.zeros(degree + 1)],
            rcond=None,
        )[0]
        return {"prediction": powers @ coefficients}

    def predict(parameters):
        denominator = 1 + powers[:, 1:] @ parameters[degree + 1 :]
        return (powers @ parameters[: degree + 1]) / denominator

    def residual(parameters):
        # Nonnegative denominator coefficients guarantee no positive-temperature pole.
        return np.r_[predict(parameters)[train] - y[train], np.sqrt(ridge) * parameters]

    initial = np.r_[np.linalg.lstsq(powers[train], y[train], rcond=None)[0], np.zeros(degree)]
    lower = np.r_[np.full(degree + 1, -np.inf), np.zeros(degree)]
    result = least_squares(residual, initial, bounds=(lower, np.inf), max_nfev=500)
    if not result.success:
        raise ValueError(f"Rational fit failed: {result.message}")
    return {"prediction": predict(result.x)}


MODELS = {"hydro": hydro_model, "solar": solar_model, "copper": copper_model}
TARGETS = {"hydro": "flow_mm_day", "solar": "power_kw", "copper": "expansion"}
UNITS = {"hydro": "mm/day", "solar": "kW", "copper": "source expansion units"}
BASELINES = {
    "hydro": {"pet": "hamon", "capacity": 100.0, "recession": 0.7},
    "solar": {"temperature": "ambient", "heat_loss": 25.0, "loss": 1.0},
    "copper": {"model": "polynomial", "ridge": 1e-6},
}
SWAPS = {
    "hydro": [dict(BASELINES["hydro"], pet="hargreaves")],
    "solar": [dict(BASELINES["solar"], temperature="ross")],
    "copper": [{"model": "rational2", "ridge": 1e-6}, {"model": "rational3", "ridge": 1e-6}],
}


def search_space(domain: str) -> SearchSpace:
    if domain == "hydro":
        return SearchSpace(
            (
                CategoricalParameter("pet", ("hamon", "hargreaves")),
                ContinuousParameter("capacity", 20, 200),
                ContinuousParameter("recession", 0.05, 0.95),
            )
        )
    if domain == "solar":
        return SearchSpace(
            (
                CategoricalParameter("temperature", ("ambient", "ross")),
                ContinuousParameter("heat_loss", 15, 60),
                ContinuousParameter("loss", 0.6, 1.05),
            )
        )
    if domain == "copper":
        return SearchSpace(
            (
                CategoricalParameter("model", ("polynomial", "rational2", "rational3")),
                ContinuousParameter("ridge", 1e-8, 1e-1, scale="log"),
            )
        )
    raise ValueError(domain)


def metrics(
    domain: str, data: pd.DataFrame, outputs: dict[str, np.ndarray], split: str
) -> dict[str, float]:
    selected = data.split.to_numpy() == split
    observed = data[TARGETS[domain]].to_numpy()[selected]
    predicted = outputs["prediction"][selected]
    if not len(observed) or not np.isfinite(predicted).all():
        raise ValueError("Empty split or nonfinite model output")
    result = {
        "rmse": float(np.sqrt(np.mean((predicted - observed) ** 2))),
        "bias": float(np.mean(predicted - observed)),
    }
    if domain == "solar":
        result["temperature_rmse"] = float(
            np.sqrt(
                np.mean(
                    (outputs["temperature"][selected] - data.module_c.to_numpy()[selected]) ** 2
                )
            )
        )
    if domain == "hydro":
        result["nse"] = float(
            1 - np.sum((predicted - observed) ** 2) / np.sum((observed - observed.mean()) ** 2)
        )
        result["max_balance_error"] = float(np.max(np.abs(outputs["balance_residual"])))
    return result
