"""Generate the local BMI example comparison from recorded results and provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import median


def summarize(directory: Path, output: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    manifest = json.loads((directory / "manifest.json").read_text())
    mismatches = [
        name
        for name, digest in manifest["inputs"].items()
        if hashlib.sha256((repo / name).read_bytes()).hexdigest() != digest
    ]
    if mismatches:
        raise ValueError(f"Input/source hashes changed: {mismatches}")
    evidence = json.loads((directory / "results.json").read_text())
    rows = evidence["runs"]
    expected = {
        (d, m, s)
        for d in manifest["domains"]
        for m in manifest["methods"]
        for s in manifest["seeds"]
    }
    actual = {(r["domain"], r["method"], r["seed"]) for r in rows}
    if expected != actual or len(rows) != len(expected):
        raise ValueError("The comparison matrix is incomplete or contains duplicates")
    raw_count = 0
    for row in rows:
        stem = f"{row['domain']}-{row['method']}-{row['seed']}"
        study = directory / stem
        study_manifest = json.loads((study / "application-result.json").read_text())
        if study_manifest != row:
            raise ValueError(f"Summary differs from study: {stem}")
        records = (study / "observations.jsonl").read_text().splitlines()
        if len(records) != manifest["evaluations"]:
            raise ValueError(f"Incorrect ledger length: {stem}")
        raw_count += len(records)
    probe = json.loads((directory.parent / "bmi-component-probe/result.json").read_text())
    closure = json.loads((directory.parent / "bmi-scalar-closure.json").read_text())
    lines = [
        "# BMI example development results",
        "",
        f"All {len(rows)} studies completed, with {raw_count} recorded model evaluations. "
        f"Recorded study time totaled {sum(r['study_seconds'] for r in rows):.1f} seconds.",
        "",
        "Each optimizer used 12 model calls and seeds 0, 1 and 2. The table gives held-out RMSE. "
        "Optimizer columns are medians across seeds. Lower is better. "
        "Fixed swaps were selected on validation data and used a separate small candidate budget.",
        "",
        "| Domain | Unit | Initial model | Selected fixed swap | Random | Sobol | BO |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    units = {"hydro": "mm/day", "solar": "kW", "copper": "native source units"}
    for workflow in evidence["workflows"]:
        domain = workflow["domain"]
        baseline = workflow["candidates"][0]["test"]["rmse"]
        fixed = workflow["candidates"][workflow["selected_index"]]["test"]["rmse"]
        values = [
            median(
                r["test"]["rmse"] for r in rows if r["domain"] == domain and r["method"] == method
            )
            for method in ["random", "sobol", "bo"]
        ]
        lines.append(
            f"| {domain} | {units[domain]} | {baseline:.4f} | {fixed:.4f} | "
            + " | ".join(f"{value:.4f}" for value in values)
            + " |"
        )
    lines += [
        "",
        "Model swaps and parameter search improve the initial examples, but BO does not "
        "beat the strongest random/Sobol median in any of these three small comparisons. "
        "Three seeds and short validation/test windows do not establish general method rankings.",
        "",
        "| Domain | Method | Seed | Validation RMSE | Test RMSE | Model seconds | Study seconds |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['domain']} | {row['method']} | {row['seed']} | "
            f"{row['recommendation']['outcomes']['rmse']:.6f} | {row['test']['rmse']:.6f} | "
            f"{row['model_seconds']:.4f} | {row['study_seconds']:.4f} |"
        )
    lines += [
        "",
        "Study time includes optimizer and durable controller overhead. Model time measures "
        "the BMI chain inside evaluator calls. Held-out evaluation, imports and fixed-swap workflow "
        "time outside the study are not included in those study totals.",
        "",
        "## BMI and component reuse",
        "",
        "Eight components implement the Python BMI interface. The graph driver checks scalar grids, "
        "float64 variables, unit matching, complete input wiring and common clocks. Water components "
        "retain daily storage. Steady-state models advance by independent sample index.",
        "",
        f"Saved solar temperature traces reproduce downstream power exactly: "
        f"`{probe['reused_power_matches_full']}`. Median repeated BMI component timings were "
        f"{probe['temperature_seconds'] * 1000:.3f} ms for temperature, "
        f"{probe['power_seconds'] * 1000:.3f} ms for DC plus inverter, and "
        f"{probe['full_seconds'] * 1000:.3f} ms for the complete solar chain.",
        "",
        "## Partial observation status",
        "",
        "Application partial BO is **not implemented or evaluated** in this suite. "
        "The earlier frozen partial-BO gate remains failed.",
        "",
        "The arbitrary trace-reversal probe demonstrates general information loss, but does not "
        "prove that the registered Ross family lacks a sufficient scalar summary. With fixed "
        "irradiance and air temperature, mean module temperature identifies the Ross coefficient "
        "and reconstructs the attainable temperature trace.",
        "",
        f"The registered-family check reconstructed AC outputs with a maximum difference of "
        f"{max(c['ac_power_max_error_kw'] for c in closure['temperature_summary_checks']):.3g} kW. "
        f"Two attainable configurations with equal mean DC power differed in mean AC power by "
        f"{closure['attainable_dc_counterexample']['ac_mean_difference_kw']:.6f} kW. "
        "Thus the separate DC-to-inverter boundary cannot be summarized exactly by mean DC alone.",
        "",
        "A temperature component followed by a combined DC/inverter component is a candidate "
        "function-network representation for a later comparison. Its cost benefit remains untested; "
        "these models are cheap enough that optimizer overhead may outweigh saved model work.",
        "",
        "## Evidence and limits",
        "",
        "The complete BMI matrix is in `bmi-development/`. `bmi-component-probe/` and "
        "`bmi-scalar-closure.json` retain component evidence. Preliminary direct-adapter results "
        "remain in `pre-bmi-development/`; the decoder failure is preserved in "
        "`interrupted-boundary/`. Neither preliminary directory is pooled with the BMI matrix.",
        "",
        "The final BMI source/input hashes were verified when generating this document. Earlier "
        "preliminary runs retain hashes and records but not a complete separate source archive. "
        "Their role is development history, not the reproducible final comparison.",
        "",
        "Hydrology uses a legacy observation cache without original API quality flags. Solar uses "
        "one short winter window and an assumed equal DC allocation between inverters. Copper "
        "retains an unresolved output-unit multiplier and includes two endpoint extrapolations. "
        "See `../README.md` and `../PROTOCOL.md` for source and scientific limitations.",
        "",
    ]
    output.write_text("\n".join(lines))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summarize(args.directory, args.output)
