"""Tests for the validation module."""

import numpy as np

from autoengineering.validate.compare import (
    ValidationResult,
    bias,
    correlation,
    kge,
    nse,
    rmse,
    validate_arrays,
)


class TestMetrics:
    def test_rmse_perfect(self):
        a = np.array([1.0, 2.0, 3.0])
        assert rmse(a, a) == 0.0

    def test_rmse_known(self):
        obs = np.array([1.0, 2.0, 3.0])
        sim = np.array([1.0, 2.0, 4.0])
        assert abs(rmse(obs, sim) - (1.0 / 3.0) ** 0.5) < 1e-6

    def test_bias_positive(self):
        obs = np.array([1.0, 2.0, 3.0])
        sim = np.array([2.0, 3.0, 4.0])
        assert bias(obs, sim) == 1.0

    def test_bias_zero(self):
        a = np.array([1.0, 2.0, 3.0])
        assert bias(a, a) == 0.0

    def test_correlation_perfect(self):
        obs = np.array([1.0, 2.0, 3.0, 4.0])
        assert abs(correlation(obs, obs) - 1.0) < 1e-10

    def test_correlation_negative(self):
        obs = np.array([1.0, 2.0, 3.0, 4.0])
        sim = np.array([4.0, 3.0, 2.0, 1.0])
        assert abs(correlation(obs, sim) - (-1.0)) < 1e-10

    def test_nse_perfect(self):
        a = np.array([1.0, 2.0, 3.0])
        assert nse(a, a) == 1.0

    def test_nse_mean_model(self):
        obs = np.array([1.0, 2.0, 3.0])
        sim = np.full(3, 2.0)
        assert abs(nse(obs, sim)) < 1e-10

    def test_kge_perfect(self):
        a = np.array([1.0, 2.0, 3.0, 4.0])
        assert abs(kge(a, a) - 1.0) < 1e-10


class TestValidateArrays:
    def test_all_metrics(self):
        obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        sim = np.array([1.1, 2.2, 2.8, 4.1, 5.3])
        results = validate_arrays("comp_a", obs, sim)
        assert len(results) == 6
        names = {r.metric for r in results}
        assert "rmse" in names
        assert "kge" in names

    def test_with_thresholds(self):
        obs = np.array([1.0, 2.0, 3.0])
        sim = np.array([1.0, 2.0, 3.0])
        results = validate_arrays("comp_a", obs, sim, metrics=["rmse"], thresholds={"rmse": 0.1})
        assert results[0].status == "pass"

    def test_failing_threshold(self):
        obs = np.array([1.0, 2.0, 3.0])
        sim = np.array([2.0, 3.0, 4.0])
        results = validate_arrays("comp_a", obs, sim, metrics=["rmse"], thresholds={"rmse": 0.1})
        assert results[0].status == "fail"

    def test_selected_metrics(self):
        obs = np.array([1.0, 2.0, 3.0])
        sim = np.array([1.0, 2.0, 3.0])
        results = validate_arrays("comp_a", obs, sim, metrics=["rmse", "bias"])
        assert len(results) == 2


class TestValidationResult:
    def test_to_dict(self):
        r = ValidationResult("comp_a", "rmse", 0.123456, threshold=0.5, status="pass")
        d = r.to_dict()
        assert d["component"] == "comp_a"
        assert d["value"] == 0.123456

    def test_to_markdown(self):
        r = ValidationResult("comp_a", "rmse", 0.5, status="fail")
        md = r.to_markdown()
        assert "FAIL" in md
        assert "rmse" in md
