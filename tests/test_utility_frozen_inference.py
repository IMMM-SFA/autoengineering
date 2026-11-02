"""Actual fixed frozen inference; no private scorer or boundary qualification."""

from dataclasses import replace
from datetime import date
import io
import json

import numpy as np
import pytest

from autoengineering.campaign.artifacts import put_bytes, read_arrays, read_bytes, reference
from autoengineering.campaign.store import StoreError
from autoengineering.utility.inference_execution import (
    FrozenRoutingExecutor,
    FrozenInferenceResult,
    FrozenInferenceJob,
)
from autoengineering.utility.confirmation import read_selected_state
from test_utility_composite_grants import prepared


def setup(tmp_path, monkeypatch, *, change=None, authorize=True):
    store, grant, _, plan, source = prepared(tmp_path, monkeypatch, details=True)
    drivers = tmp_path / "driver-scope"
    drivers.mkdir(mode=0o700)
    (drivers / "reserved").mkdir(mode=0o700)
    (drivers / "private-labels.json").write_text("AUTHORED-PRIVATE-CANARY")
    original = read_arrays(
        source, reference(source, "forcing.npz", media_type="application/x-npz", producer="author")
    )
    values = {name: np.r_[value, np.full(20, value[-1])] for name, value in original.items()}
    dates = grant.inference.forcing.ports[0].time.dates
    values["day_of_year"] = np.asarray([date.fromisoformat(d).timetuple().tm_yday for d in dates])
    if change == "prefix":
        values["precip_mm"][0] += 1.0
    stream = io.BytesIO()
    np.savez(stream, **values)
    (drivers / "reserved/drivers.npz").write_bytes(stream.getvalue())
    ref = reference(
        drivers, "reserved/drivers.npz", media_type="application/x-npz", producer="author"
    )
    replay = replace(grant.inference, forcing=replace(grant.inference.forcing, artifact=ref))
    if change == "output":
        replay = replace(replay, output_limit_bytes=1)
    if change == "timeout":
        replay = replace(replay, timeout_seconds=0.1)
    grant = replace(grant, inference=replay)
    work = tmp_path / "inference-work"
    work.mkdir(mode=0o700)
    executor = FrozenRoutingExecutor(
        store, source, drivers, work, sources=plan.source_inventory, lock=plan.lock
    )
    if authorize:
        attempt = "confirmation-" + grant.cell_digest[:48]
        arguments = dict(
            cell_digest=grant.cell_digest,
            attempt_id=attempt,
            child_digest=grant.digest,
            phase="confirmation",
        )
        with store.writer():
            store.append(
                request_id="authored-reserve",
                operation="reserve",
                resources=grant.resources,
                **arguments,
            )
            store.append(request_id="authored-start", operation="start", **arguments)
            ref = put_bytes(
                store.root,
                grant.to_json().encode(),
                name="confirmation-grant.json",
                media_type="application/json",
                producer="author",
            )
            store.append(
                request_id="authored-access",
                operation="confirmation_access",
                result_digest=ref.sha256,
                **arguments,
            )
    return store, grant, executor, values


def test_inference_scopes_cannot_overlap(tmp_path, monkeypatch):
    store, _, executor, _ = setup(tmp_path, monkeypatch, authorize=False)
    for public in (store.root, executor.source_root):
        nested = public / "nested-inference"
        nested.mkdir(mode=0o700)
        with pytest.raises(StoreError, match="work must be separate"):
            FrozenRoutingExecutor(
                store,
                executor.source_root,
                executor.driver_root,
                nested,
                sources=executor.sources,
                lock=executor.lock,
            )
        for drivers in (public, nested):
            with pytest.raises(StoreError, match="drivers must be separate"):
                FrozenRoutingExecutor(
                    store,
                    executor.source_root,
                    drivers,
                    executor.work_root,
                    sources=executor.sources,
                    lock=executor.lock,
                )
    assert not list(executor.work_root.iterdir())
    assert not (store.root / "inference-claims").exists()


def test_actual_frozen_inference_preserves_outputs_physics_and_original_recovery(
    tmp_path, monkeypatch
):
    store, grant, executor, values = setup(tmp_path, monkeypatch)
    receipt = executor.execute(grant)
    assert receipt.status == "success" and receipt.stop_verified
    root = executor.work_root / grant.digest
    result = FrozenInferenceResult.from_json(read_bytes(root, receipt.result).decode())
    assert all(c.status == "pass" for c in result.checks)
    predicted = json.loads(read_bytes(root, result.predictions))
    assert predicted["selection_digest"] == grant.selection_digest
    assert predicted["model_sha256"] == grant.model_digest
    assert predicted["partition_digest"] == grant.partition_digest
    assert len(predicted["prediction"]) == len(values["precip_mm"])
    bound = read_selected_state(store.root, grant.inference.selected_state)
    prior = bound.evaluation.outputs[0]
    original_root = next(
        p for p in store.root.glob("children/*/cases/*/campaign") if (p / prior.path).is_file()
    )
    previous = read_arrays(original_root, prior)
    current = read_arrays(root, result.outputs)
    for name, array in previous.items():
        np.testing.assert_array_equal(
            current[name] if array.ndim == 0 else current[name][: len(array)], array
        )
    assert not (root / "scratch/training-intent.json").exists()
    assert not (root / "scratch/training-result.json").exists()
    assert not any("private-labels" in str(p) for p in root.rglob("*"))
    assert str(executor.driver_root) not in (root / "job.json").read_text()
    monkeypatch.setattr(
        "autoengineering.utility.inference_execution.supervise",
        lambda *_a, **_k: pytest.fail("recovery executed"),
    )
    (executor.driver_root / "reserved/drivers.npz").unlink()
    job = FrozenInferenceJob.from_json((root / "job.json").read_text())
    (root / job.staged_driver.path).unlink()
    assert executor.recover(grant) == receipt
    with pytest.raises(StoreError, match="exists"):
        executor.execute(grant)
    assert not store.replay()["confirmation_scores"]
    alternate = tmp_path / "alternate-work"
    alternate.mkdir(mode=0o700)
    other = FrozenRoutingExecutor(
        store,
        executor.source_root,
        executor.driver_root,
        alternate,
        sources=executor.sources,
        lock=executor.lock,
    )
    with pytest.raises(StoreError, match="claimed"):
        other.execute(grant)
    assert not list(alternate.iterdir())
    with store.writer():
        store.append(
            request_id="authored-suite-stop",
            operation="cancel",
            cell_digest=grant.cell_digest,
            attempt_id="confirmation-" + grant.cell_digest[:48],
            child_digest=grant.digest,
            phase="confirmation",
        )
    assert executor.recover(grant) == receipt
    with pytest.raises(StoreError, match="cancelled"):
        other.execute(grant)


@pytest.mark.parametrize(
    "change,status",
    [("prefix", "model_failure"), ("output", "infrastructure_failure"), ("timeout", "timeout")],
)
def test_inference_failures_stay_distinct_and_never_supply_a_score_vector(
    tmp_path, monkeypatch, change, status
):
    store, grant, executor, _ = setup(tmp_path, monkeypatch, change=change)
    receipt = executor.execute(grant)
    assert receipt.status == status and receipt.stop_verified
    if receipt.result is not None:
        result = FrozenInferenceResult.from_json(
            read_bytes(executor.work_root / grant.digest, receipt.result).decode()
        )
        assert result.predictions is None
    assert (
        store.replay()["phase_used"][("fixed_evaluations", "confirmation", "scientific_starts")]
        == 2
    )


def test_no_reservation_refuses_before_driver_access_or_launch(tmp_path, monkeypatch):
    _, grant, executor, _ = setup(tmp_path, monkeypatch, authorize=False)
    (executor.driver_root / "reserved/drivers.npz").unlink()
    monkeypatch.setattr(
        "autoengineering.utility.inference_execution.supervise",
        lambda *_a, **_k: pytest.fail("unreserved launch"),
    )
    with pytest.raises(StoreError, match="reservation"):
        executor.execute(grant)
    assert not list(executor.work_root.iterdir())


def test_loss_after_saved_supervisor_completion_recovers_without_driver_or_relaunch(
    tmp_path, monkeypatch
):
    import autoengineering.utility.inference_execution as module

    _, grant, executor, _ = setup(tmp_path, monkeypatch)
    original = module.supervise

    class AuthoredLoss(BaseException):
        pass

    def lose(*args, **kwargs):
        original(*args, **kwargs)
        raise AuthoredLoss()

    monkeypatch.setattr(module, "supervise", lose)
    with pytest.raises(AuthoredLoss):
        executor.execute(grant)
    monkeypatch.setattr(module, "supervise", lambda *_a, **_k: pytest.fail("recovery relaunched"))
    (executor.driver_root / "reserved/drivers.npz").unlink()
    root = executor.work_root / grant.digest
    job = FrozenInferenceJob.from_json((root / "job.json").read_text())
    (root / job.staged_driver.path).unlink()
    assert executor.recover(grant).status == "success"


def test_original_job_stop_and_result_corruption_refuse_without_reexecution(tmp_path, monkeypatch):
    _, grant, executor, _ = setup(tmp_path, monkeypatch)
    executor.execute(grant)
    root = executor.work_root / grant.digest
    monkeypatch.setattr(
        "autoengineering.utility.inference_execution.supervise",
        lambda *_a, **_k: pytest.fail("corruption triggered a new inference"),
    )
    job_path = root / "job.json"
    original_job = job_path.read_bytes()
    document = json.loads(original_job)
    document["nonce"] = "1" * 32
    job_path.write_text(json.dumps(document))
    with pytest.raises(StoreError, match="intent|claim"):
        executor.recover(grant)
    job_path.write_bytes(original_job)
    supervisor = root / "attempts/inference/supervisor-result.json"
    original_supervisor = supervisor.read_bytes()
    document = json.loads(original_supervisor)
    document["stopped"] = False
    supervisor.write_text(json.dumps(document))
    with pytest.raises(StoreError, match="stop"):
        executor.recover(grant)
    supervisor.write_bytes(original_supervisor)
    result = root / "worker-result.json"
    original_result = result.read_bytes()
    result.write_bytes(b"authored result corruption")
    with pytest.raises(ValueError):
        executor.recover(grant)
    result.write_bytes(original_result)
    assert executor.recover(grant).status == "success"
