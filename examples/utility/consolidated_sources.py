"""One-use trusted source staging; stdout contains metadata only.

The prospective study identity is fixed before acquisition. Final suite manifests
must reference this identity and all completed receipts. No scoring occurs here.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import time
import urllib.request
import zipfile

from autoengineering.campaign.store import durable_write

DEFAULT = Path("outputs/consolidated-execution-v1")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def save(path, value):
    durable_write(path, (json.dumps(value, indent=2, allow_nan=False) + "\n").encode())
    path.chmod(0o600)


def scope(root, task):
    root = root.absolute()
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("Source staging refuses symlink paths")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.stat().st_mode & 0o077:
        raise ValueError("Source staging requires an owner-private root")
    path = root / task
    path.mkdir(mode=0o700, exist_ok=False)
    binding = Path("examples/utility/consolidated/task-bindings.json")
    identity = sha(binding)
    save(
        path / "intent.json",
        {
            "task": task,
            "study_binding_sha256": identity,
            "producer_sha256": sha(Path(__file__)),
            "retry": "never automatically retry an incomplete scope",
        },
    )
    return path


def solar(path):
    import pandas as pd
    import numpy as np
    from examples.utility.solar_1278_inputs import normalize

    listing = json.loads(Path("examples/utility/consolidated/source-inventory.json").read_text())
    keys = sorted(
        next(r for r in listing["records"] if r["source"] == "solar1278-2013")["keys"],
        key=lambda k: k.split("__date_")[1],
    )
    if len(keys) != 365 or len(set(keys)) != 365:
        raise ValueError("Solar source listing must contain 365 distinct objects")
    raw = path / "raw"
    raw.mkdir(mode=0o700)
    started = time.monotonic()

    def fetch(key):
        if time.monotonic() - started > 600:
            raise ValueError("Solar acquisition elapsed cap exceeded")
        name = key.rsplit("/", 1)[1]
        url = "https://oedi-data-lake.s3.amazonaws.com/" + key
        save(
            raw / (name + ".intent.json"),
            {"url": url, "maximum_bytes": 1000000, "socket_timeout_seconds": 30},
        )
        # One request per object. No implicit retry on failures.
        with urllib.request.urlopen(url, timeout=30) as response:
            body = response.read(1000001)
        if len(body) > 1000000:
            raise ValueError("Solar object exceeds byte reservation")
        frame = pd.read_csv(io.BytesIO(body))
        dates = pd.to_datetime(frame.measured_on, errors="raise")
        expected = name.split("__date_")[1].removesuffix(".csv").replace("_", "-")
        if len(dates) == 0 or not (dates.dt.strftime("%Y-%m-%d") == expected).all():
            raise ValueError("Solar source day differs from object key")
        durable_write(raw / name, body)
        (raw / name).chmod(0o600)
        receipt = {"key": key, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
        save(raw / (name + ".complete.json"), receipt)
        return frame, receipt

    frames, receipts = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i, (frame, receipt) in enumerate(pool.map(fetch, keys), 1):
            frames.append(frame)
            receipts.append(receipt)
            if i % 50 == 0:
                print(f"Solar objects staged: {i}/365", flush=True)
    data = normalize(pd.concat(frames, ignore_index=True), "2013-01-01", "2014-01-01")
    np.savez(path / "confirmation.npz", **data)
    (path / "confirmation.npz").chmod(0o600)
    return {
        "objects": receipts,
        "rows": len(data["mask"]),
        "usable_rows": int(data["mask"].sum()),
        "payload_sha256": sha(path / "confirmation.npz"),
        "actual_response_bytes": sum(r["bytes"] for r in receipts),
        "network_requests": len(receipts),
        "elapsed_seconds": time.monotonic() - started,
    }


def hydrology(path):
    from examples.utility.hydrology_camels import CamelsDaymetSource, iter_rows
    from examples.utility.hydrology_partitions import DailyHydrologyPlan, prepare

    prior = Path("examples/utility/verification-camels-acquisition-v1/inspection-v2")
    source = CamelsDaymetSource.from_json((prior / "source.json").read_text())
    plan = DailyHydrologyPlan.from_json((prior / "inspection-plan.json").read_text())
    archive = Path("outputs/camels-acquisition-v1/archive.zip")
    if sha(archive) != source.archive_sha256:
        raise ValueError("CAMELS archive identity changed")
    with zipfile.ZipFile(archive) as zipped:
        forcing = zipped.read(source.forcing_member)
        flow = zipped.read(source.streamflow_member)
    public, private = path / "development", path / "confirmation"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    prepare(plan, iter_rows(source, plan, forcing, flow), public, private)
    save(path / "plan.json", plan.to_dict())
    return {
        "archive_sha256": source.archive_sha256,
        "files": {
            str(p.relative_to(path)): sha(p)
            for p in path.rglob("*.json")
            if p.name != "intent.json"
        },
        "confirmation_values_exported": False,
    }


def wind(path):
    import numpy as np
    from examples.utility.wind_annual_scoring import AnnualWindDrivers

    receipts = []
    for year in (2012, 2013, 2014):
        origin = Path(f"outputs/wind-reserve-preparation-v1/{year}")
        receipt = json.loads((origin / "complete.json").read_text())
        if sha(origin / "point.npz") != receipt["point_sha256"]:
            raise ValueError("Prepared wind payload changed")
        with np.load(origin / "point.npz", allow_pickle=False) as payload:
            drivers = AnnualWindDrivers(
                year,
                receipt["request_digest"],
                tuple(payload["time_utc"].tolist()),
                payload["speed_m_s"],
                payload["direction_deg"],
            )
        raw = np.column_stack((drivers.speed_m_s, drivers.direction_deg)).astype("<f8").tobytes()
        target = path / f"year-{year}.f64le"
        durable_write(target, raw)
        target.chmod(0o600)
        receipts.append(
            {
                "year": year,
                "sha256": sha(target),
                "bytes": len(raw),
                "driver_manifest": drivers.manifest,
                "driver_manifest_digest": drivers.manifest_digest,
            }
        )
    return {"years": receipts, "scientific_model_calls": 0}


def wind_development(path):
    from examples.utility.wind_range import WindObjectPin
    from examples.utility.wind_reserve_extract import extract_development

    receipts = []
    for year in (2008, 2009, 2010, 2011):
        year_root = path / str(year)
        year_root.mkdir(mode=0o700)
        url = f"https://nrel-pds-wtk.s3.us-west-2.amazonaws.com/conus/v1.0.0/wtk_conus_{year}.h5"
        save(path / f"{year}-metadata-intent.json", {"url": url, "requests": 1})
        with urllib.request.urlopen(
            urllib.request.Request(url, method="HEAD"), timeout=30
        ) as response:
            pin = WindObjectPin(
                "utility-wind-development-object-v1",
                year,
                int(response.headers["Content-Length"]),
                response.headers["ETag"],
            )
        save(path / f"{year}-pin.json", pin.to_dict())
        print(f"Preparing wind development year {year}", flush=True)
        receipt = extract_development(pin, year_root)
        receipts.append(
            {
                "year": year,
                "point_sha256": receipt["point_sha256"],
                "hours": receipt["hours"],
                "receipt_sha256": sha(year_root / "complete.json"),
            }
        )
        print(f"Staged wind development year {year}", flush=True)
    return {"years": receipts, "scientific_model_calls": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=("solar", "hydrology", "wind", "wind_development"))
    parser.add_argument("--root", type=Path, default=DEFAULT)
    args = parser.parse_args()
    os.umask(0o077)
    path = scope(args.root, args.task)
    start = time.monotonic()
    try:
        result = globals()[args.task](path)
        result.update(
            task=args.task,
            status="staged",
            elapsed_seconds=time.monotonic() - start,
            study_binding_sha256=json.loads((path / "intent.json").read_text())[
                "study_binding_sha256"
            ],
        )
        save(path / "complete.json", result)
        print(
            json.dumps(
                {"task": args.task, "status": "staged", "receipt": str(path / "complete.json")}
            )
        )
    except Exception:
        save(
            path / "failure.json",
            {
                "status": "incomplete",
                "elapsed_seconds": time.monotonic() - start,
                "retry_authorized": False,
            },
        )
        raise RuntimeError(
            "Source staging failed; inspect metadata receipts, preserve consumed scope"
        ) from None


if __name__ == "__main__":
    main()
