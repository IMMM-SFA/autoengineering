"""Pinned public human-time logs with explicit scope closure and allocation.

The reader verifies declared logs and their public evidence. It cannot certify
that a person recorded every intervention. Human effort and physical costs remain
separate quantities, and missing logs never imply zero effort.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record
from .contracts import identifier, sha256


@dataclass(frozen=True)
class EffortScope(Record):
    scope_id: str
    phase: Literal["preparation", "research", "admission", "calibration", "training",
                   "selection", "confirmation", "reporting"]
    kind: Literal["common_setup", "route_work", "one_time_integration", "repeated_operation"]
    cell_digests: tuple[str, ...]
    allocation: tuple[float, ...]

    def _validate(self):
        identifier(self.scope_id)
        if not self.cell_digests or len(set(self.cell_digests)) != len(self.cell_digests):
            raise ValueError("effort scope needs unique assigned cells")
        for cell in self.cell_digests:
            sha256(cell)
        if len(self.allocation) != len(self.cell_digests) or any(not 0 <= v <= 1 for v in self.allocation):
            raise ValueError("effort allocations must align and be nonnegative")
        if abs(math.fsum(self.allocation)-1) > 1e-12:
            raise ValueError("exclusive effort allocations must sum to one")


@dataclass(frozen=True)
class EffortPlan(Record):
    schema: Literal["utility-effort-policy-v1"]
    scopes: tuple[EffortScope, ...]
    allowed_methods: tuple[Literal["timer", "self_reported"], ...]
    amortization_horizon: int
    primary_basis: Literal["first_use", "amortized"]

    def _validate(self):
        if not self.scopes or len({s.scope_id for s in self.scopes}) != len(self.scopes):
            raise ValueError("effort plan needs unique work scopes")
        if not self.allowed_methods or len(set(self.allowed_methods)) != len(self.allowed_methods):
            raise ValueError("effort policy needs unique allowed measurement methods")
        if not 1 <= self.amortization_horizon <= 100000:
            raise ValueError("effort amortization horizon must be explicitly bounded")


@dataclass(frozen=True)
class HumanTimeSource(Record):
    schema: Literal["utility-human-time-source-v1"]
    log_id: str
    actor_digest: str
    activity: Literal["setup", "review", "repair", "intervention", "operation", "integration", "research"]
    method: Literal["timer", "self_reported", "unknown"]
    started_at: float | None
    ended_at: float | None

    def _validate(self):
        identifier(self.log_id)
        sha256(self.actor_digest)
        if self.method == "unknown":
            if self.started_at is not None or self.ended_at is not None:
                raise ValueError("unknown human time cannot claim timestamps")
        elif (self.started_at is None or self.ended_at is None or self.started_at < 0
              or self.ended_at < self.started_at or not math.isfinite(self.ended_at-self.started_at)):
            raise ValueError("human time needs finite ordered UTC epoch timestamps")


@dataclass(frozen=True)
class HumanTimeLog(HumanTimeSource):
    schema: Literal["utility-human-time-v1"]
    scope_id: str
    evidence: ArtifactRef

    def _validate(self):
        super()._validate()
        identifier(self.scope_id)


@dataclass(frozen=True)
class EffortClosure(Record):
    schema: Literal["utility-effort-closure-v1"]
    scope_id: str
    status: Literal["closed", "incomplete"]
    logs: tuple[ArtifactRef, ...]
    evidence: ArtifactRef

    def _validate(self):
        identifier(self.scope_id)
        if len({r.sha256 for r in self.logs}) != len(self.logs):
            raise ValueError("duplicate effort log reference")
        if self.status == "closed" and not self.logs:
            raise ValueError("closed scope requires explicit logs, including measured zero effort")


@dataclass(frozen=True)
class EffortInputs(Record):
    schema: Literal["utility-effort-inputs-v1"]
    policy: ArtifactRef
    closures: tuple[ArtifactRef, ...]

    def _validate(self):
        if len({r.sha256 for r in self.closures}) != len(self.closures):
            raise ValueError("duplicate effort closure reference")


def read_effort(spec, root, inputs: EffortInputs, *, policy_digest):
    """Read frozen scopes and exclusively allocate verified public log durations."""
    policy = EffortPlan.from_json(read_bytes(root, inputs.policy).decode())
    if policy.digest != policy_digest:
        raise ValueError("effort policy differs from frozen analysis")
    assigned = {c.digest for c in spec.cells}
    scoped = {cell for scope in policy.scopes for cell in scope.cell_digests}
    if scoped != assigned:
        raise ValueError("effort scopes must cover exactly all assigned cells")
    scopes = {scope.scope_id: scope for scope in policy.scopes}
    closures, logs, sources, intervals, rows = {}, set(), set(), {}, []
    values = {cell: {"first_use_seconds": 0., "amortized_seconds": 0., "complete": True,
                     "timer_seconds": 0., "self_reported_seconds": 0., "unknown_logs": 0}
              for cell in assigned}
    for ref in inputs.closures:
        closure = EffortClosure.from_json(read_bytes(root, ref).decode())
        if closure.scope_id not in scopes or closure.scope_id in closures:
            raise ValueError("effort closure must match a unique frozen scope")
        read_bytes(root, closure.evidence)
        scope = scopes[closure.scope_id]
        closures[closure.scope_id] = closure
        for log_ref in closure.logs:
            log = HumanTimeLog.from_json(read_bytes(root, log_ref).decode())
            source = HumanTimeSource.from_json(read_bytes(root, log.evidence).decode())
            projected = {key: value for key, value in log.to_dict().items()
                         if key not in ("schema", "scope_id", "evidence")}
            if projected != {key: value for key, value in source.to_dict().items() if key != "schema"}:
                raise ValueError("human-time log differs from its original source record")
            if log.scope_id != closure.scope_id or log.log_id in logs or log.evidence.sha256 in sources:
                raise ValueError("duplicate or misplaced physical human-time evidence")
            logs.add(log.log_id)
            sources.add(log.evidence.sha256)
            if log.method != "unknown" and log.method not in policy.allowed_methods:
                raise ValueError("human-time method is not admitted by the frozen policy")
            seconds = None if log.method == "unknown" else log.ended_at-log.started_at
            if seconds is not None:
                intervals.setdefault(log.actor_digest, []).append((log.started_at, log.ended_at))
            for cell, share in zip(scope.cell_digests, scope.allocation):
                allocated = seconds*share if seconds is not None else None
                divisor = policy.amortization_horizon if scope.kind in ("common_setup", "one_time_integration") else 1
                amortized = allocated/divisor if allocated is not None else None
                rows.append({"log_id": log.log_id, "log_digest": log_ref.sha256, "source_digest": log.evidence.sha256,
                    "scope_id": scope.scope_id, "phase": scope.phase, "kind": scope.kind, "activity": log.activity, "method": log.method,
                    "actor_digest": log.actor_digest, "cell_digest": cell, "allocation": share,
                    "physical_seconds": seconds, "first_use_seconds": allocated, "amortized_seconds": amortized})
                value = values[cell]
                if allocated is None:
                    value["complete"] = False
                    value["unknown_logs"] += 1
                else:
                    value["first_use_seconds"] += allocated
                    value["amortized_seconds"] += amortized
                    value[log.method+"_seconds"] += allocated
        if closure.status != "closed":
            for cell in scope.cell_digests:
                values[cell]["complete"] = False
    for actor, windows in intervals.items():
        previous_end = -1.
        for start, end in sorted(windows):
            if start < previous_end and end > start:
                raise ValueError("human-time intervals overlap for the same actor")
            previous_end = max(previous_end, end)
    missing = sorted(set(scopes)-set(closures))
    for scope_id in missing:
        for cell in scopes[scope_id].cell_digests:
            values[cell]["complete"] = False
    for value in values.values():
        if not all(math.isfinite(v) for key, v in value.items() if key.endswith("_seconds")):
            raise ValueError("human effort totals overflowed finite range")
        if not value["complete"]:
            # Partial measured work is retained in rows, not reported as a total.
            value["first_use_seconds"] = value["amortized_seconds"] = None
    return {"schema": "utility-effort-accounting-v1", "policy_digest": policy.digest,
            "amortization_horizon": policy.amortization_horizon, "primary_basis": policy.primary_basis,
            "declared_scopes_complete": not missing and all(v["complete"] for v in values.values()),
            "missing_scopes": missing, "cells": values, "allocations": rows,
            "source_log_count": len(logs), "complete_physical_cost_evidence": False,
            "qualification": "Verified declared logs and scope closure; not an independent completeness audit"}


def analyze_effort(spec, plan, analysis, effort):
    """Evaluate the frozen human-effort claim, without claiming total-cost gains."""
    from copy import deepcopy
    from .analysis import EffortAnalysisPlan, paired_interval, uncertainty_split

    if not isinstance(plan, EffortAnalysisPlan) or effort["policy_digest"] != plan.effort_policy_digest:
        raise ValueError("human-effort decision requires its frozen analysis policy")
    if analysis["suite_digest"] != spec.digest or analysis["analysis_digest"] != plan.digest:
        raise ValueError("effort analysis differs from frozen scientific report")
    if set(effort["cells"]) != {cell.digest for cell in spec.cells}:
        raise ValueError("human-effort totals must cover every assigned cell")
    result = deepcopy(analysis)
    field = "first_use_seconds" if effort["primary_basis"] == "first_use" else "amortized_seconds"
    criteria = {(c.task_id, c.route_id, c.comparator_id): c for c in plan.effort_criteria}
    for row in result["contrasts"]:
        criterion = criteria[row["task_id"], row["route_id"], row["comparator_id"]]
        contrast = next(c for c in plan.contrasts if (c.task_id, c.route_id, c.comparator_id) == (
            row["task_id"], row["route_id"], row["comparator_id"]))
        paired = {}
        for cell in spec.cells:
            if cell.task_id == row["task_id"] and cell.regime == row["regime"] and cell.route_id in (
                    row["route_id"], row["comparator_id"]):
                paired.setdefault(cell.pair_key, {})[cell.route_id] = effort["cells"][cell.digest]
        gains, pairs = [], []
        for key, values in paired.items():
            route, comparator = values[row["route_id"]], values[row["comparator_id"]]
            if route["complete"] and comparator["complete"]:
                gain = comparator[field]-route[field]
                if not math.isfinite(gain):
                    raise ValueError("human-effort gain overflowed finite range")
                gains.append(gain)
                pairs.append({"repetition": key[2], "scenario_digest": key[3],
                              "route_seconds": route[field], "comparator_seconds": comparator[field],
                              "seconds_saved": gain})
        interval = paired_interval(gains, contrast, uncertainty_split(plan)*len(plan.contrasts)*len(spec.budgets))
        noninferior = (row["valid_pairs"] == row["assigned_pairs"] and row["interval"] is not None
            and row["interval"][0] >= -criterion.scientific_noninferiority_margin
            and row["dependence_complete"] and row["verdict"] != "failed_confirmation"
            and all((item["interval"][0] if item["interval"] else item["gain"]) >=
                    -criterion.scientific_noninferiority_margin for item in row["dependence_evidence"]))
        complete = len(gains) == row["assigned_pairs"]
        verdict = "inconclusive"
        if complete and noninferior and interval is not None:
            if interval[0] > criterion.minimum_seconds_saved:
                verdict = "efficiency_gain_supported"
            elif interval[1] <= criterion.minimum_seconds_saved:
                verdict = "no_useful_gain_demonstrated"
        row["efficiency_verdict"] = verdict
        row["efficiency_basis"] = "declared_logged_human_effort"
        row["effort"] = {"basis": effort["primary_basis"], "units": "person-s", "valid_pairs": len(gains),
            "assigned_pairs": row["assigned_pairs"], "pairs": pairs,
            "mean_seconds_saved": math.fsum(g/len(gains) for g in gains) if gains else None,
            "interval": interval, "scientific_noninferiority_established": bool(noninferior),
            "minimum_seconds_saved": criterion.minimum_seconds_saved,
            "scientific_noninferiority_margin": criterion.scientific_noninferiority_margin,
            "complete_total_cost_evidence": False,
            "claim_limit": "Declared logged scopes only; computational/monetary efficiency and unlogged human work unverified"}
    return result
