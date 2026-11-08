"""Validation metrics and component comparison."""

from __future__ import annotations

from collections.abc import Callable, Mapping
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


def pbias(observed: np.ndarray, simulated: np.ndarray) -> float:
    """Percent bias: 100 * sum(simulated - observed) / sum(observed)."""
    return 100.0 * relative_bias(observed, simulated)


def low_flow_pbias(observed: np.ndarray, simulated: np.ndarray, quantile: float = 0.10) -> float:
    """Percent bias during low-flow periods (observed <= quantile threshold, default Q10)."""
    observed, simulated = _paired_arrays(observed, simulated)
    if not (0.0 < quantile < 1.0):
        raise ValueError("quantile must be between 0 and 1")
    cutoff = float(np.quantile(observed, quantile))
    mask = observed <= cutoff
    if not np.any(mask):
        return 0.0
    obs_low = observed[mask]
    sim_low = simulated[mask]
    denom = float(np.sum(obs_low))
    if denom == 0.0:
        return 0.0 if float(np.sum(sim_low)) == 0.0 else float("inf")
    return float(100.0 * np.sum(sim_low - obs_low) / denom)


METRICS = {
    "rmse": rmse,
    "bias": bias,
    "relative_bias": relative_bias,
    "correlation": correlation,
    "nse": nse,
    "kge": kge,
}

EXTENDED_METRICS = {
    **METRICS,
    "pbias": pbias,
    "low_flow_pbias": low_flow_pbias,
}


@dataclass(frozen=True)
class PhysicalCheck:
    """Hard physical constraint evaluated on chain outputs during validation or improvement.

    Supported ``kind`` values:
    - ``"nonnegative"``: requires ``min(output[port]) >= -tolerance``
    - ``"bounds"``: requires ``lower <= output[port] <= upper``
    - ``"mass_balance"``: requires ``abs(sum(inflows) - sum(outflows)) / abs(sum(inflows)) <= tolerance``
    - ``"custom"``: invokes ``predicate(outputs) -> tuple[bool, float, str]``
    """

    name: str
    kind: str = "nonnegative"
    port: str = ""
    tolerance: float = 1e-9
    lower: float | None = None
    upper: float | None = None
    inflow_ports: tuple[str, ...] = ()
    outflow_ports: tuple[str, ...] = ()
    predicate: Callable[[Mapping[str, np.ndarray]], tuple[bool, float, str]] | None = None
    required: bool = True


@dataclass(frozen=True)
class PhysicalCheckResult:
    """Result of evaluating a PhysicalCheck against simulated outputs."""

    name: str
    passed: bool
    value: float | None = None
    threshold: float | None = None
    reason: str = ""
    required: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "value": round(self.value, 6) if self.value is not None and np.isfinite(self.value) else self.value,
            "threshold": self.threshold,
            "reason": self.reason,
            "required": self.required,
        }


def evaluate_physical_checks(
    outputs: Mapping[str, np.ndarray],
    checks: list[PhysicalCheck] | tuple[PhysicalCheck, ...],
) -> list[PhysicalCheckResult]:
    """Evaluate a sequence of physical checks on named chain output arrays."""
    results: list[PhysicalCheckResult] = []
    for check in checks:
        try:
            if check.kind == "nonnegative":
                arr = np.asarray(outputs[check.port], dtype=float)
                minimum = float(np.min(arr))
                passed = bool(np.all(np.isfinite(arr)) and minimum >= -check.tolerance)
                results.append(
                    PhysicalCheckResult(
                        name=check.name,
                        passed=passed,
                        value=minimum,
                        threshold=-check.tolerance,
                        reason=f"Port '{check.port}' minimum {minimum:.6g} >= {-check.tolerance:.6g}",
                        required=check.required,
                    )
                )
            elif check.kind == "bounds":
                arr = np.asarray(outputs[check.port], dtype=float)
                val_min = float(np.min(arr))
                val_max = float(np.max(arr))
                ok_low = True if check.lower is None else val_min >= check.lower - check.tolerance
                ok_high = True if check.upper is None else val_max <= check.upper + check.tolerance
                passed = bool(np.all(np.isfinite(arr)) and ok_low and ok_high)
                results.append(
                    PhysicalCheckResult(
                        name=check.name,
                        passed=passed,
                        value=val_max if not ok_high else val_min,
                        threshold=check.upper if not ok_high else check.lower,
                        reason=f"Port '{check.port}' range [{val_min:.6g}, {val_max:.6g}] within bounds [{check.lower}, {check.upper}]",
                        required=check.required,
                    )
                )
            elif check.kind == "mass_balance":
                inflow = sum(np.asarray(outputs[p], dtype=float) for p in check.inflow_ports)
                outflow = sum(np.asarray(outputs[p], dtype=float) for p in check.outflow_ports)
                denom = max(float(np.sum(np.abs(inflow))), 1e-12)
                rel_err = float(np.abs(np.sum(inflow) - np.sum(outflow)) / denom)
                passed = bool(np.isfinite(rel_err) and rel_err <= check.tolerance)
                results.append(
                    PhysicalCheckResult(
                        name=check.name,
                        passed=passed,
                        value=rel_err,
                        threshold=check.tolerance,
                        reason=f"Relative mass balance residual {rel_err:.6g} <= {check.tolerance:.6g}",
                        required=check.required,
                    )
                )
            elif check.kind == "custom" and check.predicate is not None:
                passed, val, reason = check.predicate(outputs)
                results.append(
                    PhysicalCheckResult(
                        name=check.name,
                        passed=bool(passed),
                        value=float(val),
                        threshold=check.tolerance,
                        reason=reason,
                        required=check.required,
                    )
                )
            else:
                raise ValueError(f"Unsupported physical check kind: {check.kind}")
        except Exception as exc:
            results.append(
                PhysicalCheckResult(
                    name=check.name,
                    passed=False,
                    value=None,
                    threshold=check.tolerance,
                    reason=f"Physical check error: {type(exc).__name__}: {exc}",
                    required=check.required,
                )
            )
    return results


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
        if name not in EXTENDED_METRICS:
            raise ValueError(f"Unknown threshold metric: {name}")
        if not np.isfinite(threshold):
            raise ValueError(f"threshold for {name} must be finite")

    results = []
    for metric_name in metrics:
        if metric_name not in EXTENDED_METRICS:
            raise ValueError(
                f"Unknown metric: {metric_name}. Available: {list(EXTENDED_METRICS.keys())}"
            )
        value = EXTENDED_METRICS[metric_name](observed, simulated)
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
