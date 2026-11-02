"""Native runtime controls with explicit authored qualification/conformance stubs.

No measured campaign or real provider executes. These tests cannot qualify a
native boundary or establish real-provider conformance.
"""

import json
from pathlib import Path
import sys
import subprocess

import autoengineering
import pytest

from autoengineering.agents.batch import BatchStore
from autoengineering.agents.conformance import load_conformance
from autoengineering.agents.store import WorkerStore
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import digest
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import durable_write
from examples.agent_campaign import native_comparison as preparation
from examples.agent_campaign import native_interruption as interruption
from examples.agent_campaign.native_runtime import NativeRuntime
from test_agent_native_comparison import capture
from test_agent_leafriver_preparation import prepared as prepared


def setup_runtime(tmp_path, monkeypatch, prepared, *, stub=True):
    root, plan, config, calls = capture(tmp_path, monkeypatch, prepared)
    required = load_conformance(
        root / "conformance",
        expected_digest=plan.conformance.sha256,
        configuration=config,
        allow_runtime=True,
    )
    observed = BatchStore.create(required.runtime_root, required.batch)
    durable_write(
        observed.root / "origin.json",
        canonical_json(
            {
                "version": "conformance-runtime-1.0",
                "preparation_digest": plan.conformance.sha256,
                "batch_digest": observed.digest,
            }
        ).encode(),
    )
    if stub:
        # Only this test's report reader is stubbed. The actual empty runtime is ready.
        monkeypatch.setattr(
            preparation,
            "conformance_report",
            lambda *a, **k: {
                "status": "completed",
                "live_conformance_complete": True,
                "preparation_digest": plan.conformance.sha256,
                "unit_fixture": True,
            },
        )
    return root, plan, config, calls, observed


def create_runtime(root, plan, config, observed):
    return NativeRuntime.create(
        root,
        expected_digest=plan.digest,
        configuration=config,
        conformance_runtime_digest=observed.digest,
    )


def test_real_prerequisite_refuses_clock_for_empty_conformance(tmp_path, monkeypatch, prepared):
    root, plan, config, calls, observed = setup_runtime(tmp_path, monkeypatch, prepared, stub=False)
    with pytest.raises(ValueError, match="real-provider conformance"):
        create_runtime(root, plan, config, observed)
    assert not Path(plan.runtime_root).exists() and not calls


def test_runtime_binds_prerequisite_and_rejects_changed_proof_or_driver(
    tmp_path, monkeypatch, prepared
):
    root, plan, config, calls, observed = setup_runtime(tmp_path, monkeypatch, prepared)
    runtime = create_runtime(root, plan, config, observed)
    before = (runtime.batch.root / "origin.json").read_bytes()
    reopened = NativeRuntime.open(
        root,
        expected_digest=plan.digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
        conformance_runtime_digest=observed.digest,
    )
    assert reopened.batch.digest == runtime.batch.digest
    assert (runtime.batch.root / "origin.json").read_bytes() == before
    monkeypatch.setattr(
        preparation,
        "conformance_report",
        lambda *a, **k: {
            "status": "completed",
            "live_conformance_complete": True,
            "preparation_digest": plan.conformance.sha256,
            "unit_fixture": "changed",
        },
    )
    with pytest.raises(ValueError, match="origin differs"):
        NativeRuntime.open(
            root,
            expected_digest=plan.digest,
            configuration=config,
            runtime_digest=runtime.batch.digest,
            conformance_runtime_digest=observed.digest,
        )
    (root / plan.driver_sources[0].path).write_bytes(b"changed driver")
    with pytest.raises(ValueError):
        preparation.load(
            root, expected_digest=plan.digest, configuration=config, allow_runtime=True
        )
    assert not calls


def test_repinning_changed_driver_does_not_satisfy_current_source(tmp_path, monkeypatch, prepared):
    root, plan, config, calls, observed = setup_runtime(tmp_path, monkeypatch, prepared)
    from autoengineering.campaign.artifacts import reference

    data = plan.to_dict()
    path = plan.driver_sources[0].path
    (root / path).write_bytes(b"invented driver")
    data["driver_sources"][0] = reference(
        root, path, media_type="text/x-python", producer="native-comparison-preparation"
    ).to_dict()
    (root / "native-comparison.json").write_text(json.dumps(data))
    with pytest.raises(ValueError, match="driver source changed"):
        NativeRuntime.create(
            root,
            expected_digest=digest(data),
            configuration=config,
            conformance_runtime_digest=observed.digest,
        )
    assert not Path(plan.runtime_root).exists() and not calls


def test_readonly_native_status_needs_no_host_or_model_imports(tmp_path, monkeypatch, prepared):
    root, plan, config, calls, observed = setup_runtime(tmp_path, monkeypatch, prepared)
    runtime = create_runtime(root, plan, config, observed)
    source = f"""
import json,sys
from examples.agent_campaign.native_status import read_report
value=read_report({str(runtime.batch.root)!r},expected_digest={runtime.batch.digest!r})
for prefix in ('autoengineering.agents.hosts','autoengineering.agents.scheduler','autoengineering.agents.broker','autoengineering.campaign.controller','examples.campaign_contracts'):
    assert not any(n == prefix or n.startswith(prefix+'.') for n in sys.modules),prefix
assert value['status']=='ready' and value['live_comparison_complete'] is False
print(json.dumps(value))
"""
    result = subprocess.run(
        (sys.executable, "-P", "-c", source),
        capture_output=True,
        text=True,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": f"{Path(autoengineering.__file__).resolve().parent.parent}:{Path(__file__).resolve().parents[1]}",
        },
        check=True,
    )
    assert json.loads(result.stdout)["kind"] == "native_matched_leaf_river_development"
    assert not calls and runtime.batch.report()["host_reservations_charged"] == 0


@pytest.mark.parametrize("state", ["pending", "failed", "passed"])
def test_serial_driver_does_not_skip_pending_or_failed_cases(
    tmp_path, monkeypatch, prepared, state
):
    from examples.agent_campaign import native_runtime as module

    root, plan, config, calls, observed = setup_runtime(tmp_path, monkeypatch, prepared)
    runtime = create_runtime(root, plan, config, observed)
    visited = []

    def unit_case(case, **kwargs):
        visited.append(case.id)
        return (
            None
            if state == "pending"
            else {"case": case.id, "passed": state == "passed", "unit_attestation_only": True}
        )

    monkeypatch.setattr(runtime, "_case", unit_case)
    monkeypatch.setattr(module, "read_report", lambda *a, **k: runtime.batch.report())
    report = runtime.advance(max_new_cases=1)
    assert visited == ["scripted"]
    assert report["status"] == (
        "active" if state == "pending" else "failed" if state == "failed" else "ready"
    )
    runtime.advance(max_new_cases=1)
    assert visited == (
        ["scripted", "scripted"]
        if state == "pending"
        else ["scripted"]
        if state == "failed"
        else ["scripted", "single_agent"]
    )
    assert not calls and report["scientific_reservations_charged"] == 0


def authored_supervisor(tmp_path, monkeypatch, plan):
    script = tmp_path / "authored-matched-supervisor.py"
    script.write_text(f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(Path(autoengineering.__file__).resolve().parent.parent)!r})
sys.path.insert(0, {str(Path(__file__).resolve().parents[1])!r})
from autoengineering.agents.hosts import brokered_host as adapter
from autoengineering.agents.hosts.codex_brokered import inspect_brokered_codex, WrappedCommand
from autoengineering.agents.hosts.native_profile import VerifiedNativeProfile
from autoengineering.campaign.store import durable_write
from examples.agent_campaign import native_comparison as preparation
from examples.agent_campaign.native_interruption import child
inventory=inspect_brokered_codex(Path({str(tmp_path / "fake-codex")!r}))
profile=VerifiedNativeProfile(Path({str(tmp_path)!r}),"0"*64,inventory,"gpt-5.5",30,65536,65536,"1"*64)
adapter.verify_native_profile=lambda *a,**k:profile
def wrap(self,command,endpoint,*_):
    policy=endpoint.directory.parent/"unit-policy.sb"
    durable_write(policy,b"authored unit wrapper, no native qualification")
    return WrappedCommand(command,policy)
adapter.BrokeredCodexHost._wrap=wrap
preparation.conformance_report=lambda *a,**k:{{"status":"completed","live_conformance_complete":True,"preparation_digest":{plan.conformance.sha256!r},"unit_fixture":True}}
from autoengineering.campaign.controller import CampaignController
def forbidden(*a,**k): raise AssertionError("interruption attempted numerical execution")
CampaignController.create=forbidden
child(Path(sys.argv[1]))
""")
    monkeypatch.setattr(
        interruption, "owner_command", lambda job: (sys.executable, "-I", str(script), str(job))
    )


@pytest.mark.parametrize("route", ["single_agent", "four_role"])
def test_owned_interruption_charges_worker_and_batch_then_replays_without_work(
    tmp_path, monkeypatch, prepared, route
):
    root, plan, config, calls, observed = setup_runtime(tmp_path, monkeypatch, prepared)
    runtime = create_runtime(root, plan, config, observed)
    for case in plan.cases:
        runtime.batch.start_case(case.id, case.configuration_digest)
        if case.id == route:
            break
        runtime.batch.finish_case(
            case.id, "passed", (runtime.batch.evidence({"unit_fixture": True}),)
        )
    worker = runtime._worker(case)
    authored_supervisor(tmp_path, monkeypatch, plan)

    def forbidden(*args, **kwargs):
        raise AssertionError("interruption attempted numerical execution")

    monkeypatch.setattr(CampaignController, "create", forbidden)
    receipt = interruption.run_interruption(runtime, case, worker)
    assert receipt["passed"] and not receipt["reconciliation_required"]
    assert receipt["credential_preflight"] == "not_started"
    assert receipt["request_may_have_been_sent"] is False
    assert receipt["elapsed_seconds"] is receipt["resolved_model"] is None
    assert receipt["usage"] == {} and not calls
    projection = worker.replay()
    assert len(projection.tasks) == len(projection.invocations) == 1
    assert projection.repairs_used == 0 and not projection.pending
    call = projection.invocations[receipt["call_id"]]
    assert call.state == "host_failure" and call.normalized_output is None
    batch = runtime.batch.replay()
    reservation = next(iter(batch.reservations.values()))
    assert reservation.task_id == "matched-owner-interruption" and reservation.resource == "host"
    assert batch.observations[reservation.id].transcript_bytes is None
    assert batch.charged_transcript_bytes == reservation.transcript_ceiling
    assert not batch.pending
    assert runtime.batch.report()["host_reservations_charged"] == 1
    assert runtime.batch.report()["scientific_reservations_charged"] == 0
    before = runtime.batch.replay().events, worker.replay().events
    assert interruption.run_interruption(runtime, case, WorkerStore(worker.root)) == receipt
    assert (runtime.batch.replay().events, worker.replay().events) == before
    assert not config.credential_path.exists()
