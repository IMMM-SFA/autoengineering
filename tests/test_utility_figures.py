"""Plot data preserve exact pairs, units, missingness and assignment totals."""
from dataclasses import replace
import hashlib
import importlib.util
import json

import pytest
from click.testing import CliRunner

from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError
from autoengineering.cli import cli
from autoengineering.utility.analysis import analyze
from autoengineering.utility.figures import figure_data, render, export_figures, verify_figures
from autoengineering.utility.reporting import comparative_report, verify_export
from test_utility_analysis import fixture
from test_utility_reporting import report_fixture


HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None


def illustration(*, dependence=False):
    if dependence:
        from test_utility_dependence import prepared
        spec, plan, scores, policy, evidence = prepared()
        analysis = analyze(spec, plan, scores, dependence=policy, dependence_evidence=evidence)
    else:
        spec, plan, scores = fixture((-.2, .3, .7, 1., 1.1, 1.9))
        scores = tuple(score if i < 10 else replace(score, status="timeout", value=None, feasible=None)
                       for i, score in enumerate(scores))
        analysis = analyze(spec, plan, scores)
    document = {"suite_digest": spec.digest, "source_head": "1"*64, "report_spec_digest": "2"*64,
        "analysis": analysis, "cells": [
            {"task_id": cell.task_id, "regime": cell.regime, "route_id": cell.route_id,
             "confirmation_status": score.status, "feasible": score.feasible}
            for cell, score in zip(spec.cells, scores)], "claim_limits": ["Authored illustration; no scientific utility evidence"]}
    data = figure_data(document, plan)
    # Display labels identify this saved illustration as authored.
    for row in (*data["contrasts"], *data["reliability"]):
        row["task_id"] = "Authored illustration"
    return data


def test_figure_data_preserve_raw_gains_counts_units_and_missing_evidence(tmp_path):
    store, request, _, _, _ = report_fixture(tmp_path)
    document = comparative_report(store, request)
    from autoengineering.utility.analysis import AnalysisPlan
    plan = AnalysisPlan.from_json((store.root / request.analysis.path).read_text())
    data = figure_data(document, plan)
    row = data["contrasts"][0]
    assert row["valid_pairs"] == 0 and row["assigned_pairs"] == 1
    assert row["pairs"] == [] and row["mean_gain"] is None and row["units"] == "W"
    assert sum(sum(counts.values()) for group in data["reliability"] for counts in group["routes"].values()) == 2
    assert data["total_cost_comparison"]["status"] == "blocked"
    with pytest.raises(ValueError, match="policy differs"):
        figure_data(document, replace(plan, dependence_policy_digest="3"*64))


def test_figure_module_import_and_numeric_data_need_no_matplotlib():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-c", "import sys; import autoengineering.utility.figures; "
        "assert not {'matplotlib','torch','openmdao','py_wake','pvlib'} & sys.modules.keys()"],
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="optional Matplotlib rendering environment required")
def test_render_is_deterministic_and_keeps_replication_separate():
    data = illustration()
    profile, images = render(data, width=5.)
    assert render(data, width=5.) == (profile, images)
    svg = images["paired-effects-001.svg"].decode()
    from xml.etree import ElementTree
    visible = " ".join(" ".join(ElementTree.fromstring(svg).itertext()).split())
    assert "Repetition mean" in visible and "Observation/scenario uncertainty is separate" in visible
    assert "Authored illustration" in svg and "Gain in power (W)" in svg
    assert "Assigned cells (count)" in images["assigned-outcomes-001.svg"].decode()
    assert all(raw for raw in images.values())


@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="optional Matplotlib rendering environment required")
def test_figure_export_reconstructs_numeric_data_and_optional_pixels(tmp_path):
    store, request, calls, _, _ = report_fixture(tmp_path)
    destination = tmp_path / "figures"
    manifest = export_figures(store, request, destination)
    assert manifest["schema"] == "utility-figure-export-v1"
    assert verify_export(store, request, destination)["image_rendering"] == "not_repeated"
    assert verify_figures(store, request, destination, rerender=True)["image_rendering"] == "reconstructed"
    assert calls == [1]
    path = destination / "figure-data.json"
    raw = path.read_bytes().replace(b'"valid_pairs":0', b'"valid_pairs":1')
    path.write_bytes(raw)
    manifest["files"]["figure-data.json"] = {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
    (destination / "manifest.json").write_text(canonical_json(manifest))
    with pytest.raises(StoreError, match="authoritative reconstruction"):
        verify_export(store, request, destination)


@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="optional Matplotlib rendering environment required")
def test_cli_figure_export_and_pixel_verification(tmp_path):
    store, request, calls, _, _ = report_fixture(tmp_path)
    inputs = tmp_path / "inputs.json"
    inputs.write_text(request.to_json())
    destination = tmp_path / "figures"
    common = [str(store.root), "--inputs", str(inputs), "--export-directory", str(destination)]
    runner = CliRunner()
    result = runner.invoke(cli, ["utility", "report", *common, "--figures"])
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli, ["utility", "verify", *common, "--rerender-figures"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["image_rendering"] == "reconstructed"
    assert calls == [1]



@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="optional Matplotlib rendering environment required")
def test_dependence_intervals_render_separately_from_repetition():
    data = illustration(dependence=True)
    profile, files = render(data)
    assert "dependence-001.svg" in files
    svg = files["dependence-001.svg"].decode()
    assert "observation/scenario uncertainty" in svg
    assert len(data["contrasts"][0]["dependence_evidence"]) == 3
    assert data["dependence_policy"]["scenarios"][0]["confidence"] == .999


@pytest.mark.skipif(HAS_MATPLOTLIB, reason="checks base profile without Matplotlib")
def test_missing_renderer_stops_before_creating_export(tmp_path):
    store, request, calls, _, _ = report_fixture(tmp_path)
    destination = tmp_path / "uncreated"
    with pytest.raises(ValueError, match="optional Matplotlib"):
        export_figures(store, request, destination)
    assert not destination.exists() and calls == [1]


@pytest.mark.skipif(not HAS_MATPLOTLIB, reason="optional Matplotlib rendering environment required")
def test_changed_image_with_updated_hash_requires_pixel_reconstruction_to_detect(tmp_path):
    store, request, _, _, _ = report_fixture(tmp_path)
    destination = tmp_path / "figures"
    manifest = export_figures(store, request, destination)
    name = "paired-effects-001.svg"
    path = destination / name
    changed = path.read_bytes().replace(b"No valid paired outcomes", b"Invented useful gains")
    assert changed != path.read_bytes()
    path.write_bytes(changed)
    manifest["files"][name] = {"sha256": hashlib.sha256(changed).hexdigest(), "size_bytes": len(changed)}
    (destination / "manifest.json").write_text(canonical_json(manifest))
    assert verify_figures(store, request, destination)["image_rendering"] == "not_repeated"
    with pytest.raises(StoreError, match="pixels differ"):
        verify_figures(store, request, destination, rerender=True)
