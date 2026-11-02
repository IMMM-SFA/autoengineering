"""Compute the CAMELS development reference and bind existing development receipts."""

from __future__ import annotations

import json
import math
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from examples.utility.consolidated_sources import DEFAULT, sha, save
from examples.utility.hydrology import BASELINE, physical_checks
from examples.utility.hydrology_partitions import DailyHydrologyPlan
from examples.utility.hydrology_site import SiteHydrologyAdapter, prepared_development


def main():
    output = DEFAULT / "baselines"
    output.mkdir(mode=0o700, exist_ok=False)
    started = time.monotonic()
    hydro = DEFAULT / "hydrology"
    plan = DailyHydrologyPlan.from_json((hydro / "plan.json").read_text())
    forcing = json.loads((hydro / "development/forcing.json").read_text())
    labels = json.loads((hydro / "development/selection.json").read_text())
    site, ctx, arrays = prepared_development(plan, forcing, BASELINE, output, role="selection")
    save(
        output / "hydrology-intent.json",
        {
            "model": ctx.model.digest,
            "model_calls_reserved": 1,
            "forcing_sha256": sha(hydro / "development/forcing.json"),
            "labels_sha256": sha(hydro / "development/selection.json"),
        },
    )
    result = run_lifecycle(
        SiteHydrologyAdapter(site), ctx, arrays, ctx.model.inputs, ctx.model.outputs
    )
    checks = physical_checks(result.outputs, arrays, BASELINE)
    if any(c.status != "pass" for c in checks):
        raise ValueError("Hydrology reference failed physical checks")
    mask = np.asarray(labels["mask"], dtype=bool)
    p, y = result.outputs["prediction"][mask], np.asarray(labels["labels"])[mask]
    references = {
        "hydrology": {
            "value": float(np.sqrt(np.mean((p - y) ** 2))),
            "units": "mm/day",
            "fraction": 0.05,
            "rows": int(mask.sum()),
            "model_digest": ctx.model.digest,
            "new_model_calls": 1,
            "volume_bias": float(p.sum() / y.sum() - 1),
        }
    }
    # Reuse completed original results, verifying their recorded artifact hashes.
    engineering = Path("outputs/engineering-envelope-supervised-v1")
    summary = json.loads((engineering / "summary.json").read_text())
    for ref in [summary["receipt"], *summary["records"]["evaluations"]]:
        read_bytes(engineering / "batch", ArtifactRef.from_dict(ref))
    references["engineering"] = {
        "value": summary["baseline_power_W"],
        "units": "W",
        "fraction": 0.05,
        "receipt_sha256": sha(engineering / "summary.json"),
        "new_model_calls": 0,
        "reuse": "verified development receipt",
    }
    wind = Path("outputs/wind-hourly-study-v2/baseline.json")
    original = json.loads(wind.read_text())
    if original["evaluation"]["status"] != "success" or any(
        c["status"] != "pass" for c in original["evaluation"]["checks"]
    ):
        raise ValueError("Wind baseline receipt is not successful and feasible")
    references["wind"] = {
        "value": original["evaluation"]["metrics"]["annual_energy"],
        "units": "GWh",
        "fraction": 0.01,
        "receipt_sha256": sha(wind),
        "new_model_calls": 0,
        "reference_period": "2007 development",
    }
    solar = Path("examples/utility/development/solar-mapping-v1/alternative_refined.json")
    original = json.loads(solar.read_text())
    references["solar"] = {
        "value": original["metrics"]["check"]["rmse_kw"],
        "units": "kW",
        "fraction": 0.05,
        "receipt_sha256": sha(solar),
        "new_model_calls": 0,
        "reference_period": "2011-10-08 through 2011-10-14 reused development",
    }
    for reference in references.values():
        if not math.isfinite(reference["value"]) or reference["value"] <= 0:
            raise ValueError("Development reference must be finite and positive")
        reference["absolute_gain"] = reference["fraction"] * reference["value"]
    save(
        output / "complete.json",
        {
            "references": references,
            "elapsed_seconds": time.monotonic() - started,
            "confirmation_calls": 0,
        },
    )
    print(json.dumps({"status": "development_references_bound", "references": references}))


if __name__ == "__main__":
    main()
