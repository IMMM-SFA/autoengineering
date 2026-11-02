"""Bind the consolidated task definitions without reading confirmation values.

These TaskSpecs are preparation records, not dispatch grants. Qualification
reports missing execution contracts explicitly instead of promoting metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from autoengineering.campaign.serialization import digest
from autoengineering.utility.contracts import TaskSpec

DIRECTORY = Path("examples/utility/consolidated")


def read(root, name):
    return json.loads((root / name).read_text())


def file_binding(root, name):
    path = root / name
    return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def definitions(root):
    solar = read(root, "examples/utility/development/solar-mapping-v1/alternative_refined.json")
    return {
        "hydrology": {
            "site": {"gauge": "01491000", "latitude_deg": 38.97, "area_km2": 292.543553},
            "callable": "examples.utility.hydrology_site:SiteHydrologyAdapter",
            "sources": [
                "examples/utility/hydrology_site.py",
                "examples/utility/hydrology_camels.py",
                "examples/utility/hydrology_camels_archive.py",
            ],
            "evidence": [
                "examples/utility/verification-camels-acquisition-v1/inspection-v2/source.json",
                "examples/utility/verification-camels-acquisition-v1/inspection-v2/inspection-result.json",
            ],
            "partition": {
                "warmup": ["1980-01-01", "1980-12-31"],
                "fit": ["1981-01-01", "1999-12-31"],
                "selection": ["2000-01-01", "2004-12-31"],
                "confirmation": ["2005-01-01", "2014-12-31"],
                "clock": "same published date; no shift or fill",
                "quality": "A only",
                "state": "causal carryover from warmup; initial soil half capacity, reservoir zero",
            },
            "baseline": {"capacity": 100.0, "recession": 0.7, "pet": "hamon"},
            "candidates": [
                {"pet": pet, "capacity_bounds": [20, 200], "recession_bounds": [0.05, 0.95]}
                for pet in ("hamon", "hargreaves")
            ],
            "outcome": {
                "metric": "discharge_rmse",
                "units": "mm/day",
                "direction": "minimize",
                "gain_fraction_of_development_baseline": 0.05,
                "secondary": {
                    "absolute_volume_bias_max": 0.10,
                    "bias_degradation_max": 0.02,
                    "nonnegative_stores": True,
                    "daily_balance": True,
                },
            },
            "claim": "Published-date discharge benchmark; no resolved physical interval claim",
        },
        "solar": {
            "site": {"system_id": 1278, "dc_kw": 171.36, "ac_kw": 150},
            "callable": "examples.utility.solar_1278_development:predict",
            "sources": ["examples/utility/solar_1278_development.py"],
            "evidence": [
                "examples/utility/development/solar-mapping-v1/decision.json",
                "examples/utility/development/solar-mapping-v1/1278_metadata.json",
                "examples/utility/development/solar-mapping-v1/alternative_refined.json",
            ],
            "partition": {
                "fit": ["2011-10-01", "2011-10-07"],
                "selection": ["2011-10-08", "2011-10-14"],
                "confirmation": ["2013-01-01", "2013-12-31"],
                "clock": "shared source clock; no fitted shift; duplicate timestamps excluded",
                "quality": "POA 100..1400 W/m2, ambient -20..60 C, wind 0..40 m/s, AC -0.5..157.5 kW",
                "aggregation": "equal-weight power samples; no integrated energy claim",
            },
            "baseline": {"scale": solar["scale"], "thermal": "faiman", "gamma": -0.004},
            "candidates": [{"scale_bounds": [0.5, 1.05], "thermal": "faiman", "gamma": -0.004}],
            "outcome": {
                "metric": "ac_rmse",
                "units": "kW",
                "direction": "minimize",
                "gain_fraction_of_development_baseline": 0.05,
                "development_reference": solar["metrics"]["check"]["rmse_kw"],
                "secondary": {
                    "absolute_power_sum_bias_max": 0.10,
                    "power_sum_bias_degradation_max": 0.01,
                },
            },
            "claim": "Conditional daytime AC reconstruction; effective derating, not identified losses",
        },
        "engineering": {
            "site": {"model": "coupled-circuit-v3"},
            "callable": "examples.utility.engineering_load:LoadCircuitAdapter",
            "sources": [
                "examples/utility/engineering_load.py",
                "examples/utility/engineering_scenarios.py",
                "examples/utility/engineering_source_binding.py",
                "examples/utility/engineering_load_scoring.py",
            ],
            "evidence": [],
            "partition": {
                "confirmation": "new private draw of 24 uniform cases before selection",
                "bounds": {
                    "ground_voltage": [-0.02, 0.02],
                    "resistor1_ohm": [90, 110],
                    "resistor2_ohm": [9000, 11000],
                },
                "sampler": "hmac-sha256-52bit-v1",
                "development_draw_reuse": False,
            },
            "baseline": {"source_current": 0.05},
            "candidates": [{"source_current_bounds": [0.01, 0.1]}],
            "outcome": {
                "metric": "mean_source_power",
                "units": "W",
                "direction": "minimize",
                "gain_fraction_of_development_baseline": 0.05,
                "secondary": {
                    "node2_voltage_min_V": 0.62,
                    "residual_max_A": 1e-10,
                    "worst_case_power_degradation_max": 0.01,
                    "all_cases": True,
                },
            },
            "claim": "Modeled performance on declared operating scenarios",
        },
        "wind": {
            "site": {"latitude": 41.5, "longitude": -70.5, "height_m": 80, "turbines": 4},
            "callable": "examples.utility.wind_common_confirmation:CommonConfirmationWindScorer",
            "sources": [
                "examples/utility/wind_common_confirmation.py",
                "examples/utility/wind_annual_callback.py",
                "examples/utility/wind_annual_source.py",
                "examples/utility/wind_annual_scoring.py",
                "examples/utility/wind_reserve_extract.py",
            ],
            "evidence": ["examples/utility/wind-reserve-preparation.json"],
            "partition": {
                "fit_years": [2007, 2009],
                "selection_years": [2010, 2011],
                "confirmation_years": [2012, 2013, 2014],
                "clock": "complete hourly UTC",
                "versions": {"2012": "v1.0.0", "2013": "v1.0.0", "2014": "v1.1.0"},
                "direction": "meteorological from, clockwise from north",
            },
            "baseline": {
                "layout_m": [[0, 0], [600, 0], [0, 600], [600, 600]],
                "hardware": "V80",
                "wake_model": "NOJ",
            },
            "candidates": [
                {
                    "layout_box_m": [0, 600],
                    "minimum_spacing_m": 320,
                    "hardware": "V80",
                    "wake_model": "NOJ",
                }
            ],
            "outcome": {
                "metric": "mean_annual_energy",
                "units": "GWh",
                "direction": "maximize",
                "gain_fraction_of_development_baseline": 0.01,
                "secondary": {"annual_degradation_max": 0.02, "minimum_spacing_m": 320},
            },
            "claim": "Modeled annual energy; each year retained including the 2014 version boundary",
        },
    }


def build(root):
    exposure = read(root, str(DIRECTORY / "exposure.json"))
    if exposure["solar"]["personal_prior_use"] != "none_attested":
        raise ValueError("Solar prior use is not cleared")
    result = {}
    for name, task in definitions(root).items():
        task["source_bindings"] = [file_binding(root, p) for p in task.pop("sources")]
        task["evidence_bindings"] = [file_binding(root, p) for p in task.pop("evidence")]
        task["environment_binding"] = file_binding(root, "pixi.lock")
        task["exposure_binding"] = file_binding(root, str(DIRECTORY / "exposure.json"))
        spec = TaskSpec(
            name,
            name,
            digest(task),
            digest(task["partition"]),
            digest(task["outcome"]),
            tuple(
                digest({"candidate": c, "sources": task["source_bindings"]})
                for c in task["candidates"]
            ),
            (),
        )
        result[name] = {
            "definition": task,
            "task_spec": spec.to_dict(),
            "task_digest": spec.digest,
            "dispatchable": False,
        }
    return {
        "schema": "utility-consolidated-task-bindings-v1",
        "tasks": result,
        "scope": "Concrete source, model, candidate, partition and outcome definitions; not runtime grants",
        "solar_policy_amendment": "Equal-weight power bias replaces unqualified energy bias; 10 percent absolute limit follows the recorded replacement development screen",
        "uncertainty_policy": "Report every paired repetition and annual/scenario stratum; no pooled independent-time confidence intervals or equivalence claims",
        "execution_allowed": False,
    }


def verify(root, bundle):
    """Reject stale definitions or source hashes before using a task identity."""
    if bundle != build(root):
        raise ValueError("Consolidated bindings differ from current sources or definitions")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    path = args.root / DIRECTORY / "task-bindings.json"
    path.write_text(json.dumps(build(args.root), indent=2) + "\n")
    print(f"Bound four task definitions: {path}")


if __name__ == "__main__":
    main()
