"""Record post-run sensor QA without changing the frozen observations or splits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import numpy as np

from examples.complex_models.models import load_data
from examples.local_models.kernels import ROOT
from examples.local_models.run import write_json


def quality() -> dict:
    data = load_data("solar_diode")
    columns = {}
    for name in ["module_c", "air_c", "poa_w_m2", "power_kw"]:
        values = data[name].to_numpy()
        columns[name] = {
            "count": len(values),
            "finite_count": int(np.isfinite(values).sum()),
            "minimum": float(np.min(values)),
            "maximum": float(np.max(values)),
            "unique_count": int(len(np.unique(values))),
        }
    invalid = (~np.isfinite(data.module_c)) | (data.module_c < -100) | (data.module_c > 200)
    return {
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "data_path": str((ROOT / "data/solar.csv").relative_to(ROOT.parents[1])),
        "data_sha256": hashlib.sha256((ROOT / "data/solar.csv").read_bytes()).hexdigest(),
        "columns": columns,
        "temperature_screen_c": [-100, 200],
        "invalid_module_temperature_rows": int(invalid.sum()),
        "module_temperature_status": "unavailable" if invalid.all() else "requires_review",
        "decision": "Withdraw measured module-temperature RMSE/ranking and observed-intermediate-truth claims. Preserve frozen AC-power experiments; no rows, targets or splits changed.",
        "limits": "Screening plausible ranges does not certify other sensors. The exact encoding of the unusable temperature value is not established.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("QA output already exists")
    write_json(args.output, quality())
