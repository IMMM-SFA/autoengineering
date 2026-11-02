"""Permanent per-role permission reservations above existing batch host adapters."""
from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
import hashlib
from typing import Literal

from autoengineering.campaign.artifacts import put_bytes, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef, identifier
from autoengineering.campaign.serialization import Record, digest
from autoengineering.campaign.store import StoreError
from .routes import RoutePlan


@dataclass(frozen=True)
class RoleClaim(Record):
    plan: ArtifactRef
    role: Literal["orchestrator", "investigator", "implementer", "reviewer", "single_agent"]
    invocation_id: str
    call_identity: str

    def _validate(self):
        from .contracts import sha256
        identifier(self.invocation_id)
        sha256(self.call_identity)


def read_claim(root, identity):
    ref = reference(root, f"artifacts/{identity}/role-claim.json",
                    media_type="application/json", producer="role-reader")
    if ref.sha256 != identity:
        raise StoreError("role claim identity changed")
    return RoleClaim.from_json(read_bytes(root, ref).decode())


def validate_claim(store, event, attempts, role_counts, invocations):
    allocation, status = attempts.get(event.attempt_id, (None, None))
    if status != "started" or (allocation.cell_digest, allocation.child_digest) != (
            event.cell_digest, event.child_digest):
        raise StoreError("role dispatch requires the active assigned child")
    claim = read_claim(store.root, event.result_digest)
    plan = RoutePlan.from_json(read_bytes(store.root, claim.plan).decode())
    routes, cells = plan.expand(store.spec.tasks, store.spec.budgets)
    if routes != store.spec.routes or cells != store.spec.cells:
        raise StoreError("role plan differs from frozen suite")
    cell = next(cell for cell in cells if cell.digest == event.cell_digest)
    recipe = next(row.recipe for row in plan.task_routes
                  if (row.task_id, row.route_id) == (cell.task_id, cell.route_id))
    allowed = next((r for r in recipe.roles if r.role == claim.role), None)
    if allowed is None or recipe.host is None:
        raise StoreError("role omitted or unavailable in frozen route")
    invocation = (event.cell_digest, claim.invocation_id)
    if invocation in invocations:
        raise StoreError("role invocation already reserved; recovery must not redispatch")
    count = role_counts.get((event.cell_digest, claim.role), 0) + 1
    total = sum(value for (cell_id, _), value in role_counts.items() if cell_id == event.cell_digest) + 1
    parent_cap = next((c.limit for c in allocation.resources if c.name == "host_invocations"), 0)
    if count > allowed.maximum_calls or total > min(recipe.host.aggregate_host_invocations, parent_cap):
        raise StoreError("role or aggregate host allowance exhausted")
    if event.resources or event.phase != "selection":
        raise StoreError("role permission cannot allocate new parent resources")
    role_counts[event.cell_digest, claim.role] = count
    invocations.add(invocation)


class RoleBoundHost:
    """Refuse before delegation; retain permission charges across crashes.

    The delegate must still provide the existing physical host accounting and
    isolation boundary. This wrapper does not qualify a new host or grant tools.
    """

    def __init__(self, store, batch, cell_digest, plan: RoutePlan, delegate, *, templates):
        if batch._trusted_pin != batch.digest:
            raise StoreError("role wrapper requires a caller-pinned child batch")
        from .controller import UtilityController
        allocation, state = store.replay()["attempts"]["child-" + cell_digest[:48]]
        child, bindings = UtilityController(store)._child(allocation.child_digest)
        case_id = next(b.case_id for b in bindings if b.cell_digest == cell_digest)
        if child.digest != batch.digest or state != "started":
            raise StoreError("role host is outside its active assigned child")
        routes, cells = plan.expand(store.spec.tasks, store.spec.budgets)
        if routes != store.spec.routes or cells != store.spec.cells:
            raise StoreError("role plan differs from frozen suite")
        cell = next(c for c in cells if c.digest == cell_digest)
        recipe = next(r.recipe for r in plan.task_routes if (r.task_id, r.route_id) == (
            cell.task_id, cell.route_id))
        if recipe.host is None:
            raise StoreError("non-agent route cannot construct a role host")
        actual = delegate.capabilities()
        stable = batch.spec.capabilities
        expected_versions = {stable.executable_version,
                             f"{stable.executable_version}:batch:{batch.digest}:{case_id}"}
        if (actual.host, actual.auth_mode, actual.adapter_version) != (
                stable.host, stable.auth_mode, stable.adapter_version):
            raise StoreError("delegate capability profile differs from child")
        if (recipe.host.host_profile_digest != batch.spec.host_configuration_digest
                or recipe.host.model != batch.spec.host.requested_model
                or recipe.host.version != stable.executable_version
                or actual.executable_version not in expected_versions):
            raise StoreError("role host model/profile/version differs from child")
        if dict(templates) != {r.role: r.prompt_digest for r in recipe.roles}:
            raise StoreError("role prompt templates differ from frozen recipe")
        self.store, self.batch, self.delegate = store, batch, delegate
        self.allocation, self.cell_digest = allocation, cell_digest
        with nullcontext() if store._locked else store.writer():
            self.plan_ref = put_bytes(store.root, plan.to_json().encode(), name="route-plan.json",
                                      media_type="application/json", producer="utility-role-host")

    def capabilities(self):
        return self.delegate.capabilities()

    def _reserve(self, task, prompt, invocation_id, limits):
        identity = digest({"task": task.to_dict(), "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                           "limits": limits, "invocation_id": invocation_id})
        claim = RoleClaim(self.plan_ref, task.role, invocation_id, identity)
        with nullcontext() if self.store._locked else self.store.writer():
            state = self.store.replay()
            if (self.cell_digest, invocation_id) in state["role_invocations"]:
                raise StoreError("role invocation already reserved; reconciliation required")
            ref = put_bytes(self.store.root, claim.to_json().encode(), name="role-claim.json",
                            media_type="application/json", producer="utility-role-host")
            self.store.append(request_id="role-" + digest({"cell": self.cell_digest,
                              "invocation": invocation_id})[:48], operation="role_reserve",
                              cell_digest=self.cell_digest, attempt_id=self.allocation.attempt_id,
                              child_digest=self.allocation.child_digest, result_digest=ref.sha256)

    def invoke(self, task, prompt, *, invocation_id, timeout_seconds, max_output_bytes):
        self._reserve(task, prompt, invocation_id,
                      {"timeout_seconds": timeout_seconds, "max_output_bytes": max_output_bytes})
        return self.delegate.invoke(task, prompt, invocation_id=invocation_id,
                                    timeout_seconds=timeout_seconds, max_output_bytes=max_output_bytes)

    def invoke_supervised(self, task, prompt, context):
        self._reserve(task, prompt, context.invocation_id,
                      {"timeout_seconds": context.timeout_seconds, "max_output_bytes": context.max_output_bytes})
        if hasattr(self.delegate, "invoke_supervised"):
            return self.delegate.invoke_supervised(task, prompt, context)
        return self.delegate.invoke(task, prompt, invocation_id=context.invocation_id,
                                    timeout_seconds=context.timeout_seconds, max_output_bytes=context.max_output_bytes)

    def cancel(self, invocation_id):
        return self.delegate.cancel(invocation_id)
