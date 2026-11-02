"""Recompute saved native/guest parity without starting either implementation."""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
from pathlib import Path

from autoengineering.campaign.artifacts import read_arrays
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.optimization import NpzReadLimits
from autoengineering.utility.inference_execution import FrozenInferenceJob, FrozenInferenceResult
from examples.utility import guest_inference_smoke as fixture
from examples.utility.guest_prediction_parity import ATOL, RTOL, compare_arrays


def read_completion(root, *, expected_digest):
    root = Path(root)
    q, done = (fixture.read(root, name) for name in ("request.json", "complete.json"))
    if (
        digest(done) != expected_digest
        or done["request_digest"] != digest(q)
        or done["schema"] != "utility-native-guest-parity-completion-v1"
        or q["schema"] != "utility-native-guest-parity-request-v1"
        or q["runner_sha256"] != hashlib.sha256(fixture.raw(root, "runner.py.txt")).hexdigest()
    ):
        raise ValueError("saved parity source, request or completion changed")
    if (
        done["native_scientific_starts"],
        done["new_guest_starts"],
        done["new_fitting_starts"],
        done["scoring_starts"],
        done["atol"],
        done["rtol"],
        done["runtime_qualified"],
        q["scientific_native_starts_reserved"],
        q["new_guest_starts_allowed"],
        q["fitting_starts_allowed"],
        q["scoring_starts_allowed"],
        q["automatic_retries"],
        q["atol"],
        q["rtol"],
        q["runtime_qualified"],
    ) != (1, 0, 0, 0, ATOL, RTOL, False, 1, 0, 0, 0, 0, ATOL, RTOL, False):
        raise ValueError("saved parity allowances or tolerances changed")
    job = FrozenInferenceJob.from_dict(fixture.read(root, "job.json"))
    result = FrozenInferenceResult.from_dict(done["native_result"])
    report = fixture.read(root, "supervisor-result.json")
    if (
        job.digest != q["native_job_digest"]
        or job.digest != done["native_job_digest"]
        or result != FrozenInferenceResult.from_dict(fixture.read(root, "worker-result.json"))
        or result.status != "success"
        or result.grant_digest != job.grant.digest
        or result.executor_digest != job.executor_digest
        or result.nonce != job.nonce
        or job.grant.inference.forcing.prior_exposure != "exposed"
        or report["status"] != "success"
        or report["stopped"] is not True
        or report["receipt_valid"] is not True
        or report["returncode"] != 0
        or report["identity"]["nonce"] != job.nonce
    ):
        raise ValueError("saved native identity or supervisor acceptance changed")
    guest = q["original_execution"]["result"]
    arrays = []
    rows = len(job.grant.inference.forcing.ports[0].time.dates)
    limits = NpzReadLimits(
        max_compressed_bytes=8 * 1024**2,
        max_members=16,
        max_member_bytes=16 * rows + 4096,
        max_total_bytes=16 * (16 * rows + 4096),
    )
    documents = []
    for prefix, outputs, predictions in (
        ("native", result.outputs, result.predictions),
        (
            "guest",
            ArtifactRef.from_dict(guest["outputs"]),
            ArtifactRef.from_dict(guest["predictions"]),
        ),
    ):
        arrays.append(
            read_arrays(root, replace(outputs, path=prefix + "-outputs.npz"), limits=limits)
        )
        raw = fixture.raw(root, prefix + "-predictions.json")
        if (
            len(raw) != predictions.size_bytes
            or hashlib.sha256(raw).hexdigest() != predictions.sha256
        ):
            raise ValueError("saved prediction bytes changed")
        documents.append(unique_json(raw.decode()))
    comparisons = compare_arrays(*arrays)
    left, right = documents
    if {k: v for k, v in left.items() if k != "prediction"} != {
        k: v for k, v in right.items() if k != "prediction"
    }:
        raise ValueError("saved prediction selection/model/partition changed")
    import numpy as np

    vector = compare_arrays(
        {"prediction": np.asarray(left["prediction"], dtype=np.float64)},
        {"prediction": np.asarray(right["prediction"], dtype=np.float64)},
    )
    if (
        comparisons != done["comparisons"]
        or done["all_outputs_within_tolerance"]
        != all(v["within_tolerance"] for v in comparisons.values())
        or done["prediction_document_exact"] != (left == right)
        or q["guest_outputs_sha256"] != guest["outputs"]["sha256"]
        or q["guest_predictions_sha256"] != guest["predictions"]["sha256"]
    ):
        raise ValueError("saved parity decision differs from recomputed values")
    return {
        "completion_digest": expected_digest,
        "comparisons": comparisons,
        "prediction_vector": vector["prediction"],
        "prediction_document_exact": left == right,
        "all_outputs_within_tolerance": done["all_outputs_within_tolerance"],
        "new_processes": 0,
        "runtime_qualified": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--expected-digest", required=True)
    a = p.parse_args()
    print(canonical_json(read_completion(a.root, expected_digest=a.expected_digest)))


if __name__ == "__main__":
    main()
