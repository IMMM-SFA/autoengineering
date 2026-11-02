"""Container recovery must not infer inner stop from an outer worker exit."""

from dataclasses import replace
import hashlib
import json
import subprocess

import pytest

from autoengineering.agents import container_recovery as recovery
from autoengineering.agents.containers import DockerBoundary
from autoengineering.agents.qualification import VerifiedQualification
from autoengineering.campaign.serialization import digest
from test_agent_containers import CID, policy, runtime


@pytest.fixture
def execution(tmp_path, monkeypatch):
    value, args = policy(tmp_path)
    actual_runtime = replace(runtime(), client_sha256="1" * 64, server_fingerprint="2" * 64)
    sources, payload = {"probe.py": b"print('ok')"}, b"input"
    declaration = {
        "version": DockerBoundary.version,
        "nonce": "a" * 32,
        "image_id": actual_runtime.image_id,
        "repository_digest": actual_runtime.repository_digest,
        "sources": {key: hashlib.sha256(raw).hexdigest() for key, raw in sources.items()},
        "entrypoint": "probe.py",
        "input_sha256": hashlib.sha256(payload).hexdigest(),
        "cpu_seconds": args["limits"].cpu_seconds,
        "memory_bytes": args["limits"].memory_bytes,
        "output_bytes": args["limits"].output_bytes,
        "wall_seconds": 5,
    }
    (tmp_path / "intent.json").write_text(json.dumps(declaration))
    (tmp_path / "stdin.bin").write_bytes(payload)
    for name, raw in sources.items():
        (tmp_path / "export" / name).write_bytes(raw)
    (tmp_path / "docker-config").mkdir(mode=0o700)
    value["Config"]["Labels"] = {
        "autoengineering.nonce": declaration["nonce"],
        "autoengineering.intent": digest(declaration),
    }
    value["HostConfig"]["RestartPolicy"] = {"Name": "no"}
    value["State"] = {"Status": "running", "Running": True}
    saved = {
        "id": CID,
        "image": actual_runtime.image_id,
        "host": value["HostConfig"],
        "config": value["Config"],
        "mounts": value["Mounts"],
    }
    (tmp_path / "effective-policy.json").write_text(json.dumps(saved))
    qualified = VerifiedQualification("3" * 64, "4" * 64, actual_runtime, args["limits"])
    monkeypatch.setattr(recovery, "verify_qualification", lambda *a, **k: qualified)
    monkeypatch.setattr(recovery, "discover_runtime", lambda *a, **k: actual_runtime)
    calls = []
    state = {"value": value, "stop_works": True, "error": None}

    def metadata(self, root, *command, **kwargs):
        calls.append(command)
        if command[0] in ("kill", "rm"):
            assert command[1] == CID
            if state["stop_works"]:
                if command[0] == "rm":
                    state["value"] = None
                else:
                    state["value"]["State"] = {"Status": "exited", "Running": False}
            return subprocess.CompletedProcess(command, 0, b"", b"")
        assert command == ("inspect", "--format", "{{json .}}", CID)
        if state["error"]:
            return subprocess.CompletedProcess(command, 1, b"", state["error"])
        if state["value"] is None:
            return subprocess.CompletedProcess(
                command, 1, b"", f"Error: No such object: {CID}".encode()
            )
        return subprocess.CompletedProcess(command, 0, json.dumps(state["value"]).encode(), b"")

    monkeypatch.setattr(DockerBoundary, "_metadata", metadata)
    kwargs = dict(
        qualification_root=tmp_path,
        qualification_digest=qualified.receipt_digest,
        sources=sources,
        payload=payload,
        entrypoint="probe.py",
    )
    return tmp_path, kwargs, state, calls


def save_result(root, *, status="success"):
    declaration = json.loads((root / "intent.json").read_text())
    (root / "stdout.bin").write_bytes(b"ok\n")
    (root / "stderr.bin").write_bytes(b"")
    result = {
        "container_id": CID,
        "nonce": declaration["nonce"],
        "intent_digest": digest(declaration),
        "image_id": declaration["image_id"],
        "stopped": True,
        "exitcode": 0,
        "oom_killed": False,
        "elapsed_seconds": 0.25,
        "status": status,
        "stdout_sha256": hashlib.sha256(b"ok\n").hexdigest(),
        "stderr_sha256": hashlib.sha256(b"").hexdigest(),
        "effective_policy_sha256": hashlib.sha256(
            (root / "effective-policy.json").read_bytes()
        ).hexdigest(),
    }
    (root / "result.json").write_text(json.dumps(result))
    return result


def test_outer_exit_does_not_prove_container_stop(execution):
    root, kwargs, _, calls = execution
    receipt = recovery.reconcile_container(root, **kwargs)
    assert not receipt.stopped and not receipt.stop_requested
    assert receipt.result_digest is None
    assert all(command[0] == "inspect" for command in calls)


def test_owned_running_container_stops_after_second_ownership_check(execution):
    root, kwargs, _, calls = execution
    receipt = recovery.reconcile_container(root, stop=True, **kwargs)
    assert receipt.stopped and receipt.stop_requested and not receipt.removed
    assert [command[0] for command in calls] == ["inspect", "inspect", "kill", "inspect"]
    assert receipt.result_digest is None  # Stop is not a recovered numerical result.


def test_created_container_removed_before_a_late_owner_can_start_it(execution):
    root, kwargs, state, calls = execution
    state["value"]["State"] = {"Status": "created", "Running": False}
    receipt = recovery.reconcile_container(root, stop=True, **kwargs)
    assert receipt.stopped and receipt.removed
    assert [command[0] for command in calls] == ["inspect", "inspect", "rm", "inspect"]


def test_unsuccessful_kill_keeps_stop_uncertain(execution):
    root, kwargs, state, _ = execution
    state["stop_works"] = False
    receipt = recovery.reconcile_container(root, stop=True, **kwargs)
    assert not receipt.stopped and receipt.stop_requested


def test_absence_without_result_is_stopped_but_has_no_outcome(execution):
    root, kwargs, state, calls = execution
    state["value"] = None
    receipt = recovery.reconcile_container(root, stop=True, **kwargs)
    assert receipt.stopped and receipt.removed and not receipt.stop_requested
    assert receipt.stdout is None and receipt.result_status is None
    assert len(calls) == 1


def test_saved_success_recovers_raw_output_without_new_execution(execution):
    root, kwargs, state, calls = execution
    expected = save_result(root)
    state["value"] = None
    before = (root / "result.json").read_bytes()
    receipt = recovery.reconcile_container(root, **kwargs)
    assert receipt.stopped and receipt.result_status == "success"
    assert receipt.result_digest == digest(expected) and receipt.stdout == b"ok\n"
    assert (root / "result.json").read_bytes() == before
    assert all(command[0] == "inspect" for command in calls)


@pytest.mark.parametrize(
    "error",
    [
        b"Cannot connect to the Docker daemon",
        b"permission denied",
        b"Error: No such object: " + b"d" * 64,
        b"Error: No such object: " + CID.encode() + b"\npermission denied",
    ],
)
def test_daemon_error_never_counts_as_absence(execution, error):
    root, kwargs, state, calls = execution
    state["error"] = error
    with pytest.raises(ValueError, match="unresolved"):
        recovery.reconcile_container(root, stop=True, **kwargs)
    assert all(command[0] == "inspect" for command in calls)


def test_lowercase_docker_absence_diagnostic(execution):
    root, kwargs, state, _ = execution
    state["error"] = f"error: no such object: {CID}\n".encode()
    assert recovery.reconcile_container(root, **kwargs).removed


@pytest.mark.parametrize(
    "change", ["nonce", "image", "mount", "restart", "source", "input", "result", "stdout"]
)
def test_changed_evidence_never_authorizes_a_signal(execution, change):
    root, kwargs, state, calls = execution
    if change == "nonce":
        state["value"]["Config"]["Labels"]["autoengineering.nonce"] = "b" * 32
    elif change == "image":
        state["value"]["Image"] = "sha256:" + "f" * 64
    elif change == "mount":
        state["value"]["Mounts"][0]["RW"] = True
    elif change == "restart":
        state["value"]["HostConfig"]["RestartPolicy"]["Name"] = "always"
    elif change == "source":
        (root / "export/probe.py").write_bytes(b"different source")
    elif change == "input":
        kwargs["payload"] = b"different input"
    elif change == "result":
        save_result(root, status="success")
    else:
        save_result(root)
        (root / "stdout.bin").write_bytes(b"tampered")
    with pytest.raises(ValueError):
        recovery.reconcile_container(root, stop=True, **kwargs)
    # Contradictory saved success must not authorize even a stop signal.
    assert all(command[0] == "inspect" for command in calls)


def test_changed_runtime_fails_before_any_daemon_command(execution, monkeypatch):
    root, kwargs, _, calls = execution
    monkeypatch.setattr(recovery, "discover_runtime", lambda *a, **k: runtime())
    with pytest.raises(ValueError, match="runtime differs"):
        recovery.reconcile_container(root, stop=True, **kwargs)
    assert not calls


@pytest.mark.parametrize(
    "status,running", [("created", False), ("paused", True), ("removing", False)]
)
def test_nonterminal_state_is_not_certified_stopped(execution, status, running):
    root, kwargs, state, _ = execution
    state["value"]["State"] = {"Status": status, "Running": running}
    assert not recovery.reconcile_container(root, **kwargs).stopped


def test_source_symlink_is_rejected_before_daemon_access(execution):
    root, kwargs, _, calls = execution
    (root / "other.py").write_bytes(kwargs["sources"]["probe.py"])
    (root / "export/probe.py").unlink()
    (root / "export/probe.py").symlink_to(root / "other.py")
    with pytest.raises(ValueError, match="symlink"):
        recovery.reconcile_container(root, **kwargs)
    assert not calls


def test_ownership_is_rechecked_before_signalling(execution, monkeypatch):
    root, kwargs, state, calls = execution
    original = DockerBoundary._metadata

    def changed(self, *args, **options):
        if len(calls) == 1:
            state["value"]["Config"]["Labels"]["autoengineering.nonce"] = "e" * 32
        return original(self, *args, **options)

    monkeypatch.setattr(DockerBoundary, "_metadata", changed)
    with pytest.raises(ValueError, match="ownership"):
        recovery.reconcile_container(root, stop=True, **kwargs)
    assert [call[0] for call in calls] == ["inspect", "inspect"]


def test_repeated_finished_recovery_is_read_only(execution):
    root, kwargs, state, calls = execution
    save_result(root)
    state["value"] = None
    first = recovery.reconcile_container(root, **kwargs)
    second = recovery.reconcile_container(root, stop=True, **kwargs)
    assert first == second
    assert [call[0] for call in calls] == ["inspect", "inspect"]


def test_missing_launch_metadata_remains_unresolved(execution):
    root, kwargs, _, calls = execution
    (root / "container-id").unlink()
    with pytest.raises(ValueError, match="regular file"):
        recovery.reconcile_container(root, stop=True, **kwargs)
    assert not calls


def test_uncertain_saved_result_does_not_prevent_owned_stop_or_invent_an_outcome(execution):
    root, kwargs, state, calls = execution
    result = save_result(root, status="reconciliation_required")
    result["stopped"] = False
    (root / "result.json").write_text(json.dumps(result))
    original = (root / "result.json").read_bytes()
    proof = recovery.reconcile_container(root, stop=True, **kwargs)
    assert proof.stopped and proof.stop_requested
    assert proof.result_digest is None and proof.result_status is None and proof.stdout is None
    assert (root / "result.json").read_bytes() == original
    assert [call[0] for call in calls] == ["inspect", "inspect", "kill", "inspect"]
