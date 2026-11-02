"""Preserve bounded development parity evidence on exposed prediction tasks."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from examples.utility import hydrology, solar


def run(output, cache):
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    sources = [Path(__file__), Path(hydrology.__file__), Path(solar.__file__)]
    manifest = {"purpose": "previously exposed development; not confirmation",
                "sources": {str(p.relative_to(hydrology.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sources}, "physical_start_cap": 10}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    records = []

    def save(record):
        records.append(record)
        (output / f"case-{len(records):02d}.json").write_text(json.dumps(record, indent=2) + "\n")
        print(f"Completed development case {len(records)}/5: {record['task']} {record['candidate']}")

    from examples.local_models.kernels import hydro_model
    data = hydrology.development_data()
    inputs = hydrology.forcing(data)
    for family in ("hamon", "hargreaves"):
        before = time.perf_counter()
        params = hydrology.BASELINE | {"pet": family}
        ctx = hydrology.context(data, params, output)
        direct = hydro_model(data, params)
        wrapped = run_lifecycle(hydrology.adapter(), ctx, inputs, ctx.model.inputs, ctx.model.outputs)
        for name in ("prediction", "soil", "aet", "pet"):
            np.testing.assert_allclose(wrapped.outputs[name], direct[name], rtol=1e-12, atol=1e-12)
        checks = hydrology.physical_checks(wrapped.outputs, inputs, params)
        mask = (data.split == "validation").to_numpy()
        error = wrapped.outputs["prediction"][mask] - data.flow_mm_day.to_numpy()[mask]
        save({"task": "hydrology", "candidate": family, "physical_starts": 2,
              "context": ctx.to_dict(), "parity": "passed", "checks": [c.to_dict() for c in checks],
              "scored_rows": int(mask.sum()), "rmse_mm_day": float(np.sqrt(np.mean(error**2))),
              "seconds": time.perf_counter() - before})
    from examples.interoperability.solar.fixture import BASELINE, forcing
    from examples.interoperability.solar.model import physical
    data, inventory = solar.load_development(cache)
    (output / "solar-acquisition.json").write_text(json.dumps(inventory, indent=2) + "\n")
    inputs = forcing(data)
    for method in ("faiman_prilliman", "faiman", "sapm_module"):
        before = time.perf_counter()
        params = BASELINE | {"method": method}
        ctx = solar.context(data, params, output)
        direct = physical(inputs, params)
        wrapped = run_lifecycle(solar.adapter(), ctx, inputs, ctx.model.inputs, ctx.model.outputs)
        for name in direct:
            np.testing.assert_allclose(wrapped.outputs[name], direct[name], rtol=1e-10, atol=1e-8)
        checks = solar.physical_checks(wrapped.outputs, inputs, params)
        save({"task": "solar", "candidate": method, "physical_starts": 2,
              "context": ctx.to_dict(), "parity": "passed", "checks": [c.to_dict() for c in checks],
              "loss": solar.primary_loss(data, wrapped.outputs),
              "seconds": time.perf_counter() - before})
    summary = {"status": "development_rehearsal", "physical_starts": sum(
        r["physical_starts"] for r in records), "cases": len(records),
        "all_physical_checks_pass": all(c["status"] == "pass" for r in records for c in r["checks"]),
        "utility_verdict": "not_attempted", "confirmation": "not_attempted",
        "learned_hydrology": hydrology.learned_candidate_admission()}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--solar-cache", type=Path, required=True)
    args = parser.parse_args()
    run(args.output, args.solar_cache)
