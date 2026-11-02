"""Scientific proposal choices bind references without labels, models or admission."""

from dataclasses import replace
from pathlib import Path
import socket
import builtins
import hashlib
import json
import subprocess

import pytest

from autoengineering.campaign.artifacts import put_bytes, read_bytes
from autoengineering.campaign.records import ArtifactRef
from examples.utility import confirmation_choices as module


def ref(task="hydrology", value=2.0):
    metric, units, _, _ = module.RULES[task]
    return module.DevelopmentReference(
        "utility-proposal-development-reference-v1",
        task,
        "development",
        "unchanged_baseline",
        metric,
        units,
        value,
        "1" * 64,
        "2" * 64,
        "3" * 64,
    )


@pytest.mark.parametrize("task", tuple(module.RULES))
def test_absolute_margin_uses_the_pinned_development_reference(tmp_path, task):
    tmp_path.chmod(0o700)
    (tmp_path / "artifacts").mkdir(mode=0o700)
    source = ref(task)
    artifact = put_bytes(
        tmp_path,
        source.to_json().encode(),
        name="reference.json",
        media_type="application/json",
        producer="authored-test-reference",
    )
    bound = module.bind_reference(tmp_path, artifact)
    assert bound["absolute_gain"] == pytest.approx(source.value * module.RULES[task][3])
    assert bound["development_reference"] == artifact.to_dict()
    assert bound["status"] == "reference_bound_not_admitted"
    assert bound["starts_authorized"] is False
    path = tmp_path / artifact.path
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        module.bind_reference(tmp_path, artifact)


@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf"), True])
def test_invalid_reference_cannot_create_zero_margin(value):
    with pytest.raises((ValueError, TypeError)):
        ref(value=value)


def test_reference_units_route_and_phase_cannot_be_substituted():
    original = ref()
    for field, value in (
        ("phase", "confirmation"),
        ("route", "conventional"),
        ("units", "kW"),
        ("metric_id", "held_out_rmse"),
    ):
        with pytest.raises(ValueError):
            replace(original, **{field: value})


def test_underflow_cannot_create_a_zero_absolute_margin(tmp_path):
    tmp_path.chmod(0o700)
    (tmp_path / "artifacts").mkdir(mode=0o700)
    source = ref(value=5e-324)
    artifact = put_bytes(
        tmp_path,
        source.to_json().encode(),
        name="reference.json",
        media_type="application/json",
        producer="authored-test-reference",
    )
    with pytest.raises(ValueError, match="positive"):
        module.bind_reference(tmp_path, artifact)


def test_metadata_preparation_does_not_dispatch_or_import_models(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("proposal preparation attempted a process or socket")

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith(
            ("examples.leaf_river", "examples.utility.hydrology_", "openmdao", "pvlib", "py_wake")
        ):
            pytest.fail("proposal preparation imported a scientific model")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = module.build(Path(__file__).parents[1])
    assert result["starts_authorized"] is result["protocol_frozen"] is False
    assert result["observations_accessed"] is False
    assert result["planning_matrix"]["logical_cells"] == 560
    assert all(t["useful_gain_policy"]["absolute_gain"] is None for t in result["tasks"].values())
    assert all(t["exposure"] == "unknown_exposure" for t in result["tasks"].values())


def test_authored_engineering_grid_excludes_all_three_nominal_loads():
    scenarios = module.engineering_scenarios()
    assert len(scenarios) == len({s["scenario_id"] for s in scenarios}) == 24
    assert sum(s["weight"] for s in scenarios) == pytest.approx(1.0)
    assert all(
        (s["forcing"]["resistor1_ohm"], s["forcing"]["resistor2_ohm"]) != (100, 10000)
        for s in scenarios
    )
    assert {tuple(s["forcing"].values()) for s in scenarios} == {
        (g, r1, r2)
        for g in (-0.05, 0, 0.05)
        for r1 in (95, 100, 105)
        for r2 in (9500, 10000, 10500)
        if (r1, r2) != (100, 10000)
    }


def test_existing_proposal_directory_is_never_overwritten(tmp_path):
    with pytest.raises(ValueError, match="absent"):
        module.write(Path(__file__).parents[1], tmp_path)


def test_published_proposal_reconstructs_from_exact_declared_sources():
    root = Path(__file__).parents[1]
    packet = root / "examples/utility/proposals/confirmation-v2"
    proposal = json.loads((packet / "proposal.json").read_text())
    assert module.digest(module.build(root)) == module.digest(proposal)
    assert (
        proposal["producer_sha256"]
        == hashlib.sha256((packet / "producer.py.txt").read_bytes()).hexdigest()
    )
    for value in proposal["sources"]:
        read_bytes(root, ArtifactRef.from_dict(value))


def test_proposed_policies_do_not_admit_or_freeze_the_four_dossiers():
    root = Path(__file__).parents[1]
    for task in module.RULES:
        value = json.loads((root / f"examples/utility/tasks/{task}.json").read_text())
        assert value["status"] == "blocked_draft"
        assert value["minimum_useful_gain"] is value["secondary_tolerances"] is None
        assert value["confirmation"]["partition"] is None
        assert value["confirmation"]["status"] == "unknown_exposure"
