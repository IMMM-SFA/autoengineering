"""Measured-POA development check for the documented PVDAQ 1278 system."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib


def predict(poa, ambient_c, wind_m_s, scale=1.0):
    temperature = pvlib.temperature.faiman(poa, ambient_c, wind_m_s)
    branch_dc = pvlib.pvsystem.pvwatts_dc(poa, temperature, 357 * 240, -0.004) * scale
    return sum(pvlib.inverter.pvwatts(branch_dc, ac / 0.96) for ac in (100000, 50000)) / 1000


def run(root):
    paths = [
        root / "1278_development_sample.csv",
        *[root / f"1278_day_{d:02d}.csv" for d in range(2, 15)],
    ]
    data = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    dates = pd.to_datetime(data.measured_on)
    if dates.min() < pd.Timestamp("2011-10-01") or dates.max() >= pd.Timestamp("2011-10-15"):
        raise ValueError("Input outside development window")
    poa = pd.to_numeric(data.poa_irradiance__3056, errors="coerce")
    ambient = (pd.to_numeric(data.ambient_temp_f__3058, errors="coerce") - 32) * 5 / 9
    wind = pd.to_numeric(data.wind_speed_mph__3060, errors="coerce") * 0.44704
    actual = pd.to_numeric(data.ac_power__3081, errors="coerce") / 1000
    valid = (
        poa.between(100, 1400)
        & ambient.between(-20, 60)
        & wind.between(0, 40)
        & actual.between(-0.5, 157.5)
        & ~dates.duplicated(keep=False)
    )
    # The power and weather share a source clock. No clock shift is fitted.
    base = predict(poa, ambient, wind)
    fitting = valid & (dates.dt.day <= 7) & poa.between(200, 600)
    scale = float(
        np.clip(
            np.dot(base[fitting], actual[fitting]) / np.dot(base[fitting], base[fitting]), 0.8, 1.05
        )
    )
    calibrated = predict(poa, ambient, wind, scale)
    results = {}
    for name, prediction in [("nominal", base), ("calibrated", calibrated)]:
        results[name] = {}
        for phase, mask in [
            ("fit", valid & (dates.dt.day <= 7)),
            ("check", valid & (dates.dt.day > 7)),
        ]:
            y, p = actual[mask], prediction[mask]
            rmse = float(np.sqrt(np.mean((p - y) ** 2)))
            bias = float(p.sum() / y.sum() - 1)
            corr = float(y.corr(p))
            results[name][phase] = {
                "rows": len(y),
                "rmse_kw": rmse,
                "rmse_fraction_ac_rating": rmse / 150,
                "daylight_energy_bias": bias,
                "correlation": corr,
                "screen_pass": len(y) >= 200
                and rmse / 150 <= 0.2
                and abs(bias) <= 0.1
                and corr >= 0.85,
            }
    hardware_sum = (data.inv1_ac_power_hw__3070 + data.inv2_ac_power_hw__3079) * 0.1
    output = {
        "site": 1278,
        "schema": "solar-alternative-development-v1",
        "fit": ["2011-10-01", "2011-10-07"],
        "check": ["2011-10-08", "2011-10-14"],
        "loss_multiplier": scale,
        "results": results,
        "input_rows": len(data),
        "pvlib_version": pvlib.__version__,
        "model_passes": 2,
        "observed_ac_versus_hardware_sum_rmse_kw": float(
            np.sqrt(np.mean((actual - hardware_sum) ** 2))
        ),
        "time_steps_seconds": {
            str(k): int(v) for k, v in dates.diff().dt.total_seconds().value_counts().items()
        },
        "confirmation_accessed": False,
        "limitations": [
            "short development screening only",
            "PVWatts generic inverter efficiency and gamma assumption",
            "power sample alignment uses shared source clock; absolute UTC/DST not established",
            "aggregate AC W and hardware hundred-W units inferred from channel agreement",
            "no annual energy or independent confirmation claim",
        ],
    }
    (root / "alternative_result.json").write_text(
        json.dumps(output, indent=2, allow_nan=False) + "\n"
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("development_directory", type=Path)
    run(parser.parse_args().development_directory)
