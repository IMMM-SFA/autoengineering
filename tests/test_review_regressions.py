"""Regression tests for scientific-review execution and retention defects."""

from __future__ import annotations

import numpy as np
import pytest

from autoengineering.execute.swap import swap_component
from autoengineering.research import Candidate, auto_improve
from autoengineering.research.loop import _target_met
from autoengineering.research.runner import build_feedforward_runner
from autoengineering.system import Component, System
from autoengineering.validate.compare import METRICS, ValidationResult, validate_arrays


def _parallel_system() -> System:
    system = System("parallel")
    system.add_component("source", outputs={"x": "array", "z": "array"})
    system.add_component(
        "model",
        inputs={"x": "array", "z": "array"},
        outputs={"y": "array"},
        metadata={"runnable": {"inputs": ["x", "z"], "outputs": ["y"]}},
    )
    system.connect("source", "model", "x", "x")
    system.connect("source", "model", "z", "z")
    return system


def test_parallel_ports_survive_roundtrip_swap_and_execution(tmp_path):
    system = _parallel_system()
    path = tmp_path / "system.yaml"
    system.to_yaml(path)
    restored = System.from_yaml(path)
    assert restored.connections == system.connections
    assert len(restored.connections) == 2
    assert restored.topological_order() == ["source", "model"]
    assert restored.direct_upstream("model") == ["source"]
    assert restored.downstream_of("source") == ["model"]
    assert restored.to_mermaid().count("-->") == 2
    assert "**Connections**: 2" in restored.describe()
    swapped = swap_component(restored, "model", restored.get_component("model"))
    assert swapped.connections == restored.connections
    graph = restored.to_networkx()
    assert graph.number_of_edges("source", "model") == 2
    graph.remove_node("model")
    assert "model" in restored.component_names

    def add(component, inputs):
        return {"y": inputs["x"] + inputs["z"]}

    run = build_feedforward_runner(
        restored, {"source.x": np.array([1.0]), "source.z": np.array([2.0])}, runner=add
    )
    np.testing.assert_array_equal(run(swapped)["model.y"], [3.0])


def test_reconnecting_identical_port_pair_updates_without_duplication():
    system = _parallel_system()
    system.connect("source", "model", "x", "x", description="updated")
    assert len(system.connections) == 2
    assert system.connections[0]["description"] == "updated"


@pytest.mark.parametrize(
    ("observed", "simulated"),
    [
        (np.array([1.0, 2.0]), np.array([[1.0], [2.0]])),
        (np.array([1.0, 2.0]), np.array([1.0])),
        (np.array([]), np.array([])),
        (np.array([1.0, np.nan]), np.array([1.0, 2.0])),
        (np.array([1.0, 2.0]), np.array([1.0, np.inf])),
        (np.array([[1.0, 2.0]]), np.array([[1.0, 2.0]])),
        (np.array([1 + 1j]), np.array([1 + 1j])),
    ],
)
def test_validation_rejects_invalid_array_contract(observed, simulated):
    with pytest.raises(ValueError):
        validate_arrays("model", observed, simulated, metrics=["rmse"])


@pytest.mark.parametrize("metric", list(METRICS))
def test_direct_metrics_reject_broadcasting(metric):
    with pytest.raises(ValueError):
        METRICS[metric](np.array([1.0, 2.0]), np.array([[1.0], [2.0]]))


def test_validation_rejects_undefined_metric():
    with pytest.raises(ValueError, match="nse"):
        validate_arrays("model", np.ones(3), np.ones(3), metrics=["nse"])


@pytest.mark.parametrize("threshold", [np.nan, np.inf, -np.inf])
def test_validation_rejects_nonfinite_threshold(threshold):
    with pytest.raises(ValueError):
        validate_arrays(
            "model",
            np.array([1.0, 2.0]),
            np.array([1.0, 2.0]),
            metrics=["rmse"],
            thresholds={"rmse": threshold},
        )


@pytest.mark.parametrize("metric", ["nse", "rmse"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_metric_never_meets_target(metric, value):
    assert not _target_met([ValidationResult("model", metric, value)], {metric: 0.9})


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_target_is_rejected(value):
    with pytest.raises(ValueError):
        _target_met([ValidationResult("model", "rmse", 0.0)], {"rmse": value})


def test_trial_inputs_are_isolated_across_runs_and_branches():
    system = System("branches")
    system.add_component("source", outputs={"x": "array"})
    for name in ("mutating", "reader"):
        system.add_component(
            name, outputs={"y": "array"}, metadata={"runnable": {"inputs": ["x"], "outputs": ["y"]}}
        )
        system.connect("source", name, "x", "x")
    source = np.array([1.0, 2.0])

    def runner(component, inputs):
        if component.name == "mutating":
            inputs["x"] *= 2
        return {"y": inputs["x"]}

    run = build_feedforward_runner(system, {"source.x": source}, runner=runner)
    first = run(system)
    first["source.x"][:] = 100
    second = run(system)
    np.testing.assert_array_equal(first["mutating.y"], [2.0, 4.0])
    np.testing.assert_array_equal(first["reader.y"], [1.0, 2.0])
    np.testing.assert_array_equal(second["mutating.y"], [2.0, 4.0])
    np.testing.assert_array_equal(second["reader.y"], [1.0, 2.0])
    np.testing.assert_array_equal(source, [1.0, 2.0])


def test_trial_component_state_is_isolated_from_caller_and_later_runs():
    system = System("state")
    system.add_component(
        "model", outputs={"y": "array"}, metadata={"runnable": {"outputs": ["y"]}, "count": 0}
    )

    def runner(component, inputs):
        component.metadata["count"] += 1
        return {"y": np.array([component.metadata["count"]], dtype=float)}

    run = build_feedforward_runner(system, {}, runner=runner)
    np.testing.assert_array_equal(run(system)["model.y"], [1.0])
    np.testing.assert_array_equal(run(system)["model.y"], [1.0])
    assert system.get_component("model").metadata["count"] == 0


def test_python_runner_copies_inputs_and_nested_parameters(monkeypatch):
    from autoengineering.research import runner as runner_module

    def mutate(values, settings):
        values *= 2
        settings["calls"] += 1
        return values

    monkeypatch.setattr(runner_module, "_load_callable", lambda *args: mutate)
    component = Component(
        "model",
        metadata={
            "runnable": {
                "entry": "unused:entry",
                "inputs": ["x"],
                "outputs": ["y"],
                "params": {"settings": {"calls": 0}},
            }
        },
    )
    values = np.array([1.0, 2.0])
    first = runner_module.run_component(component, {"x": values})
    second = runner_module.run_component(component, {"x": values})
    np.testing.assert_array_equal(first["y"], [2.0, 4.0])
    np.testing.assert_array_equal(second["y"], [2.0, 4.0])
    np.testing.assert_array_equal(values, [1.0, 2.0])
    assert component.metadata["runnable"]["params"]["settings"]["calls"] == 0


def test_feedforward_sources_are_snapshotted_at_construction():
    system = System("snapshot")
    system.add_component("source", outputs={"x": "array"})
    values = np.array([1.0, 2.0])
    sources = {"source.x": values}
    run = build_feedforward_runner(system, sources)
    values[:] = 99
    sources.clear()
    np.testing.assert_array_equal(run(system)["source.x"], [1.0, 2.0])


def test_auto_improve_isolates_custom_runner_mutations(tmp_path):
    system = System("custom")
    system.add_component("model", metadata={"count": 0})
    observed = np.array([1.0, 2.0, 3.0])
    counts = []

    def run_chain(trial):
        count = trial.get_component("model").metadata["count"]
        counts.append(count)
        trial.get_component("model").metadata["count"] += 1
        return {"model.y": observed.copy()}

    tree = auto_improve(
        system,
        run_chain,
        observed,
        validate_output="model.y",
        candidates=[Candidate("model", metadata={"count": 0})],
        metrics=["rmse"],
        workdir=tmp_path,
    )
    assert counts == [0, 0]
    assert system.get_component("model").metadata["count"] == 0
    assert tree.best().score == 0.0


def test_rejected_target_does_not_stop_search(tmp_path):
    system = System("targets")
    system.add_component("model", metadata={"variant": "baseline"})
    observed = np.array([1.0, 2.0, 3.0])
    outputs = {
        "baseline": 2 * observed,
        "rejected": observed + np.array([0.1, -0.1, 0.1]),
        "good": observed,
    }
    seen = []

    def run_chain(trial):
        variant = trial.get_component("model").metadata["variant"]
        seen.append(variant)
        return {"model.y": outputs[variant]}

    tree = auto_improve(
        system,
        run_chain,
        observed,
        validate_output="model.y",
        candidates=[
            Candidate("model", metadata={"variant": name}) for name in ("rejected", "good")
        ],
        metrics=["rmse", "correlation"],
        target={"rmse": 0.2},
        workdir=tmp_path,
    )
    assert seen == ["baseline", "rejected", "good"]
    assert all(node.status == "reverted" for node in tree.children_of("baseline"))
    assert tree.best().metrics["rmse"] > 0.2
    assert "stopping early" not in (tmp_path / "autoresearch.md").read_text()


def test_retained_target_stops_before_later_candidate(tmp_path):
    system = System("retained-target")
    system.add_component("model", metadata={"variant": "baseline"})
    observed = np.array([1.0, 2.0, 3.0])
    seen = []

    def run_chain(trial):
        variant = trial.get_component("model").metadata["variant"]
        seen.append(variant)
        return {"model.y": observed + (1.0 if variant == "baseline" else 0.0)}

    tree = auto_improve(
        system,
        run_chain,
        observed,
        validate_output="model.y",
        candidates=[Candidate("model", metadata={"variant": name}) for name in ("good", "later")],
        metrics=["rmse"],
        target={"rmse": 0.2},
        workdir=tmp_path,
    )
    assert seen == ["baseline", "good"]
    assert tree.best().status == "kept"
    assert tree.best().metrics["rmse"] == 0.0


def test_invalid_trial_is_failed_and_search_continues(tmp_path):
    system = System("invalid-trial")
    system.add_component("model", metadata={"variant": "baseline"})
    observed = np.array([1.0, 2.0, 3.0])

    def run_chain(trial):
        variant = trial.get_component("model").metadata["variant"]
        if variant == "invalid":
            return {"model.y": np.full(3, np.nan)}
        return {"model.y": observed + (1.0 if variant == "baseline" else 0.0)}

    tree = auto_improve(
        system,
        run_chain,
        observed,
        validate_output="model.y",
        candidates=[Candidate("model", metadata={"variant": name}) for name in ("invalid", "good")],
        metrics=["rmse"],
        target={"rmse": 0.2},
        workdir=tmp_path,
    )
    children = tree.children_of("baseline")
    assert [node.status for node in children] == ["failed", "kept"]
    assert "finite" in children[0].notes
    assert tree.best().metrics["rmse"] == 0.0


def test_invalid_baseline_cannot_be_reported_as_meeting_target(tmp_path):
    system = System("invalid-baseline")
    system.add_component("model")
    with pytest.raises(ValueError, match="finite"):
        auto_improve(
            system,
            lambda trial: {"model.y": np.full(3, np.nan)},
            np.array([1.0, 2.0, 3.0]),
            validate_output="model.y",
            metrics=["rmse"],
            target={"rmse": 0.2},
            workdir=tmp_path,
        )
    assert not (tmp_path / "autoresearch.md").exists()


def test_integer_metric_arithmetic_does_not_overflow():
    value = METRICS["rmse"](np.array([0], dtype=np.int32), np.array([100000], dtype=np.int32))
    assert value == 100000.0


def test_swap_copies_replacement_and_original_components():
    system = _parallel_system()
    system.get_component("source").metadata["nested"] = {"value": 1}
    replacement = Component("model", metadata={"nested": {"value": 2}})
    replacement.add_output("y")
    swapped = swap_component(system, "model", replacement)
    replacement.metadata["nested"]["value"] = 99
    replacement.outputs[0].name = "changed"
    swapped.get_component("source").metadata["nested"]["value"] = 99
    assert swapped.get_component("model").metadata["nested"]["value"] == 2
    assert swapped.get_component("model").outputs[0].name == "y"
    assert system.get_component("source").metadata["nested"]["value"] == 1


def test_swap_rejects_occupied_name_without_mutating_system():
    system = _parallel_system()
    connections = system.connections
    with pytest.raises(ValueError, match="already exists"):
        swap_component(system, "model", Component("source"))
    assert system.component_names == ["source", "model"]
    assert system.connections == connections


def test_swap_can_rename_to_unoccupied_name_and_preserve_all_ports():
    system = _parallel_system()
    swapped = swap_component(system, "model", Component("renamed"))
    assert swapped.component_names == ["source", "renamed"]
    assert len(swapped.connections) == 2
    assert all(edge["target"] == "renamed" for edge in swapped.connections)
    assert system.component_names == ["source", "model"]
