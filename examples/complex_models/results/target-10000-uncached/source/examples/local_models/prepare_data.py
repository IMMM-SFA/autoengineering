"""Build small tables from checked source snapshots, without network access."""

from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def prepare() -> dict[str, object]:
    """Keep explicit exclusions and fixed splits in the preparation audit."""
    raw = ROOT / "data" / "raw"
    tables = {}
    for name in ("env", "irr", "ac"):
        contents = gzip.decompress((raw / f"solar-{name}.csv.gz").read_bytes())
        # HTTP byte ranges may end inside a record. Discard only that final fragment.
        contents = contents[: contents.rfind(b"\n") + 1]
        tables[name] = pd.read_csv(io.BytesIO(contents), index_col="measured_on")
    env, irr, ac = (tables[n] for n in ("env", "irr", "ac"))
    solar = pd.DataFrame(
        {
            "air_c": env["weather_station_ambient_temperature_(c)_o_149727"],
            "module_c": env["thermocouple_pad_2_back-of-module_temperature_1_(c)_o_149730"],
            "poa_w_m2": irr[
                "pyranometer_(class_a)_pad_2_poa_irradiance_temp_compensated_(w/m2)_o_149726"
            ],
            "power_kw": ac["inverter_2_ac_power_(kw)_inv_150144"],
        }
    )
    solar = solar.loc[(solar.index >= "2024-01-01") & (solar.index < "2024-01-08")]
    n_solar = len(solar)
    finite = np.isfinite(solar).all(axis=1)
    solar = solar.loc[finite & (solar.poa_w_m2 >= 50) & (solar.power_kw >= 0)].copy()
    solar["split"] = np.where(
        solar.index < "2024-01-05",
        "train",
        np.where(solar.index < "2024-01-06", "validation", "test"),
    )
    solar.to_csv(ROOT / "data" / "solar.csv", index_label="timestamp", float_format="%.12g")

    text = (raw / "Hahn1.dat").read_text()
    copper = pd.DataFrame(
        np.loadtxt(io.StringIO(text.split("Data:   y              x")[1])),
        columns=["expansion", "temperature_k"],
    )
    # Stratify interpolation across temperature without using response values.
    order = np.argsort(copper.temperature_k.to_numpy(), kind="stable")
    split = np.full(len(copper), "train", dtype=object)
    split[order[::5]] = "test"
    split[order[1::5]] = "validation"
    copper["split"] = split
    copper.to_csv(ROOT / "data" / "copper.csv", index=False, float_format="%.12g")

    source = ROOT.parent / "leaf_river" / "data"
    flow = pd.read_csv(source / "streamflow.csv")
    weather = pd.read_csv(source / "weather.csv")
    hydro = flow.merge(weather, on="date", validate="one_to_one")
    if len(hydro) != 731 or not np.isfinite(hydro.select_dtypes("number")).all().all():
        raise ValueError("Expected complete finite 2019-2020 Leaf River cache")
    hydro["split"] = np.where(
        hydro.date < "2019-04-01",
        "warmup",
        np.where(
            hydro.date < "2019-10-01",
            "train",
            np.where(hydro.date < "2020-01-01", "validation", "test"),
        ),
    )
    hydro.to_csv(ROOT / "data" / "hydro.csv", index=False, float_format="%.12g")
    audit = {
        "solar": {
            "rows_in_window": n_solar,
            "excluded": n_solar - len(solar),
            "selection": "finite required sensors; POA >= 50 W/m2; AC >= 0 kW",
        },
        "splits": {
            n: d.split.value_counts().to_dict()
            for n, d in [("solar", solar), ("copper", copper), ("hydro", hydro)]
        },
    }
    (ROOT / "data" / "preparation.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
