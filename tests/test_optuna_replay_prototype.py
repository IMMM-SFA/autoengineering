"""Pinned real Optuna trajectory recovery, not an optimizer comparison."""
import pytest

from autoengineering.integrations.replay import Observation, ReplayJournal
from autoengineering.optimization.space import (
    CategoricalParameter, ContinuousParameter, IntegerParameter, SearchSpace,
)
from test_integration_contracts import DIGEST, spec


def test_real_optuna_fresh_resume_trajectory(tmp_path):
    optuna = pytest.importorskip("optuna")
    if optuna.__version__ != "4.5.0":
        pytest.skip("prototype requires its pinned environment")
    from examples.interoperability.optimizer_comparison.optuna_replay import OptunaReplayPolicy

    optuna.logging.set_verbosity(optuna.logging.ERROR)
    space = SearchSpace((ContinuousParameter("x", 0., 1.), IntegerParameter("n", 1, 3),
                         CategoricalParameter("family", ("a", "b"))))
    def factory():
        return OptunaReplayPolicy(space, seed=3, direction="minimize")
    expected = factory()
    tmp_path.chmod(0o700)
    for index in range(7):
        journal = ReplayJournal(tmp_path, spec())
        proposal = journal.propose(f"action{index}", DIGEST, factory)
        assert proposal == expected.ask()
        assert type(proposal.configuration["n"]) is int
        if index == 2:
            observation = Observation(DIGEST, "model_failure", False, None)
        else:
            observation = Observation(DIGEST, "success", True, proposal.configuration["x"] ** 2)
        expected.tell(proposal, observation)
        journal.observe(f"action{index}", observation, factory, committed_result=lambda *a: True)
        journal.observe(f"action{index}", observation, factory, committed_result=lambda *a: True)
    assert len(journal.read()) == 28
