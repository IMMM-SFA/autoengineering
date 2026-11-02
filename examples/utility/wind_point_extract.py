"""Bounded public development point acquisition; no model or reserve-year access.

Prepare freezes geography, source metadata, source/code pins and all three stage
allowances before dispatch. Failed scopes are retained and cannot auto retry.
Large neighbouring chunks stay in the local acquisition cache, not public reports.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import io
from pathlib import Path

import numpy as np

from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from examples.utility.wind_range import WindObjectPin
from examples.utility.wind_point_range import PointRangeLimits, WindPointRangeFile
from examples.utility.wind_point import nearest_site, utc_axis, decode_variable

STAGES = ("coordinates", "speed", "direction")
SOURCE_FILES = ("wind_point_extract.py", "wind_point.py", "wind_point_range.py", "wind_range.py")


def save(root, name, value):
    durable_write(root / name, canonical_json(value).encode())


def read(root, name):
    path = root / name
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 * 1024**2:
        raise ValueError("point acquisition metadata scope differs")
    return unique_json(path.read_text())


def sources():
    return {
        name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        for name in SOURCE_FILES
    }


def prepare(metadata, output):
    metadata = checked_directory(metadata)
    original = read(metadata, "metadata-result.json")
    expanded = read(metadata, "metadata-replay.json")
    if original["status"] != "complete" or not expanded["reproduced_original_metadata"]:
        raise ValueError("point acquisition requires verified source metadata")
    pin = WindObjectPin.from_dict(original["pin"])
    if pin.year != 2007:
        raise ValueError("initial acquisition is restricted to 2007 development")
    root = Path(output).absolute()
    if (
        root.exists()
        or root.is_symlink()
        or root.is_relative_to(metadata)
        or metadata.is_relative_to(root)
    ):
        raise ValueError("point acquisition needs an absent separate output")
    if any(p.is_symlink() for p in root.parents) or ".." in root.parts:
        raise ValueError("point acquisition output traverses a symlink or parent")
    root.mkdir(mode=0o700)
    limits = PointRangeLimits()
    request = {
        "schema": "utility-wind-point-acquisition-v1",
        "pin": pin.to_dict(),
        "source_metadata_digest": digest(original),
        "expanded_metadata_digest": digest(expanded),
        "dataset_metadata": original["datasets"],
        "dataset_attributes": expanded["expanded_metadata"],
        "point": {"latitude": 41.5, "longitude": -70.5, "height_m": 80},
        "nearest_policy": "spherical_great_circle_lowest_index_tie",
        "coordinate_meta_tolerance_deg": 1e-5,
        "stage_order": list(STAGES),
        "stage_limits": limits.to_dict(),
        "total_request_cap": 3 * limits.requests,
        "total_response_byte_cap": 3 * limits.response_bytes,
        "sources": sources(),
        "scope_digest": digest(str(root)),
        "phase": "development_only",
        "scientific_starts_allowed": 0,
        "automatic_retries": 0,
        "task_admitted": False,
    }
    save(root, "request.json", request)
    for name in SOURCE_FILES:
        durable_write(root / (name + ".txt"), Path(__file__).with_name(name).read_bytes())
    return request


def plain(value):
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode()
    if isinstance(value, np.generic):
        return value.item()
    return value


def dataset(file, name, request):
    import h5py

    if not isinstance(file.get(name, getlink=True), h5py.HardLink):
        raise ValueError("point acquisition refuses indirect HDF5 links")
    item = file[name]
    expected = request["dataset_metadata"][name]
    if (
        not isinstance(item, h5py.Dataset)
        or list(item.shape) != expected["shape"]
        or str(item.dtype) != expected["dtype"]
        or (list(item.chunks) if item.chunks else None) != expected["chunks"]
        or item.compression != expected["compression"]
    ):
        raise ValueError("point dataset structure differs from reviewed metadata")
    for key, value in request["dataset_attributes"][name]["attributes"].items():
        if plain(item.attrs[key]) != value:
            raise ValueError("point dataset attributes differ from reviewed metadata")
    return item


def record_for(root, stage):
    folder = root / stage / "ranges"
    folder.mkdir(mode=0o700)

    def record(event, raw):
        if raw is not None:
            filename = f"{event['request']:03d}-{event['lo']:016x}.bin"
            with (folder / filename).open("xb") as file:
                file.write(raw)
            event["body_file"] = filename
        save(folder, f"{event['request']:03d}-{event['status']}.json", event)
        if event["request"] % 16 == 0 and raw is not None:
            print(canonical_json({"stage": stage, "range_requests": event["request"]}), flush=True)

    return record


@contextmanager
def stage_file(root, stage, request):
    import h5py

    folder = root / stage
    folder.mkdir(mode=0o700)
    save(
        folder,
        "intent.json",
        {"stage": stage, "request_digest": digest(request), "limits": request["stage_limits"]},
    )
    reader = WindPointRangeFile(
        WindObjectPin.from_dict(request["pin"]),
        PointRangeLimits.from_dict(request["stage_limits"]),
        record=record_for(root, stage),
    )
    try:
        with h5py.File(reader, "r") as file:
            yield file
    except Exception:
        save(
            folder,
            "failure.json",
            {"status": "unverified", "stats": reader.stats(), "automatic_retry_allowed": False},
        )
        raise
    else:
        save(folder, "complete.json", {"status": "complete", "stats": reader.stats()})
    finally:
        reader.close()


def execute(root, *, expected_digest):
    root = checked_directory(root)
    q = read(root, "request.json")
    if (
        digest(q) != expected_digest
        or q["schema"] != "utility-wind-point-acquisition-v1"
        or q["sources"] != sources()
        or q["scope_digest"] != digest(str(root))
        or q["phase"] != "development_only"
        or q["stage_order"] != list(STAGES)
        or q["point"] != {"latitude": 41.5, "longitude": -70.5, "height_m": 80}
        or q["nearest_policy"] != "spherical_great_circle_lowest_index_tie"
        or q["scientific_starts_allowed"] != 0
        or q["automatic_retries"] != 0
    ):
        raise ValueError("point acquisition request, source or scope differs")
    limits = PointRangeLimits.from_dict(q["stage_limits"])
    if (
        q["total_request_cap"] != 3 * limits.requests
        or q["total_response_byte_cap"] != 3 * limits.response_bytes
        or WindObjectPin.from_dict(q["pin"]).year != 2007
    ):
        raise ValueError("point acquisition aggregate allowance differs")
    marker = root / "execution-intent.json"
    if marker.exists() or marker.is_symlink():
        raise StoreError("point acquisition consumed; no automatic retry")
    save(
        root,
        marker.name,
        {
            "request_digest": expected_digest,
            "total_request_cap": q["total_request_cap"],
            "total_response_byte_cap": q["total_response_byte_cap"],
        },
    )
    with stage_file(root, "coordinates", q) as file:
        coordinates = dataset(file, "coordinates", q)
        step = coordinates.chunks[0]

        def blocks():
            for start in range(0, len(coordinates), step):
                yield coordinates[start : start + step]

        selected = nearest_site(blocks(), q["point"]["latitude"], q["point"]["longitude"])
        meta = dataset(file, "meta", q)[selected["index"]]
        if (
            abs(float(meta["latitude"]) - selected["latitude"]) > q["coordinate_meta_tolerance_deg"]
            or abs(float(meta["longitude"]) - selected["longitude"])
            > q["coordinate_meta_tolerance_deg"]
        ):
            raise ValueError("coordinate and site metadata rows disagree")
        selected["meta_latitude"] = float(meta["latitude"])
        selected["meta_longitude"] = float(meta["longitude"])
        selected["meta_offshore_code"] = int(meta["offshore"])
        time = dataset(file, "time_index", q)
        axis = utc_axis(time[:], q["pin"]["year"], plain(time.attrs["time_zone"]))
    # Commit geographic choice before any wind speed/direction values are read.
    save(
        root,
        "selected-cell.json",
        selected
        | {
            "request_digest": expected_digest,
            "axis_digest": digest(axis),
            "hour_count": len(axis),
            "wind_values_read": False,
        },
    )
    values = {}
    masks = {}
    raw_values = {}
    for kind in ("speed", "direction"):
        name = "windspeed_80m" if kind == "speed" else "winddirection_80m"
        with stage_file(root, kind, q) as file:
            item = dataset(file, name, q)
            if item.shape != (len(axis), selected["sites_checked"]):
                raise ValueError("weather axes differ")
            raw_values[kind] = item[:, selected["index"]]
            values[kind], masks[kind] = decode_variable(
                raw_values[kind],
                kind=kind,
                units=plain(item.attrs["units"]),
                scale_factor=plain(item.attrs["scale_factor"]),
                fill_value=plain(item.attrs["fill_value"]),
            )
    buffer = io.BytesIO()
    np.savez_compressed(
        buffer,
        time_utc=np.array(axis, dtype="U20"),
        raw_speed=raw_values["speed"],
        raw_direction=raw_values["direction"],
        speed_m_s=values["speed"],
        direction_source_deg=values["direction"],
        speed_valid=masks["speed"],
        direction_valid=masks["direction"],
    )
    raw = buffer.getvalue()
    durable_write(root / "point.npz", raw)
    stages = {name: read(root / name, "complete.json") for name in STAGES}
    requests = sum(v["stats"]["requests"] for v in stages.values())
    transferred = sum(v["stats"]["received_response_bytes"] for v in stages.values())
    if requests > q["total_request_cap"] or transferred > q["total_response_byte_cap"]:
        raise ValueError("point acquisition aggregate accounting exceeded")
    done = {
        "schema": "utility-wind-point-acquisition-completion-v1",
        "request_digest": expected_digest,
        "point_sha256": hashlib.sha256(raw).hexdigest(),
        "point_bytes": len(raw),
        "selected_cell_digest": digest(read(root, "selected-cell.json")),
        "hour_count": len(axis),
        "valid_speed_rows": int(masks["speed"].sum()),
        "valid_direction_rows": int(masks["direction"].sum()),
        "common_valid_rows": int((masks["speed"] & masks["direction"]).sum()),
        "stages": stages,
        "range_requests": requests,
        "response_body_bytes": transferred,
        "models_started": 0,
        "reserved_objects_accessed": False,
        "direction_convention_qualified": False,
        "task_admitted": False,
        "physical_binding_qualified": False,
        "source_full_hash_verified": False,
    }
    save(root, "complete.json", done)
    return done


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("metadata", type=Path)
    prep.add_argument("output", type=Path)
    run = sub.add_parser("execute")
    run.add_argument("root", type=Path)
    run.add_argument("--expected-digest", required=True)
    a = p.parse_args()
    result = (
        prepare(a.metadata, a.output)
        if a.command == "prepare"
        else execute(a.root, expected_digest=a.expected_digest)
    )
    print(canonical_json({"schema": result["schema"], "digest": digest(result)}))


if __name__ == "__main__":
    main()
