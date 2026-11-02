"""Review PVDAQ AC-channel metadata without observations or inferred hardware joins.

CSV headers follow sensor_name. Hardware joins require explicit primary keys;
array order and similar names never supply missing links. This is a metadata
review, not source timing, scientific, exposure or private-runtime admission.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Literal

from autoengineering.campaign.serialization import Record, unique_json
from autoengineering.utility.contracts import sha256

MAX_METADATA_BYTES = 128 * 1024


@dataclass(frozen=True)
class SolarMetadataReview(Record):
    schema: Literal["utility-solar-metadata-review-v1"]
    metadata_sha256: str
    system_id: int
    channel_key: str
    metric_id: str
    csv_header: str
    units: Literal["kW"]
    aggregation: Literal["avg"]
    inverter_id: str | None
    module_ids: tuple[str, ...]
    timezone_code: str | None
    data_time_resolution: str | None
    inverter_time_interval_code: str | None
    blockers: tuple[str, ...]
    qualification: Literal["not_admitted"] = "not_admitted"

    def _validate(self):
        sha256(self.metadata_sha256)
        if self.system_id <= 0 or not self.csv_header or not self.blockers:
            raise ValueError("solar metadata review is incomplete")


def _key(value):
    if isinstance(value, bool):
        raise ValueError("boolean hardware key")
    if isinstance(value, int) and value > 0:
        return str(value)
    if isinstance(value, str) and value.isascii() and value.isdigit() and int(value) > 0:
        return str(int(value))
    if value is None or value in ("", "None"):
        return None
    raise ValueError("unsupported hardware key")


def _text(value):
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("metadata text has wrong type")
    return value


def _table(metadata, name, key):
    result = {}
    for row in metadata[name].values():
        ident = _key(row[key])
        if ident is None or ident in result:
            raise ValueError("missing or duplicated metadata primary key")
        result[ident] = row
    return result


def review_ac_metadata(content, *, expected_sha256, system_id, channel_key):
    """Resolve a declared AC header and report explicit equipment-closure gaps.

    Caller supplies already acquired metadata bytes and their expected hash.
    No filesystem, network, observations, model import or calibration is used.
    Missing joins remain named blockers, even when names or list order agree.
    Timestamp support/availability and hardware parameters need separate reviews.
    """
    try:
        sha256(expected_sha256)
        if (
            not isinstance(content, bytes)
            or len(content) > MAX_METADATA_BYTES
            or hashlib.sha256(content).hexdigest() != expected_sha256
            or type(system_id) is not int
            or system_id <= 0
        ):
            raise ValueError("metadata identity differs")
        metadata = unique_json(content.decode("utf-8"))
        system = metadata["System"]
        if type(system["system_id"]) is not int or system["system_id"] != system_id:
            raise ValueError("metadata system differs")
        metrics = metadata["Metrics"]
        metric = metrics[channel_key]
        header = _text(metric["sensor_name"])
        metric_id = _key(metric["metric_id"])
        if (
            not header
            or metric_id is None
            or sum(row.get("sensor_name") == header for row in metrics.values()) != 1
            or sum(_key(row["metric_id"]) == metric_id for row in metrics.values()) != 1
            or metric["common_name"].casefold() != "ac power"
            or metric["units"].casefold() != "kw"
            or metric["raw_units"].casefold() != "kw"
            or metric["aggregation_type"] != "avg"
            or type(metric["calc_scale"]) not in (int, float)
            or metric["calc_scale"] != 1
            or type(metric["calc_offset"]) not in (int, float)
            or metric["calc_offset"] != 0
            or metric.get("calc_details") not in (None, "")
            or metric.get("offline") is not False
        ):
            raise ValueError("AC channel semantics require a separate conversion or review")
        inverters = _table(metadata, "Inverters", "inverter_id")
        modules = _table(metadata, "Modules", "module_id")
        ident = _key(metric.get("source_id"))
        inverter = inverters.get(ident) if metric.get("source_type") == "INVERTER" else None
        blockers = []
        if inverter is None:
            blockers.append("ac_channel_inverter_join_missing")
            ident = None
        module_ids = tuple(
            sorted(
                k
                for k, v in modules.items()
                if ident is not None and _key(v.get("inverter_id")) == ident
            )
        )
        if not module_ids:
            blockers.append("module_inverter_join_missing")
        if inverter is None or any(
            _key(inverter.get(name)) is None for name in ("modules_per_string", "num_strings")
        ):
            blockers.append("string_topology_missing")
        # Codes are facts, never evidence of support endpoints or measurement availability.
        blockers.extend(
            (
                "timestamp_support_and_availability_unqualified",
                "equipment_parameters_and_limits_unqualified",
                "source_quality_and_exposure_unqualified",
            )
        )
        return SolarMetadataReview(
            "utility-solar-metadata-review-v1",
            expected_sha256,
            system_id,
            channel_key,
            metric_id,
            header,
            "kW",
            "avg",
            ident,
            module_ids,
            _text(system.get("timezone_code")),
            _text(system.get("data_time_resolution")),
            _text(inverter.get("time_interval")) if inverter is not None else None,
            tuple(blockers),
        )
    except Exception:
        pass
    raise ValueError("solar AC metadata review failed") from None
