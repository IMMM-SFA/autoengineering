"""Dependence intervals retain frozen masks, gaps and short-series limits."""
from dataclasses import replace
from datetime import date, timedelta

import numpy as np
import pytest

from autoengineering.utility.uncertainty import (
    PredictionUncertaintySpec, DependencePlan, support_digest, prediction_uncertainty,
)
from test_utility_contracts import H


def inputs(mask=None):
    times = tuple((date(2020, 1, 1)+timedelta(days=i)).isoformat() for i in range(12))
    mask = tuple(mask) if mask is not None else (True,)*12
    segments = ("development-segment",)*12
    spec = PredictionUncertaintySpec("utility-prediction-uncertainty-v1", "hydrology", "rmse",
        "mm/day", "segmented_circular_moving_block", 3, 500, .95, 17, 86400,
        support_digest(times, mask, segments), H, H)
    return spec, dict(timestamps=times, mask=mask, segments=segments)


def test_constant_paired_errors_have_known_gain_and_interval():
    spec, support = inputs()
    result = prediction_uncertainty(spec, np.zeros(12), np.ones(12), np.full(12, 3.), **support)
    assert result["gain"] == 2. and result["interval"] == [2., 2.]
    assert result["scored_samples"] == 12 and result["status"] == "estimated"
    assert result == prediction_uncertainty(spec, np.zeros(12), np.ones(12), np.full(12, 3.), **support)
    assert DependencePlan.from_json(DependencePlan("utility-dependence-v1", (spec,)).to_json()).tasks == (spec,)


def test_mask_gaps_break_segments_and_short_runs_remain_insufficient():
    spec, support = inputs([True]*2+[False]*2+[True]*8)
    result = prediction_uncertainty(spec, np.zeros(12), np.ones(12), np.full(12, 3.), **support)
    assert result["segments"] == 2 and result["scored_samples"] == 10
    assert result["status"] == "insufficient_data" and result["interval"] is None
    assert result["gain"] == 2.


def test_changed_mask_and_nonfinite_scored_values_reject():
    spec, support = inputs()
    with pytest.raises(ValueError, match="frozen policy"):
        prediction_uncertainty(spec, np.zeros(12), np.ones(12), np.full(12, 3.),
                               **(support | {"mask": (False,)+(True,)*11}))
    invalid = np.ones(12)
    invalid[0] = np.nan
    with pytest.raises(ValueError, match="nonfinite"):
        prediction_uncertainty(spec, np.zeros(12), invalid, np.full(12, 3.), **support)


def test_calendar_gaps_are_not_bridged_and_unscored_values_are_not_filled():
    spec, support = inputs()
    times = support["timestamps"][:6] + tuple((date(2020, 2, 1)+timedelta(days=i)).isoformat() for i in range(6))
    support = support | {"timestamps": times}
    spec = replace(spec, support_digest=support_digest(**support))
    result = prediction_uncertainty(spec, np.zeros(12), np.ones(12), np.full(12, 3.), **support)
    assert result["segments"] == 2 and result["status"] == "estimated"


def test_no_scoring_samples_has_no_zero_loss():
    spec, support = inputs([False]*12)
    result = prediction_uncertainty(spec, np.full(12, np.nan), np.full(12, np.nan), np.full(12, np.nan), **support)
    assert result["gain"] is None and result["interval"] is None
    assert result["status"] == "insufficient_data"


def test_fixed_design_scenarios_cannot_manufacture_population_intervals():
    from autoengineering.utility.uncertainty import ScenarioUncertaintySpec, scenario_uncertainty
    spec = ScenarioUncertaintySpec("utility-scenario-uncertainty-v1", "engineering", "W", "minimize",
        ("low", "nominal", "high"), "fixed_scenario_census", "fixed_design_cases", H, 500, .95, 17)
    result = scenario_uncertainty(spec, [1., 1., 1.], [3., 3., 3.], scenario_ids=spec.scenario_ids)
    assert result["mean_gain"] == 2. and result["interval"] is None
    assert result["status"] == "finite_scenario_summary"
    with pytest.raises(ValueError, match="sampling design"):
        replace(spec, method="iid_paired_scenario_bootstrap")
    assert DependencePlan("utility-dependence-v1", (), (spec,)).scenarios == (spec,)


def test_scenario_sample_uncertainty_is_separate_and_keeps_missing_cases():
    from autoengineering.utility.uncertainty import ScenarioUncertaintySpec, scenario_uncertainty
    spec = ScenarioUncertaintySpec("utility-scenario-uncertainty-v1", "wind", "GWh", "maximize",
        ("weather-1", "weather-2", "weather-3"), "iid_paired_scenario_bootstrap",
        "independent_scenario_sample", H, 500, .95, 17)
    result = scenario_uncertainty(spec, [3., 3., 3.], [1., 1., 1.], scenario_ids=spec.scenario_ids)
    assert result["interval"] == [2., 2.]
    missing = scenario_uncertainty(spec, [None, 3., 3.], [1., 1., 1.], scenario_ids=spec.scenario_ids)
    assert missing["assigned_scenarios"] == 3 and missing["valid_scenarios"] == 2
    assert missing["status"] == "insufficient_data" and missing["interval"] is None


def test_block_policy_preserves_more_uncertainty_for_persistent_error_runs():
    times = tuple((date(2020, 1, 1)+timedelta(days=i)).isoformat() for i in range(64))
    mask, segments = (True,)*64, ("continuous",)*64
    spec = PredictionUncertaintySpec("utility-prediction-uncertainty-v1", "hydrology", "rmse",
        "mm/day", "segmented_circular_moving_block", 8, 1000, .95, 17, 86400,
        support_digest(times, mask, segments), H, H)
    support = dict(timestamps=times, mask=mask, segments=segments)
    persistent = np.r_[np.ones(32), np.full(32, 4.)]
    blocked = prediction_uncertainty(spec, np.zeros(64), np.zeros(64), persistent, **support)
    independent = prediction_uncertainty(replace(spec, block_length=1), np.zeros(64), np.zeros(64),
                                         persistent, **support)
    assert blocked["gain"] == independent["gain"]
    assert blocked["interval"][1]-blocked["interval"][0] > independent["interval"][1]-independent["interval"][0]
