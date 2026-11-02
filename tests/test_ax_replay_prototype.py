"""Pinned Ax public Client recovery checks without physical model execution."""
from importlib.metadata import version

import pytest

from autoengineering.integrations.replay import Observation, ReplayJournal
from autoengineering.optimization.space import ContinuousParameter, SearchSpace
from test_integration_contracts import DIGEST, spec


def test_real_ax_fresh_resume_adaptive_trajectory(tmp_path):
    pytest.importorskip("ax")
    if version("ax-platform") != "1.1.2":
        pytest.skip("prototype requires its pinned environment")
    from examples.interoperability.optimizer_comparison.ax_replay import AxReplayPolicy

    space = SearchSpace((ContinuousParameter("x", 0., 1.),))

    def factory():
        return AxReplayPolicy(space, seed=3, direction="minimize")

    expected = factory()
    tmp_path.chmod(0o700)
    for index in range(6):
        journal = ReplayJournal(tmp_path, spec())
        proposal = journal.propose(f"action{index}", DIGEST, factory)
        assert proposal == expected.ask()
        observation = Observation(DIGEST, "success", True, proposal.configuration["x"] ** 2)
        expected.tell(proposal, observation)
        journal.observe(f"action{index}", observation, factory, committed_result=lambda *a: True)
    assert len(journal.read()) == 24
