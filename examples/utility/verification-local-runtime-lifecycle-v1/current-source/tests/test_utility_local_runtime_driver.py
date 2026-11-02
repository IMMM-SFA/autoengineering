"""Pure owned-container checks; these fixtures do not start a Docker container."""

import copy
import importlib.util
import json
from pathlib import Path
import struct
import signal

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "local_driver", ROOT / "scripts/qualify_utility_local_runtime.py"
)
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def fixture():
    plan = {
        "nonce": "a" * 32,
        "mode": "preflight",
        "stage": "/owned/stage",
        "container_id": "b" * 64,
    }
    config = driver.configuration(plan["nonce"], plan["mode"], Path(plan["stage"]))
    value = {
        "Id": plan["container_id"],
        "Image": driver.IMAGE,
        "Name": "/ae-utility-qual-" + plan["nonce"],
        "Config": config,
        "HostConfig": copy.deepcopy(config["HostConfig"]),
        "Mounts": [
            {"Type": "bind", "Source": plan["stage"], "Destination": "/qualification", "RW": False}
        ],
    }
    return plan, value


@pytest.mark.parametrize(
    "fault,expected_signal",
    [
        ("cancellation", signal.SIGTERM),
        ("owner-loss", signal.SIGKILL),
    ],
)
def test_fault_kills_only_own_controller_after_running_witness(
    tmp_path, monkeypatch, fault, expected_signal
):
    plan, value = fixture()
    plan["mode"] = "hold"
    value["Config"] = driver.configuration(plan["nonce"], "hold", Path(plan["stage"]))
    value["State"] = {"Running": True}
    witness = {"nonce": plan["nonce"], "mode": "hold", "status": "synthetic_hold_ready"}
    encoded = json.dumps(witness).encode()

    class FakeAPI:
        def inspect(self, cid):
            assert cid == plan["container_id"]
            return value

        def request(self, method, path, **kwargs):
            assert method == "GET" and path.endswith("/logs?stdout=1&stderr=1")
            return 200, bytes([1, 0, 0, 0]) + struct.pack(">I", len(encoded)) + encoded

    class Terminated(BaseException):
        pass

    def terminate(pid, sig):
        assert pid == driver.os.getpid() and sig == expected_signal
        assert json.loads((tmp_path / "fault-intent.json").read_bytes())["fault"] == fault
        assert (tmp_path / "fault-running-inspect.json").exists()
        raise Terminated()

    monkeypatch.setattr(driver.os, "kill", terminate)
    with pytest.raises(Terminated):
        driver.lifecycle_fault(FakeAPI(), plan, tmp_path, fault)


def test_fault_refuses_absent_original_without_signal(tmp_path, monkeypatch):
    plan, _ = fixture()
    plan["mode"] = "hold"

    class FakeAPI:
        def inspect(self, cid):
            return None

    monkeypatch.setattr(driver.os, "kill", lambda *_: pytest.fail("must not signal"))
    with pytest.raises(driver.Refused, match="disappeared"):
        driver.lifecycle_fault(FakeAPI(), plan, tmp_path, "owner-loss")


def test_recovery_path_never_creates_or_restarts_container(tmp_path, monkeypatch):
    plan, value = fixture()
    directory = tmp_path / "hold"
    directory.mkdir()
    source = b"authored source identity"
    (tmp_path / "controller.py").write_bytes(source)
    plan.update(mode="hold", controller_sha256=driver.sha(source), api_version="1.53")
    value["Config"] = driver.configuration(plan["nonce"], "hold", Path(plan["stage"]))
    value["State"] = {"Running": True}
    bound = {"container_id": plan["container_id"], "nonce": plan["nonce"]}
    driver.write(directory / "plan.json", plan)
    driver.write(directory / "fault-intent.json", {**bound, "fault": "lost-start-ack"})
    driver.write(directory / "cleanup.json", {**bound, "reason": "owner_pipe_eof", "removed": True})
    for name in ("fault-running-inspect.json", "cleanup-before.json"):
        driver.write(directory / name, value)

    class FakeAPI:
        def __init__(self, _):
            pass

        def inspect(self, cid):
            assert cid == plan["container_id"]
            return None

    monkeypatch.setattr(driver, "API", FakeAPI)
    result = driver.reconcile_lifecycle(tmp_path)
    assert result["live_absence_confirmed"] is True
    assert result["start_retries"] == 0
    assert result["private_scoring_qualified"] is False


def test_resource_configuration_is_checked_against_original_identity():
    plan, value = fixture()
    driver.verify_owned(value, plan)
    assert value["Config"]["Image"].startswith("sha256:")
    assert value["HostConfig"]["NetworkMode"] == "none"


@pytest.mark.parametrize(
    "field,value",
    [
        ("Memory", 134217728),
        ("MemorySwap", -1),
        ("NetworkMode", "host"),
        ("Privileged", True),
        ("ReadonlyRootfs", False),
        ("PidsLimit", 0),
        ("NanoCpus", 0),
        ("CapDrop", []),
        ("SecurityOpt", []),
        ("RestartPolicy", {"Name": "always", "MaximumRetryCount": 0}),
    ],
)
def test_unsafe_or_loosened_host_settings_prevent_start(field, value):
    plan, observed = fixture()
    observed["HostConfig"][field] = value
    with pytest.raises(driver.Refused):
        driver.verify_owned(observed, plan)


def test_extra_host_mount_or_writable_stage_prevents_start():
    plan, observed = fixture()
    observed["Mounts"][0]["RW"] = True
    with pytest.raises(driver.Refused):
        driver.verify_owned(observed, plan)
    plan, observed = fixture()
    observed["Mounts"].append(
        {"Type": "bind", "Source": "/home", "Destination": "/host", "RW": False}
    )
    with pytest.raises(driver.Refused):
        driver.verify_owned(observed, plan)


def test_only_declared_tmpfs_may_appear_as_an_extra_mount():
    plan, observed = fixture()
    observed["Mounts"].append({"Type": "tmpfs", "Destination": "/tmp", "RW": True})
    driver.verify_owned(observed, plan)
    observed["Mounts"][-1]["Destination"] = "/other"
    with pytest.raises(driver.Refused):
        driver.verify_owned(observed, plan)


def test_cleanup_never_removes_an_unrelated_identity(tmp_path):
    plan, observed = fixture()
    observed["Config"]["Labels"]["org.autoengineering.nonce"] = "c" * 32

    class FakeAPI:
        def inspect(self, cid):
            assert cid == plan["container_id"]
            return observed

        def request(self, *_):
            pytest.fail("unrelated container must not be removed")

    with pytest.raises(driver.Refused):
        driver.cleanup(FakeAPI(), plan, tmp_path, "authored")


def test_owned_unsafe_created_container_can_be_cleaned_without_running(tmp_path):
    plan, observed = fixture()
    observed["HostConfig"]["ReadonlyRootfs"] = False

    class FakeAPI:
        removed = False

        def inspect(self, cid):
            assert cid == plan["container_id"]
            return None if self.removed else observed

        def request(self, method, path):
            assert (method, path) == ("DELETE", f"/containers/{plan['container_id']}?force=true")
            self.removed = True
            return 204, b""

    driver.cleanup(FakeAPI(), plan, tmp_path, "authored")
    assert (tmp_path / "cleanup.json").exists()


def test_output_frames_are_bounded_and_reject_truncation():
    raw = bytes([1, 0, 0, 0]) + struct.pack(">I", 3) + b"abc"
    assert driver.logs(raw) == (b"abc", b"")
    with pytest.raises(driver.Refused):
        driver.logs(raw[:-1])
    payload = b"x" * (driver.OUTPUT + 1)
    with pytest.raises(driver.Refused):
        driver.logs(bytes([1, 0, 0, 0]) + struct.pack(">I", len(payload)) + payload)


def test_non_404_inspect_failure_does_not_prove_absence(monkeypatch):
    api = driver.API("1.41")
    monkeypatch.setattr(api, "request", lambda *_: (500, b"internal error"))
    with pytest.raises(driver.Refused):
        api.inspect("b" * 64)
    monkeypatch.setattr(api, "request", lambda *_: (404, b"not found"))
    assert api.inspect("b" * 64) is None
