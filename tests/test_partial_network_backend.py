"""Contracts for partial-observability function-network optimization."""

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
    from autoengineering.optimization.partial_network_backend import (
        PartialNetworkBayesBackend,
    )
else:
    PartialNetworkBayesBackend = None


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
