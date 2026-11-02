"""Claude handlers with authored executable, qualification and provider proof stubs.

These fixtures prove software behavior, never real qualification or provider work.
"""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time

from click.testing import CliRunner
import pytest

from autoengineering.agents.batch_native import BatchClaudeHost
from autoengineering.agents.conformance import prepare_conformance
from autoengineering.agents.conformance_runtime import ConformanceRuntime, MALFORMED_OUTPUT
from autoengineering.agents.hosts import claude_host
from autoengineering.agents.hosts.brokered_host import WIRE_PREFIX
from autoengineering.agents.hosts.codex_brokered import WrappedCommand
from autoengineering.agents.hosts.scripted import supplied_reply
from autoengineering.agents.records import RoleHandoff, NextStep, TaskAssignment
from autoengineering.campaign.serialization import canonical_json, unique_json
from autoengineering.campaign.store import durable_write
from autoengineering.cli import cli
from test_agent_claude_conformance import authored
from test_agent_claude_brokered import PROMPT, MODEL
from test_agent_conformance import snapshot


def fixture(tmp_path, monkeypatch, *, provider=True):
    root, worker, config, calls = authored(tmp_path, monkeypatch)
    profile = config.build(worker)._verify()
    path = Path(profile.inventory.executable)
    path.write_text(
        path.read_text().replace(
            f"assert prompt=={PROMPT!r}", f"assert prompt.startswith({WIRE_PREFIX!r})"
        )
    )
    inventory = replace(profile.inventory, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    profile = replace(profile, inventory=inventory)
    monkeypatch.setattr(claude_host, "verify_claude_profile", lambda *_a, **_k: profile)

    def wrap(self, command, endpoint, *_args):
        policy = endpoint.directory.parent / "authored-policy.txt"
        durable_write(policy, b"authored identity wrapper; no OS qualification")
        return WrappedCommand(command, policy)

    def upstream(self, scope, roots, deadline, cancelled, profile):
        def call(raw):
            calls.append(raw)
            prompt = unique_json(raw.decode())["messages"][0]["content"][0]["text"]
            if self.case_id in ("timeout", "cancel"):
                marker = scope / "upstream/attempt/provider-intent.json"
                marker.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                marker.write_text('{"unit_attestation_only":true}')
                while time.monotonic() < deadline + 0.1 and not cancelled():
                    time.sleep(0.005)
                raise ValueError("authored held response ended")
            if self.case_id == "text":
                inner = '{"ack":"conformance"}'
            else:
                context = unique_json(prompt[prompt.index('{"approved_evidence"') :])
                task = TaskAssignment.from_dict(context["task"])
                if self.case_id != "malformed":
                    inner = supplied_reply(task, prompt, context["invocation_id"]).raw_output
                elif context["repair"] is None:
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
            return canonical_json(
                {
                    "id": "msg_conformance_fixture",
                    "type": "message",
                    "role": "assistant",
                    "model": MODEL,
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {"input_tokens": 7, "output_tokens": 10},
                    "content": [{"type": "text", "text": canonical_json({"handoff_json": inner})}],
                }
            ).encode()

        return call

    monkeypatch.setattr(BatchClaudeHost, "_wrap", wrap)
    monkeypatch.setattr(BatchClaudeHost, "_upstream", upstream)
    plan = prepare_conformance(
        worker, root / "campaign", config, tmp_path / "proposal", tmp_path / "runtime"
    )
    runtime = ConformanceRuntime.create(
        tmp_path / "proposal", expected_digest=plan.digest, configuration=config
    )
    if provider:
        monkeypatch.setattr(
            ConformanceRuntime,
            "_provider_evidence",
            lambda self, *_: {
                "verified": True,
                "unit_attestation_only": True,
                "evidence": self.batch.evidence({"unit_attestation_only": True}).to_dict(),
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


def test_claude_prefix_roles_timeout_and_cancel_replay_without_new_calls(tmp_path, monkeypatch):
    runtime, config, calls = fixture(tmp_path, monkeypatch)
    report = runtime.advance(max_new_cases=4)
    assert report["case_results"] == dict.fromkeys(("text", "roles", "timeout", "cancel"), "passed")
    assert report["status"] == "ready" and not report["live_conformance_complete"]
    assert report["missing_execution_handlers"] == []
    assert report["host_reservations_charged"] == len(calls) == 10
    assert report["scientific_reservations_charged"] == 2
    assert report["case_verdicts"]["roles"]["scientific_evidence"]["objective_value"] == 0
    assert report["case_verdicts"]["timeout"]["remote_computation_stopped"] == "unknown"
    assert report["case_verdicts"]["text"]["usage"]["total_tokens"] is None
    before = snapshot(runtime.batch.root)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    assert reopened.advance(max_new_cases=0) == report and len(calls) == 10
    assert snapshot(runtime.batch.root) == before
    status = CliRunner().invoke(
        cli,
        [
            "agents",
            "conformance-status",
            str(runtime.batch.root),
            "--expected-digest",
            runtime.batch.digest,
        ],
    )
    assert status.exit_code == 0, status.output
    assert json.loads(status.stdout) == report
    assert snapshot(runtime.batch.root) == before and len(calls) == 10


def test_authored_claude_response_cannot_pass_actual_provider_gate(tmp_path, monkeypatch):
    runtime, _, calls = fixture(tmp_path, monkeypatch, provider=False)
    report = runtime.advance()
    assert report["status"] == "failed" and report["case_results"] == {"text": "failed"}
    assert not report["case_verdicts"]["text"]["provider"]["verified"]
    assert len(calls) == 1 and report["scientific_reservations_charged"] == 0
    before = snapshot(runtime.batch.root)
    assert runtime.advance() == report and len(calls) == 1
    assert snapshot(runtime.batch.root) == before


@pytest.mark.parametrize("stage", ["before_event_commit", "after_event_commit"])
def test_claude_saved_text_verdict_recovers_without_relaunch(tmp_path, monkeypatch, stage):
    runtime, config, calls = fixture(tmp_path, monkeypatch)

    def fault(point):
        if point == stage and runtime.batch.replay().observations:
            raise RuntimeError("authored lost verdict acknowledgement")

    runtime.batch.fault = fault
    with pytest.raises(RuntimeError, match="acknowledgement"):
        runtime.advance(max_new_cases=1)
    reopened = ConformanceRuntime.open(
        runtime.preparation,
        expected_digest=runtime.preparation_digest,
        configuration=config,
        runtime_digest=runtime.batch.digest,
    )
    report = reopened.advance(max_new_cases=1)
    assert report["case_results"] == {"text": "passed"} and len(calls) == 1


def test_claude_malformed_handler_rejects_then_repairs_with_no_science(tmp_path, monkeypatch):
    runtime, _, calls = fixture(tmp_path, monkeypatch)
    runtime.advance(max_new_cases=4)
    # Explicit unit-only owner verdict allows isolated testing of the later
    # malformed handler. It supplies no owner-loss implementation or proof.
    owner = next(c for c in runtime.plan.batch.cases if c.id == "owner_loss")
    runtime.batch.start_case(owner.id, owner.configuration_digest)
    runtime.batch.finish_case(
        owner.id,
        "passed",
        (
            runtime.batch.evidence(
                {
                    "kind": "owner_loss",
                    "passed": True,
                    "ownership": {"verified": True, "unit_attestation_only": True},
                }
            ),
        ),
    )
    report = runtime.advance()
    proof = report["case_verdicts"]["malformed"]
    assert proof["passed"] and proof["intended_rejection_exercised"] and proof["repair_validated"]
    assert proof["host_invocations"] == 2 and proof["repairs_used"] == 1
    assert proof["scientific_actions"] == proof["scientific_starts"] == 0
    assert len(calls) == 12
    assert report["status"] == "completed" and not report["live_conformance_complete"]
    assert report["missing_execution_handlers"] == []
    before = snapshot(runtime.batch.root)
    assert runtime.advance() == report and len(calls) == 12
    assert snapshot(runtime.batch.root) == before
