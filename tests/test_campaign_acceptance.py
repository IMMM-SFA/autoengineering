"""Scientific eligibility must veto attractive invalid or unavailable evidence."""

from dataclasses import replace

import numpy as np
import pytest

from autoengineering.campaign.acceptance import CheckContext, DEFAULT_CHECKS, decide, metrics
from autoengineering.campaign.records import CheckResult, EvaluationRecord
from autoengineering.campaign.spec import AcceptanceSpec, CheckSpec
from examples.campaign_contracts.build_fixture import fixture


def evaluation(name, rmse=1.0, status="success", check_status="pass"):
    return EvaluationRecord(
        name,
        name,
        {"capacity": 100.0},
        status,
        {"rmse": rmse, "kge": 0.6, "bias": 0.1},
        (CheckResult("finite", "1", check_status, True, "outputs", None, None, "Test", ()),),
        (),
        "comparison",
        f"attempt-{name}",
        0.01,
        {},
    )


@pytest.mark.parametrize("status", ["fail", "unavailable", "error"])
def test_attractive_but_invalid_candidate_cannot_win(status):
    baseline = evaluation("baseline")
    candidate = evaluation("candidate", 0, check_status=status)
    decision = decide(baseline, (candidate,), fixture().acceptance)
    assert decision.outcome == "retain_baseline"
    assert decision.selected_id == baseline.id
    assert candidate.id not in decision.eligible_alternatives


def test_missing_required_check_or_metric_cannot_pass():
    baseline = evaluation("baseline", check_status="fail")
    candidate = replace(evaluation("candidate", 0), checks=())
    rules = fixture().acceptance
    assert decide(baseline, (candidate,), rules).outcome == "no_eligible_model"
    candidate = replace(evaluation("candidate", 0), metrics={"rmse": None})
    decision = decide(baseline, (candidate,), rules)
    assert decision.selected_id is None
    assert decision.selected_configuration is None


def test_ineligible_baseline_is_never_fallback_and_exact_ties_retain_baseline():
    baseline = evaluation("baseline", check_status="fail")
    candidate = evaluation("candidate", 2)
    assert decide(baseline, (candidate,), fixture().acceptance).selected_id == "candidate"
    baseline = evaluation("baseline")
    candidate = evaluation("candidate")
    assert (
        decide(baseline, (candidate,), replace(fixture().acceptance, minimum_gain=0)).outcome
        == "retain_baseline"
    )


def test_full_precision_and_secondary_tradeoffs():
    rules = AcceptanceSpec(
        "rmse", "minimize", 0.01, {"kge": 0.02, "bias": 0.05}, fixture().acceptance.checks
    )
    baseline = evaluation("baseline")
    too_little = evaluation("almost", 0.99000000000001)
    assert decide(baseline, (too_little,), rules).outcome == "retain_baseline"
    worse_kge = replace(
        evaluation("candidate", 0.8), metrics={"rmse": 0.8, "kge": 0.57, "bias": 0.1}
    )
    assert decide(baseline, (worse_kge,), rules).outcome == "retain_baseline"
    good = evaluation("better", 0.98)
    assert decide(baseline, (good,), rules).selected_id == "better"
    with pytest.raises(ValueError, match="splits"):
        decide(baseline, (replace(good, split_id="confirmation"),), rules)


def test_unavailable_check_and_degenerate_metrics_are_explicit():
    spec = CheckSpec("unknown", "1", True, "whole_model", {})
    assert DEFAULT_CHECKS.evaluate(spec, CheckContext({}, {}, {})).status == "unavailable"
    assert metrics(np.zeros(3), np.zeros(3))["nse"] is None


def test_independent_balance_ignores_fabricated_residual():
    context = CheckContext(
        {
            "soil": np.array([50.0, 50.0]),
            "reservoir": np.zeros(2),
            "aet": np.zeros(2),
            "prediction": np.zeros(2),
            "initial_soil": np.array(50.0),
            "initial_reservoir": np.array(0.0),
            "balance_residual": np.zeros(2),
        },
        {"precip_mm": np.ones(2)},
        {"capacity": 100.0},
    )
    spec = CheckSpec("daily_balance", "1", True, "whole_model", {})
    result = DEFAULT_CHECKS.evaluate(spec, context)
    assert result.status == "fail"
    assert result.value == 1
    assert result.scope == "whole_model"


def test_nonfinite_check_result_is_an_error_not_an_unknown_physical_attempt():
    from autoengineering.campaign.acceptance import CheckRegistry

    registry = CheckRegistry(
        {("overflow", "1"): lambda *_: ("pass", float("inf"), 1.0, "Overflow")}
    )
    result = registry.evaluate(
        CheckSpec("overflow", "1", True, "whole_model", {}), CheckContext({}, {}, {})
    )
    assert result.status == "error"
    assert result.value is None
