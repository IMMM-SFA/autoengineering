"""Authored Linux observations exercise transport bindings, never guest qualification."""

from dataclasses import replace
import json
import shutil
import subprocess
import sys

import pytest

from autoengineering.campaign.artifacts import put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.store import StoreError
from autoengineering.utility import inference_guest as guest
from autoengineering.utility import inference_worker as worker
from autoengineering.utility.inference_execution import (
    FrozenGuestInferenceJob,
    FrozenInferenceJob,
    executor_identity,
)
from autoengineering.utility.inference_evidence import (
    FrozenInferenceArchive,
    verify_inference_archive,
)
from examples.utility.inference_environment import (
    InferenceEnvironmentInputs,
    ROOTS,
    locked_archives,
)
from test_utility_composite_grants import prepared

H = "1" * 64


@pytest.fixture(scope="module")
def metadata(tmp_path_factory):
    root = tmp_path_factory.mktemp("authored-guest-metadata")
    with pytest.MonkeyPatch.context() as patch:
        store, grant, _, plan, source = prepared(root, patch, details=True)
    code = root / "wheel-layout"
    code.mkdir(mode=0o700)
    refs = []
    for ref in plan.source_inventory:
        name = ref.path.removeprefix("src/")
        if not name.endswith(".py") or not name.startswith(("autoengineering/", "examples/")):
            continue
        raw = read_bytes(source, ref)
        path = code / name
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(raw)
        refs.append(ArtifactRef(name, ref.sha256, ref.size_bytes, "text/x-python", "author", {}))
    archives, virtual, assumptions = locked_archives(read_bytes(source, plan.lock))
    environment = InferenceEnvironmentInputs(
        "utility-inference-environment-inputs-v1",
        "linux-64",
        "default",
        plan.lock,
        ArtifactRef("authored-wheel.whl", H, 100, "application/zip", "author", {}),
        "0.2.0",
        tuple(sorted(refs, key=lambda r: r.path)),
        ROOTS,
        archives,
        virtual,
        assumptions,
        H,
    )
    python = guest.GuestPythonIdentity(
        "utility-guest-python-identity-v1",
        "Linux",
        "x86_64",
        "CPython",
        next(p.version for p in archives if p.name == "python"),
        H,
    )
    profile = guest.FrozenGuestProfile(
        "utility-frozen-guest-profile-v1",
        environment.digest,
        plan.lock.sha256,
        environment.wheel.sha256,
        digest([r.to_dict() for r in environment.wheel_python_sources]),
        "sha256:" + H,
        python,
        digest(dict(guest.LIMITS)),
        "unqualified-candidate",
    )
    return store, grant, plan, environment, profile, code


def stage(tmp_path, metadata):
    _, grant, plan, environment, profile, code = metadata
    root = tmp_path / "host-scope"
    root.mkdir(mode=0o700)
    (root / "artifacts").mkdir(mode=0o700)
    ref = put_bytes(
        root,
        environment.to_json().encode(),
        name="environment.json",
        media_type="application/json",
        producer="authored-guest-contract",
    )
    job = FrozenGuestInferenceJob(
        "utility-frozen-inference-job-v2",
        grant,
        guest.guest_executor_identity(
            digest([r.to_dict() for r in plan.source_inventory]),
            plan.lock.sha256,
            profile,
        ),
        digest([r.to_dict() for r in plan.source_inventory]),
        plan.source_inventory,
        plan.lock,
        "a" * 32,
        grant.inference.forcing.artifact,
        profile,
        ref,
    )
    (root / "job.json").write_text(job.to_json())
    binding = {
        "grant": grant.digest,
        "executor": job.executor_digest,
        "nonce": job.nonce,
        "job": job.digest,
    }
    (root / "intent.json").write_text(json.dumps(binding))
    (root / "claim.json").write_text(json.dumps(binding | {"scope": job.claim_scope(root)}))
    return root, job, code


def test_guest_job_roundtrip_and_legacy_serialized_fields_stay_exact(tmp_path, metadata):
    root, job, _ = stage(tmp_path, metadata)
    assert FrozenInferenceJob.from_json(job.to_json()) == job
    assert isinstance(FrozenInferenceJob.from_json(job.to_json()), FrozenGuestInferenceJob)
    legacy = FrozenInferenceJob(
        "utility-frozen-inference-job-v1",
        job.grant,
        executor_identity(job.source_digest, job.lock),
        job.source_digest,
        job.sources,
        job.lock,
        job.nonce,
        job.staged_driver,
    )
    assert set(legacy.to_dict()) == {
        "schema",
        "grant",
        "executor_digest",
        "source_digest",
        "sources",
        "lock",
        "nonce",
        "staged_driver",
    }
    assert FrozenInferenceJob.from_json(legacy.to_json()) == legacy
    assert legacy.claim_scope(root) != legacy.claim_scope(root.parent / "guest-scope")
    assert job.claim_scope(root) == job.claim_scope(root.parent / "guest-scope")
    legacy.validate_runtime(root)


def test_fixed_worker_accepts_relocated_guest_binding_before_any_driver_read(
    tmp_path, metadata, monkeypatch
):
    root, job, code = stage(tmp_path, metadata)
    relocated = tmp_path / "guest-scope"
    shutil.copytree(root, relocated)
    monkeypatch.setattr(
        guest, "observe_python", lambda: job.guest.python
    )  # authored observation only
    monkeypatch.setattr(guest, "package_root", lambda: code)
    called = []

    class ReachedModelMetadata(Exception):
        pass

    def selected(*args):
        called.append(1)
        raise ReachedModelMetadata()

    monkeypatch.setattr(worker, "read_selected_state", selected)
    monkeypatch.setattr(worker, "read_arrays", lambda *_a, **_k: pytest.fail("driver read"))
    for scope in (root, relocated):
        with pytest.raises(ReachedModelMetadata):
            worker.run(scope / "job.json")
    assert called == [1, 1]
    assert str(root) not in job.to_json() and str(relocated) not in job.to_json()


@pytest.mark.parametrize(
    "problem",
    ["interpreter", "environment", "code", "code_missing", "code_extra", "claim", "intent"],
)
def test_guest_mismatch_refuses_before_selected_model_or_driver_reads(
    tmp_path, metadata, monkeypatch, problem
):
    root, job, code = stage(tmp_path, metadata)
    monkeypatch.setattr(guest, "observe_python", lambda: job.guest.python)
    monkeypatch.setattr(guest, "package_root", lambda: code)
    monkeypatch.setattr(
        worker, "read_selected_state", lambda *_a, **_k: pytest.fail("selected state read")
    )
    monkeypatch.setattr(worker, "read_arrays", lambda *_a, **_k: pytest.fail("driver read"))
    if problem == "interpreter":
        monkeypatch.setattr(
            guest, "observe_python", lambda: replace(job.guest.python, build_digest="2" * 64)
        )
    elif problem == "environment":
        path = root / job.environment.path
        path.write_bytes(path.read_bytes() + b"altered")
    elif problem in ("code", "code_missing", "code_extra"):
        altered = tmp_path / "altered-code"
        shutil.copytree(code, altered)
        path = altered / "autoengineering/utility/inference_guest.py"
        if problem == "code_missing":
            path.unlink()
        elif problem == "code_extra":
            (altered / "autoengineering/extra.py").write_bytes(b"# unexpected code")
        else:
            path.write_bytes(path.read_bytes() + b" ")
        monkeypatch.setattr(guest, "package_root", lambda: altered)
    else:
        path = root / (problem + ".json")
        value = json.loads(path.read_text())
        value["nonce"] = "b" * 32
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        worker.run(root / "job.json")


@pytest.mark.parametrize(
    "problem",
    ["image", "limits", "lock", "source", "runtime_binding", "environment_media", "promotion"],
)
def test_changed_guest_registration_or_identity_cannot_reuse_job(tmp_path, metadata, problem):
    _, job, _ = stage(tmp_path, metadata)
    with pytest.raises(ValueError):
        if problem == "image":
            replace(job, guest=replace(job.guest, image_id="sha256:" + "2" * 64))
        elif problem == "limits":
            replace(job.guest, limits_digest="2" * 64)
        elif problem == "lock":
            replace(job, lock=replace(job.lock, sha256="2" * 64))
        elif problem == "source":
            replace(job, source_digest="2" * 64)
        elif problem == "runtime_binding":
            replace(job, executor_digest="2" * 64)
        elif problem == "environment_media":
            replace(job, environment=replace(job.environment, media_type="application/x-npz"))
        else:
            replace(job.guest, boundary="qualified")


def test_guest_cannot_reuse_a_legacy_supervisor_archive(tmp_path, metadata):
    root, job, _ = stage(tmp_path, metadata)
    job_ref = put_bytes(
        root,
        job.to_json().encode(),
        name="job.json",
        media_type="application/json",
        producer="author",
    )
    archive = FrozenInferenceArchive(
        "utility-frozen-inference-archive-v1",
        job_ref,
        job_ref,
        job_ref,
        job_ref,
        job_ref,
        job_ref,
        None,
        None,
        None,
    )
    ref = put_bytes(
        root,
        archive.to_json().encode(),
        name="archive.json",
        media_type="application/json",
        producer="author",
    )
    with pytest.raises(StoreError, match="guest execution receipt"):
        verify_inference_archive(
            root, ref, job.grant, job.executor_digest, job.source_digest, job.lock.sha256
        )


def test_host_cannot_impersonate_linux_x86_guest_observation():
    if sys.platform != "linux":
        with pytest.raises(ValueError):
            guest.observe_python()
    else:
        pytest.skip("host is Linux; observation checks are covered by authored identities")


def test_old_wheel_without_guest_sources_cannot_be_adopted(metadata):
    _, _, _, environment, profile, _ = metadata
    value = environment.to_dict()
    value["wheel_python_sources"] = [
        r for r in value["wheel_python_sources"] if not r["path"].endswith("/inference_guest.py")
    ]
    altered = replace(
        profile,
        environment_inputs_digest=digest(value),
        wheel_python_sources_digest=digest(value["wheel_python_sources"]),
    )
    with pytest.raises(ValueError, match="lock/wheel/code binding"):
        altered.validate_environment(value)


def test_guest_job_decodes_cold_without_environment_reads_or_runtime_probe(tmp_path, metadata):
    _, job, _ = stage(tmp_path, metadata)
    script = """
import importlib.abc,sys
class NoModels(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,*args):
  if fullname.split('.')[0] in {'examples','torch','openmdao','pvlib','py_wake'}:
   raise AssertionError('model import')
sys.meta_path.insert(0,NoModels())
from pathlib import Path
from autoengineering.utility.inference_execution import FrozenInferenceJob,FrozenGuestInferenceJob
from autoengineering.utility import inference_guest
import subprocess,socket,os,numpy
def forbidden(*args,**kwargs):raise AssertionError('runtime, data or execution access')
Path.open=os.open=subprocess.Popen=socket.socket=numpy.load=inference_guest.observe_python=forbidden
job=FrozenInferenceJob.from_json(sys.argv[1])
assert isinstance(job,FrozenGuestInferenceJob)
print(job.digest)
"""
    result = subprocess.run(
        [sys.executable, "-c", script, job.to_json()],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stdout.strip() == job.digest
