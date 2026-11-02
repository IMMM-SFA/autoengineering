"""Versioned supplied-engineering execution through existing parent/child journals.

This profile admits exposed scalar development inputs and scripted advice only.
Independent confirmation, live hosts and generated code require separate admission.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import sys
from typing import Literal

from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.permissions import policy_digest
from autoengineering.agents.records import AgentRunSpec, HostSelection, ResourceLimits
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import confined_file
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest
from autoengineering.campaign.store import StoreError, checked_directory, durable_write
from .contracts import identifier, sha256
from .controller import UtilityController
from .engineering_broker import (
    EngineeringBroker,
    engineering_catalogue,
    engineering_grant_identity,
    engineering_recipe_identity,
    paired_engineering_spec,
    run_engineering_recipe,
)
from .engineering_campaign import (
    EngineeringCampaign,
    EngineeringNativeCampaignSpec,
    EngineeringCallbackCampaignSpec,
)
from .engineering_process import (
    SupervisedEngineeringExecutor,
    verify_sources,
    execution_identity,
    runtime_packages,
)
from .execution import ScriptedCoordinator, BatchScriptedHost, archive_selected_state
from .role_host import RoleBoundHost
from .routes import RoutePlan


def engineering_runtime_identity():
    return digest(
        {
            "host": host_environment_identity(),
            "python": sys.executable,
            "packages": runtime_packages(),
        }
    )


def case_scoped_campaign(campaign):
    """Prepare a new v2 execution identity. Never apply this to an existing run."""
    execution = campaign.execution
    if execution.schema != "utility-engineering-execution-v1":
        return campaign
    identity = execution_identity(
        execution.entrypoint,
        execution.sources,
        execution.lock,
        execution.scenarios,
        execution.timeout_seconds,
        execution.output_bytes,
        profile="supervised-engineering-v2",
    )
    execution = replace(
        execution,
        schema="utility-engineering-execution-v2",
        study=replace(execution.study, source_identity=identity),
    )
    return replace(
        campaign, execution=execution, native=replace(campaign.native, execution=execution)
    )


@dataclass(frozen=True)
class TaskEngineeringCampaign(Record):
    task_id: str
    campaign: EngineeringNativeCampaignSpec | EngineeringCallbackCampaignSpec

    def _validate(self):
        identifier(self.task_id)


@dataclass(frozen=True)
class ScriptedEngineeringPlan(Record):
    schema: Literal["utility-scripted-engineering-v1"]
    routes: RoutePlan
    campaigns: tuple[TaskEngineeringCampaign, ...]
    source_inventory: tuple[ArtifactRef, ...]
    lock: ArtifactRef
    worker_limits: ResourceLimits
    batch_limits: ResourceLimits
    runtime_identity: str
    purpose: Literal["exposed_development_only"] = "exposed_development_only"

    def _validate(self):
        sha256(self.runtime_identity)
        if not self.campaigns or len({t.task_id for t in self.campaigns}) != len(self.campaigns):
            raise ValueError("engineering plan requires unique task campaigns")
        if not self.source_inventory or len({r.path for r in self.source_inventory}) != len(
            self.source_inventory
        ):
            raise ValueError("engineering plan requires a unique complete source inventory")
        for task in self.campaigns:
            if task.campaign.execution.schema not in (
                "utility-engineering-execution-v2",
                "utility-engineering-execution-v3",
            ):
                raise ValueError("engineering plans require case-scoped execution v2")
            if (
                task.campaign.execution.sources != self.source_inventory
                or task.campaign.execution.lock != self.lock
            ):
                raise ValueError("engineering task differs from shared source/lock closure")

    @property
    def host_configuration_digest(self):
        return digest(
            {
                "profile": "scripted-engineering-v1",
                "worker_limits": self.worker_limits.to_dict(),
                "worker_tools": "none",
            }
        )

    @property
    def host_permissions_digest(self):
        return digest({"profile": "scripted-no-tools-v1"})

    @property
    def research_corpus_digest(self):
        return digest(
            {
                "profile": "engineering-source-only-v1",
                "sources": [r.to_dict() for r in self.source_inventory],
            }
        )


def validate_engineering_task(task, campaign, source_root):
    grant = engineering_grant_identity(campaign)
    if (
        task.family
        not in (
            {"engineering", "wind"}
            if isinstance(campaign, EngineeringCallbackCampaignSpec)
            else {"engineering"}
        )
        or task.candidate_digests != grant["candidates"]
        or task.partition_digest != grant["partition_digest"]
        or task.outcome_digest != grant["acceptance_digest"]
    ):
        raise StoreError("engineering task/model/scenario/outcome identity differs")
    verify_sources(
        campaign.execution,
        source_root,
        additional_entrypoints=(campaign.native.entrypoint,),
    )


def validate_engineering_recipe(campaign, recipe, plan):
    if recipe.kind == "expert":
        raise StoreError("expert engineering route needs a separately admitted executor")
    if recipe.numerical_recipe_digest != engineering_recipe_identity(campaign):
        raise StoreError("engineering numerical recipe differs")
    expected = engineering_grant_identity(campaign)
    if any(getattr(recipe.scientific_grant, k) != v for k, v in expected.items()):
        raise StoreError("engineering scientific grant differs")
    if (
        recipe.scientific_grant.hardware_digest != host_environment_identity()
        or recipe.scientific_grant.research_corpus_digest != plan.research_corpus_digest
        or recipe.scientific_grant.training_profile_digest is not None
    ):
        raise StoreError("engineering hardware, source corpus or training grant differs")
    if recipe.host:
        if (
            recipe.host.host_profile_digest != plan.host_configuration_digest
            or recipe.host.model != "scripted"
            or recipe.host.version != "scripted-1.0"
            or recipe.host.permissions_digest != plan.host_permissions_digest
            or recipe.host.aggregate_host_invocations > plan.worker_limits.max_invocations
        ):
            raise StoreError("engineering host profile/allowance differs")
        templates = template_digests(
            "single_agent" if recipe.kind == "single_agent" else "four_role"
        )
        if any(r.prompt_digest != templates[r.role] for r in recipe.roles):
            raise StoreError("engineering role templates differ")


class ScriptedEngineeringCoordinator(ScriptedCoordinator):
    def __init__(self, store, plan: ScriptedEngineeringPlan, source_root, *, fault=None):
        self.store, self.plan, self.source_root = store, plan, checked_directory(source_root)
        self.runtime = UtilityController(store)
        self.fault = fault or (lambda stage: None)
        self._resume_scenarios = False
        if plan.runtime_identity != engineering_runtime_identity():
            raise StoreError("engineering interpreter/package environment differs from frozen plan")
        if plan.digest != store.spec.protocol_digest:
            raise StoreError("engineering protocol differs from frozen suite")
        routes, cells = plan.routes.expand(store.spec.tasks, store.spec.budgets)
        if routes != store.spec.routes or cells != store.spec.cells:
            raise StoreError("engineering execution matrix differs from frozen suite")
        if (
            plan.lock.sha256 != store.spec.lock_digest
            or digest([r.to_dict() for r in plan.source_inventory]) != store.spec.source_digest
        ):
            raise StoreError("engineering source or lock identity differs")
        for name in (
            "worker_seconds",
            "elapsed_seconds",
            "workspace_bytes",
            "transcript_bytes",
            "max_invocations",
            "max_tasks",
            "max_repairs",
        ):
            if getattr(plan.worker_limits, name) > getattr(plan.batch_limits, name):
                raise StoreError("engineering worker limits exceed child batch")
        self.campaigns = {t.task_id: t.campaign for t in plan.campaigns}
        if set(self.campaigns) != {t.task_id for t in store.spec.tasks}:
            raise StoreError("engineering campaigns do not cover the assigned tasks")
        tasks = {t.task_id: t for t in store.spec.tasks}
        for name, campaign in self.campaigns.items():
            task = tasks[name]
            validate_engineering_task(task, campaign, self.source_root)
        for row in plan.routes.task_routes:
            campaign = self.campaigns[row.task_id]
            recipe = row.recipe
            validate_engineering_recipe(campaign, recipe, plan)
        for group in store.spec.child_batches():
            calls = sum(
                self._recipe(cell).host.aggregate_host_invocations if self._recipe(cell).host else 0
                for cell in group
            )
            if calls > plan.batch_limits.max_invocations:
                raise StoreError("engineering child host allowance cannot cover its frozen group")

    def _scientific_allowance(self, cell):
        return self.campaigns[cell.task_id].scientific_starts

    def run(self, *, max_new_cells=None, resume_scenarios=False):
        if type(resume_scenarios) is not bool:
            raise ValueError("pending engineering continuation must be explicitly boolean")
        self._resume_scenarios = resume_scenarios
        try:
            return super().run(max_new_cells=max_new_cells)
        finally:
            self._resume_scenarios = False

    def _execute(self, batch, case_id, cell, *, recover=False):
        recipe = self._recipe(cell)
        paired = paired_engineering_spec(self.campaigns[cell.task_id], cell.seed)
        root = batch.root / "cases" / case_id
        root.mkdir(mode=0o700, exist_ok=True)
        checked_directory(root)
        input_path = root / "engineering-input.json"
        if input_path.exists():
            if confined_file(root, input_path.name).read_text() != paired.to_json():
                raise StoreError("original paired engineering input differs")
        else:
            if recover and any(r.case_id == case_id for r in batch.replay().reservations.values()):
                raise StoreError("original engineering work lacks its input binding")
            durable_write(input_path, paired.to_json().encode())
        self.fault("engineering_input_saved")
        executor = SupervisedEngineeringExecutor(
            paired.execution, batch, case_id, self.source_root, fault=self.fault
        )
        campaign_root = root / "engineering"
        if campaign_root.exists():
            controller = EngineeringCampaign(
                campaign_root, batch, executor=executor, fault=self.fault
            )
            if controller.spec != paired:
                raise StoreError("saved engineering campaign differs from paired input")
        else:
            if any(r.case_id == case_id for r in batch.replay().reservations.values()):
                raise StoreError("physical work lacks its original engineering controller")
            controller = EngineeringCampaign.create(
                campaign_root, paired, executor, fault=self.fault
            )
        original = controller.handle

        def handle(request, **kwargs):
            response = original(request, **kwargs)
            self.fault("engineering_scientific_response_saved")
            return response

        controller.handle = handle
        if recipe.host:
            route = "single_agent" if recipe.kind == "single_agent" else "four_role"
            worker = AgentRunSpec(
                "1.1" if route == "single_agent" else "1.0",
                "utility-engineering-" + cell.digest[:24],
                paired.name,
                digest(controller.identity),
                HostSelection("fake", "none", "scripted", "1.0"),
                template_digests(route),
                tuple(i["implementation_id"] for i in engineering_catalogue(paired)),
                policy_digest(route),
                self.plan.worker_limits,
                host_source_identity(),
                host_environment_identity(),
                "supplied",
                route,
            )
            if (root / "worker").exists():
                workers = WorkerStore(root / "worker")
                workers.require_identity(worker)
            else:
                if any(r.case_id == case_id for r in batch.replay().reservations.values()):
                    raise StoreError("original engineering work lacks its worker journal")
                workers = WorkerStore.create(root / "worker", worker)
            host = RoleBoundHost(
                self.store,
                batch,
                cell.digest,
                self.plan.routes,
                BatchScriptedHost(batch, case_id, route),
                templates={r.role: r.prompt_digest for r in recipe.roles},
            )
            broker = EngineeringBroker(
                controller,
                SerialScheduler(workers, host),
                suite_store=self.store,
                plan=self.plan.routes,
                cell_digest=cell.digest,
            )
            final = broker.advance(resume_scenarios=self._resume_scenarios if recover else False)
        else:
            final = run_engineering_recipe(
                controller,
                recipe.kind,
                resume_scenarios=self._resume_scenarios if recover else False,
            )
        if final["projection"].state != "selection_frozen" or batch.replay().pending:
            raise StoreError("engineering selection or physical evidence is unresolved")
        selection, artifacts = None, ()
        if final["selected"] is not None:
            selection, artifacts = archive_selected_state(
                self.store,
                batch,
                final["selected"],
                self.source_root,
                producer="trusted-scripted-engineering",
            )
        proof = batch.evidence(
            {
                "profile": self.plan.schema,
                "cell": cell.digest,
                "campaign": paired.digest,
                "selection": selection,
                "outcome": final["decision"].outcome,
                "decision": final["decision"].to_dict(),
                "native_reports": [r.digest for r in final["native_reports"]],
                "scientific_evaluations": len(final["evaluations"]),
            }
        )
        self.fault("engineering_selection_archived")
        batch.finish_case(case_id, "passed", (proof, *artifacts))
