"""Report verification must reject altered evidence and inconsistent decisions."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts import summarize_open_chains as report


@pytest.fixture
def wind_evidence(tmp_path, monkeypatch):
    original = report.ROOT
    for name in ["wind", "common.py", "__init__.py"]:
        (tmp_path / name).symlink_to(original / name)
    directory = tmp_path / "results/wind"
    shutil.copytree(original / "results/wind", directory)
    # Artifact tests verify the historical run, not the behavior of revised core code.
    # Keep the production live-source gate strict and materialize its exact old inputs.
    repository = report.REPO
    snapshot = tmp_path / "recorded-repository"
    manifest = json.loads((directory / "manifest.json").read_text())
    revision = "d2fe5b488aab15a2b896f8c6740d9ee79be9bba6"
    expected_sources = {
        **manifest["core_source_sha256"],
        "pixi.toml": manifest["pixi_manifest_sha256"],
        "pixi.lock": manifest["pixi_lock_sha256"],
    }
    for name, expected in expected_sources.items():
        archived = subprocess.run(
            ["git", "-C", str(repository), "show", f"{revision}:{name}"],
            check=True,
            capture_output=True,
        ).stdout
        destination = snapshot / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(archived)
        assert report.digest(destination) == expected, f"Historical input differs: {name}"
    monkeypatch.setattr(report, "ROOT", tmp_path)
    monkeypatch.setattr(report, "REPO", snapshot)
    return directory


def refresh_hash(directory: Path, name: str) -> None:
    path = directory / "artifact-sha256.json"
    hashes = json.loads(path.read_text())
    hashes[name] = report.digest(directory / name)
    path.write_text(json.dumps(hashes))


def test_saved_wind_evidence_verifies_at_recorded_source(wind_evidence):
    summary, _, _ = report.verify("wind")
    assert summary["selected"] == "topfarm_20"


def test_changed_core_source_is_rejected(wind_evidence):
    path = report.REPO / "src/autoengineering/execute/swap.py"
    path.write_bytes(path.read_bytes() + b"\n# changed source\n")
    with pytest.raises(AssertionError, match="Changed core source"):
        report.verify("wind")


def test_changed_artifact_is_rejected(wind_evidence):
    (wind_evidence / "report.md").write_text("Changed report")
    with pytest.raises(AssertionError, match="Changed wind artifact"):
        report.verify("wind")


@pytest.mark.parametrize("field", ["gain", "infeasible_trials", "selected_value"])
def test_inconsistent_summary_is_rejected(wind_evidence, field):
    path = wind_evidence / "summary.json"
    summary = json.loads(path.read_text())
    summary[field] += 1
    path.write_text(json.dumps(summary))
    refresh_hash(wind_evidence, path.name)
    with pytest.raises(AssertionError):
        report.verify("wind")


def test_changed_frozen_selection_is_rejected(wind_evidence):
    path = wind_evidence / "selection.json"
    selection = json.loads(path.read_text())
    selection["id"] = "baseline"
    path.write_text(json.dumps(selection))
    refresh_hash(wind_evidence, path.name)
    with pytest.raises(AssertionError):
        report.verify("wind")


@pytest.fixture
def version_snapshot(tmp_path, monkeypatch):
    path = tmp_path / "pixi.toml"
    path.write_text('version = "0.1.0"\nname = "example"\n')
    expected = report.digest(path)
    archived = tmp_path / "examples/open_chains/history/source-sha256" / f"{expected}.txt"
    archived.parent.mkdir(parents=True)
    shutil.copyfile(path, archived)
    monkeypatch.setattr(report, "REPO", tmp_path)
    return path, archived, expected


def test_metadata_only_version_change_verifies(version_snapshot):
    path, _, expected = version_snapshot
    path.write_text(path.read_text().replace("0.1.0", "0.2.0"))
    report.verify_release_metadata("pixi.toml", expected)


def test_non_version_change_rejected(version_snapshot):
    path, _, expected = version_snapshot
    path.write_text(path.read_text().replace("example", "different"))
    with pytest.raises(AssertionError, match="Changed non-version content"):
        report.verify_release_metadata("pixi.toml", expected)


def test_corrupt_release_snapshot_rejected(version_snapshot):
    path, archived, expected = version_snapshot
    path.write_text(path.read_text().replace("0.1.0", "0.2.0"))
    archived.write_text("corrupted")
    with pytest.raises(AssertionError, match="Invalid release snapshot"):
        report.verify_release_metadata("pixi.toml", expected)
