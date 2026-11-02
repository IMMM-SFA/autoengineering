"""Archive and verify original inference evidence without drivers or model imports.

These records preserve trusted producer claims. An offline reader cannot attest
OS isolation or independently observe that an original process has stopped.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

from autoengineering.campaign.artifacts import confined_file, put_bytes, read_bytes, reference
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.store import StoreError
from .inference_execution import FrozenInferenceJob, FrozenInferenceReceipt, FrozenInferenceResult


@dataclass(frozen=True)
class FrozenInferenceArchive(Record):
    schema: Literal["utility-frozen-inference-archive-v1"]
    job: ArtifactRef
    intent: ArtifactRef
    receipt: ArtifactRef
    supervisor: ArtifactRef
    process: ArtifactRef
    claim: ArtifactRef
    result: ArtifactRef | None
    outputs: ArtifactRef | None
    predictions: ArtifactRef | None


def _json(root, ref, kind=None):
    raw = read_bytes(root, ref, max_bytes=4 * 1024 * 1024).decode()
    return kind.from_json(raw) if kind is not None else unique_json(raw)


def _same_bytes(old, new):
    return (
        old is not None
        and new is not None
        and (old.sha256, old.size_bytes, old.media_type)
        == (new.sha256, new.size_bytes, new.media_type)
    )


def archive_inference(executor, grant):
    """Require live recovery's original stop proof, then copy only public closure."""
    receipt = executor.recover(grant)
    origin = executor.work_root / grant.digest
    public = executor.store.root

    def copy(ref, name=None):
        return put_bytes(
            public,
            read_bytes(origin, ref),
            name=name or ref.path.rsplit("/", 1)[-1],
            media_type=ref.media_type,
            producer="trusted-inference-archive",
        )

    def capture(path, name):
        return copy(reference(origin, path, media_type="application/json", producer="reader"), name)

    result = _json(origin, receipt.result, FrozenInferenceResult) if receipt.result else None
    archive = FrozenInferenceArchive(
        "utility-frozen-inference-archive-v1",
        capture("job.json", "inference-job.json"),
        capture("intent.json", "inference-intent.json"),
        capture("execution.json", "inference-execution.json"),
        copy(receipt.supervisor, "inference-supervisor.json"),
        capture("attempts/inference/process.json", "inference-process.json"),
        receipt.claim,
        copy(receipt.result, "inference-result.json") if receipt.result else None,
        copy(result.outputs) if result and result.outputs else None,
        copy(result.predictions) if result and result.predictions else None,
    )
    ref = put_bytes(
        public,
        archive.to_json().encode(),
        name="inference-archive.json",
        media_type="application/json",
        producer="trusted-inference-archive",
    )
    verify_inference_archive(
        public,
        ref,
        grant,
        executor.identity,
        executor.store.spec.source_digest,
        executor.store.spec.lock_digest,
    )
    return ref


def verify_inference_archive(root, ref, grant, executor_digest, source_digest, lock_digest):
    """Hash-check a public closure without any original workspace or execution."""
    archive = _json(root, ref, FrozenInferenceArchive)
    job = _json(root, archive.job, FrozenInferenceJob)
    if type(job) is not FrozenInferenceJob:
        raise StoreError("guest jobs require a separately verified guest execution receipt")
    receipt = _json(root, archive.receipt, FrozenInferenceReceipt)
    if (job.grant, job.executor_digest, job.source_digest) != (
        grant,
        executor_digest,
        source_digest,
    ) or digest([r.to_dict() for r in job.sources]) != source_digest:
        raise StoreError("archived inference job differs from frozen source/grant")
    if job.lock.sha256 != lock_digest:
        raise StoreError("archived inference lock differs")
    expected = {
        "grant": grant.digest,
        "executor": executor_digest,
        "nonce": job.nonce,
        "job": job.digest,
    }
    if _json(root, archive.intent) != expected:
        raise StoreError("archived inference intent differs")
    claim = _json(root, archive.claim)
    original_claim = ArtifactRef.from_json(
        confined_file(root, f"inference-claims/{grant.digest}.json").read_text()
    )
    if original_claim != archive.claim:
        raise StoreError("archive differs from the original suite inference claim")
    if not isinstance(claim, dict) or set(claim) != set(expected) | {"scope"}:
        raise StoreError("archived inference claim has invalid fields")
    from .contracts import sha256

    sha256(claim["scope"])
    if {k: claim[k] for k in expected} != expected:
        raise StoreError("archived inference claim differs")
    if (
        (receipt.grant_digest, receipt.executor_digest, receipt.nonce, receipt.stop_verified)
        != (grant.digest, executor_digest, job.nonce, True)
        or receipt.claim != archive.claim
        or not _same_bytes(receipt.supervisor, archive.supervisor)
    ):
        raise StoreError("archived inference receipt differs")
    proof, process = _json(root, archive.supervisor), _json(root, archive.process)
    if (
        not isinstance(proof, dict)
        or not isinstance(process, dict)
        or proof.get("identity") != process
        or process.get("nonce") != job.nonce
        or type(process.get("pid")) is not int
        or process["pid"] <= 0
        or type(process.get("pgid")) is not int
        or process["pgid"] != process["pid"]
        or proof.get("stopped") is not True
        or type(proof.get("returncode")) is not int
        or type(proof.get("receipt_valid")) is not bool
        or type(proof.get("elapsed_seconds")) not in (int, float)
        or not math.isfinite(proof["elapsed_seconds"])
        or proof["elapsed_seconds"] < 0
        or proof.get("status")
        not in ("success", "model_failure", "timeout", "infrastructure_failure")
        or proof.get("stop_reason") not in (None, "timeout", "cancelled")
        or (proof["status"] == "timeout") != (proof.get("stop_reason") == "timeout")
        or (proof.get("stop_reason") == "cancelled" and proof["status"] != "infrastructure_failure")
    ):
        raise StoreError("archived inference stop evidence is inconsistent")
    result = None
    if proof["status"] == "success":
        if (
            proof["returncode"] != 0
            or not proof["receipt_valid"]
            or proof.get("stop_reason") is not None
        ):
            raise StoreError("archived inference success has invalid process proof")
        if not _same_bytes(receipt.result, archive.result):
            raise StoreError("archived inference result reference differs")
        result = _json(root, archive.result, FrozenInferenceResult)
        if (result.grant_digest, result.executor_digest, result.nonce, result.status) != (
            grant.digest,
            executor_digest,
            job.nonce,
            receipt.status,
        ):
            raise StoreError("archived inference result differs")
        for original, saved, limit in (
            (result.outputs, archive.outputs, grant.inference.output_limit_bytes),
            (result.predictions, archive.predictions, 1048576),
        ):
            if original is None:
                if saved is not None:
                    raise StoreError("archive invents inference outputs")
            elif not _same_bytes(original, saved):
                raise StoreError("archived inference output reference differs")
            else:
                read_bytes(root, saved, max_bytes=limit)
    elif receipt.status != (
        "timeout" if proof["status"] == "timeout" else "infrastructure_failure"
    ) or any(
        r is not None
        for r in (receipt.result, archive.result, archive.outputs, archive.predictions)
    ):
        raise StoreError("archived failed inference invents a completed result")
    if receipt.status == "success":
        prediction = _json(root, archive.predictions)
        if (
            not isinstance(prediction, dict)
            or set(prediction)
            != {"model_sha256", "partition_digest", "selection_digest", "prediction"}
            or (
                prediction["model_sha256"],
                prediction["partition_digest"],
                prediction["selection_digest"],
            )
            != (grant.model_digest, grant.partition_digest, grant.selection_digest)
        ):
            raise StoreError("archived predictions differ from frozen selection")
        values = prediction["prediction"]
        if (
            not isinstance(values, list)
            or len(values) != len(grant.inference.forcing.ports[0].time.dates)
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
        ):
            raise StoreError("archived prediction vector is invalid")
    return archive, receipt, result, proof
