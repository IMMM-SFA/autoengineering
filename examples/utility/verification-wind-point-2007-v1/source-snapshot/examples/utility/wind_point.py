"""Pure geographic selection and source decoding for development WIND point data.

No network, PyWake, optimization, private-source admission or resource-bin policy.
Missing raw sentinels are masked before scaling; directions are not reinterpreted.
"""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
import math

import numpy as np

EARTH_RADIUS_M = 6371008.8


def nearest_site(blocks, latitude, longitude):
    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise ValueError("invalid requested geographic point")
    best = None
    offset = 0
    target = np.radians([latitude, longitude])
    for block in blocks:
        values = np.asarray(block, dtype=float)
        if (
            values.ndim != 2
            or values.shape[1] != 2
            or not len(values)
            or not np.isfinite(values).all()
            or (abs(values[:, 0]) > 90).any()
            or (abs(values[:, 1]) > 180).any()
        ):
            raise ValueError("coordinate block is invalid")
        rad = np.radians(values)
        delta_lat = rad[:, 0] - target[0]
        delta_lon = (rad[:, 1] - target[1] + np.pi) % (2 * np.pi) - np.pi
        scores = (
            np.sin(delta_lat / 2) ** 2
            + np.cos(target[0]) * np.cos(rad[:, 0]) * np.sin(delta_lon / 2) ** 2
        )
        scores = np.clip(scores, 0, 1)
        local = int(np.argmin(scores))
        score = float(scores[local])
        index = offset + local
        if best is None or (score, index) < (best["haversine_score"], best["index"]):
            best = {
                "index": index,
                "latitude": float(values[local, 0]),
                "longitude": float(values[local, 1]),
                "haversine_score": score,
                "distance_m": 2 * EARTH_RADIUS_M * math.asin(math.sqrt(score)),
            }
        offset += len(values)
    if best is None:
        raise ValueError("coordinate source has no sites")
    return best | {
        "sites_checked": offset,
        "policy": "spherical_great_circle_lowest_index_tie",
        "earth_radius_m": EARTH_RADIUS_M,
    }


def utc_axis(values, year, timezone_attribute):
    if type(year) is not int or not 2007 <= year <= 2011 or timezone_attribute != "UTC":
        raise ValueError("wind point requires declared development-year UTC support")
    expected = (366 if calendar.isleap(year) else 365) * 24
    if len(values) != expected:
        raise ValueError("wind year has incomplete hourly support")
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    result = []
    for i, value in enumerate(values):
        text = value.decode("ascii") if isinstance(value, (bytes, np.bytes_)) else value
        if not isinstance(text, str) or len(text) > 32:
            raise ValueError("wind timestamp type differs")
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp.utcoffset() != timedelta(0) or stamp != start + timedelta(hours=i):
            raise ValueError("wind hourly axis is not the complete declared UTC year")
        result.append(stamp.isoformat().replace("+00:00", "Z"))
    return tuple(result)


def decode_variable(raw, *, kind, units, scale_factor, fill_value):
    if kind not in ("speed", "direction") or units != ("m s-1" if kind == "speed" else "degree"):
        raise ValueError("wind variable or source units differ")
    if type(scale_factor) not in (int, float) or scale_factor != 100 or fill_value != 65535:
        raise ValueError("unreviewed source scaling or fill convention")
    values = np.asarray(raw)
    if values.ndim != 1 or values.dtype.kind != "u" or values.dtype.itemsize != 2:
        raise ValueError("wind variable requires an unsigned 16-bit point vector")
    valid = values != 65535
    decoded = np.full(len(values), np.nan, dtype=float)
    decoded[valid] = values[valid].astype(float) / 100.0
    upper = 100 if kind == "speed" else 360
    if (decoded[valid] < 0).any() or (decoded[valid] > upper).any():
        raise ValueError("wind source value exceeds the reviewed domain")
    return decoded, valid
