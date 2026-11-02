"""Trusted development callback joining sealed sources to the coupled-load kernel.

No CLI or private-runtime registration. The fixed-evaluation profile reserves
inner work explicitly and reports it separately from its single callback start.
Whole-operation deadlines, aggregate RSS and fixed-total-cost use are unsupported.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.confirmation import read_selected_state
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.scoring import validate_grant
from examples.utility import engineering_source_binding as binding
from examples.utility import engineering_load_scoring as kernel
from examples.utility import engineering_load as load

WORK_DIRECTORY = "engineering-load-work"


def source_identity():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def outcome_contract(policy):
    return OutcomeSpec(
        "engineering-outcome-v1",
        policy.outcome,
        policy.units,
        "minimize",
        "mean",
        digest({"kernel": policy.scorer_source_digest, "aggregation": "uniform-24-mean"}),
    )


class TrustedLoadScorer:
    def __init__(
        self,
        store,
        binding_artifact,
        public_root,
        private_root,
        source_root,
        work_root,
        *,
        expected_model,
        policy,
    ):
        self.store = store
        self.binding_artifact = binding_artifact
        self.public_root = checked_directory(public_root)
        self.private_root = checked_directory(private_root)
        self.source_root = Path(source_root)
        self.work_root = checked_directory(work_root)
        if (
            any(
                self.work_root.is_relative_to(p) or p.is_relative_to(self.work_root)
                for p in (store.root, self.public_root, self.private_root)
            )
            or self.public_root.is_relative_to(self.private_root)
            or self.private_root.is_relative_to(self.public_root)
        ):
            raise ValueError("coupled callback data and work scopes must be separate")
        self.expected_model, self.policy = expected_model, policy
        if (
            not isinstance(policy, kernel.LoadScorePolicy)
            or policy.expected_model_digest != expected_model.digest
            or policy.scorer_source_digest != kernel.source_identity()
            or load.context(0.05, self.work_root, source_root=self.source_root).model
            != expected_model
        ):
            raise ValueError("coupled callback model or kernel identity differs")
        self.binding = binding.read_binding(store, binding_artifact)
        self.outcome_contract = outcome_contract(policy)
        self.code_digest = digest(
            {
                "schema": "utility-trusted-load-callback-v1",
                "source": source_identity(),
                "kernel_policy": policy.digest,
                "expected_model": expected_model.digest,
                "outcome": self.outcome_contract.digest,
            }
        )
        self.identity = binding.scorer_identity(self.binding, self.code_digest)

    def _scope(self, grant, model):
        if (
            self.policy.scorer_source_digest != kernel.source_identity()
            or self.code_digest
            != digest(
                {
                    "schema": "utility-trusted-load-callback-v1",
                    "source": source_identity(),
                    "kernel_policy": self.policy.digest,
                    "expected_model": self.expected_model.digest,
                    "outcome": self.outcome_contract.digest,
                }
            )
            or grant.scorer_digest != self.identity
            or grant.outcome_digest != self.outcome_contract.digest
            or model.sha256 != grant.model_digest
        ):
            raise ValueError("coupled callback registration, code or grant changed")
        state = self.store.replay()
        selected = validate_grant(self.store, grant, state["frozen"])
        cell = next(c for c in self.store.spec.cells if c.digest == grant.cell_digest)
        if cell.regime != "fixed_evaluations":
            raise ValueError("trusted coupled callback has no qualified fixed-total-cost boundary")
        bound = read_selected_state(self.store.root, selected.selected_state)
        if bound.model != self.expected_model or set(bound.configuration) != {"source_current"}:
            raise ValueError(
                "coupled callback selection differs from its fixed model and design interface"
            )
        current = bound.configuration["source_current"]
        if type(current) not in (int, float) or not 0.01 <= current <= 0.1:
            raise ValueError("coupled callback selected current outside supported domain")
        if load.context(current, self.work_root, source_root=self.source_root).model != bound.model:
            raise ValueError("coupled callback execution source changed")
        resources = {r.name: r for r in grant.resources}
        for name, limit in (("load_model_starts", 24), ("load_solver_iterations", 2400)):
            resource = resources.get(name)
            if resource is None or (resource.units, resource.enforcement, resource.limit) != (
                "count",
                "reservation",
                limit,
            ):
                raise ValueError("coupled callback lacks its exact reserved inner-work allowance")
        active = resources.get("active_time")
        if (
            active is None
            or active.units != "s"
            or active.enforcement != "reservation"
            or active.limit <= 0
        ):
            raise ValueError("coupled callback requires declared active-time allocation")
        return current

    def __call__(self, grant, model):
        current = self._scope(grant, model)
        rows = binding.open_for_confirmation(
            self.store,
            grant,
            self.binding_artifact,
            self.public_root,
            self.private_root,
            scorer_code_digest=self.code_digest,
        )
        root = self.work_root / grant.digest
        if root.exists() or root.is_symlink():
            raise ValueError("coupled callback work scope consumed")
        root.mkdir(mode=0o700)
        score = kernel.score_loads(
            current, rows, root, self.source_root, policy=self.policy, execution_digest=grant.digest
        )
        complete = root / "complete.json"
        if complete.exists():
            record = unique_json(complete.read_text())
            work = {
                "attempted_model_starts": record["attempted_model_starts"],
                "completed_model_starts": record["completed_model_starts"],
                "total_inner_work": record["inner_work"],
                "known_completed_inner_work": record["inner_work"],
                "last_attempt_inner_work_unknown": False,
                "derivative_counter_scope": record["derivative_counter_scope"],
            }
        else:
            record = unique_json((root / "failed.json").read_text())
            work = {
                "attempted_model_starts": record["attempted_model_starts"],
                "completed_model_starts": record["completed_model_starts"],
                "total_inner_work": None,
                "known_completed_inner_work": record["known_completed_inner_work"],
                "last_attempt_inner_work_unknown": True,
            }
        public = self.store.root / WORK_DIRECTORY
        if public.is_symlink():
            raise ValueError("coupled work receipt scope is a symlink")
        public.mkdir(mode=0o700, exist_ok=True)
        checked_directory(public)
        work.update(
            schema="utility-trusted-load-work-v1",
            grant_digest=grant.digest,
            scorer_digest=self.identity,
            source_binding_digest=self.binding.digest,
            policy_digest=self.policy.digest,
            score_digest=score.digest,
            private_result_digest=digest(record),
            task_admitted=False,
            private_boundary_qualified=False,
            os_deadline_qualified=False,
            aggregate_rss_qualified=False,
            automatic_retries=0,
        )
        durable_write(public / (grant.digest + ".json"), canonical_json(work).encode())
        return score
