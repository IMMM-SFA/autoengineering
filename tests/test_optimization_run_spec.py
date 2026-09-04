"""Public run configuration and explicit input provenance contracts."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from autoengineering.optimization import (
    BudgetSpec,
    CategoricalParameter,
    ConstraintSpec,
    ContinuousParameter,
    IntegerParameter,
    NoiseSpec,
    ObjectiveSpec,
    OptimizationRunSpec,
    SearchSpace,
    StudySpec,
)


@pytest.fixture
def study():
    return StudySpec(
        name="public-run",
        objective=ObjectiveSpec("score", "maximize"),
        constraints=(ConstraintSpec("cost", "<=", 4.0),),
        budget=BudgetSpec(12.0, "run", max_evaluations=8),
        noise=NoiseSpec("known", 0.001),
        backend="system",
        seed=31,
    )


@pytest.fixture
def mixed_space():
    return SearchSpace(
        (
            CategoricalParameter("mode", ("simple", "complex")),
            CategoricalParameter("typed", (True, 1, "1", 1.0)),
            IntegerParameter("steps", 1, 16, "log", active_when={"mode": ("complex",)}),
            ContinuousParameter("rate", 0.01, 2.0, "log", active_when={"mode": ("complex",)}),
        )
    )


def _run_spec(study, space, **changes):
    values = {
        "study": study,
        "search_space": space,
        "policy": "botorch",
        "policy_options": {"min_initial": 4, "raw_samples": 32},
        "evaluator_factory": "local_evaluator:make_evaluator",
        "input_files": ("data/observations.csv",),
        "target_value": 0.9,
        "max_new_evaluations": 3,
    }
    values.update(changes)
    return OptimizationRunSpec(**values)


def _write_run_directory(directory: Path, run: OptimizationRunSpec) -> Path:
    (directory / "data").mkdir()
    (directory / "data" / "observations.csv").write_text("value\n1\n", encoding="utf-8")
    (directory / "system.yaml").write_text("name: example\n", encoding="utf-8")
    (directory / "local_evaluator.py").write_text(
        "def make_evaluator(system):\n    return lambda action: None\n", encoding="utf-8"
    )
    path = directory / "optimization.yaml"
    run.to_yaml(path)
    return path


@pytest.mark.parametrize(
    "parameter",
    (
        CategoricalParameter("kind", (True, 1, "1", 1.0)),
        ContinuousParameter("rate", 0.01, 10.0, "log", {"kind": ("1",)}),
        IntegerParameter("count", 1, 20, "log", {"kind": (True,)}),
    ),
)
def test_parameter_types_round_trip_through_dict_and_stable_yaml(tmp_path, parameter):
    loader = type(parameter)
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"

    parameter.to_yaml(first)
    parameter.to_yaml(second)

    assert loader.from_dict(parameter.to_dict()) == parameter
    assert loader.from_yaml(first) == parameter
    assert first.read_bytes() == second.read_bytes()


def test_mixed_conditional_search_space_round_trip_preserves_order_and_scalar_types(
    tmp_path, mixed_space
):
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"

    mixed_space.to_yaml(first)
    mixed_space.to_yaml(second)
    restored = SearchSpace.from_yaml(first)

    assert restored == mixed_space
    assert tuple(parameter.name for parameter in restored.parameters) == (
        "mode",
        "typed",
        "steps",
        "rate",
    )
    assert tuple(type(value) for value in restored.parameters[1].categories) == (
        bool,
        int,
        str,
        float,
    )
    assert first.read_bytes() == second.read_bytes()


@pytest.mark.parametrize(
    "mutation",
    (
        lambda data: data.update({"unknown": 1}),
        lambda data: data["parameters"][0].update({"unknown": 1}),
        lambda data: data["parameters"][0].update({"type": "mystery"}),
        lambda data: data["parameters"].append(data["parameters"][0]),
    ),
)
def test_search_space_rejects_unknown_fields_types_and_duplicate_names(mixed_space, mutation):
    data = mixed_space.to_dict()
    mutation(data)

    with pytest.raises((TypeError, ValueError)):
        SearchSpace.from_dict(data)


def test_search_space_yaml_rejects_duplicate_mapping_keys(tmp_path):
    path = tmp_path / "space.yaml"
    path.write_text(
        "\n".join(
            (
                "schema_version: '1.0'",
                "parameters:",
                "  - type: categorical",
                "    name: first",
                "    name: second",
                "    categories: [a, b]",
                "",
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate YAML"):
        SearchSpace.from_yaml(path)


@pytest.mark.parametrize("policy", ("random", "sobol", "botorch"))
def test_run_spec_round_trips_each_public_policy(tmp_path, study, mixed_space, policy):
    options = {"num_restarts": 3} if policy == "botorch" else {}
    run = _run_spec(study, mixed_space, policy=policy, policy_options=options)
    first = _write_run_directory(tmp_path, run)
    second = tmp_path / "optimization-copy.yaml"
    run.to_yaml(second)

    restored = OptimizationRunSpec.from_yaml(first)

    assert restored == run
    assert restored.canonical_json == run.canonical_json
    assert first.read_bytes() == second.read_bytes()
    assert restored.resolve_input_files(first) == {
        "data/observations.csv": (tmp_path / "data" / "observations.csv").resolve()
    }
    assert callable(restored.load_evaluator_factory(first))
    with pytest.raises(TypeError):
        restored.policy_options["num_restarts"] = 9
    with pytest.raises(FrozenInstanceError):
        restored.policy = "random"


@pytest.mark.parametrize(
    ("policy", "options"),
    (
        ("unknown", {}),
        ("random", {"min_initial": 2}),
        ("sobol", {"raw_samples": 8}),
        ("botorch", {"unknown": 1}),
        ("botorch", {"raw_samples": 1}),
        ("botorch", {"min_initial": True}),
    ),
)
def test_run_spec_rejects_unknown_policies_and_invalid_options(study, mixed_space, policy, options):
    with pytest.raises(ValueError):
        _run_spec(study, mixed_space, policy=policy, policy_options=options)


@pytest.mark.parametrize(
    "path",
    ("../outside.csv", "/absolute.csv", "C:" + "/absolute.csv", "./data.csv", "a\\b.csv", "."),
)
def test_run_spec_rejects_unsafe_declared_input_paths(study, mixed_space, path):
    with pytest.raises(ValueError, match="path"):
        _run_spec(study, mixed_space, input_files=(path,))


def test_run_spec_rejects_duplicate_and_missing_or_symlinked_inputs(tmp_path, study, mixed_space):
    with pytest.raises(ValueError, match="unique"):
        _run_spec(
            study,
            mixed_space,
            input_files=("data/observations.csv", "data/observations.csv"),
        )

    run = _run_spec(study, mixed_space)
    path = _write_run_directory(tmp_path, run)
    (tmp_path / "data" / "observations.csv").unlink()
    with pytest.raises(ValueError, match="does not exist"):
        OptimizationRunSpec.from_yaml(path)

    target = tmp_path / "target.csv"
    target.write_text("value\n1\n", encoding="utf-8")
    (tmp_path / "data" / "observations.csv").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        OptimizationRunSpec.from_yaml(path)


def test_run_spec_rejects_symlinked_path_components_and_specifications(
    tmp_path, study, mixed_space
):
    run = _run_spec(study, mixed_space)
    path = _write_run_directory(tmp_path, run)
    actual_data = tmp_path / "actual-data"
    (tmp_path / "data").rename(actual_data)
    (tmp_path / "data").symlink_to(actual_data, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        OptimizationRunSpec.from_yaml(path)

    linked_spec = tmp_path / "linked-optimization.yaml"
    linked_spec.symlink_to(path)
    with pytest.raises(ValueError, match="nonsymlink"):
        OptimizationRunSpec.from_yaml(linked_spec)


@pytest.mark.parametrize("entry", ("missing-colon", "bad module:factory", "module:bad.name"))
def test_run_spec_rejects_malformed_evaluator_entry_points(study, mixed_space, entry):
    with pytest.raises(ValueError, match="module:callable"):
        _run_spec(study, mixed_space, evaluator_factory=entry)


def test_loaded_evaluator_module_must_exist(tmp_path, study, mixed_space):
    run = _run_spec(study, mixed_space, evaluator_factory="absent_evaluator:factory")
    path = _write_run_directory(tmp_path, run)

    with pytest.raises(ValueError, match="cannot be imported"):
        OptimizationRunSpec.from_yaml(path)


def test_loaded_evaluator_entry_point_must_be_callable(tmp_path, study, mixed_space):
    run = _run_spec(study, mixed_space, evaluator_factory="local_evaluator:not_callable")
    path = _write_run_directory(tmp_path, run)

    with pytest.raises(ValueError, match="not callable"):
        OptimizationRunSpec.from_yaml(path)


def test_run_spec_rejects_unknown_top_level_fields(study, mixed_space):
    data = _run_spec(study, mixed_space).to_dict()
    data["unknown"] = True

    with pytest.raises(ValueError, match="keys"):
        OptimizationRunSpec.from_dict(data)


def test_run_spec_yaml_rejects_duplicate_mapping_keys(tmp_path, study, mixed_space):
    run = _run_spec(study, mixed_space)
    path = _write_run_directory(tmp_path, run)
    contents = path.read_text(encoding="utf-8")
    path.write_text(
        contents.replace("policy: botorch\n", "policy: random\npolicy: botorch\n"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate YAML"):
        OptimizationRunSpec.from_yaml(path)


@pytest.mark.parametrize(
    "changes",
    (
        {"target_value": True},
        {"target_value": float("nan")},
        {"max_new_evaluations": True},
        {"max_new_evaluations": -1},
        {"input_files": "data/observations.csv"},
    ),
)
def test_run_spec_rejects_invalid_invocation_limits_and_input_collections(
    study, mixed_space, changes
):
    with pytest.raises((TypeError, ValueError)):
        _run_spec(study, mixed_space, **changes)


def test_policy_option_serialization_uses_constructor_order(study, mixed_space):
    first = _run_spec(
        study,
        mixed_space,
        policy_options={"raw_samples": 32, "min_initial": 4},
    )
    second = _run_spec(
        study,
        mixed_space,
        policy_options={"min_initial": 4, "raw_samples": 32},
    )

    assert first.to_dict() == second.to_dict()
    assert first.canonical_json == second.canonical_json


def test_input_hashes_cover_only_declared_files_and_change_with_their_bytes(
    tmp_path, study, mixed_space
):
    run = _run_spec(study, mixed_space)
    path = _write_run_directory(tmp_path, run)
    undeclared = tmp_path / "undeclared.txt"
    undeclared.write_text("ignored\n", encoding="utf-8")

    first = run.input_artifact_hashes(system_path="system.yaml", specification_path=path)
    undeclared.write_text("changed but still ignored\n", encoding="utf-8")
    assert run.input_artifact_hashes(system_path="system.yaml", specification_path=path) == first

    declared = tmp_path / "data" / "observations.csv"
    declared.write_text("value\n2\n", encoding="utf-8")
    second = run.input_artifact_hashes(system_path="system.yaml", specification_path=path)

    assert set(first) == {
        "system:system.yaml",
        "run_spec:optimization.yaml",
        "evaluator:local_evaluator:make_evaluator",
        "input:data/observations.csv",
    }
    assert first["input:data/observations.csv"] != second["input:data/observations.csv"]
    assert (
        first["system:system.yaml"]
        == hashlib.sha256((tmp_path / "system.yaml").read_bytes()).hexdigest()
    )


@pytest.mark.parametrize(
    ("relative_path", "hash_key", "replacement"),
    (
        ("system.yaml", "system:system.yaml", "name: changed\n"),
        ("optimization.yaml", "run_spec:optimization.yaml", None),
        (
            "local_evaluator.py",
            "evaluator:local_evaluator:make_evaluator",
            "def make_evaluator(system):\n    return lambda action: 2\n",
        ),
        ("data/observations.csv", "input:data/observations.csv", "value\n3\n"),
    ),
)
def test_each_explicit_input_has_a_byte_sensitive_hash(
    tmp_path, study, mixed_space, relative_path, hash_key, replacement
):
    run = _run_spec(study, mixed_space)
    path = _write_run_directory(tmp_path, run)
    first = run.input_artifact_hashes(system_path="system.yaml", specification_path=path)
    target = tmp_path / relative_path
    if replacement is None:
        target.write_text(
            target.read_text(encoding="utf-8") + "# same run, new bytes\n",
            encoding="utf-8",
        )
    else:
        target.write_text(replacement, encoding="utf-8")

    second = run.input_artifact_hashes(system_path="system.yaml", specification_path=path)

    assert first[hash_key] != second[hash_key]


def test_local_evaluator_loading_does_not_reuse_a_module_from_another_run_directory(
    tmp_path, study, mixed_space
):
    run = _run_spec(study, mixed_space)
    directories = (tmp_path / "first", tmp_path / "second")
    for directory in directories:
        directory.mkdir()
        _write_run_directory(directory, run)
    (directories[1] / "local_evaluator.py").write_text(
        "def make_evaluator(system):\n    return lambda action: 9\n", encoding="utf-8"
    )

    hashes = [
        run.input_artifact_hashes(
            system_path="system.yaml", specification_path=directory / "optimization.yaml"
        )
        for directory in directories
    ]

    key = "evaluator:local_evaluator:make_evaluator"
    assert hashes[0][key] != hashes[1][key]


def test_local_evaluator_dependencies_are_isolated_between_run_directories(
    tmp_path, study, mixed_space
):
    run = _run_spec(
        study,
        mixed_space,
        input_files=("data/observations.csv", "helper.py"),
    )
    directories = (tmp_path / "first", tmp_path / "second")
    values = ("first", "second")
    for directory, value in zip(directories, values, strict=True):
        directory.mkdir()
        path = _write_run_directory(directory, run)
        (directory / "helper.py").write_text(f"VALUE = {value!r}\n", encoding="utf-8")
        (directory / "local_evaluator.py").write_text(
            "from helper import VALUE\n"
            "def make_evaluator(system):\n"
            "    return lambda action: VALUE\n",
            encoding="utf-8",
        )
        run.to_yaml(path)

    factories = [
        run.load_evaluator_factory(directory / "optimization.yaml") for directory in directories
    ]
    second_hashes = run.input_artifact_hashes(
        system_path="system.yaml", specification_path=directories[1] / "optimization.yaml"
    )

    assert [factory(None)(None) for factory in factories] == ["first", "second"]
    assert (
        second_hashes["input:helper.py"]
        == hashlib.sha256((directories[1] / "helper.py").read_bytes()).hexdigest()
    )


def test_local_evaluator_reload_matches_the_source_bytes_that_are_hashed(
    tmp_path, study, mixed_space
):
    run = _run_spec(study, mixed_space)
    path = _write_run_directory(tmp_path, run)
    source = tmp_path / "local_evaluator.py"
    source.write_text(
        "def make_evaluator(system):\n    return lambda action: 'old'\n", encoding="utf-8"
    )
    old_factory = run.load_evaluator_factory(path)
    old_hash = run.input_artifact_hashes(system_path="system.yaml", specification_path=path)[
        "evaluator:local_evaluator:make_evaluator"
    ]
    source.write_text(
        "def make_evaluator(system):\n    return lambda action: 'new'\n", encoding="utf-8"
    )

    new_factory = run.load_evaluator_factory(path)
    new_hash = run.input_artifact_hashes(system_path="system.yaml", specification_path=path)[
        "evaluator:local_evaluator:make_evaluator"
    ]

    assert old_factory(None)(None) == "old"
    assert new_factory(None)(None) == "new"
    assert old_hash != new_hash
    assert new_hash == hashlib.sha256(source.read_bytes()).hexdigest()


def test_evaluator_hash_binds_the_declared_entry_module_when_callable_is_decorated(
    tmp_path, study, mixed_space
):
    run = _run_spec(study, mixed_space)
    path = _write_run_directory(tmp_path, run)
    helper = tmp_path / "decorator_helper.py"
    helper.write_text(
        "def decorate(factory):\n"
        "    def wrapper(system):\n"
        "        return factory(system)\n"
        "    return wrapper\n",
        encoding="utf-8",
    )
    source = tmp_path / "local_evaluator.py"
    source.write_text(
        "from decorator_helper import decorate\n"
        "@decorate\n"
        "def make_evaluator(system):\n"
        "    return lambda action: 'old'\n",
        encoding="utf-8",
    )
    first_factory = run.load_evaluator_factory(path)
    first_hash = run.input_artifact_hashes(system_path="system.yaml", specification_path=path)[
        "evaluator:local_evaluator:make_evaluator"
    ]
    source.write_text(
        "from decorator_helper import decorate\n"
        "@decorate\n"
        "def make_evaluator(system):\n"
        "    return lambda action: 'new'\n",
        encoding="utf-8",
    )

    second_factory = run.load_evaluator_factory(path)
    second_hash = run.input_artifact_hashes(system_path="system.yaml", specification_path=path)[
        "evaluator:local_evaluator:make_evaluator"
    ]

    assert first_factory(None)(None) == "old"
    assert second_factory(None)(None) == "new"
    assert first_hash != second_hash
    assert second_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    assert second_hash != hashlib.sha256(helper.read_bytes()).hexdigest()


def test_symlinked_local_evaluator_package_cannot_escape_run_directory(
    tmp_path, study, mixed_space
):
    run_directory = tmp_path / "run"
    outside_directory = tmp_path / "outside"
    run_directory.mkdir()
    outside_directory.mkdir()
    run = _run_spec(study, mixed_space, evaluator_factory="linked_evaluator:make_evaluator")
    path = _write_run_directory(run_directory, run)
    package = outside_directory / "linked_evaluator"
    package.mkdir()
    (package / "__init__.py").write_text(
        "def make_evaluator(system):\n    return lambda action: 'outside'\n", encoding="utf-8"
    )
    (run_directory / "linked_evaluator").symlink_to(package, target_is_directory=True)

    with pytest.raises(ValueError, match="symlink"):
        OptimizationRunSpec.from_yaml(path)


def test_semantic_run_changes_have_distinct_canonical_hashes(study, mixed_space):
    run = _run_spec(study, mixed_space)

    assert replace(run, target_value=0.8).sha256 != run.sha256
    assert replace(run, policy_options={"min_initial": 5}).sha256 != run.sha256
    assert replace(run, search_space=SearchSpace(mixed_space.parameters[:-1])).sha256 != run.sha256


def test_input_hashes_reject_a_specification_file_for_a_different_run(tmp_path, study, mixed_space):
    recorded = _run_spec(study, mixed_space, target_value=0.9)
    path = _write_run_directory(tmp_path, recorded)
    requested = replace(recorded, target_value=0.1)

    with pytest.raises(ValueError, match="differs from the in-memory run"):
        requested.input_artifact_hashes(system_path="system.yaml", specification_path=path)


def test_fresh_processes_load_equal_canonical_configuration_and_hashes(
    tmp_path, study, mixed_space
):
    run = _run_spec(study, mixed_space)
    path = _write_run_directory(tmp_path, run)
    program = "\n".join(
        (
            "import json",
            "from autoengineering.optimization import OptimizationRunSpec",
            f"path = {str(path)!r}",
            "run = OptimizationRunSpec.from_yaml(path)",
            "print(json.dumps({'canonical': run.canonical_json, 'hashes': run.input_artifact_hashes(system_path='system.yaml', specification_path=path)}, sort_keys=True))",
        )
    )

    outputs = [
        subprocess.run(
            [sys.executable, "-c", program], check=True, capture_output=True, text=True
        ).stdout
        for _ in range(2)
    ]

    assert outputs[0] == outputs[1]
    payload = json.loads(outputs[0])
    assert payload["canonical"] == run.canonical_json
