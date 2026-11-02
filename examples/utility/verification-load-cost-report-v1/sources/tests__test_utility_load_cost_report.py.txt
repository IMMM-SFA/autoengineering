"""Common reports verify pinned load work without model/example imports."""

from dataclasses import replace
import csv
import io
import json

from click.testing import CliRunner
import pytest

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.cli import cli
from autoengineering.utility.load_costs import (
    CostEvidenceSpec,
    LoadCostInput,
    LoadCostRegistration,
    join_load_costs,
)
from autoengineering.utility.report import accounting_report, render_markdown
from autoengineering.utility.reporting import (
    CostReportSpec,
    ReportSpec,
    comparative_report,
    export_report,
    verify_export,
    report_files,
)
from test_utility_engineering_load_costs import archived
from test_utility_reporting import report_fixture


def native_inputs(tmp_path):
    store, grant, original, ref = archived(tmp_path)
    registration = LoadCostRegistration.from_dict(original.to_dict())
    inputs = CostEvidenceSpec(
        "utility-cost-inputs-v1", store.spec.digest, (LoadCostInput(grant, registration, ref),)
    )
    return store, inputs


def totals(document):
    return {
        r["resource"]: r["quantity"] for r in document["physical_receipt_costs"]["known_totals"]
    }


def test_core_decoder_preserves_original_native_records(tmp_path):
    from examples.utility.engineering_load_costs import join_load_costs as original
    from examples.utility.engineering_load_costs import LoadCostRegistration as OldRegistration

    store, inputs = native_inputs(tmp_path)
    c = inputs.load_callbacks[0]
    assert join_load_costs(
        store, c.grant, c.registration, work_artifact=c.work_artifact
    ) == original(
        store,
        c.grant,
        OldRegistration.from_dict(c.registration.to_dict()),
        work_artifact=c.work_artifact,
    )


def test_common_accounting_joins_native_work_and_preserves_legacy_report(tmp_path):
    store, inputs = native_inputs(tmp_path)
    before = accounting_report(store)
    head = store.replay()["head"]
    document = accounting_report(store, cost_inputs=inputs)
    assert document["schema"] == "utility-accounting-v2"
    assert document["cost_inputs_digest"] == inputs.digest
    assert totals(document)["load_model_starts"] == 24
    assert totals(document)["load_solver_iterations"] == 395
    assert totals(document)["load_component_calls"] == 6440
    assert totals(document)["load_component_linearize_calls"] == 1975
    assert not document["complete_cost_evidence"]
    assert document["physical_receipt_costs"]["unknown"]
    assert len(document["receipts"]) == len(before["receipts"]) + 11
    assert "load_solver_iterations" in render_markdown(document)
    assert accounting_report(store) == before and store.replay()["head"] == head


def test_cost_inputs_refuse_omitted_charged_callback_and_wrong_suite(tmp_path):
    store, inputs = native_inputs(tmp_path)
    with pytest.raises(ValueError, match="every charged"):
        accounting_report(store, cost_inputs=replace(inputs, load_callbacks=()))
    with pytest.raises(ValueError, match="another suite"):
        accounting_report(
            store, cost_inputs=replace(inputs, suite_digest="0" * 64, load_callbacks=())
        )
    with pytest.raises(ValueError, match="unique callback"):
        replace(inputs, load_callbacks=inputs.load_callbacks * 2)


def test_absent_proof_keeps_unknown_work_in_common_report(tmp_path):
    store, inputs = native_inputs(tmp_path)
    inputs = replace(
        inputs, load_callbacks=(replace(inputs.load_callbacks[0], work_artifact=None),)
    )
    document = accounting_report(store, cost_inputs=inputs)
    load = {
        r["resource"]: r["quantity"]
        for r in document["receipts"]
        if r["resource"].startswith("load_")
    }
    assert load["load_model_start_reservations"] == 24
    assert load["load_model_starts"] is None and load["load_solver_iterations"] is None
    assert not document["complete_cost_evidence"]


@pytest.mark.parametrize("command", ["report", "verify"])
def test_cli_reads_only_pinned_cost_inputs(tmp_path, command):
    store, inputs = native_inputs(tmp_path)
    path = tmp_path / "costs.json"
    path.write_text(inputs.to_json())
    runner = CliRunner()
    result = runner.invoke(cli, ["utility", command, str(store.root), "--cost-inputs", str(path)])
    assert result.exit_code == 0, result.output
    doc = json.loads(result.output)
    assert not doc["complete_cost_evidence"] and doc["cost_inputs_digest"] == inputs.digest
    if command == "report":
        assert totals(doc)["load_model_starts"] == 24
    else:
        assert doc["status"] == "verified_integrity"


@pytest.mark.parametrize("command", ["report", "verify"])
def test_cli_changed_cost_bytes_are_sanitized_and_start_no_work(tmp_path, command):
    store, inputs = native_inputs(tmp_path)
    path = tmp_path / "costs.json"
    path.write_text(inputs.to_json())
    ref = inputs.load_callbacks[0].work_artifact
    (store.root / ref.path).write_text("PRIVATE-COST-PAYLOAD-832")
    before = store.replay()["head"]
    result = CliRunner().invoke(
        cli, ["utility", command, str(store.root), "--cost-inputs", str(path)]
    )
    assert result.exit_code == 2
    assert json.loads(result.output)["error"] == "invalid_utility_evidence"
    assert "PRIVATE" not in result.output and store.replay()["head"] == before


def test_cost_report_v3_roundtrip_and_export_preserve_old_versions(tmp_path):
    store, original, calls, _, _ = report_fixture(tmp_path)
    empty = CostEvidenceSpec("utility-cost-inputs-v1", store.spec.digest, ())
    ref = put_bytes(
        store.root,
        empty.to_json().encode(),
        name="cost-inputs.json",
        media_type="application/json",
        producer="trusted-cost-inputs",
    )
    request = CostReportSpec(
        "utility-report-inputs-v3",
        store.spec.digest,
        original.analysis,
        original.dependence,
        original.dependence_evidence,
        costs=ref,
    )
    assert ReportSpec.from_json(request.to_json()) == request
    assert ReportSpec.from_json(original.to_json()).to_json() == original.to_json()
    document = comparative_report(store, request)
    assert document["accounting"]["cost_inputs_digest"] == empty.digest
    assert not document["complete_cost_evidence"] and calls == [1]
    destination = tmp_path / "export"
    export_report(store, request, destination)
    assert verify_export(store, request, destination)["status"] == "verified_reconstruction"
    (store.root / ref.path).write_text("changed")
    with pytest.raises(ValueError):
        verify_export(store, request, destination)


def test_comparative_cost_csv_contains_verified_native_work(tmp_path, monkeypatch):
    from autoengineering.utility.analysis import AnalysisPlan, ContrastSpec
    from autoengineering.utility.load_costs import LoadScorePolicy
    from examples.utility import engineering_load_callback as callback
    import test_utility_engineering_load_callback as helper
    from test_utility_confirmation import selected_suite
    from test_utility_contracts import H

    plan = AnalysisPlan(
        "utility-analysis-v1",
        (
            ContrastSpec(
                "task",
                "multi",
                "conventional",
                "mean_source_power",
                "W",
                "minimize",
                0.1,
                1.0,
                0.95,
                "paired_student_t",
                500,
                17,
                "single_prespecified",
            ),
        ),
        "complete_pairs_and_full_denominators",
        H,
    )

    def with_analysis(*a, **kw):
        return selected_suite(*a, analysis_plan=plan, **kw)

    monkeypatch.setattr(helper, "selected_suite", with_analysis)
    store, grant, service, captured, _ = helper.setup(tmp_path, monkeypatch)
    helper.authored_solver(monkeypatch)
    service.confirm(grant)
    from autoengineering.campaign.artifacts import reference

    ref = reference(
        store.root,
        f"engineering-load-work/{grant.digest}.json",
        media_type="application/json",
        producer="engineering-load-work",
    )
    reg = LoadCostRegistration(
        "utility-load-cost-registration-v1",
        captured["source_ref"],
        callback.source_identity(),
        LoadScorePolicy.from_dict(captured["scorer"].policy.to_dict()),
    )
    inputs = CostEvidenceSpec(
        "utility-cost-inputs-v1", store.spec.digest, (LoadCostInput(grant, reg, ref),)
    )
    costs = put_bytes(
        store.root,
        inputs.to_json().encode(),
        name="cost-inputs.json",
        media_type="application/json",
        producer="fixture",
    )
    analysis = put_bytes(
        store.root,
        plan.to_json().encode(),
        name="analysis.json",
        media_type="application/json",
        producer="fixture",
    )
    request = CostReportSpec(
        "utility-report-inputs-v3", store.spec.digest, analysis, None, (), costs=costs
    )
    document = comparative_report(store, request)
    rows = list(
        csv.DictReader(io.StringIO(report_files(document)["cost-allocations.csv"].decode()))
    )
    row = next(r for r in rows if r["resource"] == "load_solver_iterations")
    assert float(row["quantity"]) == float(row["allocated_quantity"]) == 96
    assert row["cell_digest"] == grant.cell_digest
    assert not document["complete_cost_evidence"] and len(document["cells"]) == 2
    destination = tmp_path / "native-export"
    export_report(store, request, destination)
    assert verify_export(store, request, destination)["status"] == "verified_reconstruction"


@pytest.mark.parametrize("command", ["report", "verify"])
def test_two_sources_of_cost_inputs_are_rejected(tmp_path, command):
    store, request, _, _, _ = report_fixture(tmp_path)
    path = tmp_path / "report.json"
    path.write_text(request.to_json())
    costs = tmp_path / "cost.json"
    costs.write_text("{}")
    result = CliRunner().invoke(
        cli,
        ["utility", command, str(store.root), "--inputs", str(path), "--cost-inputs", str(costs)],
    )
    assert result.exit_code == 2


def test_core_cli_works_with_examples_and_optional_framework_imports_denied(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    store, inputs = native_inputs(tmp_path)
    path = tmp_path / "costs.json"
    path.write_text(inputs.to_json())
    code = r"""
import sys, importlib.abc, json
sys.path.insert(0, sys.argv[1])
class Denied(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, *a):
        if fullname.split('.')[0] in {'examples','openmdao','pvlib','torch','py_wake','topfarm'}:
            raise RuntimeError('example or framework import denied')
sys.meta_path.insert(0, Denied())
from click.testing import CliRunner
from autoengineering.cli import cli
r = CliRunner().invoke(cli, ['utility','report',sys.argv[2],'--cost-inputs',sys.argv[3]])
assert r.exit_code == 0, (r.output, r.exception)
d = json.loads(r.output)
assert any(x['resource']=='load_solver_iterations' and x['quantity']==395 for x in d['receipts'])
assert not any(n=='examples' or n.startswith('examples.') for n in sys.modules)
"""
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            code,
            str(Path(__file__).resolve().parents[1] / "src"),
            str(store.root),
            str(path),
        ],
        check=True,
    )


def test_v3_effort_input_requires_the_existing_effort_analysis_contract(tmp_path):
    store, original, _, _, _ = report_fixture(tmp_path)
    costs = CostEvidenceSpec("utility-cost-inputs-v1", store.spec.digest, ())
    ref = put_bytes(
        store.root,
        costs.to_json().encode(),
        name="cost-inputs.json",
        media_type="application/json",
        producer="fixture",
    )
    request = CostReportSpec(
        "utility-report-inputs-v3",
        store.spec.digest,
        original.analysis,
        None,
        (),
        costs=ref,
        effort=ref,
    )
    assert ReportSpec.from_json(request.to_json()) == request
    with pytest.raises(ValueError, match="preregistered effort analysis"):
        comparative_report(store, request)


@pytest.mark.parametrize("lost_work", [False, True])
def test_core_failed_callback_retains_unknown_totals_and_original_charge(
    tmp_path, monkeypatch, lost_work
):
    from autoengineering.campaign.artifacts import reference
    from autoengineering.campaign.store import StoreError
    from autoengineering.utility.load_costs import LoadScorePolicy
    from examples.utility import engineering_load_callback as callback
    from test_utility_engineering_load_callback import setup, authored_solver

    store, grant, service, captured, _ = setup(tmp_path, monkeypatch)
    calls = authored_solver(monkeypatch, change="failure")
    if lost_work:

        def lost(*a, **kw):
            raise OSError("authored work publication loss")

        monkeypatch.setattr(callback, "durable_write", lost)
        with pytest.raises(StoreError, match="uncertain"):
            service.confirm(grant)
        ref = None
    else:
        assert service.confirm(grant).score.status == "model_failure"
        ref = reference(
            store.root,
            f"engineering-load-work/{grant.digest}.json",
            media_type="application/json",
            producer="engineering-load-work",
        )
    reg = LoadCostRegistration(
        "utility-load-cost-registration-v1",
        captured["source_ref"],
        callback.source_identity(),
        LoadScorePolicy.from_dict(captured["scorer"].policy.to_dict()),
    )
    inputs = CostEvidenceSpec(
        "utility-cost-inputs-v1", store.spec.digest, (LoadCostInput(grant, reg, ref),)
    )
    document = accounting_report(store, cost_inputs=inputs)
    rows = {
        r["resource"]: r["quantity"]
        for r in document["receipts"]
        if r["resource"].startswith("load_")
    }
    assert rows["load_solver_iterations"] is None and rows["load_model_starts"] is None
    assert rows["load_known_completed_solver_iterations"] == (None if lost_work else 8)
    assert rows["load_case_attempts"] == (None if lost_work else 3)
    assert rows["load_model_start_reservations"] == 24 and len(calls) == 3
    assert document["confirmation_state"] == (
        "reconciliation_required" if lost_work else "scored_unanalyzed"
    )
    assert not document["complete_cost_evidence"]


@pytest.mark.parametrize("change", ["binding_claim", "work_bytes", "work_role", "registration"])
def test_core_report_rejects_changed_public_proofs(tmp_path, change):
    store, inputs = native_inputs(tmp_path)
    entry = inputs.load_callbacks[0]
    if change == "binding_claim":
        path = store.root / "engineering-scenario-preparations/task.json"
        path.write_text('{"changed":true}')
    elif change == "work_bytes":
        (store.root / entry.work_artifact.path).write_text("changed")
    elif change == "work_role":
        entry = replace(entry, work_artifact=replace(entry.work_artifact, producer="wrong"))
    else:
        entry = replace(
            entry, registration=replace(entry.registration, callback_source_digest="0" * 64)
        )
    with pytest.raises(ValueError):
        accounting_report(store, cost_inputs=replace(inputs, load_callbacks=(entry,)))


def test_cost_reconstruction_refuses_a_concurrently_changed_journal(tmp_path, monkeypatch):
    from autoengineering.utility import load_costs

    store, inputs = native_inputs(tmp_path)
    original = load_costs.join_load_costs

    def changed(*a, **kw):
        result = original(*a, **kw)
        with store.writer():
            store.append(
                request_id="authored-concurrent-cancel",
                operation="cancel",
                cell_digest=store.spec.cells[0].digest,
                attempt_id="authored-concurrent-cancel",
                child_digest=store.spec.digest,
            )
        return result

    monkeypatch.setattr(load_costs, "join_load_costs", changed)
    with pytest.raises(ValueError, match="suite changed"):
        accounting_report(store, cost_inputs=inputs)
