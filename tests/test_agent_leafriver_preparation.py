"""Fresh matched Leaf River manifests without model execution or changed old evidence."""

from dataclasses import replace
import hashlib
import json
import shutil

import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.identity import scientific_identity, scientific_source_paths
from autoengineering.campaign.spec import CampaignSpec
from examples.agent_campaign import prepare_leafriver as leaf


def hashes(root):
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    root = tmp_path_factory.mktemp("matched-leaf") / "proposal"
    old = leaf.ROOT / "examples/campaign_contracts/profile"
    before = hashes(old)
    # Preparation must not initialize a runtime, subprocess, host or numerical model.
    with pytest.MonkeyPatch.context() as patch:
        import subprocess
        from autoengineering.campaign.controller import CampaignController
        from examples.campaign_contracts.hydrology import HydrologyAdapter

        def forbidden(*args, **kwargs):
            raise AssertionError("preparation attempted execution")

        patch.setattr(subprocess, "Popen", forbidden)
        patch.setattr(CampaignController, "create", forbidden)
        patch.setattr(HydrologyAdapter, "prepare", forbidden)
        patch.setattr(HydrologyAdapter, "run", forbidden)
        plan = leaf.prepare(root)
        first = hashes(root)
        assert leaf.load(root, expected_digest=plan.digest) == plan
        assert hashes(root) == first
    assert hashes(old) == before
    return root, plan


def test_fresh_routes_preserve_data_science_and_exposure(prepared):
    root, plan = prepared
    assert leaf.LeafPreparation.from_json(plan.to_json()) == plan
    assert tuple(row.route for row in plan.routes) == leaf.ROUTES
    template = CampaignSpec.from_yaml(root / plan.template.path)
    specs = [CampaignSpec.from_yaml(root / row.specification.path) for row in plan.routes]
    assert len({row.scientific_identity for row in plan.routes}) == 3
    assert len({spec.name for spec in specs}) == 3
    for row, spec in zip(plan.routes, specs):
        assert spec.data == template.data
        assert spec.calibration == template.calibration
        assert spec.acceptance == template.acceptance
        assert spec.interventions == template.interventions
        assert spec.workflow == template.workflow
        assert spec.seed == 17 and spec.confirmation == template.confirmation
        assert spec.execution == replace(template.execution, max_executions=38)
        assert spec.baseline == replace(
            template.baseline,
            model=replace(
                template.baseline.model,
                source_bundle=spec.provenance.sources,
                dependency_bundle=spec.provenance.environment_lock.sha256,
            ),
        )
        assert spec.source_bundle == "scientific-core-v1"
        assert scientific_identity(spec, root / "captured_source") == row.scientific_identity
        paths = {ref.path for ref in spec.provenance.sources}
        assert set(scientific_source_paths()) <= paths
        assert not any("/agents/" in p or "/prompts/" in p for p in paths)
        assert paths == {*leaf.SOURCES, *scientific_source_paths()}
    audit = json.loads((root / plan.audit.path).read_text())
    assert audit["development_split_counts"] == {"warmup": 90, "fitting": 183, "comparison": 92}
    assert audit["historical_split_counts"] == {
        "test": 366,
        "train": 183,
        "validation": 92,
        "warmup": 90,
    }
    assert audit["scientific_starts"] == audit["provider_calls"] == 0
    assert (
        not audit["clock_started"] and not audit["runtime_created"] and not audit["execution_ready"]
    )
    assert audit["aggregate_scientific_starts"] == 114
    assert audit["aggregate_live_host_invocations"] == 40
    assert audit["live_route_limits"] == leaf.LIVE_LIMITS.to_dict()
    assert "exposed" in audit["exposure"] and audit["confirmation"] == "confirmation_not_attempted"
    assert not any(
        p.name in ("events", "control", "worker", "processes", "manifest.json")
        for p in root.rglob("*")
    )


def test_complete_pool_accounting_uses_absent_default_and_fresh_comparison(prepared):
    root, plan = prepared
    spec = CampaignSpec.from_yaml(root / plan.routes[0].specification.path)
    allocation = leaf.allocation(spec)
    assert allocation == {
        "baseline_default": 1,
        "children": [
            {
                "candidate": "pet-hamon-v1",
                "additional_default": 0,
                "fitting": 16,
                "selected_comparison": 1,
                "child_reservation": 17,
                "causality": 1,
            },
            {
                "candidate": "pet-hargreaves-v1",
                "additional_default": 1,
                "fitting": 16,
                "selected_comparison": 1,
                "child_reservation": 18,
                "causality": 1,
            },
        ],
        "total": 38,
    }
    for bad in (
        replace(spec, seed=18),
        replace(spec, calibration=None),
        replace(spec, workflow=replace(spec.workflow, max_candidates=1)),
        replace(spec, execution=replace(spec.execution, max_executions=39)),
        replace(spec, execution=replace(spec.execution, diagnostics="none")),
    ):
        with pytest.raises(ValueError):
            leaf.allocation(bad)


@pytest.mark.parametrize(
    "change", ["pin", "capture", "route", "template", "audit", "recipe", "symlink"]
)
def test_changed_preparation_is_rejected(prepared, tmp_path, change):
    original, plan = prepared
    root = tmp_path / "proposal"
    shutil.copytree(original, root)
    pin = plan.digest
    if change == "pin":
        pin = "0" * 64
    elif change in ("template", "audit", "recipe"):
        ref = getattr(plan, change)
        (root / ref.path).write_bytes(b"changed")
    elif change == "capture":
        (root / plan.inputs[0].path).write_bytes(b"changed")
    elif change == "route":
        (root / plan.routes[0].specification.path).write_bytes(b"changed")
    else:
        path = root / plan.inputs[0].path
        target = tmp_path / "replacement"
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    with pytest.raises((ValueError, OSError)):
        leaf.load(root, expected_digest=pin)


def test_repinning_route_cannot_relax_fixed_science(prepared, tmp_path):
    original, plan = prepared
    root = tmp_path / "proposal"
    shutil.copytree(original, root)
    row = plan.routes[0]
    path = root / row.specification.path
    spec = CampaignSpec.from_yaml(path)
    spec = replace(spec, acceptance=replace(spec.acceptance, minimum_gain=0.0))
    spec.to_yaml(path)
    row = replace(
        row,
        specification=reference(
            root,
            row.specification.path,
            media_type="application/yaml",
            producer="matched-profile-author",
        ),
        scientific_identity=scientific_identity(spec, root / "captured_source"),
    )
    altered = replace(plan, routes=(row, *plan.routes[1:]))
    (root / "leaf-preparation.json").write_text(altered.to_json())
    with pytest.raises(ValueError, match="changed science"):
        leaf.load(root, expected_digest=altered.digest)


def test_preparation_refuses_reuse_and_bad_cache_before_writes(prepared, tmp_path, monkeypatch):
    root, _ = prepared
    before = hashes(root)
    with pytest.raises(ValueError, match="absent"):
        leaf.prepare(root)
    assert hashes(root) == before

    def bad():
        raise ValueError("cache audit failed")

    monkeypatch.setattr(leaf, "audit_cache", bad)
    output = tmp_path / "new"
    with pytest.raises(ValueError, match="cache audit failed"):
        leaf.prepare(output)
    assert not output.exists()


def test_added_host_files_do_not_change_scientific_identity(prepared, tmp_path):
    original, plan = prepared
    root = tmp_path / "proposal"
    shutil.copytree(original, root)
    path = root / "captured_source/src/autoengineering/agents/prompts/new.txt"
    path.parent.mkdir(parents=True)
    path.write_text("Unrelated changed host prompt")
    assert leaf.load(root, expected_digest=plan.digest) == plan


def test_module_verification_reports_no_execution(prepared, monkeypatch, capsys):
    root, plan = prepared
    monkeypatch.setattr(
        "sys.argv", ["prepare_leafriver", "--output", str(root), "--verify", plan.digest]
    )
    leaf.main()
    result = json.loads(capsys.readouterr().out)
    assert result == {
        "status": "prepared",
        "preparation_digest": plan.digest,
        "scientific_starts": 0,
        "provider_calls": 0,
        "execution_ready": False,
    }


@pytest.mark.parametrize(
    "name", ["examples/local_models/data/hydro.csv", "examples/leaf_river/data/weather.csv"]
)
def test_repinning_cache_cannot_change_historical_inputs(prepared, tmp_path, name):
    original, plan = prepared
    root = tmp_path / "proposal"
    shutil.copytree(original, root)
    relative = f"captured_source/{name}"
    path = root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    new = reference(
        root, relative, media_type="application/octet-stream", producer="matched-capture"
    )
    altered = replace(
        plan, inputs=tuple(new if ref.path == relative else ref for ref in plan.inputs)
    )
    (root / "leaf-preparation.json").write_text(altered.to_json())
    with pytest.raises(ValueError):
        leaf.load(root, expected_digest=altered.digest)


def test_repinning_audit_cannot_invent_split_counts_or_claim_a_clock(prepared, tmp_path):
    original, plan = prepared
    root = tmp_path / "proposal"
    shutil.copytree(original, root)
    path = root / plan.audit.path
    audit = json.loads(path.read_text())
    audit["historical_split_counts"]["test"] = 0
    audit["clock_started"] = 0
    path.write_text(json.dumps(audit))
    altered = replace(
        plan,
        audit=reference(
            root, plan.audit.path, media_type="application/json", producer="matched-preparation"
        ),
    )
    (root / "leaf-preparation.json").write_text(altered.to_json())
    with pytest.raises(ValueError, match="audit differs"):
        leaf.load(root, expected_digest=altered.digest)


def test_missing_captured_input_is_not_repaired_by_current_checkout(prepared, tmp_path):
    original, plan = prepared
    root = tmp_path / "proposal"
    shutil.copytree(original, root)
    (root / "captured_source/examples/campaign_contracts/hydrology.py").unlink()
    with pytest.raises((ValueError, OSError)):
        leaf.load(root, expected_digest=plan.digest)
