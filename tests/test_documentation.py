"""Structural contracts for current user-facing documentation."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import tomllib
from urllib.parse import unquote, urlparse

import pytest

from autoengineering.cli import cli
from autoengineering.optimization import OptimizationRunSpec


ROOT = Path(__file__).resolve().parents[1]
LIVE_DOCUMENTS = (
    ROOT / "README.md",
    ROOT / "CLAUDE.md",
    ROOT / ".claude/agents/auto-engineer.md",
    ROOT / "docs/optimization.md",
    ROOT / "examples/README.md",
    ROOT / "examples/leaf_river/README.md",
)
MARKDOWN_LINK = re.compile(r"\[[^]]*]\(([^)]+)\)")
PIXI_COMMAND = re.compile(r"\bpixi run(?: -e [a-z0-9_-]+)? ([a-z][a-z0-9_-]*)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("document", LIVE_DOCUMENTS, ids=lambda path: str(path.relative_to(ROOT)))
def test_local_markdown_links_resolve(document: Path):
    missing: list[str] = []
    for raw_target in MARKDOWN_LINK.findall(_read(document)):
        target = raw_target.strip().strip("<>").split("#", maxsplit=1)[0]
        if not target:
            continue
        parsed = urlparse(target)
        if parsed.scheme or target.startswith("//"):
            continue
        resolved = (document.parent / unquote(target)).resolve()
        if not resolved.exists():
            missing.append(target)

    assert not missing, f"Missing links in {document.relative_to(ROOT)}: {missing}"


def test_documented_cli_commands_match_click_registry():
    registered = set(cli.commands)
    expected = {
        "candidates",
        "components",
        "describe",
        "experiments",
        "graph",
        "improve",
        "optimize",
        "report",
        "validate",
    }
    assert registered == expected

    readme = _read(ROOT / "README.md")
    agent = _read(ROOT / ".claude/agents/auto-engineer.md")
    for command in expected:
        assert f"`{command}" in readme, f"README omits CLI command {command}"
        assert f"`{command}" in agent, f"Agent guidance omits CLI command {command}"


def test_documented_optimize_arguments_match_click_command():
    optimize = cli.commands["optimize"]
    parameter_names = {parameter.name for parameter in optimize.params}
    assert parameter_names == {
        "fmt",
        "max_new_evaluations",
        "optimization_file",
        "resume",
        "system_file",
        "workdir",
    }

    guide = _read(ROOT / "docs/optimization.md")
    for spelling in (
        "SYSTEM_FILE",
        "OPTIMIZATION_FILE",
        "--workdir",
        "--max-new-evaluations",
        "--resume",
        "--format",
    ):
        assert spelling.lower() in guide.lower()


def test_documented_python_imports_are_public():
    from autoengineering.analyze import generate_report, rank_opportunities
    from autoengineering.execute import swap_component
    from autoengineering.optimization import (
        ObservationLedger,
        OptimizationStudy,
        SearchSpace,
    )
    from autoengineering.optimization.command import build_backend
    from autoengineering.research import (
        Candidate,
        auto_improve,
        build_feedforward_runner,
        load_candidates,
        write_report,
    )
    from autoengineering.system import System
    from autoengineering.validate import ValidationResult
    from autoengineering.validate.compare import validate_arrays

    imports = (
        Candidate,
        ObservationLedger,
        OptimizationRunSpec,
        OptimizationStudy,
        SearchSpace,
        System,
        ValidationResult,
        auto_improve,
        build_backend,
        build_feedforward_runner,
        generate_report,
        load_candidates,
        rank_opportunities,
        swap_component,
        validate_arrays,
        write_report,
    )
    assert all(callable(item) for item in imports)


def test_documented_single_test_node_exists():
    command = re.search(
        r"pixi run pytest ([^\s]+)",
        _read(ROOT / "CLAUDE.md"),
    )
    assert command is not None
    path_text, class_name, method_name = command.group(1).split("::")
    test_path = ROOT / path_text
    module = ast.parse(_read(test_path))
    test_class = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    assert any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == method_name
        for node in test_class.body
    )


def test_documented_pixi_tasks_exist():
    configuration = tomllib.loads(_read(ROOT / "pixi.toml"))
    tasks = set(configuration["tasks"])
    task_like_executables = tasks | {"autoengineering", "pytest", "python"}

    documented: set[str] = set()
    for document in LIVE_DOCUMENTS:
        documented.update(PIXI_COMMAND.findall(_read(document)))

    assert documented <= task_like_executables
    assert {"lint", "test", "test-bayes", "benchmark-release-a"} <= documented
    assert "install" not in tasks
    assert all("pixi run install" not in _read(document) for document in LIVE_DOCUMENTS)


def test_python_version_and_package_extras_match_project_metadata():
    project = tomllib.loads(_read(ROOT / "pyproject.toml"))["project"]
    assert project["requires-python"] == ">=3.12,<3.13"
    assert set(project["optional-dependencies"]) == {"bayes", "benchmark"}

    for path in (ROOT / "README.md", ROOT / "docs/optimization.md"):
        document = _read(path)
        assert "'.[bayes]'" in document
        assert "'.[bayes,benchmark]'" in document
    assert "Python 3.12" in _read(ROOT / "CLAUDE.md")


def test_optimization_guide_covers_release_a_contract():
    guide = _read(ROOT / "docs/optimization.md")
    required_terms = {
        "whole-system",
        "function-network",
        "random",
        "sobol",
        "botorch",
        "deterministic",
        "known",
        "learned",
        "scientific_infeasible",
        "model_failure",
        "timeout",
        "infrastructure_failure",
        "max_categorical_assignments",
        "candidate_retry_limit",
        "invocation_limit",
        "observations.jsonl",
        "manifest.json",
        "backend-state.json",
        "recommendation.json",
        "optimization-report.md",
        "pending-*.json",
        "benchmark",
        "raw-records.jsonl",
        "gate.json",
        "duplicate keys",
        "parent traversal",
        "run file directory",
        "symbolic link",
        "symlink components",
        "regular nonsymlink file",
        "evaluator source",
        "float64 machine epsilon",
        "seeded pseudorandom samples",
    }
    missing = sorted(term for term in required_terms if term not in guide.lower())
    assert not missing, f"Optimization guide omits: {missing}"

    run = OptimizationRunSpec.from_yaml(ROOT / "examples/optimization_chain/optimization.yaml")
    for field in run.to_dict():
        assert f"`{field}`" in guide, f"Optimization guide omits run field {field}"

    path_rows = {
        "Relative system YAML": "Run file directory",
        "Declared `input_files`": "Run file directory",
        "Local evaluator module": "Run file directory",
        "Installed evaluator module": "Python environment",
        "Work directory": "Command working directory",
    }
    for input_kind, resolution_base in path_rows.items():
        assert re.search(
            rf"^\| {re.escape(input_kind)} \| {re.escape(resolution_base)} \|",
            guide,
            flags=re.MULTILINE,
        )


def test_documented_botorch_defaults_match_constructor():
    module = ast.parse(_read(ROOT / "src/autoengineering/optimization/system_backend.py"))
    backend = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "SystemBayesBackend"
    )
    constructor = next(
        node
        for node in backend.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    names = [argument.arg for argument in constructor.args.kwonlyargs]
    defaults = [ast.literal_eval(default) for default in constructor.args.kw_defaults]
    expected = dict(zip(names, defaults, strict=True))
    assert expected == {
        "candidate_retry_limit": 3,
        "max_categorical_assignments": 128,
        "min_initial": 6,
        "num_restarts": 8,
        "raw_samples": 128,
    }

    guide = _read(ROOT / "docs/optimization.md")
    for name, value in expected.items():
        assert re.search(rf"^\| `{name}` \| {value} \|", guide, flags=re.MULTILINE)


def test_example_index_matches_checked_system_examples():
    checked = {
        path.parent.name
        for path in (ROOT / "examples").glob("*/system.yaml")
        if path.parent.is_dir()
    }
    expected_network = {
        "function_network": "No",
        "hydro_chain": "No",
        "leaf_river": "No with checked cache",
        "lotka_volterra": "No",
        "optimization_chain": "No",
        "signal_chain": "No",
    }
    assert checked == set(expected_network)

    index = _read(ROOT / "examples/README.md")
    for name, network in expected_network.items():
        pattern = rf"^\| \[`{re.escape(name)}`]\([^)]*\).*\| {re.escape(network)} \|"
        assert re.search(pattern, index, flags=re.MULTILINE), (
            f"Example index omits {name} or its {network!r} network label"
        )

    assert (ROOT / "examples/leaf_river/data/streamflow.csv").is_file()
    assert (ROOT / "examples/leaf_river/data/weather.csv").is_file()
    assert "fetcher contacts USGS and NOAA only if those cache files are absent" in index


def test_live_entry_documents_do_not_restore_stale_setup_claims():
    combined = "\n".join(_read(document) for document in LIVE_DOCUMENTS)
    assert "51 tests" not in combined
    assert "osx-arm64 only" not in combined
    assert "pixi run install" not in combined
