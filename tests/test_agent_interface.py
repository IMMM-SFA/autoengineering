"""Frozen interface fixtures and receipt reconstruction without candidate execution."""

from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from autoengineering.agents.containers import ContainerResult
from autoengineering.agents.interface import (
    InterfaceCase,
    InterfaceCheck,
    InterfaceSpec,
    check_interface,
    verify_interface,
)
from autoengineering.agents.sandbox import BoundaryLimits
from autoengineering.agents.workspaces import CandidateWorkspace
from autoengineering.campaign.records import PortContract
from autoengineering.campaign.serialization import canonical_json, digest
from test_agent_containers import policy, runtime

PIN = "a" * 64
SOURCE = b'def predict(inputs):\n return {"prediction":inputs["forcing"]*2.0}\n'


def spec():
    def port(name):
        return PortContract(name, (), "mm/day", "float", (), "scalar", digest([]), None)

    return InterfaceSpec(
        "1.0",
        (port("forcing"),),
        (port("prediction"),),
        (
            InterfaceCase("first", {"forcing": 1.5}, {"prediction": 3.0}),
            InterfaceCase("second", {"forcing": 2.5}, {"prediction": 5.0}),
        ),
    )


@pytest.fixture
def run(tmp_path, monkeypatch):
    import autoengineering.agents.interface as module

    tmp_path.chmod(0o700)
    work = CandidateWorkspace.create(
        tmp_path / "workspace", run_id="run", task_id="implement", baseline={"adapter.py": SOURCE}
    )
    capture = work.capture()
    limits = BoundaryLimits(1, 128 * 1024 * 1024, 4096)
    qualified = SimpleNamespace(receipt_digest=PIN, runtime=runtime(), limits=limits)

    def qualification(root, *, expected_digest):
        if expected_digest != PIN:
            raise ValueError("qualification pin differs from trusted receipt")
        return qualified

    monkeypatch.setattr(module, "verify_qualification", qualification)
    calls = []
    replies = []

    def fake(self, sources, **kwargs):
        calls.append(kwargs)
        assert sources["adapter.py"] == SOURCE
        assert b'"expected"' not in kwargs["payload"]
        assert b'"prediction"' not in kwargs["payload"]
        root = kwargs["root"]
        root.mkdir(mode=0o700)
        value, args = policy(root)
        for name, raw in sources.items():
            (root / "export" / name).write_bytes(raw)
        (root / "stdin.bin").write_bytes(kwargs["payload"])
        intent = {
            "version": self.version,
            "entrypoint": "driver.py",
            "nonce": "nonce",
            "image_id": self.runtime.image_id,
            "repository_digest": self.runtime.repository_digest,
            "sources": {name: hashlib.sha256(raw).hexdigest() for name, raw in sources.items()},
            "input_sha256": hashlib.sha256(kwargs["payload"]).hexdigest(),
            "wall_seconds": 5,
            "cpu_seconds": limits.cpu_seconds,
            "memory_bytes": limits.memory_bytes,
            "output_bytes": limits.output_bytes,
        }
        (root / "intent.json").write_text(canonical_json(intent))
        value["Config"]["Cmd"] = ["-I", "-S", "-B", "/work/driver.py"]
        value["Config"]["Labels"]["autoengineering.intent"] = digest(intent)
        host = value["HostConfig"]
        host.update(Memory=limits.memory_bytes, MemorySwap=limits.memory_bytes)
        for limit in host["Ulimits"]:
            if limit["Name"] in ("cpu", "fsize"):
                number = limits.cpu_seconds if limit["Name"] == "cpu" else limits.output_bytes
                limit.update(Soft=number, Hard=number)
        frozen = {
            "id": value["Id"],
            "image": value["Image"],
            "config": value["Config"],
            "host": host,
            "mounts": value["Mounts"],
        }
        policy_raw = canonical_json(frozen).encode()
        (root / "effective-policy.json").write_bytes(policy_raw)
        actual = json.loads(kwargs["payload"])["inputs"]["forcing"] * 2.0
        raw = canonical_json(
            {"schema_version": "1.0", "outputs": {"prediction": actual}, "inputs_unchanged": True}
        ).encode()
        status, stopped = "success", True
        if replies:
            raw, status, stopped = replies.pop(0)
        (root / "stdout.bin").write_bytes(raw)
        (root / "stderr.bin").write_bytes(b"")
        result = {
            "status": status,
            "container_id": value["Id"],
            "nonce": "nonce",
            "stopped": stopped,
            "image_id": self.runtime.image_id,
            "intent_digest": digest(intent),
            "stdout_sha256": hashlib.sha256(raw).hexdigest(),
            "stderr_sha256": hashlib.sha256(b"").hexdigest(),
            "effective_policy_sha256": hashlib.sha256(policy_raw).hexdigest(),
            "oom_killed": False,
            "elapsed_seconds": 0.01,
        }
        (root / "result.json").write_text(canonical_json(result))
        return ContainerResult(status, value["Id"], raw, b"", stopped, False, 0.01, digest(result))

    monkeypatch.setattr(module.DockerBoundary, "run_qualified", fake)
    options = {
        "qualification_root": tmp_path / "qualification",
        "qualification_digest": PIN,
        "output": tmp_path / "checks",
    }
    return SimpleNamespace(
        work=work, capture=capture, spec=spec(), calls=calls, replies=replies, options=options
    )


def test_immutable_source_fixtures_exclude_expected_outputs_and_reconstruct(run):
    (run.work.candidate / "adapter.py").write_text("changed after snapshot")
    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    assert receipt.status == "pass" and len(run.calls) == 2
    arguments = {key: value for key, value in run.options.items() if key != "output"}
    assert (
        verify_interface(
            run.options["output"],
            run.work,
            run.capture,
            run.spec,
            expected_receipt_digest=receipt.digest,
            **arguments,
        )
        == receipt
    )


@pytest.mark.parametrize(
    "raw,status,stopped",
    [
        (b"{}", "success", True),
        (
            b'{"schema_version":"1.0","outputs":{"prediction":3},"inputs_unchanged":true}',
            "success",
            True,
        ),
        (
            b'{"schema_version":"1.0","outputs":{"prediction":3.0},"inputs_unchanged":false}',
            "success",
            True,
        ),
        (
            b'{"schema_version":"1.0","outputs":{"prediction":NaN},"inputs_unchanged":true}',
            "success",
            True,
        ),
        (
            b'{"schema_version":"1.0","outputs":{"prediction":4.0},"inputs_unchanged":true}',
            "success",
            True,
        ),
        (b"", "timeout", True),
        (b"", "model_failure", True),
        (b"", "output_limit", True),
        (b"", "reconciliation_required", False),
    ],
)
def test_failures_and_skipped_cases_remain_visible(run, raw, status, stopped):
    run.replies.append((raw, status, stopped))
    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    assert receipt.status == ("fail" if stopped else "reconciliation_required")
    assert receipt.checks[1].status == "not_attempted" and len(run.calls) == 1
    arguments = {key: value for key, value in run.options.items() if key != "output"}
    assert (
        verify_interface(
            run.options["output"],
            run.work,
            run.capture,
            run.spec,
            expected_receipt_digest=receipt.digest,
            **arguments,
        )
        == receipt
    )


@pytest.mark.parametrize(
    "name",
    [
        "case-000/stdout.bin",
        "case-000/effective-policy.json",
        "case-000/export/adapter.py",
        "case-000/stdin.bin",
    ],
)
def test_changed_execution_artifacts_fail_verification(run, name):
    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    (run.options["output"] / name).write_bytes(b"changed")
    arguments = {key: value for key, value in run.options.items() if key != "output"}
    with pytest.raises(ValueError):
        verify_interface(
            run.options["output"],
            run.work,
            run.capture,
            run.spec,
            expected_receipt_digest=receipt.digest,
            **arguments,
        )


def test_independent_static_policy_rejects_false_claim_before_execution(run):
    (run.work.candidate / "adapter.py").write_bytes(
        b"import os\ndef predict(inputs):\n return os.environ\n"
    )
    capture = replace(run.work.capture(), issues=())
    with pytest.raises(ValueError, match="independently failed"):
        check_interface(run.work, capture, run.spec, **run.options)
    assert not run.calls and not run.options["output"].exists()


def test_wrong_qualification_pin_prevents_execution(run):
    run.options["qualification_digest"] = "b" * 64
    with pytest.raises(ValueError, match="pin differs"):
        check_interface(run.work, run.capture, run.spec, **run.options)
    assert not run.calls and not run.options["output"].exists()


def test_recomputed_receipt_cannot_hide_changed_container_privileges(run):
    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    root = run.options["output"] / "case-000"
    frozen = json.loads((root / "effective-policy.json").read_text())
    frozen["host"]["CapDrop"] = []
    raw = canonical_json(frozen).encode()
    (root / "effective-policy.json").write_bytes(raw)
    result = json.loads((root / "result.json").read_text())
    result["effective_policy_sha256"] = hashlib.sha256(raw).hexdigest()
    (root / "result.json").write_text(canonical_json(result))
    changed = replace(
        receipt,
        checks=(
            InterfaceCheck("first", "pass", "public_fixture_passed", digest(result)),
            receipt.checks[1],
        ),
    )
    (run.options["output"] / "receipt.json").write_text(changed.to_json())
    arguments = {key: value for key, value in run.options.items() if key != "output"}
    with pytest.raises(ValueError, match="capabilities"):
        verify_interface(
            run.options["output"],
            run.work,
            run.capture,
            run.spec,
            expected_receipt_digest=changed.digest,
            **arguments,
        )


def test_changed_units_cannot_reinterpret_a_saved_interface_check(run):
    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    changed = replace(run.spec, outputs=(replace(run.spec.outputs[0], units="m/day"),))
    arguments = {key: value for key, value in run.options.items() if key != "output"}
    with pytest.raises(ValueError, match="manifest"):
        verify_interface(
            run.options["output"],
            run.work,
            run.capture,
            changed,
            expected_receipt_digest=receipt.digest,
            **arguments,
        )


def test_relocation_is_explicit_and_reads_no_original_execution_files(run, tmp_path):
    import shutil

    receipt = check_interface(run.work, run.capture, run.spec, **run.options)
    moved = tmp_path / "moved"
    shutil.copytree(run.options["output"], moved)
    arguments = {key: value for key, value in run.options.items() if key != "output"}
    with pytest.raises(ValueError, match="manifest"):
        verify_interface(
            moved,
            run.work,
            run.capture,
            run.spec,
            expected_receipt_digest=receipt.digest,
            **arguments,
        )
    shutil.rmtree(run.options["output"])
    assert (
        verify_interface(
            moved,
            run.work,
            run.capture,
            run.spec,
            relocated=True,
            expected_receipt_digest=receipt.digest,
            **arguments,
        )
        == receipt
    )
