"""Adapter/journal integration with a stubbed qualifier and authored provider.

These tests supply no real native qualification and do not authorize live use.
"""

from dataclasses import replace
import json
import time

import pytest

from autoengineering.agents.hosts import brokered_host as module
from autoengineering.agents.hosts.brokered_host import BrokeredCodexHost, WIRE_PREFIX
from autoengineering.agents.hosts.codex_brokered import WrappedCommand, inspect_brokered_codex
from autoengineering.agents.hosts.native_profile import VerifiedNativeProfile
from autoengineering.agents.identity import host_source_identity, host_environment_identity
from autoengineering.agents.permissions import POLICY_DIGEST
from autoengineering.agents.records import HostSelection
from autoengineering.agents.scheduler import SerialScheduler, template_digests
from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import durable_write, StoreError
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL, response_stream
from test_agent_brokered_codex import program
from test_agent_contracts import run_spec
from test_agent_scheduler import setup


def stream(text):
    def convert(value):
        if isinstance(value, dict):
            return {key: convert(item) for key, item in value.items()}
        if isinstance(value, list):
            return [convert(item) for item in value]
        return text if value == '{"ok":true}' else value

    return (
        "\n".join(
            "data: " + canonical_json(convert(json.loads(line[6:])))
            if line.startswith("data: ")
            else line
            for line in response_stream().decode().split("\n")
        )
    ).encode()


def worker(tmp_path, monkeypatch, *, wire=None, mode="normal"):
    tmp_path.chmod(0o700)
    inventory = inspect_brokered_codex(program(tmp_path, mode))
    # Test-only dependency substitution. No synthetic manifest is published or
    # asserted to be actual OS qualification evidence.
    profile = VerifiedNativeProfile(
        tmp_path, "0" * 64, inventory, OFFLINE_MODEL, 300, 65536, 65536, "1" * 64
    )
    monkeypatch.setattr(module, "verify_native_profile", lambda *a, **k: profile)
    host = BrokeredCodexHost(
        qualification_root=tmp_path,
        qualification_digest="0" * 64,
        credential_path=tmp_path / "never-open-auth.json",
        lease_id="unit-lease",
        model=OFFLINE_MODEL,
    )
    spec = replace(
        run_spec(),
        host=HostSelection("codex", "subscription", OFFLINE_MODEL, "2.1", "0" * 64),
        role_templates=template_digests(),
        tool_policy_digest=POLICY_DIGEST,
        source_identity=host_source_identity(),
        environment_identity=host_environment_identity(),
    )
    store, _, task, output = setup(tmp_path, spec=spec)
    requests = []

    def upstream(root, workspace, home, deadline, cancelled):
        def call(raw):
            requests.append(raw)
            return stream(
                wire if wire is not None else canonical_json({"handoff_json": output.to_json()})
            )

        return call

    def wrap(command, endpoint, *_):
        policy = endpoint.directory.parent / "unit-policy.sb"
        durable_write(policy, b"unit-test wrapper; not an OS qualification")
        return WrappedCommand(command, policy)

    monkeypatch.setattr(host, "_upstream", upstream)
    monkeypatch.setattr(host, "_wrap", wrap)
    return SerialScheduler(store, host, clock=lambda: 100), task, output, requests


def test_brokered_host_uses_persisted_wire_prompt_and_typed_broker_validation(
    tmp_path, monkeypatch
):
    scheduler, task, output, requests = worker(tmp_path, monkeypatch)
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "completed" and scheduler.handoff(result) == output
    assert len(requests) == 1 and read_bytes(scheduler.store.root, result.prompt).startswith(
        WIRE_PREFIX.encode()
    )
    assert result.resolved_model == OFFLINE_MODEL and result.usage["total_tokens"] == 2
    assert "handoff_json" in read_bytes(scheduler.store.root, result.raw_response).decode()
    assert read_bytes(scheduler.store.root, result.final_response).decode() == output.to_json()
    assert scheduler.dispatch(task, campaign_revision=3) == result and len(requests) == 1
    assert scheduler.host.cancel(result.id)


@pytest.mark.parametrize("wire", ['{"extra":true}', '{"handoff_json":"not json"}'])
def test_wire_or_inner_role_failure_is_invalid_output_not_a_scientific_action(
    tmp_path, monkeypatch, wire
):
    scheduler, task, _, requests = worker(tmp_path, monkeypatch, wire=wire)
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "invalid_output" and result.parse_failure and len(requests) == 1


def test_lost_adapter_return_recovers_without_native_or_provider_relaunch(tmp_path, monkeypatch):
    scheduler, task, output, requests = worker(tmp_path, monkeypatch)
    invoke = scheduler.host.invoke_supervised

    def lost(*args):
        invoke(*args)
        raise RuntimeError("authored final acknowledgment loss")

    monkeypatch.setattr(scheduler.host, "invoke_supervised", lost)
    pending = scheduler.dispatch(task, campaign_revision=3)
    assert pending.state == "reconciliation_required" and pending.process_receipt
    result = scheduler.recover_invocation(pending.id, campaign_revision=3)
    assert result.state == "completed" and result.resolved_model == OFFLINE_MODEL
    assert (
        result.usage["total_tokens"] == 2
        and scheduler.handoff(result) == output
        and len(requests) == 1
    )
    assert result.recovery_receipt
    assert (
        scheduler.recover_invocation(pending.id, campaign_revision=3) == result
        and len(requests) == 1
    )


def test_changed_qualified_configuration_cannot_resume_pending_call(tmp_path, monkeypatch):
    scheduler, task, _, requests = worker(tmp_path, monkeypatch)
    invoke = scheduler.host.invoke_supervised

    def lost(*args):
        invoke(*args)
        raise RuntimeError("lost return")

    monkeypatch.setattr(scheduler.host, "invoke_supervised", lost)
    pending = scheduler.dispatch(task, campaign_revision=3)
    scheduler.host.lease_id = "changed-lease"
    with pytest.raises(StoreError, match="capability"):
        scheduler.recover_invocation(pending.id, campaign_revision=3)
    assert len(requests) == 1


def test_preparation_deadline_and_setup_failure_never_launch(tmp_path, monkeypatch):
    scheduler, task, _, requests = worker(tmp_path, monkeypatch)

    def fail(*_):
        raise ValueError("setup unavailable")

    monkeypatch.setattr(scheduler.host, "_upstream", fail)
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "host_failure" and not requests and result.process_receipt is None
    root = scheduler.store.root / "processes" / result.id
    assert not (root / "transport").exists()


def test_missing_qualification_blocks_before_any_credential_or_process_access(tmp_path):
    tmp_path.chmod(0o700)
    with pytest.raises(ValueError):
        BrokeredCodexHost(
            qualification_root=tmp_path,
            qualification_digest="0" * 64,
            credential_path=tmp_path / "never-open-auth.json",
            lease_id="lease",
            model=OFFLINE_MODEL,
        )


def test_legacy_host_selection_keeps_exact_fields_and_new_profile_requires_pin():
    old = HostSelection("fake", "none", "scripted", "1.0")
    assert set(old.to_dict()) == {"kind", "auth_mode", "requested_model", "adapter_version"}
    assert HostSelection.from_dict(old.to_dict()) == old
    with pytest.raises(ValueError, match="qualification"):
        HostSelection("codex", "subscription", OFFLINE_MODEL, "2.1")
    with pytest.raises(ValueError, match="qualification"):
        HostSelection.from_dict({**old.to_dict(), "qualification_digest": None})


def test_run_pin_cannot_change_before_first_call(tmp_path, monkeypatch):
    scheduler, task, _, requests = worker(tmp_path, monkeypatch)
    scheduler.host.pin = "1" * 64
    with pytest.raises(ValueError, match="selection"):
        scheduler.dispatch(task, campaign_revision=3)
    assert not requests and not scheduler.store.replay().invocations


def test_actual_scoped_transport_stops_at_missing_lease_before_network(tmp_path, monkeypatch):
    scheduler, task, _, requests = worker(tmp_path, monkeypatch)
    monkeypatch.delattr(scheduler.host, "_upstream")
    result = scheduler.dispatch(task, campaign_revision=3)
    assert result.state == "host_failure" and not requests and not result.usage
    attempt = scheduler.store.root / "processes" / result.id / "upstream/attempt"
    receipt = json.loads((attempt / "provider-result.json").read_text())
    assert receipt["phase"] == "preflight" and receipt["request_may_have_been_sent"] is False
    assert not (attempt / "provider-intent.json").exists()


def test_returned_callback_cannot_release_unverified_upstream_worker(tmp_path, monkeypatch):
    from autoengineering.agents.hosts.subscription import ScopedSubscriptionUpstream

    scheduler, task, _, requests = worker(tmp_path, monkeypatch)
    monkeypatch.delattr(scheduler.host, "_upstream")
    audit = ScopedSubscriptionUpstream.stop_audit
    monkeypatch.setattr(ScopedSubscriptionUpstream, "stop_audit", lambda _: {"state": "unresolved"})
    pending = scheduler.dispatch(task, campaign_revision=3)
    assert pending.state == "reconciliation_required" and not requests
    assert scheduler.host.cancel(pending.id) is False
    root = scheduler.store.root / "processes" / pending.id
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    monkeypatch.setattr(ScopedSubscriptionUpstream, "stop_audit", audit)
    recovered = scheduler.recover_invocation(pending.id, campaign_revision=3)
    assert recovered.state == "host_failure" and not recovered.usage and not requests
    proof = json.loads(read_bytes(scheduler.store.root, recovered.recovery_receipt))
    assert proof["upstream_stop"]["state"] == "verified_stopped"
    assert {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    } == before
    assert json.loads((root / "upstream-stop.json").read_text())["state"] == "unresolved"
    assert scheduler.recover_invocation(pending.id, campaign_revision=3) == recovered


def test_slow_upstream_preparation_is_in_original_deadline(tmp_path, monkeypatch):
    from autoengineering.agents.hosts.base import InvocationContext

    scheduler, task, _, requests = worker(tmp_path, monkeypatch)
    parent = tmp_path / "direct"
    parent.mkdir(mode=0o700)

    def slow(*_):
        time.sleep(0.1)
        return lambda _: pytest.fail("expired preparation cannot call upstream")

    monkeypatch.setattr(scheduler.host, "_upstream", slow)
    context = InvocationContext(
        "call-prep",
        "prep-nonce",
        parent / "call-prep",
        0.05,
        65536,
        lambda _: pytest.fail("expired launch"),
        lambda: False,
    )
    prompt = scheduler.host.prepare_prompt(task, "bounded fixture")
    result = scheduler.host.invoke_supervised(task, prompt, context)
    assert result.status == "timeout" and result.stop_verified and not requests
    assert not (context.directory / "transport").exists()
    assert scheduler.host.recover_supervised(task, prompt, context) == result
