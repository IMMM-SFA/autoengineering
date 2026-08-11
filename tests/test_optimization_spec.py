"""Behavior tests for immutable optimization study specifications."""

from dataclasses import FrozenInstanceError
import math

import pytest

from autoengineering.optimization import (
    BudgetSpec,
    CategoricalParameter,
    ConstraintSpec,
    ContinuousParameter,
    IntegerParameter,
    NoiseSpec,
    ObjectiveSpec,
    SearchSpace,
    StudySpec,
)


def test_primary_objective_requires_an_outcome_name():
    """Reject the missing outcome that would make optimization ambiguous."""
    with pytest.raises(ValueError, match="objective outcome"):
        ObjectiveSpec(outcome="", direction="maximize")


def test_conditional_parameter_round_trip():
    """Omit inactive numeric values after encoding and decoding a configuration."""
    space = SearchSpace(
        parameters=(
            CategoricalParameter("routing_model", ("linear", "muskingum")),
            ContinuousParameter(
                "travel_time",
                0.1,
                10.0,
                active_when={"routing_model": ("muskingum",)},
            ),
        )
    )
    config = {"routing_model": "linear"}

    encoded = space.encode(config)

    assert space.decode(encoded) == config
    assert space.active_names(config) == ("routing_model",)


def test_budget_cost_must_be_positive():
    """Reject a budget that could never pay for an evaluation."""
    with pytest.raises(ValueError, match="max_cost"):
        BudgetSpec(max_cost=0.0, cost_unit="cpu_hour")


def test_search_space_rejects_duplicate_parameter_names():
    """Reject duplicate names that would overwrite one configuration value."""
    with pytest.raises(ValueError, match="duplicate"):
        SearchSpace(
            parameters=(
                CategoricalParameter("method", ("a", "b")),
                IntegerParameter("method", 1, 5),
            )
        )


def test_encode_rejects_a_category_outside_the_declared_order():
    """Reject a category that has no deterministic numeric encoding."""
    space = SearchSpace(parameters=(CategoricalParameter("method", ("linear", "spline")),))

    with pytest.raises(ValueError, match="category"):
        space.encode({"method": "neural_network"})


@pytest.mark.parametrize("category", (math.nan, math.inf, -math.inf))
def test_categorical_parameter_rejects_non_finite_float_categories(category):
    """Reject float categories that cannot have a deterministic canonical encoding."""
    with pytest.raises(ValueError, match="finite"):
        CategoricalParameter("method", ("linear", category))


@pytest.mark.parametrize(
    ("make_parameter", "message"),
    [
        (lambda: ContinuousParameter("rate", 1.0, 1.0), "lower"),
        (lambda: IntegerParameter("steps", 5, 1), "lower"),
    ],
)
def test_numeric_parameters_require_increasing_bounds(make_parameter, message):
    """Reject a range that cannot be normalized to the unit interval."""
    with pytest.raises(ValueError, match=message):
        make_parameter()


def test_integer_decode_rounds_to_the_nearest_integer():
    """Decode a unit-cube value between integer grid points predictably."""
    space = SearchSpace(parameters=(IntegerParameter("iterations", 1, 11),))

    assert space.decode((0.55,)) == {"iterations": 7}


def test_log_scaled_parameter_round_trips_through_the_unit_interval():
    """Preserve values under a log normalization instead of linear scaling."""
    space = SearchSpace(parameters=(ContinuousParameter("length_scale", 1.0, 100.0, scale="log"),))

    assert space.encode({"length_scale": 10.0}) == pytest.approx((0.5,))
    assert space.decode((0.5,)) == pytest.approx({"length_scale": 10.0})


def test_search_space_rejects_a_condition_on_an_unknown_parameter():
    """Reject an activation rule that cannot be evaluated from a configuration."""
    with pytest.raises(ValueError, match="unknown condition"):
        SearchSpace(
            parameters=(
                ContinuousParameter("travel_time", 0.1, 10.0, active_when={"routing": ("x",)}),
            )
        )


def test_safety_constraints_are_not_supported():
    """Reject safety constraints because ordinary BO constraints are insufficient."""
    with pytest.raises(ValueError, match="safety"):
        ConstraintSpec(outcome="flood_risk", operator="<=", threshold=0.1, safety=True)


def test_conditional_numeric_encoding_uses_fixed_fill_and_activity_mask():
    """Give an inactive conditional value a neutral fill and an explicit mask."""
    space = SearchSpace(
        parameters=(
            CategoricalParameter("routing_model", ("linear", "muskingum")),
            IntegerParameter(
                "subreaches",
                1,
                11,
                active_when={"routing_model": ("muskingum",)},
            ),
        )
    )

    assert space.encode({"routing_model": "linear"}) == (0.0, 0.5, 0.0)
    assert space.encode({"routing_model": "muskingum", "subreaches": 6}) == (1.0, 0.5, 1.0)
    assert space.encoded_dimension == 3


def test_study_spec_serialization_is_stable_and_records_are_immutable(tmp_path):
    """Keep study definitions reproducible across JSON and repeated YAML writes."""
    study = StudySpec(
        name="routing-calibration",
        objective=ObjectiveSpec(outcome="nse", direction="maximize"),
        constraints=(ConstraintSpec(outcome="bias", operator=">=", threshold=-0.05),),
        budget=BudgetSpec(max_cost=24.0, cost_unit="cpu_hour", max_evaluations=12),
        noise=NoiseSpec(mode="known", noise_floor=0.001),
        backend="system",
        seed=42,
    )
    first_path = tmp_path / "study-first.yaml"
    second_path = tmp_path / "study-second.yaml"

    study.to_yaml(first_path)
    study.to_yaml(second_path)

    assert StudySpec.from_yaml(first_path) == study
    assert StudySpec.from_json(study.to_json()) == study
    assert first_path.read_text() == second_path.read_text()
    with pytest.raises(FrozenInstanceError):
        study.seed = 43
