"""Behavioral contracts for deterministic optimization baseline policies."""

import json
import importlib.util
from itertools import product
import subprocess
import sys
import warnings

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

if importlib.util.find_spec("botorch") is not None:
    from autoengineering.optimization.system_backend import SystemBayesBackend
else:
    SystemBayesBackend = None


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


def test_optional_system_backend_has_a_concise_missing_dependency_boundary():
    """Leaking a partial optional-stack traceback must fail this import-boundary test."""
    command = [
        sys.executable,
        "-c",
        "import importlib.util\n"
        "available = importlib.util.find_spec('botorch') is not None\n"
        "try:\n import autoengineering.optimization.system_backend\n"
        "except ImportError as error:\n assert not available and 'install autoengineering[bayes]' in str(error)\n"
        "else:\n assert available",
    ]

    completed = subprocess.run(command, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr


def test_evaluator_model_failure_from_runner_is_durable_ledger_observation(tmp_path):
    """Misclassifying a runner OSError as infrastructure must fail this observation check."""
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
    assert stored_result.status is EvaluationStatus.MODEL_FAILURE
    assert stored_result.evaluator_seconds == pytest.approx(4.0)
    assert stored_result.cost == pytest.approx(4.0)


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_uses_replayable_sobol_cold_start(study, space, empty_ledger):
    """Replacing the cold-start Sobol policy with uncontrolled sampling must fail this test."""
    first = SystemBayesBackend(study, space, min_initial=6).suggest(empty_ledger, n=2)
    second = SystemBayesBackend(study, space, min_initial=6).suggest(empty_ledger, n=2)

    assert first == second
    assert all(action.suggested_by == "system:sobol" for action in first)
    assert all(action.id.startswith("eval-") for action in first)


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_fits_double_precision_constraint_models(empty_ledger):
    """Dropping a constraint model or fitting float32 data must fail this integration test."""
    local_study = StudySpec(
        name="bayes-fit",
        objective=ObjectiveSpec(outcome="score", direction="maximize"),
        constraints=(ConstraintSpec(outcome="limit", operator=">=", threshold=0.0),),
        budget=BudgetSpec(max_cost=20.0, cost_unit="cpu_hour"),
        noise=NoiseSpec(mode="deterministic", noise_floor=1e-5),
        backend="system",
        seed=7,
    )
    local_space = SearchSpace(parameters=(ContinuousParameter("x", 0.0, 1.0),))
    for index, x in enumerate((0.05, 0.25, 0.55, 0.85), start=1):
        _append_observation(
            empty_ledger,
            f"eval-{index:06d}",
            {"x": x},
            {"score": 1.0 - (x - 0.7) ** 2, "limit": x - 0.2},
        )

    backend = SystemBayesBackend(local_study, local_space, min_initial=2, raw_samples=16)
    action = backend.suggest(empty_ledger)[0]
    diagnostics = backend.diagnostics(empty_ledger)

    assert action.suggested_by == "system:bayes"
    assert diagnostics.fit_state == "fitted"
    assert diagnostics.details["dtype"] == "torch.float64"
    assert diagnostics.details["outcome_order"] == ("score", "limit")


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_projects_conditional_mixed_candidates(empty_ledger):
    """Allowing nonbinary masks or inactive values through decode must fail this test."""
    local_study = StudySpec(
        name="mixed-bayes",
        objective=ObjectiveSpec(outcome="score", direction="maximize"),
        constraints=(),
        budget=BudgetSpec(max_cost=20.0, cost_unit="cpu_hour"),
        noise=NoiseSpec(),
        backend="system",
        seed=11,
    )
    local_space = SearchSpace(
        parameters=(
            CategoricalParameter("routing", ("linear", "storage")),
            IntegerParameter("steps", 1, 5, active_when={"routing": ("storage",)}),
            ContinuousParameter("rate", 0.1, 10.0, scale="log"),
        )
    )
    for index, config in enumerate(
        (
            {"routing": "linear", "rate": 0.2},
            {"routing": "storage", "steps": 2, "rate": 0.8},
            {"routing": "storage", "steps": 4, "rate": 2.0},
        ),
        start=1,
    ):
        _append_observation(empty_ledger, f"eval-{index:06d}", config, {"score": float(index)})

    action = SystemBayesBackend(local_study, local_space, min_initial=2, raw_samples=16).suggest(
        empty_ledger
    )[0]

    assert local_space.decode(local_space.encode(action.config)) == action.config
    if action.config["routing"] == "linear":
        assert "steps" not in action.config


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_caps_categorical_enumeration_before_materializing(monkeypatch, study):
    """Iterating every assignment before applying the safety cap must fail this test."""
    from autoengineering.optimization import system_backend

    local_space = SearchSpace(
        parameters=(CategoricalParameter("choice", tuple(f"c{index}" for index in range(1000))),)
    )
    yielded = 0

    def counted_product(*choices):
        nonlocal yielded
        for values in product(*choices):
            yielded += 1
            yield values

    monkeypatch.setattr(system_backend, "product", counted_product)
    backend = SystemBayesBackend(study, local_space, max_categorical_assignments=3)

    assignments, exceeded = backend._fixed_assignments()

    assert assignments == ()
    assert exceeded is True
    assert yielded == 4


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_optimization_warning_falls_back_with_captured_warning(
    monkeypatch, empty_ledger
):
    """Accepting a RuntimeWarning from acquisition optimization must fail this test."""
    from autoengineering.optimization import system_backend

    local_study = StudySpec(
        name="warning",
        objective=ObjectiveSpec(outcome="score", direction="maximize"),
        constraints=(),
        budget=BudgetSpec(max_cost=20.0, cost_unit="cpu_hour"),
        noise=NoiseSpec(),
        backend="system",
        seed=4,
    )
    local_space = SearchSpace(parameters=(ContinuousParameter("x", 0.0, 1.0),))
    for index, x in enumerate((0.1, 0.4, 0.8), start=1):
        _append_observation(empty_ledger, f"eval-{index:06d}", {"x": x}, {"score": x})

    def warned_optimizer(**kwargs):
        import torch

        warnings.warn("optimization did not converge", RuntimeWarning)
        return torch.tensor([[0.6]], dtype=torch.double), torch.tensor(0.0, dtype=torch.double)

    monkeypatch.setattr(system_backend, "optimize_acqf_mixed", warned_optimizer)
    backend = SystemBayesBackend(local_study, local_space, min_initial=2, raw_samples=4)

    action = backend.suggest(empty_ledger)[0]
    diagnostics = backend.diagnostics(empty_ledger)

    assert action.suggested_by == "system:sobol"
    assert "optimization_warning" in diagnostics.fallback_reasons[0]
    assert any("did not converge" in warning for warning in diagnostics.warnings)


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
@pytest.mark.parametrize("enabled,warn_only", ((False, False), (True, False), (True, True)))
def test_system_backend_restores_torch_global_state_after_cold_start(
    study, space, empty_ledger, enabled, warn_only
):
    """Leaving deterministic mode or the global RNG changed after suggest must fail this test."""
    import torch

    original_enabled = torch.are_deterministic_algorithms_enabled()
    original_warn_only = torch.is_deterministic_algorithms_warn_only_enabled()
    try:
        torch.use_deterministic_algorithms(enabled, warn_only=warn_only)
        torch.manual_seed(918)
        expected = torch.rand(3)
        torch.manual_seed(918)

        SystemBayesBackend(study, space, min_initial=6).suggest(empty_ledger)

        assert torch.equal(torch.rand(3), expected)
        assert torch.are_deterministic_algorithms_enabled() is enabled
        assert torch.is_deterministic_algorithms_warn_only_enabled() is warn_only
    finally:
        torch.use_deterministic_algorithms(original_enabled, warn_only=original_warn_only)


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_fallback_reports_usable_and_excluded_counts(study, space, empty_ledger):
    """Replacing observed usable counts with zero in fallback diagnostics must fail this test."""
    _append_observation(empty_ledger, "eval-000001", {"model": "a"}, {"score": 1.0, "bias": 1.0})
    _append_observation(empty_ledger, "eval-000002", {"model": "b"}, {"score": 2.0})

    diagnostics = SystemBayesBackend(study, space, min_initial=6).diagnostics(empty_ledger)
    assert diagnostics.fit_state == "not_fit_for_ledger"
    SystemBayesBackend(study, space, min_initial=6).suggest(empty_ledger)
    diagnostics = SystemBayesBackend(study, space, min_initial=6).diagnostics(empty_ledger)

    # The fresh object intentionally has no stale diagnostics; inspect the fitting instance instead.
    backend = SystemBayesBackend(study, space, min_initial=6)
    backend.suggest(empty_ledger)
    diagnostics = backend.diagnostics(empty_ledger)
    assert diagnostics.details["usable_observations"] == 1
    assert diagnostics.details["excluded"]["incomplete_success"] == 1


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_implements_protocol_and_stable_constructor_state(study, space):
    """Removing backend protocol methods or replay controls from state must fail this test."""
    backend = SystemBayesBackend(study, space, min_initial=2, raw_samples=4, num_restarts=1)

    assert isinstance(backend, OptimizerBackend)
    assert json.loads(json.dumps(backend.state_dict(), sort_keys=True)) == backend.state_dict()
    assert backend.state_dict()["constructor"]["min_initial"] == 2
    with pytest.raises(ValueError, match="raw_samples"):
        SystemBayesBackend(study, space, raw_samples=1)


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_noise_modes_aggregate_replicates_and_reject_known_noise_gaps(empty_ledger):
    """Dropping replicate aggregation or learning missing known noise must fail this test."""
    local_space = SearchSpace(parameters=(ContinuousParameter("x", 0.0, 1.0),))
    for index, outcome in enumerate((1.0, 3.0), start=1):
        action = EvaluationAction.system(f"eval-{index:06d}", {"x": 0.5}, seed=index)
        empty_ledger.append(
            action,
            EvaluationResult.success(
                action.id, {"score": outcome}, {"score": 0.2}, 1.0, "cpu_hour"
            ),
        )
    deterministic = StudySpec(
        "noise",
        ObjectiveSpec("score", "maximize"),
        (),
        BudgetSpec(5, "cpu_hour"),
        NoiseSpec("deterministic", 1e-4),
        "system",
        2,
    )
    known = StudySpec(
        "noise",
        ObjectiveSpec("score", "maximize"),
        (),
        BudgetSpec(5, "cpu_hour"),
        NoiseSpec("known", 1e-6),
        "system",
        2,
    )
    learned = StudySpec(
        "noise",
        ObjectiveSpec("score", "maximize"),
        (),
        BudgetSpec(5, "cpu_hour"),
        NoiseSpec("learned", 1e-6),
        "system",
        2,
    )

    prepared, excluded, gap = SystemBayesBackend(deterministic, local_space)._observations(
        empty_ledger.entries()
    )
    assert prepared[0].shape == (1, 1)
    assert prepared[1].item() == pytest.approx(2.0)
    assert prepared[2].item() == pytest.approx(1e-8)
    assert excluded["duplicate_aggregations"] == 1
    assert gap is False
    assert (
        SystemBayesBackend(learned, local_space)._observations(empty_ledger.entries())[0][2] is None
    )

    missing_error = EvaluationAction.system("eval-000003", {"x": 0.8}, seed=3)
    empty_ledger.append(
        missing_error,
        EvaluationResult.success(missing_error.id, {"score": 0.0}, {}, 1.0, "cpu_hour"),
    )
    backend = SystemBayesBackend(known, local_space, min_initial=1, raw_samples=4)
    assert backend.suggest(empty_ledger)[0].suggested_by == "system:sobol"
    assert backend.diagnostics(empty_ledger).fallback_reasons == (
        "known_noise_missing_standard_error",
    )


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_fixed_assignments_project_categories_and_conditions(study):
    """Leaving categories, masks, or inactive values free must fail this projection test."""
    local_space = SearchSpace(
        parameters=(
            CategoricalParameter("kind", ("off", "on")),
            ContinuousParameter("gain", 0.1, 1.0, active_when={"kind": ("on",)}),
        )
    )
    assignments, exceeded = SystemBayesBackend(study, local_space)._fixed_assignments()

    assert exceeded is False
    assert assignments == ({0: 0.0, 1: 0.5, 2: 0.0}, {0: 1.0, 2: 1.0})


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_candidate_decode_rounds_integer_and_preserves_log_bounds(study):
    """Bypassing SearchSpace decode must fail integer rounding and log-bound projection."""
    import torch

    local_space = SearchSpace(
        parameters=(IntegerParameter("count", 1, 5), ContinuousParameter("rate", 0.1, 10, "log"))
    )
    backend = SystemBayesBackend(study, local_space)

    config = backend._decode_candidate(torch.tensor([0.62, 0.5], dtype=torch.double))

    assert config == {"count": 3, "rate": pytest.approx(1.0)}


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_fit_and_invalid_candidate_fallbacks_are_explicit(
    monkeypatch, study, empty_ledger
):
    """Leaking fit errors or stale invalid candidates must fail these fallback contracts."""
    import torch

    local_space = SearchSpace(parameters=(ContinuousParameter("x", 0.0, 1.0),))
    for index, x in enumerate((0.1, 0.5, 0.9), start=1):
        _append_observation(empty_ledger, f"eval-{index:06d}", {"x": x}, {"score": x, "bias": 1.0})
    backend = SystemBayesBackend(study, local_space, min_initial=2, raw_samples=4, num_restarts=1)
    monkeypatch.setattr(
        backend, "_fit", lambda *args: (_ for _ in ()).throw(RuntimeError("fit broke"))
    )
    assert backend.suggest(empty_ledger)[0].suggested_by == "system:sobol"
    assert "fit_failure" in backend.diagnostics(empty_ledger).fallback_reasons[0]

    backend = SystemBayesBackend(
        study, local_space, min_initial=2, raw_samples=4, num_restarts=1, candidate_retry_limit=1
    )
    monkeypatch.setattr(backend, "_candidate", lambda *args: torch.tensor([float("nan")]))
    assert backend.suggest(empty_ledger)[0].suggested_by == "system:sobol"
    assert "candidate_invalidation" in backend.diagnostics(empty_ledger).fallback_reasons[0]


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_passes_correct_objective_sign_and_constraint_convention(monkeypatch):
    """Reversing minimize or either threshold constraint must fail this acquisition boundary test."""
    import torch
    from autoengineering.optimization import system_backend

    captured = {}

    class CapturedAcquisition:
        pass

    def capture_acquisition(**kwargs):
        captured.update(kwargs)
        return CapturedAcquisition()

    monkeypatch.setattr(system_backend, "qLogNoisyExpectedImprovement", capture_acquisition)
    monkeypatch.setattr(
        system_backend,
        "optimize_acqf_mixed",
        lambda **kwargs: (torch.tensor([[0.5]], dtype=torch.double), torch.tensor(0.0)),
    )
    spec = StudySpec(
        "signs",
        ObjectiveSpec("loss", "minimize"),
        (ConstraintSpec("lower", ">=", 2.0), ConstraintSpec("upper", "<=", 5.0)),
        BudgetSpec(5, "cpu_hour"),
        NoiseSpec(),
        "system",
        3,
    )
    backend = SystemBayesBackend(
        spec,
        SearchSpace((ContinuousParameter("x", 0.0, 1.0),)),
        num_restarts=1,
        raw_samples=4,
    )
    backend._candidate(
        None,
        torch.tensor([[0.2]], dtype=torch.double),
        ("loss", "lower", "upper"),
        ({},),
        1,
    )
    samples = torch.tensor([[[3.0, 1.5, 4.0]]], dtype=torch.double)

    assert captured["objective"](samples).item() == -3.0
    assert captured["constraints"][0](samples).item() == pytest.approx(0.5)
    assert captured["constraints"][1](samples).item() == pytest.approx(-1.0)


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_diagnostics_are_not_reused_for_changed_ledger(study, space, empty_ledger):
    """Returning a prior-ledger fit after append must fail this stale-state test."""
    backend = SystemBayesBackend(study, space, min_initial=6)
    backend.suggest(empty_ledger)
    action = EvaluationAction.system("eval-000000", {"model": "a"}, seed=1)
    empty_ledger.append(
        action,
        EvaluationResult.success(action.id, {"score": 1.0, "bias": 1.0}, {}, 1.0, "cpu_hour"),
    )

    assert backend.diagnostics(empty_ledger).fit_state == "not_fit_for_ledger"


@pytest.mark.skipif(SystemBayesBackend is None, reason="whole-system backend is unavailable")
def test_system_backend_fixed_seed_closed_loop_improves_feasible_regret(empty_ledger):
    """A policy that never improves a constrained mixed initial design must fail this test."""
    local_space = SearchSpace(
        parameters=(
            CategoricalParameter("family", ("wide", "narrow")),
            ContinuousParameter("x", 0.0, 1.0),
            IntegerParameter("steps", 1, 4, active_when={"family": ("narrow",)}),
        )
    )
    spec = StudySpec(
        "closed-loop",
        ObjectiveSpec("score", "maximize"),
        (ConstraintSpec("feasible_x", ">=", 0.25),),
        BudgetSpec(20, "cpu_hour"),
        NoiseSpec(),
        "system",
        29,
    )

    def outcomes(config):
        x = config["x"]
        offset = 0.0 if config["family"] == "wide" else 0.08 * (config["steps"] - 3) ** 2
        return {"score": 1.0 - (x - 0.72) ** 2 - offset, "feasible_x": x - 0.25}

    initial = (
        {"family": "wide", "x": 0.3},
        {"family": "wide", "x": 0.4},
        {"family": "narrow", "x": 0.3, "steps": 1},
        {"family": "narrow", "x": 0.45, "steps": 4},
    )
    for index, config in enumerate(initial):
        _append_observation(empty_ledger, f"eval-{index:06d}", config, outcomes(config))
    initial_best = max(outcomes(config)["score"] for config in initial)
    backend = SystemBayesBackend(
        spec,
        local_space,
        min_initial=4,
        num_restarts=1,
        raw_samples=8,
        candidate_retry_limit=2,
    )
    for _ in range(8):
        action = backend.suggest(empty_ledger)[0]
        empty_ledger.append(
            action,
            EvaluationResult.success(action.id, outcomes(action.config), {}, 1.0, "cpu_hour"),
        )

    recommendation = backend.recommend(empty_ledger)

    assert len(empty_ledger.entries()) == 12
    assert recommendation.feasible is True
    assert recommendation.outcomes["score"] > initial_best
