"""Clean-checkout contract for the self-contained optimization example."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
import pytest

from autoengineering.cli import cli
from autoengineering.optimization import (
    CategoricalParameter,
    ContinuousParameter,
    EvaluationAction,
    EvaluationStatus,
    IntegerParameter,
    OptimizationRunSpec,
)
from autoengineering.system.graph import System

_EXAMPLE = Path(__file__).parents[1] / "examples" / "optimization_chain"
_SPECIFICATION = _EXAMPLE / "optimization.yaml"


def _invoke(runner: CliRunner, workdir: Path, *extra: str):
    return runner.invoke(
        cli,
        [
            "optimize",
            "system.yaml",
            str(_SPECIFICATION),
            "--workdir",
            str(workdir),
            "--format",
            "json",
            *extra,
        ],
    )


def test_example_declares_the_mixed_chain_optimum_and_controlled_failure():
    run = OptimizationRunSpec.from_yaml(_SPECIFICATION)
    system_path = run.resolve_system_file("system.yaml", _SPECIFICATION)
    system = System.from_yaml(system_path)
    parameters = run.search_space.parameters

    assert system.topological_order() == [
        "observations",
        "configurable_transform",
        "score",
    ]
    assert tuple(type(parameter) for parameter in parameters) == (
        CategoricalParameter,
        ContinuousParameter,
        IntegerParameter,
        ContinuousParameter,
    )
    assert dict(parameters[-1].active_when) == {"architecture": ("nonlinear",)}
    assert run.input_files == ("input.csv",)

    evaluator = run.load_evaluator_factory(_SPECIFICATION)(system)
    optimum = EvaluationAction.system(
        "analytic-optimum",
        {"architecture": "linear", "gain": 1.25, "stages": 2},
    )
    optimum_result = evaluator(optimum)
    expected = json.loads((_EXAMPLE / "expected-result.json").read_text(encoding="utf-8"))

    assert dict(optimum.config) == expected["known_feasible_optimum"]["config"]
    assert optimum_result.status is EvaluationStatus.SUCCESS
    assert dict(optimum_result.outcomes) == pytest.approx(
        expected["known_feasible_optimum"]["outcomes"]
    )
    assert optimum_result.outcomes["absolute_bias"] <= run.study.constraints[0].threshold

    unstable = EvaluationAction.system(
        "controlled-failure",
        {"architecture": "linear", "gain": 1.8, "stages": 4},
    )
    failure = evaluator(unstable)
    assert failure.status is EvaluationStatus.MODEL_FAILURE
    assert failure.cost == 1.0
    assert "controlled instability" in failure.message


def test_example_runs_bounded_resume_and_reproduces_checked_results(tmp_path):
    runner = CliRunner()
    resumed_directory = tmp_path / "resumed"

    first = _invoke(runner, resumed_directory, "--max-new-evaluations", "3")

    assert first.exit_code == 0, first.output
    first_summary = json.loads(first.output)
    assert first_summary["state"] == "invocation_limit"
    assert first_summary["evaluation_count"] == 3
    ledger_path = resumed_directory / "observations.jsonl"
    ledger_prefix = ledger_path.read_bytes()

    resumed = _invoke(runner, resumed_directory, "--resume")

    assert resumed.exit_code == 0, resumed.output
    resumed_summary = json.loads(resumed.output)
    assert ledger_path.read_bytes().startswith(ledger_prefix)
    expected = json.loads((_EXAMPLE / "expected-result.json").read_text(encoding="utf-8"))
    seeded = expected["seeded_sobol_run"]
    assert resumed_summary["evaluation_count"] == seeded["evaluation_count"]
    assert resumed_summary["state"] == seeded["stop_reason"]
    assert resumed_summary["recommendation"] == seeded["recommendation"]
    assert (
        json.loads((resumed_directory / "recommendation.json").read_text())
        == seeded["recommendation"]
    )
    manifest = json.loads((resumed_directory / "manifest.json").read_text())
    assert "input:input.csv" in manifest["run_identity"]["input_artifact_hashes"]

    fresh_a = tmp_path / "fresh-a"
    fresh_b = tmp_path / "fresh-b"
    first_fresh = _invoke(runner, fresh_a)
    second_fresh = _invoke(runner, fresh_b)

    assert first_fresh.exit_code == 0, first_fresh.output
    assert second_fresh.exit_code == 0, second_fresh.output
    assert (fresh_a / "observations.jsonl").read_bytes() == (
        fresh_b / "observations.jsonl"
    ).read_bytes()
    assert (fresh_a / "recommendation.json").read_bytes() == (
        fresh_b / "recommendation.json"
    ).read_bytes()
    assert json.loads(first_fresh.output)["recommendation"] == seeded["recommendation"]
    assert json.loads(second_fresh.output)["recommendation"] == seeded["recommendation"]
