"""Public application adapters. All model evaluations execute through BMI."""

from __future__ import annotations

import numpy as np
import pandas as pd
from autoengineering.system.graph import System

from examples.local_models.kernels import (  # noqa: F401
    BASELINES,
    DOMAINS,
    ROOT,
    SWAPS,
    TARGETS,
    UNITS,
    load_data,
    metrics,
    search_space,
)


def hydro_model(data: pd.DataFrame, config: dict) -> dict[str, np.ndarray]:
    from examples.local_models.bmi_chain import run_chain

    return run_chain("hydro", data, config)


def solar_model(data: pd.DataFrame, config: dict) -> dict[str, np.ndarray]:
    from examples.local_models.bmi_chain import run_chain

    return run_chain("solar", data, config)


def copper_model(data: pd.DataFrame, config: dict) -> dict[str, np.ndarray]:
    from examples.local_models.bmi_chain import run_chain

    return run_chain("copper", data, config)


def evaluate_system(domain: str, data: pd.DataFrame, system: System) -> dict[str, np.ndarray]:
    from examples.local_models.bmi_chain import run_chain

    owner = {"hydro": "pet", "solar": "temperature", "copper": "regression"}[domain]
    config = system.get_component(owner).metadata["configuration"]
    return run_chain(domain, data, config, system)


def solar_temperature(
    poa: np.ndarray, air: np.ndarray, *, model: str, heat_loss: float
) -> np.ndarray:
    from examples.local_models.bmi_chain import run_components
    from examples.local_models.bmi_components import SolarTemperatureBmi

    outputs = run_components(
        {
            "temperature": SolarTemperatureBmi(
                {"temperature": model, "heat_loss": heat_loss, "end_time": len(poa)}
            )
        },
        [],
        {"temperature": {"irradiance": np.asarray(poa), "air_temperature": np.asarray(air)}},
        len(poa),
    )
    return outputs["temperature"]["module_temperature"]


def solar_power(poa: np.ndarray, module: np.ndarray, *, loss: float) -> np.ndarray:
    from examples.local_models.bmi_chain import run_components
    from examples.local_models.bmi_components import PvWattsDcBmi, PvWattsInverterBmi

    outputs = run_components(
        {
            "dc": PvWattsDcBmi({"loss": loss, "end_time": len(poa)}),
            "inverter": PvWattsInverterBmi({"end_time": len(poa)}),
        },
        [("dc", "dc_power", "inverter", "dc_power")],
        {"dc": {"irradiance": np.asarray(poa), "module_temperature": np.asarray(module)}},
        len(poa),
    )
    return outputs["inverter"]["ac_power"]


MODELS = {"hydro": hydro_model, "solar": solar_model, "copper": copper_model}
