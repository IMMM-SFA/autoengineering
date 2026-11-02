"""Test inferred PVDAQ equipment on development data, never confirmation years."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

FILES = {
    "electrical": ("2107_electrical_data_v1.csv", {"inv_01_ac_power_inv_149583": "ac"}),
    "irradiance": ("2107_irradiance_data.csv", {"poa_irradiance_o_149574": "poa"}),
    "environment": (
        "2107_environment_data.csv",
        {"ambient_temperature_o_149575": "temperature", "wind_speed_o_149576": "wind"},
    ),
}


def load(root: Path):
    frames, coverage = [], {}
    for name, (filename, columns) in FILES.items():
        frame = pd.read_csv(root / filename, usecols=["measured_on", *columns])
        frame["measured_on"] = pd.to_datetime(frame["measured_on"])
        if frame.measured_on.max() >= pd.Timestamp("2019-07-01"):
            raise ValueError("Development input includes dates beyond the fixed cutoff")
        frame = frame.set_index("measured_on").rename(columns=columns)
        frame = frame.loc[~frame.index.duplicated(keep=False)].sort_index()
        frame = frame.loc["2019-01-01":"2019-06-30"].apply(pd.to_numeric, errors="coerce")
        counts = frame.resample("15min").count()
        values = frame.resample("15min").mean()
        required = 1 if name == "environment" else 3
        values = values.where(counts >= required)
        coverage[name] = {
            "input_rows": len(frame),
            "complete_bins": int(values.notna().all(axis=1).sum()),
        }
        frames.append(values)
    data = pd.concat(frames, axis=1)
    data.temperature = (data.temperature - 32) * (5 / 9)
    data.wind = data.wind * 0.44704
    data = data.where(
        data.ac.between(-0.1, 29)
        & data.poa.between(0, 1400)
        & data.temperature.between(-20, 60)
        & data.wind.between(0, 40),
        np.nan,
    )
    return data, coverage


def predict(data, panels, scale):
    temperature = pvlib.temperature.faiman(data.poa, data.temperature, data.wind)
    dc = pvlib.pvsystem.pvwatts_dc(data.poa, temperature, panels * 310, -0.004) * scale
    return pvlib.inverter.pvwatts(dc, 27600 / 0.96) / 1000


def metrics(data, prediction, phase):
    months = data.index.month
    mask = (months <= 3) if phase == "fit" else (months >= 4)
    mask &= data.notna().all(axis=1) & prediction.notna() & (data.poa >= 100)
    y, p = data.loc[mask, "ac"], prediction.loc[mask]
    if len(y) < 1000 or y.sum() <= 0:
        return {"rows": len(y), "usable": False}
    rmse = float(np.sqrt(np.mean((p - y) ** 2)))
    bias = float(p.sum() / y.sum() - 1)
    corr = float(y.corr(p))
    return {
        "rows": len(y),
        "usable": True,
        "rmse_kw": rmse,
        "rmse_fraction_ac_rating": rmse / 27.6,
        "daylight_energy_bias": bias,
        "correlation": corr,
        "screen_pass": rmse / 27.6 <= 0.2 and abs(bias) <= 0.1 and corr >= 0.85,
    }


def run(root):
    data, coverage = load(root)
    results = []
    for shift in (0, -15, 15):
        shifted = data.copy()
        shifted[["poa", "temperature", "wind"]] = data[["poa", "temperature", "wind"]].shift(
            shift // 15
        )
        for panels in (80, 120, 160, 200):
            base = predict(shifted, panels, 1.0)
            fit = (
                (shifted.index.month <= 3)
                & shifted.notna().all(axis=1)
                & shifted.poa.between(200, 600)
            )
            scale = float(
                np.clip(
                    np.dot(base[fit], shifted.ac[fit]) / np.dot(base[fit], base[fit]), 0.8, 1.05
                )
            )
            for label, multiplier in [
                ("calibrated", scale),
                *([("nominal", 1.0)] if shift == 0 else []),
            ]:
                pred = predict(shifted, panels, multiplier)
                results.append(
                    {
                        "round": label,
                        "panels": panels,
                        "dc_capacity_kw": panels * 0.310,
                        "driver_shift_minutes": shift,
                        "loss_multiplier": multiplier,
                        "fit": metrics(shifted, pred, "fit"),
                        "check": metrics(shifted, pred, "check"),
                    }
                )
    eligible = [r for r in results if r["fit"]["usable"]]
    selected = min(eligible, key=lambda r: r["fit"]["rmse_kw"]) if eligible else None
    initial = next(r for r in results if r["round"] == "nominal" and r["panels"] == 120)
    output = {
        "schema": "solar-inferred-equipment-development-v1",
        "pvlib_version": pvlib.__version__,
        "fit_window": ["2019-01-01", "2019-03-31"],
        "check_window": ["2019-04-01", "2019-06-30"],
        "coverage": coverage,
        "configurations": len(results),
        "initial_guess": initial,
        "selected_by_fit_only": selected,
        "results": results,
        "confirmation_accessed": False,
        "physical_mapping_authenticated": False,
        "interval_assumption": "same source wall clock; left 15-minute bins; complete 5-minute electrical/POA bins; environmental samples averaged within bin; ambiguous duplicates dropped",
        "claim": "conditional development prediction plausibility only; no physical topology identification or annual energy validation",
    }
    (root / "result.json").write_text(json.dumps(output, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {"initial_guess": initial, "selected_by_fit_only": selected, "coverage": coverage},
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("development_directory", type=Path)
    run(parser.parse_args().development_directory)
