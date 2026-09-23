"""Run a measured-input solar chain with chronological selection and testing."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.research.runner import run_component
from autoengineering.validate.compare import validate_arrays
from examples.open_chains.common import (
    compare,
    fetch_sources,
    output_directory,
    parser,
    verify_sources,
    write_json,
)

HERE = Path(__file__).resolve().parent
POA = "pyranometer_(class_a)_pad_2_poa_irradiance_temp_compensated_(w/m2)_o_149726"
AIR = "weather_station_ambient_temperature_(c)_o_149727"
WIND = "wind_sensor_wind_speed_(m/s)_o_149736"
TEMP = "thermocouple_pad_2_back-of-module_temperature_1_(c)_o_149730"
POWER = "inverter_2_ac_power_(kw)_inv_150144"


def load_data(start: str, end: str) -> tuple[pd.DataFrame, dict]:
    """Read only needed columns, preserving a documented complete-case mask."""
    parts = []
    for filename, columns in [
        ("9068_irradiance_data.csv", [POA]),
        ("9068_environment_data.csv", [AIR, WIND, TEMP]),
        ("9068_ac_power_data.csv", [POWER]),
    ]:
        print(f"Reading {filename}", flush=True)
        frame = pd.read_csv(HERE / "data" / filename, usecols=["measured_on", *columns])
        index = pd.DatetimeIndex(pd.to_datetime(frame.pop("measured_on")))
        # Match the upstream convention; ambiguous/nonexistent local times are excluded.
        frame.index = index.tz_localize("US/Mountain", ambiguous="NaT", nonexistent="NaT")
        frame = frame.loc[frame.index.notna()]
        if frame.index.has_duplicates:
            raise ValueError(f"Duplicate timestamps in {filename}")
        parts.append(frame.loc[start:end])
    full = pd.concat(parts, axis=1).sort_index()
    valid = np.isfinite(full[[POA, AIR, WIND]]).all(axis=1) & (full[POA] >= 0) & (full[WIND] >= 0)
    data = full.loc[valid].copy()
    if data.empty:
        raise ValueError("No valid forcing data")
    gaps = data.index.to_series().diff().ne(pd.Timedelta(minutes=5))
    since_gap = data.groupby(gaps.cumsum()).cumcount()
    # Do not remove outages or clipping based on candidate residuals.
    data["score"] = (
        (since_gap >= 4) & (data[POA] >= 50) & np.isfinite(data[[POWER, TEMP]]).all(axis=1)
    )
    data["score"] &= data[POWER] >= 0
    coverage = {
        "union_rows": len(full),
        "valid_driver_rows": len(data),
        "scored_rows": int(data["score"].sum()),
        "selection": [start, end],
        "interval_minutes": 5,
        "mask": "complete drivers, POA>=50, wind>=0, finite power and module sensor, "
        "power>=0, four-step transient warmup after every gap; outages retained",
    }
    if coverage["scored_rows"] < 24:
        raise ValueError("Fewer than 24 usable evaluation samples")
    return data, coverage


def run_chain(system, data: pd.DataFrame) -> dict[str, np.ndarray]:
    inputs = {
        "poa": data[POA].to_numpy(),
        "ambient": data[AIR].to_numpy(),
        "wind": data[WIND].to_numpy(),
        "timestamp": data.index.as_unit("ns").asi8,
    }
    thermal = run_component(system.get_component("temperature"), inputs)
    dc = run_component(system.get_component("dc"), {**inputs, **thermal})
    voltage = run_component(system.get_component("voltage"), {"value": dc["v_dc"]})
    ac = run_component(system.get_component("inverter"), {**dc, **voltage})
    return {**thermal, **dc, **ac}


def temperature_quality(values: np.ndarray) -> dict:
    """Flag implausible sensor records without repairing them or changing power scoring."""
    invalid = (~np.isfinite(values)) | (values < -60) | (values > 110)
    return {
        "status": "invalid_observation_range" if invalid.any() else "range_check_passed",
        "invalid_count": int(invalid.sum()),
        "count": len(values),
        "minimum_c": float(np.min(values)),
        "maximum_c": float(np.max(values)),
        "limits_c": [-60, 110],
    }


def evaluator(data: pd.DataFrame):
    mask = data["score"].to_numpy()

    def evaluate(system):
        arrays = run_chain(system, data)
        results = validate_arrays(
            "inverter",
            data[POWER].to_numpy()[mask],
            arrays["ac_kw"][mask],
            metrics=["rmse", "bias"],
        )
        observed_temperature = data[TEMP].to_numpy()[mask]
        thermal_status = temperature_quality(observed_temperature)
        thermal = []
        if thermal_status["status"] == "range_check_passed":
            thermal = validate_arrays(
                "temperature",
                observed_temperature,
                arrays["module_temperature"][mask],
                metrics=["rmse", "bias"],
            )
        metrics = {f"{r.component}.{r.metric}": r.value for r in [*results, *thermal]}
        metrics["temperature_observation_qa"] = thermal_status
        # This is energy over scored intervals, not annual plant energy.
        metrics["scored_energy_bias_kwh"] = float(
            np.sum(arrays["ac_kw"][mask] - data[POWER].to_numpy()[mask]) / 12
        )
        return results[0].value, metrics, {k: v[mask] for k, v in arrays.items()}

    return evaluate


def main() -> None:
    args = parser(__doc__).parse_args()
    if args.fetch:
        fetch_sources(HERE)
        return
    inputs = verify_sources(HERE)
    output = output_directory(HERE, args.output)
    end = "2018-01-07" if args.smoke else "2018-12-31"
    data, coverage = load_data("2018-01-01", end)
    evaluate = evaluator(data)

    def test(baseline, selected, destination):
        test_end = "2019-01-07" if args.smoke else "2019-12-31"
        held, held_coverage = load_data("2019-01-01", test_end)
        assess = evaluator(held)
        base, base_metrics, base_arrays = assess(baseline)
        chosen, chosen_metrics, chosen_arrays = assess(selected)
        np.savez_compressed(destination / "test-baseline.npz", **base_arrays)
        np.savez_compressed(destination / "test-selected.npz", **chosen_arrays)
        mask = held["score"].to_numpy()
        held.loc[mask, [POWER, TEMP]].to_csv(destination / "test-observed.csv")
        result = {
            "coverage": held_coverage,
            "baseline_rmse_kw": base,
            "selected_rmse_kw": chosen,
            "gain_kw": base - chosen,
            "baseline_metrics": base_metrics,
            "selected_metrics": chosen_metrics,
        }
        write_json(destination / "test.json", result)
        return result

    from autoengineering.system.graph import System

    system = System.from_yaml(HERE / "system.yaml")
    arrays = run_chain(system, data)
    mask = data["score"].to_numpy()
    validation = []
    for component, observed, simulated in [
        ("temperature", data[TEMP].to_numpy(), arrays["module_temperature"]),
        ("inverter", data[POWER].to_numpy(), arrays["ac_kw"]),
    ]:
        # Normalize RMSE by explicit illustrative tolerances, never compare C directly to kW.
        scale = 5.0 if component == "temperature" else 100.0
        if component == "temperature" and temperature_quality(observed[mask])["invalid_count"]:
            continue
        validation.extend(
            validate_arrays(
                component,
                observed[mask] / scale,
                simulated[mask] / scale,
                metrics=["rmse"],
                thresholds={"rmse": 1.0},
            )
        )
    write_json(output / "component-validation.json", [asdict(r) for r in validation])
    write_json(output / "opportunities.json", rank_opportunities(validation))
    data.loc[mask, [POWER, TEMP]].to_csv(output / "selection-observed.csv")
    compare(
        HERE,
        output,
        evaluate,
        objective="selection AC power RMSE (kW)",
        evidence="Observed plant validation, conditional on measured POA; "
        + ("smoke check only" if args.smoke else "2018 selection, 2019 held-out test"),
        packages=["autoengineering", "pvlib", "numpy", "pandas"],
        context={"inputs": inputs, "coverage": coverage, "smoke": args.smoke},
        test=test,
    )


if __name__ == "__main__":
    main()
