"""Authored OCI projections verify record consistency, never actual isolation."""

from dataclasses import replace
import io
import json
import shutil
import subprocess
import sys

import numpy as np
import pytest

from autoengineering.campaign.artifacts import put_bytes, read_bytes
from autoengineering.campaign.records import CheckResult
from autoengineering.utility.inference_execution import FrozenInferenceResult, PHYSICAL_CHECKS
from autoengineering.utility import guest_receipts as module
import test_utility_inference_guest as guest_fixture

metadata = guest_fixture.metadata
stage = guest_fixture.stage

H = "1" * 64


def prepared(
    tmp_path,
    metadata,
    *,
    worker_status="success",
    reason=None,
    exit_code=0,
    oom=False,
    dead=False,
    capture_state="complete",
    elapsed=2.0,
):
    root, job, _ = stage(tmp_path, metadata)

    def save(value, name):
        raw = value.to_json().encode() if hasattr(value, "to_json") else json.dumps(value).encode()
        return put_bytes(
            root, raw, name=name, media_type="application/json", producer="authored-OCI-projection"
        )

    jobref = save(job, "guest-job.json")
    intent = save(json.loads((root / "intent.json").read_text()), "guest-intent.json")
    claim = save(json.loads((root / "claim.json").read_text()), "guest-claim.json")
    (root / "inference-claims").mkdir(mode=0o700)
    (root / "inference-claims" / f"{job.grant.digest}.json").write_text(claim.to_json())
    launch = module.GuestLaunchIntent(
        "utility-guest-launch-intent-v1",
        job.digest,
        job.grant.digest,
        job.executor_digest,
        H,
        claim.sha256,
        job.nonce,
        job.guest.image_id,
        job.grant.inference.timeout_seconds,
        module.GuestContainerPolicy(),
    )
    start = module.GuestContainerStart(
        "utility-guest-container-start-v1",
        launch.digest,
        H,
        job.nonce,
        job.guest.image_id,
        launch.policy.digest,
        "2026-01-01T00:00:00Z",
        H,
        H,
        1,
    )
    stop = module.GuestContainerStop(
        "utility-guest-container-stop-v1",
        start.digest,
        H,
        job.nonce,
        start.started_at,
        "2026-01-01T00:00:02Z",
        False,
        0,
        exit_code,
        oom,
        dead,
        reason,
        elapsed,
        H,
    )
    cleanup = module.GuestContainerCleanup(
        "utility-guest-container-cleanup-v1", stop.digest, H, job.nonce, True, True, H
    )
    outputs = predictions = None
    checks = ()
    if worker_status in ("success", "scientific_infeasible"):
        stream = io.BytesIO()
        np.savez(stream, prediction=np.ones(140), soil=np.ones(140), reservoir=np.ones(140))
        outputs = put_bytes(
            root,
            stream.getvalue(),
            name="outputs.npz",
            media_type="application/x-npz",
            producer="author",
        )
        checks = tuple(
            CheckResult(
                n,
                "1",
                "fail" if worker_status == "scientific_infeasible" and i == 0 else "pass",
                True,
                "outputs",
                0,
                0,
                "authored checks",
                (),
            )
            for i, n in enumerate(PHYSICAL_CHECKS)
        )
        if worker_status == "success":
            predictions = save(
                {
                    "model_sha256": job.grant.model_digest,
                    "partition_digest": job.grant.partition_digest,
                    "selection_digest": job.grant.selection_digest,
                    "prediction": [1.0] * 140,
                },
                "predictions.json",
            )
    result = FrozenInferenceResult(
        "utility-frozen-inference-result-v1",
        job.grant.digest,
        job.executor_digest,
        job.nonce,
        worker_status,
        outputs,
        predictions,
        checks,
        1.0 if outputs is not None else None,
    )
    result_ref = save(result, "result.json") if capture_state == "complete" else None
    captured = module.GuestResultCapture(
        "utility-guest-result-capture-v1",
        job.digest,
        job.nonce,
        capture_state,
        result_ref,
        result_ref.sha256 if result_ref else None if capture_state == "missing" else H,
    )
    transport_failure = (
        reason is not None or exit_code != 0 or oom or dead or capture_state != "complete"
    )
    archive = module.GuestInferenceArchive(
        "utility-guest-inference-archive-v1",
        jobref,
        intent,
        claim,
        save(launch, "launch.json"),
        save(start, "start.json"),
        save(stop, "stop.json"),
        save(cleanup, "cleanup.json"),
        save(captured, "capture.json"),
        None if transport_failure else outputs,
        None if transport_failure else predictions,
    )
    ref = save(archive, "guest-archive.json")
    args = dict(
        source_digest=job.source_digest,
        lock_digest=job.lock.sha256,
        executor_digest=job.executor_digest,
        runtime_digest=H,
    )
    return root, job, archive, ref, args, save


def test_completed_guest_archive_relocates_and_preserves_unknown_cost(
    tmp_path, metadata, monkeypatch
):
    root, job, archive, ref, args, _ = prepared(tmp_path, metadata, elapsed=None)
    from autoengineering.utility import inference_guest

    monkeypatch.setattr(inference_guest, "observe_python", lambda: pytest.fail("runtime probe"))
    monkeypatch.setattr(np, "load", lambda *_a, **_k: pytest.fail("array interpretation"))
    result = module.verify_guest_archive(root, ref, job.grant, **args)
    assert result.status == "success" and result.container_starts == 1
    assert result.lifecycle_seconds is None and result.result.lifecycle_seconds == 1
    assert result.boundary == "unqualified-candidate"
    relocated = tmp_path / "public-copy"
    shutil.copytree(root, relocated)
    assert module.verify_guest_archive(relocated, ref, job.grant, **args) == result
    assert read_bytes(root, archive.outputs) == read_bytes(relocated, archive.outputs)


@pytest.mark.parametrize(
    "case,kwargs,expected",
    [
        ("model", {"worker_status": "model_failure"}, "model_failure"),
        ("science", {"worker_status": "scientific_infeasible"}, "scientific_infeasible"),
        ("infrastructure", {"worker_status": "infrastructure_failure"}, "infrastructure_failure"),
        ("timeout", {"reason": "timeout", "exit_code": 137}, "timeout"),
        ("cancel", {"reason": "cancelled", "exit_code": 137}, "infrastructure_failure"),
        ("oom", {"oom": True, "exit_code": 137}, "infrastructure_failure"),
        ("dead", {"dead": True}, "infrastructure_failure"),
        ("exit", {"exit_code": 1}, "infrastructure_failure"),
        ("missing", {"capture_state": "missing"}, "infrastructure_failure"),
        ("malformed", {"capture_state": "malformed"}, "infrastructure_failure"),
        ("limited", {"capture_state": "limited"}, "infrastructure_failure"),
    ],
)
def test_failed_guest_records_never_turn_into_a_scoring_vector(
    tmp_path, metadata, case, kwargs, expected
):
    root, job, archive, ref, args, _ = prepared(tmp_path, metadata, **kwargs)
    result = module.verify_guest_archive(root, ref, job.grant, **args)
    assert result.status == expected and archive.predictions is None
    if case not in ("model", "science", "infrastructure"):
        assert result.result is None and archive.outputs is None
    if case == "science":
        assert result.result.outputs is not None


@pytest.mark.parametrize(
    "problem",
    [
        "runtime",
        "executor",
        "source",
        "lock",
        "start",
        "stop",
        "cleanup",
        "capture",
        "claim",
        "prediction",
    ],
)
def test_guest_archive_foreign_binding_refuses(tmp_path, metadata, problem):
    root, job, archive, ref, args, save = prepared(tmp_path, metadata)
    if problem in ("runtime", "executor", "source", "lock"):
        args[problem + "_digest"] = "2" * 64
    elif problem == "claim":
        path = root / "inference-claims" / f"{job.grant.digest}.json"
        path.write_text(archive.job.to_json())
    elif problem == "prediction":
        bad = save(
            {
                "model_sha256": "2" * 64,
                "partition_digest": job.grant.partition_digest,
                "selection_digest": job.grant.selection_digest,
                "prediction": [1.0] * 140,
            },
            "foreign-vector.json",
        )
        archive = replace(archive, predictions=bad)
        ref = save(archive, "foreign-archive.json")
    else:
        kinds = {
            "start": module.GuestContainerStart,
            "stop": module.GuestContainerStop,
            "cleanup": module.GuestContainerCleanup,
            "capture": module.GuestResultCapture,
        }
        record = kinds[problem].from_json(read_bytes(root, getattr(archive, problem)).decode())
        bad = save(replace(record, nonce="b" * 32), "foreign-" + problem + ".json")
        archive = replace(archive, **{problem: bad})
        ref = save(archive, "foreign-archive.json")
    with pytest.raises(ValueError):
        module.verify_guest_archive(root, ref, job.grant, **args)


@pytest.mark.parametrize(
    "problem", ["network", "mount", "privileged", "command", "environment", "boolean_cpu"]
)
def test_unbounded_or_changed_guest_policy_is_not_a_valid_projection(problem):
    policy = module.GuestContainerPolicy()
    with pytest.raises(ValueError):
        if problem == "network":
            replace(policy, network="host")
        elif problem == "mount":
            replace(policy, host_mounts=("/private-labels",))
        elif problem == "privileged":
            replace(policy, privileged=True)
        elif problem == "command":
            replace(policy, command=("/bin/sh",))
        elif problem == "environment":
            replace(policy, environment=(("TOKEN", "secret-canary"),))
        else:
            replace(policy, nano_cpus=True)


@pytest.mark.parametrize(
    "problem", ["pid", "running", "chronology", "zero_time", "cleanup", "worker_timeout"]
)
def test_unverified_terminal_evidence_cannot_complete_guest_archive(tmp_path, metadata, problem):
    root, job, archive, ref, args, save = prepared(
        tmp_path, metadata, worker_status="timeout" if problem == "worker_timeout" else "success"
    )
    with pytest.raises(ValueError):
        if problem == "worker_timeout":
            module.verify_guest_archive(root, ref, job.grant, **args)
        elif problem == "cleanup":
            value = module.GuestContainerCleanup.from_json(
                read_bytes(root, archive.cleanup).decode()
            )
            replace(value, removed=False)
        else:
            value = module.GuestContainerStop.from_json(read_bytes(root, archive.stop).decode())
            if problem == "pid":
                replace(value, pid=1)
            elif problem == "running":
                replace(value, running=True)
            elif problem == "zero_time":
                replace(value, started_at="0001-01-01T00:00:00Z")
            else:
                replace(value, finished_at="2025-01-01T00:00:00Z")


def test_guest_archive_cold_reader_uses_only_public_bytes(tmp_path, metadata):
    root, job, _, ref, args, _ = prepared(tmp_path, metadata)
    script = """
import importlib.abc,sys,json
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:
   raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.utility.guest_receipts import verify_guest_archive
from autoengineering.utility.scoring import ConfirmationGrant
from autoengineering.campaign.records import ArtifactRef
from autoengineering.utility import inference_guest
import numpy,subprocess,socket,os
def forbidden(*args,**kwargs):raise AssertionError('execution/runtime/array access')
numpy.load=subprocess.Popen=socket.socket=inference_guest.observe_python=forbidden
root=Path(sys.argv[1]);allowed={p for p in root.rglob('*') if p.is_file()}
old=Path.open;old_os=os.open
def guarded(path,mode='r',*args,**kwargs):
 if path not in allowed or any(c in mode for c in 'wax+'):raise AssertionError('ungranted access')
 return old(path,mode,*args,**kwargs)
def guarded_os(path,flags,*args,**kwargs):
 if Path(path) not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT):
  raise AssertionError('ungranted access')
 return old_os(path,flags,*args,**kwargs)
Path.open=guarded;os.open=guarded_os
result=verify_guest_archive(root,ArtifactRef.from_json(sys.argv[2]),
 ConfirmationGrant.from_json(sys.argv[3]),**json.loads(sys.argv[4]))
assert result.status=='success' and result.boundary=='unqualified-candidate'
print(result.job_digest)
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            script,
            str(root),
            ref.to_json(),
            job.grant.to_json(),
            json.dumps(args),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stdout.strip() == job.digest


@pytest.mark.parametrize(
    "member",
    ["job", "intent", "launch", "start", "stop", "cleanup", "capture", "outputs", "predictions"],
)
def test_guest_archive_byte_corruption_is_not_reconciled_by_execution(tmp_path, metadata, member):
    root, job, archive, ref, args, _ = prepared(tmp_path, metadata)
    path = root / getattr(archive, member).path
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        module.verify_guest_archive(root, ref, job.grant, **args)


def test_failure_cannot_publish_partial_success_predictions(tmp_path, metadata):
    root, job, archive, ref, args, save = prepared(tmp_path, metadata, reason="timeout")
    capture = module.GuestResultCapture.from_json(read_bytes(root, archive.capture).decode())
    result = FrozenInferenceResult.from_json(read_bytes(root, capture.worker_result).decode())
    archive = replace(archive, predictions=result.predictions)
    ref = save(archive, "invalid-partial-success.json")
    with pytest.raises(ValueError, match="failure cannot supply"):
        module.verify_guest_archive(root, ref, job.grant, **args)


@pytest.mark.parametrize("problem", ["worker_identity", "boolean_vector", "dimension", "binding"])
def test_conflicting_worker_results_or_vectors_refuse(tmp_path, metadata, problem):
    root, job, archive, ref, args, save = prepared(tmp_path, metadata)
    capture = module.GuestResultCapture.from_json(read_bytes(root, archive.capture).decode())
    result = FrozenInferenceResult.from_json(read_bytes(root, capture.worker_result).decode())
    if problem == "worker_identity":
        result = replace(result, executor_digest="2" * 64)
    else:
        vector = json.loads(read_bytes(root, result.predictions))
        if problem == "boolean_vector":
            vector["prediction"][0] = True
        elif problem == "dimension":
            vector["prediction"] = vector["prediction"][:-1]
        else:
            vector["selection_digest"] = "2" * 64
        prediction = save(vector, "changed-vector.json")
        result = replace(result, predictions=prediction)
        archive = replace(archive, predictions=prediction)
    result_ref = save(result, "changed-result.json")
    capture = replace(capture, worker_result=result_ref, original_capture_digest=result_ref.sha256)
    archive = replace(archive, capture=save(capture, "changed-capture.json"))
    ref = save(archive, "changed-result-archive.json")
    with pytest.raises(ValueError):
        module.verify_guest_archive(root, ref, job.grant, **args)


@pytest.mark.parametrize("problem", ["missing", "bytes", "metadata"])
def test_archived_environment_is_required_and_bound(tmp_path, metadata, problem):
    root, job, archive, ref, args, save = prepared(tmp_path, metadata)
    path = root / job.environment.path
    if problem == "missing":
        path.unlink()
    elif problem == "bytes":
        path.write_bytes(path.read_bytes() + b" ")
    else:
        value = json.loads(path.read_text())
        value["runtime_qualified"] = True
        altered = save(value, "foreign-environment.json")
        job = replace(job, environment=altered)
        archive = replace(archive, job=save(job, "foreign-job.json"))
        ref = save(archive, "foreign-environment-archive.json")
    with pytest.raises(ValueError):
        module.verify_guest_archive(root, ref, job.grant, **args)
