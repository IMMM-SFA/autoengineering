"""Provider reservation, privacy and saved-byte recovery without networking."""

from __future__ import annotations

import json

import pytest

from autoengineering.agents.hosts.response_boundary import MAX_RESPONSE_BYTES
from autoengineering.agents.hosts.text_exchange import TextExchange
from autoengineering.agents.hosts.subscription_worker import TRUSTED_INSTRUCTIONS
from autoengineering.campaign.store import WriterBusy
from examples.agent_campaign.probe_external_codex import OFFLINE_MODEL, response_stream

PROMPT = "approved role brief"
SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}}


def exchange(tmp_path, **kwargs):
    tmp_path.chmod(0o700)
    return TextExchange.create(
        tmp_path / "broker",
        invocation_id="call-one",
        requested_model=OFFLINE_MODEL,
        approved_prompt=PROMPT,
        output_schema=SCHEMA,
        **kwargs,
    )


def client(*, prompt=PROMPT):
    return json.dumps(
        {
            "model": OFFLINE_MODEL,
            "instructions": "unapproved native instructions must never reach the provider",
            "stream": True,
            "input": [
                {
                    "type": "message",
                    "role": "developer",
                    "content": [{"type": "input_text", "text": "unapproved ambient canary"}],
                },
                {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                },
            ],
            "tools": [{"type": "function", "name": "exec_command"}],
            "client_metadata": {"private": "unapproved metadata"},
            "text": {"format": {"schema": {"changed": "unapproved schema"}}},
            "unknown": "unapproved field",
        }
    ).encode()


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_only_approved_prompt_and_schema_reach_the_single_provider_request(tmp_path):
    broker = exchange(tmp_path)
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream()

    result = broker.execute(client(), upstream)
    assert result.status == "completed" and not result.replayed
    assert result.provider_requests_reserved == 1
    assert result.response.text == '{"ok":true}'
    request = json.loads(calls[0])
    assert request["input"] == [
        {"type": "message", "role": "user", "content": [{"type": "input_text", "text": PROMPT}]}
    ]
    assert request["tools"] == [] and request["tool_choice"] == "none"
    assert request["instructions"] == TRUSTED_INSTRUCTIONS
    assert request["store"] is False
    assert request["text"]["format"]["schema"] == SCHEMA
    assert b"unapproved" not in calls[0]
    before = snapshot(broker.root)
    replay = broker.execute(client(), upstream)
    assert replay.replayed and replay.response == result.response
    assert snapshot(broker.root) == before and len(calls) == 1
    assert TextExchange(broker.root).recover().response == result.response
    with pytest.raises(ValueError, match="conflicting client request"):
        broker.execute(client(prompt="different"), upstream)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "stage,count,reserved,status",
    [
        ("request_saved", 0, 0, "reconciliation_required"),
        ("dispatch_committed", 0, 1, "reconciliation_required"),
        ("raw_saved", 1, 1, "completed"),
        ("before_outcome_commit", 1, 1, "completed"),
    ],
)
def test_every_saved_gap_recovers_without_another_provider_call(
    tmp_path, stage, count, reserved, status
):
    def fault(where):
        if where == stage:
            raise OSError("injected acknowledgment loss")

    broker = exchange(tmp_path, fault=fault)
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream()

    with pytest.raises(OSError, match="acknowledgment"):
        broker.execute(client(), upstream)
    recovered = TextExchange(broker.root)
    for result in (recovered.recover(), recovered.execute(client(), upstream)):
        assert result.status == status
        assert result.provider_requests_reserved == reserved
        assert result.replayed
    assert len(calls) == count


def test_failed_transport_retains_unknown_outcome_and_never_saves_credentials(tmp_path):
    broker = exchange(tmp_path)
    calls = []

    def failed(raw):
        calls.append(raw)
        raise RuntimeError("credential-canary-do-not-record")

    result = broker.execute(client(), failed)
    assert result.status == "reconciliation_required" and result.response is None
    assert result.provider_requests_reserved == 1
    assert "credential-canary" not in repr(snapshot(broker.root))
    assert broker.execute(client(), failed).status == "reconciliation_required"
    assert len(calls) == 1


def test_tool_response_is_saved_but_never_delivered_and_replays_rejection(tmp_path):
    broker = exchange(tmp_path)
    raw = response_stream(tool_command="touch forbidden")
    result = broker.execute(client(), lambda _: raw)
    assert result.status == "rejected" and result.response is None
    assert result.reason == "forbidden_response_item"
    assert list(broker.root.glob("artifacts/*/upstream-response.sse"))[0].read_bytes() == raw
    assert not list(broker.root.glob("artifacts/*/client-response.sse"))
    assert broker.recover().status == "rejected"


def test_wrong_prompt_is_preserved_and_rejected_before_reservation(tmp_path):
    broker = exchange(tmp_path)
    calls = []
    result = broker.execute(client(prompt="other task"), lambda raw: calls.append(raw))
    assert result.status == "rejected" and result.provider_requests_reserved == 0
    assert not calls and not (broker.root / "dispatch.json").exists()
    assert list(broker.root.glob("artifacts/*/client-request.json"))
    assert broker.recover().status == "rejected"


def test_saved_bytes_and_outcomes_are_verified_on_recovery(tmp_path):
    broker = exchange(tmp_path)
    broker.execute(client(), lambda _: response_stream())
    path = next(broker.root.glob("artifacts/*/upstream-response.sse"))
    raw = path.read_bytes()
    path.write_bytes(raw.replace(b'"ok"', b'"no"'))
    # Same-size corruption still fails the digest check.
    if path.read_bytes() == raw:
        path.write_bytes(b"x" + raw[1:])
    with pytest.raises(ValueError, match="digest/size"):
        broker.recover()


def test_oversized_response_retains_bounded_prefix_and_no_success(tmp_path):
    broker = exchange(tmp_path)
    result = broker.execute(client(), lambda _: b"x" * (MAX_RESPONSE_BYTES + 100))
    assert result.status == "rejected" and result.response is None
    prefix = next(broker.root.glob("artifacts/*/upstream-overflow.bin"))
    assert prefix.stat().st_size == MAX_RESPONSE_BYTES
    assert (
        json.loads((broker.root / "overflow.json").read_text())["observed_bytes"]
        == MAX_RESPONSE_BYTES + 100
    )
    assert broker.recover().status == "rejected"


def test_policy_copy_cannot_change_the_frozen_exchange_and_lost_intent_is_not_zero_work(tmp_path):
    broker = exchange(tmp_path)
    copy = broker.manifest
    copy["approved_prompt"] = "other"
    copy["output_schema"]["properties"].clear()
    assert broker.manifest["approved_prompt"] == PROMPT
    assert broker.manifest["output_schema"] == SCHEMA
    broker.execute(client(), lambda _: response_stream())
    (broker.root / "dispatch.json").unlink()
    with pytest.raises(ValueError, match="dispatch evidence is missing"):
        broker.recover()


def test_competing_owner_cannot_recover_or_dispatch_while_transport_is_active(tmp_path):
    broker = exchange(tmp_path)
    competing = TextExchange(broker.root)
    calls = []

    def upstream(raw):
        calls.append(raw)
        with pytest.raises(WriterBusy):
            competing.execute(client(), lambda _: pytest.fail("duplicate upstream call"))
        with pytest.raises(WriterBusy):
            competing.recover()
        return response_stream()

    assert broker.execute(client(), upstream).status == "completed"
    assert len(calls) == 1


def test_changed_source_and_corrupt_outcome_fail_before_any_replacement_call(tmp_path, monkeypatch):
    broker = exchange(tmp_path)
    broker.execute(client(), lambda _: response_stream())
    path = broker.root / "outcome.json"
    outcome = json.loads(path.read_text())
    outcome["usage"]["input_tokens"] = 0
    path.write_text(json.dumps(outcome))
    with pytest.raises(ValueError, match="immutable exchange outcome mismatch"):
        broker.execute(client(), lambda _: pytest.fail("replacement call"))
    monkeypatch.setattr(
        "autoengineering.agents.hosts.text_exchange.host_source_identity", lambda: "0" * 64
    )
    with pytest.raises(ValueError, match="identity changed"):
        broker.execute(client(), lambda _: pytest.fail("changed-source call"))


def test_orphan_response_artifacts_cannot_replenish_the_provider_allowance(tmp_path):
    broker = exchange(tmp_path)
    calls = []

    def upstream(raw):
        calls.append(raw)
        return response_stream()

    broker.execute(client(), upstream)
    for name in ("client.json", "dispatch.json", "outcome.json"):
        (broker.root / name).unlink()
    before = snapshot(broker.root)
    with pytest.raises(ValueError, match="client request is missing"):
        broker.execute(client(), upstream)
    with pytest.raises(ValueError, match="dispatch evidence is missing"):
        broker.recover()
    assert len(calls) == 1 and snapshot(broker.root) == before
