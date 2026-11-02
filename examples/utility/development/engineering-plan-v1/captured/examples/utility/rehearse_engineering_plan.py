"""Public engineering plan run/resume and selection sealing on exposed inputs."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

from autoengineering.agents.identity import host_environment_identity
from autoengineering.agents.process import supervise_process
from autoengineering.agents.records import ResourceLimits
from autoengineering.agents.scheduler import template_digests
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import digest
from autoengineering.utility.contracts import BudgetSpec, ResourceCap, TaskSpec, UtilitySuiteSpec
from autoengineering.utility.engineering_broker import (
    engineering_grant_identity,
    engineering_recipe_identity,
)
from autoengineering.utility.engineering_execution import (
    ScriptedEngineeringPlan,
    TaskEngineeringCampaign,
    case_scoped_campaign,
    engineering_runtime_identity,
)
from autoengineering.utility.mechanical import mechanism_identity
from autoengineering.utility.routes import (
    ScientificGrant,
    HostGrant,
    RoleAllowance,
    RouteRecipe,
    TaskRoute,
    RoutePlan,
    conventional_recipe,
    single_agent_recipe,
    role_removals,
)
from autoengineering.utility.store import SuiteStore
from examples.utility.rehearse_engineering_native import prepare


def prepare_plan(output: Path):
    output, source, campaign = prepare(
        output, extra_sources=("examples/utility/rehearse_engineering_plan.py",)
    )
    campaign = case_scoped_campaign(campaign)
    worker = ResourceLimits(30, 30, 0, 0, 600.0, 10.0, 4194304, 1048576)
    batch = ResourceLimits(150, 150, 0, 0, 1200.0, 10.0, 33554432, 1048576)
    caps = tuple(
        ResourceCap(n, u, v, "reservation")
        for n, u, v in (
            ("scientific_starts", "count", campaign.scientific_starts * 7 + 21),
            ("host_invocations", "count", 150),
            ("training_starts", "count", 0),
            ("active_time", "s", 1200.0 * 7),
        )
    )
    budget = BudgetSpec(
        "fixed_evaluations", caps, (ResourceCap("scientific_starts", "count", 21, "reservation"),)
    )
    shared = engineering_grant_identity(campaign)
    grant = ScientificGrant(
        shared["candidates"],
        shared["partition_digest"],
        shared["search_bounds_digest"],
        shared["acceptance_digest"],
        digest(
            {
                "profile": "engineering-source-only-v1",
                "sources": [r.to_dict() for r in campaign.execution.sources],
            }
        ),
        host_environment_identity(),
        None,
    )
    baseline = RouteRecipe(
        "baseline", grant, None, (), {}, engineering_recipe_identity(campaign), caps
    )
    provisional = RoutePlan(
        "utility-routes-v1",
        (TaskRoute("circuit", "baseline", baseline),),
        1,
        17,
        {"circuit": grant.partition_digest},
    )
    plan = ScriptedEngineeringPlan(
        "utility-scripted-engineering-v1",
        provisional,
        (TaskEngineeringCampaign("circuit", campaign),),
        campaign.execution.sources,
        campaign.execution.lock,
        worker,
        batch,
        engineering_runtime_identity(),
    )
    full = replace(
        baseline,
        kind="multi_agent",
        host=HostGrant(
            plan.host_configuration_digest,
            "scripted",
            "scripted-1.0",
            plan.host_permissions_digest,
            30,
        ),
        roles=tuple(
            RoleAllowance(r, n, template_digests()[r])
            for r, n in (
                ("orchestrator", 11),
                ("investigator", 3),
                ("implementer", 3),
                ("reviewer", 4),
            )
        ),
    )
    variants = (
        baseline,
        conventional_recipe(full, numerical_recipe_digest=full.numerical_recipe_digest),
        single_agent_recipe(
            full, prompt_digest=template_digests("single_agent")["single_agent"], maximum_calls=30
        ),
        full,
        *role_removals(
            full, {r: mechanism_identity(r) for r in ("investigator", "implementer", "reviewer")}
        ),
    )
    routes = RoutePlan(
        "utility-routes-v1",
        tuple(TaskRoute("circuit", r.kind, r) for r in variants),
        1,
        17,
        {"circuit": grant.partition_digest},
    )
    plan = replace(plan, routes=routes)
    task = TaskSpec(
        "circuit",
        "engineering",
        digest(
            {"profile": "exposed-circuit-development", "independent_confirmation": "not_admitted"}
        ),
        grant.partition_digest,
        grant.acceptance_digest,
        grant.candidates,
        ("supplied_scalar_engineering",),
    )
    route_specs, cells = routes.expand((task,), (budget,))
    suite = UtilitySuiteSpec(
        "utility-suite-v1",
        "exposed-engineering-plan",
        (task,),
        route_specs,
        (budget,),
        cells,
        digest([r.to_dict() for r in plan.source_inventory]),
        plan.lock.sha256,
        digest({"analysis": "not_attempted"}),
        digest({"exposure": "known_exposed_ground_scenarios"}),
        plan.digest,
    )
    store = SuiteStore.create(output / "suite", suite)
    (output / "execution-plan.json").write_text(plan.to_json())
    return output, source, plan, store


def run(output: Path):
    output, source, plan, store = prepare_plan(output)
    directory = output / "cli"
    directory.mkdir(mode=0o700)
    results = []

    def command(name, args):
        print("Engineering CLI: " + name, flush=True)
        result = supervise_process(
            (sys.executable, "-m", "autoengineering.cli", "utility", *args),
            directory=directory / name,
            cwd=Path.cwd(),
            environment={},
            nonce="engineering-" + name,
            stdin=b"",
            timeout_seconds=1500.0,
            max_output_bytes=65536,
            on_launch=lambda _: None,
            parent_watchdog=True,
        )
        if (
            result.status != "completed"
            or result.returncode != 0
            or not result.stopped
            or result.truncated
        ):
            raise RuntimeError("Engineering CLI operation failed: " + name)
        document = json.loads(result.stdout)
        results.append({"name": name, "result": document, "stop_verified": result.stopped})
        return document

    common = [
        str(store.root),
        str(output / "execution-plan.json"),
        "--source-root",
        str(source),
        "--scripted-development",
    ]
    first = command("run-one", ["run", *common, "--max-new-cells", "1"])
    assert first["finished_cells"] == 1
    completed = command("resume-rest", ["resume", *common])
    assert completed["finished_cells"] == 7
    repeated = command("resume-complete", ["resume", *common])
    assert repeated["completed_this_call"] == 0
    proposal = completed["selection_proposal"]
    manifest = output / "selection-for-review.json"
    from autoengineering.campaign.records import ArtifactRef

    manifest.write_bytes(read_bytes(store.root, ArtifactRef.from_dict(proposal)))
    assert store.replay()["frozen"] is None
    sealed = command("freeze", ["freeze", str(store.root), str(manifest)])
    assert sealed["status"] == "selection_frozen"
    command("verify", ["verify", str(store.root)])
    command("status", ["status", str(store.root)])
    assert not store.replay()["confirmation_accesses"] and not store.replay()["confirmation_scores"]
    summary = {
        "purpose": "public scripted engineering development plan, not independent utility evidence",
        "operations": results,
        "finished_cells": 7,
        "completed_resume_added_cells": repeated["completed_this_call"],
        "selection_manifest": store.replay()["frozen"],
        "confirmation_accesses": 0,
        "utility_verdict": "not_attempted",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "operations"}), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
