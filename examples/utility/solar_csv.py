"""Bounded trusted CSV normalization with caller-pinned sensor and time semantics.

No timestamp, interval, quality or equipment convention is inferred. Source bytes
may include reserved labels and belong only in trusted preparation. This parser
is not a worker grant, an OS boundary or scientific admission.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import io
from pathlib import Path
import re
from typing import Literal

from autoengineering.campaign.serialization import Record, digest
from autoengineering.utility.contracts import sha256
from examples.utility.solar_intervals import AverageValue, DriverSample, align, instant, stamp
from examples.utility.solar_metadata import SolarMetadataReview
from examples.utility.solar_partitions import prepare as prepare_partitions

MAX_BYTES = 32 * 1024**2
MAX_ROWS = 100_000
MAX_COLUMNS = 128
MAX_FIELD = 4096
ROLES = ("ac", "poa", "temperature", "wind")
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
TIME = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:Z|[+-][0-9]{2}:[0-9]{2})?\Z"
)


@dataclass(frozen=True)
class CsvSensor(Record):
    role: Literal["ac", "poa", "temperature", "wind"]
    value_header: str
    timestamp_header: str
    units: Literal["kW", "W/m2", "C", "F", "m/s", "mph"]
    clock: Literal["offset_in_text", "fixed_utc_offset"]
    fixed_offset_minutes: int | None
    support: Literal["start_average", "end_average", "instantaneous"]
    duration_seconds: int | None
    duration_header: str | None
    availability_delay_seconds: int
    missing_tokens: tuple[str, ...]
    quality_header: str | None
    quality_good: tuple[str, ...]
    quality_bad: tuple[str, ...]
    absent_quality: Literal["unflagged_unqualified"] = "unflagged_unqualified"
    blank_value_missing: Literal[True] = True
    blank_quality: Literal["bad", "reject"] = "reject"

    def _validate(self):
        allowed = {
            "ac": ("kW",),
            "poa": ("W/m2",),
            "temperature": ("C", "F"),
            "wind": ("m/s", "mph"),
        }
        if (
            self.units not in allowed[self.role]
            or not self.value_header
            or not self.timestamp_header
            or not 0 <= self.availability_delay_seconds <= 86400
        ):
            raise ValueError("solar CSV channel semantics differ")
        if self.clock == "offset_in_text":
            if self.fixed_offset_minutes is not None:
                raise ValueError("offset-bearing solar timestamps cannot have a clock override")
        elif (
            self.fixed_offset_minutes is None
            or not -720 <= self.fixed_offset_minutes <= 840
            or self.fixed_offset_minutes % 15
        ):
            raise ValueError("solar CSV fixed clock requires an explicit bounded offset")
        average = self.role in ("ac", "poa")
        if average != (self.support != "instantaneous"):
            raise ValueError("solar CSV average and sample roles differ")
        if average:
            if (self.duration_seconds is None) == (self.duration_header is None):
                raise ValueError("solar CSV averages require exactly one duration source")
            if self.duration_seconds is not None:
                _duration(self.duration_seconds)
        elif self.duration_seconds is not None or self.duration_header is not None:
            raise ValueError("solar CSV samples cannot have average durations")
        if (
            not self.missing_tokens
            or len(set(self.missing_tokens)) != len(self.missing_tokens)
            or any(
                len(t) > 64 for t in (*self.missing_tokens, *self.quality_good, *self.quality_bad)
            )
        ):
            raise ValueError("solar CSV tokens must be explicit and bounded")
        if self.quality_header is None:
            if self.quality_good or self.quality_bad:
                raise ValueError("solar CSV quality tokens need their declared column")
        elif (
            not self.quality_good
            or not self.quality_bad
            or len(set((*self.quality_good, *self.quality_bad)))
            != len(self.quality_good) + len(self.quality_bad)
        ):
            raise ValueError("solar CSV quality token classes must be disjoint")


@dataclass(frozen=True)
class SolarCsvPlan(Record):
    schema: Literal["utility-solar-csv-v1"]
    source_sha256: str
    metadata_review_digest: str
    semantics_review_digest: str
    headers: tuple[str, ...]
    sensors: tuple[CsvSensor, ...]

    def _validate(self):
        for value in (
            self.source_sha256,
            self.metadata_review_digest,
            self.semantics_review_digest,
        ):
            sha256(value)
        if (
            not 1 <= len(self.headers) <= MAX_COLUMNS
            or len(set(self.headers)) != len(self.headers)
            or any(not h or len(h) > MAX_FIELD or "\x00" in h for h in self.headers)
            or tuple(s.role for s in self.sensors) != ROLES
            or len({s.value_header for s in self.sensors}) != 4
        ):
            raise ValueError("solar CSV header or channel inventory differs")
        for sensor in self.sensors:
            names = (
                sensor.value_header,
                sensor.timestamp_header,
                sensor.duration_header,
                sensor.quality_header,
            )
            if any(n is not None and n not in self.headers for n in names):
                raise ValueError("solar CSV channel uses an undeclared header")


@dataclass(frozen=True)
class ParsedSolarCsv(Record):
    schema: Literal["utility-parsed-solar-csv-v1"]
    plan_digest: str
    source_sha256: str
    row_count: int
    ac: tuple[AverageValue, ...]
    poa: tuple[AverageValue, ...]
    temperature: tuple[DriverSample, ...]
    wind: tuple[DriverSample, ...]
    qualification: Literal["not_admitted"] = "not_admitted"

    def _validate(self):
        sha256(self.plan_digest)
        sha256(self.source_sha256)
        if not 1 <= self.row_count <= MAX_ROWS or any(
            len(getattr(self, r)) != self.row_count for r in ROLES
        ):
            raise ValueError("parsed solar CSV rows are incomplete")


def _duration(value):
    if type(value) is not int or not 60 <= value <= 3600 or value % 60:
        raise ValueError("solar CSV duration must be an explicit whole number of minutes")
    return value


def _timestamp(text, sensor):
    if not TIME.fullmatch(text):
        raise ValueError("solar CSV timestamp format differs")
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if sensor.clock == "offset_in_text":
        if value.tzinfo is None:
            raise ValueError("solar CSV timestamp requires an explicit offset")
    else:
        if value.tzinfo is not None:
            raise ValueError("solar CSV fixed clock requires an unzoned source timestamp")
        value = value.replace(tzinfo=timezone(timedelta(minutes=sensor.fixed_offset_minutes)))
    return value.astimezone(timezone.utc)


def _value(row, sensor):
    token = row[sensor.value_header].strip(" \t")
    if not token or token in sensor.missing_tokens:
        value = None
    else:
        if not NUMBER.fullmatch(token):
            raise ValueError("solar CSV value encoding differs")
        value = float(token)
        if not float("-inf") < value < float("inf"):
            raise ValueError("solar CSV numeric value is not finite")
    if sensor.quality_header is None:
        good = True
    else:
        quality = row[sensor.quality_header]
        if quality == "" and sensor.blank_quality == "bad":
            return value, False
        if quality not in (*sensor.quality_good, *sensor.quality_bad):
            raise ValueError("solar CSV quality code is undeclared")
        good = quality in sensor.quality_good
    return value, good and value is not None


def parse_csv(plan, content, metadata_review):
    """Read exact caller-pinned UTF-8 bytes; errors never contain source cells."""
    try:
        if (
            not isinstance(plan, SolarCsvPlan)
            or not isinstance(metadata_review, SolarMetadataReview)
            or metadata_review.digest != plan.metadata_review_digest
            or metadata_review.csv_header != plan.sensors[0].value_header
            or not isinstance(content, bytes)
            or len(content) > MAX_BYTES
            or hashlib.sha256(content).hexdigest() != plan.source_sha256
        ):
            raise ValueError("solar CSV source or channel metadata identity differs")
        reader = csv.reader(io.StringIO(content.decode("utf-8"), newline=""), strict=True)
        if tuple(next(reader)) != plan.headers:
            raise ValueError("solar CSV header differs")
        columns = {role: [] for role in ROLES}
        count = 0
        for cells in reader:
            if (
                count >= MAX_ROWS
                or len(cells) != len(plan.headers)
                or any(len(c) > MAX_FIELD or "\x00" in c for c in cells)
            ):
                raise ValueError("solar CSV row or field envelope differs")
            row = dict(zip(plan.headers, cells, strict=True))
            for sensor in plan.sensors:
                when = _timestamp(row[sensor.timestamp_header], sensor)
                value, good = _value(row, sensor)
                if sensor.support == "instantaneous":
                    record = DriverSample(
                        stamp(when),
                        stamp(when + timedelta(seconds=sensor.availability_delay_seconds)),
                        value,
                        good,
                    )
                    if columns[sensor.role] and instant(columns[sensor.role][-1].timestamp) >= when:
                        raise ValueError("solar CSV samples must be strictly ordered")
                else:
                    seconds = sensor.duration_seconds
                    if seconds is None:
                        token = row[sensor.duration_header]
                        if not re.fullmatch(r"[0-9]{1,4}", token):
                            raise ValueError("solar CSV interval duration encoding differs")
                        seconds = _duration(int(token))
                    start, end = (
                        (when, when + timedelta(seconds=seconds))
                        if sensor.support == "start_average"
                        else (when - timedelta(seconds=seconds), when)
                    )
                    record = AverageValue(
                        stamp(start),
                        stamp(end),
                        stamp(end + timedelta(seconds=sensor.availability_delay_seconds)),
                        value,
                        good,
                    )
                    if columns[sensor.role] and instant(columns[sensor.role][-1].end) > start:
                        raise ValueError("solar CSV averages must be ordered without overlap")
                columns[sensor.role].append(record)
            count += 1
        return ParsedSolarCsv(
            "utility-parsed-solar-csv-v1",
            plan.digest,
            plan.source_sha256,
            count,
            *(tuple(columns[r]) for r in ROLES),
        )
    except Exception:
        pass
    raise ValueError("solar CSV normalization failed") from None


def source_binding_digest(plan):
    return digest(
        {
            "csv_plan": plan.digest,
            "source_sha256": plan.source_sha256,
            "parser_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
    )


def prepare_csv(partition_plan, csv_plan, source, metadata_review, public_root, private_root):
    """Delay source acquisition until the existing role claims have committed.

    The callable must return already authorized source bytes inside trusted
    preparation. No fetcher is installed here. Normalized outputs retain their
    existing not-admitted flags and contain no raw source table.
    """

    def rows():
        try:
            alignment = partition_plan.alignment
            if (
                alignment.source_digest != source_binding_digest(csv_plan)
                or alignment.semantics_review_digest != csv_plan.semantics_review_digest
                or partition_plan.hardware_review_digest != metadata_review.digest
                or alignment.temperature_units != csv_plan.sensors[2].units
                or alignment.wind_units != csv_plan.sensors[3].units
            ):
                raise ValueError("solar CSV alignment or partition binding differs")
            parsed = parse_csv(csv_plan, source(), metadata_review)
            yield from align(
                alignment,
                ac=parsed.ac,
                poa=parsed.poa,
                temperature=parsed.temperature,
                wind=parsed.wind,
            )
            return
        except Exception:
            pass
        raise ValueError("solar CSV preparation failed") from None

    return prepare_partitions(partition_plan, rows(), public_root, private_root)
