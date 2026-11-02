"""Preregistered task-specific paired analysis without models or private data.

Inputs are public scored receipts. Analysis never repairs missing outcomes or
combines unlike scientific units into a suite-wide score.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Literal

import numpy as np
from scipy.stats import t

from autoengineering.campaign.serialization import Record
from .contracts import UtilitySuiteSpec, identifier, sha256


@dataclass(frozen=True)
class ContrastSpec(Record):
    task_id: str
    route_id: str
    comparator_id: str
    outcome: str
    units: str
    direction: Literal["minimize", "maximize"]
    minimum_gain: float
    minimum_feasible_rate: float
    confidence: float
    interval: Literal["paired_student_t", "paired_percentile_bootstrap"]
    resamples: int
    seed: int
    multiplicity: Literal["single_prespecified", "bonferroni"]

    def _validate(self):
        for name in (self.task_id, self.route_id, self.comparator_id, self.outcome):
            identifier(name)
        if self.route_id == self.comparator_id:
            raise ValueError("contrast needs distinct routes")
        if self.minimum_gain < 0 or not 0 <= self.minimum_feasible_rate <= 1:
            raise ValueError("invalid useful gain or feasible-rate threshold")
        if not 0 < self.confidence < 1 or not 0 <= self.seed < 2**63:
            raise ValueError("invalid confidence or resampling seed")
        if not 100 <= self.resamples <= 100000:
            raise ValueError("resamples must be explicitly bounded between 100 and 100000")


@dataclass(frozen=True)
class AnalysisPlan(Record):
    schema: Literal["utility-analysis-v1"]
    contrasts: tuple[ContrastSpec, ...]
    missing_policy: Literal["complete_pairs_and_full_denominators"]
    dependence_policy_digest: str

    def _validate(self):
        sha256(self.dependence_policy_digest)
        keys = [(c.task_id, c.route_id, c.comparator_id) for c in self.contrasts]
        if not keys or len(set(keys)) != len(keys):
            raise ValueError("analysis needs unique contrasts")
        if len(keys) > 1 and any(c.multiplicity == "single_prespecified" for c in self.contrasts):
            raise ValueError("multiple contrasts require explicit multiplicity adjustment")


@dataclass(frozen=True)
class DependentAnalysisPlan(AnalysisPlan):
    """A new identity explicitly declares the combined scientific decision rule."""
    schema: Literal["utility-analysis-v2"]
    dependence_rule: Literal["all_paired_lower_bounds"] = "all_paired_lower_bounds"


@dataclass(frozen=True)
class EffortCriterion(Record):
    task_id: str
    route_id: str
    comparator_id: str
    scientific_noninferiority_margin: float
    minimum_seconds_saved: float

    def _validate(self):
        for name in (self.task_id, self.route_id, self.comparator_id):
            identifier(name)
        if self.scientific_noninferiority_margin < 0 or self.minimum_seconds_saved < 0:
            raise ValueError("effort criteria need nonnegative scientific and human-effort margins")


@dataclass(frozen=True)
class EffortAnalysisPlan(DependentAnalysisPlan):
    schema: Literal["utility-analysis-v3"]
    effort_policy_digest: str = field(kw_only=True)
    effort_criteria: tuple[EffortCriterion, ...] = field(kw_only=True)

    def _validate(self):
        super()._validate()
        sha256(self.effort_policy_digest)
        keys = [(c.task_id, c.route_id, c.comparator_id) for c in self.effort_criteria]
        if len(set(keys)) != len(keys) or set(keys) != {
                (c.task_id, c.route_id, c.comparator_id) for c in self.contrasts}:
            raise ValueError("effort criteria must cover exactly the frozen contrasts")


def read_analysis_plan(raw):
    from autoengineering.campaign.serialization import unique_json
    data = unique_json(raw)
    if not isinstance(data, dict):
        raise ValueError("analysis must be an exact record")
    kind = {"utility-analysis-v1": AnalysisPlan, "utility-analysis-v2": DependentAnalysisPlan,
            "utility-analysis-v3": EffortAnalysisPlan}.get(data.get("schema"))
    if kind is None:
        raise ValueError("unknown analysis schema")
    return kind.from_dict(data)


def uncertainty_split(plan):
    return 3 if isinstance(plan, EffortAnalysisPlan) else 2


@dataclass(frozen=True)
class ScoredCell(Record):
    cell_digest: str
    score_digest: str
    status: Literal["success", "scientific_infeasible", "model_failure", "timeout", "cancelled",
                    "infrastructure_failure", "no_eligible_model", "insufficient_data",
                    "not_attempted", "reconciliation_required"]
    outcome: str
    units: str
    value: float | None
    feasible: bool | None
    active_seconds: float | None
    reached_target: bool | None

    def _validate(self):
        sha256(self.cell_digest)
        sha256(self.score_digest)
        identifier(self.outcome)
        if self.active_seconds is not None and self.active_seconds < 0:
            raise ValueError("active duration must be nonnegative or unknown")
        if self.status == "success" and (self.value is None or self.feasible is None):
            raise ValueError("successful score needs finite scientific outcome and feasibility")
        if self.status != "success" and self.value is not None:
            raise ValueError("unsuccessful scores cannot be imputed objective values")


def paired_interval(differences, contrast: ContrastSpec, family_size=1):
    values = np.asarray(differences, dtype=float)
    if len(values) < 2:
        return None
    alpha = (1 - contrast.confidence) / family_size
    if contrast.interval == "paired_student_t":
        radius = float(t.ppf(1-alpha/2, len(values)-1) * np.std(values, ddof=1) / np.sqrt(len(values)))
        return [float(np.mean(values)-radius), float(np.mean(values)+radius)]
    rng = np.random.default_rng(contrast.seed)
    # Bounded memory: never allocate resamples times the full matrix.
    means = np.empty(contrast.resamples)
    for index in range(contrast.resamples):
        means[index] = np.mean(values[rng.integers(0, len(values), len(values))])
    return [float(v) for v in np.quantile(means, [alpha/2, 1-alpha/2])]


def analyze(spec: UtilitySuiteSpec, plan: AnalysisPlan, scores: tuple[ScoredCell, ...],
            *, shared_baselines=(), dependence=None, dependence_evidence=()) -> dict:
    if plan.digest != spec.analysis_digest:
        raise ValueError("analysis policy differs from frozen suite")
    assigned = {cell.digest: cell for cell in spec.cells}
    routes = {route.route_id for route in spec.routes}
    tasks = {task.task_id for task in spec.tasks}
    from .baselines import validate_shared_scores
    seen = {}
    for score in scores:
        if score.cell_digest not in assigned or score.cell_digest in seen:
            raise ValueError("score must reference a unique assigned cell")
        seen[score.cell_digest] = score
    validate_shared_scores(spec, scores, shared_baselines)
    from .dependence import validate_evidence
    policies, dependence_by_pair = validate_evidence(spec, plan, scores, dependence, dependence_evidence)
    if dependence is not None and not isinstance(plan, DependentAnalysisPlan):
        raise ValueError("combined dependence decisions require utility-analysis-v2")
    results = []
    for contrast in plan.contrasts:
        if contrast.task_id not in tasks or not {contrast.route_id, contrast.comparator_id} <= routes:
            raise ValueError("contrast references unknown task or route")
        for regime in (b.regime for b in spec.budgets):
            cells = [cell for cell in spec.cells if cell.task_id == contrast.task_id
                     and cell.regime == regime and cell.route_id in (
                         contrast.route_id, contrast.comparator_id)]
            pairs = {}
            for cell in cells:
                score = seen.get(cell.digest)
                if score and (score.outcome, score.units) != (contrast.outcome, contrast.units):
                    raise ValueError("scientific outcomes or units differ within contrast")
                pairs.setdefault(cell.pair_key, {})[cell.route_id] = score
            differences, raw_pairs, dependence_pairs = [], [], []
            counts = {route: {"assigned": 0, "successful_feasible": 0, "statuses": {},
                               "target_reached": 0, "target_censored": 0, "target_unknown": 0}
                      for route in (contrast.route_id, contrast.comparator_id)}
            for pair_key, pair in pairs.items():
                for route, score in pair.items():
                    summary = counts[route]
                    summary["assigned"] += 1
                    status = score.status if score else "missing_evidence"
                    summary["statuses"][status] = summary["statuses"].get(status, 0) + 1
                    summary["successful_feasible"] += int(bool(score and score.status == "success"
                                                              and score.feasible is True))
                    target = ("target_unknown" if score is None or score.reached_target is None
                              else "target_reached" if score.reached_target else "target_censored")
                    summary[target] += 1
                route, comparator = pair.get(contrast.route_id), pair.get(contrast.comparator_id)
                if all(s is not None and s.status == "success" and s.feasible is True
                       for s in (route, comparator)):
                    gain = comparator.value-route.value if contrast.direction == "minimize" else (
                        route.value-comparator.value)
                    if not math.isfinite(gain):
                        raise ValueError("paired gain overflowed finite numeric range")
                    differences.append(gain)
                    item = dependence_by_pair.get((route.cell_digest, comparator.cell_digest))
                    dependence_pairs.append(item)
                    raw_pairs.append({"repetition": pair_key[2], "scenario_digest": pair_key[3],
                                      "route_value": route.value, "comparator_value": comparator.value,
                                      "gain": gain})
            family_size = len(plan.contrasts)*len(spec.budgets)
            interval = paired_interval(differences, contrast, family_size*(
                uncertainty_split(plan) if isinstance(plan, DependentAnalysisPlan) else 1))
            missing = len(pairs)-len(differences)
            rates = {route: (summary["successful_feasible"]/summary["assigned"]
                             if summary["assigned"] else None) for route, summary in counts.items()}
            unresolved = any(s is None or s.status == "reconciliation_required"
                             for pair in pairs.values() for s in pair.values())
            if not unresolved and any(rate < contrast.minimum_feasible_rate for rate in rates.values()):
                verdict = "failed_confirmation"
            elif missing or interval is None:
                verdict = "inconclusive"
            elif interval[0] > contrast.minimum_gain:
                verdict = "scientific_gain_supported"
            elif interval[1] <= contrast.minimum_gain:
                verdict = "no_useful_gain_demonstrated"
            else:
                verdict = "inconclusive"
            repetition_verdict = verdict
            policy = policies.get(contrast.task_id)
            dependence_complete = (len(dependence_pairs) == len(pairs) and bool(dependence_pairs)
                                   and all(item is not None and item.status != "insufficient_data"
                                           for item in dependence_pairs))
            bounds = [item.interval[0] if item.interval else item.gain
                      for item in dependence_pairs if item is not None and item.gain is not None]
            if verdict != "failed_confirmation":
                if not isinstance(plan, DependentAnalysisPlan) or not dependence_complete:
                    verdict = "inconclusive"
                elif verdict == "scientific_gain_supported" and not all(
                        bound > contrast.minimum_gain for bound in bounds):
                    verdict = "inconclusive"
            results.append({"task_id": contrast.task_id, "regime": regime,
                            "route_id": contrast.route_id, "comparator_id": contrast.comparator_id,
                            "outcome": contrast.outcome, "units": contrast.units,
                            "assigned_pairs": len(pairs), "valid_pairs": len(differences),
                            "missing_pairs": missing, "route_counts": counts,
                            "successful_feasible_rates": rates, "pairs": raw_pairs,
                            "mean_gain": float(np.mean(differences)) if differences else None,
                            "interval": interval, "verdict": verdict,
                            "efficiency_verdict": "inconclusive",
                            "repetition_verdict": repetition_verdict,
                            "dependence_complete": dependence_complete,
                            "dependence_evidence": [item.to_dict() if item else None for item in dependence_pairs],
                            "scientific_claim_scope": (
                                "unresolved dependence scope" if policy is None else
                                "frozen finite scenarios" if policy.schema in ("utility-scenario-uncertainty-v1", "utility-scenario-uncertainty-v2")
                                and policy.method == "fixed_scenario_census" else "frozen task and sampled support"),
                            "uncertainty_scope": "repetition and observation/scenario uncertainty kept separate"})
    return {"schema": "utility-paired-analysis-v1", "suite_digest": spec.digest,
            "analysis_digest": plan.digest, "dependence_policy_digest": plan.dependence_policy_digest,
            "dependence_policy": dependence.to_dict() if dependence is not None else None,
            "assigned_cells": len(spec.cells),
            "scored_cells": len(scores), "physical_score_receipts": len({s.score_digest for s in scores}),
            "shared_baselines": [a.to_dict() for a in shared_baselines], "contrasts": results,
            "global_scientific_score": None}


def analyze_receipts(spec, plan, root, references, *, dependence=None, dependence_references=()):
    """Verify public score envelopes before analysis; no private source is opened."""
    from autoengineering.campaign.artifacts import read_bytes
    from autoengineering.campaign.serialization import unique_json

    scores, allocations = [], []
    for ref in references:
        envelope = unique_json(read_bytes(root, ref).decode())
        if not isinstance(envelope, dict) or envelope.get("suite_digest") != spec.digest:
            raise ValueError("public score suite identity differs")
        shared = envelope.get("schema") == "utility-shared-baseline-v1"
        fields = {"schema", "suite_digest", "score", "allocation"} if shared else {
            "schema", "suite_digest", "score"}
        if set(envelope) != fields or envelope["schema"] not in (
                "utility-public-score-v1", "utility-shared-baseline-v1"):
            raise ValueError("invalid public score envelope")
        score = envelope["score"]
        if not isinstance(score, dict) or "score_digest" in score:
            raise ValueError("score evidence identity comes from the pinned artifact")
        if shared:
            from .baselines import SharedBaseline
            if not isinstance(envelope["allocation"], dict) or "score_digest" in envelope["allocation"]:
                raise ValueError("baseline evidence identity comes from its pinned artifact")
            allocation = SharedBaseline.from_dict(envelope["allocation"] | {"score_digest": ref.sha256})
            allocations.append(allocation)
            if "cell_digest" in score:
                raise ValueError("shared baseline cells belong in their exclusive allocation")
            scores.extend(ScoredCell.from_dict(score | {"cell_digest": cell, "score_digest": ref.sha256})
                          for cell in allocation.cell_digests)
        else:
            scores.append(ScoredCell.from_dict(score | {"score_digest": ref.sha256}))
    from .dependence import PairedDependenceEvidence
    evidence = tuple(PairedDependenceEvidence.from_json(read_bytes(root, ref).decode())
                     for ref in dependence_references)
    result = analyze(spec, plan, tuple(scores), shared_baselines=tuple(allocations),
                     dependence=dependence, dependence_evidence=evidence)
    result["dependence_references"] = [ref.to_dict() for ref in dependence_references]
    result["score_references"] = [ref.to_dict() for ref in references]
    return result


def analyze_confirmation(store, plan, *, shared_baselines=(), dependence=None, dependence_references=()):
    """Analyze only journal-committed public scores after the complete barrier."""
    from dataclasses import replace
    from .confirmation import read_manifest
    from .scoring import read_receipt, ConfirmationGrant, _read

    state = store.replay()
    if state["frozen"] is None:
        raise ValueError("comparative analysis requires the complete selection barrier")
    from .baseline_execution import resolve_baseline_allocations
    shared_baselines = resolve_baseline_allocations(store, state, shared_baselines)
    scores = []
    for attempt, identity in state["confirmation_scores"].items():
        receipt = read_receipt(store.root, identity)
        access = state["confirmation_accesses"][attempt]
        grant = _read(store.root, access, "confirmation-grant.json", ConfirmationGrant)
        value = receipt.score
        scores.append(ScoredCell(grant.cell_digest, identity, value.status, value.outcome, value.units,
                                  value.value, value.feasible, None, None))
    selected = {c.cell_digest: c for c in read_manifest(store.root, state["frozen"]).cells}
    for allocation in shared_baselines:
        allocation.validate(store.spec)
        matches = [score for score in scores if score.score_digest == allocation.score_digest]
        if len(matches) != 1 or matches[0].cell_digest not in allocation.cell_digests:
            raise ValueError("baseline allocation needs one committed original score")
        allocation.validate_selections(selected)
        original = matches[0]
        reused_cells = set(allocation.cell_digests) - {original.cell_digest}
        if any(
            entry.cell_digest in reused_cells and entry.phase == "confirmation"
            for entry, _ in state["attempts"].values()
        ):
            raise ValueError("shared baseline cannot hide charged confirmation work")
        scores.extend(replace(original, cell_digest=cell) for cell in allocation.cell_digests
                      if cell != original.cell_digest)
    from autoengineering.campaign.artifacts import read_bytes
    from .dependence import PairedDependenceEvidence
    evidence = tuple(PairedDependenceEvidence.from_json(read_bytes(store.root, ref).decode())
                     for ref in dependence_references)
    result = analyze(store.spec, plan, tuple(scores), shared_baselines=shared_baselines,
                     dependence=dependence, dependence_evidence=evidence)
    result["dependence_references"] = [ref.to_dict() for ref in dependence_references]
    return result
