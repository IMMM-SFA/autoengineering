"""Prepare and consume one local 2007 hourly baseline parity scope, without retry.

Limits count top-level wake calls and curve-reference calls, not internal solver
operations. Elapsed checks do not qualify OS deadline or aggregate memory control.
"""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import distribution, version
from pathlib import Path
import platform
import time

import numpy as np

from autoengineering.adapters.python import run_lifecycle
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write
from examples.utility.wind import ROOT
from examples.utility.wind_hourly import POLICY, SOURCE_FILES, WindHourly, read_point
from examples.utility.wind_parameters import WindGeometry

POINT_ROOT = ROOT / "examples/utility/verification-wind-point-2007-v1/public"
POINT_SHA = "b0539c5cb91bb6aa7a6ec642342492cab9494403e9d9cb339fa45f1783a6cca9"
ASSUMPTIONS = {
    "schema": "utility-wind-hourly-development-assumptions-v1",
    "direction": "Assume source angles are wind-from, clockwise from north for development.",
    "basis": "SAM WIND Toolkit CSV documentation supplies related convention, not raw HDF5 proof.",
    "direction_source": "https://samrepo.nlr.gov/help/weather_format_csv_wind.html",
    "raw_hdf_direction_qualified": False,
    "height": "Use source 80 m fields directly with explicit 80 m hub height, no shear correction.",
    "turbine": "PyWake V80 linear curves on authored 80 m hardware; not a certified installation.",
    "turbine_source": "https://topfarm.pages.windenergy.dtu.dk/PyWake/notebooks/WindTurbines.html",
    "quadrature": "Each instantaneous hourly source value represents one hour of modeled power.",
    "density": "No air-density or observed availability correction.",
    "purpose": "Development baseline direct/wrapped parity, no layout selection or useful-gain claim.",
    "task_admitted": False,
}
CODE = (
    *SOURCE_FILES,
    "examples/utility/wind_hourly_check.py",
    "src/autoengineering/adapters/python.py",
    "src/autoengineering/adapters/contracts.py",
)
BACKEND_FILES = (
    "py_wake/examples/data/hornsrev1.py",
    "py_wake/wind_turbines/_wind_turbines.py",
    "py_wake/wind_turbines/power_ct_functions.py",
    "py_wake/site/xrsite.py",
    "py_wake/wind_farm_models/wind_farm_model.py",
    "py_wake/deficit_models/noj.py",
)


def save(root, name, value):
    durable_write(root / name, canonical_json(value).encode())


def read(root, name):
    return unique_json(
        read_bytes(
            root,
            reference(root, name, media_type="application/json", producer="wind-hourly"),
            max_bytes=4 * 1024**2,
        ).decode()
    )


def pins():
    installed = distribution("py-wake")
    if installed.version != "2.6.20":
        raise ValueError("reviewed hourly backend requires PyWake 2.6.20")
    return {
        "versions": {name: version(name) for name in ("py-wake", "numpy", "scipy", "xarray")},
        "python": platform.python_version(),
        "backend_files": {
            name: hashlib.sha256(Path(installed.locate_file(name)).read_bytes()).hexdigest()
            for name in BACKEND_FILES
        },
        "project_files": {
            name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in CODE
        },
    }


def load_task(request):
    ref = reference(POINT_ROOT, "point.npz", media_type="application/npz", producer="wind-point")
    if ref.to_dict() != request["point_ref"]:
        raise ValueError("development point identity differs")
    data = read_point(POINT_ROOT, ref, 2007)
    return WindHourly(
        WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0)),
        2007,
        tuple(data["time_utc"]),
        data["speed_m_s"],
        data["direction_source_deg"],
        ref.sha256,
        digest(ASSUMPTIONS),
    )


def prepare(output):
    root = Path(output).absolute()
    if (
        root.exists()
        or root.is_symlink()
        or ".." in root.parts
        or any(p.is_symlink() for p in root.parents)
    ):
        raise ValueError("hourly check requires an absent output without symlink traversal")
    ref = reference(POINT_ROOT, "point.npz", media_type="application/npz", producer="wind-point")
    complete = read(POINT_ROOT, "complete.json")
    if (
        ref.sha256 != POINT_SHA
        or ref.sha256 != complete["point_sha256"]
        or digest(complete) != "aa9ef3ecdd47ea9f3f8057b9f6f40f4142d38e18bfb3f9ead6041bcd30156a5c"
        or complete["hour_count"] != 8760
    ):
        raise ValueError("point acquisition completion differs")
    request = {
        "schema": "utility-wind-hourly-parity-request-v1",
        "scope_digest": digest(str(root)),
        "point_ref": ref.to_dict(),
        "acquisition_completion_digest": digest(complete),
        "assumptions": ASSUMPTIONS,
        "policy": POLICY,
        "pins": pins(),
        "wake_calls_cap": 2,
        "curve_reference_calls_cap": 1,
        "automatic_retries": 0,
        "elapsed_application_cap_seconds": 120.0,
        "os_deadline_qualified": False,
        "aggregate_rss_qualified": False,
        "rtol": 1e-12,
        "atol": 1e-10,
        "optimization_calls": 0,
        "training_calls": 0,
        "provider_calls": 0,
        "new_http_requests": 0,
        "task_admitted": False,
    }
    profile = load_task(request)
    request["profile_identity"] = profile.identity
    root.mkdir(mode=0o700)
    save(root, "request.json", request)
    save(root, "assumptions.json", ASSUMPTIONS)
    return request


def execute(output, expected):
    root = checked_directory(output)
    request = read(root, "request.json")
    if (
        digest(request) != expected
        or request["scope_digest"] != digest(str(root))
        or request["pins"] != pins()
        or request["assumptions"] != ASSUMPTIONS
        or request["policy"] != POLICY
    ):
        raise ValueError("hourly request, sources, backend or assumptions changed")
    profile = load_task(request)
    if profile.identity != request["profile_identity"]:
        raise ValueError("hourly profile identity differs")
    if (
        request["wake_calls_cap"],
        request["curve_reference_calls_cap"],
        request["automatic_retries"],
    ) != (2, 1, 0):
        raise ValueError("hourly scientific caps differ")
    # No call can precede the exclusive durable consumed marker.
    save(root, "consumed.json", {"request_digest": expected, "automatic_retry_allowed": False})
    began = time.monotonic()
    wake = curve = 0
    receipts = []
    try:
        context = profile.context(profile.geometry.baseline, root / "scratch")
        values = {}
        for index, label in enumerate(("direct", "wrapped", "curve-reference")):
            if time.monotonic() - began >= request["elapsed_application_cap_seconds"]:
                raise TimeoutError("hourly check application allowance expired")
            wake += int(label != "curve-reference")
            curve += int(label == "curve-reference")
            intent = {
                "request_digest": expected,
                "stage": label,
                "wake_calls_reserved": wake,
                "curve_reference_calls_reserved": curve,
                "unknown_until_receipt": True,
            }
            save(root, f"{index}-intent.json", intent)
            print(
                f"Starting {label}: wake calls {wake}/2, curve reference calls {curve}/1",
                flush=True,
            )
            start = time.monotonic()
            if label == "direct":
                result = profile.physical({}, profile.geometry.baseline)
            elif label == "wrapped":
                lifecycle = run_lifecycle(profile.adapter(), context, {}, (), context.model.outputs)
                if lifecycle.training.status != "not_applicable":
                    raise ValueError("hourly profile unexpectedly trained")
                result = lifecycle.outputs
            else:
                result = profile.reference()
            receipt = {
                "stage": label,
                "elapsed_seconds": time.monotonic() - start,
                "outputs": {k: float(v) for k, v in result.items()},
                "status": "complete",
            }
            save(root, f"{index}-receipt.json", receipt)
            receipts.append(receipt)
            values[label] = receipt["outputs"]
        if time.monotonic() - began >= request["elapsed_application_cap_seconds"]:
            raise TimeoutError("hourly completion exceeded application allowance")
        for name in values["direct"]:
            np.testing.assert_allclose(
                values["direct"][name],
                values["wrapped"][name],
                rtol=request["rtol"],
                atol=request["atol"],
            )
        if profile.identity != request["profile_identity"]:
            raise ValueError("hourly input state mutated")
        result = {
            "status": "complete",
            "request_digest": expected,
            "profile_identity": profile.identity,
            "wake_calls_reserved": wake,
            "curve_reference_calls_reserved": curve,
            "receipts": receipts,
            "direct_wrapped_parity": True,
            "elapsed_seconds": time.monotonic() - began,
            "task_admitted": False,
            "independent_confirmation": False,
            "os_deadline_qualified": False,
            "aggregate_rss_qualified": False,
            "raw_direction_convention_qualified": False,
        }
        save(root, "complete.json", result)
        return result
    except BaseException as error:
        save(
            root,
            "failed.json",
            {
                "request_digest": expected,
                "status": "failed",
                "error_type": type(error).__name__,
                "message": str(error)[:1024],
                "wake_calls_reserved": wake,
                "curve_reference_calls_reserved": curve,
                "completed_receipts": len(receipts),
                "automatic_retry_allowed": False,
            },
        )
        raise


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("phase", choices=("prepare", "execute"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-digest")
    args = parser.parse_args()
    result = (
        prepare(args.output)
        if args.phase == "prepare"
        else execute(args.output, args.expected_digest)
    )
    print(canonical_json({"status": result.get("status", "prepared"), "digest": digest(result)}))


if __name__ == "__main__":
    main()
