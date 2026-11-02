"""Supplied resource scenario using the existing owned engineering executor.

This executes public/development inputs. It is not a qualified private scorer.
Private confirmation resources must not be placed in its public source bundle.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import time

import numpy as np

from autoengineering.adapters.python import PythonAdapter, run_lifecycle
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.serialization import digest
from examples.utility.wind_parameters import WindGeometry
from examples.utility.wind_resource import RESOURCE_PATH, read_resource
from examples.utility.wind_scenario import GEOMETRY_PATH, rules, score_outputs


def outputs(geometry, resource, configuration):
    geometry.validate(configuration)
    resource.validate_geometry(geometry)
    x, y = (np.asarray(a) for a in geometry.positions(configuration))
    aep, power = resource.evaluate(x, y)
    distance = np.hypot(x[:, None] - x, y[:, None] - y)
    np.fill_diagonal(distance, np.inf)
    return {
        name: np.asarray(value)
        for name, value in {
            "annual_energy": np.sum(aep),
            "minimum_spacing": distance.min(),
            "boundary_violation": 0.0,
            "maximum_power": np.max(power),
            "minimum_power": np.min(power),
        }.items()
    }


def load_inputs(job):
    """Validate geometry, resource, rules and case before any physical model call."""
    root = Path(job.source_root)
    refs = {r.path: r for r in job.execution.sources}
    if GEOMETRY_PATH not in refs or RESOURCE_PATH not in refs:
        raise ValueError("wind resource scenario requires geometry and resource artifacts")
    geometry = WindGeometry.from_json(
        read_bytes(root, refs[GEOMETRY_PATH], max_bytes=65536).decode()
    )
    resource = read_resource(root, refs[RESOURCE_PATH])
    resource.validate_geometry(geometry)
    if len(geometry.x) != 4 or len(job.execution.scenarios) != 1:
        raise ValueError("supplied wind resource profile needs four turbines and one scenario")
    scenario = job.execution.scenarios[0]
    if scenario.scenario_id != job.scenario_id or dict(scenario.forcing) != {
        "direction_step": float(geometry.direction_step)
    }:
        raise ValueError("wind resource scenario cannot override its frozen flow cases")
    if job.execution.study.rules != rules():
        raise ValueError("wind resource scenario rules differ from registered physics")
    geometry.validate(job.configuration)
    return geometry, resource, scenario, refs[RESOURCE_PATH]


def _evaluate(job, *, direct):
    geometry, resource, scenario, resource_ref = load_inputs(job)
    root = Path(job.source_root)
    context = geometry.context(job.configuration, job.scratch_path, source_root=root)
    extra = tuple(
        reference(root, name, media_type="text/plain", producer="wind-resource")
        for name in (
            "examples/utility/wind_resource.py",
            "examples/utility/wind_resource_scenario.py",
        )
    )
    context = replace(
        context,
        seed=job.seed,
        model=replace(
            context.model,
            graph_digest=digest(
                {
                    "profile": "supplied-wind-resource-v1",
                    "geometry_graph": context.model.graph_digest,
                    "resource": resource.digest,
                }
            ),
            implementations={"wind": "supplied-resource-noj-v1"},
            source_bundle=(*context.model.source_bundle, *extra, resource_ref),
        ),
    )
    if direct:
        began = time.perf_counter()
        values = outputs(geometry, resource, job.configuration)
        elapsed = time.perf_counter() - began
    else:

        def physical(forcing, configuration):
            if forcing:
                raise ValueError("wind resource is frozen; forcing overrides are forbidden")
            return outputs(geometry, resource, configuration)

        result = run_lifecycle(
            PythonAdapter(physical, geometry.validate), context, {}, (), context.model.outputs
        )
        if result.training.status != "not_applicable":
            raise ValueError("wind resource scenario does not admit training")
        values, elapsed = result.outputs, result.elapsed_seconds
    return score_outputs(job, geometry, scenario, context, values, elapsed)


def execute(job):
    return _evaluate(job, direct=False)


def direct(job):
    return _evaluate(job, direct=True)
