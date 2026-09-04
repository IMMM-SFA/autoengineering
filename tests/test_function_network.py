"""Contracts for the immutable function-network representation."""

from dataclasses import FrozenInstanceError, replace
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import pytest

from autoengineering.optimization.function_network_evaluator import (
    FunctionNetworkArtifactError,
    FunctionNetworkEvaluator,
    NpzReadLimits,
    read_verified_npz,
    reconstruct_component_training_tables,
)
from autoengineering.optimization.function_network import (
    CouplingSpec,
    FunctionComponentSpec,
    FunctionNetworkSpec,
    FunctionPortSpec,
    ScalarOutputSpec,
    TerminalConstraintSpec,
    TerminalObjectiveSpec,
    reduce_scalar,
    scalar_observation_name,
)
from autoengineering.optimization.records import EvaluationScope
from autoengineering.optimization.records import EvaluationAction, EvaluationResult, EvaluationStatus
from autoengineering.optimization.space import CategoricalParameter, ContinuousParameter
from autoengineering.optimization.ledger import ObservationLedger
from autoengineering.research.runner import EvaluationContext, ParentArtifactReference
from autoengineering.system.graph import System


def _port(name, direction, data_type="timeseries", units="m3/s"):
    return FunctionPortSpec(name, direction, data_type, units)


@pytest.fixture
def network_system():
    system = System("synthetic-chain")
    source = system.add_component("source", outputs={"driver": "timeseries"})
    source.outputs[0].units = "mm/day"
    transform = system.add_component(
        "transform",
        inputs={"driver": "timeseries"},
        outputs={"flow": "timeseries"},
        metadata={
            "runnable": {
                "kind": "python",
                "entry": "synthetic:transform",
                "inputs": ["driver"],
                "outputs": ["flow"],
                "params": {"gain": 1.0},
            }
        },
    )
    transform.inputs[0].units = "mm/day"
    transform.outputs[0].units = "m3/s"
    score = system.add_component(
        "score",
        inputs={"flow": "timeseries"},
        outputs={"utility": "timeseries"},
        metadata={
            "runnable": {
                "kind": "python",
                "entry": "synthetic:score",
                "inputs": ["flow"],
                "outputs": ["utility"],
                "params": {"offset": 0.0},
            }
        },
    )
    score.inputs[0].units = "m3/s"
    score.outputs[0].units = "point"
    system.connect("source", "transform", "driver", "driver")
    system.connect("transform", "score", "flow", "flow")
    return system


@pytest.fixture
def network_spec():
    system_scope = (EvaluationScope.SYSTEM,)
    both_scopes = (EvaluationScope.SYSTEM, EvaluationScope.COMPONENT)
    return FunctionNetworkSpec(
        name="synthetic-chain",
        components=(
            FunctionComponentSpec(
                component="source",
                entry_point=None,
                parameters=(),
                inputs=(),
                outputs=(FunctionPortSpec("driver", "out", "timeseries", "mm/day"),),
                scalar_outputs=(
                    ScalarOutputSpec("driver_mean", "driver", "mean", system_scope),
                ),
                expected_cost=0.0,
                cost_unit="second",
                evaluation_scopes=system_scope,
            ),
            FunctionComponentSpec(
                component="transform",
                entry_point="synthetic:transform",
                parameters=(
                    CategoricalParameter("choice", ("base",)),
                    ContinuousParameter("gain", 0.5, 2.0),
                ),
                inputs=(FunctionPortSpec("driver", "in", "timeseries", "mm/day"),),
                outputs=(FunctionPortSpec("flow", "out", "timeseries", "m3/s"),),
                scalar_outputs=(
                    ScalarOutputSpec("flow_mean", "flow", "mean", both_scopes),
                ),
                expected_cost=1.0,
                cost_unit="second",
                evaluation_scopes=both_scopes,
            ),
            FunctionComponentSpec(
                component="score",
                entry_point="synthetic:score",
                parameters=(
                    CategoricalParameter("choice", ("base",)),
                    ContinuousParameter("offset", -2.0, 2.0),
                ),
                inputs=(FunctionPortSpec("flow", "in", "timeseries", "m3/s"),),
                outputs=(FunctionPortSpec("utility", "out", "timeseries", "point"),),
                scalar_outputs=(
                    ScalarOutputSpec("utility_last", "utility", "last", both_scopes),
                ),
                expected_cost=0.5,
                cost_unit="second",
                evaluation_scopes=both_scopes,
            ),
        ),
        couplings=(
            CouplingSpec("source", "driver", "transform", "driver"),
            CouplingSpec("transform", "flow", "score", "flow"),
        ),
        objective=TerminalObjectiveSpec("utility", "score", "utility_last", "maximize"),
        constraints=(
            TerminalConstraintSpec("minimum_flow", "transform", "flow_mean", ">=", 0.0),
        ),
        evaluation_scopes=(EvaluationScope.SYSTEM, EvaluationScope.COMPONENT),
    )


def test_function_network_round_trips_canonical_json_and_yaml(
    tmp_path, network_system, network_spec
):
    json_text = network_spec.to_json()
    assert FunctionNetworkSpec.from_json(json_text) == network_spec
    assert FunctionNetworkSpec.from_json(json_text).to_json() == json_text
    assert json.dumps(json.loads(json_text), separators=(",", ":")) == json_text

    path = tmp_path / "network.yaml"
    network_spec.to_yaml(path)
    first = path.read_bytes()
    loaded = FunctionNetworkSpec.from_yaml(path)
    loaded.to_yaml(path)

    assert loaded == network_spec
    assert path.read_bytes() == first
    assert loaded.validate(network_system) == ("source", "transform", "score")


def test_function_network_records_are_immutable(network_spec):
    with pytest.raises(FrozenInstanceError):
        network_spec.name = "changed"
    with pytest.raises(FrozenInstanceError):
        network_spec.components[1].expected_cost = 2.0
    with pytest.raises(TypeError):
        network_spec.component_map["other"] = network_spec.components[0]


@pytest.mark.parametrize(
    "reducer",
    ("mean", "sum", "minimum", "maximum", "last"),
)
def test_scalar_reducers_return_finite_values(reducer):
    assert isinstance(reduce_scalar([1.0, 2.0, 3.0], reducer), float)
    assert scalar_observation_name("routing", "peak") == "routing.peak"


def test_function_network_rejects_duplicate_components_parameters_ports_and_outputs(network_spec):
    transform = network_spec.components[1]
    with pytest.raises(ValueError, match="duplicate component"):
        replace(network_spec, components=(*network_spec.components, transform))
    with pytest.raises(ValueError, match="duplicate parameter"):
        replace(transform, parameters=(*transform.parameters, transform.parameters[0]))
    with pytest.raises(ValueError, match="duplicate port"):
        replace(transform, outputs=(*transform.outputs, transform.outputs[0]))
    with pytest.raises(ValueError, match="duplicate scalar output"):
        replace(transform, scalar_outputs=(*transform.scalar_outputs, transform.scalar_outputs[0]))


def test_function_network_rejects_duplicate_coupling_input_ownership(network_spec):
    conflicting = CouplingSpec("score", "utility", "transform", "driver")
    with pytest.raises(ValueError, match="only one owner"):
        replace(network_spec, couplings=(*network_spec.couplings, conflicting))


def test_validation_rejects_unknown_and_missing_components(network_system, network_spec):
    missing = replace(network_spec, components=network_spec.components[:-1])
    with pytest.raises(ValueError, match="components differ"):
        missing.validate(network_system)
    unknown = replace(network_spec.components[-1], component="other")
    replaced = replace(network_spec, components=(*network_spec.components[:-1], unknown))
    with pytest.raises(ValueError, match="components differ"):
        replaced.validate(network_system)


def test_validation_rejects_system_cycles(network_system, network_spec):
    source = network_system.get_component("source")
    source.add_input("feedback", data_type="timeseries", units="point")
    network_system.connect("score", "source", "utility", "feedback")
    represented_source = replace(
        network_spec.components[0],
        inputs=(FunctionPortSpec("feedback", "in", "timeseries", "point"),),
    )
    cycle = CouplingSpec("score", "utility", "source", "feedback")
    cyclic_spec = replace(
        network_spec,
        components=(represented_source, *network_spec.components[1:]),
        couplings=(*network_spec.couplings, cycle),
    )
    with pytest.raises(ValueError, match="acyclic"):
        cyclic_spec.validate(network_system)


def test_validation_rejects_dangling_and_incomplete_couplings(network_system, network_spec):
    dangling = replace(network_spec.couplings[0], source_port="absent")
    with pytest.raises(ValueError, match="couplings differ"):
        replace(network_spec, couplings=(dangling, *network_spec.couplings[1:])).validate(
            network_system
        )
    with pytest.raises(ValueError, match="couplings differ"):
        replace(network_spec, couplings=network_spec.couplings[:-1]).validate(network_system)


def test_validation_rejects_incompatible_types_and_units(network_system, network_spec):
    transform = network_spec.components[1]
    wrong_type = replace(transform.inputs[0], data_type="scalar")
    with pytest.raises(ValueError, match="data type"):
        replace(
            network_spec,
            components=(
                network_spec.components[0],
                replace(transform, inputs=(wrong_type,)),
                network_spec.components[2],
            ),
        ).validate(network_system)

    wrong_units = replace(transform.inputs[0], units="kelvin")
    with pytest.raises(ValueError, match="units"):
        replace(
            network_spec,
            components=(
                network_spec.components[0],
                replace(transform, inputs=(wrong_units,)),
                network_spec.components[2],
            ),
        ).validate(network_system)


def test_representation_rejects_incompatible_observation_declarations(network_spec):
    transform = network_spec.components[1]
    component_only = replace(
        transform.scalar_outputs[0], observed_in=(EvaluationScope.COMPONENT,)
    )
    invalid_terminal = replace(
        network_spec,
        components=(
            network_spec.components[0],
            replace(transform, scalar_outputs=(component_only,)),
            network_spec.components[2],
        ),
    )
    with pytest.raises(ValueError, match="system-observable"):
        invalid_terminal.validate(_system_from_spec_fixture())

    with pytest.raises(ValueError, match="not permitted"):
        replace(
            transform,
            scalar_outputs=(
                replace(
                    transform.scalar_outputs[0],
                    observed_in=(EvaluationScope.SYSTEM, EvaluationScope.COMPONENT),
                ),
            ),
            evaluation_scopes=(EvaluationScope.SYSTEM,),
        )


def _system_from_spec_fixture():
    """Create the system outside fixture injection for one construction regression."""
    system = System("synthetic-chain")
    source = system.add_component("source", outputs={"driver": "timeseries"})
    source.outputs[0].units = "mm/day"
    transform = system.add_component(
        "transform",
        inputs={"driver": "timeseries"},
        outputs={"flow": "timeseries"},
        metadata={
            "runnable": {
                "kind": "python",
                "entry": "synthetic:transform",
                "inputs": ["driver"],
                "outputs": ["flow"],
                "params": {"gain": 1.0},
            }
        },
    )
    transform.inputs[0].units = "mm/day"
    transform.outputs[0].units = "m3/s"
    score = system.add_component(
        "score",
        inputs={"flow": "timeseries"},
        outputs={"utility": "timeseries"},
        metadata={
            "runnable": {
                "kind": "python",
                "entry": "synthetic:score",
                "inputs": ["flow"],
                "outputs": ["utility"],
                "params": {"offset": 0.0},
            }
        },
    )
    score.inputs[0].units = "m3/s"
    score.outputs[0].units = "point"
    system.connect("source", "transform", "driver", "driver")
    system.connect("transform", "score", "flow", "flow")
    return system


def _synthetic_runner(component, inputs):
    params = component.metadata["runnable"]["params"]
    if component.name == "transform":
        return {"flow": np.asarray(inputs["driver"]) * params["gain"]}
    if component.name == "score":
        flow = np.asarray(inputs["flow"])
        return {"utility": 10.0 - (flow - 4.0) ** 2 + params["offset"]}
    raise AssertionError(f"unexpected component {component.name!r}")


def _clock(start=0.0, stop=1.0):
    values = iter((start, stop))
    return lambda: next(values)


def _evaluation_context(tmp_path, system, *, parents=None):
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(mode=0o700, exist_ok=True)
    artifact_dir.chmod(0o700)
    alternatives = {
        name: {"base": system.get_component(name)} for name in ("transform", "score")
    }
    return EvaluationContext(
        system=system,
        alternatives=alternatives,
        source_arrays={"source.driver": np.array([1.0, 2.0, 3.0])},
        observed={},
        outcome_functions={"placeholder": lambda _: 0.0},
        cost_unit="second",
        artifact_dir=artifact_dir,
        parent_artifacts={} if parents is None else parents,
    )


def test_function_network_evaluates_system_and_component_actions_and_replays_tables(
    tmp_path, network_system, network_spec
):
    ledger = ObservationLedger(tmp_path / "observations.jsonl")
    system_action = EvaluationAction.system(
        "eval-000001",
        {
            "transform.choice": "base",
            "transform.gain": 2.0,
            "score.choice": "base",
            "score.offset": 1.0,
        },
        seed=11,
    )
    context = _evaluation_context(tmp_path, network_system)
    system_result = FunctionNetworkEvaluator(
        network_spec, context, runner=_synthetic_runner, clock=_clock()
    ).evaluate(system_action)
    assert system_result.status is EvaluationStatus.SUCCESS
    assert system_result.cost == 1.0
    assert system_result.outcomes == {
        "source.driver_mean": 2.0,
        "transform.flow_mean": 4.0,
        "score.utility_last": 7.0,
        "utility": 7.0,
        "minimum_flow": 4.0,
    }
    assert len(system_result.artifacts) == 1
    ledger.append(system_action, system_result)

    parent_id = next(iter(system_result.artifacts))
    parent = ParentArtifactReference(
        system_result.artifacts[parent_id], system_result.artifact_sha256[parent_id]
    )
    component_context = _evaluation_context(tmp_path, network_system, parents={parent_id: parent})
    component_action = EvaluationAction.component(
        "eval-000002",
        "transform",
        {"transform.choice": "base", "transform.gain": 1.5},
        parent_artifact_ids=(parent_id,),
        seed=12,
    )
    component_result = FunctionNetworkEvaluator(
        network_spec,
        component_context,
        runner=_synthetic_runner,
        clock=_clock(2.0, 2.5),
    ).evaluate(component_action)
    assert component_result.status is EvaluationStatus.SUCCESS
    assert component_result.outcomes == {"transform.flow_mean": 3.0}
    assert component_result.cost == 0.5
    ledger.append(component_action, component_result)

    first = reconstruct_component_training_tables(network_spec, network_system, ledger)
    second = reconstruct_component_training_tables(
        network_spec, network_system, ObservationLedger(ledger.path)
    )
    assert first == second
    assert tuple(first) == ("source", "transform", "score")
    assert [row.action_id for row in first["transform"]] == ["eval-000001", "eval-000002"]
    assert first["transform"][0].inputs == {
        "choice": "base",
        "gain": 2.0,
        "source.driver_mean": 2.0,
    }
    assert first["transform"][1].outputs == {"flow_mean": 3.0}
    assert first["transform"][1].artifact_ids == (
        parent_id,
        next(iter(component_result.artifacts)),
    )
    assert first["score"][0].inputs["transform.flow_mean"] == 4.0

    record = json.loads(ledger.path.read_text(encoding="utf-8").splitlines()[0])
    assert all(isinstance(value, (int, float)) for value in record["result"]["outcomes"].values())
    assert record["result"]["artifacts"] == dict(system_result.artifacts)


def test_function_network_component_scope_requires_permission_parents_and_observations(
    tmp_path, network_system, network_spec
):
    context = _evaluation_context(tmp_path, network_system)
    evaluator = FunctionNetworkEvaluator(network_spec, context, runner=_synthetic_runner)
    missing_parent = EvaluationAction.component(
        "eval-000001",
        "transform",
        {"transform.choice": "base", "transform.gain": 1.0},
    )
    with pytest.raises(ValueError, match="requires declared parent"):
        evaluator.evaluate(missing_parent)

    source_action = EvaluationAction.component("eval-000002", "source", {})
    with pytest.raises(ValueError, match="does not permit"):
        evaluator.evaluate(source_action)

    undeclared = EvaluationAction.system("eval-000003", {"score.absent": 1.0})
    with pytest.raises(ValueError, match="undeclared parameters"):
        evaluator.evaluate(undeclared)


def test_verified_npz_rejects_digest_object_arrays_and_resource_excess(tmp_path):
    numeric = tmp_path / "numeric.npz"
    np.savez(numeric, values=np.array([1.0, 2.0]))
    digest = hashlib.sha256(numeric.read_bytes()).hexdigest()
    loaded = read_verified_npz(numeric, digest)
    assert np.array_equal(loaded["values"], np.array([1.0, 2.0]))
    assert loaded["values"].flags.writeable is False

    with pytest.raises(FunctionNetworkArtifactError, match="SHA-256"):
        read_verified_npz(numeric, "0" * 64)
    with pytest.raises(FunctionNetworkArtifactError, match="compressed byte"):
        read_verified_npz(numeric, digest, limits=NpzReadLimits(max_compressed_bytes=1))

    objects = tmp_path / "objects.npz"
    np.savez(objects, values=np.array([{"unsafe": True}], dtype=object))
    object_digest = hashlib.sha256(objects.read_bytes()).hexdigest()
    with pytest.raises(FunctionNetworkArtifactError, match="object arrays"):
        read_verified_npz(objects, object_digest)

    member = io.BytesIO()
    np.lib.format.write_array(member, np.array([1.0]), allow_pickle=False)
    unsafe = tmp_path / "unsafe.npz"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("../values.npy", member.getvalue())
    unsafe_digest = hashlib.sha256(unsafe.read_bytes()).hexdigest()
    with pytest.raises(FunctionNetworkArtifactError, match="member name is unsafe"):
        read_verified_npz(unsafe, unsafe_digest)

    with pytest.raises(FunctionNetworkArtifactError, match="cannot be opened"):
        read_verified_npz(tmp_path / "missing.npz", "0" * 64)


def test_training_reconstruction_rejects_changed_and_unknown_parent_artifacts(
    tmp_path, network_system, network_spec
):
    artifact = tmp_path / "trace.npz"
    np.savez(
        artifact,
        **{
            "source.driver": np.array([1.0]),
            "transform.flow": np.array([2.0]),
            "score.utility": np.array([3.0]),
        },
    )
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    action = EvaluationAction.component(
        "eval-000001",
        "transform",
        {"transform.choice": "base", "transform.gain": 2.0},
        parent_artifact_ids=("future",),
    )
    result = EvaluationResult.success(
        action.id,
        {"transform.flow_mean": 2.0},
        {},
        1.0,
        "second",
        artifacts={"trace": str(artifact)},
        artifact_sha256={"trace": digest},
    )

    class EntriesOnly:
        def entries(self):
            return ((action, result),)

    with pytest.raises(FunctionNetworkArtifactError, match="unknown or not from an earlier"):
        reconstruct_component_training_tables(network_spec, network_system, EntriesOnly())

    artifact.write_bytes(b"changed")
    with pytest.raises(FunctionNetworkArtifactError, match="SHA-256"):
        read_verified_npz(artifact, digest)


def test_training_reconstruction_rejects_duplicate_artifact_ids(
    tmp_path, network_system, network_spec
):
    artifact = tmp_path / "trace.npz"
    np.savez(
        artifact,
        **{
            "source.driver": np.array([1.0]),
            "transform.flow": np.array([2.0]),
            "score.utility": np.array([3.0]),
        },
    )
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    actions = tuple(
        EvaluationAction.system(
            f"eval-{index:06d}",
            {
                "transform.choice": "base",
                "transform.gain": 2.0,
                "score.choice": "base",
                "score.offset": 0.0,
            },
        )
        for index in (1, 2)
    )
    outcomes = {
        "source.driver_mean": 1.0,
        "transform.flow_mean": 2.0,
        "score.utility_last": 3.0,
        "utility": 3.0,
        "minimum_flow": 2.0,
    }
    results = tuple(
        EvaluationResult.success(
            action.id,
            outcomes,
            {},
            1.0,
            "second",
            artifacts={"same": str(artifact)},
            artifact_sha256={"same": digest},
        )
        for action in actions
    )

    class EntriesOnly:
        def entries(self):
            return tuple(zip(actions, results, strict=True))

    with pytest.raises(FunctionNetworkArtifactError, match="duplicate artifact ID"):
        reconstruct_component_training_tables(network_spec, network_system, EntriesOnly())


def test_checked_function_network_example_replays_scientific_tables(tmp_path):
    root = Path(__file__).resolve().parents[1]
    script = root / "examples" / "function_network" / "run_example.py"
    expected = json.loads(
        (script.parent / "expected-result.json").read_text(encoding="utf-8")
    )
    results = []
    for name in ("first", "second"):
        output = tmp_path / name
        completed = subprocess.run(
            [sys.executable, str(script), "--output", str(output)],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        assert "reconstructed 4 component rows" in completed.stdout
        result = json.loads((output / "training-tables.json").read_text(encoding="utf-8"))
        for rows in result["training_tables"].values():
            for row in rows:
                row.pop("artifact_ids")
                row.pop("artifact_sha256")
        results.append(result)
    assert results == [expected, expected]


def test_function_network_imports_do_not_load_bayesian_dependencies():
    command = [
        sys.executable,
        "-c",
        "import autoengineering.optimization.function_network; "
        "import autoengineering.optimization.function_network_evaluator; "
        "import sys; blocked={'torch','botorch','gpytorch','smac'}; "
        "assert not (blocked & {name.split('.')[0] for name in sys.modules})",
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
