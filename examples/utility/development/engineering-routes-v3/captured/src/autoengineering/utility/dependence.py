"""Public paired dependence evidence, bound to exact scored selections.

Custodians compute these aggregates inside their admitted scoring boundary. Offline
readers verify identities and decision coverage without opening private arrays.
This schema does not itself qualify a custodian or its execution boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

from autoengineering.campaign.serialization import Record
from .contracts import sha256
from .uncertainty import DependencePlan


@dataclass(frozen=True)
class PairedDependenceEvidence(Record):
    schema: Literal["utility-paired-dependence-v1"]
    route_cell_digest: str
    comparator_cell_digest: str
    route_score_digest: str
    comparator_score_digest: str
    policy_digest: str
    gain: float | None
    interval: tuple[float, float] | None
    status: Literal["estimated", "finite_scenario_summary", "insufficient_data"]

    def _validate(self):
        for identity in (self.route_cell_digest, self.comparator_cell_digest,
                         self.route_score_digest, self.comparator_score_digest, self.policy_digest):
            sha256(identity)
        if self.route_cell_digest == self.comparator_cell_digest:
            raise ValueError("dependence evidence needs distinct paired cells")
        if self.status == "estimated" and (self.gain is None or self.interval is None):
            raise ValueError("estimated dependence needs gain and interval")
        if self.status != "estimated" and self.interval is not None:
            raise ValueError("only estimated dependence may supply a population interval")
        if self.status == "finite_scenario_summary" and self.gain is None:
            raise ValueError("finite scenario summary needs a gain")
        if self.interval is not None and self.interval[0] > self.interval[1]:
            raise ValueError("dependence interval endpoints are reversed")


def bind_summary(policy, route, comparator, summary):
    """Bind a trusted aggregate from the registered resampler to public scores."""
    if summary.get("policy_digest") != policy.digest or summary.get("task_id") != policy.task_id:
        raise ValueError("resampling summary differs from frozen policy")
    if summary.get("units") != policy.units:
        raise ValueError("resampling summary units differ")
    prediction = policy.schema == "utility-prediction-uncertainty-v1"
    expected = "utility-prediction-interval-v1" if prediction else "utility-scenario-interval-v1"
    if summary.get("schema") != expected:
        raise ValueError("resampling summary schema differs")
    if prediction and summary.get("outcome") != policy.outcome:
        raise ValueError("resampling outcome differs")
    result = PairedDependenceEvidence("utility-paired-dependence-v1", route.cell_digest,
        comparator.cell_digest, route.score_digest, comparator.score_digest, policy.digest,
        summary.get("gain" if prediction else "mean_gain"),
        tuple(summary["interval"]) if summary.get("interval") is not None else None, summary["status"])
    return result


def validate_evidence(spec, plan, scores, dependence, evidence):
    """Reject mismatched, duplicate and unused evidence before drawing conclusions."""
    if dependence is None:
        if evidence:
            raise ValueError("dependence evidence requires its frozen policy")
        return {}, {}
    if not isinstance(dependence, DependencePlan) or dependence.digest != plan.dependence_policy_digest:
        raise ValueError("dependence policy differs from frozen analysis")
    policies = {policy.task_id: policy for policy in (*dependence.tasks, *dependence.scenarios)}
    tasks = {task.task_id: task for task in spec.tasks}
    if set(policies) != set(tasks):
        raise ValueError("dependence policy must cover exactly the assigned tasks")
    cells = {cell.digest: cell for cell in spec.cells}
    scored = {score.cell_digest: score for score in scores}
    contrasts = {(c.task_id, c.route_id, c.comparator_id): c for c in plan.contrasts}
    result = {}
    for item in evidence:
        route, comparator = cells.get(item.route_cell_digest), cells.get(item.comparator_cell_digest)
        if route is None or comparator is None or route.pair_key != comparator.pair_key:
            raise ValueError("dependence evidence is not an assigned repetition/scenario pair")
        contrast = contrasts.get((route.task_id, route.route_id, comparator.route_id))
        if contrast is None:
            raise ValueError("dependence evidence does not belong to a frozen contrast")
        policy = policies[route.task_id]
        if policy.digest != item.policy_digest or policy.units != contrast.units:
            raise ValueError("dependence evidence policy or units differ")
        if policy.schema == "utility-prediction-uncertainty-v1":
            if (policy.outcome != contrast.outcome or contrast.direction != "minimize"
                    or policy.partition_digest != tasks[route.task_id].partition_digest):
                raise ValueError("prediction dependence outcome, direction or partition differs")
            census = False
        else:
            if (policy.schema != "utility-scenario-uncertainty-v2"
                    or policy.partition_digest != tasks[route.task_id].partition_digest):
                raise ValueError("scenario dependence requires the frozen partition identity")
            if policy.direction != contrast.direction:
                raise ValueError("scenario dependence direction differs")
            census = policy.method == "fixed_scenario_census"
        if item.status == "finite_scenario_summary" and not census:
            raise ValueError("finite summary requires a frozen scenario census")
        if item.status == "estimated" and census:
            raise ValueError("fixed scenario census cannot provide a population interval")
        left, right = scored.get(route.digest), scored.get(comparator.digest)
        if (left is None or right is None or left.status != "success" or right.status != "success"
                or left.feasible is not True or right.feasible is not True
                or (left.score_digest, right.score_digest) != (
                    item.route_score_digest, item.comparator_score_digest)):
            raise ValueError("dependence evidence needs exact successful feasible score receipts")
        gain = right.value-left.value if contrast.direction == "minimize" else left.value-right.value
        if item.gain is not None and not math.isclose(item.gain, gain, rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("dependence gain differs from public paired outcomes")
        key = (route.digest, comparator.digest)
        if key in result:
            raise ValueError("duplicate paired dependence evidence")
        # Split the nominal family error allowance across the frozen uncertainty
        # sources, including every assigned pair in each contrast/regime.
        pairs = sum(c.task_id == route.task_id and c.regime == route.regime
                    and c.route_id == route.route_id for c in spec.cells)
        from .analysis import uncertainty_split
        required = 1-(1-contrast.confidence)/(uncertainty_split(plan)*len(plan.contrasts)*len(spec.budgets)*pairs)
        if not census and policy.confidence < required-1e-12:
            raise ValueError("dependence confidence does not cover the frozen decision family")
        result[key] = item
    return policies, result
