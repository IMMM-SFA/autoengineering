"""Contracts for full-observability function-network Bayesian optimization."""

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType

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
    NoiseSpec,
    ObjectiveSpec,
    ObservationLedger,
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

    from autoengineering.optimization.full_network_backend import (
        FullNetworkBayesBackend,
        _PreparedComponent,
    )
else:
    FullNetworkBayesBackend = None


@pytest.fixture
def full_network_contract():
    root = Path(__file__).resolve().parents[1] / "examples" / "function_network"
    system = System.from_yaml(root / "system.yaml")
    network = FunctionNetworkSpec.from_yaml(root / "network.yaml")
    study = StudySpec(
        name="full-network-test",
        objective=ObjectiveSpec("utility", "maximize"),
        constraints=(ConstraintSpec("minimum_flow", ">=", 0.0),),
        budget=BudgetSpec(20.0, "second"),
        noise=NoiseSpec("deterministic", 1e-6),
        backend="function_network_full",
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
    artifact_dir.mkdir(mode=0o700)
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
    configs = (
        (0.5, -2.0),
        (1.0, 0.0),
        (1.5, 2.0),
        (2.0, -1.0),
        (0.75, 1.0),
        (1.25, -0.5),
    )
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


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_full_network_constructor_binds_study_space_network_and_cost(
    full_network_contract,
):
    system, network, study, space = full_network_contract
    backend = FullNetworkBayesBackend(study, space, network, system)
    assert backend.name == "function_network_full"
    assert backend.order == ("source", "transform", "score")

    with pytest.raises(ValueError, match="study backend"):
        FullNetworkBayesBackend(replace(study, backend="system"), space, network, system)
    with pytest.raises(ValueError, match="objective"):
        FullNetworkBayesBackend(
            replace(study, objective=ObjectiveSpec("other", "maximize")),
            space,
            network,
            system,
        )
    with pytest.raises(ValueError, match="search space"):
        FullNetworkBayesBackend(
            study,
            SearchSpace(space.parameters[:-1]),
            network,
            system,
        )
    with pytest.raises(ValueError, match="cost units"):
        FullNetworkBayesBackend(
            replace(study, budget=BudgetSpec(20.0, "cpu_hour")),
            space,
            network,
            system,
        )
    hidden = replace(
        network.components[-1].scalar_outputs[0],
        observed_in=(EvaluationScope.COMPONENT,),
    )
    hidden_component = replace(network.components[-1], scalar_outputs=(hidden,))
    hidden_network = replace(
        network,
        components=(*network.components[:-1], hidden_component),
        objective=replace(network.objective, component="transform", scalar_output="flow_mean"),
    )
    with pytest.raises(ValueError, match="requires every scalar output"):
        FullNetworkBayesBackend(study, space, hidden_network, system)


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_full_network_reusable_seams_follow_concrete_backend_and_scope_hooks(
    full_network_contract,
):
    system, network, study, space = full_network_contract

    class MixedScopeBackend(FullNetworkBayesBackend):
        name = "function_network_partial"

        def _validate_observability_contract(self, network):
            return None

        def _validate_training_entries(self, entries):
            return None

        def _select_component_training_rows(self, component_name, tables):
            return tables[component_name]

    backend = MixedScopeBackend(
        replace(study, backend="function_network_partial"),
        space,
        network,
        system,
    )
    assert backend.name == "function_network_partial"
    assert backend._select_component_training_rows("source", {"source": (1, 2)}) == (1, 2)

    with pytest.raises(ValueError, match="function_network_partial"):
        MixedScopeBackend(study, space, network, system)


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_full_network_cold_start_returns_only_replayable_system_actions(
    tmp_path, full_network_contract
):
    system, network, study, space = full_network_contract
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    first = FullNetworkBayesBackend(study, space, network, system).suggest(ledger, 2)
    second = FullNetworkBayesBackend(study, space, network, system).suggest(ledger, 2)
    assert first == second
    assert all(action.scope is EvaluationScope.SYSTEM for action in first)
    assert all(action.suggested_by == "function_network_full:sobol" for action in first)
    assert (
        FullNetworkBayesBackend(study, space, network, system).diagnostics(ledger).fit_state
        == "not_fit_for_ledger"
    )


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_full_network_posterior_and_suggestion_replay_from_verified_tables(
    tmp_path, full_network_contract
):
    system, network, study, space = full_network_contract
    ledger = _observed_ledger(tmp_path, full_network_contract)
    config = {
        "transform.choice": "base",
        "transform.gain": 1.2,
        "score.choice": "base",
        "score.offset": 0.5,
    }
    first_backend = FullNetworkBayesBackend(
        study, space, network, system, candidate_pool_size=8, posterior_samples=32
    )
    second_backend = FullNetworkBayesBackend(
        study, space, network, system, candidate_pool_size=8, posterior_samples=32
    )
    first = first_backend.posterior_samples(ledger, config, sample_count=64)
    second = second_backend.posterior_samples(ledger, config, sample_count=64)
    assert np.array_equal(first.objective, second.objective)
    assert np.array_equal(first.constraints["minimum_flow"], second.constraints["minimum_flow"])
    assert np.all(np.isfinite(first.objective))
    assert float(np.var(first.objective)) > 1e-6

    first_actions = first_backend.suggest(ledger)
    second_actions = second_backend.suggest(ledger)
    assert first_actions == second_actions
    assert first_actions[0].scope is EvaluationScope.SYSTEM
    space.encode(first_actions[0].config)
    diagnostics = first_backend.diagnostics(ledger)
    assert diagnostics.fit_state in {"fitted", "fallback"}
    assert diagnostics.details["usable_system_observations"] == 4
    if diagnostics.fit_state == "fitted":
        assert (
            diagnostics.details["posterior_dependence"]
            == "independent_output_and_component_innovations"
        )
    assert first_backend.recommend(ledger).action_id in {
        action.id for action, _ in ledger.entries()
    }
    state = first_backend.state_dict()
    assert json.loads(json.dumps(state, sort_keys=True)) == state
    assert "SingleTaskGP" not in str(state)
    assert first_backend.identity_dict()["constructor"]["posterior_samples"] == 32


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_component_gp_uses_declared_feature_coordinates_without_second_transform(
    tmp_path, full_network_contract
):
    system, network, study, space = full_network_contract
    ledger = _observed_ledger(tmp_path, full_network_contract)
    backend = FullNetworkBayesBackend(study, space, network, system)
    tables = reconstruct_component_training_tables(network, system, ledger)
    prepared = backend._fit_components(tables, backend._fingerprint(ledger.entries()))

    fitted = [model for component in prepared.values() for model in component.models.values()]
    assert fitted
    for model in fitted:
        assert not hasattr(model, "input_transform")
        assert torch.equal(model.transform_inputs(model.train_inputs[0]), model.train_inputs[0])


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_affine_posterior_propagation_matches_closed_form(full_network_contract):
    system, network, study, space = full_network_contract
    constraint = replace(network.constraints[0], threshold=2.0)
    network = replace(network, constraints=(constraint,))
    study = replace(study, constraints=(ConstraintSpec("minimum_flow", ">=", 2.0),))
    backend = FullNetworkBayesBackend(study, space, network, system)

    class Posterior:
        def __init__(self, mean, variance):
            self.mean = mean
            self.variance = torch.full_like(mean, variance)

    class AffineModel:
        def __init__(self, multiplier, variance):
            self.multiplier = multiplier
            self.variance = variance

        def posterior(self, values):
            return Posterior(self.multiplier * values[:, :1], self.variance)

    components = network.component_map
    prepared = MappingProxyType(
        {
            "source": _PreparedComponent(
                components["source"],
                (),
                MappingProxyType({}),
                MappingProxyType({}),
                MappingProxyType({}),
                MappingProxyType({"driver_mean": (2.0, 0.04)}),
                MappingProxyType({}),
                4,
            ),
            "transform": _PreparedComponent(
                components["transform"],
                ("source.driver_mean",),
                MappingProxyType({"source.driver_mean": 0.0}),
                MappingProxyType({"source.driver_mean": 1.0}),
                MappingProxyType({"flow_mean": AffineModel(1.0, 0.01)}),
                MappingProxyType({}),
                MappingProxyType({"flow_mean": 1}),
                4,
            ),
            "score": _PreparedComponent(
                components["score"],
                ("transform.flow_mean",),
                MappingProxyType({"transform.flow_mean": 0.0}),
                MappingProxyType({"transform.flow_mean": 1.0}),
                MappingProxyType({"utility_last": AffineModel(2.0, 0.01)}),
                MappingProxyType({}),
                MappingProxyType({"utility_last": 1}),
                4,
            ),
        }
    )
    config = {
        "transform.choice": "base",
        "transform.gain": 1.0,
        "score.choice": "base",
        "score.offset": 0.0,
    }
    first = backend._propagate(prepared, config, "affine-fixture", 65_536)
    second = backend._propagate(prepared, config, "affine-fixture", 65_536)
    assert np.array_equal(first.objective, second.objective)
    assert abs(float(np.mean(first.objective)) - 4.0) <= 0.02
    assert abs(float(np.var(first.objective)) - 0.21) <= 0.03
    probability = float(np.mean(first.constraints["minimum_flow"] >= 2.0))
    assert abs(probability - 0.5) <= 0.02
    assert float(np.var(first.objective)) >= 0.0


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_full_network_propagation_failure_uses_recorded_sobol_fallback(
    tmp_path, full_network_contract, monkeypatch
):
    system, network, study, space = full_network_contract
    ledger = _observed_ledger(tmp_path, full_network_contract)
    backend = FullNetworkBayesBackend(
        study, space, network, system, candidate_pool_size=8, posterior_samples=16
    )
    monkeypatch.setattr(
        backend,
        "_propagate",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("propagation failed")),
    )
    action = backend.suggest(ledger)[0]
    diagnostics = backend.diagnostics(ledger)
    assert action.scope is EvaluationScope.SYSTEM
    assert action.suggested_by == "function_network_full:sobol"
    assert diagnostics.fit_state == "fallback"
    assert "posterior_propagation_failure" in diagnostics.fallback_reasons[0]


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_full_network_posterior_requires_minimum_observations(tmp_path, full_network_contract):
    system, network, study, space = full_network_contract
    ledger = _observed_ledger(tmp_path, full_network_contract, count=2)
    backend = FullNetworkBayesBackend(study, space, network, system)
    config = {
        "transform.choice": "base",
        "transform.gain": 1.0,
        "score.choice": "base",
        "score.offset": 0.0,
    }
    with pytest.raises(ValueError, match="minimum successful"):
        backend.posterior_samples(ledger, config)


@pytest.mark.skipif(FullNetworkBayesBackend is None, reason="optional Bayesian dependencies")
def test_full_network_rejects_component_scope_ledger_rows(tmp_path, full_network_contract):
    system, network, study, space = full_network_contract
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    action = EvaluationAction.component("eval-000000", "transform", {})
    from autoengineering.optimization import EvaluationResult

    ledger.append(action, EvaluationResult.model_failure(action.id, "not observed"))
    backend = FullNetworkBayesBackend(study, space, network, system)
    with pytest.raises(ValueError, match="system scope"):
        backend.suggest(ledger)


def test_full_network_optional_dependency_boundary_is_concise():
    command = [
        sys.executable,
        "-c",
        "import importlib.util\n"
        "available = importlib.util.find_spec('botorch') is not None\n"
        "try:\n import autoengineering.optimization.full_network_backend\n"  # waterology: allow-abs-path
        "except ImportError as error:\n"  # waterology: allow-abs-path
        " assert not available and 'install autoengineering[bayes]' in str(error)\n"
        "else:\n assert available",  # waterology: allow-abs-path
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
