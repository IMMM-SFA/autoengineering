"""Public CLI construction, execution, and resume contracts."""

from __future__ import annotations

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from click.testing import CliRunner
import pytest

from autoengineering.cli import cli
from autoengineering.optimization import (
    BudgetSpec,
    CategoricalParameter,
    EvaluationAction,
    EvaluationResult,
    IntegerParameter,
    NoiseSpec,
    ObjectiveSpec,
    OptimizationRunSpec,
    OptimizationStudy,
    SearchSpace,
    StudySpec,
)
from autoengineering.system.graph import System


def _write_case(
    directory: Path,
    *,
    policy: str = "random",
    maximum: int | None = 4,
    max_cost: float = 20.0,
    initial_cost: float = 1.0,
    target: float | None = None,
    upper: int = 3,
    single_value: bool = False,
    run_limit: int | None = None,
    evaluator_source: str | None = None,
) -> OptimizationRunSpec:
    system = System("example")
    system.to_yaml(directory / "system.yaml")
    source = (
        evaluator_source
        or """
from autoengineering.optimization import EvaluationResult

def make_evaluator(system):
    def evaluate(action):
        return EvaluationResult.success(
            action.id,
            {"score": float(action.config["x"])},
            {},
            1.0,
            "run",
        )
    return evaluate
""".lstrip()
    )
    (directory / "local_evaluator.py").write_text(source, encoding="utf-8")
    options = {"min_initial": 1, "num_restarts": 1, "raw_samples": 2} if policy == "botorch" else {}
    run = OptimizationRunSpec(
        study=StudySpec(
            name="cli-study",
            objective=ObjectiveSpec("score", "maximize"),
            constraints=(),
            budget=BudgetSpec(
                max_cost,
                "run",
                max_evaluations=maximum,
                initial_cost_estimate=initial_cost,
            ),
            noise=NoiseSpec(),
            backend="system",
            seed=19,
        ),
        search_space=SearchSpace(
            (CategoricalParameter("x", (0,)) if single_value else IntegerParameter("x", 0, upper),)
        ),
        policy=policy,
        policy_options=options,
        evaluator_factory="local_evaluator:make_evaluator",
        target_value=target,
        max_new_evaluations=run_limit,
    )
    run.to_yaml(directory / "optimization.yaml")
    return run


def _invoke(
    runner: CliRunner,
    workdir: str,
    *extra: str,
):
    return runner.invoke(
        cli,
        [
            "optimize",
            "system.yaml",
            "optimization.yaml",
            "--workdir",
            workdir,
            "--format",
            "json",
            *extra,
        ],
    )


@pytest.mark.parametrize("policy", ("random", "sobol"))
def test_optimize_runs_public_baseline_policies_with_stable_json(policy):
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), policy=policy, maximum=2)

        result = _invoke(runner, "study")

        assert result.exit_code == 0, result.output
        summary = json.loads(result.output)
        assert summary["state"] == "max_evaluations"
        assert summary["evaluation_count"] == 2
        assert summary["new_evaluation_count"] == 2
        assert summary["total_evaluator_cost"] == 2.0
        assert summary["cost_unit"] == "run"
        assert summary["status_counts"] == {"success": 2}
        assert summary["recommendation"]["feasible"] is True


def test_bounded_invocation_resumes_exact_state_and_is_seed_reproducible():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd())

        first = _invoke(runner, "study", "--max-new-evaluations", "1")

        assert first.exit_code == 0, first.output
        first_summary = json.loads(first.output)
        assert first_summary["state"] == "invocation_limit"
        ledger_path = Path("study/observations.jsonl")
        first_ledger = ledger_path.read_bytes()
        first_identity = json.loads(Path("study/manifest.json").read_text())["run_identity"]

        second = _invoke(
            runner,
            "study",
            "--resume",
            "--max-new-evaluations",
            "1",
        )

        assert second.exit_code == 0, second.output
        second_summary = json.loads(second.output)
        assert second_summary["state"] == "invocation_limit"
        assert second_summary["evaluation_count"] == 2
        assert second_summary["new_evaluation_count"] == 1
        assert ledger_path.read_bytes().startswith(first_ledger)
        second_identity = json.loads(Path("study/manifest.json").read_text())["run_identity"]
        assert second_identity["start_timestamp"] == first_identity["start_timestamp"]

        third = _invoke(runner, "repeated", "--max-new-evaluations", "2")
        assert third.exit_code == 0, third.output
        repeated = Path("repeated/observations.jsonl").read_text().splitlines()
        resumed = ledger_path.read_text().splitlines()
        assert [json.loads(line)["action"] for line in repeated] == [
            json.loads(line)["action"] for line in resumed
        ]
        assert json.loads(third.output)["recommendation"] == second_summary["recommendation"]


def test_cli_limit_overrides_the_run_limit_and_zero_is_nonterminal():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), run_limit=1)

        configured = _invoke(runner, "configured")
        overridden = _invoke(runner, "overridden", "--max-new-evaluations", "2")
        zero = _invoke(runner, "zero", "--max-new-evaluations", "0")

        assert configured.exit_code == 0, configured.output
        assert json.loads(configured.output)["evaluation_count"] == 1
        assert overridden.exit_code == 0, overridden.output
        assert json.loads(overridden.output)["evaluation_count"] == 2
        assert zero.exit_code == 0, zero.output
        zero_summary = json.loads(zero.output)
        assert zero_summary["state"] == "invocation_limit"
        assert zero_summary["evaluation_count"] == 0
        assert zero_summary["recommendation"]["feasible"] is False


def test_system_path_is_resolved_relative_to_the_run_specification():
    runner = CliRunner()
    with runner.isolated_filesystem():
        configuration = Path("configuration")
        configuration.mkdir()
        _write_case(configuration, maximum=1)

        result = runner.invoke(
            cli,
            [
                "optimize",
                "system.yaml",
                "configuration/optimization.yaml",
                "--workdir",
                "study",
                "--format",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["evaluation_count"] == 1


def test_cli_summary_uses_one_locked_snapshot_and_its_own_completed_count(monkeypatch):
    runner = CliRunner()
    original = OptimizationStudy.run_result

    def append_after_snapshot(study, *, max_new_evaluations=None):
        snapshot = original(study, max_new_evaluations=max_new_evaluations)
        observed = int(snapshot.entries[-1][0].config["x"])
        action = EvaluationAction.system(
            "eval-999999",
            {"x": (observed + 1) % 4},
            suggested_by="concurrent-test",
        )
        study.ledger.append(
            action,
            EvaluationResult.success(action.id, {"score": 99.0}, {}, 1.0, "run"),
        )
        return snapshot

    monkeypatch.setattr(OptimizationStudy, "run_result", append_after_snapshot)
    with runner.isolated_filesystem():
        _write_case(Path.cwd())

        result = _invoke(runner, "study", "--max-new-evaluations", "1")

        assert result.exit_code == 0, result.output
        summary = json.loads(result.output)
        assert len(Path("study/observations.jsonl").read_text().splitlines()) == 2
        assert summary["evaluation_count"] == 1
        assert summary["new_evaluation_count"] == 1
        assert summary["recommendation"]["outcomes"] != {"score": 99.0}


def test_optimize_requires_explicit_new_or_resume_intent_without_mutation():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd())
        Path("occupied").mkdir()
        marker = Path("occupied/user.txt")
        marker.write_text("keep", encoding="utf-8")

        occupied = _invoke(runner, "occupied")
        Path("empty").mkdir()
        empty_resume = _invoke(runner, "empty", "--resume")
        absent_resume = _invoke(runner, "absent", "--resume")
        Path("actual").mkdir()
        Path("linked").symlink_to("actual", target_is_directory=True)
        linked = _invoke(runner, "linked")
        nested_linked = _invoke(runner, "linked/study")

        assert occupied.exit_code != 0
        assert "not empty" in occupied.output
        assert marker.read_text(encoding="utf-8") == "keep"
        assert empty_resume.exit_code != 0
        assert "recognizable" in empty_resume.output
        assert absent_resume.exit_code != 0
        assert "existing" in absent_resume.output
        assert linked.exit_code != 0
        assert "symlink" in linked.output
        assert nested_linked.exit_code != 0
        assert "symlink" in nested_linked.output
        assert not Path("actual/study").exists()

        Path("marker-only").mkdir()
        Path("marker-only/manifest.json").write_text("{}\n", encoding="utf-8")
        marker_only = _invoke(runner, "marker-only", "--resume")
        assert marker_only.exit_code != 0
        assert sorted(path.name for path in Path("marker-only").iterdir()) == ["manifest.json"]

        Path("malformed").mkdir()
        Path("malformed/manifest.json").write_text("{}\n", encoding="utf-8")
        Path("malformed/observations.jsonl").write_bytes(b"")
        malformed = _invoke(runner, "malformed", "--resume")
        assert malformed.exit_code != 0
        assert sorted(path.name for path in Path("malformed").iterdir()) == [
            "manifest.json",
            "observations.jsonl",
        ]


def test_resume_recreates_a_missing_advisory_lock_for_valid_durable_state():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd())
        first = _invoke(runner, "study", "--max-new-evaluations", "1")
        assert first.exit_code == 0, first.output
        Path("study/.study.lock").unlink()

        resumed = _invoke(
            runner,
            "study",
            "--resume",
            "--max-new-evaluations",
            "1",
        )

        assert resumed.exit_code == 0, resumed.output
        assert Path("study/.study.lock").is_file()
        assert json.loads(resumed.output)["evaluation_count"] == 2


def test_optimize_rejects_function_network_architecture_before_creating_state():
    runner = CliRunner()
    with runner.isolated_filesystem():
        run = _write_case(Path.cwd())
        unsupported = replace(run.study, backend="function_network_full")
        replace(run, study=unsupported).to_yaml("optimization.yaml")

        result = _invoke(runner, "study")

        assert result.exit_code != 0
        assert "Release A" in result.output
        assert not Path("study").exists()


def test_incompatible_resume_preserves_all_existing_artifact_bytes():
    runner = CliRunner()
    with runner.isolated_filesystem():
        run = _write_case(Path.cwd())
        first = _invoke(runner, "study", "--max-new-evaluations", "1")
        assert first.exit_code == 0, first.output
        before = {
            path.relative_to("study").as_posix(): path.read_bytes()
            for path in Path("study").iterdir()
            if path.is_file()
        }
        changed_study = replace(run.study, seed=run.study.seed + 1)
        replace(run, study=changed_study).to_yaml("optimization.yaml")

        resumed = _invoke(
            runner,
            "study",
            "--resume",
            "--max-new-evaluations",
            "1",
        )

        after = {
            path.relative_to("study").as_posix(): path.read_bytes()
            for path in Path("study").iterdir()
            if path.is_file()
        }
        assert resumed.exit_code != 0
        assert "differs from the manifest" in resumed.output
        assert after == before


@pytest.mark.parametrize(
    ("case", "expected"),
    (
        ({"maximum": 1}, "max_evaluations"),
        ({"maximum": 4, "target": -1.0}, "target_attained"),
        ({"maximum": 4, "single_value": True}, "finite_space_exhausted"),
        (
            {"maximum": 4, "max_cost": 0.5, "initial_cost": 1.0},
            "insufficient_remaining_budget",
        ),
    ),
)
def test_optimize_reports_each_public_stop_condition(case, expected):
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), **case)

        result = _invoke(runner, "study")

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["state"] == expected


@pytest.mark.parametrize(
    ("case", "expected"),
    (
        (
            {"maximum": 4, "max_cost": 1.5, "initial_cost": 1.0},
            "insufficient_remaining_budget",
        ),
        ({"maximum": 4, "single_value": True}, "finite_space_exhausted"),
    ),
)
def test_bounded_invocation_commits_a_terminal_condition_reached_at_its_boundary(case, expected):
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), **case)

        result = _invoke(runner, "study", "--max-new-evaluations", "1")

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["state"] == expected


def test_evaluator_exceptions_are_committed_and_reported_as_failures():
    runner = CliRunner()
    source = """
def make_evaluator(system):
    def evaluate(action):
        raise RuntimeError("worker unavailable")
    return evaluate
""".lstrip()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), maximum=1, evaluator_source=source)

        result = _invoke(runner, "study")

        assert result.exit_code == 0, result.output
        summary = json.loads(result.output)
        assert summary["state"] == "max_evaluations"
        assert summary["total_evaluator_cost"] == 0.0
        assert summary["status_counts"] == {"infrastructure_failure": 1}
        record = json.loads(Path("study/observations.jsonl").read_text())
        assert "worker unavailable" in record["result"]["message"]


@pytest.mark.parametrize(
    ("result_arguments", "failure_text"),
    (
        ('"wrong-action", {"score": 1.0}, {}, 1.0, "run"', "action ID"),
        ('action.id, {"score": 1.0}, {}, 1.0, "wrong-unit"', "cost_unit"),
    ),
)
def test_invalid_evaluator_result_semantics_are_committed_as_failures(
    result_arguments, failure_text
):
    runner = CliRunner()
    source = f"""
from autoengineering.optimization import EvaluationResult

def make_evaluator(system):
    def evaluate(action):
        return EvaluationResult.success({result_arguments})
    return evaluate
""".lstrip()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), maximum=1, evaluator_source=source)

        result = _invoke(runner, "study")

        assert result.exit_code == 0, result.output
        summary = json.loads(result.output)
        assert summary["status_counts"] == {"infrastructure_failure": 1}
        record = json.loads(Path("study/observations.jsonl").read_text())
        assert failure_text in record["result"]["message"]
        assert record["result"]["action_id"] == record["action"]["id"]
        assert not Path("study/pending-actions.json").exists()


def test_invalid_evaluator_factory_output_fails_before_workdir_creation():
    runner = CliRunner()
    source = """
def make_evaluator(system):
    return object()
""".lstrip()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), evaluator_source=source)

        result = _invoke(runner, "study")

        assert result.exit_code != 0
        assert "must return a callable" in result.output
        assert not Path("study").exists()


@pytest.mark.parametrize(
    ("optimization_contents", "evaluator_source", "message"),
    (
        ("study: [\n", None, "Error:"),
        (
            None,
            "def make_evaluator(system):\n    raise RuntimeError('factory failed')\n",
            "factory failed",
        ),
    ),
)
def test_configuration_and_factory_errors_are_concise_and_create_no_state(
    optimization_contents,
    evaluator_source,
    message,
):
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), evaluator_source=evaluator_source)
        if optimization_contents is not None:
            Path("optimization.yaml").write_text(optimization_contents, encoding="utf-8")

        result = _invoke(runner, "study")

        assert result.exit_code != 0
        assert message in result.output
        assert result.exception is not None
        assert not Path("study").exists()


def test_optimize_text_output_contains_the_same_run_summary():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), maximum=1)

        result = runner.invoke(
            cli,
            [
                "optimize",
                "system.yaml",
                "optimization.yaml",
                "--workdir",
                "study",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "State: max_evaluations" in result.output
        assert "Evaluations: 1 total, 1 new" in result.output
        assert "Cost: 1.0 run" in result.output
        assert "Recommendation:" in result.output


@pytest.mark.skipif(
    importlib.util.find_spec("botorch") is None,
    reason="Bayesian dependencies are not installed",
)
def test_optimize_constructs_botorch_policy_in_bayesian_environment():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), policy="botorch", maximum=1)

        result = _invoke(runner, "study")

        assert result.exit_code == 0, result.output
        assert json.loads(result.output)["state"] == "max_evaluations"


@pytest.mark.skipif(
    importlib.util.find_spec("botorch") is not None,
    reason="missing-dependency behavior is a base-environment contract",
)
def test_optimize_botorch_policy_names_the_bayesian_environment_when_unavailable():
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_case(Path.cwd(), policy="botorch", maximum=1)

        result = _invoke(runner, "study")

        assert result.exit_code != 0
        assert "pixi run -e bayes" in result.output
        assert not Path("study").exists()


def test_command_module_import_does_not_load_optional_optimizers():
    command = [
        sys.executable,
        "-c",
        (
            "import sys; import autoengineering.optimization.command; "
            "blocked={'torch','botorch','gpytorch','smac'}; "
            "assert not (blocked & {name.split('.')[0] for name in sys.modules})"
        ),
    ]

    completed = subprocess.run(command, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr
