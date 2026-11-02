"""Public reports reconstruct every assigned cell and verify exported numbers."""
import csv
import io
import json
from dataclasses import replace

import pytest
from click.testing import CliRunner

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.store import StoreError
from autoengineering.cli import cli
from autoengineering.utility.analysis import AnalysisPlan, ContrastSpec
from autoengineering.utility.reporting import ReportSpec, comparative_report, report_files, export_report, verify_export
from autoengineering.utility.scoring import PublicScore
from autoengineering.utility.store import SuiteStore
from test_utility_contracts import H, suite
from test_utility_scoring import setup


def report_fixture(tmp_path, *, score=True):
    contrast = ContrastSpec("task", "multi", "conventional", "power", "W", "minimize", .1,
                            1., .95, "paired_student_t", 500, 17, "single_prespecified")
    plan = AnalysisPlan("utility-analysis-v1", (contrast,),
                        "complete_pairs_and_full_denominators", H)
    calls = []

    def scorer(*args):
        calls.append(1)
        return PublicScore("success", "power", "W", 3., True)

    store, grant, service, _ = setup(tmp_path, scorer, analysis_plan=plan)
    if score:
        service.confirm(grant)
    ref = put_bytes(store.root, plan.to_json().encode(), name="analysis.json",
                    media_type="application/json", producer="authored-test-fixture")
    return store, ReportSpec("utility-report-inputs-v1", store.spec.digest, ref, None, ()), calls, service, grant


def rows(raw):
    return list(csv.DictReader(io.StringIO(raw.decode())))


def test_report_retains_missing_cell_denominators_and_unknown_costs(tmp_path):
    store, request, calls, _, _ = report_fixture(tmp_path)
    head = store.replay()["head"]
    document = comparative_report(SuiteStore(store.root), request)
    assert len(document["cells"]) == 2
    assert document["analysis"]["contrasts"][0]["verdict"] == "inconclusive"
    files = report_files(document)
    cells = rows(files["cells.csv"])
    assert [row["confirmation_status"] for row in cells] == ["success", "no_eligible_model"]
    assert cells[0]["value"] == "3.0" and cells[1]["value"] == ""
    assert all(row["assigned"] == "1" for row in rows(files["failure-counts.csv"]))
    assert rows(files["paired-effects.csv"]) == []
    assert document["complete_cost_evidence"] is False
    assert "2" in files["summary.md"].decode()
    assert calls == [1] and store.replay()["head"] == head
    assert document == comparative_report(store, request)


def test_export_rebuilds_all_tables_and_refuses_overwrite_or_extra_files(tmp_path):
    store, request, calls, _, _ = report_fixture(tmp_path)
    destination = tmp_path / "export"
    manifest = export_report(store, request, destination)
    assert len(manifest["files"]) == 10
    assert verify_export(store, request, destination)["status"] == "verified_reconstruction"
    assert calls == [1]
    with pytest.raises(StoreError, match="absent path"):
        export_report(store, request, destination)
    (destination / "extra.csv").write_text("extra")
    with pytest.raises(StoreError, match="manifest differs"):
        verify_export(store, request, destination)


def test_updated_hashes_cannot_launder_changed_exported_numbers(tmp_path):
    import hashlib
    store, request, _, _, _ = report_fixture(tmp_path)
    destination = tmp_path / "export"
    export_report(store, request, destination)
    path = destination / "cells.csv"
    altered = path.read_bytes().replace(b"3.0", b"300.0")
    path.write_bytes(altered)
    manifest_path = destination / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["cells.csv"] = {"sha256": hashlib.sha256(altered).hexdigest(), "size_bytes": len(altered)}
    manifest_path.write_text(canonical_json(manifest))
    with pytest.raises(StoreError, match="authoritative reconstruction"):
        verify_export(store, request, destination)


def test_changed_suite_policy_or_analysis_artifact_blocks_report(tmp_path):
    store, request, _, _, _ = report_fixture(tmp_path)
    with pytest.raises(StoreError, match="another suite"):
        comparative_report(store, replace(request, suite_digest="2"*64))
    (store.root / request.analysis.path).write_text("altered")
    with pytest.raises(ValueError):
        comparative_report(store, request)
    empty = SuiteStore.create(tmp_path / "empty", suite())
    with pytest.raises(StoreError, match="selection barrier"):
        comparative_report(empty, replace(request, suite_digest=empty.spec.digest))


def test_uncertain_access_preserves_full_cell_row_without_rescoring(tmp_path):
    store, request, calls, service, grant = report_fixture(tmp_path, score=False)

    def crash(stage):
        if stage == "confirmation_access_committed":
            raise RuntimeError("owner lost")

    store.fault = crash
    with pytest.raises(RuntimeError):
        service.confirm(grant)
    document = comparative_report(SuiteStore(store.root), request)
    assert document["cells"][0]["confirmation_status"] == "reconciliation_required"
    assert document["cells"][0]["value"] is None
    assert calls == []


def test_cli_exports_and_verifies_comparative_tables_offline(tmp_path):
    store, request, calls, _, _ = report_fixture(tmp_path)
    source = tmp_path / "inputs.json"
    source.write_text(request.to_json())
    destination = tmp_path / "report"
    runner = CliRunner()
    exported = runner.invoke(cli, ["utility", "report", str(store.root), "--inputs", str(source),
                                    "--export-directory", str(destination)])
    assert exported.exit_code == 0, exported.output
    assert json.loads(exported.output)["schema"] == "utility-report-export-v1"
    verified = runner.invoke(cli, ["utility", "verify", str(store.root), "--inputs", str(source),
                                    "--export-directory", str(destination)])
    assert verified.exit_code == 0, verified.output
    assert json.loads(verified.output)["status"] == "verified_reconstruction"
    markdown = runner.invoke(cli, ["utility", "report", str(store.root), "--inputs", str(source), "--format", "markdown"])
    assert markdown.exit_code == 0 and "inconclusive" in markdown.output
    assert calls == [1]


def test_physical_cost_and_allocated_cost_tables_reconcile_without_zero_fill(tmp_path):
    from autoengineering.utility.costs import CostRecord
    store, request, _, _, _ = report_fixture(tmp_path)
    document = comparative_report(store, request)
    cells = tuple(row["cell_digest"] for row in document["cells"])
    known = CostRecord("shared", H, "selection", "science_duration", "s", 10., cells, (.25, .75))
    unknown = CostRecord("unknown", "2"*64, "selection", "provider_spend", "USD", None, cells, (.5, .5))
    document["accounting"]["receipts"] = [known.to_dict(), unknown.to_dict()]
    files = report_files(document)
    physical, allocations = rows(files["physical-costs.csv"]), rows(files["cost-allocations.csv"])
    assert len(physical) == 2 and len(allocations) == 4
    assert sum(float(row["allocated_quantity"]) for row in allocations if row["receipt_id"] == "shared") == 10.
    assert physical[1]["quantity"] == ""
    assert all(row["allocated_quantity"] == "" for row in allocations if row["receipt_id"] == "unknown")


def test_export_refuses_symlink_and_changed_authoritative_head(tmp_path):
    store, request, _, service, grant = report_fixture(tmp_path, score=False)
    destination = tmp_path / "report"
    export_report(store, request, destination)
    link = tmp_path / "link"
    link.symlink_to(destination, target_is_directory=True)
    with pytest.raises(ValueError):
        verify_export(store, request, link)
    with pytest.raises(StoreError, match="absent path"):
        export_report(store, request, link / "child")
    service.confirm(grant)
    with pytest.raises(StoreError, match="authoritative reconstruction"):
        verify_export(store, request, destination)
