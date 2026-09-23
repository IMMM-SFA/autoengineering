"""Couple scalar BMI components using only BMI control and exchange methods."""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd

from autoengineering.system.graph import System
from examples.local_models import kernels
from examples.local_models.bmi_components import CopperRegressionBmi


def run_components(
    components: dict,
    connections: list[tuple[str, str, str, str]],
    forcing: dict[str, dict[str, np.ndarray]],
    count: int,
) -> dict:
    """Advance already configured components in insertion/topological order."""
    initialized = []
    collected = {}
    try:
        for name, model in components.items():
            model.initialize()
            initialized.append(model)
            if (
                model.get_start_time() != 0.0
                or model.get_current_time() != 0.0
                or model.get_time_step() != 1.0
                or model.get_end_time() != float(count)
            ):
                raise ValueError("BMI driver requires start=0, step=1 and end=count")
            for variable in (*model.get_input_var_names(), *model.get_output_var_names()):
                grid = model.get_var_grid(variable)
                if (
                    model.get_grid_type(grid) != "scalar"
                    or model.get_grid_rank(grid) != 0
                    or model.get_grid_size(grid) != 1
                    or model.get_var_type(variable) != "float64"
                ):
                    raise ValueError("BMI driver requires scalar float64 exchange variables")
            collected[name] = {v: np.empty(count) for v in model.get_output_var_names()}
        order = list(components)
        for name, model in components.items():
            supplied = set(forcing.get(name, {}))
            incoming = [item[3] for item in connections if item[2] == name]
            if (
                supplied & set(incoming)
                or len(set(incoming)) != len(incoming)
                or supplied | set(incoming) != set(model.get_input_var_names())
            ):
                raise ValueError(f"BMI inputs must each have exactly one source: {name}")
            if any(len(v) != count for v in forcing.get(name, {}).values()):
                raise ValueError("BMI forcing length differs from the requested step count")
        for source, output, target, input_ in connections:
            if order.index(source) >= order.index(target):
                raise ValueError("BMI components must be in topological order")
            left, right = components[source], components[target]
            if output not in left.get_output_var_names():
                raise ValueError("A BMI connection must originate at an output variable")
            if left.get_var_units(output) != right.get_var_units(input_):
                raise ValueError(
                    f"BMI connection units differ: {source}.{output} -> {target}.{input_}"
                )
            if left.get_time_units() != right.get_time_units():
                raise ValueError("BMI component time units differ")
        for row in range(count):
            for name, model in components.items():
                for variable, values in forcing.get(name, {}).items():
                    model.set_value(variable, np.array([values[row]], dtype=float))
                for source, output, target, input_ in connections:
                    if target == name:
                        model.set_value(input_, components[source].get_value_ptr(output))
                model.update()
                for variable, values in collected[name].items():
                    values[row] = model.get_value_ptr(variable)[0]
        return collected
    finally:
        for model in reversed(initialized):
            model.finalize()


def run_chain(domain: str, data: pd.DataFrame, config: dict, system: System | None = None) -> dict:
    """Build the declared BMI model chain and feed measured forcing one sample at a time."""
    if system is None:
        system = System.from_yaml(kernels.ROOT / f"{domain}-system.yaml")
    components = {}
    for name in system.topological_order():
        definition = system.get_component(name)
        module_name, class_name = definition.metadata["bmi_class"].split(":")
        cls = getattr(importlib.import_module(module_name), class_name)
        parameters = dict(config, end_time=len(data))
        components[name] = (
            cls(parameters, training=data) if cls is CopperRegressionBmi else cls(parameters)
        )
    if domain == "hydro":
        forcing = {
            "pet": {
                "air_temperature": data.tmean_c.to_numpy(),
                "maximum_temperature": data.tmax_c.to_numpy(),
                "minimum_temperature": data.tmin_c.to_numpy(),
                "day_of_year": pd.to_datetime(data.date).dt.dayofyear.to_numpy(),
            },
            "soil_bucket": {"precipitation": data.precip_mm.to_numpy()},
        }
    elif domain == "solar":
        forcing = {
            "temperature": {
                "irradiance": data.poa_w_m2.to_numpy(),
                "air_temperature": data.air_c.to_numpy(),
            },
            "dc_power": {"irradiance": data.poa_w_m2.to_numpy()},
        }
    else:
        forcing = {"temperature_basis": {"temperature": data.temperature_k.to_numpy()}}
    connections = [
        (c["source"], c["port_from"], c["target"], c["port_to"]) for c in system.connections
    ]
    outputs = run_components(components, connections, forcing, len(data))
    if domain == "hydro":
        soil, route = outputs["soil_bucket"], outputs["routing"]
        storage = soil["soil_storage"] + route["reservoir_storage"]
        balance = (
            data.precip_mm.to_numpy()
            - soil["actual_evaporation"]
            - route["flow"]
            - np.diff(np.r_[float(config["capacity"]) / 2, storage])
        )
        return {
            "prediction": route["flow"],
            "soil": soil["soil_storage"],
            "aet": soil["actual_evaporation"],
            "pet": outputs["pet"]["potential_evaporation"],
            "balance_residual": balance,
        }
    if domain == "solar":
        return {
            "prediction": outputs["inverter"]["ac_power"],
            "temperature": outputs["temperature"]["module_temperature"],
        }
    return {"prediction": outputs["regression"]["expansion_coefficient"]}
