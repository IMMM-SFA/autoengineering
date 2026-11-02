"""Core wind cost readers join pinned native evidence without example execution."""

import builtins
from dataclasses import replace
import json
from pathlib import Path
import shutil
import socket
import subprocess

from click.testing import CliRunner
import pytest

from autoengineering.campaign.artifacts import put_bytes
from autoengineering.campaign.records import ArtifactRef, ModelSnapshot
from autoengineering.campaign.serialization import digest
from autoengineering.cli import cli
from autoengineering.utility.analysis import AnalysisPlan, ContrastSpec
from autoengineering.utility.costs import reconcile
from autoengineering.utility.load_costs import (
    CostEvidenceSpec,
    DomainCostEvidenceSpec,
    LoadCostInput,
    LoadCostRegistration,
    LoadScorePolicy,
    join_cost_inputs,
)
from autoengineering.utility.report import accounting_report
from autoengineering.utility.reporting import (
    CostReportSpec,
    comparative_report,
    export_report,
    verify_export,
)
from autoengineering.utility.scoring import ConfirmationGrant
from autoengineering.utility.store import SuiteStore
from autoengineering.utility.wind_costs import (
    WindCostInput,
    WindCostRegistration,
    WindScorePolicy,
    join_wind_costs,
)

ARCHIVE = (
    Path(__file__).resolve().parents[1] / "examples/utility/verification-wind-annual-native-v1"
)


def archived(tmp_path):
    shutil.copytree(ARCHIVE / "suite", tmp_path / "suite")
    store = SuiteStore(tmp_path / "suite")
    request = json.loads((ARCHIVE / "native-request.json").read_text())
    actual = json.loads((ARCHIVE / "native-result.json").read_text())
    expected = ModelSnapshot.from_dict(request["expected_model"])
    registration = WindCostRegistration(
        "utility-wind-cost-registration-v1",
        ArtifactRef.from_dict(request["source_binding_artifact"]),
        next(
            r.sha256 for r in expected.source_bundle if r.path.endswith("wind_annual_callback.py")
        ),
        WindScorePolicy.from_dict(request["policy"]),
        expected.digest,
        digest(request["geometry"]),
    )
    grant = ConfirmationGrant.from_dict(request["grant"])
    return store, grant, registration, ArtifactRef.from_dict(actual["work_artifact"])


def inputs(store, grant, registration, artifact):
    return DomainCostEvidenceSpec(
        schema="utility-cost-inputs-v2",
        suite_digest=store.spec.digest,
        load_callbacks=(),
        wind_callbacks=(WindCostInput(grant, registration, artifact),),
    )


def values(records):
    return {row.resource: row.quantity for row in records}


def forbid_execution(monkeypatch):
    original = builtins.__import__

    def guarded(name, *args, **kwargs):
        if name.split(".")[0] in {
            "examples",
            "py_wake",
            "h5py",
            "netCDF4",
            "matplotlib",
            "torch",
            "botorch",
        }:
            pytest.fail("metadata cost reader imported source or model code")
        return original(name, *args, **kwargs)

    def denied(*args, **kwargs):
        pytest.fail("metadata cost reader attempted a process or network")

    monkeypatch.setattr(builtins, "__import__", guarded)
    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)


def test_archived_native_work_joins_without_models_and_preserves_unknowns(tmp_path, monkeypatch):
    store, grant, registration, artifact = archived(tmp_path)
    forbid_execution(monkeypatch)
    before = store.replay()["head"]
    records = join_wind_costs(store, grant, registration, work_artifact=artifact)
    result = values(records)
    assert result["wind_model_starts"] == result["wind_completed_evaluations"] == 3
    assert result["wind_private_reads"] == result["wind_private_read_reservations"] == 3
    assert result["wind_private_bytes"] == result["wind_private_byte_reservations"] == 420864
    assert (
        result["wind_cpu_time"]
        is result["wind_peak_rss"]
        is result["wind_inner_wake_calls"]
        is None
    )
    assert store.replay()["head"] == before
    assert all(
        row.category == "confirmation" and row.cell_digests == (grant.cell_digest,)
        for row in records
    )
    assert next(row.units for row in records if row.resource == "wind_private_bytes") == "byte"


def test_absent_work_does_not_turn_a_successful_score_into_known_inner_work(tmp_path):
    store, grant, registration, artifact = archived(tmp_path)
    missing = join_wind_costs(store, grant, registration)
    assert values(missing)["wind_model_starts"] is values(missing)["wind_private_bytes"] is None
    assert values(missing)["wind_model_start_reservations"] == 3
    known = join_wind_costs(store, grant, registration, work_artifact=artifact)
    assert [r.receipt_id for r in missing] == [r.receipt_id for r in known]
    with pytest.raises(ValueError, match="duplicate"):
        reconcile((*known, *known), tuple(r.receipt_id for r in (*known, *known)))


@pytest.mark.parametrize(
    "change",
    ["callback", "model", "geometry", "binding_role", "work_role", "work_bytes", "source_reads"],
)
def test_changed_identity_or_original_evidence_refuses(tmp_path, change):
    store, grant, registration, artifact = archived(tmp_path)
    if change == "callback":
        registration = replace(registration, callback_source_digest="f" * 64)
    elif change == "model":
        registration = replace(registration, expected_model_digest="f" * 64)
    elif change == "geometry":
        registration = replace(registration, geometry_digest="f" * 64)
    elif change == "binding_role":
        registration = replace(
            registration, binding_artifact=replace(registration.binding_artifact, producer="other")
        )
    elif change == "work_role":
        artifact = replace(artifact, producer="other")
    elif change == "work_bytes":
        path = store.root / artifact.path
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = store.root / f"wind-annual-source-accesses/{grant.digest}-2012-complete.json"
        path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        join_wind_costs(store, grant, registration, work_artifact=artifact)


def test_v2_decoding_common_accounting_and_complete_callback_coverage(tmp_path, monkeypatch):
    store, grant, registration, artifact = archived(tmp_path)
    request = inputs(store, grant, registration, artifact)
    assert CostEvidenceSpec.from_json(request.to_json()) == request
    forbid_execution(monkeypatch)
    before = accounting_report(store)
    document = accounting_report(store, cost_inputs=request)
    assert document["cost_inputs_digest"] == request.digest
    assert not document["complete_cost_evidence"]
    assert accounting_report(store) == before
    assert join_cost_inputs(store, request) == join_wind_costs(
        store, grant, registration, work_artifact=artifact
    )
    with pytest.raises(ValueError, match="every charged"):
        join_cost_inputs(store, replace(request, wind_callbacks=()))
    with pytest.raises(ValueError, match="v2"):
        join_cost_inputs(store, CostEvidenceSpec("utility-cost-inputs-v1", store.spec.digest, ()))
    with pytest.raises(ValueError, match="unique"):
        replace(request, wind_callbacks=request.wind_callbacks * 2)


@pytest.mark.parametrize("command", ["report", "verify"])
def test_cli_decodes_wind_inputs_with_no_execution(tmp_path, monkeypatch, command):
    store, grant, registration, artifact = archived(tmp_path)
    request = inputs(store, grant, registration, artifact)
    path = tmp_path / "costs.json"
    path.write_text(request.to_json())
    forbid_execution(monkeypatch)
    result = CliRunner().invoke(
        cli, ["utility", command, str(store.root), "--cost-inputs", str(path)]
    )
    assert result.exit_code == 0, result.output
    if command == "report":
        assert "wind_model_starts" in result.output
    else:
        document = json.loads(result.output)
        assert document["cost_inputs_digest"] == request.digest
        assert document["complete_cost_evidence"] is False


def current(tmp_path, monkeypatch, *, failed=False, uncertain=False, analysis=None):
    from test_utility_wind_annual_callback import setup, lose_score_publication

    context = setup(tmp_path, monkeypatch, fail_model=failed, analysis_plan=analysis)
    if uncertain:
        lose_score_publication(context)
    else:
        context["service"].confirm(context["grant"])
    scorer = context["scorer"]
    registration = WindCostRegistration(
        "utility-wind-cost-registration-v1",
        scorer.binding_artifact,
        next(
            r.sha256
            for r in scorer.expected_model.source_bundle
            if r.path.endswith("wind_annual_callback.py")
        ),
        WindScorePolicy.from_dict(scorer.policy.to_dict()),
        scorer.expected_model.digest,
        scorer.geometry.digest,
    )
    assert registration.code_digest == scorer.code_digest
    artifact = scorer.public_work(context["grant"], context["model"])
    return context, registration, artifact


def test_failed_model_retains_known_completions_full_reads_and_unknown_last_work(
    tmp_path, monkeypatch
):
    context, registration, artifact = current(tmp_path, monkeypatch, failed=True)
    result = values(
        join_wind_costs(context["store"], context["grant"], registration, work_artifact=artifact)
    )
    assert result["wind_case_attempts"] == 2
    assert result["wind_completed_evaluations"] == 1
    assert result["wind_model_starts"] is None
    assert result["wind_private_reads"] == 3 and result["wind_private_bytes"] == 420864
    assert result["wind_model_start_reservations"] == 3


def test_cost_proof_survives_uncommitted_score_without_publishing_or_retrying(
    tmp_path, monkeypatch
):
    context, registration, artifact = current(tmp_path, monkeypatch, uncertain=True)
    store = context["store"]
    before = store.replay()["head"]
    records = join_wind_costs(store, context["grant"], registration, work_artifact=artifact)
    assert values(records)["wind_model_starts"] == 3
    assert store.replay()["head"] == before
    assert not store.replay()["confirmation_scores"]
    assert len(context["calls"]) == len(context["reads"]) == 3


def test_comparative_export_uses_wind_work_without_changing_missing_denominators(
    tmp_path, monkeypatch
):
    plan = AnalysisPlan(
        "utility-analysis-v1",
        (
            ContrastSpec(
                "task",
                "multi",
                "conventional",
                "mean_annual_energy",
                "GWh",
                "maximize",
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
        "1" * 64,
    )
    context, registration, artifact = current(tmp_path, monkeypatch, analysis=plan)
    store, grant = context["store"], context["grant"]
    evidence = inputs(store, grant, registration, artifact)
    analysis_ref = put_bytes(
        store.root,
        plan.to_json().encode(),
        name="analysis.json",
        media_type="application/json",
        producer="authored-test",
    )
    cost_ref = put_bytes(
        store.root,
        evidence.to_json().encode(),
        name="costs.json",
        media_type="application/json",
        producer="authored-test",
    )
    request = CostReportSpec(
        "utility-report-inputs-v3", store.spec.digest, analysis_ref, None, (), costs=cost_ref
    )
    forbid_execution(monkeypatch)
    report = comparative_report(store, request)
    assert len(report["cells"]) == 2
    assert report["analysis"]["contrasts"][0]["verdict"] == "inconclusive"
    assert report["complete_cost_evidence"] is False
    export_report(store, request, tmp_path / "report")
    assert verify_export(store, request, tmp_path / "report")["status"] == "verified_reconstruction"
    assert len(context["calls"]) == len(context["reads"]) == 3


@pytest.mark.parametrize(
    "change", ["attempts", "source", "configuration", "score", "admission", "sequence"]
)
def test_rehashed_foreign_or_inconsistent_work_cannot_supply_costs(tmp_path, change):
    store, grant, registration, artifact = archived(tmp_path)
    proof = json.loads((store.root / artifact.path).read_text())
    if change == "attempts":
        proof["attempted_model_starts"] = 2
    elif change == "source":
        proof["run"]["results"][0]["source_digest"] = "f" * 64
    elif change == "configuration":
        proof["run"]["configuration_digest"] = "f" * 64
    elif change == "score":
        proof["score"]["value"] = 1.0
    elif change == "admission":
        proof["task_admitted"] = True
    else:
        proof["run"]["results"][0].update(status="not_attempted", energy_gwh=None)
    forged = put_bytes(
        store.root,
        json.dumps(proof).encode(),
        name="annual-wind-work.json",
        media_type="application/json",
        producer="annual-wind-confirmation-work",
    )
    with pytest.raises(ValueError):
        join_wind_costs(store, grant, registration, work_artifact=forged)


def test_missing_read_evidence_refuses_a_supplied_work_pin(tmp_path):
    store, grant, registration, artifact = archived(tmp_path)
    path = store.root / f"wind-annual-source-accesses/{grant.digest}-2012-complete.json"
    path.unlink()  # Disposable copy of public producer metadata.
    with pytest.raises((ValueError, OSError)):
        join_wind_costs(store, grant, registration, work_artifact=artifact)
    assert values(join_wind_costs(store, grant, registration))["wind_model_starts"] is None


def test_one_cell_cannot_be_charged_under_both_cost_domains(tmp_path):
    store, grant, registration, artifact = archived(tmp_path)
    wind = WindCostInput(grant, registration, artifact)
    load = LoadCostInput(
        grant,
        LoadCostRegistration(
            "utility-load-cost-registration-v1",
            registration.binding_artifact,
            "1" * 64,
            LoadScorePolicy("utility-coupled-load-score-v1", "1" * 64, "1" * 64, 0.62),
        ),
        None,
    )
    with pytest.raises(ValueError, match="unique"):
        DomainCostEvidenceSpec(
            schema="utility-cost-inputs-v2",
            suite_digest=store.spec.digest,
            load_callbacks=(load,),
            wind_callbacks=(wind,),
        )


def test_wrong_binding_path_is_rejected_before_reading_its_body(tmp_path, monkeypatch):
    import autoengineering.utility.wind_costs as module

    store, grant, registration, _ = archived(tmp_path)
    registration = replace(
        registration, binding_artifact=replace(registration.binding_artifact, path="other.json")
    )

    def denied(*args, **kwargs):
        pytest.fail("wrong-role artifact body was opened")

    monkeypatch.setattr(module, "read_bytes", denied)
    with pytest.raises(ValueError, match="role"):
        join_wind_costs(store, grant, registration)
