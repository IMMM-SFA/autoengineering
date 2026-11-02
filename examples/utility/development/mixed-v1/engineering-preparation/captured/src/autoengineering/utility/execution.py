"""Trusted scripted development execution above campaign and suite journals.

Only supplied prediction campaigns over already exposed data are supported here.
Live hosts, generated code and independent confirmation are separate profiles.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from autoengineering.agents.batch import BatchCase, BatchSpec, PhysicalReservation, PhysicalObservation
from autoengineering.agents.batch_science import BatchCampaignController
from autoengineering.agents.broker import CampaignBroker
from autoengineering.agents.hosts.scripted import scripted_host
from autoengineering.agents.identity import host_source_identity, host_environment_identity
from autoengineering.agents.permissions import policy_digest
from autoengineering.agents.records import AgentRunSpec, HostSelection, ResourceLimits
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.agents.single_agent import SingleAgentBroker
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import read_bytes, put_bytes, confined_file
from autoengineering.campaign.acceptance import eligible
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.campaign.store import StoreError, durable_write
from .controller import UtilityController, CaseBinding
from .confirmation import SelectedState, SelectedCell, SelectionManifest
from .mechanical import AblationBroker
from .role_host import RoleBoundHost
from .routes import RoutePlan
from .contracts import identifier


@dataclass(frozen=True)
class TaskCampaign(Record):
    task_id: str
    specification: ArtifactRef

    def _validate(self):
        identifier(self.task_id)


@dataclass(frozen=True)
class ScriptedExecutionPlan(Record):
    schema: Literal["utility-scripted-development-v1"]
    routes: RoutePlan
    campaigns: tuple[TaskCampaign, ...]
    source_inventory: tuple[ArtifactRef, ...]
    lock: ArtifactRef
    worker_limits: ResourceLimits
    batch_limits: ResourceLimits
    purpose: Literal["exposed_development_only"] = "exposed_development_only"

    def _validate(self):
        if not self.campaigns or len({c.task_id for c in self.campaigns}) != len(self.campaigns):
            raise ValueError("execution plan needs unique task campaigns")
        if not self.source_inventory or len({r.path for r in self.source_inventory}) != len(self.source_inventory):
            raise ValueError("execution plan needs unique source closure")

    @property
    def host_configuration_digest(self):
        return digest({"profile": "scripted-supplied-v1", "worker_limits": self.worker_limits.to_dict()})


def campaign_recipe_identity(campaign):
    """Bind the supplied queue and inner numerical recipe, including its limits."""
    return digest({"profile": "campaign-supplied-queue-v1", "baseline": campaign.baseline.to_dict(),
                   "interventions": [item.to_dict() for item in campaign.interventions],
                   "calibration": campaign.calibration.to_dict() if campaign.calibration else None,
                   "workflow": campaign.workflow.to_dict(), "execution": campaign.execution.to_dict(),
                   "seed_rule": "paired-cell-seed-for-campaign-and-calibration"})


class BatchScriptedHost:
    """Physical batch receipts for deterministic supplied handoffs; no provider."""
    def __init__(self, batch, case_id, route):
        self.batch, self.case_id = batch, case_id
        self.delegate = scripted_host(route)

    def capabilities(self):
        return self.delegate.capabilities()

    def cancel(self, invocation_id):
        return self.delegate.cancel(invocation_id)

    def invoke(self, task, prompt, *, invocation_id, timeout_seconds, max_output_bytes):
        identity = digest({"case": self.case_id, "invocation": invocation_id, "task": task.to_dict()})
        reservation = PhysicalReservation("scripted-" + identity[:32], self.case_id, "host", identity,
            task.id, self.batch.clock(), timeout_seconds, len(prompt.encode()), max_output_bytes, 0)

        def observe(reservation, result):
            proof = self.batch.evidence({"profile": "scripted-supplied-v1", "task": task.id,
                "invocation": invocation_id, "role": task.role, "status": result.status})
            return PhysicalObservation(reservation.id, result.status, result.stop_verified,
                len(prompt.encode())+len(result.raw_output.encode()), result.usage, result.resolved_model,
                "absent", result.elapsed_seconds, (proof,))

        return self.batch.execute(reservation, lambda _: self.delegate.invoke(task, prompt,
            invocation_id=invocation_id, timeout_seconds=timeout_seconds, max_output_bytes=max_output_bytes), observe)


def archive_selected_state(store, batch, bound, source_root, *, producer="trusted-scripted"):
    """Archive verified sources and exact state, retaining child proof bytes."""
    model = bound.model
    for source in model.source_bundle:
        raw = read_bytes(source_root, source)
        destination = store.root / source.path
        if destination.exists() or destination.is_symlink():
            read_bytes(store.root, source)
        else:
            if any(part.is_symlink() for part in destination.parents):
                raise StoreError("selected source archive contains a symlink")
            destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            durable_write(destination, raw)
    model_ref = put_bytes(store.root, model.to_json().encode(), name="selected-model.json",
                         media_type="application/json", producer=producer)
    state_ref = put_bytes(store.root, bound.to_json().encode(), name="selected-state.json",
                         media_type="application/json", producer=producer)
    return ({"model": model_ref.to_dict(), "selected_state": state_ref.to_dict()},
            (batch.evidence(model.to_dict()), batch.evidence(bound.to_dict())))


def validate_prediction_inputs(campaign, source_root):
    if campaign.confirmation.mode != "disabled" or any(d.prior_exposure != "exposed" for d in campaign.data):
        raise StoreError("scripted development cannot access independent/private confirmation data")
    if any(adapter not in ("linear", "linear-fixed", "hydrology", "routing", "solar-pvlib")
           for adapter in campaign.execution.adapter_ids):
        raise StoreError("campaign requires an unsupported execution profile")
    for data in campaign.data:
        read_bytes(source_root, data.artifact)


def validate_prediction_recipe(campaign, recipe, plan):
    if recipe.numerical_recipe_digest != campaign_recipe_identity(campaign):
        raise StoreError("route numerical recipe differs from supplied campaign workflow")
    if recipe.kind == "expert":
        raise StoreError("expert workflow requires a separate admitted executor")
    if recipe.host and (recipe.host.host_profile_digest != plan.host_configuration_digest
            or recipe.host.model != "scripted" or recipe.host.version != "scripted-1.0"):
        raise StoreError("scripted host profile differs from frozen recipe")
    if recipe.host:
        expected_templates = template_digests("single_agent" if recipe.kind == "single_agent" else "four_role")
        if any(role.prompt_digest != expected_templates[role.role] for role in recipe.roles):
            raise StoreError("execution prompt templates differ from frozen recipe")
    if recipe.host and recipe.host.aggregate_host_invocations > plan.worker_limits.max_invocations:
        raise StoreError("worker allowance cannot cover role recipe")
    if (recipe.scientific_grant.acceptance_digest != campaign.acceptance.digest
            or recipe.scientific_grant.partition_digest != digest([d.to_dict() for d in campaign.data])
            or recipe.scientific_grant.search_bounds_digest != digest([i.to_dict() for i in campaign.interventions])):
        raise StoreError("scientific route grant differs from campaign")


class ScriptedCoordinator:
    def __init__(self, store, plan: ScriptedExecutionPlan, source_root, *, fault=None):
        self.store, self.plan, self.source_root = store, plan, Path(source_root)
        self.runtime = UtilityController(store)
        self.fault = fault or (lambda stage: None)
        if plan.digest != store.spec.protocol_digest:
            raise StoreError("execution protocol differs from frozen suite")
        routes, cells = plan.routes.expand(store.spec.tasks, store.spec.budgets)
        if routes != store.spec.routes or cells != store.spec.cells:
            raise StoreError("execution matrix differs from frozen suite")
        if plan.lock.sha256 != store.spec.lock_digest or digest(
                [r.to_dict() for r in plan.source_inventory]) != store.spec.source_digest:
            raise StoreError("execution source or lock identity differs")
        for ref in (*plan.source_inventory, plan.lock):
            read_bytes(self.source_root, ref)
        # All installed core Python sources must be in the declared closure.
        package = Path(__file__).resolve().parents[1]
        declared = {r.path: r for r in plan.source_inventory}
        for path in package.rglob("*.py"):
            relative = "src/autoengineering/" + str(path.relative_to(package))
            ref = declared.get(relative)
            if ref is None or read_bytes(self.source_root, ref) != path.read_bytes():
                raise StoreError("execution runtime source closure is incomplete or changed")
        if (plan.worker_limits.worker_seconds > plan.batch_limits.worker_seconds
                or plan.worker_limits.elapsed_seconds > plan.batch_limits.elapsed_seconds
                or plan.worker_limits.workspace_bytes > plan.batch_limits.workspace_bytes):
            raise StoreError("worker resource bounds exceed the child batch")
        self.campaigns = {}
        for task in plan.campaigns:
            campaign = CampaignSpec.from_json(read_bytes(self.source_root, task.specification).decode())
            validate_prediction_inputs(campaign, self.source_root)
            self.campaigns[task.task_id] = campaign
        if set(self.campaigns) != {t.task_id for t in store.spec.tasks}:
            raise StoreError("execution campaigns do not cover all assigned tasks")
        for row in plan.routes.task_routes:
            campaign, recipe = self.campaigns[row.task_id], row.recipe
            validate_prediction_recipe(campaign, recipe, plan)

    def _recipe(self, cell):
        return next(row.recipe for row in self.plan.routes.task_routes if (row.task_id, row.route_id) == (
            cell.task_id, cell.route_id))

    def _execute(self, batch, case_id, cell, *, recover=False):
        recipe = self._recipe(cell)
        root = batch.root / "cases" / case_id
        if not recover:
            root.mkdir(mode=0o700, exist_ok=True)
        campaign = self.campaigns[cell.task_id]
        if campaign.calibration:
            run = campaign.calibration.run
            campaign = replace(campaign, calibration=replace(campaign.calibration,
                run=replace(run, study=replace(run.study, seed=cell.seed))))
        campaign = replace(campaign, seed=cell.seed)
        path = root / "campaign-input.json"
        if recover:
            if confined_file(root, "campaign-input.json").read_bytes() != campaign.to_json().encode():
                raise StoreError("saved campaign input differs from paired execution")
            controller = BatchCampaignController.open(root / "campaign", batch=batch, case_id=case_id)
            if controller.spec != campaign:
                raise StoreError("saved campaign differs from paired execution")
            if (root / "worker").exists():
                projection = WorkerStore(root / "worker").replay()
                if projection.pending or projection.pending_preparations:
                    raise StoreError("pending worker requires explicit reconciliation")
            controller.reconcile_batch()
            if batch.replay().pending or controller.state().budget.unresolved_attempts:
                raise StoreError("physical work remains uncertain")
        else:
            durable_write(path, campaign.to_json().encode())
            controller = BatchCampaignController.create(path, self.source_root, root / "campaign",
                                                         batch=batch, case_id=case_id)
        original_handle = controller.service.handle

        def handle(request):
            response = original_handle(request)
            self.fault("scripted_scientific_response_saved")
            return response

        controller.service.handle = handle
        pool = tuple(dict.fromkeys((controller.spec.baseline.model.digest,
                                    *(s.model.digest for s in controller.supplied_snapshots()))))
        if pool != recipe.scientific_grant.candidates:
            raise StoreError("execution candidate catalogue differs from frozen shared pool")
        if recipe.kind == "baseline":
            controller.request("evaluate", {"candidate_id": "baseline", "mode": "fixed"}, request_id="baseline-only")
        elif recipe.kind == "conventional":
            controller.advance()
        else:
            route = "single_agent" if recipe.kind == "single_agent" else "four_role"
            identity = unique_json((controller.store.root / "identity.json").read_text())["scientific_identity"]
            worker = AgentRunSpec("1.1" if route == "single_agent" else "1.0",
                "utility-"+cell.digest[:24], campaign.name, identity, HostSelection("fake", "none", "scripted", "1.0"),
                template_digests(route), tuple(dict.fromkeys(i for item in campaign.interventions for i in item.implementation_ids)),
                policy_digest(route), self.plan.worker_limits, host_source_identity(), host_environment_identity(),
                "supplied", route)
            if recover:
                workers = WorkerStore(root / "worker")
                workers.require_identity(worker)
            else:
                workers = WorkerStore.create(root / "worker", worker)
            host = RoleBoundHost(self.store, batch, cell.digest, self.plan.routes,
                                 BatchScriptedHost(batch, case_id, route),
                                 templates={r.role: r.prompt_digest for r in recipe.roles})
            scheduler = SerialScheduler(workers, host)
            if recipe.kind.startswith("no_"):
                broker = AblationBroker(controller, scheduler, suite_store=self.store,
                                       plan=self.plan.routes, cell_digest=cell.digest)
            else:
                broker = (SingleAgentBroker if route == "single_agent" else CampaignBroker)(controller, scheduler)
            broker.advance()
        state = controller.state()
        if state.budget.unresolved_attempts:
            raise StoreError("scientific work remains uncertain")
        if recipe.kind != "baseline" and controller.store.replay().state != "completed":
            raise StoreError("scientific campaign is not terminal")
        selected = state.baseline if recipe.kind == "baseline" else next(
            (e for e in state.evaluations if state.decisions and e.id == state.decisions[-1].selected_id), None)
        selection, artifacts = None, []
        if selected is not None and eligible(selected, campaign.acceptance):
            candidate = next((s for s in state.snapshots if s.digest == selected.model_id), None)
            model = candidate.model if candidate is not None else campaign.baseline.model
            bound = SelectedState("utility-selected-state-v1", model, selected.configuration, selected, candidate)
            selection, selected_artifacts = archive_selected_state(
                self.store, batch, bound, controller.bundle)
            artifacts.extend(selected_artifacts)
        evidence = batch.evidence({"profile": self.plan.schema, "cell": cell.digest,
            "campaign": campaign.digest, "outcome": state.outcome, "selection": selection,
            "scientific_attempts": len(state.budget.attempts),
            "decision": state.decisions[-1].to_dict() if state.decisions else None})
        batch.finish_case(case_id, "passed", (evidence, *artifacts))

    def selection_manifest(self):
        """Reconstruct a reviewable barrier from finished child evidence only."""
        state = self.store.replay()
        selections = []
        for cell in self.store.spec.cells:
            attempt = "child-"+cell.digest[:48]
            entry = state["attempts"].get(attempt)
            if entry is None:
                selections.append(SelectedCell(cell.digest, "not_attempted", None, None, None,
                                                "No selection execution was attempted"))
                continue
            if entry[1] != "finished":
                raise StoreError("unresolved assigned work prevents selection projection")
            result = self.runtime.verify_result(attempt)
            child, _ = self.runtime._child(entry[0].child_digest)
            summaries = [unique_json(read_bytes(child.root, ArtifactRef.from_dict(ref)).decode())
                         for ref in result["case_result"]["evidence"]]
            summary = next(s for s in summaries if isinstance(s, dict) and s.get("profile") == self.plan.schema)
            chosen = summary["selection"]
            finish = next(e for e in state["events"] if e.attempt_id == attempt and e.operation == "finish")
            selections.append(SelectedCell(cell.digest, "selected" if chosen else "no_eligible_model",
                attempt, finish.result_digest, ArtifactRef.from_dict(chosen["model"]) if chosen else None,
                "Exposed scripted development selection", ArtifactRef.from_dict(chosen["selected_state"]) if chosen else None))
        return SelectionManifest("utility-selection-v2", self.store.spec.digest,
                                 self.store.spec.protocol_digest, tuple(selections))

    def _scientific_allowance(self, cell):
        return (1 if self._recipe(cell).kind == "baseline" else
                self.campaigns[cell.task_id].execution.max_executions)

    def run(self, *, max_new_cells=None):
        if max_new_cells is not None and (type(max_new_cells) is not int or max_new_cells < 0):
            raise ValueError("max_new_cells must be a nonnegative integer or absent")
        completed = 0
        for index, group in enumerate(self.store.spec.child_batches()):
            if max_new_cells is not None and completed >= max_new_cells:
                break
            cases = tuple(BatchCase("cell-"+cell.digest[:24], "comparison",
                next(r.configuration_digest for r in self.store.spec.routes if r.route_id == cell.route_id),
                self._recipe(cell).host.aggregate_host_invocations if self._recipe(cell).host else 0,
                self._scientific_allowance(cell))
                for cell in group)
            profile = BatchSpec("1.0", f"utility-batch-{index}", host_source_identity(), host_environment_identity(),
                HostSelection("fake", "none", "scripted", "1.0"), scripted_host().capabilities(),
                self.plan.host_configuration_digest, self.plan.batch_limits,
                sum(case.scientific_starts for case in cases), cases)
            bindings = tuple(CaseBinding(cell.digest, case.id) for cell, case in zip(group, cases))
            child = self.runtime.prepare_batch(profile, bindings)
            for cell in group:
                if max_new_cells is not None and completed >= max_new_cells:
                    break
                state = self.store.replay()
                allocation, status = state["attempts"]["child-"+cell.digest[:48]]
                if status == "finished":
                    self.runtime.verify_result(allocation.attempt_id)
                    continue
                if status == "started":
                    with self.store.writer():
                        child, bindings = self.runtime._child(child.root.name)
                        binding = next(b for b in bindings if b.cell_digest == cell.digest)
                        if binding.case_id not in child.replay().finished:
                            current = self.store.replay()
                            if current["cancelled"] or current["frozen"]:
                                raise StoreError("cancelled or frozen suite cannot resume execution")
                            if child.replay().active_case != binding.case_id:
                                raise StoreError("started cell lacks its original active case")
                            self._execute(child, binding.case_id, cell, recover=True)
                        self.runtime._finish(child, binding, allocation)
                    completed += 1
                    continue
                self.runtime.dispatch(child.root.name, cell.digest,
                    lambda batch, case_id: self._execute(batch, case_id, cell))
                completed += 1
        state = self.store.replay()
        return {"profile": self.plan.schema, "completed_this_call": completed,
                "finished_cells": sum(status == "finished" for _, status in state["attempts"].values()),
                "assigned_cells": len(self.store.spec.cells), "utility_verdict": "not_attempted"}
