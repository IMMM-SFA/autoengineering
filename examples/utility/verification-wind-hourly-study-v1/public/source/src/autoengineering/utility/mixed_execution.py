"""Exposed prediction and engineering tasks under one frozen suite barrier."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Literal

from autoengineering.agents.identity import host_environment_identity
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import Record, digest
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.store import StoreError, checked_directory
from .contracts import identifier, sha256
from .controller import UtilityController
from .engineering_execution import (
    ScriptedEngineeringPlan,
    ScriptedEngineeringCoordinator,
    TaskEngineeringCampaign,
    engineering_runtime_identity,
    validate_engineering_task,
    validate_engineering_recipe,
)
from .execution import (
    ScriptedCoordinator, validate_prediction_inputs, validate_prediction_recipe,
    validate_prediction_training_task,
)


@dataclass(frozen=True)
class TaskPredictionCampaign(Record):
    task_id: str
    campaign: CampaignSpec

    def _validate(self):
        identifier(self.task_id)


@dataclass(frozen=True)
class ScriptedMixedPlan(ScriptedEngineeringPlan):
    schema: Literal["utility-scripted-mixed-v1"]
    campaigns: tuple[TaskPredictionCampaign | TaskEngineeringCampaign, ...]

    def _validate(self):
        sha256(self.runtime_identity)
        if not any(isinstance(t, TaskPredictionCampaign) for t in self.campaigns) or not any(
            isinstance(t, TaskEngineeringCampaign) for t in self.campaigns
        ):
            raise ValueError("mixed plan requires prediction and engineering campaigns")
        if len({t.task_id for t in self.campaigns}) != len(self.campaigns):
            raise ValueError("mixed plan requires unique task campaigns")
        if not self.source_inventory or len({r.path for r in self.source_inventory}) != len(
            self.source_inventory
        ):
            raise ValueError("mixed plan requires a unique complete source inventory")
        for task in self.campaigns:
            if isinstance(task, TaskEngineeringCampaign):
                execution = task.campaign.execution
                if (
                    execution.schema
                    not in ("utility-engineering-execution-v2", "utility-engineering-execution-v3")
                    or execution.sources != self.source_inventory
                    or execution.lock != self.lock
                ):
                    raise ValueError(
                        "engineering campaign differs from shared v2 source/lock closure"
                    )
            else:
                lock = task.campaign.provenance.environment_lock
                if (lock.path, lock.sha256, lock.size_bytes) != (
                    self.lock.path,
                    self.lock.sha256,
                    self.lock.size_bytes,
                ):
                    raise ValueError("prediction campaign differs from shared lock")

    @property
    def host_configuration_digest(self):
        return digest(
            {
                "profile": "scripted-mixed-v1",
                "worker_limits": self.worker_limits.to_dict(),
                "worker_tools": "none",
            }
        )


class ScriptedMixedCoordinator(ScriptedEngineeringCoordinator):
    def __init__(self, store, plan: ScriptedMixedPlan, source_root, *, fault=None):
        self.store, self.plan, self.source_root = store, plan, checked_directory(source_root)
        self.runtime = UtilityController(store)
        self.fault = fault or (lambda stage: None)
        self._resume_scenarios = False
        if plan.runtime_identity != engineering_runtime_identity():
            raise StoreError("mixed interpreter/package environment differs from frozen plan")
        from .baseline_selection import execution_protocol_digest
        if plan.digest != execution_protocol_digest(store.spec):
            raise StoreError("mixed protocol differs from frozen suite")
        routes, cells = plan.routes.expand(store.spec.tasks, store.spec.budgets)
        if routes != store.spec.routes or cells != store.spec.cells:
            raise StoreError("mixed execution matrix differs from frozen suite")
        if (
            plan.lock.sha256 != store.spec.lock_digest
            or digest([r.to_dict() for r in plan.source_inventory]) != store.spec.source_digest
        ):
            raise StoreError("mixed source or lock identity differs")
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
                raise StoreError("mixed worker limits exceed child batch")
        self.campaigns = {t.task_id: t.campaign for t in plan.campaigns}
        self.prediction_tasks = {
            t.task_id for t in plan.campaigns if isinstance(t, TaskPredictionCampaign)
        }
        if set(self.campaigns) != {t.task_id for t in store.spec.tasks}:
            raise StoreError("mixed campaigns do not cover the assigned tasks")
        for task in store.spec.tasks:
            campaign = self.campaigns[task.task_id]
            if task.task_id not in self.prediction_tasks:
                validate_engineering_task(task, campaign, self.source_root)
                continue
            validate_prediction_inputs(campaign, self.source_root)
            snapshots = tuple(CampaignController.supplied_snapshots(SimpleNamespace(spec=campaign)))
            for ref in (
                *campaign.provenance.sources,
                campaign.baseline.system,
                *campaign.baseline.model.source_bundle,
                *(ref for snapshot in snapshots for ref in snapshot.model.source_bundle),
            ):
                read_bytes(self.source_root, ref)
            pool = tuple(
                dict.fromkeys(
                    (
                        campaign.baseline.model.digest,
                        *(s.model.digest for s in snapshots),
                    )
                )
            )
            if (
                task.family not in ("hydrology", "solar")
                or task.candidate_digests != pool
                or task.partition_digest != digest([d.to_dict() for d in campaign.data])
                or task.outcome_digest != campaign.acceptance.digest
            ):
                raise StoreError("prediction task/model/partition/outcome identity differs")
            validate_prediction_training_task(task, campaign)
        from .baseline_selection import validate_selection_campaign
        for task_id, campaign in self.campaigns.items():
            validate_selection_campaign(store.spec, task_id, campaign)
        for row in plan.routes.task_routes:
            campaign, recipe = self.campaigns[row.task_id], row.recipe
            if row.task_id not in self.prediction_tasks:
                validate_engineering_recipe(campaign, recipe, plan)
                continue
            validate_prediction_recipe(campaign, recipe, plan)
            if (
                recipe.scientific_grant.candidates
                != next(t for t in store.spec.tasks if t.task_id == row.task_id).candidate_digests
                or recipe.scientific_grant.hardware_digest != host_environment_identity()
                or recipe.scientific_grant.research_corpus_digest != plan.research_corpus_digest
                or (recipe.host and recipe.host.permissions_digest != plan.host_permissions_digest)
            ):
                raise StoreError(
                    "prediction catalogue, hardware, corpus or permissions grant differs"
                )
        for group in store.spec.child_batches():
            if (
                sum(
                    self._recipe(c).host.aggregate_host_invocations if self._recipe(c).host else 0
                    for c in group
                )
                > plan.batch_limits.max_invocations
            ):
                raise StoreError("mixed child host allowance cannot cover its frozen group")

    def _scientific_allowance(self, cell):
        executor = (
            ScriptedCoordinator
            if cell.task_id in self.prediction_tasks
            else ScriptedEngineeringCoordinator
        )
        return executor._scientific_allowance(self, cell)

    def _execute(self, batch, case_id, cell, *, recover=False):
        executor = (
            ScriptedCoordinator
            if cell.task_id in self.prediction_tasks
            else ScriptedEngineeringCoordinator
        )
        return executor._execute(self, batch, case_id, cell, recover=recover)
