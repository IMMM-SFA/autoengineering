"""Annual WIND comparison metadata, without source access or model execution.

Keep every proposed year and expose the 2014 source-version boundary. These
records bind producer claims, not rights, exposure, runtime or task admission.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
import math
from typing import Literal

from autoengineering.campaign.serialization import Record
from autoengineering.utility.contracts import sha256


@dataclass(frozen=True)
class AnnualWindSource(Record):
    year: int
    source_version: Literal["v1.0.0", "v1.1.0"]
    object_key: str
    object_identity_digest: str
    point_manifest_digest: str

    def _validate(self):
        if type(self.year) is not int or not 2007 <= self.year <= 2014:
            raise ValueError("annual WIND source requires a 2007-2014 year")
        version = "v1.1.0" if self.year == 2014 else "v1.0.0"
        if self.source_version != version or self.object_key != (
            f"conus/{version}/wtk_conus_{self.year}.h5"
        ):
            raise ValueError("annual WIND object and source version differ")
        sha256(self.object_identity_digest)
        sha256(self.point_manifest_digest)


@dataclass(frozen=True)
class AnnualWindPlan(Record):
    schema: Literal["utility-wind-annual-plan-v1"]
    sources: tuple[AnnualWindSource, ...]
    model_digest: str
    geometry_digest: str
    interpretation_digest: str

    def _validate(self):
        years = tuple(source.year for source in self.sources)
        if not years or years != tuple(sorted(set(years))):
            raise ValueError("annual WIND plan needs unique chronological years")
        for value in (self.model_digest, self.geometry_digest, self.interpretation_digest):
            sha256(value)


@dataclass(frozen=True)
class AnnualWindResult(Record):
    year: int
    source_digest: str
    status: Literal[
        "success", "scientific_infeasible", "model_failure", "timeout", "infrastructure_failure"
    ]
    energy_gwh: float | None

    def _validate(self):
        if type(self.year) is not int or not 2007 <= self.year <= 2014:
            raise ValueError("annual WIND result year differs from the source profile")
        sha256(self.source_digest)
        if self.status == "success":
            hours = (366 if calendar.isleap(self.year) else 365) * 24
            maximum = 4 * 2e6 * hours / 1e9
            if (
                type(self.energy_gwh) not in (int, float)
                or not math.isfinite(self.energy_gwh)
                or not 0 <= self.energy_gwh <= maximum * (1 + 1e-10)
            ):
                raise ValueError("annual WIND energy exceeds the four-V80 physical profile")
        elif self.energy_gwh is not None:
            raise ValueError("unsuccessful annual WIND result cannot supply an energy value")


@dataclass(frozen=True)
class AnnualWindRun(Record):
    schema: Literal["utility-wind-annual-run-v1"]
    plan_digest: str
    configuration_digest: str
    results: tuple[AnnualWindResult, ...]

    def _validate(self):
        sha256(self.plan_digest)
        sha256(self.configuration_digest)
        years = tuple(result.year for result in self.results)
        if not years or years != tuple(sorted(set(years))):
            raise ValueError("annual WIND run needs unique chronological results")


def _bound_results(plan: AnnualWindPlan, run: AnnualWindRun):
    if run.plan_digest != plan.digest or tuple(result.year for result in run.results) != tuple(
        source.year for source in plan.sources
    ):
        raise ValueError("annual WIND run changed its plan or omitted a declared year")
    for source, result in zip(plan.sources, run.results, strict=True):
        if result.source_digest != source.digest:
            raise ValueError("annual WIND run changed a year's source identity")
    return run.results


def compare_annual(
    plan: AnnualWindPlan,
    conventional: AnnualWindRun,
    candidate: AnnualWindRun,
    *,
    maximum_yearly_degradation: float,
):
    """Pair producer metadata by exact source and retain all unsuccessful years.

    Call only inside the trusted scoring/report boundary. This function does not
    enforce confirmation access, qualify receipts or decide useful improvement.
    """
    if (
        type(maximum_yearly_degradation) not in (int, float)
        or not math.isfinite(maximum_yearly_degradation)
        or not 0 <= maximum_yearly_degradation < 1
    ):
        raise ValueError("annual WIND comparison requires an explicit fractional tolerance")
    reference = _bound_results(plan, conventional)
    proposed = _bound_results(plan, candidate)
    rows = []
    for source, baseline, result in zip(plan.sources, reference, proposed, strict=True):
        complete = baseline.status == result.status == "success"
        rows.append(
            {
                "year": source.year,
                "source_version": source.source_version,
                "source_digest": source.digest,
                "conventional_status": baseline.status,
                "candidate_status": result.status,
                "conventional_energy_gwh": baseline.energy_gwh,
                "candidate_energy_gwh": result.energy_gwh,
                "gain_gwh": result.energy_gwh - baseline.energy_gwh if complete else None,
                "degradation_passed": (
                    result.energy_gwh >= (1 - maximum_yearly_degradation) * baseline.energy_gwh
                    if complete
                    else False
                ),
            }
        )

    def summary(items):
        complete = all(row["gain_gwh"] is not None for row in items)
        return {
            "years": [row["year"] for row in items],
            "complete": complete,
            "conventional_mean_annual_energy_gwh": (
                math.fsum(row["conventional_energy_gwh"] for row in items) / len(items)
                if complete
                else None
            ),
            "candidate_mean_annual_energy_gwh": (
                math.fsum(row["candidate_energy_gwh"] for row in items) / len(items)
                if complete
                else None
            ),
            "mean_gain_gwh": (
                math.fsum(row["gain_gwh"] for row in items) / len(items) if complete else None
            ),
            "all_years_degradation_passed": all(row["degradation_passed"] for row in items),
        }

    return {
        "schema": "utility-wind-annual-comparison-v1",
        "plan_digest": plan.digest,
        "conventional_run_digest": conventional.digest,
        "candidate_run_digest": candidate.digest,
        "units": "GWh",
        "weighting": "equal-year, including leap years at their actual duration",
        "maximum_yearly_degradation": maximum_yearly_degradation,
        "annual": rows,
        "overall": summary(rows),
        "by_source_version": {
            version: summary([row for row in rows if row["source_version"] == version])
            for version in sorted({row["source_version"] for row in rows})
        },
        "claim": "Modeled energy across declared weather and generator-version scenarios",
        "useful_improvement_decided": False,
        "task_admitted": False,
    }
