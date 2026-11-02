"""Native comparison preparation using authored host metadata, without execution."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from autoengineering.agents.conformance import prepare_conformance
from autoengineering.agents.batch import BatchStore
from autoengineering.agents.records import AgentRunSpec
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.serialization import digest
from examples.agent_campaign import native_comparison as native
from test_agent_conformance import fixture as host_fixture
from test_agent_leafriver_preparation import prepared as prepared


def snapshot(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def fixture(tmp_path, monkeypatch, prepared):
    root, worker, config, _, calls = host_fixture(tmp_path, monkeypatch)
    conformance = prepare_conformance(
        worker,
        root / "campaign",
        config,
        tmp_path / "conformance",
        tmp_path / "conformance-runtime",
    )
    leaf_root, leaf = prepared
    return root, worker, config, calls, leaf_root, leaf, conformance


def capture(tmp_path, monkeypatch, prepared):
    root, worker, config, calls, leaf_root, leaf, conformance = fixture(
        tmp_path, monkeypatch, prepared
    )
    output = tmp_path / "native"
    plan = native.prepare(
        leaf_root,
        leaf_digest=leaf.digest,
        conformance_root=tmp_path / "conformance",
        conformance_digest=conformance.digest,
        template=worker,
        configuration=config,
        output=output,
        runtime_root=tmp_path / "native-runtime",
    )
    return output, plan, config, calls


def test_capture_binds_three_leaf_workers_and_conformance_without_work(
    tmp_path, monkeypatch, prepared
):
    root, worker, config, calls, leaf_root, leaf, conformance = fixture(
        tmp_path, monkeypatch, prepared
    )
    before = snapshot(leaf_root), snapshot(tmp_path / "conformance")

    def forbidden(*args, **kwargs):
        raise AssertionError("native preparation attempted execution")

    import subprocess

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(CampaignController, "create", forbidden)
    monkeypatch.setattr(BatchStore, "create", forbidden)
    output = tmp_path / "native"
    plan = native.prepare(
        leaf_root,
        leaf_digest=leaf.digest,
        conformance_root=tmp_path / "conformance",
        conformance_digest=conformance.digest,
        template=worker,
        configuration=config,
        output=output,
        runtime_root=tmp_path / "native-runtime",
    )
    assert native.NativePreparation.from_json(plan.to_json()) == plan
    assert not calls and not config.credential_path.exists()
    assert (
        not (tmp_path / "conformance-runtime").exists()
        and not (tmp_path / "native-runtime").exists()
    )
    assert (snapshot(leaf_root), snapshot(tmp_path / "conformance")) == before
    assert [c.worker.host.kind for c in plan.cases] == ["fake", "codex", "codex"]
    assert [c.worker.workflow_route for c in plan.cases] == [
        "four_role",
        "single_agent",
        "four_role",
    ]
    assert [c.host_invocations for c in plan.batch.cases] == [0, 20, 20]
    assert [c.scientific_starts for c in plan.batch.cases] == [38, 38, 38]
    assert plan.batch.scientific_starts == 114
    assert [c.worker.campaign_identity for c in plan.cases] == [
        r.scientific_identity for r in leaf.routes
    ]
    assert plan.batch.host == worker.host and plan.batch.host_configuration_digest == config.digest
    assert plan.conformance.sha256 == conformance.digest
    first = snapshot(output)
    report = native.inspect(output, expected_digest=plan.digest, configuration=config)
    assert report["execution_ready"] is False and report["runtime_created"] is False
    assert report["clock_started"] is False and report["credential_opened"] is False
    assert report["provider_calls"] == report["scientific_starts"] == 0
    assert report["authorization"] == "not_granted_by_preparation"
    assert snapshot(output) == first
    assert all(not (p.stat().st_mode & 0o077) for p in output.rglob("*") if p.is_dir())


@pytest.mark.parametrize(
    "problem", ["pin", "recipe", "leaf", "conformance", "budget", "worker", "runtime"]
)
def test_changes_are_rejected_before_runtime_or_lease_use(tmp_path, monkeypatch, prepared, problem):
    output, plan, config, calls = capture(tmp_path, monkeypatch, prepared)
    pin = plan.digest
    if problem == "pin":
        pin = "0" * 64
    elif problem == "recipe":
        (output / plan.recipe.path).write_bytes(b"changed")
    elif problem == "leaf":
        (
            output / "leaf/captured_source/examples/campaign_contracts/profile/forcing.npz"
        ).write_bytes(b"changed")
    elif problem == "conformance":
        (
            output / "conformance/captured_source/examples/campaign_contracts/forcing.json"
        ).write_bytes(b"changed")
    elif problem == "runtime":
        Path(plan.runtime_root).mkdir(mode=0o700)
    else:
        data = plan.to_dict()
        if problem == "budget":
            data["batch"]["limits"]["max_invocations"] = 41
        else:
            data["cases"][1]["worker"]["permitted_interventions"] = ["hargreaves-v1"]
        (output / "native-comparison.json").write_text(json.dumps(data))
        pin = digest(data)
    with pytest.raises(ValueError):
        native.load(output, expected_digest=pin, configuration=config)
    assert not calls and not config.credential_path.exists()


def test_host_or_conformance_scope_cannot_change(tmp_path, monkeypatch, prepared):
    output, plan, config, calls = capture(tmp_path, monkeypatch, prepared)
    with pytest.raises(ValueError):
        native.load(
            output,
            expected_digest=plan.digest,
            configuration=replace(config, lease_id="another-account-source"),
        )
    with pytest.raises(ValueError, match="absent"):
        native.prepare(
            prepared[0],
            leaf_digest=prepared[1].digest,
            conformance_root=tmp_path / "conformance",
            conformance_digest=plan.conformance.sha256,
            template=AgentRunSpec.from_file(output / plan.template.path),
            configuration=config,
            output=output,
            runtime_root=tmp_path / "other",
        )
    assert not calls


def test_authored_or_incomplete_conformance_does_not_enable_execution(
    tmp_path, monkeypatch, prepared
):
    output, plan, config, calls = capture(tmp_path, monkeypatch, prepared)
    observed = []

    def authored(root, *, expected_digest):
        observed.append((root, expected_digest))
        return {"status": "completed", "live_conformance_complete": False}

    monkeypatch.setattr(native, "conformance_report", authored)
    with pytest.raises(ValueError, match="real-provider conformance"):
        native.verify_conformance_prerequisite(
            output, expected_digest=plan.digest, configuration=config, runtime_digest="a" * 64
        )
    assert observed and not calls and not Path(plan.runtime_root).exists()


@pytest.mark.parametrize("problem", [None, "preparation", "specification"])
def test_conformance_binding_with_explicit_authored_report_stub(
    tmp_path, monkeypatch, prepared, problem
):
    from autoengineering.agents.conformance import load_conformance

    output, plan, config, calls = capture(tmp_path, monkeypatch, prepared)
    required = load_conformance(
        output / "conformance",
        expected_digest=plan.conformance.sha256,
        configuration=config,
        allow_runtime=True,
    )
    spec = (
        replace(required.batch, scientific_starts=3)
        if problem == "specification"
        else required.batch
    )
    observed = BatchStore.create(required.runtime_root, spec)
    # This stubs only a unit-test report. The unmodified real reader would call
    # this empty runtime ready, never completed real-provider conformance.
    monkeypatch.setattr(
        native,
        "conformance_report",
        lambda *a, **k: {
            "status": "completed",
            "live_conformance_complete": True,
            "preparation_digest": "f" * 64 if problem == "preparation" else plan.conformance.sha256,
        },
    )
    if problem:
        with pytest.raises(ValueError, match="differs from frozen"):
            native.verify_conformance_prerequisite(
                output,
                expected_digest=plan.digest,
                configuration=config,
                runtime_digest=observed.digest,
            )
    else:
        result = native.verify_conformance_prerequisite(
            output,
            expected_digest=plan.digest,
            configuration=config,
            runtime_digest=observed.digest,
        )
        assert result["conformance_runtime_digest"] == observed.digest
        assert result["authorization"] == "not_granted_by_prerequisite"
        assert result["execution_ready"] is False
    assert not calls and not Path(plan.runtime_root).exists()
