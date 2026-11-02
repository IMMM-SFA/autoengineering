"""Prepare a new installed suite from an exported bound bundle without dispatch."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import platform
from unittest.mock import patch

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import digest
from autoengineering.utility.contracts import UtilitySuiteSpec
from autoengineering.utility.engineering_broker import engineering_recipe_identity
from autoengineering.utility.engineering_execution import (
    TaskEngineeringCampaign,
    engineering_runtime_identity,
)
from autoengineering.utility.engineering_process import execution_identity
from autoengineering.utility.execution import campaign_recipe_identity
from autoengineering.utility.mixed_execution import ScriptedMixedPlan, ScriptedMixedCoordinator
from autoengineering.utility.store import SuiteStore

parser = argparse.ArgumentParser()
parser.add_argument("root", type=Path)
parser.add_argument("--baseline-only", action="store_true")
args = parser.parse_args()
root = args.root.resolve()
source = root / "captured"
original = ScriptedMixedPlan.from_json((root / "execution-plan.json").read_text())
parent = UtilitySuiteSpec.from_json((root / "original-suite.json").read_text())
policy = reference(
    source, "runtime-policy.py", media_type="text/plain", producer="installed-qualification"
)
refs = (*original.source_inventory, policy)
campaigns = []
for task in original.campaigns:
    if isinstance(task, TaskEngineeringCampaign):
        old = task.campaign.execution
        identity = execution_identity(
            old.entrypoint,
            refs,
            old.lock,
            old.scenarios,
            old.timeout_seconds,
            old.output_bytes,
            profile="supervised-engineering-v2",
        )
        execution = replace(old, sources=refs, study=replace(old.study, source_identity=identity))
        campaign = replace(
            task.campaign,
            execution=execution,
            native=replace(task.campaign.native, execution=execution),
        )
        task = replace(task, campaign=campaign)
    campaigns.append(task)
plan = replace(
    original,
    campaigns=tuple(campaigns),
    source_inventory=refs,
    runtime_identity=engineering_runtime_identity(),
)
by_task = {t.task_id: t for t in plan.campaigns}
rows = []
for row in plan.routes.task_routes:
    task = by_task[row.task_id]
    numerical = (
        engineering_recipe_identity(task.campaign)
        if isinstance(task, TaskEngineeringCampaign)
        else campaign_recipe_identity(task.campaign)
    )
    grant = replace(row.recipe.scientific_grant, research_corpus_digest=plan.research_corpus_digest)
    rows.append(
        replace(
            row,
            recipe=replace(row.recipe, scientific_grant=grant, numerical_recipe_digest=numerical),
        )
    )
plan = replace(plan, routes=replace(plan.routes, task_routes=tuple(rows)))
if args.baseline_only:
    plan = replace(
        plan,
        routes=replace(
            plan.routes,
            task_routes=tuple(
                row for row in plan.routes.task_routes if row.recipe.kind == "baseline"
            ),
        ),
    )
prefix = "prepared-baseline" if args.baseline_only else "prepared"
routes, cells = plan.routes.expand(parent.tasks, parent.budgets)
new_spec = replace(
    parent,
    suite_id="installed-baseline-smoke" if args.baseline_only else "installed-prepared-four-family",
    routes=routes,
    cells=cells,
    source_digest=digest([r.to_dict() for r in refs]),
    protocol_digest=plan.digest,
    exposure_digest=digest(
        {
            "original": parent.exposure_digest,
            "scope": "exported exposed inputs",
            "policy": policy.sha256,
        }
    ),
)
platform.platform()


def denied(*args, **kwargs):
    raise AssertionError("installed preparation dispatched work")


with patch("subprocess.Popen", denied):
    store = SuiteStore.create(root / (prefix + "-suite"), new_spec)
    ScriptedMixedCoordinator(store, plan, source)
    assert not store.replay()["attempts"] and store.replay()["frozen"] is None
(root / (prefix + "-plan.json")).write_text(plan.to_json())
summary = {
    "status": "passed",
    "cells": len(cells),
    "families": sorted({t.family for t in parent.tasks}),
    "allocations": 0,
    "model_dispatch": "denied",
    "network_sockets": "denied_by_bound_startup_policy",
    "input_scope": "exported digest-bound source/data bundle; no acquisition or source generation",
    "original_study": "unchanged; this is a newly prepared installed-runtime study",
    "confirmation": "not_attempted",
    "utility_verdict": "not_attempted",
}
(root / (prefix + "-summary.json")).write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
