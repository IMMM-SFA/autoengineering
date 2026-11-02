"""Owned supervisor tests with an authored qualifier, executable and wrapper.

The fixed upstream worker is real but held before its gate. No credential or
provider is used. These unit attestations do not qualify a native boundary.
"""

from pathlib import Path
import sys

import pytest
import autoengineering

from autoengineering.agents import conformance_owner as module
from autoengineering.agents.conformance_runtime import ConformanceRuntime
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.store import StoreError
from test_agent_conformance_runtime import fixture
from test_agent_conformance import snapshot


def owner_fixture(tmp_path, monkeypatch):
    runtime, config, calls = fixture(tmp_path, monkeypatch, provider=False)
    role_root = runtime.batch.root / "cases/roles/worker"
    role_root.parent.mkdir(mode=0o700, parents=True)
    worker = WorkerStore.create(role_root, runtime.plan.worker)
    for case in runtime.plan.batch.cases[:4]:
        runtime.batch.start_case(case.id, case.configuration_digest)
        runtime.batch.finish_case(
            case.id,
            "passed",
            (
                runtime.batch.evidence(
                    {
                        "unit_attestation_only": True,
                        "executed": False,
                        "worker_head": worker.replay().events[-1].digest,
                    }
                ),
            ),
        )
    script = tmp_path / "authored-supervisor.py"
    script.write_text(f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(Path(autoengineering.__file__).resolve().parent.parent)!r})
from autoengineering.agents.hosts import brokered_host as adapter
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex, WrappedCommand
from autoengineering.agents.hosts.native_profile import VerifiedNativeProfile
from autoengineering.campaign.store import durable_write
from autoengineering.agents.conformance_owner import child
inventory=inspect_brokered_codex(Path({str(tmp_path / "fake-codex")!r}))
profile=VerifiedNativeProfile(Path({str(tmp_path)!r}),"0"*64,inventory,"gpt-5.5",30,65536,65536,"1"*64)
adapter.verify_native_profile=lambda *a,**k:profile
def wrap(self,command,endpoint,*_):
    policy=endpoint.directory.parent/"unit-policy.sb"
    durable_write(policy,b"authored unit wrapper, no native qualification")
    return WrappedCommand(command,policy)
adapter.BrokeredCodexHost._wrap=wrap
child(Path(sys.argv[1]))
""")
    monkeypatch.setattr(
        module, "owner_command", lambda job: (sys.executable, "-I", str(script), str(job))
    )
    return runtime, config, calls


def test_owner_loss_retires_original_call_as_unknown_without_preflight_or_relaunch(
    tmp_path, monkeypatch
):
    runtime, config, calls = owner_fixture(tmp_path, monkeypatch)
    report = runtime.advance(max_new_cases=1)
    assert report["case_results"]["owner_loss"] == "passed"
    assert report["status"] == "ready" and not report["live_conformance_complete"]
    proof = report["case_verdicts"]["owner_loss"]
    assert proof["phase"] == module.PHASE and proof["credential_preflight"] == "not_started"
    assert proof["host_status"] == "host_failure" and proof["stop_verified"]
    assert proof["usage"] == {} and proof["elapsed_seconds"] is proof["resolved_model"] is None
    assert proof["request_may_have_been_sent"] is False
    assert report["host_reservations_charged"] == 1 and not calls
    assert report["scientific_reservations_charged"] == 0
    batch = runtime.batch.replay()
    reservation = next(iter(batch.reservations.values()))
    observation = batch.observations[reservation.id]
    assert observation.transcript_bytes is None
    assert batch.charged_transcript_bytes == reservation.transcript_ceiling
    root = runtime.batch.root / "cases/owner_loss"
    assert not (root / "owner_loss-call/upstream/attempt/process/launch-gate.json").exists()
    assert not (root / "owner_loss-call/upstream/attempt/provider-intent.json").exists()
    before = snapshot(runtime.batch.root)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    assert reopened.owner_loss() == proof
    assert snapshot(runtime.batch.root) == before
    assert reopened.advance(max_new_cases=0) == report
    ownership = proof["ownership"]["evidence"]
    (runtime.batch.root / ownership["path"]).write_bytes(b"corrupt proof")
    with pytest.raises(ValueError):
        reopened.report()


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_owner_loss_recovers_verdict_ack_loss_without_replacement(tmp_path, monkeypatch, stage):
    runtime, config, _ = owner_fixture(tmp_path, monkeypatch)

    def fault(point):
        proof_exists = any(
            b'"kind":"owned_supervisor_interruption_before_credential_preflight"' in p.read_bytes()
            for p in (runtime.batch.root / "artifacts").glob("*/receipt.json")
        )
        if point == stage and proof_exists:
            raise RuntimeError("authored owner-loss acknowledgment fault")

    runtime.batch.fault = fault
    with pytest.raises(RuntimeError, match="acknowledgment"):
        runtime.advance(max_new_cases=1)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    # Once CaseFinished committed, allowing a new case would legitimately start
    # malformed. Acknowledgment replay must inspect that committed verdict only.
    report = reopened.advance(max_new_cases=0 if stage == "after_event_commit" else 1)
    assert report["case_results"]["owner_loss"] == "passed"
    assert report["host_reservations_charged"] == 1


def test_saved_supervisor_metadata_before_launch_is_pending_and_never_launched_on_reopen(
    tmp_path, monkeypatch
):
    runtime, config, _ = owner_fixture(tmp_path, monkeypatch)

    def absent(*_):
        raise RuntimeError("authored before supervisor launch")

    monkeypatch.setattr(module, "_launch", absent)
    with pytest.raises(RuntimeError):
        runtime.advance(max_new_cases=1)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    report = reopened.advance(max_new_cases=1)
    assert report["status"] == "reconciliation_required"
    assert report["active_case"] == "owner_loss" and not report["host_reservations_charged"]


def test_changed_supervisor_binding_is_rejected_without_another_launch(tmp_path, monkeypatch):
    runtime, _, _ = owner_fixture(tmp_path, monkeypatch)
    runtime.advance(max_new_cases=1)
    root = runtime.batch.root / "cases/owner_loss"
    (root / "host.toml").write_text('schema_version="changed"')
    with pytest.raises(StoreError, match="metadata changed"):
        runtime.owner_loss()
    assert len(runtime.batch.replay().reservations) == 1


def test_copied_bound_request_corruption_invalidates_owner_loss_report(tmp_path, monkeypatch):
    runtime, _, _ = owner_fixture(tmp_path, monkeypatch)
    report = runtime.advance(max_new_cases=1)
    reference = report["case_verdicts"]["owner_loss"]["captures"][1]
    assert read_bytes(runtime.batch.root, ArtifactRef.from_dict(reference))
    (runtime.batch.root / reference["path"]).write_bytes(b"changed request")
    with pytest.raises(ValueError):
        runtime.report()


def test_unobserved_native_watchdog_remains_pending_then_recovers_same_call(tmp_path, monkeypatch):
    runtime, config, _ = owner_fixture(tmp_path, monkeypatch)
    original = module.recover_watchdog_stop

    def unavailable(directory):
        if Path(directory).parent.name == "transport":
            raise ValueError("authored unavailable native observation")
        return original(directory)

    monkeypatch.setattr(module, "recover_watchdog_stop", unavailable)
    report = runtime.advance(max_new_cases=1)
    assert report["status"] == "reconciliation_required"
    assert report["host_reservations_charged"] == 1
    assert report["pending_reservations"]
    monkeypatch.setattr(module, "recover_watchdog_stop", original)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    final = reopened.advance(max_new_cases=1)
    assert final["case_results"]["owner_loss"] == "passed"
    assert final["host_reservations_charged"] == 1 and not final["pending_reservations"]


def test_native_failure_before_gate_is_failed_unexercised_without_retry(tmp_path, monkeypatch):
    from autoengineering.agents.hosts import brokered_host as adapter
    from autoengineering.agents.hosts.native_profile import VerifiedNativeProfile
    from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex
    from test_agent_brokered_codex import program

    runtime, config, _ = owner_fixture(tmp_path, monkeypatch)
    native = program(tmp_path)
    native.write_text(
        native.read_text().replace(
            " prompt=sys.stdin.read()", " prompt=sys.stdin.read()\n sys.exit(17)"
        )
    )
    inventory = inspect_brokered_codex(native)
    profile = VerifiedNativeProfile(
        tmp_path, "0" * 64, inventory, "gpt-5.5", 30, 65536, 65536, "1" * 64
    )
    monkeypatch.setattr(adapter, "verify_native_profile", lambda *a, **k: profile)
    report = runtime.advance(max_new_cases=1)
    proof = report["case_verdicts"]["owner_loss"]
    assert report["status"] == "failed" and not proof["intended_phase_exercised"]
    assert proof["reason"] == "native_stopped_before_interruption_gate"
    assert proof["stop_verified"] and not report["pending_reservations"]
    assert report["host_reservations_charged"] == 1
    assert not (runtime.batch.root / "cases/owner_loss/phase-ready.json").exists()
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    before = snapshot(runtime.batch.root)
    assert reopened.advance() == report and snapshot(runtime.batch.root) == before
