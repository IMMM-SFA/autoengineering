"""Declarative scalar geometry checks with durable evidence of zero model starts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from typing import Literal

from autoengineering.campaign.artifacts import read_bytes, confined_file
from autoengineering.campaign.records import CheckResult, EvaluationRecord
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.store import StoreError
from .contracts import identifier, sha256
from .outcomes import EngineeringEvaluation, ScenarioScore, scenario_checks


@dataclass(frozen=True)
class MinimumDistance(Record):
    id: str
    first: tuple[str, str]
    second: tuple[str, str]
    minimum: float
    units: Literal["m"] = "m"

    def _validate(self):
        identifier(self.id)
        if len(set((*self.first, *self.second))) != 4 or self.minimum <= 0:
            raise ValueError(
                "minimum distance needs two distinct coordinate pairs and positive bound"
            )
        for name in (*self.first, *self.second):
            identifier(name)

    def distance(self, configuration):
        return math.hypot(
            *(configuration[a] - configuration[b] for a, b in zip(self.first, self.second))
        )


@dataclass(frozen=True)
class PreflightRejection(Record):
    schema: Literal["utility-preflight-rejection-v1"]
    execution_digest: str
    binding_digest: str
    case_id: str
    action_digest: str
    distances: Mapping[str, float]
    violated: tuple[str, ...]

    def _validate(self):
        for value in (self.execution_digest, self.binding_digest, self.action_digest):
            sha256(value)
        identifier(self.case_id)
        if (
            not self.violated
            or len(set(self.violated)) != len(self.violated)
            or not set(self.violated) <= set(self.distances)
        ):
            raise ValueError("preflight rejection requires actual violated constraints")


def rejection(spec, binding_digest, case_id, action):
    """Pure numeric checks only. No model imports or source/data acquisition."""
    if not spec.preflight:
        return None
    spec.study.run.search_space.encode(action.config)
    distances = {rule.id: rule.distance(action.config) for rule in spec.preflight}
    violated = tuple(rule.id for rule in spec.preflight if distances[rule.id] < rule.minimum)
    if not violated:
        return None
    return PreflightRejection(
        "utility-preflight-rejection-v1",
        spec.digest,
        binding_digest,
        case_id,
        digest(action.to_dict()),
        distances,
        violated,
    )


def rejection_identity(spec, case_id, action):
    return digest(
        {
            "execution": spec.digest,
            "case": case_id,
            "action": action.to_dict(),
            "phase": "preflight",
        }
    )


def rejected_evaluation(spec, action, ref, *, model_id="supplied-engineering"):
    from .engineering_process import SupervisedEngineeringExecutor

    scores = []
    for scenario in spec.scenarios:
        checks = tuple(
            CheckResult(
                c.name,
                c.version,
                "unavailable",
                c.required,
                c.scope,
                None,
                None,
                "Parameter preflight rejected configuration before model dispatch",
                (ref,),
            )
            for c in spec.study.rules.checks
        )
        scores.append(
            ScenarioScore(
                scenario.scenario_id,
                SupervisedEngineeringExecutor._forcing_digest(scenario),
                {o.name: None for o in spec.study.rules.outcomes},
                checks,
            )
        )
    rules = spec.study.rules
    value = EvaluationRecord(
        action.id,
        model_id,
        action.config,
        "scientific_infeasible",
        {o.name: None for o in rules.outcomes},
        scenario_checks(scores, rules.checks),
        (),
        "development-fitting",
        action.id,
        0.0,
        {
            "engineering_rules": rules.digest,
            "executor": spec.digest,
            "preflight_rejection": ref.sha256,
        },
    )
    return EngineeringEvaluation(rules.digest, tuple(scores), value)


def verify_rejection(
    spec, binding_digest, batch, case_id, action, value, *, model_id="supplied-engineering"
):
    """Verify deterministic rejection and absence of conflicting physical work."""
    from .engineering_process import engineering_invocation_identity

    expected = rejection(spec, binding_digest, case_id, action)
    if expected is None or value.evaluation.status != "scientific_infeasible":
        return False
    directory = batch.root / "cases" / case_id / "engineering-processes"
    binding = unique_json(confined_file(directory, "execution.json").read_text())
    if digest(binding) != binding_digest or binding.get("execution") != spec.to_dict():
        raise StoreError("preflight execution binding changed")
    name = "preflight-" + rejection_identity(spec, case_id, action) + ".json"
    if confined_file(directory, name).read_text() != expected.to_json():
        raise StoreError("original preflight receipt changed")
    refs = (
        value.scenarios[0].checks[0].evidence
        if value.scenarios and value.scenarios[0].checks
        else ()
    )
    if len(refs) != 1:
        raise StoreError("preflight rejection lacks its exact receipt")
    recorded = PreflightRejection.from_json(read_bytes(batch.root, refs[0]).decode())
    if recorded != expected or value != rejected_evaluation(
        spec, action, refs[0], model_id=model_id
    ):
        raise StoreError("preflight scientific result differs from declared constraints/action")
    state = batch.replay()
    identities = {
        engineering_invocation_identity(spec, action, s.scenario_id, case_id)
        for s in spec.scenarios
    }
    if any(
        r.case_id == case_id and r.invocation_digest in identities
        for r in state.reservations.values()
    ):
        raise StoreError(
            "preflight rejection conflicts with existing physical work; charges retained"
        )
    return True
