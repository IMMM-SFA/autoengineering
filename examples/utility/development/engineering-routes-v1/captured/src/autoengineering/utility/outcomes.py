"""Registered engineering outcomes with scenario checks and shared acceptance.

Registrations are trusted Python code. Configuration names a frozen registration,
never an expression. No observation vector is fabricated for engineering scores.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import hashlib
import inspect
from types import MappingProxyType
from typing import Callable, Literal

import numpy as np

from autoengineering.campaign.acceptance import CheckContext, CheckRegistry, decide, eligible
from autoengineering.campaign.records import CheckResult, EvaluationRecord
from autoengineering.campaign.serialization import Record, digest
from autoengineering.campaign.spec import CheckSpec
from .contracts import identifier, sha256


@dataclass(frozen=True)
class OutcomeSpec(Record):
    schema: Literal["engineering-outcome-v1"]
    name: str
    units: Literal["W", "kW", "Wh", "kWh", "GWh", "USD", "V", "A", "m", "mm/day", "m3/s"]
    direction: Literal["minimize", "maximize"]
    aggregation: Literal["mean", "sum", "minimum", "maximum"]
    evaluator_identity: str

    def _validate(self):
        identifier(self.name)
        sha256(self.evaluator_identity)


def evaluator_identity(function: Callable) -> str:
    """Bind callable source; dependency closure is separately bound by the suite."""
    return hashlib.sha256(inspect.getsource(function).encode()).hexdigest()


@dataclass(frozen=True)
class EngineeringAcceptance(Record):
    schema: Literal["engineering-acceptance-v1"]
    outcomes: tuple[OutcomeSpec, ...]
    primary_metric: str
    minimum_gain: float
    secondary_limits: Mapping[str, float]
    checks: tuple[CheckSpec, ...]

    def _validate(self):
        names = tuple(o.name for o in self.outcomes)
        if not names or len(set(names)) != len(names) or self.primary_metric not in names:
            raise ValueError("outcomes need unique names and a declared primary")
        if self.minimum_gain < 0 or any(v < 0 for v in self.secondary_limits.values()):
            raise ValueError("gain and degradation limits must be nonnegative")
        if set(self.secondary_limits) != set(names) - {self.primary_metric}:
            raise ValueError("every secondary outcome needs an explicit degradation limit")
        if not self.checks or not any(c.required for c in self.checks):
            raise ValueError("engineering acceptance requires physical checks")
        if any(c.name == "secondary_outcomes" for c in self.checks):
            raise ValueError("secondary_outcomes is reserved for acceptance screening")
        if len({c.name for c in self.checks}) != len(self.checks):
            raise ValueError("duplicate engineering check")

    @property
    def direction(self):
        return next(o.direction for o in self.outcomes if o.name == self.primary_metric)

    @property
    def secondary_tolerances(self):
        # Generic secondary quantities are screened with their frozen directions
        # below, before the shared campaign decision function is called.
        return {}


@dataclass(frozen=True)
class ScenarioScore(Record):
    scenario_id: str
    forcing_digest: str
    values: Mapping[str, float | None]
    checks: tuple[CheckResult, ...]

    def _validate(self):
        identifier(self.scenario_id)
        sha256(self.forcing_digest)


@dataclass(frozen=True)
class EngineeringEvaluation(Record):
    rules_digest: str
    scenarios: tuple[ScenarioScore, ...]
    evaluation: EvaluationRecord

    def _validate(self):
        sha256(self.rules_digest)
        if not self.scenarios or len({s.scenario_id for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("scenario IDs must be nonempty and unique")


def aggregate(values, method):
    if any(v is None for v in values):
        return None
    function = {"mean": np.mean, "sum": np.sum, "minimum": np.min, "maximum": np.max}[method]
    with np.errstate(over="ignore", invalid="ignore"):
        result = float(function(values))
    return result if np.isfinite(result) else None


def scenario_checks(scores, specs):
    results = []
    for spec in specs:
        items = [next((c for c in s.checks if c.name == spec.name), None) for s in scores]
        passed = all(c is not None and c.status == "pass" and c.version == spec.version
                     and c.scope == spec.scope and c.required == spec.required for c in items)
        results.append(CheckResult(spec.name, spec.version, "pass" if passed else "fail",
                                   spec.required, spec.scope, None, None,
                                   "Every declared scenario must satisfy the check", ()))
    return tuple(results)


def copied_context(context):
    arrays = {}
    for name, source in context.outputs.items():
        value = np.array(source, copy=True)
        value.setflags(write=False)
        arrays[name] = value
    forcing = {}
    for name, source in context.forcing.items():
        value = np.array(source, copy=True)
        value.setflags(write=False)
        forcing[name] = value
    return CheckContext(MappingProxyType(arrays), MappingProxyType(forcing),
                        MappingProxyType(dict(context.parameters)))


class OutcomeRegistry:
    def __init__(self, registrations: Mapping[str, Callable]):
        self.registrations = MappingProxyType(dict(registrations))

    def evaluate(self, rules: EngineeringAcceptance, contexts: Mapping[str, CheckContext],
                 checks: CheckRegistry, template: EvaluationRecord) -> EngineeringEvaluation:
        functions = {}
        # Resolve all identities before any scoring callback is entered.
        for outcome in rules.outcomes:
            function = self.registrations.get(outcome.name)
            if function is None or evaluator_identity(function) != outcome.evaluator_identity:
                raise ValueError("engineering evaluator registration is absent or changed")
            functions[outcome.name] = function
        if not contexts:
            raise ValueError("scenario evaluation requires declared contexts")
        scores = []
        for scenario_id, context in contexts.items():
            values = {}
            for name, function in functions.items():
                try:
                    raw = function(copied_context(context))
                    value = float(raw) if type(raw) in (int, float) else None
                    values[name] = value if value is not None and np.isfinite(value) else None
                except Exception:
                    values[name] = None
            results = tuple(checks.evaluate(spec, copied_context(context)) for spec in rules.checks)
            forcing_identity = {}
            for name, source in context.forcing.items():
                array = np.asarray(source)
                if array.dtype.kind not in "biuf" or not np.isfinite(array).all():
                    raise ValueError("scenario forcing must be finite numeric arrays")
                forcing_identity[name] = {"shape": list(array.shape), "dtype": array.dtype.str,
                                          "sha256": hashlib.sha256(array.tobytes()).hexdigest()}
            scores.append(ScenarioScore(scenario_id, digest(forcing_identity), values, results))
        metrics = {o.name: aggregate([s.values[o.name] for s in scores], o.aggregation)
                   for o in rules.outcomes}
        result = replace(template, metrics=metrics, checks=scenario_checks(scores, rules.checks),
                         provenance=dict(template.provenance) | {"engineering_rules": rules.digest})
        return EngineeringEvaluation(rules.digest, tuple(scores), result)


def engineering_decision(baseline, alternatives, rules: EngineeringAcceptance):
    """Use campaign eligibility/ranking after direction-aware secondary screening."""
    records = (baseline, *alternatives)
    for record in records:
        if record.rules_digest != rules.digest:
            raise ValueError("engineering rules identity mismatch")
        if tuple((s.scenario_id, s.forcing_digest) for s in record.scenarios) != tuple(
                (s.scenario_id, s.forcing_digest) for s in baseline.scenarios):
            raise ValueError("engineering scenarios differ")
        expected = {o.name: aggregate([s.values.get(o.name) for s in record.scenarios], o.aggregation)
                    for o in rules.outcomes}
        if dict(record.evaluation.metrics) != expected or record.evaluation.checks != scenario_checks(
                record.scenarios, rules.checks):
            raise ValueError("engineering aggregate differs from saved scenario evidence")
    base = baseline.evaluation
    candidates = []
    base_ok = eligible(base, rules) and all(v is not None for v in base.metrics.values())
    for record in alternatives:
        candidate = record.evaluation
        passed = all(v is not None for v in candidate.metrics.values())
        if passed and base_ok:
            for outcome in rules.outcomes:
                if outcome.name not in rules.secondary_limits:
                    continue
                sign = 1 if outcome.direction == "minimize" else -1
                degradation = sign * (candidate.metrics[outcome.name] - base.metrics[outcome.name])
                passed &= degradation <= rules.secondary_limits[outcome.name]
        if not passed:
            candidate = replace(candidate, checks=(*candidate.checks, CheckResult(
                "secondary_outcomes", "1", "fail", True, "selection", None, None,
                "Secondary outcome missing or degradation exceeds frozen allowance", ())))
        candidates.append(candidate)
    if not base_ok:
        base = replace(base, status="scientific_infeasible")
    return decide(base, tuple(candidates), rules)
