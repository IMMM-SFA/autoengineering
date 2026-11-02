"""Engineering outcomes retain units, feasibility and shared selection behavior."""
from dataclasses import replace

import numpy as np
import pytest

from autoengineering.campaign.acceptance import CheckContext, CheckRegistry
from autoengineering.campaign.records import EvaluationRecord
from autoengineering.campaign.spec import AcceptanceSpec, CheckSpec
from autoengineering.utility.outcomes import (
    EngineeringAcceptance, OutcomeSpec, OutcomeRegistry, evaluator_identity, engineering_decision,
)


def power(context):
    return float(context.outputs["power"])


def revenue(context):
    return float(context.outputs["revenue"])


def physical(context, options):
    return ("pass" if bool(context.outputs["valid"]) else "fail", None, None, "Physics check")


def rules():
    return EngineeringAcceptance(
        "engineering-acceptance-v1",
        [OutcomeSpec("engineering-outcome-v1", "power", "W", "minimize", "mean",
                     evaluator_identity(power)),
         OutcomeSpec("engineering-outcome-v1", "revenue", "USD", "maximize", "sum",
                     evaluator_identity(revenue))],
        "power", 1., {"revenue": 2.}, [CheckSpec("physics", "1", True, "scenario", {})])


def score(name, powers=(10, 20), revenues=(5, 5), valid=True):
    template = EvaluationRecord(name, name, {}, "success", {}, (), (), "selection", name, 0., {})
    contexts = {f"scenario-{i}": CheckContext(
        {"power": np.array(p), "revenue": np.array(r), "valid": np.array(valid)}, {}, {})
        for i, (p, r) in enumerate(zip(powers, revenues))}
    return OutcomeRegistry({"power": power, "revenue": revenue}).evaluate(
        rules(), contexts, CheckRegistry({("physics", "1"): physical}), template)


def test_engineering_units_and_scenario_aggregation():
    result = score("baseline")
    assert result.evaluation.metrics == {"power": 15., "revenue": 10.}
    assert result.scenarios[0].values == {"power": 10., "revenue": 5.}
    assert EngineeringAcceptance.from_json(rules().to_json()) == rules()
    assert result.evaluation.provenance["engineering_rules"] == rules().digest


def test_shared_selection_vetoes_physics_and_secondary_degradation():
    base = score("baseline")
    feasible = score("good", powers=(8, 18))
    invalid = score("invalid", powers=(0, 0), valid=False)
    low_revenue = score("low-revenue", powers=(1, 1), revenues=(0, 0))
    decision = engineering_decision(base, (invalid, low_revenue, feasible), rules())
    assert decision.selected_id == "good"
    assert decision.rules_digest == rules().digest
    assert "invalid" not in decision.eligible_alternatives
    assert "low-revenue" not in decision.eligible_alternatives


def test_tie_retains_baseline_and_unavailable_never_wins():
    decision = engineering_decision(score("baseline"), (
        score("equal"), score("nonfinite", powers=(float("nan"), 0))), rules())
    assert decision.selected_id == "baseline"
    assert "nonfinite" not in decision.eligible_alternatives


def test_identity_and_saved_aggregate_tamper():
    base = score("baseline")
    altered = replace(base, evaluation=replace(base.evaluation, metrics={"power": 0, "revenue": 10}))
    with pytest.raises(ValueError, match="aggregate"):
        engineering_decision(altered, (), rules())
    with pytest.raises(ValueError, match="identity"):
        engineering_decision(base, (), replace(rules(), minimum_gain=2))


def test_unknown_registration_stops_before_callbacks():
    called = []

    def wrong(context):
        called.append(1)
        return 0.

    with pytest.raises(ValueError, match="registration"):
        OutcomeRegistry({"power": wrong}).evaluate(rules(), {}, CheckRegistry(),
                                                   score("baseline").evaluation)
    assert not called


def test_legacy_acceptance_does_not_deserialize_engineering_names():
    with pytest.raises(ValueError):
        AcceptanceSpec("power", "minimize", 1, {}, rules().checks)


def test_scenario_forcing_identity_must_match():
    base = score("baseline")
    candidate = score("candidate", powers=(8, 18))
    candidate = replace(candidate, scenarios=(replace(candidate.scenarios[0],
                        forcing_digest="2" * 64), candidate.scenarios[1]))
    with pytest.raises(ValueError, match="scenarios differ"):
        engineering_decision(base, (candidate,), rules())
