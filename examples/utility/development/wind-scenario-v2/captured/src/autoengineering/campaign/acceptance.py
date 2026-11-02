"""Independent checks and full-precision scientific decisions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np

from autoengineering.validate.compare import METRICS

from .records import CheckResult, DecisionRecord, EvaluationRecord
from .spec import AcceptanceSpec, CheckSpec


@dataclass(frozen=True)
class CheckContext:
    outputs: Mapping[str, np.ndarray]
    forcing: Mapping[str, np.ndarray]
    parameters: Mapping[str, object]


class CheckRegistry:
    """Trusted name/version registrations. Campaign YAML never contains expressions."""

    def __init__(self, checks: Mapping[tuple[str, str], Callable] | None = None):
        self._checks = MappingProxyType(dict(checks or {}))

    def evaluate(self, spec: CheckSpec, context: CheckContext) -> CheckResult:
        check = self._checks.get((spec.name, spec.version))
        status, value, threshold, reason = "unavailable", None, None, "Check is not registered"
        if check is not None:
            try:
                status, value, threshold, reason = check(context, spec.options)
            except KeyError:
                status, value, threshold, reason = (
                    "unavailable",
                    None,
                    None,
                    "Required diagnostic absent",
                )
            except Exception:
                status, value, threshold, reason = (
                    "error",
                    None,
                    None,
                    "Check implementation failed",
                )
        try:
            return CheckResult(
                spec.name,
                spec.version,
                status,
                spec.required,
                spec.scope,
                value,
                threshold,
                reason,
                (),
            )
        except (ValueError, TypeError):
            return CheckResult(
                spec.name,
                spec.version,
                "error",
                spec.required,
                spec.scope,
                None,
                None,
                "Check returned an invalid or nonfinite result",
                (),
            )


def finite(context: CheckContext, options):
    arrays = tuple(context.outputs.values())
    passed = bool(arrays) and all(np.isfinite(array).all() for array in arrays)
    return ("pass" if passed else "fail", None, None, "Finite outputs required")


def nonnegative(context: CheckContext, options):
    names = ("soil", "reservoir", "aet", "prediction", "pet")
    minimum = min(float(np.min(context.outputs[name])) for name in names)
    tolerance = float(options.get("tolerance", 1e-10))
    return (
        "pass" if minimum >= -tolerance else "fail",
        minimum,
        -tolerance,
        "Stores and fluxes must be nonnegative",
    )


def soil_capacity(context: CheckContext, options):
    maximum = float(np.max(context.outputs["soil"]))
    capacity = float(context.parameters["capacity"])
    tolerance = float(options.get("tolerance", 1e-10))
    return (
        "pass" if maximum <= capacity + tolerance else "fail",
        maximum,
        capacity + tolerance,
        "Soil store must not exceed capacity",
    )


def daily_balance(context: CheckContext, options):
    """Recompute from saved stores and fluxes; ignore any model-reported residual."""
    out = context.outputs
    precipitation = np.asarray(context.forcing["precip_mm"])
    soil, reservoir, et, flow = (
        np.asarray(out[name]) for name in ("soil", "reservoir", "aet", "prediction")
    )
    if any(
        array.shape != precipitation.shape or array.ndim != 1
        for array in (soil, reservoir, et, flow)
    ) or not len(precipitation):
        return "fail", None, None, "Balance arrays must be aligned nonempty daily series"
    initial = float(out["initial_soil"]) + float(out["initial_reservoir"])
    # Independently require the prescribed initial conditions.
    if (
        abs(float(out["initial_soil"]) - float(context.parameters["capacity"]) / 2) > 1e-10
        or abs(float(out["initial_reservoir"])) > 1e-10
    ):
        return "fail", None, None, "Initial conditions differ from the frozen prescription"
    change = np.diff(np.r_[initial, soil + reservoir])
    residual = precipitation - et - flow - change
    scale = np.maximum.reduce(
        [
            np.ones_like(precipitation),
            abs(precipitation),
            abs(et),
            abs(flow),
            abs(change),
        ]
    )
    tolerance = 1e-8 + 1e-10 * scale
    maximum = float(np.max(abs(residual)))
    passed = np.isfinite(residual).all() and np.all(abs(residual) <= tolerance)
    return (
        "pass" if passed else "fail",
        maximum,
        float(np.max(tolerance)),
        "Daily P - ET - Q - delta storage, in mm",
    )


def routing_accounting(context: CheckContext, options):
    from examples.leaf_river.models.routing import triangular_uh
    from examples.leaf_river.models.routing_calibrated import gamma_uh

    parameters = context.parameters
    kernel = (
        triangular_uh(parameters["uh_peak"], parameters["uh_length"])
        if parameters["family"] == "triangular"
        else gamma_uh(parameters["gamma_shape"], parameters["gamma_scale"], parameters["uh_length"])
    )
    runoff, recharge = context.forcing["runoff"], context.forcing["recharge"]
    predicted = context.outputs["prediction"]
    if predicted.shape != runoff.shape or not np.isfinite(predicted).all():
        return "fail", None, None, "Routing output is not aligned and finite"
    baseflow = np.zeros(len(runoff))
    baseflow[0] = 0.5
    for i in range(1, len(baseflow)):
        baseflow[i] = (
            parameters["k_base"] * baseflow[i - 1] + parameters["recharge_frac"] * recharge[i]
        )
    full = np.convolve(runoff, kernel)
    error = float(np.max(abs(predicted - full[: len(runoff)] - baseflow)))
    passed = (
        np.min(predicted) >= -1e-12
        and abs(kernel.sum() - 1) <= 1e-12
        and np.allclose(predicted, full[: len(runoff)] + baseflow, atol=1e-10, rtol=1e-10)
        and abs(full.sum() - runoff.sum()) <= 1e-8
    )
    return (
        "pass" if passed else "fail",
        error,
        1e-10,
        "Routing convolution, baseflow and tail accounting only",
    )


def solar_physical(context: CheckContext, options):
    """Check declared equipment limits without changing negative night-time tare."""
    ac = np.asarray(context.outputs["prediction"])
    poa = np.asarray(context.forcing["poa"])
    wind = np.asarray(context.forcing["wind"])
    capacity = float(options["capacity_kw"])
    floor = float(options["standby_floor_kw"])
    loss = context.parameters["dc_loss_scale"]
    valid = (
        np.isfinite(ac).all() and capacity > 0 and floor <= 0
        and np.all(ac <= capacity + 1e-8) and np.all(ac >= floor - 1e-8)
        and np.all(poa >= 0) and np.all(wind >= 0)
        and np.all(ac[poa == 0] <= 1e-8)
        and type(loss) in (int, float) and .9 <= loss <= 1.
    )
    return ("pass" if valid else "fail", float(np.max(ac)), capacity,
            "Declared inverter capacity, standby, night-time and loss limits")


DEFAULT_CHECKS = CheckRegistry(
    {
        ("finite", "1"): finite,
        ("solar_physical", "1"): solar_physical,
        ("routing_accounting", "1"): routing_accounting,
        ("nonnegative", "1"): nonnegative,
        ("soil_capacity", "1"): soil_capacity,
        ("daily_balance", "1"): daily_balance,
    }
)


def metrics(observed: np.ndarray, predicted: np.ndarray) -> dict[str, float | None]:
    """Unavailable numeric metrics remain null, never a favorable sentinel score."""
    result = {}
    for name, function in METRICS.items():
        try:
            value = function(observed, predicted)
            result[name] = value if np.isfinite(value) else None
        except (ValueError, FloatingPointError):
            result[name] = None
    return result


def eligible(record: EvaluationRecord, rules: AcceptanceSpec) -> bool:
    if not record.eligible:
        return False
    checks = {check.name: check for check in record.checks}
    for required in rules.checks:
        if not required.required:
            continue
        result = checks.get(required.name)
        if (
            result is None
            or result.version != required.version
            or not result.required
            or result.scope != required.scope
            or result.status != "pass"
        ):
            return False
    return all(
        record.metrics.get(name) is not None
        for name in (rules.primary_metric, *rules.secondary_tolerances)
    )


def _loss(name: str, value: float) -> float:
    return -value if name in ("kge", "nse", "correlation") else abs(value)


def decide(
    baseline: EvaluationRecord,
    alternatives: tuple[EvaluationRecord, ...],
    rules: AcceptanceSpec,
) -> DecisionRecord:
    """Compare on one split. Exact primary ties retain an eligible comparator."""
    if any(item.split_id != baseline.split_id for item in alternatives):
        raise ValueError("cannot compare evaluations from different splits")
    records = (baseline, *alternatives)
    if len({item.id for item in records}) != len(records):
        raise ValueError("duplicate evaluation identities")
    allowed = [item for item in records if eligible(item, rules)]
    if not allowed:
        return DecisionRecord(
            baseline.id,
            (),
            None,
            None,
            "no_eligible_model",
            rules.digest,
            ("No successful alternative has all required scientific evidence",),
            (),
        )
    sign = 1 if rules.direction == "minimize" else -1
    ranked = sorted(allowed, key=lambda item: (sign * item.metrics[rules.primary_metric], item.id))
    baseline_eligible = baseline in allowed
    selected = baseline if baseline_eligible else ranked[0]
    reasons = []
    if baseline_eligible:
        for candidate in ranked:
            if candidate.id == baseline.id:
                continue
            gain = sign * (
                baseline.metrics[rules.primary_metric] - candidate.metrics[rules.primary_metric]
            )
            if gain <= 0 or gain < rules.minimum_gain:
                reasons.append(f"{candidate.id}: primary gain below required improvement")
                continue
            if any(
                _loss(name, candidate.metrics[name]) - _loss(name, baseline.metrics[name])
                > tolerance
                for name, tolerance in rules.secondary_tolerances.items()
            ):
                reasons.append(f"{candidate.id}: secondary tolerance exceeded")
                continue
            selected = candidate
            break
    outcome = "retain_baseline" if selected.id == baseline.id else "accepted_candidate"
    return DecisionRecord(
        baseline.id,
        tuple(item.id for item in allowed),
        selected.id,
        selected.configuration,
        outcome,
        rules.digest,
        tuple(reasons) or ("Applied frozen eligibility and ranking rules",),
        (),
    )
