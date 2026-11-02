"""Authored identity-discovery controls; no real Docker or image execution."""

import json
import shutil
from types import SimpleNamespace
import zipfile

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import guest_identity as module
from examples.utility import guest_image_build as build
from examples.utility import guest_image_environment
from examples.utility.inference_environment import verify_inputs
import test_utility_guest_image_build as parent
import test_utility_inference_environment as environment_fixture

SERVER = {"Os": "linux", "Arch": "arm64", "Version": "authored", "ApiVersion": "1.56"}
CID = "8" * 64


def test_derived_prepare_binds_verified_derivative_environment(tmp_path, monkeypatch):
    original = tmp_path / "derived"
    original.mkdir(mode=0o700)
    module._save(
        original, "complete.json", {"schema": "utility-guest-image-environment-completion-v1"}
    )
    module._save(original, "request.json", {"environment_digest": "7" * 64})
    module._save(original, "bindings.json", {})
    calls = []

    def verified(root, *, expected_digest):
        calls.append((root, expected_digest))
        return {"image_id": "sha256:" + "6" * 64}

    def stop(environment, *, expected_digest):
        assert expected_digest == "7" * 64
        raise ValueError("stopped before identity launch preparation")

    monkeypatch.setattr(guest_image_environment, "read_completion", verified)
    monkeypatch.setattr(
        build, "read_completion", lambda *a, **kw: pytest.fail("used legacy build reader")
    )
    monkeypatch.setattr(module, "verify_inputs", stop)
    with pytest.raises(ValueError, match="stopped before"):
        module.prepare(
            original,
            completion_digest="5" * 64,
            environment=tmp_path / "environment",
            output=tmp_path / "bundle",
            work=tmp_path / "work",
        )
    assert calls == [(original, "5" * 64)]
    assert not (tmp_path / "work").exists() and not (tmp_path / "bundle").exists()


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    original_inputs = environment_fixture.inputs

    def inputs(root):
        lock, _ = original_inputs(root)
        with zipfile.ZipFile(root / "autoengineering-0.2.0-py3-none-any.whl", "a") as archive:
            archive.writestr("autoengineering/utility/inference_guest.py", b"# metadata only\n")
        return lock, environment_fixture.refs(root)

    monkeypatch.setattr(environment_fixture, "inputs", inputs)
    bundle, request, work, _, original = parent.prepared(tmp_path, monkeypatch)

    def version(argv, **kwargs):
        status = original(argv, **kwargs)
        if "version" in argv:
            kwargs["log"].write_text(json.dumps(SERVER))
        return status

    monkeypatch.setattr(build, "_run", version)
    completion = build.execute(bundle, expected_digest=digest(request))
    state = {"calls": [], "api": [], "owned": False, "client_status": 0, "delete_unknown": False}

    class API:
        def __init__(self, endpoint, *, api_version, server_digest):
            self.profile = SimpleNamespace(
                to_dict=lambda: {"api_version": api_version, "server_digest": server_digest}
            )

        def _json(self, *args, **kwargs):
            return SERVER

        def _request(self, method, path, **kwargs):
            state["api"].append((method, path))
            if method == "DELETE":
                if state["delete_unknown"]:
                    raise ValueError("lost removal acknowledgment")
                state["owned"] = False
                return 204, b""
            if state["owned"]:
                q = state["request"]
                value = {
                    "Id": CID,
                    "Name": "/ae-guest-identity-" + q["nonce"],
                    "Config": {
                        "Image": q["image_id"],
                        "Labels": {
                            "org.autoengineering.purpose": module.PURPOSE,
                            "org.autoengineering.nonce": q["nonce"],
                        },
                    },
                }
                if state.get("wrong_owner"):
                    value["Name"] = "/another-owner"
                return 200, json.dumps(value).encode()
            return 404, b"{}"

    monkeypatch.setattr(module, "GuestDaemonAPI", API)
    output, job = tmp_path / "identity", tmp_path / "identity-work"
    q = module.prepare(
        work,
        completion_digest=digest(completion),
        environment=tmp_path / "environment",
        output=output,
        work=job,
    )
    env = verify_inputs(tmp_path / "environment", expected_digest=q["environment_digest"])
    source = next(r for r in env.wheel_python_sources if r.path.endswith("inference_guest.py"))
    response = {
        "schema": "utility-guest-python-observation-v1",
        "nonce": q["nonce"],
        "python": {
            "schema": "utility-guest-python-identity-v1",
            "system": "Linux",
            "architecture": "x86_64",
            "implementation": "CPython",
            "version": "3.12.99",
            "build_digest": "0" * 64,
        },
        "executable": "/opt/inference/bin/python",
        "isolated": 1,
        "uid": 1000,
        "gid": 1000,
        "package_version": "0.2.0",
        "identity_source_sha256": source.sha256,
    }
    state.update(request=q, response=response)

    def run(argv, *, env, cwd, deadline, log):
        state["calls"].append((argv, env))
        (cwd / "container.id").write_text(CID)
        log.write_text(json.dumps(state["response"]))
        return state["client_status"]

    monkeypatch.setattr(build, "_run", run)
    return output, q, job, state


def test_one_fixed_metadata_start_and_unqualified_profile(prepared, monkeypatch):
    bundle, request, work, state = prepared
    monkeypatch.setenv("PRIVATE_LABEL", "NOT-A-CONTAINER-INPUT")
    result = module.execute(bundle, expected_digest=digest(request))
    assert result["profile"]["boundary"] == "unqualified-candidate"
    assert not result["runtime_qualified"] and result["scientific_starts"] == 0
    assert result["cleanup"]["absent"] and result["cleanup"]["creation_outcome_known"]
    assert len(state["calls"]) == 1
    argv, env = state["calls"][0]
    assert "--pull=never" in argv and "--rm" in argv and "PRIVATE_LABEL" not in env
    assert "--volume" not in argv and "--mount" not in argv and "--privileged" not in argv
    assert argv[argv.index("--network") + 1] == "none" and "--read-only" in argv
    with pytest.raises(ValueError, match="consumed"):
        module.execute(bundle, expected_digest=digest(request))
    assert len(state["calls"]) == 1 and (work / "complete.json").exists()


@pytest.mark.parametrize(
    "problem", ["nonce", "version", "source", "uid", "isolated", "package", "uid_float"]
)
def test_wrong_identity_never_publishes_profile_and_keeps_start_charge(prepared, problem):
    bundle, request, work, state = prepared
    if problem == "version":
        state["response"]["python"]["version"] = "3.12.98"
    elif problem == "uid_float":
        state["response"]["uid"] = 1000.0
    else:
        field = {"source": "identity_source_sha256", "package": "package_version"}.get(
            problem, problem
        )
        state["response"][field] = 0 if problem in ("uid", "isolated") else "unreviewed"
    with pytest.raises(ValueError):
        module.execute(bundle, expected_digest=digest(request))
    assert len(state["calls"]) == 1 and not (work / "complete.json").exists()
    assert json.loads((work / "intent.json").read_text())["starts_reserved"] == 1
    assert json.loads((work / "failure.json").read_text())["physical_container_starts"] == 1
    assert (work / "cleanup.json").exists()


def test_owned_cleanup_is_one_deletion_with_absence_observation(prepared):
    bundle, request, _, state = prepared
    state["owned"] = True
    result = module.execute(bundle, expected_digest=digest(request))
    assert result["cleanup"]["container_id"] == CID
    assert [m for m, _ in state["api"]] == ["GET", "DELETE", "GET"]


def test_lost_delete_ack_never_retries_or_completes(prepared):
    bundle, request, work, state = prepared
    state.update(owned=True, delete_unknown=True)
    with pytest.raises(ValueError, match="acknowledgment"):
        module.execute(bundle, expected_digest=digest(request))
    assert [m for m, _ in state["api"]] == ["GET", "DELETE"]
    assert (work / "cleanup-unknown.json").exists() and not (work / "complete.json").exists()
    with pytest.raises(ValueError, match="consumed"):
        module.execute(bundle, expected_digest=digest(request))
    assert len(state["calls"]) == 1


def test_another_owner_cannot_be_removed(prepared):
    bundle, request, work, state = prepared
    state.update(owned=True, wrong_owner=True)
    with pytest.raises(ValueError, match="ownership"):
        module.execute(bundle, expected_digest=digest(request))
    assert all(method != "DELETE" for method, _ in state["api"])
    assert (work / "cleanup-unknown.json").exists()


def test_client_failure_retains_one_intent_and_original_cleanup(prepared):
    bundle, request, work, state = prepared
    state["client_status"] = 1
    with pytest.raises(ValueError, match="client failed"):
        module.execute(bundle, expected_digest=digest(request))
    assert len(state["calls"]) == 1 and (work / "cleanup-intent.json").exists()
    assert (work / "failure.json").exists() and not (work / "complete.json").exists()


def test_changed_client_starts_no_identity_work(prepared):
    bundle, request, work, state = prepared
    bindings = json.loads((bundle / "bindings.json").read_text())
    with open(bindings["cli"], "w") as stream:
        stream.write("changed executable")
    with pytest.raises(ValueError, match="bindings changed"):
        module.execute(bundle, expected_digest=digest(request))
    assert not work.exists() and not state["calls"]


def test_missing_cid_keeps_creation_unknown_without_retry(prepared, monkeypatch):
    bundle, request, work, state = prepared
    original = build._run

    def lost_id(argv, **kwargs):
        result = original(argv, **kwargs)
        (kwargs["cwd"] / "container.id").unlink()
        return result

    monkeypatch.setattr(build, "_run", lost_id)
    with pytest.raises(ValueError, match="creation outcome remains unknown"):
        module.execute(bundle, expected_digest=digest(request))
    cleanup = json.loads((work / "cleanup.json").read_text())
    assert cleanup["absent"] and not cleanup["creation_outcome_known"]
    assert len(state["calls"]) == 1 and not (work / "complete.json").exists()


def test_saved_identity_replays_without_live_bindings(prepared, monkeypatch, tmp_path):
    bundle, request, work, _ = prepared
    result = module.execute(bundle, expected_digest=digest(request))
    copy = tmp_path / "cold"
    shutil.copytree(work, copy)

    def forbidden(*args, **kwargs):
        raise AssertionError("saved identity reader attempted a live operation")

    monkeypatch.setattr(build, "_binary", forbidden)
    monkeypatch.setattr(build, "_endpoint", forbidden)
    monkeypatch.setattr(build, "_run", forbidden)
    monkeypatch.setattr(module, "GuestDaemonAPI", forbidden)
    monkeypatch.setattr(module.time, "monotonic", forbidden)
    assert module.read_completion(copy, expected_digest=digest(result)) == result


@pytest.mark.parametrize(
    "artifact",
    ["runner.py", "output.log", "client-result.json", "container.id", "cleanup-intent.json"],
)
def test_saved_identity_rejects_changed_proofs(prepared, artifact):
    bundle, request, work, _ = prepared
    result = module.execute(bundle, expected_digest=digest(request))
    (work / artifact).write_text("tampered")
    with pytest.raises((ValueError, TypeError)):
        module.read_completion(work, expected_digest=digest(result))


def test_late_completion_keeps_start_and_cleanup_evidence(prepared, monkeypatch):
    bundle, request, work, _ = prepared
    values = iter([100.0, 101.0])
    monkeypatch.setattr(module.time, "monotonic", lambda: next(values, 171.0))
    with pytest.raises(TimeoutError, match="allowance expired"):
        module.execute(bundle, expected_digest=digest(request))
    assert not (work / "complete.json").exists() and (work / "cleanup.json").exists()
    assert json.loads((work / "failure.json").read_text())["physical_container_starts"] == 1


@pytest.mark.parametrize("problem", ["large_cid", "symlink_cid", "large_output"])
def test_saved_identity_bounds_files_before_parsing(prepared, problem):
    bundle, request, work, _ = prepared
    result = module.execute(bundle, expected_digest=digest(request))
    if problem == "large_cid":
        (work / "container.id").write_text("0" * 1024)
    elif problem == "symlink_cid":
        (work / "container.id").unlink()
        (work / "container.id").symlink_to(work.parent / "absent-private-target")
    else:
        (work / "output.log").write_bytes(b"x" * 16385)
    with pytest.raises(ValueError):
        module.read_completion(work, expected_digest=digest(result))
