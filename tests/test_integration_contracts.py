"""Integration identity and synchronization evidence boundaries."""

from dataclasses import replace

import pytest

from autoengineering.campaign.records import ArtifactRef
from autoengineering.integrations import ExternalTrialLink, IntegrationReceipt, IntegrationSpec

DIGEST = "a" * 64


def spec():
    return IntegrationSpec(
        1, "fixture", "1.0", "fixture-policy", "policy", DIGEST, DIGEST, DIGEST,
        ["serial"], 0, "json-v1",
    )


def artifact(path="checkpoint.json"):
    return ArtifactRef(path, DIGEST, 2, "application/json", "fixture", {})


def link():
    return ExternalTrialLink(
        1, spec().digest, "campaign", "study", "action", "experiment", None,
        None, (), None, DIGEST, None, "ask_intent",
    )


def test_identity_roundtrip_and_detachment():
    capabilities = ["serial"]
    value = replace(spec(), capabilities=capabilities)
    capabilities.append("parallel")
    assert value.capabilities == ("serial",)
    assert IntegrationSpec.from_json(value.to_json()) == value
    for changes in (
        {"framework_version": "2.0"}, {"seed": 1},
        {"configuration_digest": "b" * 64}, {"environment_digest": "b" * 64},
        {"checkpoint_format": "json-v2"},
    ):
        with pytest.raises(ValueError, match="identity changed"):
            value.require_compatible(replace(value, **changes))


@pytest.mark.parametrize("changes", [
    {"seed": True}, {"seed": -1}, {"configuration_digest": "bad"},
    {"capabilities": ["serial", "serial"]}, {"schema_version": 2},
    {"framework": "../framework"}, {"seed": float("inf")},
])
def test_invalid_identity(changes):
    with pytest.raises(ValueError):
        replace(spec(), **changes)


def test_strict_json():
    with pytest.raises(ValueError, match="duplicate"):
        IntegrationSpec.from_json('{"seed":0,"seed":1}')
    with pytest.raises(ValueError, match="unknown or missing"):
        IntegrationSpec.from_dict({**spec().to_dict(), "secret": "value"})
    with pytest.raises(ValueError):
        IntegrationSpec.from_json(spec().to_json().replace('"seed":0', '"seed":NaN'))


def test_trial_evidence_states():
    intent = link()
    proposal = replace(
        intent, synchronization="proposal_saved", external_trial_id="trial-1",
        proposal_digest=DIGEST, checkpoint=artifact(),
    )
    told = replace(
        proposal, synchronization="tell_intent", observation_digest=DIGEST,
        attempt_ids=["attempt-1"],
    )
    synced = replace(told, synchronization="synchronized")
    for value in (intent, proposal, told, synced):
        assert ExternalTrialLink.from_json(value.to_json()) == value
    for changes in (
        {"checkpoint": None}, {"observation_digest": None},
        {"attempt_ids": []}, {"proposal_digest": None},
        {"attempt_ids": ["attempt-1", "attempt-1"]},
    ):
        with pytest.raises(ValueError):
            replace(synced, **changes)
    with pytest.raises(ValueError):
        replace(intent, observation_digest=DIGEST)


def test_evidence_paths_and_qualification():
    for path in ("../checkpoint", "/tmp/checkpoint", "dir/../checkpoint", "dir\\checkpoint"):
        with pytest.raises(ValueError):
            artifact(path)
    receipt = IntegrationReceipt(
        1, spec().digest, "test-platform", [artifact("direct.json")], artifact("tolerances.json"),
        ["parity"], ["fixture only"], "verified",
    )
    assert IntegrationReceipt.from_json(receipt.to_json()) == receipt
    with pytest.raises(ValueError):
        replace(receipt, direct_reference=[])
