"""Rehearse seven supplied routes on exposed Leaf River, solar and circuit tasks."""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from types import SimpleNamespace

from autoengineering.agents.identity import host_environment_identity
from autoengineering.agents.process import supervise_process
from autoengineering.agents.records import ResourceLimits
from autoengineering.agents.scheduler import template_digests
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.identity import scientific_source_paths
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest
from autoengineering.utility.contracts import BudgetSpec, ResourceCap, TaskSpec, UtilitySuiteSpec
from autoengineering.utility.engineering_broker import (
    engineering_grant_identity,
    engineering_recipe_identity,
)
from autoengineering.utility.engineering_execution import (
    TaskEngineeringCampaign,
    engineering_runtime_identity,
)
from autoengineering.utility.engineering_process import execution_identity
from autoengineering.utility.execution import campaign_recipe_identity
from autoengineering.utility.mechanical import mechanism_identity
from autoengineering.utility.mixed_execution import (
    ScriptedMixedPlan,
    TaskPredictionCampaign,
    ScriptedMixedCoordinator,
)
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
from examples.agent_campaign.prepare_leafriver import _template, TEMPLATE
from examples.campaign_contracts.hydrology import SOURCES
from examples.interoperability.solar.campaign import prepare as prepare_solar
from examples.utility.engineering import ROOT
from examples.utility.rehearse_engineering_native import prepare as prepare_engineering


def _capture(source, origin, refs, inventory):
    for ref in refs:
        raw = read_bytes(origin, ref)
        target = source / ref.path
        if target.exists() and target.read_bytes() != raw:
            raise ValueError("mixed source closure has conflicting bytes")
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(raw)
        inventory[ref.path] = reference(
            source, ref.path, media_type=ref.media_type, producer="mixed-development-capture"
        )


def prepare(output: Path, solar_cache: Path):
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("mixed rehearsal requires an absent output directory")
    # Solar preparation only reads a verified existing cache. No network acquisition.
    output.mkdir(mode=0o700, parents=True)
    solar = prepare_solar(solar_cache, output / "solar-preparation")
    _, source, engineering = prepare_engineering(
        output / "engineering-preparation",
        extra_sources=(
            "examples/utility/rehearse_mixed.py",
            "examples/agent_campaign/prepare_leafriver.py",
            "examples/campaign_contracts/build_profile.py",
            TEMPLATE,
        ),
    )
    inventory = {r.path: r for r in engineering.execution.sources}
    lock = engineering.execution.lock
    _capture(
        source,
        output / "solar-preparation/source",
        (*solar.provenance.sources, solar.baseline.system, *(d.artifact for d in solar.data)),
        inventory,
    )
    leaf = _template(ROOT / TEMPLATE)
    leaf_sources = tuple(
        reference(ROOT, name, media_type="text/plain", producer="mixed-leaf")
        for name in sorted({*SOURCES, *scientific_source_paths()})
    )
    _capture(
        source,
        ROOT,
        (*leaf_sources, leaf.baseline.system, *(d.artifact for d in leaf.data)),
        inventory,
    )
    # Preserve old source references only in the old profiles. These are fresh specs.
    leaf_refs = tuple(inventory[r.path] for r in leaf_sources)
    leaf = replace(
        leaf,
        name="utility-exposed-leaf",
        source_bundle="scientific-core-v1",
        baseline=replace(
            leaf.baseline,
            system=inventory[leaf.baseline.system.path],
            model=replace(
                leaf.baseline.model, source_bundle=leaf_refs, dependency_bundle=lock.sha256
            ),
        ),
        execution=replace(leaf.execution, max_executions=38),
        provenance=replace(leaf.provenance, sources=leaf_refs, environment_lock=lock),
    )
    solar_refs = tuple(inventory[r.path] for r in solar.provenance.sources)
    solar = replace(
        solar,
        name="utility-exposed-solar",
        baseline=replace(
            solar.baseline,
            system=inventory[solar.baseline.system.path],
            model=replace(
                solar.baseline.model, source_bundle=solar_refs, dependency_bundle=lock.sha256
            ),
        ),
        provenance=replace(solar.provenance, sources=solar_refs, environment_lock=lock),
    )
    refs = tuple(inventory[name] for name in sorted(inventory))
    old = engineering.execution
    identity = execution_identity(
        old.entrypoint,
        refs,
        lock,
        old.scenarios,
        old.timeout_seconds,
        old.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        old,
        schema="utility-engineering-execution-v2",
        sources=refs,
        study=replace(old.study, source_identity=identity),
    )
    engineering = replace(
        engineering, execution=execution, native=replace(engineering.native, execution=execution)
    )
    campaigns = (
        TaskPredictionCampaign("leaf", leaf),
        TaskPredictionCampaign("solar", solar),
        TaskEngineeringCampaign("circuit", engineering),
    )
    worker = ResourceLimits(30, 30, 0, 0, 1200.0, 10.0, 8388608, 1048576)
    batch = ResourceLimits(450, 450, 0, 0, 3600.0, 10.0, 134217728, 1048576)
    # Reuse a valid temporary route record until the shared plan digests are available.
    placeholder = "1" * 64
    provisional = RoutePlan(
        "utility-routes-v1",
        (
            TaskRoute(
                "leaf",
                "baseline",
                RouteRecipe(
                    "baseline",
                    ScientificGrant(
                        (placeholder,),
                        placeholder,
                        placeholder,
                        placeholder,
                        placeholder,
                        placeholder,
                        None,
                    ),
                    None,
                    (),
                    {},
                    placeholder,
                    (ResourceCap("scientific_starts", "count", 1, "reservation"),),
                ),
            ),
        ),
        1,
        17,
        {"leaf": placeholder},
    )
    plan = ScriptedMixedPlan(
        "utility-scripted-mixed-v1",
        provisional,
        campaigns,
        refs,
        lock,
        worker,
        batch,
        engineering_runtime_identity(),
    )
    rows, tasks = [], []
    for name, family, campaign in (
        ("leaf", "hydrology", leaf),
        ("solar", "solar", solar),
        ("circuit", "engineering", engineering),
    ):
        if family == "engineering":
            common = engineering_grant_identity(campaign)
            numerical = engineering_recipe_identity(campaign)
            starts = campaign.scientific_starts
        else:
            snapshots = tuple(CampaignController.supplied_snapshots(SimpleNamespace(spec=campaign)))
            common = {
                "candidates": tuple(
                    dict.fromkeys(
                        (campaign.baseline.model.digest, *(s.model.digest for s in snapshots))
                    )
                ),
                "partition_digest": digest([d.to_dict() for d in campaign.data]),
                "search_bounds_digest": digest([i.to_dict() for i in campaign.interventions]),
                "acceptance_digest": campaign.acceptance.digest,
            }
            numerical, starts = (
                campaign_recipe_identity(campaign),
                campaign.execution.max_executions,
            )
        grant = ScientificGrant(
            **common,
            research_corpus_digest=plan.research_corpus_digest,
            hardware_digest=host_environment_identity(),
            training_profile_digest=None,
        )
        caps = tuple(
            ResourceCap(n, u, v, "reservation")
            for n, u, v in (
                ("scientific_starts", "count", starts),
                ("host_invocations", "count", 30),
                ("training_starts", "count", 0),
                ("active_time", "s", 3600.0),
            )
        )
        full = RouteRecipe(
            "multi_agent",
            grant,
            HostGrant(
                plan.host_configuration_digest,
                "scripted",
                "scripted-1.0",
                plan.host_permissions_digest,
                30,
            ),
            tuple(
                RoleAllowance(r, n, template_digests()[r])
                for r, n in (
                    ("orchestrator", 11),
                    ("investigator", 3),
                    ("implementer", 3),
                    ("reviewer", 4),
                )
            ),
            {},
            numerical,
            caps,
        )
        conventional = conventional_recipe(full, numerical_recipe_digest=numerical)
        variants = (
            replace(conventional, kind="baseline"),
            conventional,
            single_agent_recipe(
                full,
                prompt_digest=template_digests("single_agent")["single_agent"],
                maximum_calls=30,
            ),
            full,
            *role_removals(
                full,
                {r: mechanism_identity(r) for r in ("investigator", "implementer", "reviewer")},
            ),
        )
        rows.extend(TaskRoute(name, r.kind, r) for r in variants)
        tasks.append(
            TaskSpec(
                name,
                family,
                digest(
                    {
                        "profile": "exposed-mixed-development",
                        "task": name,
                        "independent_confirmation": "not_admitted",
                    }
                ),
                grant.partition_digest,
                grant.acceptance_digest,
                grant.candidates,
                ("supplied_development",),
            )
        )
    route_plan = RoutePlan(
        "utility-routes-v1", tuple(rows), 1, 17, {t.task_id: t.partition_digest for t in tasks}
    )
    plan = replace(plan, routes=route_plan)
    reserve = 63
    caps = tuple(
        ResourceCap(n, u, v, "reservation")
        for n, u, v in (
            ("scientific_starts", "count", 7 * (38 + 18 + engineering.scientific_starts) + reserve),
            ("host_invocations", "count", 450),
            ("training_starts", "count", 0),
            ("active_time", "s", 3600.0 * 21),
        )
    )
    budget = BudgetSpec(
        "fixed_evaluations",
        caps,
        (ResourceCap("scientific_starts", "count", reserve, "reservation"),),
    )
    routes, cells = route_plan.expand(tuple(tasks), (budget,))
    exposure = {
        "purpose": "known exposed development; no confirmation admission",
        "access_date": datetime.now(timezone.utc).date().isoformat(),
        "leaf": "Historical 2019 fitting/comparison; original labels already exposed",
        "solar": "OEDI 9068, 2018-06-01 through 2018-06-07; original exposed development window",
        "circuit": "Ground -0.05, 0, +0.05 V; existing development voltage constraint 0.62 V",
        "sources": [r.to_dict() for r in refs],
        "actors": "local scripted workers and implementation worker",
    }
    (output / "exposure.json").write_text(json.dumps(exposure, indent=2) + "\n")
    spec = UtilitySuiteSpec(
        "utility-suite-v1",
        "exposed-mixed-development",
        tuple(tasks),
        routes,
        (budget,),
        cells,
        digest([r.to_dict() for r in refs]),
        lock.sha256,
        digest({"analysis": "not_attempted"}),
        digest(exposure),
        plan.digest,
    )
    store = SuiteStore.create(output / "suite", spec)
    ScriptedMixedCoordinator(
        store, plan, source
    )  # Validate the complete proposal before any allocation.
    (output / "execution-plan.json").write_text(plan.to_json())
    return output, source, plan, store


def run(output: Path, solar_cache: Path):
    output, source, plan, store = prepare(output, solar_cache)
    directory = output / "cli"
    directory.mkdir(mode=0o700)
    operations = []

    def command(name, args):
        print("Mixed CLI: " + name, flush=True)
        result = supervise_process(
            (sys.executable, "-m", "autoengineering.cli", "utility", *args),
            directory=directory / name,
            cwd=ROOT,
            environment={},
            nonce="mixed-" + name,
            stdin=b"",
            timeout_seconds=3600.0,
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
            raise RuntimeError("Mixed CLI operation failed: " + name)
        document = json.loads(result.stdout)
        operations.append({"name": name, "result": document, "stop_verified": result.stopped})
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
    assert completed["finished_cells"] == 21
    repeated = command("resume-complete", ["resume", *common])
    assert repeated["completed_this_call"] == 0
    manifest = output / "selection-for-review.json"
    manifest.write_bytes(
        read_bytes(store.root, ArtifactRef.from_dict(completed["selection_proposal"]))
    )
    assert store.replay()["frozen"] is None
    command("freeze", ["freeze", str(store.root), str(manifest)])
    command("verify", ["verify", str(store.root)])
    command("status", ["status", str(store.root)])
    assert not store.replay()["confirmation_accesses"] and not store.replay()["confirmation_scores"]
    summary = {
        "purpose": "exposed three-family scripted development; not independent utility evidence",
        "operations": operations,
        "finished_cells": 21,
        "completed_resume_added_cells": 0,
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
    parser.add_argument("--solar-cache", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        out, source, plan, store = prepare(args.output, args.solar_cache)
        print(
            json.dumps(
                {
                    "suite": str(store.root),
                    "source": str(source),
                    "plan": plan.digest,
                    "cells": len(store.spec.cells),
                }
            )
        )
    else:
        run(args.output, args.solar_cache)
