"""Report verification must reject altered evidence and inconsistent decisions."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from scripts import summarize_open_chains as report


@pytest.fixture
def wind_evidence(tmp_path, monkeypatch):
    original = report.ROOT
    for name in ["wind", "common.py", "__init__.py"]:
        (tmp_path / name).symlink_to(original / name)
    directory = tmp_path / "results/wind"
    shutil.copytree(original / "results/wind", directory)
    monkeypatch.setattr(report, "ROOT", tmp_path)
    return directory


def refresh_hash(directory: Path, name: str) -> None:
    path = directory / "artifact-sha256.json"
    hashes = json.loads(path.read_text())
    hashes[name] = report.digest(directory / name)
    path.write_text(json.dumps(hashes))


def test_saved_wind_evidence_verifies(wind_evidence):
    summary, _, _ = report.verify("wind")
    assert summary["selected"] == "topfarm_20"


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
