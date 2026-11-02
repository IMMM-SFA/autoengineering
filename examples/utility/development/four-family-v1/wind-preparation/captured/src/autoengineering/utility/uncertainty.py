"""Frozen segmented block resampling for paired prediction-error uncertainty.

This custodian-side function returns aggregate numbers only. It does not export
observations, residual vectors or bootstrap indices to workers or public reports.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import numpy as np

from autoengineering.campaign.serialization import Record, digest
from .contracts import identifier, sha256


@dataclass(frozen=True)
class PredictionUncertaintySpec(Record):
    schema: Literal["utility-prediction-uncertainty-v1"]
    task_id: str
    outcome: Literal["rmse"]
    units: str
    method: Literal["segmented_circular_moving_block"]
    block_length: int
    resamples: int
    confidence: float
    seed: int
    interval_seconds: int
    support_digest: str
    development_digest: str
    partition_digest: str
    minimum_blocks: int = 2

    def _validate(self):
        identifier(self.task_id)
        for identity in (self.support_digest, self.development_digest, self.partition_digest):
            sha256(identity)
        if self.block_length < 1 or self.interval_seconds < 1 or self.minimum_blocks < 2:
            raise ValueError("uncertainty requires positive blocks/time step and at least two blocks")
        if not 100 <= self.resamples <= 100000 or not 0 < self.confidence < 1 or not 0 <= self.seed < 2**63:
            raise ValueError("invalid bounded resampling count, confidence or seed")


@dataclass(frozen=True)
class DependencePlan(Record):
    schema: Literal["utility-dependence-v1"]
    tasks: tuple[PredictionUncertaintySpec, ...]
    scenarios: tuple[ScenarioUncertaintySpec | BoundScenarioUncertaintySpec, ...] = ()

    def _validate(self):
        names = [t.task_id for t in (*self.tasks, *self.scenarios)]
        if not names or len(set(names)) != len(names):
            raise ValueError("dependence plan needs unique task policies")


def support_digest(timestamps, mask, segments):
    return digest({"timestamps": list(timestamps), "mask": list(mask), "segments": list(segments)})


def _aligned_inputs(spec, observed, route, comparator, timestamps, mask, segments):
    arrays = tuple(np.asarray(value) for value in (observed, route, comparator))
    if not arrays or any(a.ndim != 1 or a.dtype.kind not in "fiu" for a in arrays):
        raise ValueError("prediction uncertainty requires aligned numeric vectors")
    size = len(arrays[0])
    if not size or any(len(a) != size for a in arrays) or any(len(v) != size for v in (timestamps, mask, segments)):
        raise ValueError("prediction uncertainty vectors/support are unaligned")
    if any(type(value) is not bool for value in mask) or any(type(s) is not str or not s for s in segments):
        raise ValueError("uncertainty mask and segment IDs need exact types")
    if support_digest(timestamps, mask, segments) != spec.support_digest:
        raise ValueError("uncertainty time support or mask differs from frozen policy")
    try:
        times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in timestamps]
        gaps = [(right-left).total_seconds() for left, right in zip(times, times[1:])]
    except (ValueError, TypeError, AttributeError):
        raise ValueError("uncertainty timestamps must be comparable ISO times") from None
    if any(gap <= 0 for gap in gaps):
        raise ValueError("uncertainty time axis must be strictly increasing")
    runs, current = [], []
    for index, keep in enumerate(mask):
        if keep and current and (segments[index] != segments[index-1]
                                 or gaps[index-1] != spec.interval_seconds):
            runs.append(np.asarray(current))
            current = []
        if keep:
            current.append(index)
        elif current:
            runs.append(np.asarray(current))
            current = []
    if current:
        runs.append(np.asarray(current))
    selected = np.asarray(mask, dtype=bool)
    if any(not np.isfinite(a[selected]).all() for a in arrays):
        raise ValueError("scored predictions/observations contain nonfinite values")
    return tuple(a.astype(float, copy=True) for a in arrays), selected, runs


def prediction_uncertainty(spec, observed, route, comparator, *, timestamps, mask, segments):
    """Positive gain is comparator RMSE minus route RMSE on the identical mask."""
    arrays, selected, runs = _aligned_inputs(spec, observed, route, comparator,
                                            timestamps, mask, segments)
    count = int(selected.sum())
    result = {"schema": "utility-prediction-interval-v1", "policy_digest": spec.digest,
              "task_id": spec.task_id, "outcome": "rmse", "units": spec.units,
              "scored_samples": count, "segments": len(runs), "block_length": spec.block_length,
              "resamples": spec.resamples, "confidence": spec.confidence,
              "gain": None, "interval": None, "status": "insufficient_data",
              "uncertainty_scope": "observation dependence; separate from algorithm repetitions"}
    if not count:
        return result
    observed, route, comparator = arrays
    with np.errstate(over="ignore", invalid="ignore"):
        route_squared = (route-observed)**2
        comparator_squared = (comparator-observed)**2
    if not np.isfinite(route_squared[selected]).all() or not np.isfinite(comparator_squared[selected]).all():
        raise ValueError("prediction uncertainty loss overflowed finite range")

    def gain(index):
        left, right = comparator_squared[index], route_squared[index]
        # Scale before summation to keep finite large squared losses finite.
        return float(np.sqrt(np.sum(left/len(left))) - np.sqrt(np.sum(right/len(right))))

    result["gain"] = gain(selected)
    if (any(len(run) < spec.block_length for run in runs)
            or sum(len(run)//spec.block_length for run in runs) < spec.minimum_blocks):
        return result
    rng = np.random.default_rng(spec.seed)
    draws = np.empty(spec.resamples)
    for repetition in range(spec.resamples):
        samples = []
        for run in runs:
            blocks = (len(run)+spec.block_length-1)//spec.block_length
            starts = rng.integers(0, len(run), blocks)
            offsets = (starts[:, None] + np.arange(spec.block_length)) % len(run)
            samples.append(run[offsets.ravel()[:len(run)]])
        draws[repetition] = gain(np.concatenate(samples))
    alpha = 1-spec.confidence
    result.update(status="estimated", interval=[float(v) for v in np.quantile(draws, [alpha/2, 1-alpha/2])])
    return result


@dataclass(frozen=True)
class ScenarioUncertaintySpec(Record):
    schema: Literal["utility-scenario-uncertainty-v1"]
    task_id: str
    units: str
    direction: Literal["minimize", "maximize"]
    scenario_ids: tuple[str, ...]
    method: Literal["fixed_scenario_census", "iid_paired_scenario_bootstrap"]
    sampling_basis: Literal["fixed_design_cases", "independent_scenario_sample"]
    independence_evidence_digest: str
    resamples: int
    confidence: float
    seed: int

    def _validate(self):
        identifier(self.task_id)
        if not self.scenario_ids or len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ValueError("scenario uncertainty needs unique ordered cases")
        for name in self.scenario_ids:
            identifier(name)
        sha256(self.independence_evidence_digest)
        if (self.method == "fixed_scenario_census") != (self.sampling_basis == "fixed_design_cases"):
            raise ValueError("scenario method must match its sampling design")
        if not 100 <= self.resamples <= 100000 or not 0 < self.confidence < 1 or not 0 <= self.seed < 2**63:
            raise ValueError("invalid scenario uncertainty count, confidence or seed")


@dataclass(frozen=True)
class BoundScenarioUncertaintySpec(ScenarioUncertaintySpec):
    """Confirmation policy binds the complete forcing/partition manifest."""
    schema: Literal["utility-scenario-uncertainty-v2"]
    partition_digest: str

    def _validate(self):
        super()._validate()
        sha256(self.partition_digest)


def scenario_uncertainty(spec, route, comparator, *, scenario_ids):
    """Summarize modeled case effects without manufacturing independent scenarios."""
    if tuple(scenario_ids) != spec.scenario_ids:
        raise ValueError("scenario identities differ from frozen uncertainty policy")
    if len(route) != len(scenario_ids) or len(comparator) != len(scenario_ids):
        raise ValueError("scenario outcomes are unaligned")
    result = {"schema": "utility-scenario-interval-v1", "policy_digest": spec.digest,
              "task_id": spec.task_id, "units": spec.units, "assigned_scenarios": len(scenario_ids),
              "valid_scenarios": 0, "mean_gain": None, "interval": None,
              "status": "insufficient_data", "uncertainty_scope": "scenario variation only"}
    valid = []
    for left, right in zip(route, comparator):
        if left is None or right is None:
            continue
        if type(left) not in (float, int) or type(right) not in (float, int):
            raise ValueError("scenario outcomes must be finite scalars or explicitly unavailable")
        value = right-left if spec.direction == "minimize" else left-right
        if not np.isfinite(value):
            raise ValueError("scenario gain is nonfinite")
        valid.append(value)
    result["valid_scenarios"] = len(valid)
    if valid:
        result["mean_gain"] = float(np.sum(np.asarray(valid)/len(valid)))
    if len(valid) != len(scenario_ids):
        return result
    if spec.method == "fixed_scenario_census":
        result["status"] = "finite_scenario_summary"
        result["uncertainty_scope"] = "fixed cases; no population uncertainty or independent replication"
        return result
    if len(valid) < 2:
        return result
    rng = np.random.default_rng(spec.seed)
    values = np.asarray(valid)
    draws = np.empty(spec.resamples)
    for index in range(spec.resamples):
        draws[index] = np.sum(values[rng.integers(0, len(values), len(values))]/len(values))
    alpha = 1-spec.confidence
    result.update(status="estimated", interval=[float(v) for v in np.quantile(draws, [alpha/2, 1-alpha/2])])
    return result
