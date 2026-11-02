"""Fixed supplied frozen-routing worker. No labels, fitting payload or score calculation."""

from __future__ import annotations

from dataclasses import replace
from importlib import import_module
import io
from pathlib import Path
import sys

import numpy as np

from autoengineering.adapters.contracts import AdapterRegistration, AdapterRegistry, PrepareContext
from autoengineering.adapters.python import run_lifecycle
from autoengineering.campaign.acceptance import CheckContext, DEFAULT_CHECKS
from autoengineering.campaign.artifacts import put_bytes, read_arrays, read_bytes
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.spec import CheckSpec
from autoengineering.campaign.store import checked_directory, durable_write
from .confirmation import read_selected_state
from .inference_execution import (
    FrozenInferenceJob,
    FrozenInferenceResult,
    verify_code,
    PHYSICAL_CHECKS,
    driver_limits,
)


def run(job_path):
    root = checked_directory(job_path.parent)
    job = FrozenInferenceJob.from_json(job_path.read_text())
    grant, replay = job.grant, job.grant.inference
    intent = unique_json((root / "intent.json").read_text())
    if intent != {
        "grant": grant.digest,
        "executor": job.executor_digest,
        "nonce": job.nonce,
        "job": job.digest,
    }:
        raise ValueError("inference job differs from durable intent")
    claim = unique_json((root / "claim.json").read_text())
    if claim != {
        "grant": grant.digest,
        "executor": job.executor_digest,
        "nonce": job.nonce,
        "job": job.digest,
        "scope": job.claim_scope(root),
    }:
        raise ValueError("inference worker differs from its original suite claim")
    job.validate_runtime(root)
    bound = read_selected_state(root, replay.selected_state)
    replay.validate_selection(root, replay.selected_state, bound)
    verify_code(root, job.sources, job.lock, job.source_digest, bound.model)
    if (job.staged_driver.sha256, job.staged_driver.size_bytes, job.staged_driver.media_type) != (
        replay.forcing.artifact.sha256,
        replay.forcing.artifact.size_bytes,
        replay.forcing.artifact.media_type,
    ):
        raise ValueError("staged inference drivers differ from grant")
    from autoengineering.campaign.runtime import RUNTIME_ROOT
    from examples.utility.hydrology_runtime import (
        RoutingRuntimeProfile,
        RegisteredRoutingAdapter,
        SOURCES,
    )

    profile = RoutingRuntimeProfile.from_json(read_bytes(root, replay.runtime_profile).decode())
    first = replay.forcing.ports[0].time
    outputs = tuple(
        replace(
            p,
            time=replace(
                p.time,
                dates=first.dates,
                warmup_mask=first.warmup_mask,
                scoring_mask=first.scoring_mask,
            ),
        )
        if p.time is not None
        else p
        for p in bound.model.outputs
    )
    model = replace(bound.model, inputs=replay.forcing.ports, outputs=outputs)
    scratch = root / "scratch"
    scratch.mkdir(mode=0o700)
    context = PrepareContext(model, bound.configuration, replay.seed, str(scratch), ())

    def factory():
        for path in SOURCES:
            import_module(path.removesuffix(".py").replace("/", ".").removesuffix(".__init__"))
        return RegisteredRoutingAdapter(profile, root, bound)

    adapters = AdapterRegistry(
        (AdapterRegistration("frozen-routing", "1", factory, SOURCES, source_root=RUNTIME_ROOT),)
    )
    adapters.validate("frozen-routing", model, root)
    adapter = adapters.create("frozen-routing")
    forcing = read_arrays(root, job.staged_driver, limits=driver_limits(replay))
    try:
        lifecycle = run_lifecycle(adapter, context, forcing, model.inputs, model.outputs)
    except Exception:
        return FrozenInferenceResult(
            "utility-frozen-inference-result-v1",
            grant.digest,
            job.executor_digest,
            job.nonce,
            "model_failure",
            None,
            None,
            (),
            None,
        )
    if (
        lifecycle.training.status != "not_applicable"
        or lifecycle.training.cost is not None
        or lifecycle.training.artifact is None
        or lifecycle.training.artifact.sha256 != bound.training.fit.sha256
        or (scratch / "training-intent.json").exists()
        or (scratch / "training-result.json").exists()
    ):
        raise ValueError("frozen inference attempted fitting or changed the fit")
    checks = tuple(
        DEFAULT_CHECKS.evaluate(
            CheckSpec(name, "1", True, "outputs", {}),
            CheckContext(lifecycle.outputs, forcing, context.parameters),
        )
        for name in PHYSICAL_CHECKS
    )
    buffer = io.BytesIO()
    np.savez(buffer, **lifecycle.outputs)
    raw = buffer.getvalue()
    if len(raw) > replay.output_limit_bytes:
        raise ValueError("inference output exceeds its declared limit")
    arrays = put_bytes(
        root, raw, name="outputs.npz", media_type="application/x-npz", producer="inference"
    )
    status = "success" if all(c.status == "pass" for c in checks) else "scientific_infeasible"
    predictions = None
    if status == "success":
        raw = canonical_json(
            {
                "model_sha256": grant.model_digest,
                "partition_digest": grant.partition_digest,
                "selection_digest": grant.selection_digest,
                "prediction": lifecycle.outputs["prediction"].tolist(),
            }
        ).encode()
        if len(raw) > 1048576:
            raise ValueError("frozen prediction vector exceeds fixed scorer limit")
        predictions = put_bytes(
            root, raw, name="predictions.json", media_type="application/json", producer="inference"
        )
    return FrozenInferenceResult(
        "utility-frozen-inference-result-v1",
        grant.digest,
        job.executor_digest,
        job.nonce,
        status,
        arrays,
        predictions,
        checks,
        lifecycle.elapsed_seconds,
    )


def main(job_path):
    try:
        result = run(job_path)
    except Exception:
        # No exception text, driver values or private paths enter the worker envelope.
        job = FrozenInferenceJob.from_json(job_path.read_text())
        result = FrozenInferenceResult(
            "utility-frozen-inference-result-v1",
            job.grant.digest,
            job.executor_digest,
            job.nonce,
            "infrastructure_failure",
            None,
            None,
            (),
            None,
        )
    durable_write(job_path.parent / "worker-result.json", result.to_json().encode())


if __name__ == "__main__":
    main(Path(sys.argv[1]))
