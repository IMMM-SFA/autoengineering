"""Support-aware alignment of normalized solar channels in trusted preparation.

No source timestamps, timezone codes, hardware joins or quality flags are inferred.
Averages may be combined into coarser windows, never split into finer estimates.
Sample drivers use an explicit causal hold with bounded observation age. This
module provides neither source admission nor an OS boundary for private labels.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.campaign.serialization import Record
from autoengineering.utility.contracts import sha256

MAX_SOURCE_ROWS = 1_000_000
MAX_TOTAL_SOURCE_ROWS = 2_000_000
MAX_TARGET_ROWS = 500_000


def instant(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None or dt.microsecond:
            raise ValueError
        normalized = dt.astimezone(timezone.utc)
        if normalized.microsecond:
            raise ValueError
        return normalized
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise ValueError("solar timestamps require explicit offsets and whole seconds") from None


def stamp(value):
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class SolarAlignmentPlan(Record):
    schema: Literal["utility-solar-interval-alignment-v1"]
    source_digest: str
    semantics_review_digest: str
    start: str
    end: str
    step_seconds: int
    max_sample_age_seconds: int
    temperature_units: Literal["F", "C"]
    wind_units: Literal["mph", "m/s"]
    sample_policy: Literal["causal_hold"]

    def _validate(self):
        sha256(self.source_digest)
        sha256(self.semantics_review_digest)
        start, end = instant(self.start), instant(self.end)
        if not 60 <= self.step_seconds <= 3600 or self.step_seconds % 60:
            raise ValueError("solar target step must be a declared whole number of minutes")
        duration = (end - start).total_seconds()
        if (
            duration <= 0
            or duration % self.step_seconds
            or start.second
            or end.second
            or duration / self.step_seconds > MAX_TARGET_ROWS
        ):
            raise ValueError("solar target range must contain bounded whole intervals")
        if not 1 <= self.max_sample_age_seconds <= 86400:
            raise ValueError("solar sample age requires an explicit bounded policy")


@dataclass(frozen=True)
class AverageValue(Record):
    start: str
    end: str
    available_at: str
    value: float | None
    quality_ok: bool

    def _validate(self):
        start, end, available = instant(self.start), instant(self.end), instant(self.available_at)
        if start >= end or available < end:
            raise ValueError(
                "solar average needs positive support and availability after completion"
            )
        if self.quality_ok and self.value is None:
            raise ValueError("valid solar averages require a finite value")


@dataclass(frozen=True)
class DriverSample(Record):
    timestamp: str
    available_at: str
    value: float | None
    quality_ok: bool

    def _validate(self):
        if instant(self.available_at) < instant(self.timestamp):
            raise ValueError("solar sample availability cannot precede observation")
        if self.quality_ok and self.value is None:
            raise ValueError("valid solar samples require a finite value")


@dataclass(frozen=True)
class AlignedInterval(Record):
    start: str
    end: str
    duration_seconds: int
    ac_kw: float | None
    poa_w_m2: float | None
    temperature_c: float | None
    wind_m_s: float | None
    ac_energy_kwh: float | None
    drivers_usable: bool
    usable: bool
    reasons: tuple[str, ...]
    alignment_digest: str
    alignment_implementation_digest: str

    def _validate(self):
        sha256(self.alignment_digest)
        sha256(self.alignment_implementation_digest)
        start, end = instant(self.start), instant(self.end)
        if (
            end <= start
            or (end - start).total_seconds() != self.duration_seconds
            or stamp(start) != self.start
            or stamp(end) != self.end
        ):
            raise ValueError("solar aligned rows require exact canonical UTC support")
        forcing = (self.poa_w_m2, self.temperature_c, self.wind_m_s)
        driver_reasons = tuple(r for r in self.reasons if not r.startswith("ac:"))
        if (
            self.usable != (not self.reasons)
            or self.drivers_usable != (not driver_reasons)
            or (self.drivers_usable and any(v is None for v in forcing))
            or (not self.drivers_usable and any(v is not None for v in forcing))
            or (self.usable and (self.ac_kw is None or self.ac_energy_kwh is None))
            or (not self.usable and (self.ac_kw is not None or self.ac_energy_kwh is not None))
        ):
            raise ValueError("solar alignment requires complete driver and common score masks")
        if self.drivers_usable and (self.poa_w_m2 < 0 or self.wind_m_s < 0):
            raise ValueError("solar aligned physical forcing differs")
        if self.usable and not math.isclose(
            self.ac_energy_kwh,
            self.ac_kw * (self.duration_seconds / 3600),
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("solar aligned integrated energy differs")


def _averages(rows, remaining):
    result = []
    for row in rows:
        if len(result) >= min(MAX_SOURCE_ROWS, remaining):
            raise ValueError("solar average or total source row bound exceeded")
        if not isinstance(row, AverageValue):
            raise ValueError("solar alignment requires normalized average records")
        item = (
            instant(row.start),
            instant(row.end),
            instant(row.available_at),
            row.value,
            row.quality_ok,
        )
        if result and item[0] < result[-1][1]:
            raise ValueError("solar average supports must be ordered without overlap")
        result.append(item)
    return result


def _samples(rows, remaining):
    result = []
    for row in rows:
        if len(result) >= min(MAX_SOURCE_ROWS, remaining):
            raise ValueError("solar sample or total source row bound exceeded")
        if not isinstance(row, DriverSample):
            raise ValueError("solar alignment requires normalized sample records")
        item = (instant(row.timestamp), instant(row.available_at), row.value, row.quality_ok)
        if result and (item[0] <= result[-1][0] or item[1] < result[-1][1]):
            raise ValueError(
                "solar samples and availability must be ordered without duplicate observations"
            )
        result.append(item)
    return result


def _mean(rows, ends, start, end, minimum=None):
    index = bisect_right(ends, start)
    cursor = start
    terms, reasons = [], set()
    duration = (end - start).total_seconds()
    while index < len(rows) and rows[index][0] < end:
        left, right, available, value, good = rows[index]
        if left < start or right > end:
            reasons.add("support_crosses_target")
        if left != cursor:
            reasons.add("gap")
        if not good:
            reasons.add("quality")
        if available > end:
            reasons.add("late_available")
        if good and value is not None and minimum is not None and value < minimum:
            reasons.add("below_domain")
        if value is not None and good and start <= left < right <= end:
            terms.append(value * ((right - left).total_seconds() / duration))
        cursor = right
        index += 1
    if cursor != end:
        reasons.add("gap")
    return (None, reasons) if reasons else (math.fsum(terms), reasons)


def _held_mean(rows, arrivals, start, end, max_age, convert, minimum=None):
    index = bisect_right(arrivals, start) - 1
    cursor = start
    terms, reasons = [], set()
    duration = (end - start).total_seconds()
    while cursor < end:
        following = index + 1
        boundary = min(end, rows[following][1]) if following < len(rows) else end
        if boundary > cursor:
            if index < 0:
                reasons.add("no_available_sample")
            else:
                observed, available, value, good = rows[index]
                if (boundary - observed).total_seconds() > max_age:
                    reasons.add("stale_sample")
                if not good:
                    reasons.add("quality")
                if good and value is not None:
                    if minimum is not None and convert(value) < minimum:
                        reasons.add("below_domain")
                    terms.append(convert(value) * ((boundary - cursor).total_seconds() / duration))
            cursor = boundary
        if following < len(rows) and rows[following][1] <= cursor:
            index = following
        elif boundary == end:
            break
    return (None, reasons) if reasons else (math.fsum(terms), reasons)


def align(plan, *, ac, poa, temperature, wind, on_progress=None):
    """Yield UTC rows with distinct driver continuity and common scoring masks.

    AC and POA are interval averages available by prediction time (target end).
    Sample drivers are held only after their declared availability, with age
    measured from the observation timestamp. A point at target end contributes
    zero duration. The resulting driver means are causal-hold estimates, not
    recovered continuous measurements. The optional progress callback gets only
    completed-row counts. Source qualification and private partitioning are separate.
    """
    if not isinstance(plan, SolarAlignmentPlan):
        raise ValueError("solar alignment requires a frozen plan")
    ac = _averages(ac, MAX_TOTAL_SOURCE_ROWS)
    poa = _averages(poa, MAX_TOTAL_SOURCE_ROWS - len(ac))
    temperature = _samples(temperature, MAX_TOTAL_SOURCE_ROWS - len(ac) - len(poa))
    wind = _samples(wind, MAX_TOTAL_SOURCE_ROWS - len(ac) - len(poa) - len(temperature))
    ac_ends, poa_ends = [r[1] for r in ac], [r[1] for r in poa]
    temp_arrivals, wind_arrivals = [r[1] for r in temperature], [r[1] for r in wind]
    temp_convert = (
        (lambda value: (value - 32) * (5 / 9)) if plan.temperature_units == "F" else float
    )
    wind_convert = (lambda value: value * 0.44704) if plan.wind_units == "mph" else float
    alignment_identity = plan.digest
    implementation_identity = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    cursor, stop = instant(plan.start), instant(plan.end)
    count = 0
    while cursor < stop:
        end = cursor + timedelta(seconds=plan.step_seconds)
        power, power_reasons = _mean(ac, ac_ends, cursor, end)
        irradiance, poa_reasons = _mean(poa, poa_ends, cursor, end, minimum=0.0)
        temp, temp_reasons = _held_mean(
            temperature, temp_arrivals, cursor, end, plan.max_sample_age_seconds, temp_convert
        )
        speed, wind_reasons = _held_mean(
            wind, wind_arrivals, cursor, end, plan.max_sample_age_seconds, wind_convert, minimum=0.0
        )
        reasons = tuple(
            sorted(
                f"{name}:{reason}"
                for name, values in (
                    ("ac", power_reasons),
                    ("poa", poa_reasons),
                    ("temperature", temp_reasons),
                    ("wind", wind_reasons),
                )
                for reason in values
            )
        )
        drivers_ok = not (poa_reasons or temp_reasons or wind_reasons)
        energy = None if reasons else power * (plan.step_seconds / 3600)
        if drivers_ok and not all(math.isfinite(v) for v in (irradiance, temp, speed)):
            raise ValueError("solar aligned forcing arithmetic must remain finite")
        if not reasons and not all(math.isfinite(v) for v in (power, energy)):
            raise ValueError("solar aligned observation arithmetic must remain finite")
        yield AlignedInterval(
            stamp(cursor),
            stamp(end),
            plan.step_seconds,
            None if reasons else power,
            irradiance if drivers_ok else None,
            temp if drivers_ok else None,
            speed if drivers_ok else None,
            energy,
            drivers_ok,
            not reasons,
            reasons,
            alignment_identity,
            implementation_identity,
        )
        cursor = end
        count += 1
        if on_progress is not None and (count % 4096 == 0 or cursor == stop):
            on_progress(count)
