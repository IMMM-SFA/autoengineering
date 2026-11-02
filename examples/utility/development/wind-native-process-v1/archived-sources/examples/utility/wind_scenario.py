"""One supervised wind evaluation under the fixed bundled distribution.

The scenario's direction step is numerical configuration, not unseen weather.
Public wind task admission and the native-process bridge remain separate work.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from autoengineering.campaign.acceptance import CheckContext, CheckRegistry, finite
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import EvaluationRecord
from autoengineering.campaign.spec import CheckSpec
from autoengineering.utility.engineering_process import EngineeringScenarioResult
from autoengineering.utility.outcomes import (
    EngineeringAcceptance,
    OutcomeSpec,
    OutcomeRegistry,
    evaluator_identity,
)
from examples.utility.wind_parameters import WindGeometry

GEOMETRY_PATH = "inputs/wind-geometry.json"


def annual_energy(context):
    return float(context.outputs["annual_energy"])


def spacing(context, options):
    value, lower = float(context.outputs["minimum_spacing"]), float(options["minimum_m"])
    return "pass" if value >= lower else "fail", value, lower, "Fixed four-diameter spacing"


def nonnegative_power(context, options):
    value = float(context.outputs["minimum_power"])
    return "pass" if value >= 0 else "fail", value, 0.0, "Nonnegative modeled turbine power"


def rated_power(context, options):
    value, upper = float(context.outputs["maximum_power"]), float(options["maximum_W"])
    return "pass" if value <= upper else "fail", value, upper, "Fixed V80 turbine rating"


def boundary(context, options):
    value = float(context.outputs["boundary_violation"])
    return "pass" if value == 0 else "fail", value, 0.0, "Frozen rectangle and parameter domain"


def rules():
    return EngineeringAcceptance(
        "engineering-acceptance-v1",
        (
            OutcomeSpec(
                "engineering-outcome-v1",
                "annual_energy",
                "GWh",
                "maximize",
                "mean",
                evaluator_identity(annual_energy),
            ),
        ),
        "annual_energy",
        0.0,
        {},
        (
            CheckSpec("finite", "1", True, "outputs", {}),
            CheckSpec("wind_spacing", "1", True, "outputs", {"minimum_m": 320.0 - 1e-3}),
            CheckSpec("wind_nonnegative_power", "1", True, "outputs", {}),
            CheckSpec("wind_rated_power", "1", True, "outputs", {"maximum_W": 2e6 * (1 + 1e-10)}),
            CheckSpec("wind_boundary", "1", True, "outputs", {}),
        ),
    )


def _evaluate(job, *, direct):
    geometry_ref = next((r for r in job.execution.sources if r.path == GEOMETRY_PATH), None)
    if geometry_ref is None:
        raise ValueError("wind evaluation requires a frozen geometry artifact")
    geometry = WindGeometry.from_json(
        read_bytes(Path(job.source_root), geometry_ref, max_bytes=65536).decode()
    )
    if len(geometry.x) != 4 or len(job.execution.scenarios) != 1:
        raise ValueError(
            "wind scenario profile requires four turbines and one bundled distribution"
        )
    scenario = next(s for s in job.execution.scenarios if s.scenario_id == job.scenario_id)
    if dict(scenario.forcing) != {"direction_step": float(geometry.direction_step)}:
        raise ValueError(
            "wind scenario cannot override its frozen distribution or numerical profile"
        )
    if job.execution.study.rules != rules():
        raise ValueError("wind scenario rules differ from the registered profile")
    geometry.validate(job.configuration)
    context = replace(
        geometry.context(job.configuration, job.scratch_path, source_root=job.source_root),
        seed=job.seed,
    )
    if direct:
        from examples.open_chains.wind.models import wakes

        x, y = (np.asarray(values) for values in geometry.positions(job.configuration))
        before = time.perf_counter()
        aep, power = wakes(x, y, geometry.direction_step)
        distances = np.hypot(x[:, None] - x, y[:, None] - y)
        np.fill_diagonal(distances, np.inf)
        outputs = {
            "annual_energy": np.asarray(np.sum(aep)),
            "minimum_spacing": np.asarray(distances.min()),
            "boundary_violation": np.asarray(0.0),
            "maximum_power": np.asarray(np.max(power)),
            "minimum_power": np.asarray(np.min(power)),
        }
        elapsed = time.perf_counter() - before
    else:
        result = run_lifecycle(geometry.adapter(), context, {}, (), context.model.outputs)
        if result.training.status != "not_applicable":
            raise ValueError("wind scenario profile does not admit training")
        outputs, elapsed = result.outputs, result.elapsed_seconds
    forcing = {"direction_step": np.asarray(float(geometry.direction_step))}
    template = EvaluationRecord(
        job.action_id,
        context.model.digest,
        job.configuration,
        "success",
        {},
        (),
        (),
        "development-fitting",
        job.action_id,
        elapsed,
        {},
    )
    scored = OutcomeRegistry({"annual_energy": annual_energy}).evaluate(
        job.execution.study.rules,
        {scenario.scenario_id: CheckContext(outputs, forcing, context.parameters)},
        CheckRegistry(
            {
                ("finite", "1"): finite,
                ("wind_spacing", "1"): spacing,
                ("wind_nonnegative_power", "1"): nonnegative_power,
                ("wind_rated_power", "1"): rated_power,
                ("wind_boundary", "1"): boundary,
            }
        ),
        template,
    )
    return EngineeringScenarioResult(
        "utility-engineering-result-v1",
        job.digest,
        scored.scenarios[0],
        {"wind_evaluations": 1.0},
        elapsed,
        {"wind_evaluations": "count"},
    )


def execute(job):
    return _evaluate(job, direct=False)


def direct(job):
    return _evaluate(job, direct=True)
