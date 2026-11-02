"""Offline costs from caller-pinned coupled-load callback work receipts.

The callback's work record is trusted application evidence, not an OS proof.
Missing records and interrupted native attempts retain unknown totals. Permission,
case attempts, completed evaluations and actual starts are separate quantities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility.confirmation import read_selected_state
from autoengineering.utility.contracts import sha256
from autoengineering.utility.costs import CostRecord
from autoengineering.utility.outcomes import OutcomeSpec
from autoengineering.utility.scoring import ConfirmationGrant, _read, read_receipt, validate_grant
from examples.utility.engineering_load_scoring import LoadScorePolicy
from examples.utility.engineering_source_binding import read_binding, scorer_identity

WORK_DIRECTORY = "engineering-load-work"
COUNTER_SCOPE = "component _linearize invocations, including Newton linearization; not FLOPs"


@dataclass(frozen=True)
class CounterWork(Record):
    solver_iterations: int
    component_calls: int
    derivative_calls: int

    def _validate(self):
        if any(
            type(v) is not int or v < 0
            for v in (self.solver_iterations, self.component_calls, self.derivative_calls)
        ):
            raise ValueError("load work counters must be nonnegative integers")


@dataclass(frozen=True)
class LoadWorkReceipt(Record):
    schema: Literal["utility-trusted-load-work-v1"]
    grant_digest: str
    scorer_digest: str
    source_binding_digest: str
    policy_digest: str
    score_digest: str
    private_result_digest: str
    attempted_model_starts: int
    completed_model_starts: int
    total_inner_work: CounterWork | None
    known_completed_inner_work: CounterWork
    last_attempt_inner_work_unknown: bool
    task_admitted: Literal[False]
    private_boundary_qualified: Literal[False]
    os_deadline_qualified: Literal[False]
    aggregate_rss_qualified: Literal[False]
    automatic_retries: Literal[0]
    derivative_counter_scope: (
        Literal["component _linearize invocations, including Newton linearization; not FLOPs"]
        | None
    ) = None

    def _validate(self):
        for value in (
            self.grant_digest,
            self.scorer_digest,
            self.source_binding_digest,
            self.policy_digest,
            self.score_digest,
            self.private_result_digest,
        ):
            sha256(value)
        a, c = self.attempted_model_starts, self.completed_model_starts
        if type(a) is not int or type(c) is not int or not 1 <= a <= 24 or not 0 <= c <= a:
            raise ValueError("load work counts exceed supported case profile")
        if self.known_completed_inner_work.solver_iterations > 100 * c:
            raise ValueError("load work exceeds reserved solver allowance")
        if self.total_inner_work is not None:
            if (
                a != 24
                or c != 24
                or self.last_attempt_inner_work_unknown
                or self.known_completed_inner_work != self.total_inner_work
                or self.derivative_counter_scope != COUNTER_SCOPE
            ):
                raise ValueError("complete load work fields disagree")
        elif (
            c != a - 1
            or not self.last_attempt_inner_work_unknown
            or self.derivative_counter_scope is not None
        ):
            raise ValueError("failed load work must retain its unknown last attempt")


@dataclass(frozen=True)
class LoadCostRegistration(Record):
    schema: Literal["utility-load-cost-registration-v1"]
    binding_artifact: ArtifactRef
    callback_source_digest: str
    policy: LoadScorePolicy

    def _validate(self):
        sha256(self.callback_source_digest)

    @property
    def outcome(self):
        p = self.policy
        return OutcomeSpec(
            "engineering-outcome-v1",
            p.outcome,
            p.units,
            "minimize",
            "mean",
            digest({"kernel": p.scorer_source_digest, "aggregation": "uniform-24-mean"}),
        )

    @property
    def code_digest(self):
        return digest(
            {
                "schema": "utility-trusted-load-callback-v1",
                "source": self.callback_source_digest,
                "kernel_policy": self.policy.digest,
                "expected_model": self.policy.expected_model_digest,
                "outcome": self.outcome.digest,
            }
        )


def _charged_scope(store, grant, registration):
    if type(grant) is not ConfirmationGrant or not isinstance(registration, LoadCostRegistration):
        raise ValueError("load costs need a typed grant and pinned registration")
    state = store.replay()
    selected = validate_grant(store, grant, state["frozen"])
    fixed = read_binding(store, registration.binding_artifact)
    if (
        grant.scorer_digest != scorer_identity(fixed, registration.code_digest)
        or grant.partition_digest != fixed.partition_policy_digest
        or grant.outcome_digest != registration.outcome.digest
    ):
        raise ValueError("load cost source or scorer registration differs from grant")
    bound = read_selected_state(store.root, selected.selected_state)
    if (
        bound.model.digest != registration.policy.expected_model_digest
        or set(bound.configuration) != {"source_current"}
        or type(bound.configuration["source_current"]) not in (int, float)
        or not 0.01 <= bound.configuration["source_current"] <= 0.1
    ):
        raise ValueError("load cost model or selected current differs")
    cell = next(c for c in store.spec.cells if c.digest == grant.cell_digest)
    if cell.task_id != fixed.task_id or cell.regime != "fixed_evaluations":
        raise ValueError("load costs support the fixed-evaluation callback only")
    resources = {r.name: r for r in grant.resources}
    for name, limit in (("load_model_starts", 24), ("load_solver_iterations", 2400)):
        r = resources.get(name)
        if r is None or (r.units, r.limit, r.enforcement) != ("count", limit, "reservation"):
            raise ValueError("load cost grant lacks exact inner-work reservation")
    active = resources.get("active_time")
    if (
        active is None
        or (active.units, active.enforcement) != ("s", "reservation")
        or active.limit <= 0
    ):
        raise ValueError("load cost grant lacks active-time allocation")
    attempt = "confirmation-" + grant.cell_digest[:48]
    allocation, _ = state["attempts"].get(attempt, (None, None))
    if (
        allocation is None
        or allocation.phase != "confirmation"
        or allocation.child_digest != grant.digest
        or allocation.resources != grant.resources
    ):
        raise StoreError("load costs need the original charged grant")
    access = state["confirmation_accesses"].get(attempt)
    if (
        access is not None
        and _read(store.root, access, "confirmation-grant.json", ConfirmationGrant) != grant
    ):
        raise StoreError("load cost access differs from charged grant")
    receipt_id = state["confirmation_scores"].get(attempt)
    receipt = read_receipt(store.root, receipt_id) if receipt_id else None
    if receipt is not None and (
        receipt.grant_digest != grant.digest
        or receipt.access_digest != access
        or receipt.outcome_contract != registration.outcome
    ):
        raise StoreError("load cost score differs from charged grant")
    return fixed, access, receipt


def join_load_costs(store, grant, registration, *, work_artifact=None):
    """Project one original callback without scanning for or refreshing a proof.

    A supplied ArtifactRef must be pinned by the trusted evidence owner. Missing
    or changed supplied bytes are errors. Omitted proof means unknown work, even
    after a successful score. A durable work proof can retain completed work when
    the suite score commit was lost. It does not recover or publish a score.

    Full counters, known-completed subsets and reservations have distinct names.
    Do not add them together. These records also do not replace callback duration,
    OS/process receipts, CPU/RSS, human effort or provider costs. Combining these
    records with generic confirmation costs preserves those remaining unknowns.
    """
    fixed, access, receipt = _charged_scope(store, grant, registration)
    work = None
    if work_artifact is not None:
        if (
            not isinstance(work_artifact, ArtifactRef)
            or work_artifact.path != f"{WORK_DIRECTORY}/{grant.digest}.json"
            or work_artifact.media_type != "application/json"
            or work_artifact.producer != "engineering-load-work"
            or work_artifact.metadata
            or access is None
        ):
            raise ValueError("load cost proof role or active access differs")
        work = LoadWorkReceipt.from_json(
            read_bytes(store.root, work_artifact, max_bytes=65536).decode()
        )
        if (
            work.grant_digest != grant.digest
            or work.scorer_digest != grant.scorer_digest
            or work.source_binding_digest != fixed.digest
            or work.policy_digest != registration.policy.digest
        ):
            raise ValueError("load cost work is bound to another callback")
        if receipt is not None:
            if (
                work.score_digest != receipt.score.digest
                or ((work.total_inner_work is None) != (receipt.score.status == "model_failure"))
                or receipt.score.status not in ("success", "scientific_infeasible", "model_failure")
            ):
                raise ValueError("load cost work differs from committed score")
    total = work.total_inner_work if work else None
    known = work.known_completed_inner_work if work else None
    quantities = [
        ("load_model_start_reservations", 24),
        ("load_solver_iteration_reservations", 2400),
        ("load_case_attempts", work.attempted_model_starts if work else None),
        ("load_completed_evaluations", work.completed_model_starts if work else None),
        ("load_model_starts", 24 if total else None),
    ]
    for raw, resource in (
        ("solver_iterations", "solver_iterations"),
        ("component_calls", "component_calls"),
        ("derivative_calls", "component_linearize_calls"),
    ):
        quantities.extend(
            [
                ("load_" + resource, getattr(total, raw) if total else None),
                ("load_known_completed_" + resource, getattr(known, raw) if known else None),
            ]
        )
    # Stable physical identity prevents double charging after proof acquisition,
    # lost acknowledgments, changed ArtifactRef metadata or later score commits.
    return tuple(
        CostRecord(
            "load-cost-" + digest({"grant": grant.digest, "resource": name})[:48],
            grant.digest,
            "confirmation",
            name,
            "count",
            quantity,
            (grant.cell_digest,),
            (1.0,),
        )
        for name, quantity in quantities
    )
