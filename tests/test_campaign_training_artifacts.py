"""Training artifact transport and parent commits use the original campaign writer."""

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil

import pytest

from autoengineering.adapters.contracts import TrainingArtifactBundle, TrainingResult
from autoengineering.campaign.artifacts import commit_worker_lifecycle, put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import canonical_json


def trained(tmp_path):
    from test_utility_hydrology_learned import fixture, fit

    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    site, profile, ctx, forcing, data, _ = fixture(source)
    result = fit(site, profile, ctx, forcing, data)
    return Path(ctx.scratch_path), profile, result


def parent(tmp_path):
    root = tmp_path / "parent"
    root.mkdir(mode=0o700)
    (root / "artifacts").mkdir(mode=0o700)
    return root


def metadata(training):
    return canonical_json(
        {"training": training.to_dict(), "elapsed_seconds": 1.0, "output_sha256": "1" * 64}
    ).encode()


def test_real_fit_bundle_is_portable_and_offline_reconstruction_needs_no_scratch(
    tmp_path, monkeypatch
):
    from autoengineering.utility.hydrology_training import (
        TrainingIntent,
        read_training_costs,
    )

    scratch, profile, result = trained(tmp_path)
    root = parent(tmp_path)
    refs = commit_worker_lifecycle(
        root, scratch, metadata(result.training), output_sha256="1" * 64, producer="attempt-000001"
    )
    assert len(refs) == 6
    document = json.loads(read_bytes(root, refs[0]))
    assert document["schema_version"] == "2.0"
    assert document["worker_training"] == result.training.to_dict()
    retained = TrainingResult.from_dict(document["training"])
    bundle_ref = ArtifactRef.from_json(retained.artifact.metadata["training_bundle"])
    bundle = TrainingArtifactBundle.from_json(read_bytes(root, bundle_ref).decode())
    assert bundle.primary in refs and all(r in refs for r in bundle.companions)
    intent_ref = next(r for r in bundle.companions if r.path.endswith("/training-intent.json"))
    result_ref = next(r for r in bundle.companions if r.path.endswith("/training-result.json"))
    intent = TrainingIntent.from_json(read_bytes(root, intent_ref).decode())
    original = Path.open

    def guard(path, *args, **kwargs):
        if path.is_relative_to(scratch):
            raise AssertionError("offline reconstruction read scratch")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guard)
    original_os_open = os.open

    def guard_os(path, *args, **kwargs):
        if Path(path).is_relative_to(scratch):
            raise AssertionError("offline reconstruction read scratch")
        return original_os_open(path, *args, **kwargs)

    monkeypatch.setattr(os, "open", guard_os)
    costs = read_training_costs(
        root,
        intent_ref,
        result_ref,
        identity=intent.identity,
        profile=profile,
        seed=17,
        cell_digest="4" * 64,
    )
    assert (
        next(r.quantity for r in costs if r.resource == "training_routing_starts")
        == result.training.cost
    )


def test_legacy_metadata_bytes_and_generic_trained_artifact(tmp_path):
    root = parent(tmp_path)
    scratch = tmp_path / "scratch"
    scratch.mkdir(mode=0o700)
    (scratch / "artifacts").mkdir(mode=0o700)
    raw = json.dumps(
        json.loads(metadata(TrainingResult("not_applicable", None, None))), indent=2
    ).encode()
    refs = commit_worker_lifecycle(root, scratch, raw, output_sha256="1" * 64, producer="attempt")
    assert len(refs) == 1 and read_bytes(root, refs[0]) == raw
    fit = put_bytes(
        scratch, b"authored fit", name="fit.txt", media_type="text/plain", producer="trainer"
    )
    refs = commit_worker_lifecycle(
        root,
        scratch,
        metadata(TrainingResult("trained", fit, 1.0)),
        output_sha256="1" * 64,
        producer="attempt",
    )
    assert len(refs) == 2 and read_bytes(root, refs[1]) == b"authored fit"


@pytest.mark.parametrize("change", ["corrupt", "symlink", "primary", "missing"])
def test_invalid_explicit_bundle_refuses(tmp_path, change):
    scratch, _, result = trained(tmp_path)
    root = parent(tmp_path)
    bundle_ref = ArtifactRef.from_json(result.training.artifact.metadata["training_bundle"])
    bundle = TrainingArtifactBundle.from_json(read_bytes(scratch, bundle_ref).decode())
    broken = tmp_path / "broken"
    shutil.copytree(scratch, broken)
    target = broken / bundle.companions[0].path
    if change == "corrupt":
        target.write_bytes(b"corrupt")
    elif change == "symlink":
        target.unlink()
        target.symlink_to(scratch / bundle.companions[0].path)
    elif change == "missing":
        target.unlink()
    else:
        altered = replace(bundle, primary=replace(bundle.primary, producer="other"))
        ref = put_bytes(
            broken,
            altered.to_json().encode(),
            name="training-bundle.json",
            media_type="application/json",
            producer="trainer",
        )
        result = replace(
            result,
            training=replace(
                result.training,
                artifact=replace(
                    result.training.artifact, metadata={"training_bundle": ref.to_json()}
                ),
            ),
        )
    with pytest.raises(ValueError):
        commit_worker_lifecycle(
            root, broken, metadata(result.training), output_sha256="1" * 64, producer="attempt"
        )


@pytest.mark.parametrize("recover", [False, True])
def test_parent_completion_and_recovery_commit_the_same_training_closure(
    tmp_path, monkeypatch, recover
):
    """Transport fixture: a real scalar worker carries an authored training envelope.

    The fit runs separately before the worker. This verifies parent transport and
    recovery, not admission of supervised learned-model execution.
    """
    import autoengineering.campaign.controller as module
    from test_agent_batch_science import fixture

    scratch, _, result = trained(tmp_path)
    batch, controller = fixture(tmp_path, science=1)
    supervise = module.supervise

    def envelope(*args, **kwargs):
        finished = supervise(*args, **kwargs)
        job_path = Path(args[0][-1])
        job = json.loads(job_path.read_bytes())
        shutil.copytree(scratch / "artifacts", Path(job["context"]["scratch_path"]) / "artifacts")
        path = Path(job["output_path"]).with_suffix(".metadata.json")
        document = json.loads(path.read_bytes())
        document["training"] = result.training.to_dict()
        path.write_text(canonical_json(document))
        return finished

    monkeypatch.setattr(module, "supervise", envelope)
    checkpoint = controller._checkpoint

    class AuthoredLoss(BaseException):
        pass

    def interrupted(target, state, reason, artifacts=()):
        if reason == "action_finished":
            raise AuthoredLoss()
        return checkpoint(target, state, reason, artifacts)

    if recover:
        monkeypatch.setattr(controller, "_checkpoint", interrupted)
        with pytest.raises(AuthoredLoss):
            controller.advance()
        monkeypatch.setattr(controller, "_checkpoint", checkpoint)

        def forbidden(*args, **kwargs):
            raise AssertionError("recovery launched science")

        monkeypatch.setattr(module, "supervise", forbidden)
        controller.reconcile_batch()
    else:
        controller.remaining = 1
        controller.advance()
    state = controller.state()
    assert len(state.budget.attempts) == 1
    evaluation = state.evaluations[0]
    projection = controller.store.replay()
    event = next(
        e
        for e in projection.events
        if any(ref.sha256 == evaluation.provenance["lifecycle_record"] for ref in e.artifacts)
    )
    lifecycle = next(
        r for r in event.artifacts if r.sha256 == evaluation.provenance["lifecycle_record"]
    )
    document = json.loads(read_bytes(controller.store.root, lifecycle))
    fitted = TrainingResult.from_dict(document["training"]).artifact
    bundle_ref = ArtifactRef.from_json(fitted.metadata["training_bundle"])
    bundle = TrainingArtifactBundle.from_json(
        read_bytes(controller.store.root, bundle_ref).decode()
    )
    assert bundle_ref in event.artifacts and bundle.primary in event.artifacts
    assert all(ref in event.artifacts for ref in bundle.companions)
    assert (
        hashlib.sha256(read_bytes(controller.store.root, bundle.primary)).hexdigest()
        == fitted.sha256
    )
    assert batch.report()["scientific_reservations_charged"] == 1
