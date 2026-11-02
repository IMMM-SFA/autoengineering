"""Handlers with authored native/profile/upstream and explicit provider-proof stubs.

Positive unit attestations here do not establish real provider conformance.
"""

from dataclasses import replace
import json
import time

import pytest

from autoengineering.agents.conformance import prepare_conformance, IMPLEMENTED_CASES
from autoengineering.agents.conformance_runtime import ConformanceRuntime
from autoengineering.agents.batch_native import BatchCodexHost
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError
from examples.agent_campaign.check_brokered_scheduler_fixture import authored_stream
from test_agent_conformance import fixture as preparation_fixture, snapshot


def fixture(tmp_path, monkeypatch, *, provider=True):
    root, worker, config, _, calls = preparation_fixture(tmp_path, monkeypatch)
    plan = prepare_conformance(
        worker, root / "campaign", config, tmp_path / "proposal", tmp_path / "runtime"
    )
    runtime = ConformanceRuntime.create(
        tmp_path / "proposal", expected_digest=plan.digest, configuration=config
    )
    # The helper patched the base adapter with an authored role responder.
    upstream = BatchCodexHost._upstream

    def route(self, *args):
        if self.case_id in ("timeout", "cancel"):
            scope, _, _, deadline, cancelled = args

            def waiting(raw):
                calls.append(raw)
                marker = scope / "upstream/attempt/provider-intent.json"
                marker.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                marker.write_text('{"unit_attestation_only":true}')
                while time.monotonic() < deadline + 0.1 and not cancelled():
                    time.sleep(0.005)
                raise ValueError("authored held response ended")

            return waiting
        if self.case_id == "malformed":

            def malformed_reply(raw):
                from autoengineering.agents.records import NextStep, RoleHandoff, TaskAssignment
                from autoengineering.campaign.serialization import unique_json
                from autoengineering.agents.conformance_runtime import MALFORMED_OUTPUT

                calls.append(raw)
                prompt = unique_json(raw.decode())["input"][0]["content"][0]["text"]
                context = unique_json(prompt[prompt.index('{"approved_evidence"') :])
                task = TaskAssignment.from_dict(context["task"])
                if context["repair"] is None:
                    inner = canonical_json(MALFORMED_OUTPUT)
                else:
                    inner = RoleHandoff(
                        "1.0",
                        "handoff-" + context["invocation_id"],
                        task.id,
                        context["invocation_id"],
                        task.role,
                        task.campaign_revision,
                        "complete",
                        NextStep("stop", None, "Repair validated"),
                        (),
                        (),
                        "stop",
                    ).to_json()
                return authored_stream(canonical_json({"handoff_json": inner}))

            return malformed_reply
        if self.case_id != "text":
            return upstream(self, *args)

        def call(raw):
            calls.append(raw)
            return authored_stream(canonical_json({"handoff_json": '{"ack":"conformance"}'}))

        return call

    monkeypatch.setattr(BatchCodexHost, "_upstream", route)
    if provider:
        monkeypatch.setattr(
            ConformanceRuntime,
            "_provider_evidence",
            lambda self, *_: {
                "verified": True,
                "unit_attestation_only": True,
                "evidence": self.batch.evidence(
                    {"unit_attestation_only": True, "kind": "response"}
                ).to_dict(),
            },
        )
        monkeypatch.setattr(
            ConformanceRuntime,
            "_request_evidence",
            lambda self, scope, **_: {
                "verified": (scope / "upstream/attempt/provider-intent.json").exists(),
                "unit_attestation_only": True,
            },
        )
    return runtime, config, calls


def test_supported_prefix_uses_frozen_inputs_then_stops_at_case_limit(tmp_path, monkeypatch):
    runtime, config, calls = fixture(tmp_path, monkeypatch)
    report = runtime.advance(max_new_cases=2)
    assert report["status"] == "ready" and report["live_conformance_complete"] is False
    assert report["case_results"] == {"text": "passed", "roles": "passed"}
    assert report["host_reservations_charged"] == len(calls) == 8
    assert report["scientific_reservations_charged"] == 2
    assert report["missing_execution_handlers"] == []
    before = snapshot(runtime.batch.root)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    assert reopened.advance(max_new_cases=0) == report and len(calls) == 8
    assert snapshot(runtime.batch.root) == before


def test_authored_reply_cannot_pass_provider_gate_without_stub(tmp_path, monkeypatch):
    runtime, _, calls = fixture(tmp_path, monkeypatch, provider=False)
    report = runtime.advance()
    assert report["status"] == "failed" and report["case_results"] == {"text": "failed"}
    assert len(calls) == 1 and report["scientific_reservations_charged"] == 0
    assert not (runtime.batch.root / "cases/roles").exists()


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_saved_text_recovers_when_case_verdict_acknowledgment_is_lost(tmp_path, monkeypatch, stage):
    runtime, config, calls = fixture(tmp_path, monkeypatch)

    def fault(point):
        # Interrupt case completion after the original direct invocation and
        # batch observation exist. Its SDK output must be recovered, not rerun.
        if (
            point == stage
            and (runtime.batch.root / "cases/text/text-call/adapter.json").exists()
            and runtime.batch.replay().observations
        ):
            raise RuntimeError("authored case acknowledgment loss")

    runtime.batch.fault = fault
    with pytest.raises(RuntimeError, match="acknowledgment"):
        runtime.advance()
    assert len(calls) == 1
    before = snapshot(runtime.batch.root / "cases/text/text-call")
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    report = reopened.advance(max_new_cases=2)
    assert report["case_results"]["text"] == "passed" and report["status"] == "ready"
    assert len(calls) == 8 and snapshot(runtime.batch.root / "cases/text/text-call") == before


def test_metadata_before_reservation_remains_pending_without_free_relaunch(tmp_path, monkeypatch):
    runtime, config, calls = fixture(tmp_path, monkeypatch)

    def fail(*_):
        raise RuntimeError("authored pre-reservation failure")

    monkeypatch.setattr(BatchCodexHost, "invoke_supervised", fail)
    with pytest.raises(RuntimeError):
        runtime.advance()
    assert not calls
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    with pytest.raises(StoreError, match="reservation is absent"):
        reopened.advance()
    assert not calls and not reopened.batch.replay().reservations


def test_runtime_manifest_and_origin_cannot_be_switched(tmp_path, monkeypatch):
    runtime, config, calls = fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        ConformanceRuntime.open(
            runtime.preparation,
            expected_digest=runtime.preparation_digest,
            configuration=replace(config, lease_id="changed"),
            runtime_digest=runtime.batch.digest,
        )
    path = runtime.batch.root / "origin.json"
    value = json.loads(path.read_text())
    value["preparation_digest"] = "0" * 64
    path.write_text(json.dumps(value))
    with pytest.raises(StoreError, match="origin"):
        ConformanceRuntime.open(
            runtime.preparation,
            expected_digest=runtime.preparation_digest,
            configuration=config,
            runtime_digest=runtime.batch.digest,
        )
    assert not calls


def test_implemented_handlers_are_actual_methods():
    assert all(callable(getattr(ConformanceRuntime, name)) for name in IMPLEMENTED_CASES)


def test_copied_provider_metadata_corruption_invalidates_report(tmp_path, monkeypatch):
    runtime, _, _ = fixture(tmp_path, monkeypatch)
    runtime.advance(max_new_cases=1)
    references = runtime.batch.replay().finished["text"].evidence
    assert len(references) >= 2
    (runtime.batch.root / references[1].path).write_bytes(b"changed provider proof")
    with pytest.raises(ValueError):
        runtime.report()


def test_direct_native_capture_corruption_invalidates_report(tmp_path, monkeypatch):
    runtime, _, _ = fixture(tmp_path, monkeypatch)
    report = runtime.advance(max_new_cases=1)
    ref = report["case_verdicts"]["text"]["transcripts"][0]
    (runtime.batch.root / ref["path"]).write_bytes(b"corrupt native capture")
    with pytest.raises(ValueError):
        runtime.report()


@pytest.mark.parametrize(
    "field,value",
    [
        (None, None),
        ("http_status", 401),
        ("request_may_have_been_sent", False),
        ("status", "transport_failure"),
    ],
)
def test_provider_metadata_gate_checks_fixed_response_fields(tmp_path, monkeypatch, field, value):
    runtime, _, _ = fixture(tmp_path, monkeypatch, provider=False)
    from autoengineering.agents import conformance_runtime as module
    from autoengineering.agents.hosts.subscription_worker import HOST, PORT, ROUTE

    scope = runtime.batch.root / "cases/text/sample"
    attempt = scope / "upstream/attempt"
    (attempt / "process").mkdir(mode=0o700, parents=True)
    policy = {
        "model": runtime.plan.worker.host.requested_model,
        "lease_id": runtime.configuration.lease_id,
        "credential_path": str(runtime.configuration.credential_path),
        "request_sha256": "0" * 64,
    }
    monkeypatch.setattr(
        module, "verify_subscription_attempt", lambda _: (policy, {"unit_attestation_only": True})
    )
    monkeypatch.setattr(module, "recover_command_upstream", lambda _: b"authored response bytes")
    result = {
        "status": "response_received",
        "http_status": 200,
        "request_may_have_been_sent": True,
        "scope": str(scope / "upstream"),
    }
    if field is not None:
        result[field] = value
    (attempt / "provider-result.json").write_text(json.dumps(result))
    (attempt / "provider-intent.json").write_text(
        json.dumps(
            {
                "host": HOST,
                "port": PORT,
                "path": ROUTE,
                "automatic_retries": 0,
                "lease_id": runtime.configuration.lease_id,
                "request_sha256": "0" * 64,
                "scope": str(scope / "upstream"),
            }
        )
    )
    (attempt / "process/completion.json").write_text('{"unit_attestation_only":true}')
    assert runtime._provider_evidence(scope)["verified"] is (field is None)


def test_timeout_and_cancel_probes_stop_owned_work_without_remote_stop_claim(tmp_path, monkeypatch):
    runtime, config, calls = fixture(tmp_path, monkeypatch)
    report = runtime.advance(max_new_cases=4)
    assert report["status"] == "ready"
    assert report["case_results"] == {
        "text": "passed",
        "roles": "passed",
        "timeout": "passed",
        "cancel": "passed",
    }
    assert report["host_reservations_charged"] == len(calls) == 10
    assert report["scientific_reservations_charged"] == 2 and not runtime.batch.replay().pending
    from autoengineering.campaign.artifacts import read_bytes

    for case_id in ("timeout", "cancel"):
        proof = json.loads(
            read_bytes(runtime.batch.root, runtime.batch.replay().finished[case_id].evidence[0])
        )
        assert proof["remote_computation_stopped"] == "unknown"
        assert proof["usage"] == {} and proof["resolved_model"] is None
    before = snapshot(runtime.batch.root)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    assert (
        reopened.advance(max_new_cases=0) == report
        and len(calls) == 10
        and snapshot(runtime.batch.root) == before
    )


def malformed_fixture(tmp_path, monkeypatch, *, provider=True):
    """Author zero-work prefix verdicts to isolate the last handler, not conformance."""
    from autoengineering.agents.store import WorkerStore

    runtime, config, calls = fixture(tmp_path, monkeypatch, provider=provider)
    role_root = runtime.batch.root / "cases/roles/worker"
    role_root.parent.mkdir(mode=0o700, parents=True)
    worker = WorkerStore.create(role_root, runtime.plan.worker)
    for case in runtime.plan.batch.cases[:-1]:
        runtime.batch.start_case(case.id, case.configuration_digest)
        runtime.batch.finish_case(
            case.id,
            "passed",
            (
                runtime.batch.evidence(
                    {
                        "unit_attestation_only": True,
                        "worker_head": worker.replay().events[-1].digest,
                    }
                ),
            ),
        )
    return runtime, config, calls


def test_malformed_payload_is_preserved_then_repaired_without_science(tmp_path, monkeypatch):
    from autoengineering.agents.store import WorkerStore
    from autoengineering.campaign.artifacts import read_bytes
    from autoengineering.agents.conformance_runtime import MALFORMED_OUTPUT

    runtime, config, calls = malformed_fixture(tmp_path, monkeypatch)
    report = runtime.advance()
    assert report["status"] == "completed" and not report["live_conformance_complete"]
    proof = report["case_verdicts"]["malformed"]
    assert proof["passed"] and proof["intended_rejection_exercised"] and proof["repair_validated"]
    assert proof["host_invocations"] == len(calls) == 2 and proof["repairs_used"] == 1
    assert proof["scientific_actions"] == proof["scientific_starts"] == 0
    worker = WorkerStore(runtime.batch.root / "cases/malformed/worker")
    first, second = worker.replay().invocations.values()
    assert first.state == "invalid_output" and first.normalized_output is None
    assert json.loads(read_bytes(worker.root, first.final_response)) == MALFORMED_OUTPUT
    failure = read_bytes(worker.root, first.parse_failure).decode()
    initial_prompt = read_bytes(worker.root, first.prompt).decode()
    prompt = read_bytes(worker.root, second.prompt).decode()
    initial_context = json.loads(initial_prompt[initial_prompt.index('{"approved_evidence"') :])
    repaired_context = json.loads(prompt[prompt.index('{"approved_evidence"') :])
    assert initial_context["output_contract"] == {
        "version": "initial-malformed-probe-1.0",
        "expected_inner": MALFORMED_OUTPUT,
    }
    assert "Role template" not in initial_prompt
    assert "Return one JSON handoff object" not in initial_prompt
    from autoengineering.agents.output_contract import VERSION as OUTPUT_CONTRACT_VERSION

    assert repaired_context["output_contract"]["version"] == OUTPUT_CONTRACT_VERSION
    assert repaired_context["repair"] == failure
    from autoengineering.agents.conformance_runtime import MalformedProbeHost

    probe_host = MalformedProbeHost(config, runtime.batch, "malformed")
    task = worker.replay().tasks[first.task_id]
    with pytest.raises(ValueError, match="fixed diagnostic task"):
        probe_host.prepare_prompt(replace(task, id="ordinary-worker-task"), initial_prompt)
    assert json.loads(failure)["error"] in prompt.replace('\\"', '"')
    assert first.id != second.id and first.launch_nonce != second.launch_nonce
    before = snapshot(runtime.batch.root)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    assert reopened.advance() == report and len(calls) == 2
    assert snapshot(runtime.batch.root) == before
    (worker.root / first.parse_failure.path).write_bytes(b"changed failure")
    with pytest.raises(ValueError):
        reopened.report()


@pytest.mark.parametrize("problem", ["missing_provider", "wrong_payload", "valid_first"])
def test_malformed_unexercised_rejection_does_not_spend_repair(tmp_path, monkeypatch, problem):
    from autoengineering.agents.conformance_runtime import MALFORMED_OUTPUT

    runtime, _, calls = malformed_fixture(
        tmp_path, monkeypatch, provider=problem != "missing_provider"
    )
    if problem == "wrong_payload":
        monkeypatch.setitem(MALFORMED_OUTPUT, "conformance_probe", "changed expectation")
        # The responder captures this object too, so change only its expected payload at verdict.
        original = runtime._provider_evidence

        def proof(scope):
            MALFORMED_OUTPUT["conformance_probe"] = "different from saved output"
            return original(scope)

        monkeypatch.setattr(runtime, "_provider_evidence", proof)
    elif problem == "valid_first":
        original = BatchCodexHost._upstream

        def route(self, *args):
            callback = original(self, *args)

            def valid(raw):
                request = json.loads(raw)
                prompt = request["input"][0]["content"][0]["text"]
                marker = prompt.index('{"approved_evidence"')
                context = json.loads(prompt[marker:])
                context["repair"] = "authored valid first output"
                request["input"][0]["content"][0]["text"] = prompt[:marker] + canonical_json(
                    context
                )
                return callback(canonical_json(request).encode())

            return valid

        monkeypatch.setattr(BatchCodexHost, "_upstream", route)
    report = runtime.advance()
    assert report["status"] == "failed" and report["case_results"]["malformed"] == "failed"
    assert report["host_reservations_charged"] == len(calls) == 1
    assert report["scientific_reservations_charged"] == 0


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_malformed_verdict_ack_loss_recovers_without_new_invocations(tmp_path, monkeypatch, stage):
    runtime, config, calls = malformed_fixture(tmp_path, monkeypatch)

    def fault(point):
        from autoengineering.agents.store import WorkerStore

        worker = runtime.batch.root / "cases/malformed/worker"
        clients = list(WorkerStore(worker).replay().invocations.values()) if worker.exists() else []
        if (
            point == stage
            and len(runtime.batch.replay().observations) == 2
            and clients[-1].state == "completed"
        ):
            raise RuntimeError("authored verdict acknowledgment loss")

    runtime.batch.fault = fault
    with pytest.raises(RuntimeError, match="acknowledgment"):
        runtime.advance()
    assert len(calls) == 2
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    assert reopened.advance()["case_results"]["malformed"] == "passed"
    assert len(calls) == 2


def test_malformed_repair_failure_stops_at_two_calls_across_reopen(tmp_path, monkeypatch):
    runtime, config, calls = malformed_fixture(tmp_path, monkeypatch)
    original = BatchCodexHost._upstream

    def route(self, *args):
        callback = original(self, *args)

        def still_invalid(raw):
            request = json.loads(raw)
            prompt = request["input"][0]["content"][0]["text"]
            marker = prompt.index('{"approved_evidence"')
            context = json.loads(prompt[marker:])
            context["repair"] = None
            request["input"][0]["content"][0]["text"] = prompt[:marker] + canonical_json(context)
            return callback(canonical_json(request).encode())

        return still_invalid

    monkeypatch.setattr(BatchCodexHost, "_upstream", route)
    report = runtime.advance()
    proof = report["case_verdicts"]["malformed"]
    assert report["status"] == "failed" and proof["repairs_used"] == 1
    assert proof["intended_rejection_exercised"] and not proof["repair_validated"]
    assert proof["invocation_states"] == {
        "call-000001": "invalid_output",
        "call-000002": "invalid_output",
    }
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    before = snapshot(runtime.batch.root)
    assert reopened.advance() == report and len(calls) == 2
    assert snapshot(runtime.batch.root) == before
