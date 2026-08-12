"""Behavioral contracts for deterministic optimization baseline policies."""

import json
import subprocess
import sys

import numpy as np
import pytest
from scipy.stats import qmc

from autoengineering.optimization import (
    BudgetSpec,
    CategoricalParameter,
    ConstraintSpec,
    ContinuousParameter,
    EvaluationAction,
    EvaluationResult,
    EvaluationStatus,
    IntegerParameter,
    NoiseSpec,
    OptimizerBackend,
    ObjectiveSpec,
    ObservationLedger,
    RandomBackend,
    SearchSpace,
    SearchSpaceExhausted,
    SobolBackend,
    StudySpec,
)
from autoengineering.research.runner import EvaluationContext, execute_action
from autoengineering.system.graph import System


@pytest.fixture
def study():
    return StudySpec(
        name="baseline-policy",
        objective=ObjectiveSpec(outcome="score", direction="maximize"),
        constraints=(ConstraintSpec(outcome="bias", operator=">=", threshold=0.0),),
        budget=BudgetSpec(max_cost=20.0, cost_unit="cpu_hour"),
        noise=NoiseSpec(),
        backend="system",
        seed=23,
    )


@pytest.fixture
def space():
    return SearchSpace(parameters=(CategoricalParameter("model", ("a", "b", "c")),))


@pytest.fixture
def empty_ledger(tmp_path):
    return ObservationLedger(tmp_path / "observations.jsonl")


def test_sobol_suggestions_replay_from_seed(study, space, empty_ledger):
    """Replacing Sobol sampling with uncontrolled randomness must fail this test."""
    first = SobolBackend(spec=study, space=space).suggest(empty_ledger, n=3)
    second = SobolBackend(spec=study, space=space).suggest(empty_ledger, n=3)

    assert first == second


def test_recommendation_is_best_feasible_observation(study, space, empty_ledger):
    """Ranking failed or infeasible observations must fail this test."""
    actions = tuple(
        EvaluationAction.system(f"eval-{index:06d}", {"model": model}, seed=index)
        for index, model in enumerate(("a", "b", "c"), start=1)
    )
    for action, score, bias in zip(actions, (1.0, 3.0, 2.0), (1.0, -1.0, 1.0), strict=True):
        empty_ledger.append(
            action,
            EvaluationResult.success(
                action.id,
                {"score": score, "bias": bias},
                {},
                1.0,
                "cpu_hour",
            ),
        )

    recommendation = RandomBackend(spec=study, space=space).recommend(empty_ledger)

    assert recommendation.action_id == "eval-000003"
    assert recommendation.feasible is True


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
def test_baselines_implement_the_public_runtime_protocol(backend_type, study, space):
    """Removing one backend contract method must fail runtime protocol recognition."""
    assert isinstance(backend_type(spec=study, space=space), OptimizerBackend)


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
def test_suggestions_replay_with_fresh_instances_and_unchanged_ledger(
    backend_type, study, space, empty_ledger
):
    """Adding hidden mutable sampling state must make equivalent requests diverge."""
    first = backend_type(spec=study, space=space).suggest(empty_ledger, n=2)
    second = backend_type(spec=study, space=space).suggest(empty_ledger, n=2)

    assert first == second


def test_action_seeds_use_the_declared_seed_sequence(study, space, empty_ledger):
    """Changing action seed derivation must fail this exact SeedSequence expectation."""
    actions = RandomBackend(spec=study, space=space).suggest(empty_ledger, n=2)

    assert tuple(action.seed for action in actions) == tuple(
        int(np.random.SeedSequence([study.seed, index]).generate_state(1)[0]) for index in (0, 1)
    )


def test_ids_follow_the_largest_noncontiguous_existing_index(study, space, empty_ledger):
    """Reusing an ID after a noncontiguous ledger entry must fail this test."""
    existing = EvaluationAction.system("eval-000007", {"model": "a"}, seed=7)
    empty_ledger.append(
        existing,
        EvaluationResult.success(existing.id, {"score": 1.0, "bias": 1.0}, {}, 1.0, "cpu_hour"),
    )

    action = RandomBackend(spec=study, space=space).suggest(empty_ledger)[0]

    assert action.id == "eval-000008"
    assert action.seed == int(np.random.SeedSequence([study.seed, 8]).generate_state(1)[0])


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
def test_suggestions_cover_bounds_and_exclude_existing_configs(backend_type, study, empty_ledger):
    """Returning an out-of-space or already observed configuration must fail this test."""
    full_space = SearchSpace(
        parameters=(
            CategoricalParameter("method", ("fixed",)),
            IntegerParameter("steps", 1, 3),
            ContinuousParameter("rate", 1e-2, 1e2, scale="log"),
        )
    )
    existing = EvaluationAction.system(
        "eval-000000", {"method": "fixed", "steps": 1, "rate": 1.0}, seed=0
    )
    empty_ledger.append(
        existing,
        EvaluationResult.success(existing.id, {"score": 0.0, "bias": 0.0}, {}, 1.0, "cpu_hour"),
    )

    actions = backend_type(spec=study, space=full_space).suggest(empty_ledger, n=3)

    assert len({tuple(action.config.items()) for action in actions}) == 3
    for action in actions:
        full_space.encode(action.config)
        assert action.config["method"] == "fixed"
        assert 1 <= action.config["steps"] <= 3
        assert 1e-2 <= action.config["rate"] <= 1e2
        assert action.config != existing.config


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
def test_suggestions_project_conditional_masks_to_the_valid_manifold(
    backend_type, study, empty_ledger
):
    """Passing a nonbinary conditional activity value to decode must fail this test."""
    conditional_space = SearchSpace(
        parameters=(
            CategoricalParameter("routing", ("linear", "storage")),
            IntegerParameter("subreaches", 1, 3, active_when={"routing": ("storage",)}),
        )
    )

    actions = backend_type(spec=study, space=conditional_space).suggest(empty_ledger, n=4)

    assert {action.config["routing"] for action in actions} == {"linear", "storage"}
    for action in actions:
        encoded = conditional_space.encode(action.config)
        if action.config["routing"] == "linear":
            assert "subreaches" not in action.config
            assert encoded[1:] == (0.5, 0.0)
        else:
            assert 1 <= action.config["subreaches"] <= 3
            assert encoded[2] == 1.0


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
def test_finite_spaces_exhaust_exactly_and_reject_invalid_batch_sizes(
    backend_type, study, empty_ledger
):
    """Silently repeating a finite configuration or accepting zero must fail this test."""
    finite_space = SearchSpace(
        parameters=(
            CategoricalParameter("enabled", (True, 1)),
            IntegerParameter("count", 1, 2),
        )
    )
    backend = backend_type(spec=study, space=finite_space)

    assert len(backend.suggest(empty_ledger, n=4)) == 4
    with pytest.raises(SearchSpaceExhausted):
        backend.suggest(empty_ledger, n=5)
    for invalid_n in (0, -1, True, 1.5):
        with pytest.raises(ValueError, match="n"):
            backend.suggest(empty_ledger, n=invalid_n)


def test_sobol_first_continuous_point_matches_scrambled_scipy_sequence(study, empty_ledger):
    """Replacing the Sobol sequence with pseudorandom draws must fail this test."""
    continuous_space = SearchSpace(parameters=(ContinuousParameter("x", 0.0, 1.0),))

    action = SobolBackend(spec=study, space=continuous_space).suggest(empty_ledger)[0]
    expected = float(qmc.Sobol(d=1, scramble=True, seed=study.seed).random(1)[0, 0])

    assert action.config == pytest.approx({"x": expected})


def test_sobol_returns_a_batch_larger_than_the_former_fixed_scan_limit(study, empty_ledger):
    """Capping all Sobol scans at 1,024 points must fail this large-batch request."""
    continuous_space = SearchSpace(parameters=(ContinuousParameter("x", 0.0, 1.0),))

    actions = SobolBackend(spec=study, space=continuous_space).suggest(empty_ledger, n=1025)

    assert len(actions) == 1025
    assert len({action.config["x"] for action in actions}) == 1025


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
@pytest.mark.parametrize(
    ("action", "message"),
    (
        (
            EvaluationAction.system("eval-1", {"model": "a"}, seed=1),
            "canonical action ID",
        ),
        (
            EvaluationAction.system("eval-０００００１", {"model": "a"}, seed=1),
            "canonical action ID",
        ),
        (
            EvaluationAction.system("eval-0000000", {"model": "a"}, seed=1),
            "canonical action ID",
        ),
        (
            EvaluationAction.component("eval-000001", "routing", {"model": "a"}, seed=1),
            "system scope",
        ),
    ),
)
def test_suggest_rejects_ledger_actions_outside_the_system_protocol(
    backend_type, study, space, empty_ledger, action, message
):
    """Accepting malformed IDs or component actions must fail protocol validation."""
    empty_ledger.append(
        action,
        EvaluationResult.success(action.id, {"score": 1.0, "bias": 1.0}, {}, 1.0, "cpu_hour"),
    )

    with pytest.raises(ValueError, match=message):
        backend_type(spec=study, space=space).suggest(empty_ledger)


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
def test_suggest_continues_from_a_canonical_id_beyond_six_digits(
    backend_type, study, space, empty_ledger
):
    """Rejecting minimum-width IDs above 999,999 must fail resumed suggestion replay."""
    action = EvaluationAction.system("eval-1000000", {"model": "a"}, seed=1)
    empty_ledger.append(
        action,
        EvaluationResult.success(action.id, {"score": 1.0, "bias": 1.0}, {}, 1.0, "cpu_hour"),
    )

    suggestion = backend_type(spec=study, space=space).suggest(empty_ledger)

    assert suggestion[0].id == "eval-1000001"


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
@pytest.mark.parametrize(
    ("config", "message"),
    (
        ({"routing": "linear", "subreaches": 2}, "inactive parameter"),
        ({"routing": "storage", "subreaches": 2, "unknown": 1}, "unknown configuration"),
    ),
)
def test_suggest_rejects_ledger_configs_outside_its_search_space(
    backend_type, study, empty_ledger, config, message
):
    """Using invalid observed configs for duplicate tracking must fail fast."""
    conditional_space = SearchSpace(
        parameters=(
            CategoricalParameter("routing", ("linear", "storage")),
            IntegerParameter("subreaches", 1, 3, active_when={"routing": ("storage",)}),
        )
    )
    action = EvaluationAction.system("eval-000001", config, seed=1)
    empty_ledger.append(
        action,
        EvaluationResult.success(action.id, {"score": 1.0, "bias": 1.0}, {}, 1.0, "cpu_hour"),
    )

    with pytest.raises(ValueError, match=message):
        backend_type(spec=study, space=conditional_space).suggest(empty_ledger)


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
def test_large_finite_integer_space_is_sampled_without_materializing_every_value(
    backend_type, study, empty_ledger
):
    """Enumerating a billion integer values must fail this prompt sampling contract."""
    large_space = SearchSpace(parameters=(IntegerParameter("count", 1, 1_000_000_000),))

    first = backend_type(spec=study, space=large_space).suggest(empty_ledger)
    second = backend_type(spec=study, space=large_space).suggest(empty_ledger)

    assert first == second
    assert 1 <= first[0].config["count"] <= 1_000_000_000


def _append_observation(ledger, action_id, config, outcomes, *, cost=1.0, status=None):
    action = EvaluationAction.system(action_id, config, seed=1)
    result = (
        EvaluationResult.success(action_id, outcomes, {}, cost, "cpu_hour")
        if status is None
        else EvaluationResult(action_id, status, cost=cost, cost_unit="cpu_hour", message="failed")
    )
    ledger.append(action, result)


def test_recommendation_honors_minimization_constraints_and_tie_breaking(empty_ledger):
    """Ignoring constraint direction, cost, or action IDs must fail this ranking test."""
    minimize_study = StudySpec(
        name="minimize",
        objective=ObjectiveSpec(outcome="loss", direction="minimize"),
        constraints=(
            ConstraintSpec(outcome="lower", operator=">=", threshold=2.0),
            ConstraintSpec(outcome="upper", operator="<=", threshold=5.0),
        ),
        budget=BudgetSpec(max_cost=20.0, cost_unit="cpu_hour"),
        noise=NoiseSpec(),
        backend="system",
        seed=3,
    )
    local_space = SearchSpace(parameters=(CategoricalParameter("model", ("a", "b", "c", "d")),))
    _append_observation(
        empty_ledger,
        "eval-000004",
        {"model": "a"},
        {"loss": 1.0, "lower": 2.0, "upper": 5.0},
        cost=3.0,
    )
    _append_observation(
        empty_ledger,
        "eval-000003",
        {"model": "b"},
        {"loss": 1.0, "lower": 2.0, "upper": 5.0},
        cost=2.0,
    )
    _append_observation(
        empty_ledger, "eval-000002", {"model": "c"}, {"loss": 0.0, "lower": 1.0, "upper": 5.0}
    )
    _append_observation(
        empty_ledger, "eval-000001", {"model": "d"}, {"loss": 0.0, "lower": 2.0, "upper": 6.0}
    )

    recommendation = SobolBackend(spec=minimize_study, space=local_space).recommend(empty_ledger)

    assert recommendation.action_id == "eval-000003"
    assert recommendation.outcomes == {"loss": 1.0, "lower": 2.0, "upper": 5.0}


def test_recommendation_excludes_missing_and_failed_observations(study, space, empty_ledger):
    """Treating incomplete or failed results as feasible must fail this test."""
    _append_observation(empty_ledger, "eval-000001", {"model": "a"}, {"score": 9.0})
    _append_observation(
        empty_ledger,
        "eval-000002",
        {"model": "b"},
        {},
        status=EvaluationStatus.SCIENTIFIC_INFEASIBLE,
    )

    recommendation = RandomBackend(spec=study, space=space).recommend(empty_ledger)

    assert recommendation.action_id is None
    assert recommendation.config == {}
    assert recommendation.outcomes == {}
    assert recommendation.feasible is False
    assert recommendation.message


@pytest.mark.parametrize("backend_type", (RandomBackend, SobolBackend))
def test_diagnostics_and_state_are_truthful_stable_json(backend_type, study, space, empty_ledger):
    """Claiming a fitted surrogate or returning unstable state must fail this test."""
    backend = backend_type(spec=study, space=space)

    diagnostics = backend.diagnostics(empty_ledger)
    state = backend.state_dict()

    assert diagnostics.backend == backend.name
    assert diagnostics.fit_state == "stateless_baseline"
    assert diagnostics.details["ledger_entries"] == 0
    assert json.loads(json.dumps(state, sort_keys=True)) == state
    assert state["sequence_state"] == "derived_from_ledger"
    assert state["finite_enumeration_limit"] == 100_000
    if backend_type is SobolBackend:
        assert state["scan_retries_per_candidate"] == 64


def test_base_optimization_import_has_no_bayesian_or_smac_dependencies():
    """Eagerly importing optional optimization stacks must fail this import boundary test."""
    command = [
        sys.executable,
        "-c",
        "import autoengineering.optimization, sys; "
        "blocked={'torch','botorch','gpytorch','smac'}; "
        "assert not (blocked & {name.split('.')[0] for name in sys.modules})",
    ]

    completed = subprocess.run(command, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr


def test_evaluator_infrastructure_failure_is_durable_ledger_observation(tmp_path):
    """Discarding timed infrastructure failures must make this ledger entry disappear."""
    system = System("empty")
    component = system.add_component("model", metadata={"runnable": {"outputs": ["y"]}})
    component.add_input("x")
    component.add_output("y")
    context = EvaluationContext(
        system=system,
        alternatives={},
        source_arrays={"x": np.array([1.0])},
        observed={},
        outcome_functions={"value": lambda outputs: float(outputs["y"][0])},
        cost_unit="cpu_second",
    )
    action = EvaluationAction.component("eval-000001", "model", {})
    clock = iter((0.0, 4.0))

    result = execute_action(
        action,
        context,
        runner=lambda component, inputs: (_ for _ in ()).throw(OSError("storage down")),
        clock=lambda: next(clock),
    )
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    ledger.append(action, result)

    stored_action, stored_result = ledger.entries()[0]
    assert stored_action == action
    assert stored_result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE
    assert stored_result.evaluator_seconds == pytest.approx(4.0)
    assert stored_result.cost == pytest.approx(4.0)
