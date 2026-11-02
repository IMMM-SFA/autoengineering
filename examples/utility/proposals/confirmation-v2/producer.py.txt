"""Prepare the existing four-task proposal without observations or execution.

Proposed relative gains become absolute only against explicit positive development
baseline references. Reference binding is not receipt qualification or admission.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import product
import hashlib
import math
from pathlib import Path
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, digest
from autoengineering.campaign.store import durable_write
from autoengineering.utility.contracts import sha256

PROPOSAL = "docs/reviews/part-5-confirmation-proposal.md"
PUBLIC_METADATA = (
    "examples/utility/proposals/confirmation-v1/metadata-evidence.json",
    "examples/utility/proposals/confirmation-v1/rights-access-evidence.json",
)
RULES = {
    "hydrology": ("discharge_rmse", "mm/day", "minimize", 0.05),
    "solar": ("ac_rmse", "kW", "minimize", 0.05),
    "engineering": ("mean_source_power", "W", "minimize", 0.05),
    "wind": ("mean_annual_energy", "GWh", "maximize", 0.01),
}


@dataclass(frozen=True)
class DevelopmentReference(Record):
    schema: Literal["utility-proposal-development-reference-v1"]
    task_id: Literal["hydrology", "solar", "engineering", "wind"]
    phase: Literal["development"]
    route: Literal["unchanged_baseline"]
    metric_id: str
    units: Literal["mm/day", "kW", "W", "GWh"]
    value: float
    baseline_model_digest: str
    input_manifest_digest: str
    execution_receipt_digest: str

    def _validate(self):
        metric, units, _, _ = RULES[self.task_id]
        if (self.metric_id, self.units) != (metric, units):
            raise ValueError("development reference metric or units differ from the proposed task")
        if type(self.value) not in (int, float) or not math.isfinite(self.value) or self.value <= 0:
            raise ValueError("development baseline reference must be finite and positive")
        for value in (
            self.baseline_model_digest,
            self.input_manifest_digest,
            self.execution_receipt_digest,
        ):
            sha256(value)


def bind_reference(root, artifact: ArtifactRef):
    """Bind claimed development provenance; never inspect labels or execute models.

    The returned artifact still requires authoritative receipt and task review.
    Its source hash prevents silently replacing the reference after confirmation.
    """
    ref = DevelopmentReference.from_json(read_bytes(root, artifact, max_bytes=65536).decode())
    metric, units, direction, fraction = RULES[ref.task_id]
    absolute = fraction * ref.value
    if not math.isfinite(absolute) or absolute <= 0:
        raise ValueError("absolute useful gain is not finite and positive")
    return {
        "schema": "utility-proposed-absolute-gain-v1",
        "status": "reference_bound_not_admitted",
        "task_id": ref.task_id,
        "metric_id": metric,
        "units": units,
        "direction": direction,
        "development_reference": artifact.to_dict(),
        "reference_identity": ref.digest,
        "policy_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "reference_value": ref.value,
        "fraction": fraction,
        "absolute_gain": absolute,
        "receipt_qualification": "required; metadata declaration alone does not prove the numeric reference",
        "starts_authorized": False,
    }


def engineering_scenarios():
    """Exactly the proposed 24 authored cases, excluding the three nominal loads."""
    return [
        {
            "scenario_id": f"load-{i:02d}",
            "weight": 1 / 24,
            "forcing": {"ground_voltage": ground, "resistor1_ohm": r1, "resistor2_ohm": r2},
        }
        for i, (ground, r1, r2) in enumerate(
            (
                values
                for values in product(
                    (-0.05, 0.0, 0.05), (95.0, 100.0, 105.0), (9500.0, 10000.0, 10500.0)
                )
                if values[1:] != (100.0, 10000.0)
            ),
            1,
        )
    ]


def task_choices():
    return {
        "hydrology": {
            "source": "CAMELS",
            "basin": "01491000",
            "forcing_product": "Daymet",
            "warmup_years": [1980, 1980],
            "fitting_years": [1981, 1999],
            "selection_years": [2000, 2004],
            "reserved_years": [2005, 2014],
            "secondary_policy": {
                "absolute_volume_bias_fraction_max": 0.10,
                "volume_bias_degradation_percentage_points_max": 2.0,
                "nonnegative_stores_required": True,
                "daily_water_balance_required": True,
            },
            "blockers": [
                "source registration/access condition",
                "daily interval and quality semantics",
                "coverage and exposure review",
                "development support for learned candidate",
                "qualified protected inference/scoring",
            ],
        },
        "solar": {
            "source": "PVDAQ",
            "site_id": 2107,
            "inverter": 1,
            "fitting_years": [2019, 2020],
            "selection_years": [2021, 2021],
            "reserved_years": [2022, 2022],
            "question": "conditional AC reconstruction with measured contemporaneous POA",
            "equipment_policy": "site 2107 metadata; never inherit site 9068 equipment",
            "secondary_policy": {
                "absolute_daytime_energy_bias_fraction_max": 0.05,
                "energy_bias_degradation_percentage_points_max": 1.0,
                "qualified_interval_integration_required": True,
                "equipment_specific_nighttime_and_ac_limits_required": True,
            },
            "blockers": [
                "mixed interval and timestamp convention",
                "equipment/channel binding and conversions",
                "quality masks and causal initialization",
                "coverage/exposure/source rights review",
                "qualified protected inference/scoring",
            ],
        },
        "engineering": {
            "source": "authored load scenarios under the coupled OpenMDAO circuit",
            "design_variable": "source_current",
            "supported_current_A": [0.01, 0.1],
            "final_domain_frozen": False,
            "reserved_scenarios": engineering_scenarios(),
            "scenario_units": {
                "ground_voltage": "V",
                "resistor1_ohm": "ohm",
                "resistor2_ohm": "ohm",
            },
            "secondary_policy": {
                "node_2_voltage_external_reference_min_V": 0.62,
                "constitutive_residual_max_A": 1e-10,
                "all_24_cases_must_pass": True,
                "worst_case_power_degradation_fraction_max": 0.01,
            },
            "blockers": [
                "scenario exposure review without evaluating reserved cases",
                "final design domain and native work caps",
                "qualified protected scenario scoring",
            ],
        },
        "wind": {
            "source": "WIND Toolkit CONUS",
            "longitude": -70.5,
            "latitude": 41.5,
            "development_years": [2007, 2009],
            "selection_years": [2010, 2011],
            "reserved_years": [2012, 2014],
            "hub_height_m": 80,
            "turbines": 4,
            "turbine_curve": "V80",
            "secondary_policy": {
                "geometry_and_spacing_required": True,
                "per_year_energy_degradation_fraction_max": 0.02,
            },
            "blockers": [
                "bounded anonymous point extraction",
                "grid/height/time semantics",
                "2014 source-version comparability",
                "hardware/resource binding and geometry",
                "coverage/exposure/rights review",
                "qualified protected scenario scoring",
            ],
        },
    }


def build(source_root):
    source_root = Path(source_root)
    paths = (PROPOSAL, *PUBLIC_METADATA, *(f"examples/utility/tasks/{name}.json" for name in RULES))
    refs = [
        reference(
            source_root,
            name,
            media_type="text/plain" if name.endswith(".md") else "application/json",
            producer="confirmation-proposal-source",
        )
        for name in paths
    ]
    tasks = task_choices()
    for name, task in tasks.items():
        metric, units, direction, fraction = RULES[name]
        task.update(
            task_id=name,
            status="proposed_not_admitted",
            exposure="unknown_exposure",
            primary={"metric_id": metric, "units": units, "direction": direction},
            useful_gain_policy={
                "fraction_of_fixed_development_baseline": fraction,
                "reference_route": "unchanged_baseline",
                "reference_phase": "development",
                "numeric_reference": None,
                "absolute_gain": None,
                "freeze_before_confirmation": True,
            },
        )
    result = {
        "schema": "utility-four-task-confirmation-choices-v2",
        "status": "proposed_not_admitted",
        "tasks": tasks,
        "sources": [ref.to_dict() for ref in refs],
        "producer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "decision_status": "existing proposed study judgments; not task-owner numeric declarations or confirmation-derived thresholds",
        "analysis_policy": {
            "confidence": 0.95,
            "familywise_contrasts": 48,
            "multiplicity": "bonferroni",
            "all_assigned_repetitions_feasible_required": True,
            "time_or_scenario_dependence_method": None,
            "frozen": False,
        },
        "planning_matrix": {
            "tasks": 4,
            "paired_repetitions": 10,
            "budget_regimes": 2,
            "routes": 7,
            "logical_cells": 560,
            "adaptive_cells": 480,
            "numeric_budgets": None,
            "frozen": False,
        },
        "custody": "trusted preparation and scoring code separated from advisory workers; a separate person or pre-existing private dataset is not required",
        "reference_rule": "compute unchanged-baseline reference once on admitted development data; invalid or zero references block; never derive margins from confirmation performance",
        "claim_limits": [
            "public source proposals do not prove rights, coverage or untouched evidence",
            "engineering and wind outcomes are modeled quantities, not empirical validation",
            "reference binding is not authoritative receipt qualification",
            "scenario construction runs no engineering solve",
            "G1-G8 remain open where their evidence is missing",
        ],
        "starts_authorized": False,
        "observations_accessed": False,
        "protocol_frozen": False,
    }
    return result


def write(source_root, output):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("proposal output must be absent; preserve preceding proposals")
    result = build(source_root)
    output.mkdir(mode=0o700)
    durable_write(output / "proposal.json", canonical_json(result).encode())
    durable_write(output / "producer.py.txt", Path(__file__).read_bytes())
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("source_root", type=Path)
    prep.add_argument("output", type=Path)
    bind = sub.add_parser("bind-reference")
    bind.add_argument("root", type=Path)
    bind.add_argument("artifact", type=Path)
    a = p.parse_args()
    if a.command == "prepare":
        result = write(a.source_root, a.output)
    else:
        result = bind_reference(a.root, ArtifactRef.from_json(a.artifact.read_text()))
    print(canonical_json({"digest": digest(result), "schema": result["schema"]}))


if __name__ == "__main__":
    main()
