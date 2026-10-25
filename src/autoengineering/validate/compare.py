"""Validation metrics and component comparison."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class ValidationResult:
    """Result of validating a component against a baseline."""

    component: str
    metric: str
    value: float
    threshold: float | None = None
    status: str = "info"  # "pass", "fail", "warn", "info"
    interpretation: str = ""

    def __post_init__(self):
        if self.threshold is not None and not self.status:
            self.status = "pass" if self.value <= self.threshold else "fail"

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "metric": self.metric,
            "value": round(self.value, 6),
            "threshold": self.threshold,
            "status": self.status,
            "interpretation": self.interpretation,
        }

    def to_markdown(self) -> str:
        icon = {"pass": "OK", "fail": "FAIL", "warn": "WARN", "info": "INFO"}.get(self.status, "")
        line = f"[{icon}] **{self.metric}** = {self.value:.4f}"
        if self.threshold is not None:
            line += f" (threshold: {self.threshold})"
        if self.interpretation:
            line += f" — {self.interpretation}"
        return line


def _paired_arrays(observed: np.ndarray, simulated: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Require aligned, finite, nonempty real-valued time series."""
    if np.iscomplexobj(observed) or np.iscomplexobj(simulated):
        raise ValueError("validation arrays must be real-valued")
    observed = np.asarray(observed, dtype=float)
    simulated = np.asarray(simulated, dtype=float)
    if observed.ndim != 1 or simulated.ndim != 1:
        raise ValueError("validation arrays must be one-dimensional")
    if observed.shape != simulated.shape:
        raise ValueError("observed and simulated arrays must have identical shapes")
    if observed.size == 0:
        raise ValueError("validation arrays must be nonempty")
    if not np.all(np.isfinite(observed)) or not np.all(np.isfinite(simulated)):
        raise ValueError("validation arrays must contain only finite values")
    return observed, simulated


def rmse(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Root Mean Squared Error."""
    observed, simulated = _paired_arrays(observed, simulated)
    return float(np.sqrt(np.mean((observed - simulated) ** 2)))


def bias(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Mean bias (simulated - observed)."""
    observed, simulated = _paired_arrays(observed, simulated)
    return float(np.mean(simulated - observed))


def relative_bias(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Relative bias as a fraction of mean observed."""
    observed, simulated = _paired_arrays(observed, simulated)
    obs_mean = np.mean(observed)
    if obs_mean == 0:
        return float("inf")
    return float(np.mean(simulated - observed) / obs_mean)


def correlation(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Pearson correlation coefficient."""
    observed, simulated = _paired_arrays(observed, simulated)
    if np.std(observed) == 0 or np.std(simulated) == 0:
        return 0.0
    return float(np.corrcoef(observed, simulated)[0, 1])


def nse(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Nash-Sutcliffe Efficiency."""
    observed, simulated = _paired_arrays(observed, simulated)
    numerator = np.sum((observed - simulated) ** 2)
    denominator = np.sum((observed - np.mean(observed)) ** 2)
    if denominator == 0:
        return float("-inf")
    return float(1 - numerator / denominator)


def kge(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Kling-Gupta Efficiency."""
    observed, simulated = _paired_arrays(observed, simulated)
    r = correlation(observed, simulated)
    alpha = np.std(simulated) / np.std(observed) if np.std(observed) > 0 else 0.0
    beta = np.mean(simulated) / np.mean(observed) if np.mean(observed) != 0 else 0.0
    return float(1 - np.sqrt((r - 1) ** 2 + (alpha - 1) ** 2 + (beta - 1) ** 2))


METRICS = {
    "rmse": rmse,
    "bias": bias,
    "relative_bias": relative_bias,
    "correlation": correlation,
    "nse": nse,
    "kge": kge,
}


def validate_arrays(
    component_name: str,
    observed: np.ndarray,
    simulated: np.ndarray,
    metrics: list[str] | None = None,
    thresholds: dict[str, float] | None = None,
) -> list[ValidationResult]:
    """Validate aligned, nonempty, finite one-dimensional arrays.

    Args:
        component_name: Name of the component being validated.
        observed: Observed/baseline data array.
        simulated: Simulated/test data array of exactly the same shape.
        metrics: List of metric names to compute. Defaults to all.
        thresholds: Optional dict of {metric_name: finite threshold_value}.

    Returns:
        List of ValidationResult objects.

    Raises:
        ValueError: If inputs violate the array contract or a metric is nonfinite.
    """
    observed, simulated = _paired_arrays(observed, simulated)
    if metrics is None:
        metrics = list(METRICS.keys())
    thresholds = thresholds or {}
    for name, threshold in thresholds.items():
        if name not in METRICS:
            raise ValueError(f"Unknown threshold metric: {name}")
        if not np.isfinite(threshold):
            raise ValueError(f"threshold for {name} must be finite")

    results = []
    for metric_name in metrics:
        if metric_name not in METRICS:
            raise ValueError(f"Unknown metric: {metric_name}. Available: {list(METRICS.keys())}")
        value = METRICS[metric_name](observed, simulated)
        if not np.isfinite(value):
            raise ValueError(f"metric {metric_name} is undefined or nonfinite for these arrays")
        threshold = thresholds.get(metric_name)

        if threshold is not None:
            if metric_name in ("nse", "kge", "correlation"):
                status = "pass" if value >= threshold else "fail"
            else:
                status = "pass" if abs(value) <= threshold else "fail"
        else:
            status = "info"

        results.append(
            ValidationResult(
                component=component_name,
                metric=metric_name,
                value=value,
                threshold=threshold,
                status=status,
            )
        )

    return results


def validate_component(
    system,
    component_name: str,
    baseline: np.ndarray,
    simulated: np.ndarray,
    metrics: list[str] | None = None,
    thresholds: dict[str, float] | None = None,
) -> list[ValidationResult]:
    """Validate a component in a system against baseline data.

    This is the high-level API that takes a System object.
    """
    # Verify component exists
    system.get_component(component_name)
    return validate_arrays(component_name, baseline, simulated, metrics, thresholds)
