"""Trusted, bounded reserve-point preparation; never a worker-facing data tool.

Separate from the unchanged development extractor. Output stays in an owned
private directory. Three stages each have the existing 128-request, 64 MiB,
120-second logical limits. This is not OS deadline or privacy qualification.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import re
from typing import Literal

import numpy as np

from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write
from examples.utility.wind_annual_scoring import _axis
from examples.utility.wind_point import decode_variable, nearest_site
from examples.utility.wind_point_range import PointRangeLimits, WindPointRangeFile
from examples.utility.wind_range import WindObjectPin


@dataclass(frozen=True)
class ReserveObjectPin(WindObjectPin):
    schema: Literal["utility-wind-reserve-object-v1"]

    def _validate(self):
        if self.year not in (2012, 2013, 2014) or not 0 < self.size_bytes <= 2 * 1024**4:
            raise ValueError("reserve source must be one of the three declared years")
        if not re.fullmatch(r'"[0-9a-f]{32}(?:-[0-9]{1,6})?"', self.etag):
            raise ValueError("reserve source requires a strong opaque ETag")

    @property
    def url(self):
        version = "v1.1.0" if self.year == 2014 else "v1.0.0"
        return f"https://nrel-pds-wtk.s3.us-west-2.amazonaws.com/conus/{version}/wtk_conus_{self.year}.h5"


def reserve_axis(values, year, zone):
    expected = _axis(year)
    if year not in (2012, 2013, 2014) or zone != "UTC" or len(values) != len(expected):
        raise ValueError("reserve source needs complete declared UTC hourly support")
    for raw, want in zip(values, expected, strict=True):
        text = raw.decode("ascii") if isinstance(raw, (bytes, np.bytes_)) else str(raw)
        if len(text) > 32:
            raise ValueError("invalid reserve timestamp")
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if stamp.isoformat().replace("+00:00", "Z") != want:
            raise ValueError("reserve timestamp differs from declared UTC axis")
    return expected


def _plain(value):
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode()
    return value.item() if isinstance(value, np.generic) else value


def extract(pin: ReserveObjectPin, private_root: Path, *, reader_factory=WindPointRangeFile):
    """One consumed preparation attempt. Returns metadata only, never weather."""
    if type(pin) is not ReserveObjectPin:
        raise ValueError("explicit reserve pin required")
    return _extract(
        pin, private_root, reader_factory, reserve_axis, "utility-wind-reserve-extraction-v1"
    )


def extract_development(pin: WindObjectPin, root: Path, *, reader_factory=WindPointRangeFile):
    """The four declared additional development years, with the same range caps."""
    from examples.utility.wind_point import utc_axis

    if type(pin) is not WindObjectPin or pin.year not in (2008, 2009, 2010, 2011):
        raise ValueError("explicit remaining development-year pin required")
    return _extract(pin, root, reader_factory, utc_axis, "utility-wind-development-extraction-v2")


def _extract(pin, private_root, reader_factory, axis_reader, schema):
    import h5py

    root = checked_directory(private_root)
    if any(root.iterdir()):
        raise ValueError("reserve preparation directory is consumed or not empty")
    limits = PointRangeLimits()
    request = {
        "schema": schema,
        "pin": pin.to_dict(),
        "point": [41.5, -70.5],
        "height_m": 80,
        "limits_each_stage": limits.to_dict(),
        "stages": ["coordinates", "speed", "direction"],
        "automatic_retry": False,
    }
    # Exclusive creation prevents two writers from sharing a preparation scope.
    with (root / "intent.json").open("xb") as handle:
        handle.write(canonical_json(request).encode())
    (root / "intent.json").chmod(0o600)
    stages = {}

    @contextmanager
    def stage(name):
        folder = root / name
        folder.mkdir(mode=0o700)

        def record(event, raw):
            # Keep byte hashes and reservations, not copies of weather chunks.
            durable_write(
                folder / f"{event['request']}-{event['status']}.json",
                canonical_json(event).encode(),
            )

        reader = reader_factory(pin, limits, record=record)
        try:
            with h5py.File(reader, "r") as file:
                yield file
        finally:
            stages[name] = reader.stats()
            durable_write(folder / "accounting.json", canonical_json(stages[name]).encode())
            reader.close()

    def dataset(file, name):
        if not isinstance(file.get(name, getlink=True), h5py.HardLink):
            raise ValueError("reserve source rejects external or soft links")
        item = file[name]
        if not isinstance(item, h5py.Dataset):
            raise ValueError("reserve source requires a dataset")
        return item

    try:
        with stage("coordinates") as file:
            coords = dataset(file, "coordinates")
            if len(coords.shape) != 2 or coords.shape[1] != 2 or not 1 <= len(coords) <= 3_000_000:
                raise ValueError("reserve coordinate shape is outside bounds")
            chosen = nearest_site(
                (coords[i : i + 32768] for i in range(0, len(coords), 32768)), 41.5, -70.5
            )
            meta = dataset(file, "meta")[chosen["index"]]
            if any(abs(float(meta[key]) - chosen[key]) > 1e-5 for key in ("latitude", "longitude")):
                raise ValueError("reserve geographic metadata mismatch")
            times = dataset(file, "time_index")
            if times.shape != (len(_axis(pin.year)),):
                raise ValueError("reserve time axis has wrong size")
            axis = axis_reader(times[:], pin.year, _plain(times.attrs["time_zone"]))
        durable_write(root / "selected-cell.json", canonical_json(chosen).encode())
        decoded = {}
        for kind, name in (("speed", "windspeed_80m"), ("direction", "winddirection_80m")):
            with stage(kind) as file:
                item = dataset(file, name)
                if item.shape != (len(axis), chosen["sites_checked"]):
                    raise ValueError("reserve weather shape differs")
                values, mask = decode_variable(
                    item[:, chosen["index"]],
                    kind=kind,
                    units=_plain(item.attrs["units"]),
                    scale_factor=_plain(item.attrs["scale_factor"]),
                    fill_value=_plain(item.attrs["fill_value"]),
                )
                if not mask.all():
                    raise ValueError("reserve source has missing joint hours")
                decoded[kind] = values
        buffer = io.BytesIO()
        np.savez_compressed(
            buffer,
            time_utc=np.array(axis, dtype="U20"),
            speed_m_s=decoded["speed"],
            direction_deg=decoded["direction"],
        )
        payload = buffer.getvalue()
        durable_write(root / "point.npz", payload)
        receipt = {
            "request_digest": digest(request),
            "year": pin.year,
            "hours": len(axis),
            "point_sha256": hashlib.sha256(payload).hexdigest(),
            "stages": stages,
            "source_object_sha256": None,
            "task_admitted": False,
            "private_boundary_qualified": False,
        }
        durable_write(root / "complete.json", canonical_json(receipt).encode())
        return receipt
    except Exception:
        durable_write(
            root / "failure.json",
            canonical_json(
                {"status": "incomplete", "automatic_retry": False, "stages": stages}
            ).encode(),
        )
        raise ValueError(
            "reserve preparation incomplete; inspect private accounting, do not retry"
        ) from None
