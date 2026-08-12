"""Tests for the research subpackage: runner, candidates, tree, and the loop.

Everything here is synthetic and offline. A tiny two-component chain
(source -> transform) is defined in-process, with candidate transforms written to
a temp module so the python runnable path exercises a real import.
"""

from __future__ import annotations

import textwrap
import hashlib
import io
import zipfile
from pathlib import Path

import numpy as np
import pytest
import autoengineering.research.runner as runner_module

from autoengineering.research.candidates import (
    Candidate,
    load_candidates,
    save_candidates,
)
from autoengineering.research.experiment import ExperimentNode, ExperimentTree
from autoengineering.research.loop import auto_improve
from autoengineering.research.runner import (
    EvaluationContext,
    InfrastructureFailure,
    ParentArtifactReference,
    ScientificInfeasibleError,
    build_feedforward_runner,
    execute_action,
    run_component,
)
from autoengineering.optimization import EvaluationAction, EvaluationStatus
from autoengineering.system.component import Component
from autoengineering.system.graph import System


# --------------------------------------------------------------------------- #
# Fixtures: a temp models module and a two-component system
# --------------------------------------------------------------------------- #

MODELS_SRC = textwrap.dedent(
    """
    import numpy as np

    def scale_two(x):
        # Poor model: doubles the input.
        return np.asarray(x) * 2.0

    def identity(x):
        # Good model: reproduces the input exactly.
        return np.asarray(x)

    def two_outputs(x):
        return np.asarray(x), np.asarray(x) + 1.0
    """
)


@pytest.fixture
def models_dir(tmp_path: Path) -> Path:
    (tmp_path / "tmodels.py").write_text(MODELS_SRC)
    return tmp_path


def _transform(entry: str, sys_path: str) -> Component:
    comp = Component(
        name="transform",
        model_type="transform",
        metadata={
            "runnable": {
                "kind": "python",
                "entry": entry,
                "sys_path": sys_path,
                "inputs": ["x"],
                "outputs": ["y"],
            }
        },
    )
    comp.add_input("x", data_type="timeseries")
    comp.add_output("y", data_type="timeseries")
    return comp


def _system(models_dir: Path) -> System:
    s = System("synthetic")
    src = s.add_component("source", model_type="data_source")
    src.add_output("x", data_type="timeseries")
    # baseline transform is the poor 'scale_two' model
    poor = _transform("tmodels:scale_two", str(models_dir))
    s._graph.add_node("transform", component=poor)
    s.connect("source", "transform", port_from="x", port_to="x")
    return s


def _evaluator_context(models_dir: Path) -> EvaluationContext:
    """Create the independent evaluator fixture used by action tests."""
    system = _system(models_dir)
    identity = _transform("tmodels:identity", str(models_dir))
    return EvaluationContext(
        system=system,
        alternatives={"transform": {"identity": identity}},
        source_arrays={"source.x": np.array([1.0, 2.0, 3.0])},
        observed={"y": np.array([1.0, 2.0, 3.0])},
        outcome_functions={
            "rmse": lambda outputs: float(
                np.sqrt(np.mean((outputs["transform.y"] - np.array([1.0, 2.0, 3.0])) ** 2))
            )
        },
        cost_unit="cpu_second",
    )


# --------------------------------------------------------------------------- #
# run_component
# --------------------------------------------------------------------------- #


class TestRunComponent:
    def test_python_single_output(self, models_dir):
        comp = _transform("tmodels:scale_two", str(models_dir))
        out = run_component(comp, {"x": np.array([1.0, 2.0, 3.0])})
        assert "y" in out
        np.testing.assert_allclose(out["y"], [2.0, 4.0, 6.0])

    def test_python_tuple_output(self, models_dir):
        comp = Component(
            name="t",
            metadata={
                "runnable": {
                    "kind": "python",
                    "entry": "tmodels:two_outputs",
                    "sys_path": str(models_dir),
                    "inputs": ["x"],
                    "outputs": ["a", "b"],
                }
            },
        )
        out = run_component(comp, {"x": np.array([1.0, 2.0])})
        np.testing.assert_allclose(out["a"], [1.0, 2.0])
        np.testing.assert_allclose(out["b"], [2.0, 3.0])

    def test_missing_runnable_raises(self):
        comp = Component(name="bare")
        with pytest.raises(ValueError, match="no metadata"):
            run_component(comp, {})

    def test_missing_input_raises(self, models_dir):
        comp = _transform("tmodels:scale_two", str(models_dir))
        with pytest.raises(KeyError):
            run_component(comp, {"wrong": np.array([1.0])})

    def test_command_kind_npz_contract(self, models_dir, tmp_path):
        # A command runnable that reads inputs.npz and writes outputs.npz.
        script = tmp_path / "cmd_model.py"
        script.write_text(
            textwrap.dedent(
                """
                import sys, numpy as np
                data = np.load(sys.argv[1])
                np.savez(sys.argv[2], y=data['x'] + 10.0)
                """
            )
        )
        comp = Component(
            name="cmd",
            metadata={
                "runnable": {
                    "kind": "command",
                    "entry": f"python {script} {{inputs}} {{outputs}}",
                    "inputs": ["x"],
                    "outputs": ["y"],
                }
            },
        )
        out = run_component(comp, {"x": np.array([1.0, 2.0])})
        np.testing.assert_allclose(out["y"], [11.0, 12.0])


# --------------------------------------------------------------------------- #
# build_feedforward_runner
# --------------------------------------------------------------------------- #


class TestFeedforwardRunner:
    def test_runs_chain_and_exposes_outputs(self, models_dir):
        system = _system(models_dir)
        x = np.array([1.0, 2.0, 3.0])
        run_chain = build_feedforward_runner(system, {"source.x": x})
        out = run_chain(system)
        # baseline transform doubles x
        np.testing.assert_allclose(out["transform.y"], [2.0, 4.0, 6.0])
        assert "y" in out  # bare port name exposed too

    def test_swap_takes_effect_in_runner(self, models_dir):
        from autoengineering.execute.swap import swap_component

        system = _system(models_dir)
        x = np.array([1.0, 2.0, 3.0])
        run_chain = build_feedforward_runner(system, {"source.x": x})

        good = _transform("tmodels:identity", str(models_dir))
        swapped = swap_component(system, "transform", good)
        out = run_chain(swapped)
        np.testing.assert_allclose(out["transform.y"], [1.0, 2.0, 3.0])


# --------------------------------------------------------------------------- #
# Evaluation actions
# --------------------------------------------------------------------------- #


def test_execute_system_action_applies_choice_without_mutating_inputs(models_dir):
    """Removing action configuration application must return the doubled baseline."""
    context = _evaluator_context(models_dir)
    baseline_metadata = context.system.get_component("transform").metadata.copy()
    alternative_metadata = context.alternatives["transform"]["identity"].metadata.copy()
    action = EvaluationAction.system(
        "eval-000001",
        {"transform.choice": "identity"},
        seed=1,
    )

    result = execute_action(action, context)

    assert result.status is EvaluationStatus.SUCCESS
    assert result.outcomes["rmse"] == pytest.approx(0.0)
    assert result.cost > 0.0
    assert context.system.get_component("transform").metadata == baseline_metadata
    assert context.alternatives["transform"]["identity"].metadata == alternative_metadata


def test_evaluation_context_snapshots_caller_owned_system_alternatives_and_arrays(models_dir):
    """Mutating source objects after construction must not change an evaluation."""
    system = _system(models_dir)
    identity = _transform("tmodels:identity", str(models_dir))
    source_arrays = {"source.x": np.array([1.0, 2.0, 3.0])}
    context = EvaluationContext(
        system=system,
        alternatives={"transform": {"identity": identity}},
        source_arrays=source_arrays,
        observed={},
        outcome_functions={"value": lambda outputs: float(outputs["transform.y"][0])},
        cost_unit="cpu_second",
    )
    system.get_component("transform").metadata["runnable"]["entry"] = "tmodels:identity"
    identity.metadata["runnable"]["entry"] = "tmodels:scale_two"
    source_arrays["source.x"][0] = 99.0

    result = execute_action(
        EvaluationAction.system("eval-000011", {"transform.choice": "identity"}), context
    )

    assert result.status is EvaluationStatus.SUCCESS
    assert result.outcomes == {"value": 1.0}


def test_execute_action_applies_parameter_to_a_copy(models_dir):
    """Ignoring a configured parameter must leave the runner output at its default."""
    context = _evaluator_context(models_dir)
    alternative = context.alternatives["transform"]["identity"]
    alternative.metadata["runnable"]["params"] = {"offset": 0.0}
    action = EvaluationAction.system(
        "eval-000002",
        {"transform.choice": "identity", "transform.offset": 2.0},
    )

    result = execute_action(
        action,
        context,
        runner=lambda component, inputs: {
            "y": inputs["x"] + component.metadata["runnable"]["params"]["offset"]
        },
    )

    assert result.outcomes["rmse"] == pytest.approx(2.0)
    assert alternative.metadata["runnable"]["params"] == {"offset": 0.0}


def test_parameter_binding_requires_an_explicit_choice(models_dir):
    """Applying a parameter to the implicit baseline must be rejected."""
    system = _system(models_dir)
    alternative = _transform("tmodels:identity", str(models_dir))
    alternative.metadata["runnable"]["params"] = {"offset": 0.0}
    context = EvaluationContext(
        system=system,
        alternatives={"transform": {"identity": alternative}},
        source_arrays={"source.x": np.array([1.0])},
        observed={},
        outcome_functions={"value": lambda outputs: float(outputs["transform.y"][0])},
        cost_unit="cpu_second",
    )

    with pytest.raises(ValueError, match="explicit.*choice"):
        execute_action(EvaluationAction.system("eval-000012", {"transform.offset": 2.0}), context)


@pytest.mark.parametrize(
    "config",
    (
        {"transform": "identity"},
        {"missing.choice": "identity"},
        {"transform.choice": "missing"},
        {"transform.unknown": 1.0},
        {"transform.offset.extra": 1.0},
    ),
)
def test_execute_action_rejects_malformed_or_unknown_bindings(models_dir, config):
    """Silently ignoring an invalid optimizer binding must be impossible."""
    with pytest.raises(ValueError):
        execute_action(
            EvaluationAction.system("eval-000003", config), _evaluator_context(models_dir)
        )


def test_component_action_rejects_an_unknown_target_before_execution(models_dir):
    """A missing target must not be converted into an ambiguous model result."""
    with pytest.raises(ValueError, match="unknown component"):
        execute_action(
            EvaluationAction.component("eval-000031", "missing", {}), _evaluator_context(models_dir)
        )


def test_component_action_uses_only_target_component_and_source_inputs(models_dir):
    """Executing the full graph for a component action must make this call fail."""
    context = _evaluator_context(models_dir)
    action = EvaluationAction.component("eval-000004", "transform", {})

    result = execute_action(
        action,
        context,
        runner=lambda component, inputs: {
            "y": inputs["x"]
            if component.name == "transform"
            else (_ for _ in ()).throw(AssertionError())
        },
    )

    assert result.status is EvaluationStatus.SUCCESS
    assert result.outcomes["rmse"] == pytest.approx(0.0)


def test_system_action_wires_multiple_components_and_source_arrays(models_dir):
    """Skipping an edge or an unconnected source input changes the final output."""
    system = System("three-stage")
    source = system.add_component("source")
    source.add_output("x")
    first = system.add_component(
        "first", metadata={"runnable": {"inputs": ["x"], "outputs": ["y"]}}
    )
    first.add_input("x")
    first.add_output("y")
    second = system.add_component(
        "second", metadata={"runnable": {"inputs": ["y", "offset"], "outputs": ["z"]}}
    )
    second.add_input("y")
    second.add_input("offset")
    second.add_output("z")
    system.connect("source", "first", "x", "x")
    system.connect("first", "second", "y", "y")
    context = EvaluationContext(
        system=system,
        alternatives={},
        source_arrays={"source.x": np.array([1.0]), "second.offset": np.array([3.0])},
        observed={},
        outcome_functions={"value": lambda outputs: float(outputs["second.z"][0])},
        cost_unit="cpu_second",
    )

    result = execute_action(
        EvaluationAction.system("eval-000041", {}),
        context,
        runner=lambda component, inputs: (
            {"y": inputs["x"] + 1.0}
            if component.name == "first"
            else {"z": inputs["y"] + inputs["offset"]}
        ),
    )

    assert result.status is EvaluationStatus.SUCCESS
    assert result.outcomes == {"value": 5.0}


def test_replicates_report_mean_standard_error_and_measured_time(models_dir):
    """Collapsing replicate results to the last run must break both statistics."""
    values = iter((1.0, 3.0))
    times = iter((5.0, 7.5))
    context = _evaluator_context(models_dir)
    context = EvaluationContext(
        **{
            **context.__dict__,
            "outcome_functions": {"value": lambda outputs: float(outputs["y"][0])},
        }
    )
    action = EvaluationAction.component("eval-000005", "transform", {}, replicates=2)

    result = execute_action(
        action,
        context,
        runner=lambda component, inputs: {"y": np.array([next(values)])},
        clock=lambda: next(times),
    )

    assert result.outcomes == {"value": 2.0}
    assert result.standard_errors == {"value": pytest.approx(1.0)}
    assert result.evaluator_seconds == pytest.approx(2.5)
    assert result.cost == pytest.approx(2.5)


@pytest.mark.parametrize(
    ("error", "status"),
    (
        (TimeoutError("late"), EvaluationStatus.TIMEOUT),
        (ImportError("missing"), EvaluationStatus.MODEL_FAILURE),
        (RuntimeError("model exploded"), EvaluationStatus.MODEL_FAILURE),
        (OSError("disk unavailable"), EvaluationStatus.MODEL_FAILURE),
        (ScientificInfeasibleError("outside domain"), EvaluationStatus.SCIENTIFIC_INFEASIBLE),
    ),
)
def test_execute_action_classifies_runner_failures(models_dir, error, status):
    """Changing a narrow evaluator failure boundary must change this status."""
    context = _evaluator_context(models_dir)
    clock_values = iter((0.0, 3.0))

    result = execute_action(
        EvaluationAction.component("eval-000006", "transform", {}),
        context,
        runner=lambda component, inputs: (_ for _ in ()).throw(error),
        clock=lambda: next(clock_values),
    )

    assert result.status is status
    assert result.evaluator_seconds == pytest.approx(3.0)
    assert result.cost == pytest.approx(3.0)


def test_runner_can_explicitly_report_infrastructure_failure(models_dir):
    """Only a runner's explicit infrastructure signal may produce that status."""
    clock_values = iter((0.0, 3.0))

    result = execute_action(
        EvaluationAction.component("eval-000013", "transform", {}),
        _evaluator_context(models_dir),
        runner=lambda component, inputs: (_ for _ in ()).throw(InfrastructureFailure("queue down")),
        clock=lambda: next(clock_values),
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE


def test_all_outcomes_run_and_nonfinite_values_are_scientifically_infeasible(models_dir):
    """Returning after the first invalid outcome must skip the required second check."""
    called = []
    base = _evaluator_context(models_dir)
    context = EvaluationContext(
        **{
            **base.__dict__,
            "outcome_functions": {
                "invalid": lambda outputs: float("nan"),
                "also_called": lambda outputs: called.append(True) or 1.0,
            },
        }
    )

    result = execute_action(
        EvaluationAction.component("eval-000007", "transform", {}),
        context,
        runner=lambda component, inputs: {"y": inputs["x"]},
    )

    assert result.status is EvaluationStatus.SCIENTIFIC_INFEASIBLE
    assert called == [True]


def test_missing_declared_runner_output_is_a_model_failure(models_dir):
    """Accepting an undeclared output would hide a broken runnable contract."""
    base = _evaluator_context(models_dir)
    context = EvaluationContext(
        **{**base.__dict__, "outcome_functions": {"value": lambda outputs: float(outputs["z"][0])}}
    )

    result = execute_action(
        EvaluationAction.component("eval-000071", "transform", {}),
        context,
        runner=lambda component, inputs: {"z": inputs["x"]},
    )

    assert result.status is EvaluationStatus.MODEL_FAILURE


def test_artifacts_are_hashed_and_identical_replays_reuse_them(models_dir, tmp_path):
    """Overwriting an existing artifact without comparing bytes must fail this test."""
    base = _evaluator_context(models_dir)
    context = EvaluationContext(**{**base.__dict__, "artifact_dir": tmp_path / "artifacts"})
    action = EvaluationAction.component("eval-000008", "transform", {})

    def runner(component, inputs):
        return {"y": inputs["x"]}

    first = execute_action(action, context, runner=runner)
    second = execute_action(action, context, runner=runner)

    artifact = Path(first.artifacts[action.id])
    assert artifact.is_absolute() and artifact.exists()
    assert first.artifact_sha256[action.id] == hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert second.artifact_sha256 == first.artifact_sha256


def test_artifact_replay_refuses_to_overwrite_different_bytes(models_dir, tmp_path):
    """Replacing a durable action artifact with changed model output must fail closed."""
    base = _evaluator_context(models_dir)
    context = EvaluationContext(**{**base.__dict__, "artifact_dir": tmp_path / "artifacts"})
    action = EvaluationAction.component("eval-000081", "transform", {})
    values = iter((1.0, 2.0))

    def changing_runner(component, inputs):
        return {"y": np.array([next(values)])}

    first = execute_action(action, context, runner=changing_runner)
    second = execute_action(action, context, runner=changing_runner)

    assert first.status is EvaluationStatus.SUCCESS
    assert second.status is EvaluationStatus.INFRASTRUCTURE_FAILURE


@pytest.mark.parametrize("state", ("unregistered", "missing", "mismatched"))
def test_unverified_parent_artifact_never_calls_component_runner(models_dir, tmp_path, state):
    """Calling a component before parent verification must trigger the assertion runner."""
    parent = tmp_path / "parent.npz"
    np.savez(parent, x=np.array([9.0]))
    digest = hashlib.sha256(parent.read_bytes()).hexdigest()
    registry = (
        {}
        if state == "unregistered"
        else {
            "parent": ParentArtifactReference(
                tmp_path / "missing.npz" if state == "missing" else parent,
                "0" * 64 if state == "mismatched" else digest,
            )
        }
    )
    base = _evaluator_context(models_dir)
    context = EvaluationContext(**{**base.__dict__, "parent_artifacts": registry})

    result = execute_action(
        EvaluationAction.component("eval-000009", "transform", {}, parent_artifact_ids=("parent",)),
        context,
        runner=lambda component, inputs: (_ for _ in ()).throw(AssertionError("runner was called")),
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE


def test_verified_parent_arrays_load_but_explicit_sources_win_collisions(models_dir, tmp_path):
    """Reversing the documented source-over-parent collision rule changes this outcome."""
    parent = tmp_path / "parent.npz"
    np.savez(parent, x=np.array([99.0]))
    base = _evaluator_context(models_dir)
    context = EvaluationContext(
        **{
            **base.__dict__,
            "source_arrays": {"x": np.array([2.0])},
            "observed": {"y": np.array([2.0])},
            "outcome_functions": {"value": lambda outputs: float(outputs["y"][0])},
            "parent_artifacts": {
                "parent": ParentArtifactReference(
                    parent, hashlib.sha256(parent.read_bytes()).hexdigest()
                )
            },
        }
    )

    result = execute_action(
        EvaluationAction.component("eval-000010", "transform", {}, parent_artifact_ids=("parent",)),
        context,
        runner=lambda component, inputs: {"y": inputs["x"]},
    )

    assert result.outcomes == {"value": 2.0}


def test_parent_artifact_is_loaded_from_the_verified_bytes_snapshot(
    models_dir, tmp_path, monkeypatch
):
    """Replacing a file after its bytes are read must not change runner inputs."""
    parent = tmp_path / "parent.npz"
    np.savez(parent, x=np.array([4.0]))
    original = parent.read_bytes()
    base = _evaluator_context(models_dir)
    context = EvaluationContext(
        **{
            **base.__dict__,
            "source_arrays": {},
            "outcome_functions": {"value": lambda outputs: float(outputs["y"][0])},
            "parent_artifacts": {
                "parent": ParentArtifactReference(parent, hashlib.sha256(original).hexdigest())
            },
        }
    )

    def replace_after_read(path, *, max_bytes):
        np.savez(path, x=np.array([99.0]))
        return original

    monkeypatch.setattr(runner_module, "_read_parent_artifact_bytes", replace_after_read)
    result = execute_action(
        EvaluationAction.component("eval-000014", "transform", {}, parent_artifact_ids=("parent",)),
        context,
        runner=lambda component, inputs: {"y": inputs["x"]},
    )

    assert result.status is EvaluationStatus.SUCCESS
    assert result.outcomes == {"value": 4.0}


def test_artifact_action_id_cannot_escape_configured_directory(models_dir, tmp_path):
    """A traversal action ID must not create an artifact beside the configured root."""
    root = tmp_path / "artifacts"
    context = EvaluationContext(**{**_evaluator_context(models_dir).__dict__, "artifact_dir": root})

    result = execute_action(
        EvaluationAction.component("../escaped", "transform", {}),
        context,
        runner=lambda component, inputs: {"y": inputs["x"]},
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE
    assert not (tmp_path / "escaped.npz").exists()


def test_artifact_writer_rejects_existing_symlink_target(models_dir, tmp_path):
    """Replacing a symlink target must not write outside the artifact root."""
    root = tmp_path / "artifacts"
    root.mkdir()
    outside = tmp_path / "outside.npz"
    outside.write_bytes(b"unchanged")
    (root / "eval-000015.npz").symlink_to(outside)
    context = EvaluationContext(**{**_evaluator_context(models_dir).__dict__, "artifact_dir": root})

    result = execute_action(
        EvaluationAction.component("eval-000015", "transform", {}),
        context,
        runner=lambda component, inputs: {"y": inputs["x"]},
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE
    assert outside.read_bytes() == b"unchanged"


def test_artifact_temp_symlink_substitution_cannot_write_outside_root(
    models_dir, tmp_path, monkeypatch
):
    """Replacing the generated temp name with a symlink must abort finalization."""
    root = tmp_path / "artifacts"
    outside = tmp_path / "outside.npz"
    outside.write_bytes(b"unchanged")
    create_temp = runner_module._create_artifact_temp

    def substituted_temp(directory, artifact_id):
        descriptor, path = create_temp(directory, artifact_id)
        path.unlink()
        path.symlink_to(outside)
        return descriptor, path

    monkeypatch.setattr(runner_module, "_create_artifact_temp", substituted_temp)
    context = EvaluationContext(**{**_evaluator_context(models_dir).__dict__, "artifact_dir": root})

    result = execute_action(
        EvaluationAction.component("eval-000019", "transform", {}),
        context,
        runner=lambda component, inputs: {"y": inputs["x"]},
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE
    assert outside.read_bytes() == b"unchanged"
    assert not list(root.glob("*.tmp"))


def test_artifact_collision_cleans_secure_temporary_file(models_dir, tmp_path):
    """A different existing artifact must fail without leaving a temporary file behind."""
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "eval-000020.npz").write_bytes(b"different bytes")
    context = EvaluationContext(**{**_evaluator_context(models_dir).__dict__, "artifact_dir": root})

    result = execute_action(
        EvaluationAction.component("eval-000020", "transform", {}),
        context,
        runner=lambda component, inputs: {"y": inputs["x"]},
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE
    assert not list(root.glob("*.tmp"))


@pytest.mark.parametrize(
    "clock",
    (
        lambda: (_ for _ in ()).throw(RuntimeError("clock unavailable")),
        lambda: float("nan"),
        lambda: 1.0 + 0.0j,
    ),
)
def test_clock_start_failures_return_infrastructure_results(models_dir, clock):
    """A clock exception or nonfinite start value must not escape execute_action."""
    result = execute_action(
        EvaluationAction.component("eval-000016", "transform", {}),
        _evaluator_context(models_dir),
        runner=lambda component, inputs: {"y": inputs["x"]},
        clock=clock,
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE
    assert result.evaluator_seconds == 0.0
    assert result.cost == 0.0


def test_invalid_completion_clock_is_not_called_again_during_failure_construction(models_dir):
    """Retrying a broken completion clock would call this test clock a third time."""
    values = iter((1.0, 1.0))
    calls = 0

    def clock():
        nonlocal calls
        calls += 1
        if calls > 2:
            raise AssertionError("clock retried")
        return next(values)

    result = execute_action(
        EvaluationAction.component("eval-000017", "transform", {}),
        _evaluator_context(models_dir),
        runner=lambda component, inputs: {"y": inputs["x"]},
        clock=clock,
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE
    assert result.evaluator_seconds == 0.0
    assert result.cost == 0.0
    assert calls == 2


def test_finished_clock_interval_is_cached_when_cost_overflows(models_dir):
    """A cost overflow must retain timing and never request a third clock value."""
    calls = 0

    def clock():
        nonlocal calls
        calls += 1
        if calls > 2:
            raise AssertionError("clock retried")
        return (1.0, 3.0)[calls - 1]

    context = EvaluationContext(
        **{
            **_evaluator_context(models_dir).__dict__,
            "cost_per_evaluator_second": float.fromhex("0x1.fffffffffffffp+1023"),
        }
    )
    result = execute_action(
        EvaluationAction.component("eval-000021", "transform", {}),
        context,
        runner=lambda component, inputs: {"y": inputs["x"]},
        clock=clock,
    )

    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE
    assert result.evaluator_seconds == 2.0
    assert result.cost == 0.0
    assert calls == 2


def _parent_context(models_dir, parent, digest, **limits):
    base = _evaluator_context(models_dir)
    return EvaluationContext(
        **{
            **base.__dict__,
            "source_arrays": {},
            "parent_artifacts": {"parent": ParentArtifactReference(parent, digest)},
            **limits,
        }
    )


def _assert_parent_limit_rejects_before_runner(models_dir, context):
    result = execute_action(
        EvaluationAction.component("eval-000022", "transform", {}, parent_artifact_ids=("parent",)),
        context,
        runner=lambda component, inputs: (_ for _ in ()).throw(AssertionError("runner was called")),
    )
    assert result.status is EvaluationStatus.INFRASTRUCTURE_FAILURE


def test_parent_artifact_compressed_byte_limit_rejects_before_reading_arrays(models_dir, tmp_path):
    """Oversized parent bytes must be rejected before any runner invocation."""
    parent = tmp_path / "parent.npz"
    np.savez(parent, x=np.arange(20.0))
    context = _parent_context(
        models_dir,
        parent,
        hashlib.sha256(parent.read_bytes()).hexdigest(),
        max_parent_artifact_bytes=10,
    )

    _assert_parent_limit_rejects_before_runner(models_dir, context)


def test_parent_artifact_member_count_limit_rejects_before_runner(models_dir, tmp_path):
    """An archive with too many members must not reach the runner."""
    parent = tmp_path / "parent.npz"
    np.savez(parent, x=np.array([1.0]), extra=np.array([2.0]))
    context = _parent_context(
        models_dir,
        parent,
        hashlib.sha256(parent.read_bytes()).hexdigest(),
        max_parent_artifact_members=1,
    )

    _assert_parent_limit_rejects_before_runner(models_dir, context)


def test_parent_artifact_uncompressed_member_limit_rejects_zip_bomb(models_dir, tmp_path):
    """A highly compressed large member must be rejected from ZIP metadata."""
    parent = tmp_path / "parent.npz"
    np.savez_compressed(parent, x=np.zeros(10_000))
    context = _parent_context(
        models_dir,
        parent,
        hashlib.sha256(parent.read_bytes()).hexdigest(),
        max_parent_artifact_bytes=10_000,
        max_parent_artifact_member_bytes=100,
    )

    _assert_parent_limit_rejects_before_runner(models_dir, context)


def test_parent_artifact_declared_huge_shape_rejects_before_allocation(models_dir, tmp_path):
    """A tiny NPY header declaring a huge array must never allocate that array."""
    header = io.BytesIO()
    np.lib.format.write_array_header_1_0(
        header,
        {"descr": "<f8", "fortran_order": False, "shape": (1_000_000_000,)},
    )
    parent = tmp_path / "parent.npz"
    with zipfile.ZipFile(parent, "w") as archive:
        archive.writestr("x.npy", header.getvalue())
    context = _parent_context(
        models_dir,
        parent,
        hashlib.sha256(parent.read_bytes()).hexdigest(),
        max_parent_artifact_member_bytes=1_000,
        max_parent_artifact_total_bytes=1_000,
    )

    _assert_parent_limit_rejects_before_runner(models_dir, context)


@pytest.mark.parametrize(
    ("declared", "returned"),
    (
        (["y", "y"], {"y": np.array([1.0])}),
        ([""], {"": np.array([1.0])}),
        (["y"], {"y": np.array([1.0]), "extra": np.array([1.0])}),
    ),
)
def test_declared_outputs_must_be_unique_nonempty_and_exact(models_dir, declared, returned):
    """Malformed declarations or extra model outputs must not be accepted."""
    system = _system(models_dir)
    system.get_component("transform").metadata["runnable"]["outputs"] = declared
    context = EvaluationContext(
        system=system,
        alternatives={},
        source_arrays={"source.x": np.array([1.0])},
        observed={},
        outcome_functions={"value": lambda outputs: 1.0},
        cost_unit="cpu_second",
    )

    result = execute_action(
        EvaluationAction.component("eval-000018", "transform", {}),
        context,
        runner=lambda component, inputs: returned,
    )

    assert result.status is EvaluationStatus.MODEL_FAILURE


# --------------------------------------------------------------------------- #
# Candidate round-trip
# --------------------------------------------------------------------------- #


class TestCandidates:
    def test_to_component_carries_provenance(self):
        c = Candidate(
            name="transform",
            model_type="transform",
            rationale="identity beats doubling",
            sources=["https://example.org/paper"],
            metadata={"runnable": {"kind": "python"}},
        )
        comp = c.to_component()
        assert comp.metadata["rationale"] == "identity beats doubling"
        assert comp.metadata["sources"] == ["https://example.org/paper"]
        assert comp.metadata["runnable"]["kind"] == "python"

    def test_yaml_round_trip(self, tmp_path):
        cands = [
            Candidate(name="a", rationale="r", sources=["s1"], metadata={"k": 1}),
            Candidate(name="b"),
        ]
        path = tmp_path / "cands.yaml"
        save_candidates(path, cands, target="a")
        loaded = load_candidates(path)
        assert [c.name for c in loaded] == ["a", "b"]
        assert loaded[0].rationale == "r"
        assert loaded[0].sources == ["s1"]


# --------------------------------------------------------------------------- #
# ExperimentTree
# --------------------------------------------------------------------------- #


class TestExperimentTree:
    def _tree(self):
        tree = ExperimentTree(ExperimentNode(id="baseline", score=0.2, status="baseline"))
        tree.add_child(
            "baseline",
            ExperimentNode(id="e1", score=0.5, status="kept", candidate="c1"),
        )
        tree.add_child(
            "e1",
            ExperimentNode(id="e2", score=0.3, status="reverted", candidate="c2"),
        )
        return tree

    def test_best_is_highest_kept(self):
        tree = self._tree()
        assert tree.best().id == "e1"

    def test_grows_down_path(self):
        tree = self._tree()
        path = [n.id for n in tree.path_to_best()]
        assert path == ["baseline", "e1"]

    def test_jsonl_round_trip(self, tmp_path):
        tree = self._tree()
        path = tmp_path / "tree.jsonl"
        tree.to_jsonl(path)
        restored = ExperimentTree.from_jsonl(path)
        assert restored.best().id == "e1"
        assert set(restored.nodes) == {"baseline", "e1", "e2"}

    def test_jsonl_preserves_optional_evaluation_links_and_defaults_old_rows(self, tmp_path):
        """Dropping action/result links or requiring them in old logs must fail this test."""
        path = tmp_path / "tree.jsonl"
        path.write_text(
            "\n".join(
                (
                    '{"id": "baseline", "status": "baseline"}',
                    '{"id": "child", "parent_id": "baseline", "action_id": "eval-000001", '
                    '"result_status": "success"}',
                )
            )
            + "\n"
        )

        restored = ExperimentTree.from_jsonl(path)

        assert restored.nodes["baseline"].action_id is None
        assert restored.nodes["baseline"].result_status is None
        assert restored.nodes["child"].action_id == "eval-000001"
        assert restored.nodes["child"].result_status == "success"
        assert "action_id" in restored.nodes["child"].to_dict()

    def test_root_requires_no_parent(self):
        with pytest.raises(ValueError):
            ExperimentTree(ExperimentNode(id="x", parent_id="y"))


# --------------------------------------------------------------------------- #
# auto_improve end-to-end (the core integration test)
# --------------------------------------------------------------------------- #


class TestAutoImprove:
    def test_baseline_plus_improving_candidate(self, models_dir, tmp_path):
        system = _system(models_dir)
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        observed = x.copy()  # truth == identity, so the good model is perfect
        run_chain = build_feedforward_runner(system, {"source.x": x})

        good = Candidate(
            name="transform",
            model_type="transform",
            description="identity model",
            rationale="matches observed exactly",
            sources=["https://example.org/identity"],
            metadata={
                "runnable": {
                    "kind": "python",
                    "entry": "tmodels:identity",
                    "sys_path": str(models_dir),
                    "inputs": ["x"],
                    "outputs": ["y"],
                }
            },
        )

        tree = auto_improve(
            system,
            run_chain,
            observed,
            validate_output="transform.y",
            candidates=[good],
            metrics=["rmse", "nse", "kge"],
            thresholds={"nse": 0.5, "kge": 0.5},
            workdir=tmp_path,
            slug="synthetic",
        )

        # Tree has baseline + one child; the child was kept and is best.
        assert len(tree.nodes) == 2
        best = tree.best()
        assert best.candidate == "transform"
        assert best.status == "kept"
        assert best.score > tree.nodes["baseline"].score
        # identity model should give near-perfect NSE
        assert best.metrics["nse"] > 0.99

        # Artifacts written with feynman-compatible names.
        assert (tmp_path / "autoresearch.md").exists()
        assert (tmp_path / "autoresearch.jsonl").exists()
        assert (tmp_path / "CHANGELOG.md").exists()

    def test_report_and_provenance_written(self, models_dir, tmp_path):
        from autoengineering.research.provenance import write_report

        system = _system(models_dir)
        x = np.arange(1.0, 11.0)
        run_chain = build_feedforward_runner(system, {"source.x": x})
        good = Candidate(
            name="transform",
            metadata={
                "runnable": {
                    "kind": "python",
                    "entry": "tmodels:identity",
                    "sys_path": str(models_dir),
                    "inputs": ["x"],
                    "outputs": ["y"],
                }
            },
            sources=["https://example.org/ref"],
        )
        tree = auto_improve(
            system,
            run_chain,
            x.copy(),
            validate_output="transform.y",
            candidates=[good],
            workdir=tmp_path,
            slug="synthetic",
        )
        report_path, prov_path = write_report(
            tree, system, "synthetic", tmp_path, now="2026-07-22 00:00"
        )
        report = report_path.read_text()
        prov = prov_path.read_text()
        assert "## Evidence" in report
        assert "| Metric | Baseline | Best | Δ |" in report
        assert "https://example.org/ref" in report
        assert "Verification:" in prov

    def test_failed_candidate_does_not_kill_loop(self, models_dir, tmp_path):
        system = _system(models_dir)
        x = np.arange(1.0, 6.0)
        run_chain = build_feedforward_runner(system, {"source.x": x})

        bad = Candidate(
            name="transform",
            metadata={
                "runnable": {
                    "kind": "python",
                    "entry": "tmodels:does_not_exist",
                    "sys_path": str(models_dir),
                    "inputs": ["x"],
                    "outputs": ["y"],
                }
            },
        )
        good = Candidate(
            name="transform",
            metadata={
                "runnable": {
                    "kind": "python",
                    "entry": "tmodels:identity",
                    "sys_path": str(models_dir),
                    "inputs": ["x"],
                    "outputs": ["y"],
                }
            },
        )
        tree = auto_improve(
            system,
            run_chain,
            x.copy(),
            validate_output="transform.y",
            candidates=[bad, good],
            workdir=tmp_path,
            slug="synthetic",
        )
        statuses = [n.status for n in tree.nodes.values()]
        # baseline + one failed node + one kept node; loop survived the failure
        assert len(tree.nodes) == 3
        assert "failed" in statuses
        assert tree.best().status == "kept"

    def test_target_stops_early(self, models_dir, tmp_path):
        system = _system(models_dir)
        x = np.arange(1.0, 6.0)
        run_chain = build_feedforward_runner(system, {"source.x": x})
        good = Candidate(
            name="transform",
            metadata={
                "runnable": {
                    "kind": "python",
                    "entry": "tmodels:identity",
                    "sys_path": str(models_dir),
                    "inputs": ["x"],
                    "outputs": ["y"],
                }
            },
        )
        # Two identical good candidates; target met after the first.
        tree = auto_improve(
            system,
            run_chain,
            x.copy(),
            validate_output="transform.y",
            candidates=[good, good],
            metrics=["rmse", "nse"],
            target={"nse": 0.9},
            workdir=tmp_path,
            slug="synthetic",
        )
        # baseline + only the first candidate evaluated
        assert len(tree.nodes) == 2
