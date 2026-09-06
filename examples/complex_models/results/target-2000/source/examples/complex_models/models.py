"""Larger hydrologic and photovoltaic chains using measured forcing and BMI."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pvlib.pvsystem import calcparams_desoto, max_power_point

from autoengineering.optimization import CategoricalParameter, ContinuousParameter, SearchSpace
from autoengineering.system.graph import System
from examples.local_models import models as original
from examples.local_models.bmi_base import ScalarBmi
from examples.local_models.bmi_chain import run_components

ROOT = Path(__file__).resolve().parent
DOMAINS = (*original.DOMAINS, "hymod", "solar_diode")
BASE_DOMAIN = {**{d: d for d in original.DOMAINS}, "hymod": "hydro", "solar_diode": "solar"}
MODULE = json.loads((ROOT / "module.json").read_text())["parameters"]
BASELINES = {
    "hymod": dict(
        pet="hargreaves", cmax=300.0, beta=1.0, alpha=0.5, kfast=0.5, kslow=0.05, pet_scale=1.0
    ),
    "solar_diode": dict(
        heat_loss=25.0,
        irradiance_scale=1.0,
        rs_scale=1.0,
        rsh_scale=1.0,
        io_scale=1.0,
        a_scale=1.0,
        loss=0.85,
    ),
}


def load_data(domain: str) -> pd.DataFrame:
    return original.load_data(BASE_DOMAIN[domain])


def score(domain: str, data: pd.DataFrame, output: dict, split: str) -> dict:
    return original.metrics(BASE_DOMAIN[domain], data, output, split)


def search_space(domain: str) -> SearchSpace:
    if domain in original.DOMAINS:
        return original.search_space(domain)
    if domain == "hymod":
        return SearchSpace(
            [
                CategoricalParameter("pet", ("hamon", "hargreaves")),
                ContinuousParameter("cmax", 50.0, 1000.0, scale="log"),
                ContinuousParameter("beta", 0.1, 3.0),
                ContinuousParameter("alpha", 0.05, 0.95),
                ContinuousParameter("kfast", 0.1, 0.9),
                ContinuousParameter("kslow", 0.001, 0.15, scale="log"),
                ContinuousParameter("pet_scale", 0.5, 1.5),
            ]
        )
    return SearchSpace(
        [
            ContinuousParameter("heat_loss", 15.0, 60.0),
            ContinuousParameter("irradiance_scale", 0.85, 1.15),
            ContinuousParameter("rs_scale", 0.5, 2.0, scale="log"),
            ContinuousParameter("rsh_scale", 0.5, 2.0, scale="log"),
            ContinuousParameter("io_scale", 0.3, 3.0, scale="log"),
            ContinuousParameter("a_scale", 0.8, 1.2),
            ContinuousParameter("loss", 0.6, 1.05),
        ]
    )


class PdmSoilBmi(ScalarBmi):
    """Pareto-distributed soil capacity with storage-limited evapotranspiration."""

    INPUTS = {"precipitation": "mm d-1", "potential_evaporation": "mm d-1"}
    OUTPUTS = {"excess_water": "mm d-1", "actual_evaporation": "mm d-1", "soil_storage": "mm"}
    TIME_UNITS = "d"

    def _initialize_model(self) -> None:
        p = self.parameters
        self.cmax, self.beta = float(p["cmax"]), float(p["beta"])
        self.scale = float(p["pet_scale"])
        if min(self.cmax, self.beta, self.scale) <= 0:
            raise ValueError("Soil parameters must be positive")
        self.smax = self.cmax / (1 + self.beta)
        self._values["soil_storage"][0] = self.smax / 2

    def _step(self) -> None:
        v = self._values
        rain, pet, old = (v[n][0] for n in self.INPUTS | {"soil_storage": "mm"})
        if min(rain, pet) < 0:
            raise ValueError("Fluxes must be nonnegative")
        capacity = self.cmax * (1 - max(0, 1 - old / self.smax) ** (1 / (1 + self.beta)))
        overflow = max(0.0, rain + capacity - self.cmax)
        infiltration = rain - overflow
        new = self.smax * (
            1 - max(0.0, 1 - (capacity + infiltration) / self.cmax) ** (1 + self.beta)
        )
        runoff = overflow + max(0.0, infiltration - (new - old))
        evaporation = min(new, pet * self.scale * new / self.smax)
        v["soil_storage"][0] = new - evaporation
        v["excess_water"][0] = runoff
        v["actual_evaporation"][0] = evaporation


class ParallelRoutingBmi(ScalarBmi):
    """One slow reservoir in parallel with a cascade of three fast reservoirs."""

    FAST_STORES = 3
    INPUTS = {"excess_water": "mm d-1"}
    OUTPUTS = {"flow": "mm d-1", "routing_storage": "mm"}
    TIME_UNITS = "d"

    def _initialize_model(self) -> None:
        self.alpha, self.kfast, self.kslow = (
            float(self.parameters[k]) for k in ["alpha", "kfast", "kslow"]
        )
        if not all(0 <= x <= 1 for x in [self.alpha, self.kfast, self.kslow]):
            raise ValueError("Routing fractions must be in [0,1]")
        self.stores = np.zeros(1 + self.FAST_STORES)

    def _step(self) -> None:
        excess = self._values["excess_water"][0]
        if excess < 0:
            raise ValueError("Excess must be nonnegative")
        self.stores[0] += (1 - self.alpha) * excess
        slow = self.kslow * self.stores[0]
        self.stores[0] -= slow
        quick = self.alpha * excess
        for i in range(1, len(self.stores)):
            self.stores[i] += quick
            quick = self.kfast * self.stores[i]
            self.stores[i] -= quick
        self._values["flow"][0] = slow + quick
        self._values["routing_storage"][0] = self.stores.sum()


class EffectiveIrradianceBmi(ScalarBmi):
    INPUTS = {"irradiance": "W m-2"}
    OUTPUTS = {"effective_irradiance": "W m-2"}

    def _step(self) -> None:
        self._values["effective_irradiance"][:] = (
            self._values["irradiance"] * self.parameters["irradiance_scale"]
        )


def diode_power(irradiance, temperature, p: dict):
    """Solve the equivalent module and scale its watts to plant kilowatts."""
    params = calcparams_desoto(
        irradiance,
        temperature,
        alpha_sc=MODULE["alpha_sc"],
        a_ref=MODULE["a_ref"] * p["a_scale"],
        I_L_ref=MODULE["I_L_ref"],
        I_o_ref=MODULE["I_o_ref"] * p["io_scale"],
        R_sh_ref=MODULE["R_sh_ref"] * p["rsh_scale"],
        R_s=MODULE["R_s"] * p["rs_scale"],
        EgRef=1.121,
        dEgdT=-0.0002677,
    )
    return max_power_point(*params, method="brentq")["p_mp"] * (2369.0 / MODULE["STC"]) * p["loss"]


class SingleDiodeBmi(ScalarBmi):
    INPUTS = {"effective_irradiance": "W m-2", "module_temperature": "degC"}
    OUTPUTS = {"dc_power": "kW"}

    def _step(self) -> None:
        v = self._values
        irradiance = v["effective_irradiance"][0]
        if irradiance < 0:
            raise ValueError("Irradiance must be nonnegative")
        v["dc_power"][0] = (
            0.0
            if irradiance == 0
            else diode_power(irradiance, v["module_temperature"][0], self.parameters)
        )


def evaluate(domain: str, data: pd.DataFrame, config: dict, system: System | None = None) -> dict:
    if domain in original.DOMAINS:
        return original.MODELS[domain](data, config)
    system = system or System.from_yaml(ROOT / f"{domain}-system.yaml")
    components = {}
    for name in system.topological_order():
        module, cls = system.get_component(name).metadata["bmi_class"].split(":")
        components[name] = getattr(importlib.import_module(module), cls)(
            dict(config, temperature="ross", end_time=len(data))
        )
    if domain == "hymod":
        forcing = {
            "pet": {
                "air_temperature": data.tmean_c.to_numpy(),
                "maximum_temperature": data.tmax_c.to_numpy(),
                "minimum_temperature": data.tmin_c.to_numpy(),
                "day_of_year": pd.to_datetime(data.date).dt.dayofyear.to_numpy(),
            },
            "soil": {"precipitation": data.precip_mm.to_numpy()},
        }
    else:
        forcing = {
            "effective": {"irradiance": data.poa_w_m2.to_numpy()},
            "temperature": {"air_temperature": data.air_c.to_numpy()},
        }
    connections = [
        (c["source"], c["port_from"], c["target"], c["port_to"]) for c in system.connections
    ]
    out = run_components(components, connections, forcing, len(data))
    if domain == "hymod":
        storage = out["soil"]["soil_storage"] + out["routing"]["routing_storage"]
        balance = (
            data.precip_mm.to_numpy()
            - out["soil"]["actual_evaporation"]
            - out["routing"]["flow"]
            - np.diff(np.r_[config["cmax"] / (1 + config["beta"]) / 2, storage])
        )
        return {
            "prediction": out["routing"]["flow"],
            "balance_residual": balance,
            "storage": storage,
            "aet": out["soil"]["actual_evaporation"],
        }
    return {
        "prediction": out["inverter"]["ac_power"],
        "temperature": out["temperature"]["module_temperature"],
    }


class SingleFastRoutingBmi(ParallelRoutingBmi):
    """Simpler routing alternative with one fast reservoir for the swap example."""

    FAST_STORES = 1


class EmpiricalDcBmi(SingleDiodeBmi):
    """PVWatts alternative with the same BMI exchange ports as the diode model."""

    def _step(self) -> None:
        from pvlib.pvsystem import pvwatts_dc

        self._values["dc_power"][:] = (
            pvwatts_dc(
                self._values["effective_irradiance"],
                self._values["module_temperature"],
                pdc0=2369.0,
                gamma_pdc=-0.0028,
            )
            * self.parameters["loss"]
        )
