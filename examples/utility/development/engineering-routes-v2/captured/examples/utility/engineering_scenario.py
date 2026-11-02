"""Supplied coupled-circuit callback for one supervised development scenario."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from autoengineering.campaign.acceptance import CheckContext, CheckRegistry
from autoengineering.campaign.records import EvaluationRecord
from autoengineering.utility.engineering_process import EngineeringScenarioResult
from autoengineering.utility.outcomes import OutcomeRegistry
from examples.utility.engineering import adapter, context, required_voltage, source_power


def execute(job):
    if set(job.configuration) != {"source_current"}:
        raise ValueError("circuit profile only admits source-current design")
    scenario = next(s for s in job.execution.scenarios if s.scenario_id == job.scenario_id)
    if set(scenario.forcing) != {"ground_voltage"}:
        raise ValueError("circuit profile needs its ground-voltage forcing")
    ctx = context(job.configuration["source_current"], Path(job.scratch_path), source_root=Path(job.source_root))
    ctx = replace(ctx, seed=job.seed)
    forcing = {name: np.asarray(value) for name, value in scenario.forcing.items()}
    result = run_lifecycle(adapter(), ctx, forcing, ctx.model.inputs, ctx.model.outputs)
    if result.training.status != "not_applicable":
        raise ValueError("engineering scenario profile does not admit training")
    template = EvaluationRecord(job.action_id, ctx.model.digest, job.configuration, "success", {}, (), (),
        "development-fitting", job.action_id, result.elapsed_seconds, {})
    scored = OutcomeRegistry({"source_power": source_power}).evaluate(job.execution.study.rules,
        {scenario.scenario_id: CheckContext(result.outputs, forcing, ctx.parameters)},
        CheckRegistry({("node_voltage", "1"): required_voltage}), template)
    return EngineeringScenarioResult("utility-engineering-result-v1", job.digest, scored.scenarios[0],
        {name: float(value) for name, value in result.diagnostics.items()}, result.elapsed_seconds,
        {"converged":"boolean", "residual_norm":"A", "residual_tolerance":"A",
         "solver_iterations":"count", "component_calls":"count", "derivative_calls":"count"})
