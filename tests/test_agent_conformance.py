"""Conformance preparation with authored native qualification and no credential use."""

from dataclasses import replace
import hashlib
import json

from click.testing import CliRunner
import pytest

from autoengineering.agents.conformance import (
    ConformancePreparation,
    prepare_conformance,
    inspect_conformance,
    LIMITS,
    POLICIES,
    IMPLEMENTED_CASES,
)
from autoengineering.agents.host_configuration import HostConfiguration
from autoengineering.agents.records import AgentRunSpec
from autoengineering.campaign.spec import CampaignSpec
from autoengineering.agents.conformance import _synthetic
from autoengineering.cli import cli
from test_agent_host_configuration import configured


def fixture(tmp_path, monkeypatch):
    root, config_file, calls = configured(tmp_path, monkeypatch)
    worker = AgentRunSpec.from_file(root / "agent-run.json")
    config = HostConfiguration.from_file(config_file)
    return root, worker, config, config_file, calls


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_prepare_captures_inputs_without_a_clock_lease_or_physical_work(tmp_path, monkeypatch):
    root, worker, config, _, calls = fixture(tmp_path, monkeypatch)
    before = snapshot(root)
    output, runtime = tmp_path / "proposal", tmp_path / "runtime"
    plan = prepare_conformance(worker, root / "campaign", config, output, runtime)
    assert ConformancePreparation.from_json(plan.to_json()) == plan
    assert not calls and not runtime.exists() and snapshot(root) == before
    assert plan.batch.limits == LIMITS and sum(c.host_invocations for c in plan.batch.cases) == 13
    assert sum(c.scientific_starts for c in plan.batch.cases) == 2
    first = snapshot(output)
    status = inspect_conformance(output, expected_digest=plan.digest, configuration=config)
    assert status["clock_started"] is False and status["runtime_created"] is False
    assert status["execution_ready"] is True
    assert status["missing_execution_handlers"] == [
        p[0] for p in POLICIES if p[0] not in IMPLEMENTED_CASES
    ]
    assert not calls and not runtime.exists() and snapshot(output) == first
    with pytest.raises(ValueError, match="fresh"):
        prepare_conformance(worker, root / "campaign", config, output, runtime)
    assert snapshot(output) == first


@pytest.mark.parametrize("problem", ["pin", "input", "worker", "budget", "runtime"])
def test_preparation_inspection_rejects_changed_bindings(tmp_path, monkeypatch, problem):
    root, worker, config, _, calls = fixture(tmp_path, monkeypatch)
    output, runtime = tmp_path / "proposal", tmp_path / "runtime"
    plan = prepare_conformance(worker, root / "campaign", config, output, runtime)
    pin = plan.digest
    if problem == "pin":
        pin = "0" * 64
    elif problem == "input":
        (output / plan.inputs[0].path).write_bytes(b"changed")
    elif problem == "runtime":
        runtime.mkdir(mode=0o700)
    else:
        value = plan.to_dict()
        if problem == "worker":
            value["worker"]["host"]["requested_model"] = "different"
        else:
            value["batch"]["limits"]["max_invocations"] += 1
        raw = json.dumps(value).encode()
        (output / "conformance.json").write_bytes(raw)
        pin = hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):
        inspect_conformance(output, expected_digest=pin, configuration=config)
    assert not calls


def test_different_host_metadata_fails_inspection_without_opening_lease(tmp_path, monkeypatch):
    root, worker, config, _, calls = fixture(tmp_path, monkeypatch)
    output = tmp_path / "proposal"
    plan = prepare_conformance(worker, root / "campaign", config, output, tmp_path / "runtime")
    with pytest.raises(ValueError, match="configuration or capabilities"):
        inspect_conformance(
            output, expected_digest=plan.digest, configuration=replace(config, lease_id="different")
        )
    assert not calls


def test_cli_prepare_and_inspect_produce_no_execution_and_do_not_modify_sources(
    tmp_path, monkeypatch
):
    root, _, _, config_file, calls = fixture(tmp_path, monkeypatch)
    output, runtime = tmp_path / "proposal", tmp_path / "runtime"
    result = CliRunner().invoke(
        cli,
        [
            "agents",
            "conformance-prepare",
            str(root / "agent-run.json"),
            "--campaign",
            str(root / "campaign"),
            "--host-config",
            str(config_file),
            "--output",
            str(output),
            "--runtime-root",
            str(runtime),
        ],
    )
    assert result.exit_code == 0, result.output
    status = json.loads(result.stdout)
    assert status["authorization"] == "not_granted_by_preparation" and status["provider_calls"] == 0
    inspected = CliRunner().invoke(
        cli,
        [
            "agents",
            "conformance-inspect",
            str(output),
            "--expected-digest",
            status["preparation_digest"],
        ],
    )
    assert inspected.exit_code == 0, inspected.output
    assert not calls and not runtime.exists() and not (root / "worker").exists()


def test_preparation_rejects_scope_overlap_before_writes(tmp_path, monkeypatch):
    root, worker, config, _, calls = fixture(tmp_path, monkeypatch)
    output = tmp_path / "proposal"
    with pytest.raises(ValueError, match="separate roots"):
        prepare_conformance(worker, root / "campaign", config, output, output / "runtime")
    assert not output.exists() and not calls


@pytest.mark.parametrize("problem", ["criterion", "source", "data_path"])
def test_fixed_protocol_rejects_relaxed_science_or_extra_source_before_reading(
    tmp_path, monkeypatch, problem
):
    root, _, _, _, _ = fixture(tmp_path, monkeypatch)
    spec = CampaignSpec.from_yaml(root / "campaign/campaign.yaml")
    if problem == "criterion":
        spec = replace(spec, acceptance=replace(spec.acceptance, minimum_gain=0))
    elif problem == "source":
        ref = replace(spec.provenance.sources[0], path="private-not-a-source")
        spec = replace(
            spec, provenance=replace(spec.provenance, sources=(*spec.provenance.sources, ref))
        )
    else:
        spec = replace(
            spec,
            data=(
                replace(
                    spec.data[0], artifact=replace(spec.data[0].artifact, path="private-not-data")
                ),
                *spec.data[1:],
            ),
        )
    from autoengineering.agents import conformance

    monkeypatch.setattr(
        conformance, "read_bytes", lambda *a, **k: pytest.fail("unapproved source read")
    )
    with pytest.raises(ValueError):
        _synthetic(spec, root / "campaign/bundle")
