"""Crash recovery without physical execution or duplicate framework observations."""
from dataclasses import replace

import pytest

from autoengineering.integrations.replay import (
    Observation, Proposal, ReconciliationRequired, ReplayJournal,
)
from test_integration_contracts import DIGEST, spec


class Policy:
    def __init__(self):
        self.next = 0
        self.told = []

    def ask(self):
        self.next += 1
        return Proposal(str(self.next), {"x": self.next / 10})

    def tell(self, proposal, observation):
        assert proposal.external_id not in self.told
        self.told.append(proposal.external_id)


def journal(tmp_path):
    tmp_path.chmod(0o700)
    return ReplayJournal(tmp_path, spec())


def outcome():
    return Observation(DIGEST, "success", True, 0.25)


@pytest.mark.parametrize("phase", ["ask_intent", "proposal", "tell_intent", "synchronized"])
def test_crash_after_every_commit(tmp_path, monkeypatch, phase):
    store = journal(tmp_path)
    append = store._append

    def crash(*args, **kwargs):
        rows = append(*args, **kwargs)
        if rows[-1].phase == phase:
            raise RuntimeError("injected crash")
        return rows

    with monkeypatch.context() as patch:
        patch.setattr(store, "_append", crash)
        with pytest.raises(RuntimeError, match="injected"):
            store.propose("action1", DIGEST, Policy)
            store.observe("action1", outcome(), Policy, committed_result=lambda *a: True)
    reopened = ReplayJournal(tmp_path, spec())
    assert reopened.propose("action1", DIGEST, Policy) == Proposal("1", {"x": .1})
    reopened.observe("action1", outcome(), Policy, committed_result=lambda *a: True)
    saved = reopened.read()
    reopened.observe("action1", outcome(), Policy, committed_result=lambda *a: True)
    assert reopened.read() == saved
    assert len(saved) == 4
    assert reopened.propose("action2", "b" * 64, Policy).external_id == "2"


def test_uncommitted_or_conflicting_result_fails(tmp_path):
    store = journal(tmp_path)
    store.propose("action1", DIGEST, Policy)
    with pytest.raises(ReconciliationRequired, match="not committed"):
        store.observe("action1", outcome(), Policy, committed_result=lambda *a: False)
    store.observe("action1", outcome(), Policy, committed_result=lambda *a: True)
    with pytest.raises(ReconciliationRequired, match="conflicting"):
        store.observe("action1", replace(outcome(), objective=5), Policy,
                      committed_result=lambda *a: True)


def test_replay_drift_and_corruption_fail_closed(tmp_path):
    store = journal(tmp_path)
    store.propose("action1", DIGEST, Policy)

    class Drift(Policy):
        def ask(self):
            return Proposal("1", {"x": .9})

    with pytest.raises(ReconciliationRequired, match="replay differs"):
        store.propose("action1", DIGEST, Drift)
    path = tmp_path / "transition-00000002.json"
    path.write_text(path.read_text().replace('"previous_digest":"', '"previous_digest":"b'))
    with pytest.raises(ValueError):
        store.propose("action1", DIGEST, Policy)


def test_only_one_outstanding_action(tmp_path):
    store = journal(tmp_path)
    store.propose("action1", DIGEST, Policy)
    with pytest.raises(ReconciliationRequired, match="outstanding"):
        store.propose("action2", DIGEST, Policy)
    with pytest.raises(ReconciliationRequired, match="prefix changed"):
        store.propose("action1", "b" * 64, Policy)


@pytest.mark.parametrize("status", [
    "scientific_infeasible", "model_failure", "timeout", "infrastructure_failure",
])
def test_no_invented_failure_objective(status):
    with pytest.raises(ValueError):
        Observation(DIGEST, status, False, 1e9)
    assert Observation(DIGEST, status, False, None).objective is None
