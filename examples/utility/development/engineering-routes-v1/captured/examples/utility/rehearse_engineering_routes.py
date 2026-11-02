"""Seven scripted engineering routes over the same exposed circuit choices.

This is a bounded development rehearsal, not evidence of LLM or scientific utility.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from autoengineering.agents.batch import BatchCase, BatchSpec
from autoengineering.agents.hosts.scripted import scripted_host
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.permissions import policy_digest
from autoengineering.agents.records import AgentRunSpec, HostSelection, ResourceLimits
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.serialization import digest
from autoengineering.utility.contracts import BudgetSpec, ResourceCap, TaskSpec, UtilitySuiteSpec
from autoengineering.utility.controller import CaseBinding, UtilityController
from autoengineering.utility.engineering_broker import (
    EngineeringBroker,
    engineering_catalogue,
    engineering_grant_identity,
    engineering_recipe_identity,
    paired_engineering_spec,
    run_engineering_recipe,
)
from autoengineering.utility.engineering_campaign import EngineeringCampaign
from autoengineering.utility.engineering_process import SupervisedEngineeringExecutor
from autoengineering.utility.execution import BatchScriptedHost
from autoengineering.utility.mechanical import mechanism_identity
from autoengineering.utility.role_host import RoleBoundHost
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


def run(output: Path):
    output, source, campaign_spec = prepare(
        output, extra_sources=("examples/utility/rehearse_engineering_routes.py",)
    )
    worker_limits = ResourceLimits(30, 30, 0, 0, 600.0, 10.0, 4194304, 1048576)
    batch_limits = replace(worker_limits, elapsed_seconds=900.0)
    host_profile = digest(
        {"profile": "scripted-engineering-routes-v1", "worker_limits": worker_limits.to_dict()}
    )
    shared = engineering_grant_identity(campaign_spec)
    grant = ScientificGrant(
        shared["candidates"],
        shared["partition_digest"],
        shared["search_bounds_digest"],
        shared["acceptance_digest"],
        digest(
            {
                "corpus": "supplied source inventory only",
                "sources": [r.sha256 for r in campaign_spec.execution.sources],
            }
        ),
        host_environment_identity(),
        None,
    )
    caps = tuple(
        ResourceCap(name, unit, value, "reservation")
        for name, unit, value in (
            ("scientific_starts", "count", campaign_spec.scientific_starts * 7 + 21),
            ("host_invocations", "count", 150),
            ("training_starts", "count", 0),
            ("active_time", "s", 900.0 * 7),
        )
    )
    budget = BudgetSpec(
        "fixed_evaluations", caps, (ResourceCap("scientific_starts", "count", 21, "reservation"),)
    )
    recipe = RouteRecipe(
        "multi_agent",
        grant,
        HostGrant(host_profile, "scripted", "scripted-1.0", policy_digest("four_role"), 30),
        tuple(
            RoleAllowance(role, count, template_digests()[role])
            for role, count in (
                ("orchestrator", 11),
                ("investigator", 3),
                ("implementer", 3),
                ("reviewer", 4),
            )
        ),
        {},
        engineering_recipe_identity(campaign_spec),
        caps,
    )
    conventional = conventional_recipe(
        recipe, numerical_recipe_digest=recipe.numerical_recipe_digest
    )
    variants = (
        replace(conventional, kind="baseline"),
        conventional,
        single_agent_recipe(
            recipe, prompt_digest=template_digests("single_agent")["single_agent"], maximum_calls=30
        ),
        recipe,
        *role_removals(
            recipe,
            {
                role: mechanism_identity(role)
                for role in ("investigator", "implementer", "reviewer")
            },
        ),
    )
    plan = RoutePlan(
        "utility-routes-v1",
        tuple(TaskRoute("circuit", v.kind, v) for v in variants),
        1,
        17,
        {"circuit": grant.partition_digest},
    )
    task = TaskSpec(
        "circuit",
        "engineering",
        digest(
            {"purpose": "exposed-circuit-development", "independent_confirmation": "not_admitted"}
        ),
        grant.partition_digest,
        grant.acceptance_digest,
        grant.candidates,
        ("supplied_scalar_engineering",),
    )
    routes, cells = plan.expand((task,), (budget,))
    spec = UtilitySuiteSpec(
        "utility-suite-v1",
        "exposed-engineering-routes",
        (task,),
        routes,
        (budget,),
        cells,
        digest([r.to_dict() for r in campaign_spec.execution.sources]),
        campaign_spec.execution.lock.sha256,
        digest({"analysis": "not_attempted"}),
        digest({"exposure": "known_exposed_ground_scenarios"}),
        digest(
            {
                "profile": "scripted-engineering-rehearsal-v1",
                "plan": plan.digest,
                "campaign": campaign_spec.digest,
            }
        ),
    )
    store = SuiteStore.create(output / "suite", spec)
    runtime = UtilityController(store)
    (output / "route-plan.json").write_text(plan.to_json())
    (output / "base-campaign.json").write_text(campaign_spec.to_json())
    results = []
    for index, cell in enumerate(cells):
        row = next(row for row in plan.task_routes if row.route_id == cell.route_id)
        case = BatchCase(
            "selection",
            "comparison",
            next(r.configuration_digest for r in routes if r.route_id == cell.route_id),
            30 if row.recipe.host else 0,
            campaign_spec.scientific_starts,
        )
        batch_spec = BatchSpec(
            "1.0",
            f"engineering-route-{index}",
            host_source_identity(),
            host_environment_identity(),
            HostSelection("fake", "none", "scripted", "1.0"),
            scripted_host().capabilities(),
            host_profile,
            batch_limits,
            campaign_spec.scientific_starts,
            (case,),
        )
        child = runtime.prepare_batch(batch_spec, (CaseBinding(cell.digest, case.id),))

        def execute(batch, case_id):
            root = batch.root / "cases" / case_id
            root.mkdir(mode=0o700, exist_ok=True)
            paired = paired_engineering_spec(campaign_spec, cell.seed)
            controller = EngineeringCampaign.create(
                root / "engineering",
                paired,
                SupervisedEngineeringExecutor(paired.execution, batch, case_id, source),
            )
            if row.recipe.host:
                route = "single_agent" if row.recipe.kind == "single_agent" else "four_role"
                worker_spec = AgentRunSpec(
                    "1.1" if route == "single_agent" else "1.0",
                    "engineering-" + cell.digest[:24],
                    paired.name,
                    digest(controller.identity),
                    batch_spec.host,
                    template_digests(route),
                    tuple(i["implementation_id"] for i in engineering_catalogue(paired)),
                    policy_digest(route),
                    worker_limits,
                    host_source_identity(),
                    host_environment_identity(),
                    "supplied",
                    route,
                )
                workers = WorkerStore.create(root / "worker", worker_spec)
                host = RoleBoundHost(
                    store,
                    batch,
                    cell.digest,
                    plan,
                    BatchScriptedHost(batch, case_id, route),
                    templates={r.role: r.prompt_digest for r in row.recipe.roles},
                )
                broker = EngineeringBroker(
                    controller,
                    SerialScheduler(workers, host),
                    suite_store=store,
                    plan=plan,
                    cell_digest=cell.digest,
                )
                final = broker.advance()
                calls = len(workers.replay().invocations)
                assert broker.advance()["selected"] == final["selected"]
                assert len(workers.replay().invocations) == calls
            else:
                final = run_engineering_recipe(controller, row.recipe.kind)
                calls = 0
                assert (
                    run_engineering_recipe(controller, row.recipe.kind)["selected"]
                    == final["selected"]
                )
            science = sum(r.resource == "science" for r in batch.replay().reservations.values())
            proof = batch.evidence(
                {
                    "profile": "scripted-engineering-routes-v1",
                    "cell": cell.digest,
                    "route": cell.route_id,
                    "campaign": paired.digest,
                    "selection": final["selected"].to_dict() if final["selected"] else None,
                    "scientific_process_reservations": science,
                    "host_calls": calls,
                }
            )
            batch.finish_case(case_id, "passed", (proof,))
            result = {
                "cell_digest": cell.digest,
                "route": cell.route_id,
                "seed": cell.seed,
                "campaign": paired.digest,
                "scientific_process_reservations": science,
                "verified_process_stops": sum(
                    o.stop_verified
                    for o in batch.replay().observations.values()
                    if o.reservation_id.startswith(("science-", "native-"))
                ),
                "host_calls": calls,
                "selected_configuration": dict(final["selected"].configuration)
                if final["selected"]
                else None,
                "native_jobs": len(final["native_reports"]),
                "coded_decision": final["decision"].outcome,
            }
            results.append(result)
            print(json.dumps(result), flush=True)

        runtime.dispatch(child.root.name, cell.digest, execute)
        runtime.verify_result("child-" + cell.digest[:48])
    summary = {
        "purpose": "scripted exposed engineering routes; not LLM or independent utility evidence",
        "cells": results,
        "finished_cells": len(results),
        "paired_seed_count": len({r["seed"] for r in results}),
        "mechanical_steps": len(store.replay()["mechanical_steps"]),
        "role_calls": sum(store.replay()["role_counts"].values()),
        "utility_verdict": "not_attempted",
        "selection_barrier": "not_frozen_by_this_rehearsal",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "cells"}), flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
