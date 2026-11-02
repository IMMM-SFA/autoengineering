"""New capability admission cannot silently reuse older scientific profiles."""
from dataclasses import replace
import json
import shutil

import pytest

from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.identity import (
    INTEROPERABILITY_SCIENTIFIC_CLOSURE, INTEROPERABILITY_SOURCES,
    SCIENTIFIC_CLOSURE, scientific_source_paths, verify_runtime_sources,
)
from autoengineering.campaign.runtime import validate_policy
from test_campaign_studies import ROOT, calibrated_spec


def profile(version="3"):
    original = calibrated_spec()
    paths = ("examples/campaign_contracts/fixture_model.py", *scientific_source_paths(version=version))
    sources = tuple(reference(ROOT, path, media_type="application/octet-stream", producer="test")
                    for path in paths)
    return replace(
        original, source_bundle=f"scientific-core-v{version}",
        baseline=replace(original.baseline, model=replace(original.baseline.model, source_bundle=sources)),
        provenance=replace(original.provenance, sources=sources),
        calibration=replace(original.calibration, run=replace(original.calibration.run, policy="optuna")),
    )


def test_version_three_is_exact_extension_without_workers():
    base = set(scientific_source_paths())
    current = set(scientific_source_paths(version="3"))
    assert current == base | {f"src/autoengineering/{p}" for p in INTEROPERABILITY_SOURCES} | {
        INTEROPERABILITY_SCIENTIFIC_CLOSURE,
    }
    assert not any("/agents/" in p for p in current)
    verify_runtime_sources(profile())


def test_old_scientific_profile_cannot_admit_optuna():
    with pytest.raises(ValueError, match="closure version 3"):
        validate_policy(profile("1"))


def test_missing_implementation_rejected_before_dependency_import():
    spec = profile()
    sources = tuple(ref for ref in spec.provenance.sources
                    if ref.path != "src/autoengineering/optimization/optuna_backend.py")
    bad = replace(spec, baseline=replace(spec.baseline, model=replace(spec.baseline.model,
                                                                   source_bundle=sources)),
                  provenance=replace(spec.provenance, sources=sources))
    with pytest.raises(ValueError, match="implementation is missing"):
        validate_policy(bad)
    with pytest.raises(ValueError, match="incomplete"):
        verify_runtime_sources(bad)


def test_altered_allowlist_cannot_shorten_capability_closure(tmp_path):
    package = ROOT / "src/autoengineering"
    copied = tmp_path / "package"
    shutil.copytree(package, copied, ignore=shutil.ignore_patterns("__pycache__"))
    manifest = copied / "campaign/scientific-closure-v3.json"
    document = json.loads(manifest.read_text())
    document["files"].remove("optimization/optuna_backend.py")
    manifest.write_text(json.dumps(document))
    with pytest.raises(ValueError, match="explicit set"):
        scientific_source_paths(copied, version="3")


def test_base_manifest_required():
    spec = profile()
    sources = tuple(ref for ref in spec.provenance.sources if ref.path != SCIENTIFIC_CLOSURE)
    bad = replace(spec, baseline=replace(spec.baseline, model=replace(spec.baseline.model,
                                                                   source_bundle=sources)),
                  provenance=replace(spec.provenance, sources=sources))
    with pytest.raises(ValueError, match="base manifest"):
        verify_runtime_sources(bad)
