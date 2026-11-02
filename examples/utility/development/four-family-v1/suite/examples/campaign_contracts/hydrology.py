"""Stateful wrapper around the existing Leaf River equations, with explicit stores.

No observed discharge enters preparation or execution. A new handle initializes
soil at half its own capacity and the reservoir at zero. A continuing handle
preserves those stores across forcing chunks.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from autoengineering.adapters.contracts import PrepareContext, TrainingResult
from examples.leaf_river.models.pet_hamon import hamon_pet
from examples.leaf_river.models.pet_hargreaves import hargreaves_pet
from examples.leaf_river.models.soil_moisture import soil_bucket

SOURCES = (
    "examples/leaf_river/models/__init__.py",
    "examples/campaign_contracts/hydrology.py",
    "examples/leaf_river/models/pet_hamon.py",
    "examples/leaf_river/models/pet_hargreaves.py",
    "examples/leaf_river/models/soil_moisture.py",
)


@dataclass
class Handle:
    context: PrepareContext
    soil: float
    reservoir: float = 0.0
    closed: bool = False


class HydrologyAdapter:
    def prepare(self, context: PrepareContext) -> Handle:
        capacity = context.parameters.get("capacity")
        if type(capacity) not in (int, float):
            raise ValueError("capacity must be numeric")
        return Handle(context, float(capacity) / 2)

    def validate(self, handle: Handle) -> None:
        parameters = handle.context.parameters
        if set(parameters) != {"capacity", "recession", "pet"}:
            raise ValueError("hydrology parameters must be exactly capacity, recession and pet")
        if handle.closed or parameters["pet"] not in ("hamon", "hargreaves"):
            raise ValueError("invalid model implementation or closed handle")
        for name, lower, upper in (("capacity", 20, 200), ("recession", 0.05, 0.95)):
            value = parameters[name]
            if (
                type(value) not in (int, float)
                or not np.isfinite(value)
                or not lower <= value <= upper
            ):
                raise ValueError(f"{name} is outside declared bounds")
        if {port.name for port in handle.context.model.inputs} != {
            "precip_mm",
            "tmean_c",
            "tmax_c",
            "tmin_c",
            "day_of_year",
        }:
            raise ValueError("both PET families require the complete meteorological interface")

    def train(self, handle: Handle, fitting_data) -> TrainingResult:
        return TrainingResult("not_applicable", None, None)

    def run(self, handle: Handle, forcing):
        self.validate(handle)
        if set(forcing) != {port.name for port in handle.context.model.inputs}:
            raise ValueError("missing required meteorological input")
        params = handle.context.parameters
        initial_soil, initial_reservoir = handle.soil, handle.reservoir
        if params["pet"] == "hamon":
            pet = hamon_pet(forcing["tmean_c"], forcing["day_of_year"])
        else:
            pet = hargreaves_pet(
                forcing["tmean_c"], forcing["tmax_c"], forcing["tmin_c"], forcing["day_of_year"]
            )
        aet, excess, soil = soil_bucket(
            forcing["precip_mm"],
            pet,
            float(params["capacity"]),
            handle.soil,
        )
        flow, reservoirs = [], []
        for value in excess:
            handle.reservoir += value
            discharge = (1 - float(params["recession"])) * handle.reservoir
            handle.reservoir -= discharge
            flow.append(discharge)
            reservoirs.append(handle.reservoir)
        if len(soil):
            handle.soil = float(soil[-1])
        return {
            "prediction": np.asarray(flow),
            "soil": soil,
            "reservoir": np.asarray(reservoirs),
            "aet": aet,
            "pet": pet,
            "initial_soil": np.asarray(initial_soil),
            "initial_reservoir": np.asarray(initial_reservoir),
        }

    def inspect(self, handle: Handle, outputs):
        return MappingProxyType({"final_stores": np.asarray([handle.soil, handle.reservoir])})

    def cleanup(self, handle: Handle | None) -> None:
        if handle is not None:
            handle.closed = True
