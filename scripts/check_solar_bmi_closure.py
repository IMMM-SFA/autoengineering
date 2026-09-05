"""Check scalar summaries using attainable configurations in the real solar BMI model."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from examples.local_models.bmi_chain import run_components
from examples.local_models.bmi_components import PvWattsDcBmi, PvWattsInverterBmi
from examples.local_models.models import load_data, solar_temperature


def power_stages(poa: np.ndarray, temperature: np.ndarray, loss: float) -> dict:
    return run_components(
        {
            "dc": PvWattsDcBmi({"loss": loss, "end_time": len(poa)}),
            "inverter": PvWattsInverterBmi({"end_time": len(poa)}),
        },
        [("dc", "dc_power", "inverter", "dc_power")],
        {"dc": {"irradiance": poa, "module_temperature": temperature}},
        len(poa),
    )


def check() -> dict:
    data = load_data("solar")
    data = data.loc[data.split != "test"]
    poa, air = data.poa_w_m2.to_numpy(), data.air_c.to_numpy()
    checks = []
    for heat_loss in [15.0, 25.0, 60.0]:
        temperature = solar_temperature(poa, air, model="ross", heat_loss=heat_loss)
        coefficient = (temperature.mean() - air.mean()) / poa.mean()
        reconstructed = air + coefficient * poa
        expected = power_stages(poa, temperature, 0.9)
        actual = power_stages(poa, reconstructed, 0.9)
        checks.append(
            {
                "heat_loss": heat_loss,
                "temperature_max_error_c": float(np.max(np.abs(temperature - reconstructed))),
                "ac_power_max_error_kw": float(
                    np.max(
                        np.abs(expected["inverter"]["ac_power"] - actual["inverter"]["ac_power"])
                    )
                ),
            }
        )
    left_temp = solar_temperature(poa, air, model="ross", heat_loss=15.0)
    right_temp = solar_temperature(poa, air, model="ross", heat_loss=60.0)
    left = power_stages(poa, left_temp, 0.9)
    right_unit = power_stages(poa, right_temp, 1.0)
    right_loss = float(left["dc"]["dc_power"].mean() / right_unit["dc"]["dc_power"].mean())
    if not 0.6 <= right_loss <= 1.05:
        raise ValueError("Counterexample leaves registered loss bounds")
    right = power_stages(poa, right_temp, right_loss)
    return {
        "temperature_summary_checks": checks,
        "attainable_dc_counterexample": {
            "left": {"heat_loss": 15.0, "loss": 0.9},
            "right": {"heat_loss": 60.0, "loss": right_loss},
            "dc_mean_difference_kw": float(
                left["dc"]["dc_power"].mean() - right["dc"]["dc_power"].mean()
            ),
            "ac_mean_difference_kw": float(
                left["inverter"]["ac_power"].mean() - right["inverter"]["ac_power"].mean()
            ),
        },
        "application_partial_bo_status": "not_implemented_or_evaluated",
        "interpretation": "Temperature mean preserves the registered Ross family on fixed forcing. "
        "Mean DC does not preserve inverter output for the demonstrated attainable configurations. "
        "Grouping DC and inverter is a candidate representation, not evidence of BO benefit.",
        "probe_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = check()
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))
