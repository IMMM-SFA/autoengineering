"""New scientific closures exclude hosts while old resume checks remain strict."""

from dataclasses import replace
from pathlib import Path

import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.identity import (
    SCIENTIFIC_CLOSURE,
    ISOLATED_SCIENTIFIC_CLOSURE,
    ISOLATED_SOURCES,
    scientific_identity,
    scientific_source_paths,
    verify_runtime_sources,
)
from autoengineering.campaign.spec import CampaignSpec
from examples.agent_campaign.fixture import agent_fixture
from examples.campaign_contracts.build_fixture import ROOT


def test_explicit_scientific_closure_excludes_worker_modules():
    spec = agent_fixture()
    paths = {ref.path for ref in spec.provenance.sources}
    assert SCIENTIFIC_CLOSURE in paths
    assert not any("/agents/" in path for path in paths)
    verify_runtime_sources(spec)
    assert scientific_identity(spec, ROOT)
    assert spec.baseline.model.source_bundle == spec.provenance.sources


def test_host_only_changes_do_not_change_scientific_identity(tmp_path):
    spec = agent_fixture()
    # Copy the actual declared closure and inputs to a different root. Extra
    # worker source bytes cannot enter verify_dependencies by directory discovery.
    refs = (
        spec.baseline.system,
        spec.provenance.environment_lock,
        *spec.provenance.sources,
        *(data.artifact for data in spec.data),
    )
    for ref in refs:
        target = tmp_path / ref.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / ref.path).read_bytes())
    before = scientific_identity(spec, tmp_path)
    host = tmp_path / "src/autoengineering/agents/host.py"
    host.parent.mkdir()
    host.write_text("changed host")
    assert scientific_identity(spec, tmp_path) == before
    shared = tmp_path / "src/autoengineering/campaign/serialization.py"
    shared.write_text(shared.read_text() + "\n# modified shared science\n")
    with pytest.raises(ValueError, match="mismatch"):
        scientific_identity(spec, tmp_path)


def test_shortened_or_changed_scientific_closure_is_rejected():
    spec = agent_fixture()
    sources = tuple(
        ref
        for ref in spec.provenance.sources
        if ref.path != "src/autoengineering/campaign/serialization.py"
    )
    shortened = replace(
        spec,
        baseline=replace(spec.baseline, model=replace(spec.baseline.model, source_bundle=sources)),
        provenance=replace(spec.provenance, sources=sources),
    )
    with pytest.raises(ValueError, match="incomplete"):
        verify_runtime_sources(shortened)
    changed = tuple(
        replace(ref, sha256="0" * 64) if ref.path == SCIENTIFIC_CLOSURE else ref
        for ref in spec.provenance.sources
    )
    bad = replace(
        spec,
        baseline=replace(spec.baseline, model=replace(spec.baseline.model, source_bundle=changed)),
        provenance=replace(spec.provenance, sources=changed),
    )
    with pytest.raises(ValueError, match="mismatch"):
        verify_runtime_sources(bad)


def test_historical_profile_cannot_silently_resume_under_changed_sources():
    old = CampaignSpec.from_yaml(ROOT / "examples/campaign_contracts/fixture.yaml")
    assert SCIENTIFIC_CLOSURE not in {ref.path for ref in old.provenance.sources}
    with pytest.raises(ValueError):
        verify_runtime_sources(old)
    with pytest.raises(ValueError):
        scientific_identity(old, ROOT)
    assert old.digest != agent_fixture().digest


def test_manifest_source_paths_exist_and_are_digest_bound():
    assert len(scientific_source_paths()) > 10
    for path in scientific_source_paths():
        assert Path(ROOT / path).is_file()
        assert reference(ROOT, path, media_type="text/plain", producer="test").size_bytes > 0


def isolated_spec():
    original = agent_fixture()
    sources = tuple(
        reference(ROOT, path, media_type="application/octet-stream", producer="author")
        for path in (
            "examples/campaign_contracts/fixture_model.py",
            *scientific_source_paths(version="2"),
        )
    )
    return replace(
        original,
        source_bundle="scientific-isolated-v2",
        baseline=replace(
            original.baseline, model=replace(original.baseline.model, source_bundle=sources)
        ),
        provenance=replace(original.provenance, sources=sources),
    )


def test_isolated_closure_binds_execution_and_recovery_without_provider_sources():
    spec = isolated_spec()
    paths = {ref.path for ref in spec.provenance.sources}
    assert {SCIENTIFIC_CLOSURE, ISOLATED_SCIENTIFIC_CLOSURE} <= paths
    assert all(f"src/autoengineering/{name}" in paths for name in ISOLATED_SOURCES)
    assert "src/autoengineering/campaign/container_execution.py" in paths
    assert not any(
        "/hosts/" in path or "/prompts/" in path or "/agents/records.py" in path for path in paths
    )
    verify_runtime_sources(spec)
    assert scientific_identity(spec, ROOT)
    assert spec.digest != agent_fixture().digest
    assert ISOLATED_SCIENTIFIC_CLOSURE not in scientific_source_paths()


@pytest.mark.parametrize(
    "missing",
    [
        SCIENTIFIC_CLOSURE,
        "src/autoengineering/agents/container_recovery.py",
        "src/autoengineering/campaign/container_execution.py",
        "src/autoengineering/adapters/registration.py",
    ],
)
def test_shortened_isolated_engine_is_rejected(missing):
    spec = isolated_spec()
    sources = tuple(ref for ref in spec.provenance.sources if ref.path != missing)
    spec = replace(
        spec,
        baseline=replace(spec.baseline, model=replace(spec.baseline.model, source_bundle=sources)),
        provenance=replace(spec.provenance, sources=sources),
    )
    with pytest.raises(ValueError, match="missing|incomplete"):
        verify_runtime_sources(spec)


def test_isolated_manifest_digest_is_verified_before_its_source_list():
    spec = isolated_spec()
    sources = tuple(
        replace(ref, sha256="0" * 64) if ref.path == ISOLATED_SCIENTIFIC_CLOSURE else ref
        for ref in spec.provenance.sources
    )
    spec = replace(
        spec,
        baseline=replace(spec.baseline, model=replace(spec.baseline.model, source_bundle=sources)),
        provenance=replace(spec.provenance, sources=sources),
    )
    with pytest.raises(ValueError, match="mismatch"):
        verify_runtime_sources(spec)


def test_unrecognized_closure_version_is_rejected():
    with pytest.raises(ValueError, match="version"):
        scientific_source_paths(version="4")
