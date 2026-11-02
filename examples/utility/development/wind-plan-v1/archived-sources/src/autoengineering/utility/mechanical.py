"""Registered mechanical role substitutions over unchanged campaign acceptance."""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.agents.broker import CampaignBroker
from autoengineering.agents.records import CandidateBrief, SuppliedConfiguration, ReviewFindings
from autoengineering.campaign.artifacts import put_bytes, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, canonical_json, digest, unique_json
from autoengineering.campaign.store import StoreError
from .routes import RoutePlan


def mechanism_identity(role):
    if role not in ("investigator", "implementer", "reviewer"):
        raise ValueError("mechanical role is unsupported")
    return digest({"profile": "supplied-mechanical-v1", "role": role,
                   "source": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})


def mechanical_output(role, summary, evidence_id):
    """Deterministic supplied-pool choices; no imports or worker-supplied code."""
    if role not in ("investigator", "implementer", "reviewer"):
        raise ValueError("mechanical role is unsupported")
    submitted = summary.get("submitted_handoff", {})
    if role == "investigator":
        tried = {(p["target"], p["implementation_id"]) for p in summary["proposed_interventions"]}
        item = next(p for p in summary["catalogue"] if (p["target"], p["implementation_id"]) not in tried)
        return CandidateBrief("mechanical-" + digest(item)[:24], item["target"], item["implementation_id"],
            "Evaluate the next supplied candidate in frozen catalogue order", "Apply the declared scientific checks",
            (evidence_id,), ())
    if role == "implementer":
        item = next(p for p in summary["catalogue"] if (p["target"], p["implementation_id"]) == (
            submitted["target"], submitted["implementation_id"]))
        return SuppliedConfiguration(submitted["id"], item["implementation_id"], item["parameters"], (evidence_id,))
    evaluation = next(e for e in summary["evaluations"] if e["id"] == submitted["evaluation_id"])
    checks = {c["name"]: c for c in evaluation["checks"]}
    missing = tuple(c["name"] for c in summary["mandatory_checks"] if c["name"] not in checks
                    or checks[c["name"]]["version"] != c["version"]
                    or checks[c["name"]]["status"] not in ("pass", "fail"))
    # A failed scientific check remains a controller veto. Mechanical review
    # merely confirms the coded checks were evaluated, including adverse ones.
    return ReviewFindings(submitted["proposal"]["id"], evaluation["id"], (evidence_id,), (), missing,
                          "stop" if missing else "proceed")


@dataclass(frozen=True)
class MechanicalClaim(Record):
    plan: ArtifactRef
    role: Literal["investigator", "implementer", "reviewer"]
    key: str
    context: ArtifactRef
    output: CandidateBrief | SuppliedConfiguration | ReviewFindings


def read_mechanical(root, identity):
    ref = reference(root, f"artifacts/{identity}/mechanical-step.json",
                    media_type="application/json", producer="mechanical-reader")
    if ref.sha256 != identity:
        raise StoreError("mechanical receipt changed")
    return MechanicalClaim.from_json(read_bytes(root, ref).decode())


def validate_mechanical(store, event, attempts, steps):
    allocation, status = attempts.get(event.attempt_id, (None, None))
    if status != "started" or (allocation.cell_digest, allocation.child_digest) != (
            event.cell_digest, event.child_digest):
        raise StoreError("mechanical step requires its active assigned child")
    claim = read_mechanical(store.root, event.result_digest)
    plan = RoutePlan.from_json(read_bytes(store.root, claim.plan).decode())
    routes, cells = plan.expand(store.spec.tasks, store.spec.budgets)
    if routes != store.spec.routes or cells != store.spec.cells:
        raise StoreError("mechanical plan differs from suite")
    cell = next(c for c in cells if c.digest == event.cell_digest)
    recipe = next(r.recipe for r in plan.task_routes if (r.task_id, r.route_id) == (cell.task_id, cell.route_id))
    if recipe.replacements.get(claim.role) != mechanism_identity(claim.role):
        raise StoreError("mechanical replacement is absent or unregistered")
    summary = unique_json(read_bytes(store.root, claim.context).decode())
    if mechanical_output(claim.role, summary, claim.context.sha256) != claim.output:
        raise StoreError("mechanical output differs from registered policy")
    key = (event.cell_digest, claim.role, claim.key)
    if key in steps or event.resources or event.phase != "selection":
        raise StoreError("mechanical step identity conflicts or allocates new resources")
    steps[key] = event.result_digest


@dataclass(frozen=True)
class MechanicalReply:
    output: CandidateBrief | SuppliedConfiguration | ReviewFindings
    invocation_id: None = None


class AblationBroker(CampaignBroker):
    """Reuse scientific transitions; replace exactly one supplied-role handoff."""
    def __init__(self, controller, scheduler, *, suite_store, plan, cell_digest):
        super().__init__(controller, scheduler)
        if controller.spec.confirmation.mode != "disabled":
            raise StoreError("suite ablations cannot expose child confirmation before the suite barrier")
        if self.store.spec.execution_mode != "supplied":
            raise StoreError("mechanical ablations support trusted supplied candidates only")
        from .role_host import RoleBoundHost
        host = scheduler.host
        if not isinstance(host, RoleBoundHost) or host.store.root != suite_store.root or host.cell_digest != cell_digest:
            raise StoreError("ablation broker requires the bound role host")
        cell = next(c for c in suite_store.spec.cells if c.digest == cell_digest)
        recipe = next(r.recipe for r in plan.task_routes if (r.task_id, r.route_id) == (cell.task_id, cell.route_id))
        if not recipe.kind.startswith("no_"):
            raise StoreError("ablation broker requires one frozen omitted role")
        if not controller.store.root.is_relative_to(host.batch.root / "cases"):
            raise StoreError("ablation campaign is outside assigned child")
        pool = tuple(dict.fromkeys((controller.spec.baseline.model.digest,
                                    *(s.model.digest for s in self.catalogue.values()))))
        grant = recipe.scientific_grant
        if (grant.candidates, grant.acceptance_digest, grant.partition_digest, grant.search_bounds_digest) != (
                pool, controller.spec.acceptance.digest, digest([d.to_dict() for d in controller.spec.data]),
                digest([i.to_dict() for i in controller.spec.interventions])):
            raise StoreError("ablation scientific grants differ from campaign")
        self.suite_store, self.plan, self.cell_digest = suite_store, plan, cell_digest
        self.host_binding, self.recipe = host, recipe
        self.omitted = recipe.kind.removeprefix("no_")
        if recipe.replacements[self.omitted] != mechanism_identity(self.omitted):
            raise StoreError("ablation replacement implementation differs from frozen recipe")

    def _role(self, role, key, question, *, validate=None, context=None, **kwargs):
        if role != self.omitted:
            return super()._role(role, key, question, validate=validate, context=context, **kwargs)
        store = self.suite_store
        with nullcontext() if store._locked else store.writer():
            state = store.replay()
            prior = state["mechanical_steps"].get((self.cell_digest, role, key))
            if prior:
                claim = read_mechanical(store.root, prior)
            else:
                self._require_time()
                summary = self.summary()
                if context is not None:
                    summary["submitted_handoff"] = context
                summary["mandatory_checks"] = [c.to_dict() for c in self.controller.spec.acceptance.checks if c.required]
                ref = put_bytes(store.root, canonical_json(summary).encode(), name="mechanical-context.json",
                                media_type="application/json", producer="trusted-mechanical")
                output = mechanical_output(role, summary, ref.sha256)
                reply = MechanicalReply(output)
                if validate is not None:
                    validate(reply)
                claim = MechanicalClaim(self.host_binding.plan_ref, role, key, ref, output)
                artifact = put_bytes(store.root, claim.to_json().encode(), name="mechanical-step.json",
                                     media_type="application/json", producer="trusted-mechanical")
                allocation = self.host_binding.allocation
                store.append(request_id="mechanical-" + digest({"cell": self.cell_digest,
                    "role": role, "key": key})[:48], operation="mechanical_step",
                    cell_digest=self.cell_digest, attempt_id=allocation.attempt_id,
                    child_digest=allocation.child_digest, result_digest=artifact.sha256)
            reply = MechanicalReply(claim.output)
            if validate is not None:
                validate(reply)
            return reply
