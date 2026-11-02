"""Source-bound hourly wind scenarios for the existing scientific executor.

Public 2007 development inputs only. This binding grants no private-data access,
new hardware choices, direction qualification or generated-code admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
import time
from typing import Literal

import numpy as np

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.adapters.python import run_lifecycle
from autoengineering.campaign.acceptance import CheckContext, CheckRegistry, finite
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.records import (
    ArtifactRef,
    EvaluationRecord,
    ModelSnapshot,
    PortContract,
)
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.engineering_process import EngineeringScenarioResult
from autoengineering.utility.outcomes import OutcomeRegistry
from examples.utility.wind import ROOT, UNITS
from examples.utility.wind_hourly import POLICY, SOURCE_FILES, WindHourly, read_point
from examples.utility.wind_parameters import WindGeometry
from examples.utility.wind_scenario import (
    annual_energy,
    rules,
    spacing,
    nonnegative_power,
    rated_power,
    boundary,
)

BINDING_PATH = "inputs/wind-hourly-binding.json"
POINT_PATH = "inputs/wind-hourly-point.npz"
REVIEW_PATH = "inputs/wind-hourly-assumptions.json"
COMPLETION_DIGEST = "aa9ef3ecdd47ea9f3f8057b9f6f40f4142d38e18bfb3f9ead6041bcd30156a5c"
POINT_SHA = "b0539c5cb91bb6aa7a6ec642342492cab9494403e9d9cb339fa45f1783a6cca9"
# This review was frozen before the separately counted standalone parity run.
REVIEW_SHA = "f56f3c72c7486d71b6e6de6ef61f71a792e4de354fb1a8f1dcdb60739a1f3c6a"
SCENARIO_ID = "wind-hourly-2007-development"
SCENARIO_FORCING = {"source_year": 2007.0, "height_m": 80.0}
MODEL_SOURCES = (
    *SOURCE_FILES,
    "examples/utility/wind_scenario.py",
    "examples/utility/wind_hourly_scenario.py",
)


@dataclass(frozen=True)
class HourlyBinding(Record):
    schema: Literal["utility-wind-hourly-scenario-binding-v1"]
    geometry: WindGeometry
    point: ArtifactRef
    assumptions: ArtifactRef
    policy_digest: str
    acquisition_completion_digest: str
    task_admitted: Literal[False] = False

    def _validate(self):
        self.geometry.validate(self.geometry.baseline)
        if (
            len(self.geometry.x) != 4
            or self.point.path != POINT_PATH
            or self.point.sha256 != POINT_SHA
            or self.point.size_bytes > 512 * 1024
            or self.assumptions.path != REVIEW_PATH
            or self.assumptions.sha256 != REVIEW_SHA
            or self.assumptions.size_bytes > 65536
            or self.policy_digest != digest(POLICY)
            or self.acquisition_completion_digest != COMPLETION_DIGEST
        ):
            raise ValueError("hourly binding differs from reviewed development source or policy")


def materialize_inputs(source):
    """Copy existing public data and assumption bytes, without a model or provider."""
    source = checked_directory(source)
    original = ROOT / "examples/utility/verification-wind-hourly-2007-v1/public"
    target = source / "inputs"
    target.mkdir(mode=0o700, exist_ok=True)
    checked_directory(target)
    for name, origin in ((POINT_PATH, "point.npz"), (REVIEW_PATH, "assumptions.json")):
        ref = reference(
            original, origin, media_type="application/octet-stream", producer="wind-hourly"
        )
        durable_write(source / name, read_bytes(original, ref, max_bytes=512 * 1024))
    point = reference(source, POINT_PATH, media_type="application/npz", producer="wind-hourly")
    review = reference(source, REVIEW_PATH, media_type="application/json", producer="wind-hourly")
    binding = HourlyBinding(
        "utility-wind-hourly-scenario-binding-v1",
        WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0)),
        point,
        review,
        digest(POLICY),
        COMPLETION_DIGEST,
    )
    durable_write(source / BINDING_PATH, binding.to_json().encode())
    return binding


def load_inputs(job):
    """Refuse mismatched metadata, source or geometry before importing the model."""
    root = Path(job.source_root)
    refs = {r.path: r for r in job.execution.sources}
    if (
        len(refs) != len(job.execution.sources)
        or not {BINDING_PATH, POINT_PATH, REVIEW_PATH} <= refs.keys()
    ):
        raise ValueError("hourly scenario requires unique declared binding, point and review")
    binding = HourlyBinding.from_json(
        read_bytes(root, refs[BINDING_PATH], max_bytes=65536).decode()
    )
    if refs[POINT_PATH] != binding.point or refs[REVIEW_PATH] != binding.assumptions:
        raise ValueError("hourly source declarations differ from binding")
    review = unique_json(read_bytes(root, binding.assumptions, max_bytes=65536).decode())
    if (
        review.get("raw_hdf_direction_qualified") is not False
        or review.get("task_admitted") is not False
    ):
        raise ValueError("hourly scenario cannot promote unqualified assumptions")
    if (
        len(job.execution.scenarios) != 1
        or job.scenario_id != SCENARIO_ID
        or job.execution.scenarios[0].scenario_id != SCENARIO_ID
        or dict(job.execution.scenarios[0].forcing) != SCENARIO_FORCING
        or job.execution.study.rules != rules()
    ):
        raise ValueError("hourly scenario, forcing or scientific rules differ")
    binding.geometry.validate(job.configuration)
    data = read_point(root, binding.point, 2007)
    profile = WindHourly(
        binding.geometry,
        2007,
        tuple(data["time_utc"]),
        data["speed_m_s"],
        data["direction_source_deg"],
        binding.point.sha256,
        digest(review),
    )
    return binding, profile, job.execution.scenarios[0]


def context(job, binding, profile):
    root = Path(job.source_root)
    declared = {ref.path: ref for ref in job.execution.sources}
    names = (*MODEL_SOURCES, BINDING_PATH, POINT_PATH, REVIEW_PATH)
    if not set(names) <= declared.keys():
        raise ValueError("hourly scenario model source closure is incomplete")
    refs = tuple(declared[name] for name in names)
    for ref in refs:
        read_bytes(root, ref)
    if version("py-wake") != "2.6.20":
        raise ValueError("hourly scenario needs reviewed PyWake 2.6.20")
    outputs = tuple(
        PortContract(name, (), unit, "float", (), "scalar", digest({"grid": "scalar"}), None)
        for name, unit in UNITS.items()
    )
    model = ModelSnapshot(
        digest({"profile": profile.identity, "binding": binding.digest}),
        {"wind": "hourly-80m-noj-development-v1"},
        refs,
        digest({"py-wake": version("py-wake")}),
        (),
        outputs,
    )
    return PrepareContext(model, dict(job.configuration), job.seed, job.scratch_path, ())


def _evaluate(job, *, direct):
    binding, profile, scenario = load_inputs(job)
    ctx = context(job, binding, profile)
    if direct:
        started = time.perf_counter()
        outputs = profile.physical({}, job.configuration)
        elapsed = time.perf_counter() - started
    else:
        result = run_lifecycle(profile.adapter(), ctx, {}, (), ctx.model.outputs)
        if result.training.status != "not_applicable":
            raise ValueError("hourly wind cannot train during scenario execution")
        outputs, elapsed = result.outputs, result.elapsed_seconds
    template = EvaluationRecord(
        job.action_id,
        ctx.model.digest,
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
        {
            scenario.scenario_id: CheckContext(
                outputs, {k: np.asarray(v) for k, v in scenario.forcing.items()}, ctx.parameters
            )
        },
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
