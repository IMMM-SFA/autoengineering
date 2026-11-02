"""Fixed numerical parity decisions without science or process starts."""

import numpy as np
import pytest

from examples.utility import guest_prediction_parity as module


def test_all_values_and_scalar_initial_states_are_compared():
    values = {"prediction": np.array([0.0, 1.0, 2.0]), "initial_soil": np.asarray(10.0)}
    result = module.compare_arrays(values, {key: value.copy() for key, value in values.items()})
    assert all(item["within_tolerance"] and item["bitwise_equal"] for item in result.values())
    assert result["initial_soil"]["shape"] == []


def test_nonfinite_or_changed_shape_cannot_pass():
    reference = {"prediction": np.array([1.0, 2.0])}
    for value in (
        np.array([1.0, np.nan]),
        np.array([1.0]),
        np.array([1.0, np.inf]),
        np.array([1, 2]),
    ):
        with pytest.raises(ValueError):
            module.compare_arrays(reference, {"prediction": value})


def test_tolerance_reports_failure_without_relaxing_the_threshold():
    reference = {"prediction": np.array([0.0, 1.0])}
    close = module.compare_arrays(reference, {"prediction": np.array([module.ATOL / 2, 1.0])})
    far = module.compare_arrays(reference, {"prediction": np.array([module.ATOL * 2, 1.0])})
    assert close["prediction"]["within_tolerance"]
    assert not far["prediction"]["within_tolerance"]
    assert not close["prediction"]["bitwise_equal"]


def test_missing_output_cannot_be_hidden_by_a_matching_prediction():
    with pytest.raises(ValueError, match="names"):
        module.compare_arrays(
            {"prediction": np.array([1.0]), "soil": np.array([1.0])},
            {"prediction": np.array([1.0])},
        )
