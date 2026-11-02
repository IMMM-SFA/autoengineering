"""Stage verified development inputs and exercise the new selection connections."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

from autoengineering.campaign.serialization import digest
from examples.utility.consolidated_sources import DEFAULT, save, sha


def solar():
    import pandas as pd
    from examples.utility.solar_1278_inputs import normalize
    from examples.utility.consolidated_runtime import solar as evaluate

    target = DEFAULT / "solar-development"
    target.mkdir(mode=0o700, exist_ok=False)
    root = Path("outputs/solar-mapping-development-v1")
    decision = json.loads(
        Path("examples/utility/development/solar-mapping-v1/decision.json").read_text()
    )
    paths = [
        root / "1278_development_sample.csv",
        *[root / f"1278_day_{d:02d}.csv" for d in range(2, 15)],
    ]
    for path in paths:
        if sha(path) != decision["source_files"][path.name]["sha256"]:
            raise ValueError("Solar development source changed")
    data = normalize(
        pd.concat([pd.read_csv(p) for p in paths], ignore_index=True), "2011-10-01", "2011-10-15"
    )
    for role, mask in (
        ("fitting", data["time"] < "2011-10-08"),
        ("selection", data["time"] >= "2011-10-08"),
    ):
        selected = data | {"mask": data["mask"] & mask}
        np.savez(target / f"{role}.npz", **selected)
        (target / f"{role}.npz").chmod(0o600)
    previous = json.loads(
        Path("examples/utility/development/solar-mapping-v1/alternative_refined.json").read_text()
    )
    save(
        target / "intent.json",
        {"model_starts_reserved": 1, "configuration": {"scale": previous["scale"]}},
    )
    result = evaluate(selected, {"scale": previous["scale"]})
    if not np.isclose(result["ac_rmse"], previous["metrics"]["check"]["rmse_kw"], rtol=1e-12):
        raise ValueError("Solar runtime differs from recorded development reference")
    save(
        target / "complete.json",
        {
            "status": "passed",
            "reference_agreement": True,
            "result": result,
            "files": {p.name: sha(p) for p in target.glob("*.npz")},
        },
    )
    print(json.dumps({"solar_development_connection": "passed", "new_model_starts": 1}))


def wind():
    from examples.utility.wind_hourly import WindHourly, POLICY
    from examples.utility.wind_parameters import WindGeometry
    from examples.utility.consolidated_runtime import wind as evaluate

    target = DEFAULT / "wind-development-check"
    target.mkdir(mode=0o700, exist_ok=False)
    geometry = WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0))
    profiles = []
    for year in (2010, 2011):
        root = DEFAULT / "wind_development" / str(year)
        receipt = json.loads((root / "complete.json").read_text())
        if sha(root / "point.npz") != receipt["point_sha256"]:
            raise ValueError("Wind development point changed")
        with np.load(root / "point.npz", allow_pickle=False) as data:
            profiles.append(
                WindHourly(
                    geometry,
                    year,
                    tuple(data["time_utc"].tolist()),
                    data["speed_m_s"],
                    data["direction_deg"],
                    receipt["point_sha256"],
                    digest(POLICY),
                )
            )
    save(target / "intent.json", {"model_starts_reserved": 2, "configuration": geometry.baseline})
    started = time.monotonic()
    result = evaluate(profiles, geometry.baseline)
    save(
        target / "complete.json",
        {
            "status": "passed",
            "result": result,
            "elapsed_seconds": time.monotonic() - started,
            "confirmation_accessed": False,
        },
    )
    print(json.dumps({"wind_development_connection": "passed", "result": result}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=("solar", "wind"))
    globals()[parser.parse_args().task]()
