"""Bounded CAMELS-US Daymet byte parsing for trusted daily preparation.

No acquisition or archive extraction occurs here. Declared checksums bind bytes,
not source authenticity, rights, exposure or daily timestamp interpretation.
See docs/utility.md for the format references and remaining admission checks.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
import hashlib
import math
from typing import Literal

from autoengineering.campaign.serialization import Record
from autoengineering.utility.contracts import sha256
from autoengineering.utility.exposure import iso_date
from examples.utility.hydrology_partitions import DailyHydrologyPlan, DailyHydrologyRow

FORCING_COLUMNS = (
    "Year",
    "Mnth",
    "Day",
    "Hr",
    "dayl(s)",
    "prcp(mm/day)",
    "srad(W/m2)",
    "swe(mm)",
    "tmax(C)",
    "tmin(C)",
    "vp(Pa)",
)
MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 20000


@dataclass(frozen=True)
class CamelsDaymetSource(Record):
    schema: Literal["utility-camels-us-daymet-source-v1"]
    gauge_id: str
    forcing_sha256: str
    streamflow_sha256: str
    forcing_hour: Literal[0, 12]

    @classmethod
    def from_dict(cls, value):
        if (
            cls is CamelsDaymetSource
            and isinstance(value, Mapping)
            and value.get("schema") == "utility-camels-us-daymet-source-v2"
        ):
            return CamelsArchiveDaymetSource.from_dict(value)
        return super().from_dict(value)

    def _validate(self):
        if len(self.gauge_id) != 8 or any(c not in "0123456789" for c in self.gauge_id):
            raise ValueError("CAMELS source requires its eight-digit gauge ID")
        sha256(self.forcing_sha256)
        sha256(self.streamflow_sha256)


@dataclass(frozen=True, kw_only=True)
class CamelsArchiveDaymetSource(CamelsDaymetSource):
    """Declared legacy-archive provenance, not source or temporal admission.

    Archive identity is supplied by trusted acquisition. This parser receives
    member bytes only and cannot verify their membership in an archive. Modern
    Daymet products require their own parser and prospective source contract.
    """

    schema: Literal["utility-camels-us-daymet-source-v2"]
    archive_sha256: str
    archive_metadata_sha256: str
    huc02: str
    archive_name: Literal["basin_timeseries_v1p2_metForcing_obsFlow.zip"] = (
        "basin_timeseries_v1p2_metForcing_obsFlow.zip"
    )
    product: Literal["camels-us-v1p2-basin-mean-daymet"] = "camels-us-v1p2-basin-mean-daymet"
    date_policy: Literal["same-published-date-no-hour-shift"] = "same-published-date-no-hour-shift"
    calendar_policy: Literal["complete-published-gregorian-no-fill"] = (
        "complete-published-gregorian-no-fill"
    )
    physical_interval: Literal["unresolved"] = "unresolved"
    archive_membership_verified: Literal[False] = False

    def _validate(self):
        super()._validate()
        sha256(self.archive_sha256)
        sha256(self.archive_metadata_sha256)
        if (
            len(self.huc02) != 2
            or any(c not in "0123456789" for c in self.huc02)
            or not 1 <= int(self.huc02) <= 18
        ):
            raise ValueError("legacy CAMELS source requires a CONUS HUC02 code")

    @property
    def forcing_member(self):
        return (
            f"basin_dataset_public_v1p2/basin_mean_forcing/daymet/{self.huc02}/"
            f"{self.gauge_id}_lump_cida_forcing_leap.txt"
        )

    @property
    def streamflow_member(self):
        return (
            f"basin_dataset_public_v1p2/usgs_streamflow/{self.huc02}/"
            f"{self.gauge_id}_streamflow_qc.txt"
        )


def _lines(raw: bytes, expected: str, maximum: int) -> list[str]:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_BYTES:
        raise ValueError("source byte bound")
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("source checksum differs")
    lines = raw.decode("ascii").splitlines()
    if len(lines) > maximum or any(not line.strip() or len(line) > 1024 for line in lines):
        raise ValueError("source line bound or empty row")
    return lines


def _date(parts: list[str]) -> str:
    if any(not value or any(c not in "0123456789" for c in value) for value in parts):
        raise ValueError("invalid source date")
    return date(*(int(value) for value in parts)).isoformat()


def _number(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("nonfinite source number")
    return result


def _parse(source, plan, forcing, streamflow):
    if not isinstance(source, CamelsDaymetSource) or not isinstance(plan, DailyHydrologyPlan):
        raise ValueError("source and plan required")
    if plan.declared_source_digest != source.digest or plan.site_id != f"usgs-{source.gauge_id}":
        raise ValueError("plan source identity differs")
    forcing_lines = _lines(forcing, source.forcing_sha256, MAX_ROWS + 4)
    flow_lines = _lines(streamflow, source.streamflow_sha256, MAX_ROWS)
    if len(forcing_lines) < 5 or tuple(forcing_lines[3].split()) != FORCING_COLUMNS:
        raise ValueError("unsupported forcing columns or units")
    latitude, _elevation, area_m2 = (_number(line) for line in forcing_lines[:3])
    if latitude != plan.latitude_deg or area_m2 / 1e6 != plan.area_km2:
        raise ValueError("forcing basin metadata differs")
    # Elevation is retained in source bytes, but is not used by these PET models.
    if len(forcing_lines) - 4 != len(flow_lines):
        raise ValueError("driver and flow axes differ")
    rows = []
    for driver_line, flow_line in zip(forcing_lines[4:], flow_lines):
        driver, flow = driver_line.split(), flow_line.split()
        if len(driver) != len(FORCING_COLUMNS) or len(flow) != 6:
            raise ValueError("unsupported source row")
        day = _date(driver[:3])
        if flow[0] != source.gauge_id or _date(flow[1:4]) != day:
            raise ValueError("flow gauge or date differs")
        if driver[3] != str(source.forcing_hour):
            raise ValueError("forcing hour differs; no implicit date shift")
        dayl, precip, radiation, swe, tmax, tmin, vapor = map(_number, driver[4:])
        if (
            any(value == -999.0 for value in (dayl, precip, radiation, swe, tmax, tmin, vapor))
            or not 0 <= dayl <= 86400
            or min(precip, radiation, swe, vapor) < 0
        ):
            raise ValueError("missing or invalid drivers")
        q = _number(flow[4])
        if q == -999.0:
            q = None
        elif q < 0:
            raise ValueError("unknown negative streamflow sentinel")
        if any(not 33 <= ord(char) <= 126 for char in flow[5]):
            raise ValueError("invalid flow quality flag")
        rows.append(DailyHydrologyRow(day, precip, tmin, tmax, q, flow[5]))
    # Date selection never depends on label values. No sorting, joining or filling.
    start, end = iso_date(plan.windows[0].start), iso_date(plan.windows[-1].end)
    expected = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    if [row.date for row in rows] != expected:
        raise ValueError("source dates differ from the frozen plan")
    return rows


def iter_rows(
    source: CamelsDaymetSource, plan: DailyHydrologyPlan, forcing: bytes, streamflow: bytes
) -> Iterator[DailyHydrologyRow]:
    """Validate the complete bounded pair before yielding any canonical rows.

    Pass this iterator directly to hydrology_partitions.prepare so its immutable
    scope claims precede parsing. Call only in the trusted preparation context.
    Errors omit source lines, labels and underlying exception text.
    """
    try:
        yield from _parse(source, plan, forcing, streamflow)
    except Exception:
        raise ValueError("CAMELS Daymet parsing failed") from None
