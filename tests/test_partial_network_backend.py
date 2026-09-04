"""Contracts for partial-observability function-network optimization."""

# waterology: allow-unseeded - stochastic fixtures use backend-derived recorded seeds.

from dataclasses import replace
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from autoengineering.optimization import (
    BudgetSpec,
    CategoricalParameter,
    ConstraintSpec,
    ContinuousParameter,
    EvaluationAction,
    EvaluationScope,
    FunctionNetworkEvaluator,
    FunctionNetworkSpec,
    LedgerBackedFunctionNetworkEvaluator,
    MarginalValueExhausted,
    NoiseSpec,
    ObjectiveSpec,
    ObservationLedger,
    OptimizationStudy,
    SearchSpace,
    StudySpec,
)
from autoengineering.optimization.function_network_evaluator import (
    reconstruct_component_training_tables,
)
from autoengineering.research.runner import EvaluationContext
from autoengineering.system.graph import System

if importlib.util.find_spec("botorch") is not None:
    import torch

    from autoengineering.optimization.partial_network_backend import (
        _ScoredCandidate,
        PartialNetworkBayesBackend,
    )
    from autoengineering.optimization.partial_network_baselines import (
        CheapestInformativePartialNetworkBackend,
        RandomPartialNetworkBackend,
    )
else:
    PartialNetworkBayesBackend = None
    CheapestInformativePartialNetworkBackend = None
    RandomPartialNetworkBackend = None


@pytest.fixture
def partial_contract():
    root = Path(__file__).resolve().parents[1] / "examples" / "function_network"
    system = System.from_yaml(root / "system.yaml")
    network = FunctionNetworkSpec.from_yaml(root / "network.yaml")
    study = StudySpec(
        name="partial-network-test",
        objective=ObjectiveSpec("utility", "maximize"),
        constraints=(ConstraintSpec("minimum_flow", ">=", 0.0),),
        budget=BudgetSpec(20.0, "second"),
        noise=NoiseSpec("deterministic", 1e-6),
        backend="function_network_partial",
        seed=37,
    )
    space = SearchSpace(
        (
            CategoricalParameter("transform.choice", ("base",)),
            ContinuousParameter("transform.gain", 0.5, 2.0),
            CategoricalParameter("score.choice", ("base",)),
            ContinuousParameter("score.offset", -2.0, 2.0),
        )
    )
    return system, network, study, space


def _runner(component, inputs):
    params = component.metadata["runnable"]["params"]
    if component.name == "transform":
        return {"flow": np.asarray(inputs["driver"]) * params["gain"]}
    flow = np.asarray(inputs["flow"])
    return {"utility_series": 10.0 - (flow - params["target"]) ** 2 + params["offset"]}


def _context(tmp_path, system):
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(mode=0o700, exist_ok=True)
    artifact_dir.chmod(0o700)
    return EvaluationContext(
        system=system,
        alternatives={
            name: {"base": system.get_component(name)} for name in ("transform", "score")
        },
        source_arrays={"source.driver": np.array([1.0, 2.0, 3.0])},
        observed={},
        outcome_functions={"placeholder": lambda _: 0.0},
        cost_unit="second",
        artifact_dir=artifact_dir,
    )


def _observed_ledger(tmp_path, contract, count=4):
    system, network, _, _ = contract
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    context = _context(tmp_path, system)
    configs = ((0.5, -2.0), (1.0, 0.0), (1.5, 2.0), (2.0, -1.0))
    for index, (gain, offset) in enumerate(configs[:count]):
        action = EvaluationAction.system(
            f"eval-{index:06d}",
            {
                "transform.choice": "base",
                "transform.gain": gain,
                "score.choice": "base",
                "score.offset": offset,
            },
            seed=index,
        )
        times = iter((float(index), float(index + 1)))
        result = FunctionNetworkEvaluator(
            network, context, runner=_runner, clock=lambda: next(times)
        ).evaluate(action)
        ledger.append(action, result)
    return ledger


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_candidate_pools_replay_and_bind_parent_lineage(tmp_path, partial_contract):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract)
    first = PartialNetworkBayesBackend(
        study, space, network, system, candidate_pool_size=8, decision_pool_size=8
    )
    second = PartialNetworkBayesBackend(
        study, space, network, system, candidate_pool_size=8, decision_pool_size=8
    )

    first_pool = first._candidate_pools(ledger)
    second_pool = second._candidate_pools(ObservationLedger(ledger.path))
    assert first_pool == second_pool
    assert len(first_pool.decisions) == 8
    assert len(first_pool.system) == 8
    assert {candidate.component for candidate in first_pool.component} == {
        "transform",
        "score",
    }
    successful_system_artifacts = {
        artifact_id
        for action, result in ledger.entries()
        if action.scope is EvaluationScope.SYSTEM
        for artifact_id in result.artifacts
    }
    assert all(
        candidate.parent_artifact_id in successful_system_artifacts
        for candidate in first_pool.component
    )
    assert all(candidate.estimated_cost >= 0.5 for candidate in first_pool.component)

    action, result = ledger.entries()[0]
    relocated = replace(
        result,
        artifacts={name: f"/other/location/{name}.npz" for name in result.artifacts},
    )
    assert first._fingerprint(((action, result),)) == first._fingerprint(((action, relocated),))


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_validation_costs_and_monotone_mixed_scope_ids(tmp_path, partial_contract):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract, count=1)
    backend = PartialNetworkBayesBackend(study, space, network, system)
    entries = ledger.entries()
    parent_id = next(iter(entries[0][1].artifacts))
    action = EvaluationAction.component(
        "eval-000001",
        "score",
        {"score.choice": "base", "score.offset": 0.5},
        parent_artifact_ids=(parent_id,),
    )
    backend.validate_action(action, entries)
    assert backend.estimated_action_cost(action, entries) == 0.5
    assert backend.minimum_action_cost(entries) == 0.5

    with pytest.raises(ValueError, match="foreign"):
        backend.validate_action(
            replace(action, config={"transform.gain": 1.0}), entries
        )
    with pytest.raises(ValueError, match="next mixed-scope"):
        backend.validate_action(replace(action, id="eval-000002"), entries)
    with pytest.raises(ValueError, match="exactly one"):
        backend.validate_action(replace(action, parent_artifact_ids=(parent_id, parent_id)), entries)


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_candidate_pool_reserves_one_observed_system_refresh(
    tmp_path, partial_contract
):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract)
    backend = PartialNetworkBayesBackend(
        replace(study, budget=BudgetSpec(5.6, "second")),
        space,
        network,
        system,
        candidate_pool_size=4,
        decision_pool_size=4,
    )

    pools = backend._candidate_pools(ledger)

    assert pools.system
    assert not pools.component
    assert backend.minimum_action_cost(ledger.entries()) == 1.5


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_minimum_cost_requires_system_after_component_streak(
    tmp_path, partial_contract
):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract)
    parent_id = next(iter(ledger.entries()[0][1].artifacts))
    ticks = iter((5.0, 5.25, 6.0, 6.25))
    evaluator = LedgerBackedFunctionNetworkEvaluator(
        network,
        _context(tmp_path, system),
        ledger,
        runner=_runner,
        clock=lambda: next(ticks),
    )
    for index, offset in enumerate((0.25, 0.75), start=4):
        action = EvaluationAction.component(
            f"eval-{index:06d}",
            "score",
            {"score.choice": "base", "score.offset": offset},
            parent_artifact_ids=(parent_id,),
            seed=index,
        )
        ledger.append(action, evaluator.evaluate(action))
    backend = PartialNetworkBayesBackend(
        study, space, network, system, max_component_streak=2
    )

    assert backend.minimum_action_cost(ledger.entries()) == 1.5


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_fit_uses_component_rows_without_summing_system_costs(
    tmp_path, partial_contract
):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract)
    parent_id = next(iter(ledger.entries()[0][1].artifacts))
    action = EvaluationAction.component(
        "eval-000004",
        "score",
        {"score.choice": "base", "score.offset": 1.75},
        parent_artifact_ids=(parent_id,),
        seed=4,
    )
    times = iter((5.0, 5.25))
    evaluator = LedgerBackedFunctionNetworkEvaluator(
        network,
        _context(tmp_path, system),
        ledger,
        runner=_runner,
        clock=lambda: next(times),
    )
    ledger.append(action, evaluator.evaluate(action))
    backend = PartialNetworkBayesBackend(study, space, network, system)
    tables = reconstruct_component_training_tables(network, system, ledger)
    prepared = backend._fit_components(tables, backend._fingerprint(ledger.entries()))

    assert prepared["transform"].row_count == 4
    assert prepared["score"].row_count == 5
    assert sum(result.cost for _, result in ledger.entries()) == 4.25
    assert backend.recommend(ledger).action_id in {f"eval-{index:06d}" for index in range(4)}


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_value_suggestion_replays_with_fantasy_diagnostics(
    tmp_path, partial_contract
):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract)
    settings = {
        "candidate_pool_size": 2,
        "decision_pool_size": 2,
        "posterior_samples": 8,
        "fantasy_samples": 2,
    }
    first = PartialNetworkBayesBackend(study, space, network, system, **settings)
    second = PartialNetworkBayesBackend(study, space, network, system, **settings)

    first_action = first.suggest(ledger)[0]
    second_action = second.suggest(ObservationLedger(ledger.path))[0]
    assert first_action == second_action
    first.validate_action(first_action, ledger.entries())
    diagnostics = first.diagnostics(ledger)
    assert diagnostics.fit_state == "fitted"
    assert diagnostics.details["fantasy_samples"] == 2
    assert diagnostics.details["candidate_scores"]
    assert any(
        record["scope"] == "component"
        for record in diagnostics.details["candidate_scores"]
    )
    assert all(
        record["estimated_cost"] > 0
        and record["monte_carlo_standard_error"] >= 0
        for record in diagnostics.details["candidate_scores"]
    )
    assert first.identity_dict()["constructor"]["fantasy_samples"] == 2
    assert first.identity_dict()["constructor"]["reserve_system_refresh_budget"] is True
    assert first.state_dict()["partial_policy"]["reserve_system_refresh_budget"] is True


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_exact_gaussian_conditioning_matches_closed_form(
    tmp_path, partial_contract
):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract)
    backend = PartialNetworkBayesBackend(
        study,
        space,
        network,
        system,
        candidate_pool_size=2,
        decision_pool_size=2,
        posterior_samples=8,
        fantasy_samples=2,
    )
    tables = reconstruct_component_training_tables(network, system, ledger)
    fingerprint = backend._fingerprint(ledger.entries())
    prepared = backend._fit_components(tables, fingerprint)
    candidate = next(
        item for item in backend._candidate_pools(ledger).component if item.component == "score"
    )
    x = backend._component_candidate_input(ledger, candidate, prepared["score"])
    model = prepared["score"].models["utility_last"]
    posterior = model.posterior(x)
    mean = float(posterior.mean.squeeze().detach())
    variance = float(posterior.variance.squeeze().detach())
    conditioned, seeds = backend._conditioned_fantasies(
        prepared, "score", x, fingerprint, candidate
    )
    draw = mean + variance**0.5 * np.random.default_rng(seeds[0]).standard_normal(2)[0]
    noise = max(study.noise.noise_floor, np.finfo(np.float64).eps) ** 2
    expected_mean = mean + variance / (variance + noise) * (draw - mean)
    expected_variance = variance - variance**2 / (variance + noise)
    actual = conditioned[0]["score"].models["utility_last"].posterior(x)

    assert torch.isclose(
        actual.mean.squeeze(), torch.tensor(expected_mean, dtype=torch.double), atol=1e-6
    )
    assert torch.isclose(
        actual.variance.squeeze(),
        torch.tensor(expected_variance, dtype=torch.double),
        atol=1e-6,
    )


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_zero_value_triggers_distinct_marginal_stop(
    tmp_path, partial_contract, monkeypatch
):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract)
    backend = PartialNetworkBayesBackend(
        study,
        space,
        network,
        system,
        candidate_pool_size=2,
        decision_pool_size=2,
        posterior_samples=8,
        fantasy_samples=2,
        minimum_value_per_cost=0.0,
    )
    candidate = backend._candidate_pools(ledger).system[0]
    monkeypatch.setattr(
        backend,
        "_score_candidates",
        lambda *args, **kwargs: (_ScoredCandidate(candidate, 0.0, 0.0, 0.0, 0.0, ()),),
    )

    with pytest.raises(MarginalValueExhausted):
        backend.suggest(ledger)
    assert backend.diagnostics(ledger).details["maximum_value_per_cost_bound"] == 0.0


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_benchmark_baselines_replay_and_keep_observed_recommendations(
    tmp_path, partial_contract
):
    system, network, study, space = partial_contract
    ledger = _observed_ledger(tmp_path, partial_contract)
    settings = {
        "candidate_pool_size": 2,
        "decision_pool_size": 2,
        "posterior_samples": 8,
        "fantasy_samples": 2,
    }
    for backend_type in (
        RandomPartialNetworkBackend,
        CheapestInformativePartialNetworkBackend,
    ):
        first = backend_type(study, space, network, system, **settings)
        second = backend_type(study, space, network, system, **settings)
        first_action = first.suggest(ledger)[0]
        second_action = second.suggest(ObservationLedger(ledger.path))[0]
        assert first_action == second_action
        first.validate_action(first_action, ledger.entries())
        assert first.recommend(ledger).action_id in {
            f"eval-{index:06d}" for index in range(4)
        }
        assert first.identity_dict()["name"] == first.name

    informative = CheapestInformativePartialNetworkBackend(
        study, space, network, system, **settings
    ).suggest(ledger)[0]
    assert informative.scope is EvaluationScope.COMPONENT


@pytest.mark.skipif(PartialNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_partial_closed_loop_executes_component_and_resumes_from_ledger(
    tmp_path, partial_contract
):
    system, network, study, space = partial_contract
    directory = tmp_path / "study"
    directory.mkdir()
    ledger = ObservationLedger(directory / "observations.jsonl")
    ticks = iter(np.arange(0.0, 20.0, 0.25))
    evaluator = LedgerBackedFunctionNetworkEvaluator(
        network,
        _context(directory, system),
        ledger,
        runner=_runner,
        clock=lambda: next(ticks),
    )
    settings = {
        "candidate_pool_size": 2,
        "decision_pool_size": 2,
        "posterior_samples": 8,
        "fantasy_samples": 2,
    }
    backend = CheapestInformativePartialNetworkBackend(
        study, space, network, system, **settings
    )
    controller = OptimizationStudy(
        study, space, backend, ledger, evaluator, directory
    )
    result = controller.run_result(max_new_evaluations=5)

    assert result.new_evaluation_count == 5
    assert [action.scope for action, _ in result.entries[:4]] == [
        EvaluationScope.SYSTEM
    ] * 4
    assert result.entries[4][0].scope is EvaluationScope.COMPONENT
    parent_id = result.entries[4][0].parent_artifact_ids[0]
    assert any(
        parent_id in observation.artifacts
        and action.scope is EvaluationScope.SYSTEM
        and observation.status.value == "success"
        for action, observation in result.entries[:4]
    )
    assert sum(observation.cost for _, observation in result.entries) == 1.25
    assert result.recommendation.action_id in {
        action.id for action, _ in result.entries[:4]
    }

    resumed = OptimizationStudy(
        study,
        space,
        CheapestInformativePartialNetworkBackend(
            study, space, network, system, **settings
        ),
        ObservationLedger(ledger.path),
        LedgerBackedFunctionNetworkEvaluator(
            network,
            _context(directory, system),
            ObservationLedger(ledger.path),
            runner=_runner,
            clock=lambda: next(ticks),
        ),
        directory,
    )
    assert resumed.recommend() == result.recommendation


def test_partial_network_optional_dependency_boundary_is_concise():
    command = [
        __import__("sys").executable,
        "-c",
        "import importlib.util\n"
        "available = importlib.util.find_spec('botorch') is not None\n"
        "try:\n import autoengineering.optimization.partial_network_backend\n"  # waterology: allow-abs-path
        "except ImportError as error:\n"  # waterology: allow-abs-path
        " assert not available and 'install autoengineering[bayes]' in str(error)\n"
        "else:\n assert available",  # waterology: allow-abs-path
    ]
    completed = __import__("subprocess").run(
        command, check=False, capture_output=True, text=True
    )
    assert completed.returncode == 0, completed.stderr
