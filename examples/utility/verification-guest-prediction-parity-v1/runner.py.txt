"""One bounded native reference for an existing exposed guest inference.

The original guest never reruns. A separately reserved native worker replays the
same fit, seed, drivers and axis. This checks platform/transport parity, not an
independent scientific implementation, predictive skill or private admission.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
from pathlib import Path
import sys
from uuid import uuid4

from autoengineering.campaign.artifacts import read_arrays, read_bytes
from autoengineering.optimization import NpzReadLimits
from autoengineering.campaign.execution import supervise
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest
from autoengineering.campaign.spec import ExecutionSpec
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.confirmation import read_selected_state
from autoengineering.utility.guest_executor import GuestRoutingExecutor
from autoengineering.utility.guest_receipts import VerifiedGuestExecution
from autoengineering.utility.inference_execution import (
    FrozenInferenceJob,
    FrozenInferenceResult,
    executor_identity,
)
from autoengineering.utility.scoring import CompositeConfirmationGrant
from autoengineering.utility.store import SuiteStore
from examples.utility import guest_inference_smoke as fixture

ATOL = 1e-10
RTOL = 1e-12


def compare_arrays(native, guest):
    import numpy as np

    if set(native) != set(guest) or not native:
        raise ValueError("parity output names differ")
    records = {}
    for name in sorted(native):
        left, right = np.asarray(native[name]), np.asarray(guest[name])
        if (
            left.dtype != right.dtype
            or left.shape != right.shape
            or left.dtype.kind != "f"
            or left.size == 0
            or not np.all(np.isfinite(left))
            or not np.all(np.isfinite(right))
        ):
            raise ValueError("parity output shape, dtype or finite values differ")
        delta = np.abs(left.astype(np.float64) - right.astype(np.float64))
        allowed = ATOL + RTOL * np.maximum(np.abs(left), np.abs(right))
        records[name] = {
            "shape": list(left.shape),
            "dtype": str(left.dtype),
            "max_abs_difference": float(np.max(delta)),
            "bitwise_equal": left.tobytes() == right.tobytes(),
            "within_tolerance": bool(np.all(delta <= allowed)),
        }
    return records


def original(smoke, expected_digest):
    smoke = checked_directory(smoke)
    done, request = fixture.read(smoke, "complete.json"), fixture.read(smoke, "request.json")
    if digest(done) != expected_digest or done["request_digest"] != digest(request):
        raise ValueError("original guest completion changed")
    grant = CompositeConfirmationGrant.from_dict(request["grant"])
    if grant.inference.forcing.prior_exposure != "exposed":
        raise ValueError("parity permits only the exposed authored fixture")
    store = SuiteStore(smoke / "suite")
    observed = GuestRoutingExecutor.for_recovery(
        store, grant, Path("/unavailable-original-work")
    ).recover(grant)
    if (
        observed != VerifiedGuestExecution.from_dict(done["execution"])
        or observed.status != "success"
    ):
        raise ValueError("original guest inference is not a verified success")
    return smoke, request, store, grant, observed


def prepare(smoke, *, completion_digest, output):
    smoke, previous, store, grant, observed = original(smoke, completion_digest)
    output = Path(output).absolute()
    fixture.build.guest_image._public_directory(output.parent)
    if (
        output.exists()
        or output.is_symlink()
        or output.is_relative_to(smoke)
        or smoke.is_relative_to(output)
    ):
        raise ValueError("parity output must be absent and separate from original smoke")
    output.mkdir(mode=0o700)
    fixture.save(
        output,
        "preparation-intent.json",
        {
            "original_completion_digest": completion_digest,
            "native_inference_starts_reserved": 1,
            "new_guest_starts": 0,
            "fitting_starts": 0,
            "scoring_starts": 0,
            "atol": ATOL,
            "rtol": RTOL,
        },
    )
    work = output / "work"
    work.mkdir(mode=0o700)
    for name in ("artifacts", "attempts", "control"):
        (work / name).mkdir(mode=0o700)
    sources = tuple(ArtifactRef.from_dict(v) for v in previous["sources"])
    lock = ArtifactRef.from_dict(previous["lock"])
    driver = grant.inference.forcing.artifact
    staged = ArtifactRef(
        f"artifacts/{driver.sha256}/drivers.npz",
        driver.sha256,
        driver.size_bytes,
        "application/x-npz",
        "inference",
        {},
    )
    job = FrozenInferenceJob(
        "utility-frozen-inference-job-v1",
        grant,
        executor_identity(store.spec.source_digest, lock),
        store.spec.source_digest,
        sources,
        lock,
        uuid4().hex,
        staged,
    )
    binding = {
        "grant": grant.digest,
        "executor": job.executor_digest,
        "nonce": job.nonce,
        "job": job.digest,
    }
    fixture.save(work, "job.json", job.to_dict())
    fixture.save(work, "intent.json", binding)
    fixture.save(work, "claim.json", binding | {"scope": job.claim_scope(work)})
    bound = read_selected_state(store.root, grant.inference.selected_state)
    assets = {
        ref.path: (ref, store.root)
        for ref in (
            grant.inference.selected_state,
            grant.inference.runtime_profile,
            *bound.training.references(),
        )
    }
    for ref in (
        *bound.model.source_bundle,
        lock,
        *(
            r
            for r in sources
            if r.path.startswith("src/autoengineering/") and r.path.endswith(".py")
        ),
    ):
        assets[ref.path] = (ref, smoke / "source")
    for ref, origin in assets.values():
        fixture.private_parents(work, Path(ref.path).parent)
        durable_write(work / ref.path, read_bytes(origin, ref, max_bytes=fixture.MAX_FILE))
    fixture.save(
        output, "driver-copy-intent.json", {"driver": driver.to_dict(), "prior_exposure": "exposed"}
    )
    fixture.private_parents(work, Path(staged.path).parent)
    durable_write(
        work / staged.path, read_bytes(smoke / "drivers", driver, max_bytes=fixture.MAX_FILE)
    )
    guest_result = observed.result
    for name, ref in (
        ("guest-outputs.npz", guest_result.outputs),
        ("guest-predictions.json", guest_result.predictions),
    ):
        durable_write(output / name, read_bytes(store.root, ref, max_bytes=8 * 1024**2))
    request = {
        "schema": "utility-native-guest-parity-request-v1",
        "original_completion_digest": completion_digest,
        "original_execution": observed.to_dict(),
        "native_job_digest": job.digest,
        "root_scope": digest(str(output)),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "native_python_digest": hashlib.sha256(sys.version.encode()).hexdigest(),
        "scientific_native_starts_reserved": 1,
        "new_guest_starts_allowed": 0,
        "fitting_starts_allowed": 0,
        "scoring_starts_allowed": 0,
        "automatic_retries": 0,
        "timeout_seconds": grant.inference.timeout_seconds,
        "atol": ATOL,
        "rtol": RTOL,
        "guest_outputs_sha256": guest_result.outputs.sha256,
        "guest_predictions_sha256": guest_result.predictions.sha256,
        "runtime_qualified": False,
    }
    fixture.save(output, "request.json", request)
    durable_write(output / "runner.py.txt", Path(__file__).read_bytes())
    return request


def execute(root, *, expected_digest):
    root = checked_directory(root)
    q = fixture.read(root, "request.json")
    if (
        digest(q) != expected_digest
        or q["root_scope"] != digest(str(root))
        or q["runner_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        or q["native_python_digest"] != hashlib.sha256(sys.version.encode()).hexdigest()
    ):
        raise ValueError("parity request, source, interpreter or scope changed")
    if (
        q["scientific_native_starts_reserved"],
        q["new_guest_starts_allowed"],
        q["fitting_starts_allowed"],
        q["scoring_starts_allowed"],
        q["automatic_retries"],
        q["atol"],
        q["rtol"],
        q["runtime_qualified"],
    ) != (1, 0, 0, 0, 0, ATOL, RTOL, False):
        raise ValueError("parity bounds or original tolerances changed")
    if (root / "execution-intent.json").exists() or (root / "execution-intent.json").is_symlink():
        raise ValueError("parity attempt consumed; no retry")
    work = checked_directory(root / "work")
    job = FrozenInferenceJob.from_dict(fixture.read(work, "job.json"))
    if (
        job.digest != q["native_job_digest"]
        or job.grant.inference.forcing.prior_exposure != "exposed"
    ):
        raise ValueError("parity job changed")
    fixture.save(
        root,
        "execution-intent.json",
        {
            "request_digest": expected_digest,
            "native_starts_reserved": 1,
            "guest_starts_allowed": 0,
            "fitting_starts_allowed": 0,
        },
    )
    from autoengineering.campaign.runtime import RUNTIME_ROOT

    report = supervise(
        (sys.executable, "-m", "autoengineering.utility.inference_worker", str(work / "job.json")),
        root=work,
        attempt_id="native-reference",
        campaign_id="authored-native-parity",
        settings=ExecutionSpec(
            ("hydrology-learned-routing-v1",), timeout_seconds=q["timeout_seconds"]
        ),
        cwd=RUNTIME_ROOT,
        launch_nonce=job.nonce,
    )
    if report.status != "success" or not report.stopped or not report.receipt_valid:
        raise ValueError("native reference did not complete; original reservation remains charged")
    result = FrozenInferenceResult.from_dict(fixture.read(work, "worker-result.json"))
    if (
        result.status != "success"
        or result.grant_digest != job.grant.digest
        or result.nonce != job.nonce
        or result.executor_digest != job.executor_digest
    ):
        raise ValueError("native result differs from original job or physical acceptance")
    native_bytes = read_bytes(work, result.outputs, max_bytes=8 * 1024**2)
    guest_bytes = fixture.raw(root, "guest-outputs.npz")
    if hashlib.sha256(guest_bytes).hexdigest() != q["guest_outputs_sha256"]:
        raise ValueError("original guest outputs changed")
    rows = len(job.grant.inference.forcing.ports[0].time.dates)
    member = 16 * rows + 4096
    limits = NpzReadLimits(
        max_compressed_bytes=8 * 1024**2,
        max_members=16,
        max_member_bytes=member,
        max_total_bytes=16 * member,
    )
    native = read_arrays(work, result.outputs, limits=limits)
    guest_ref = ArtifactRef.from_dict(q["original_execution"]["result"]["outputs"])
    guest = read_arrays(root, replace(guest_ref, path="guest-outputs.npz"), limits=limits)
    arrays = compare_arrays(native, guest)
    prediction = read_bytes(work, result.predictions, max_bytes=1024**2)
    guest_prediction = fixture.raw(root, "guest-predictions.json")
    if hashlib.sha256(guest_prediction).hexdigest() != q["guest_predictions_sha256"]:
        raise ValueError("original guest prediction changed")
    from autoengineering.campaign.serialization import unique_json

    native_doc, guest_doc = (unique_json(raw.decode()) for raw in (prediction, guest_prediction))
    if {k: v for k, v in native_doc.items() if k != "prediction"} != {
        k: v for k, v in guest_doc.items() if k != "prediction"
    }:
        raise ValueError("prediction model, partition or selection binding differs")
    prediction_equal = native_doc == guest_doc
    complete = {
        "schema": "utility-native-guest-parity-completion-v1",
        "request_digest": expected_digest,
        "native_job_digest": job.digest,
        "native_result": result.to_dict(),
        "comparisons": arrays,
        "all_outputs_within_tolerance": all(v["within_tolerance"] for v in arrays.values()),
        "prediction_document_exact": prediction_equal,
        "native_scientific_starts": 1,
        "new_guest_starts": 0,
        "new_fitting_starts": 0,
        "scoring_starts": 0,
        "atol": ATOL,
        "rtol": RTOL,
        "runtime_qualified": False,
    }
    durable_write(root / "native-outputs.npz", native_bytes)
    durable_write(root / "native-predictions.json", prediction)
    fixture.save(root, "complete.json", complete)
    return complete


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("smoke", type=Path)
    prep.add_argument("output", type=Path)
    prep.add_argument("--completion-digest", required=True)
    run = sub.add_parser("execute")
    run.add_argument("root", type=Path)
    run.add_argument("--expected-digest", required=True)
    args = parser.parse_args()
    result = (
        prepare(args.smoke, completion_digest=args.completion_digest, output=args.output)
        if args.command == "prepare"
        else execute(args.root, expected_digest=args.expected_digest)
    )
    print(canonical_json({"digest": digest(result), "schema": result["schema"]}))


if __name__ == "__main__":
    main()
