"""Fixed annual wind kernel for application-owned trusted execution.

No source access, optimization, fitting, admission or OS isolation is provided.
The caller must enforce the suite barrier and authorize private drivers before
supplying them. Outputs never contain weather, model exceptions or power arrays.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import math
from pathlib import Path
from typing import Literal

import numpy as np

from autoengineering.campaign.serialization import Record, canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.contracts import sha256
from autoengineering.utility.scoring import PublicScore
from examples.utility import wind_hourly
from examples.utility.wind_annual import (
    AnnualWindPlan,
    AnnualWindResult,
    AnnualWindRun,
)
from examples.utility.wind_parameters import WindGeometry

INTERPRETATION = {
    "schema": "utility-wind-annual-interpretation-v1",
    "height_m": 80,
    "turbines": 4,
    "rotor_diameter_m": 80,
    "rated_power_W": 2e6,
    "direction": "meteorological-from-degrees-clockwise-from-north",
    "direction_360": "wrap-to-zero",
    "integration": "instantaneous-UTC-hour-represents-one-hour",
    "missing": "reject-incomplete-joint-support",
    "density": "fixed-curve-no-weather-density-correction",
    "year_weighting": "equal-year-actual-duration",
    "source_interpretation_admitted": False,
}
MODEL_FILES = (
    "examples/utility/wind_hourly.py",
    "examples/utility/wind_parameters.py",
    "examples/utility/wind.py",
    "examples/utility/wind_annual.py",
    "pixi.lock",
)


def source_identity():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def model_identity():
    root = Path(__file__).resolve().parents[2]
    return digest(
        {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in MODEL_FILES}
    )


def _axis(year):
    if type(year) is not int or not 2007 <= year <= 2014:
        raise ValueError("annual wind kernel requires a declared historical year")
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    return tuple(
        (start + timedelta(hours=i)).isoformat().replace("+00:00", "Z")
        for i in range((366 if calendar.isleap(year) else 365) * 24)
    )


@dataclass(frozen=True)
class AnnualWindDrivers:
    year: int
    object_identity_digest: str
    time_utc: tuple[str, ...]
    speed_m_s: np.ndarray
    direction_deg: np.ndarray

    def __post_init__(self):
        sha256(self.object_identity_digest)
        axis = _axis(self.year)
        if type(self.time_utc) is not tuple or self.time_utc != axis:
            raise ValueError("annual wind kernel requires complete chronological UTC support")
        object.__setattr__(self, "time_utc", axis)
        for name, maximum in (("speed_m_s", 100), ("direction_deg", 360)):
            raw = np.asarray(getattr(self, name))
            if raw.dtype.kind not in "fiu" or raw.shape != (len(axis),):
                raise ValueError("annual wind drivers require normalized numeric vectors")
            values = np.asarray(raw, dtype="<f8")
            if (
                values.shape != (len(axis),)
                or not np.isfinite(values).all()
                or (values < 0).any()
                or (values > maximum).any()
            ):
                raise ValueError("annual wind drivers exceed the complete finite source profile")
            object.__setattr__(self, name, np.frombuffer(values.tobytes(), dtype="<f8"))

    @property
    def manifest(self):
        return {
            "schema": "utility-wind-annual-driver-manifest-v1",
            "year": self.year,
            "object_identity_digest": self.object_identity_digest,
            "time_utc_digest": digest(self.time_utc),
            "hours": len(self.time_utc),
            "height_m": 80,
            "speed_f64le_sha256": hashlib.sha256(self.speed_m_s.tobytes()).hexdigest(),
            "direction_f64le_sha256": hashlib.sha256(self.direction_deg.tobytes()).hexdigest(),
        }

    @property
    def manifest_digest(self):
        return digest(self.manifest)


@dataclass(frozen=True)
class AnnualWindScorePolicy(Record):
    schema: Literal["utility-wind-annual-score-v1"]
    scorer_source_digest: str
    model_digest: str
    plan_digest: str

    def _validate(self):
        for value in (self.scorer_source_digest, self.model_digest, self.plan_digest):
            sha256(value)


@dataclass(frozen=True)
class AnnualWindKernelResult:
    score: PublicScore
    run: AnnualWindRun
    attempted_model_starts: int
    completed_model_starts: int
    last_attempt_work_unknown: bool


class _InvalidPhysicalOutput(ValueError):
    pass


def _energy(drivers, x, y):
    model, _ = wind_hourly._backend()
    axis = np.asarray([stamp[:-1] for stamp in drivers.time_utc], dtype="datetime64[s]")
    result = model(
        x=np.asarray(x),
        y=np.asarray(y),
        h=np.full(4, 80.0),
        ws=drivers.speed_m_s.copy(),
        wd=drivers.direction_deg.copy() % 360,
        time=axis,
    )
    if not np.array_equal(result.time.values, axis) or not np.array_equal(
        result.h.values, np.full(4, 80.0)
    ):
        raise _InvalidPhysicalOutput("annual wind model changed declared support")
    power = np.asarray(result.Power.transpose("wt", "time").values, dtype=float)
    if (
        power.shape != (4, len(axis))
        or not np.isfinite(power).all()
        or (power < 0).any()
        or (power > 2e6 * (1 + 1e-10)).any()
    ):
        raise _InvalidPhysicalOutput("annual wind model violated fixed hardware output bounds")
    return float(power.sum(dtype=np.float64)) / 1e9


def score_annual(configuration, geometry, plan, drivers, root, *, policy, execution_digest):
    """Consume an empty private work scope once; never retry a started model year.

    Validation precedes optional model import. Backend entry is charged before
    constructing the annual model. A failed attempt has unknown inner work.
    Remaining years are retained as not_attempted, never evaluated after failure.
    """
    if (
        not isinstance(policy, AnnualWindScorePolicy)
        or policy.scorer_source_digest != source_identity()
        or policy.model_digest != model_identity()
        or not isinstance(plan, AnnualWindPlan)
        or policy.plan_digest != plan.digest
        or plan.model_digest != policy.model_digest
        or plan.interpretation_digest != digest(INTERPRETATION)
        or not isinstance(geometry, WindGeometry)
        or len(geometry.x) != 4
        or plan.geometry_digest != geometry.digest
    ):
        raise ValueError("annual wind kernel source, policy, model or geometry changed")
    sha256(execution_digest)
    configuration = dict(configuration)
    geometry.validate(configuration)
    x, y = geometry.positions(configuration)
    # Bound iterable consumption even when a caller supplies an unbounded source.
    from itertools import islice

    drivers = tuple(islice(drivers, 9))
    if len(drivers) != len(plan.sources) or len(drivers) > 8:
        raise ValueError("annual wind driver coverage differs from the complete plan")
    for source, data in zip(plan.sources, drivers, strict=True):
        if (
            not isinstance(data, AnnualWindDrivers)
            or data.year != source.year
            or data.object_identity_digest != source.object_identity_digest
            or data.manifest_digest != source.point_manifest_digest
        ):
            raise ValueError("annual wind drivers changed their frozen source identity")
    root = checked_directory(root)
    if any(root.iterdir()):
        raise ValueError("annual wind scoring scope already consumed")

    def save(name, value):
        durable_write(root / name, canonical_json(value).encode())

    save(
        "intent.json",
        {
            "execution_digest": execution_digest,
            "policy_digest": policy.digest,
            "plan_digest": plan.digest,
            "configuration_digest": digest(configuration),
            "model_starts_reserved": len(plan.sources),
            "automatic_retries": 0,
            "private_boundary_qualified": False,
            "os_limits_qualified": False,
        },
    )
    results, attempted, completed = [], 0, 0
    failed = False
    unknown = False
    for index, (source, data) in enumerate(zip(plan.sources, drivers, strict=True)):
        if failed:
            results.append(AnnualWindResult(source.year, source.digest, "not_attempted", None))
            continue
        save(
            f"{index:02d}-start.json",
            {
                "year": source.year,
                "source_digest": source.digest,
                "status": "started",
                "execution_digest": execution_digest,
                "automatic_retries": 0,
            },
        )
        attempted += 1
        try:
            energy = _energy(data, x, y)
        except _InvalidPhysicalOutput:
            status, energy = "scientific_infeasible", None
            failed, unknown = True, True
        except TimeoutError:
            status, energy = "timeout", None
            failed, unknown = True, True
        except ImportError:
            status, energy = "infrastructure_failure", None
            failed, unknown = True, True
        except Exception:
            # Model exceptions can contain forcing or filesystem details.
            status, energy = "model_failure", None
            failed, unknown = True, True
        else:
            completed += 1
            status = "success"
        annual = AnnualWindResult(source.year, source.digest, status, energy)
        save(f"{index:02d}-result.json", annual.to_dict())
        results.append(annual)
    run = AnnualWindRun(
        "utility-wind-annual-run-v1",
        plan.digest,
        digest(configuration),
        tuple(results),
    )
    status = next((result.status for result in results if result.status != "success"), "success")
    mean = math.fsum(result.energy_gwh for result in results) / len(results) if not failed else None
    feasible = True if not failed else False if status == "scientific_infeasible" else None
    score = PublicScore(status, "mean_annual_energy", "GWh", mean, feasible)
    save(
        "complete.json",
        {
            "execution_digest": execution_digest,
            "policy_digest": policy.digest,
            "score": score.to_dict(),
            "annual_run": run.to_dict(),
            "attempted_model_starts": attempted,
            "completed_model_starts": completed,
            "last_attempt_work_unknown": unknown,
            "inner_solver_work": None,
            "automatic_retries": 0,
            "task_admitted": False,
        },
    )
    return AnnualWindKernelResult(score, run, attempted, completed, unknown)
