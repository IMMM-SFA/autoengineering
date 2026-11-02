"""Shared-clock PVDAQ 1278 inputs for conditional power reconstruction."""

from __future__ import annotations

import numpy as np
import pandas as pd

COLUMNS = (
    "measured_on",
    "poa_irradiance__3056",
    "ambient_temp_f__3058",
    "wind_speed_mph__3060",
    "ac_power__3081",
)


def normalize(frame, start, end):
    """Preserve source order, reject wrong periods, and mask unusable samples.

    This trusted function returns labels. Only its forcing and development
    partitions may be supplied to advisory workers.
    """
    if not set(COLUMNS) <= set(frame.columns) or len(frame) > 200000:
        raise ValueError("Solar source columns or row cap differ")
    time = pd.to_datetime(frame.measured_on, errors="raise")
    if time.dt.tz is not None or time.isna().any():
        raise ValueError("Solar source requires a finite shared local clock")
    if len(time) == 0 or time.min() < pd.Timestamp(start) or time.max() >= pd.Timestamp(end):
        raise ValueError("Solar source falls outside the declared partition")
    if not time.is_monotonic_increasing:
        raise ValueError("Solar source timestamps are not ordered")
    poa, ambient, wind, labels = (
        pd.to_numeric(frame[name], errors="coerce").to_numpy(dtype=float) for name in COLUMNS[1:]
    )
    ambient = (ambient - 32) * 5 / 9
    wind = wind * 0.44704
    labels = labels / 1000
    finite = np.isfinite(np.column_stack((poa, ambient, wind, labels))).all(axis=1)
    mask = (
        finite
        & (poa >= 100)
        & (poa <= 1400)
        & (ambient >= -20)
        & (ambient <= 60)
        & (wind >= 0)
        & (wind <= 40)
        & (labels >= -0.5)
        & (labels <= 157.5)
        & ~time.duplicated(keep=False).to_numpy()
    )
    if mask.sum() < 200:
        raise ValueError("Solar partition has fewer than 200 usable daytime samples")
    # Do not make predictions on invalid drivers. Mask is frozen independently
    # of predictions and identical for every route.
    return {
        "time": time.astype(str).to_numpy(dtype="U32"),
        "poa": poa,
        "ambient_c": ambient,
        "wind_m_s": wind,
        "labels_kw": labels,
        "mask": mask,
    }


def evaluate(data, scale):
    from examples.utility.solar_1278_development import predict

    if not np.isfinite(scale) or not 0.5 <= scale <= 1.05:
        raise ValueError("Solar effective derating exceeds the frozen domain")
    mask = data["mask"]
    y = data["labels_kw"][mask]
    p = predict(data["poa"][mask], data["ambient_c"][mask], data["wind_m_s"][mask], scale)
    if not np.isfinite(p).all() or (p < 0).any() or (p > 150 + 1e-9).any():
        raise ValueError("Solar predictions violate physical output limits")
    if y.sum() <= 0:
        raise ValueError("Solar power-sum bias denominator is not positive")
    return {
        "ac_rmse": float(np.sqrt(np.mean((p - y) ** 2))),
        "power_sum_bias": float(p.sum() / y.sum() - 1),
        "rows": int(mask.sum()),
    }
