"""Real owned watchdogs/API worker, authored qualification/native executable.

The API worker is held before preflight. No key or provider is used. An authored
child bootstrap supplies only qualification/wrapper stubs, never a fake stop.
"""

import json
from pathlib import Path
import sys

import autoengineering
import pytest

from autoengineering.agents import conformance_owner as owner
from autoengineering.agents.conformance_runtime import ConformanceRuntime
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.store import StoreError
from test_agent_claude_conformance_runtime import fixture
from test_agent_conformance import snapshot


def owner_fixture(tmp_path, monkeypatch, *, first_four_stubbed=True, provider=False):
    runtime, config, calls = fixture(tmp_path, monkeypatch, provider=provider)
    if first_four_stubbed:
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
    profile = config.build(runtime.plan.worker)._verify()
    inventory = profile.inventory
    script = tmp_path / "authored-claude-supervisor.py"
    script.write_text(f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(Path(autoengineering.__file__).resolve().parent.parent)!r})
from autoengineering.agents.hosts import claude_host as adapter
from autoengineering.agents.hosts.claude import ClaudeInventory
from autoengineering.agents.hosts.claude_profile import VerifiedClaudeProfile
from autoengineering.agents.hosts.codex_brokered import WrappedCommand
from autoengineering.campaign.store import durable_write
from autoengineering.agents.conformance_owner import child
inventory=ClaudeInventory({inventory.executable!r},{inventory.sha256!r},
                         {inventory.version!r},{inventory.supported_flags!r})
profile=VerifiedClaudeProfile(Path({str(profile.root)!r}),"0"*64,inventory,
    {profile.model!r},300,65536,65536,"1"*64,512,0.1)
adapter.verify_claude_profile=lambda *a,**k:profile
def wrap(self,command,endpoint,*_):
    policy=endpoint.directory.parent/"authored-policy.txt"
    durable_write(policy,b"authored identity wrapper; no OS qualification")
    return WrappedCommand(command,policy)
adapter.BrokeredClaudeHost._wrap=wrap
child(Path(sys.argv[1]))
""")
    monkeypatch.setattr(
        owner, "owner_command", lambda job: (sys.executable, "-I", str(script), str(job))
    )
    return runtime, config, calls


def test_claude_owner_loss_keeps_unknowns_and_reuses_original_watchdogs(tmp_path, monkeypatch):
    runtime, config, calls = owner_fixture(tmp_path, monkeypatch)
    report = runtime.advance(max_new_cases=1)
    proof = report["case_verdicts"]["owner_loss"]
    assert proof["passed"] and proof["intended_phase_exercised"]
    assert proof["credential_preflight"] == "not_started"
    assert proof["host_status"] == "host_failure" and proof["stop_verified"]
    assert proof["elapsed_seconds"] is proof["resolved_model"] is None and proof["usage"] == {}
    assert proof["request_may_have_been_sent"] is False
    assert proof["remote_computation_stopped"] == "unknown"
    assert report["host_reservations_charged"] == 1 and not calls
    assert report["scientific_reservations_charged"] == 0
    root = runtime.batch.root / "cases/owner_loss"
    assert (
        json.loads((root / "supervision.json").read_text())["version"]
        == "conformance-owner-loss-1.1"
    )
    assert not (root / "owner_loss-call/upstream/attempt/process/launch-gate.json").exists()
    assert not (root / "owner_loss-call/upstream/attempt/provider-intent.json").exists()
    assert not (root / "owner_loss-call/upstream/attempt/provider-result.json").exists()
    projection = runtime.batch.replay()
    reservation = next(iter(projection.reservations.values()))
    assert projection.observations[reservation.id].transcript_bytes is None
    assert projection.charged_transcript_bytes == reservation.transcript_ceiling
    before = snapshot(runtime.batch.root)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    assert reopened.owner_loss() == proof and snapshot(runtime.batch.root) == before
    assert reopened.advance(max_new_cases=0) == report
    assert not report["live_conformance_complete"]


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_claude_owner_verdict_ack_loss_does_not_start_a_replacement(tmp_path, monkeypatch, stage):
    runtime, config, _ = owner_fixture(tmp_path, monkeypatch)

    def fault(point):
        proof_exists = any(
            b'"kind":"owned_supervisor_interruption_before_credential_preflight"' in p.read_bytes()
            for p in (runtime.batch.root / "artifacts").glob("*/receipt.json")
        )
        if point == stage and proof_exists:
            raise RuntimeError("authored owner acknowledgement loss")

    runtime.batch.fault = fault
    with pytest.raises(RuntimeError, match="acknowledgement"):
        runtime.advance(max_new_cases=1)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    report = reopened.advance(max_new_cases=0 if stage == "after_event_commit" else 1)
    assert report["case_results"]["owner_loss"] == "passed"
    assert report["host_reservations_charged"] == 1


def test_claude_owner_metadata_before_launch_stays_pending_without_retry(tmp_path, monkeypatch):
    runtime, config, _ = owner_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        owner, "_launch", lambda *_: (_ for _ in ()).throw(RuntimeError("before launch"))
    )
    with pytest.raises(RuntimeError, match="before launch"):
        runtime.advance(max_new_cases=1)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    report = reopened.advance(max_new_cases=1)
    assert report["status"] == "reconciliation_required" and report["active_case"] == "owner_loss"
    assert report["host_reservations_charged"] == 0


def test_claude_owner_changed_bindings_are_rejected_without_relaunch(tmp_path, monkeypatch):
    runtime, _, _ = owner_fixture(tmp_path, monkeypatch)
    runtime.advance(max_new_cases=1)
    root = runtime.batch.root / "cases/owner_loss"
    (root / "host.toml").write_text('schema_version="1.0"')
    with pytest.raises(StoreError, match="metadata changed"):
        runtime.owner_loss()
    assert len(runtime.batch.replay().reservations) == 1


@pytest.mark.parametrize("target", ["native", "upstream"])
def test_claude_missing_watchdog_observation_stays_pending_then_recovers(
    tmp_path, monkeypatch, target
):
    runtime, config, _ = owner_fixture(tmp_path, monkeypatch)
    original = owner.recover_watchdog_stop

    def unavailable(directory):
        if Path(directory).parent.name == ("transport" if target == "native" else "attempt"):
            raise ValueError("authored unavailable native observation")
        return original(directory)

    monkeypatch.setattr(owner, "recover_watchdog_stop", unavailable)
    report = runtime.advance(max_new_cases=1)
    assert report["status"] == "reconciliation_required" and report["pending_reservations"]
    assert report["host_reservations_charged"] == 1
    monkeypatch.setattr(owner, "recover_watchdog_stop", original)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    final = reopened.advance(max_new_cases=1)
    assert final["case_results"]["owner_loss"] == "passed"
    assert final["host_reservations_charged"] == 1 and not final["pending_reservations"]


@pytest.mark.parametrize("target", ["prompt.txt", "workspace/schema.json", "job-binding.json"])
def test_claude_abandoned_input_corruption_is_not_decoded_as_failure(tmp_path, monkeypatch, target):
    runtime, _, _ = owner_fixture(tmp_path, monkeypatch)
    runtime.advance(max_new_cases=1)
    scope = runtime.batch.root / "cases/owner_loss/owner_loss-call"
    path = scope / "transport" / target
    path.write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        runtime.owner_loss()
    assert len(runtime.batch.replay().reservations) == 1


def test_legacy_configuration_bytes_are_preserved(tmp_path):
    from autoengineering.agents.host_configuration import HostConfiguration
    from autoengineering.campaign.serialization import canonical_json

    config = HostConfiguration(tmp_path, "0" * 64, tmp_path / "key", "lease")
    expected = {
        "schema_version": "1.0",
        "qualification_root": str(tmp_path),
        "qualification_digest": "0" * 64,
        "credential_path": str(tmp_path / "key"),
        "lease_id": "lease",
    }
    assert (
        owner._configuration(config)
        == "".join(f"{key} = {canonical_json(value)}\n" for key, value in expected.items()).encode()
    )


def test_all_six_claude_cases_replay_with_one_owner_charge_and_no_live_claim(tmp_path, monkeypatch):
    runtime, config, calls = owner_fixture(
        tmp_path, monkeypatch, first_four_stubbed=False, provider=True
    )
    report = runtime.advance()
    assert report["status"] == "completed" and not report["live_conformance_complete"]
    assert report["missing_execution_handlers"] == []
    assert report["case_results"] == dict.fromkeys(
        ("text", "roles", "timeout", "cancel", "owner_loss", "malformed"), "passed"
    )
    assert report["host_reservations_charged"] == 13 and len(calls) == 12
    assert report["scientific_reservations_charged"] == 2
    assert not report["pending_reservations"]
    assert report["case_verdicts"]["owner_loss"]["credential_preflight"] == "not_started"
    before = snapshot(runtime.batch.root)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    assert reopened.advance() == report and len(calls) == 12
    assert snapshot(runtime.batch.root) == before


def test_claude_ambiguous_original_owner_is_not_treated_as_dead(tmp_path, monkeypatch):
    from autoengineering.agents.hosts import claude_abandoned

    runtime, _, _ = owner_fixture(tmp_path, monkeypatch)
    runtime.advance(max_new_cases=1)
    monkeypatch.setattr(claude_abandoned, "_owner_absent", lambda *_: False)
    with pytest.raises(ValueError, match="supervisor is still live or ambiguous"):
        runtime.owner_loss()
    assert len(runtime.batch.replay().reservations) == 1
