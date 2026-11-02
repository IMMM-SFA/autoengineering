"""Shared conditional identity and native framework activation checks."""
import pytest

from autoengineering.integrations.replay import Observation
from autoengineering.optimization.space import (
    CategoricalParameter, ContinuousParameter, SearchSpace,
)
from examples.interoperability.optimizer_comparison.branches import BranchMapping
from test_integration_contracts import DIGEST


def mapping():
    space = SearchSpace((
        CategoricalParameter("family", ("linear", "quadratic")),
        ContinuousParameter("linear_curvature", 0., 1., active_when={"family": ("linear",)}),
        ContinuousParameter("quadratic_slope", 0., 1., active_when={"family": ("quadratic",)}),
    ))
    return BranchMapping(space, {"linear_curvature": 0., "quadratic_slope": 0.})


def test_defaults_and_roundtrip():
    branch = mapping()
    active = {"family": "linear", "linear_curvature": .5}
    expanded = {**active, "quadratic_slope": 0.}
    assert branch.canonical(active) == expanded
    assert branch.scientific(expanded) == active
    assert branch.configuration_digest(active) == branch.configuration_digest(expanded)
    with pytest.raises(ValueError, match="noncanonical"):
        branch.scientific({**expanded, "quadratic_slope": .3})
    with pytest.raises(ValueError):
        BranchMapping(branch.space, {})


@pytest.mark.parametrize("framework", ["optuna", "ax"])
def test_real_conditional_activation(framework):
    pytest.importorskip(framework)
    if framework == "optuna":
        from examples.interoperability.optimizer_comparison.optuna_replay import OptunaReplayPolicy
        cls = OptunaReplayPolicy
    else:
        from examples.interoperability.optimizer_comparison.ax_replay import AxReplayPolicy
        cls = AxReplayPolicy
    branch = mapping()
    policy = cls(branch.space, seed=2, direction="maximize")
    for _ in range(4):
        proposal = policy.ask()
        config = proposal.configuration
        assert len(config) == 2  # Framework never samples the inactive decision.
        assert branch.scientific(branch.canonical(config)) == config
        objective = config["linear_curvature" if config["family"] == "linear"
                           else "quadratic_slope"]
        policy.tell(proposal, Observation(DIGEST, "success", True, objective))


def test_sobol_projection_uses_selector_not_random_activity():
    from examples.interoperability.optimizer_comparison.branches import project_sobol
    from examples.interoperability.optimizer_comparison.cases import case

    branch = case("conditional")
    # Deliberately conflicting random activity entries must be projected from
    # the categorical selector, never passed to canonical decode as metadata.
    config = project_sobol(branch.space, [.2, .3, 0., .4, 0., .7, 1.])
    assert config == {"x": .2, "y": .3, "family": "linear", "linear_curvature": .4}
    branch.space.encode(config)
