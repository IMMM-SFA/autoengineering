"""Corrupted partial owner-loss evidence must not become a stopped failure."""

import pytest

from test_agent_claude_conformance_owner import owner_fixture


@pytest.mark.parametrize(
    "target",
    [
        "transport/timing.json",
        "transport/client/completion.json",
        "transport/stops/000001.json",
        "transport/auth/capability",
        "upstream/attempt/request.bin",
        "upstream/attempt/upstream.json",
    ],
)
def test_partial_or_changed_claude_evidence_cannot_use_abandoned_recovery(
    tmp_path, monkeypatch, target
):
    runtime, _, calls = owner_fixture(tmp_path, monkeypatch)
    report = runtime.advance(max_new_cases=1)
    assert report["case_verdicts"]["owner_loss"]["passed"]
    scope = runtime.batch.root / "cases/owner_loss/owner_loss-call"
    (scope / target).write_bytes(b"corrupt")
    with pytest.raises(ValueError):
        runtime.owner_loss()
    assert len(runtime.batch.replay().reservations) == 1 and not calls
