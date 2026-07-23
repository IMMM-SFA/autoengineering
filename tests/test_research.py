"""Tests for the research subpackage: runner, candidates, tree, and the loop.

Everything here is synthetic and offline. A tiny two-component chain
(source -> transform) is defined in-process, with candidate transforms written to
a temp module so the python runnable path exercises a real import.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np
import pytest

from autoengineering.research.candidates import (
    Candidate,
    load_candidates,
    save_candidates,
)
from autoengineering.research.experiment import ExperimentNode, ExperimentTree
from autoengineering.research.loop import auto_improve
from autoengineering.research.runner import (
    build_feedforward_runner,
    run_component,
)
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
        tree = ExperimentTree(
            ExperimentNode(id="baseline", score=0.2, status="baseline")
        )
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
