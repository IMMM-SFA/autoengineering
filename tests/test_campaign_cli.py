"""JSON command behavior and read-only reporting share the direct broker's decisions."""

import json

from click.testing import CliRunner

from autoengineering.cli import cli
from autoengineering.campaign.controller import CampaignController
from examples.campaign_contracts.build_fixture import ROOT, fixture


def fresh_spec(tmp_path):
    path = tmp_path / "current-fixture.yaml"
    fixture().to_yaml(path)
    return path


def test_cli_commands_and_direct_decision_agree(tmp_path):
    runner = CliRunner()
    spec = fresh_spec(tmp_path)
    validated = runner.invoke(cli, ["campaign", "validate", str(spec), "--source-root", str(ROOT)])
    assert validated.exit_code == 0, validated.output
    assert json.loads(validated.stdout)["status"] == "ok"
    work = tmp_path / "cli"
    run = runner.invoke(
        cli,
        [
            "campaign",
            "run",
            str(spec),
            "--source-root",
            str(ROOT),
            "--workdir",
            str(work),
            "--max-new-evaluations",
            "1",
        ],
    )
    assert run.exit_code == 0, run.output
    assert json.loads(run.stdout)["physical_attempts"] == 1
    resumed = runner.invoke(cli, ["campaign", "resume", str(work), "--max-new-evaluations", "1"])
    assert resumed.exit_code == 0, resumed.output
    assert json.loads(resumed.stdout)["outcome"] == "accepted_candidate"
    status = runner.invoke(cli, ["campaign", "status", str(work), "--format", "json"])
    assert json.loads(status.stdout)["state"] == "completed"
    report = runner.invoke(cli, ["campaign", "report", str(work), "--format", "json"])
    assert json.loads(report.stdout)["records"]["confirmation"] == "confirmation_not_attempted"
    direct = CampaignController.create(spec, ROOT, tmp_path / "direct")
    direct.advance()
    observed = json.loads(report.stdout)["records"]["decisions"][-1]
    assert observed == direct.state().decisions[-1].to_dict()
    again = runner.invoke(
        cli, ["campaign", "run", str(spec), "--source-root", str(ROOT), "--workdir", str(work)]
    )
    assert again.exit_code == 2


def test_cli_idle_cancel_and_json_schema_error(tmp_path):
    runner = CliRunner()
    work = tmp_path / "cancel"
    runner.invoke(
        cli,
        [
            "campaign",
            "run",
            str(fresh_spec(tmp_path)),
            "--source-root",
            str(ROOT),
            "--workdir",
            str(work),
            "--max-new-evaluations",
            "0",
        ],
    )
    cancelled = runner.invoke(cli, ["campaign", "cancel", str(work), "--request-id", "stop-1"])
    assert cancelled.exit_code == 0
    assert json.loads(cancelled.stdout)["status"] == "queued"
    resumed = runner.invoke(cli, ["campaign", "resume", str(work)])
    assert resumed.exit_code == 0
    assert json.loads(resumed.stdout)["outcome"] == "cancelled"
    invalid = runner.invoke(cli, ["campaign", "request", str(work)], input="{broken")
    assert invalid.exit_code == 2
    assert json.loads(invalid.stdout)["error"] == "schema_error"


def test_request_report_is_read_only_and_cancel_retries_preserve_response(tmp_path):
    from dataclasses import replace
    from autoengineering.campaign.records import Request, Response

    controller = CampaignController.create(
        fresh_spec(tmp_path),
        ROOT,
        tmp_path / "campaign",
        max_new_evaluations=0,
    )
    request = Request("1.0", controller.spec.name, "report-read", 0, "report", {})
    before = {str(p): p.read_bytes() for p in controller.store.root.rglob("*") if p.is_file()}
    result = Response.from_json(controller.service.request_json(request.to_json()))
    assert result.status == "ok" and "report" in result.result
    assert before == {
        str(p): p.read_bytes() for p in controller.store.root.rglob("*") if p.is_file()
    }
    bad = replace(request, request_id="bad-report", payload={"code": "ignored"})
    assert controller.service.handle(bad).error == "schema_error"
    cancel = Request(
        "1.0", controller.spec.name, "cancel-1", controller.store.replay().revision, "cancel", {}
    )
    first = controller.service.handle(cancel)
    assert first.result["status"] == "queued"
    controller.advance()
    assert controller.service.handle(cancel) == first
    assert (
        controller.service.handle(replace(cancel, expected_revision=999)).error
        == "request_conflict"
    )


def test_invalid_utf8_has_a_bounded_transport_receipt(tmp_path):
    import hashlib

    controller = CampaignController.create(
        fresh_spec(tmp_path),
        ROOT,
        tmp_path / "campaign",
        max_new_evaluations=0,
    )
    raw = b"\xffinvalid"
    response = json.loads(controller.service.request_bytes(raw))
    assert response["error"] == "schema_error"
    receipt = next((controller.store.root / "control").glob("transport-*.json"))
    recorded = json.loads(receipt.read_text())
    assert recorded["size_bytes"] == len(raw)
    assert recorded["sha256"] == hashlib.sha256(raw).hexdigest()
    assert controller.store.replay().revision == 0


def test_valid_negative_decision_has_zero_exit_and_no_eligible_recommendation(tmp_path):
    from dataclasses import replace
    from examples.campaign_contracts.build_fixture import fixture

    spec = fixture()
    spec = replace(
        spec,
        acceptance=replace(
            spec.acceptance,
            checks=tuple(replace(check, version="unavailable") for check in spec.acceptance.checks),
        ),
    )
    path = tmp_path / "negative.yaml"
    spec.to_yaml(path)
    result = CliRunner().invoke(
        cli,
        [
            "campaign",
            "run",
            str(path),
            "--source-root",
            str(ROOT),
            "--workdir",
            str(tmp_path / "negative"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["outcome"] == "no_eligible_model"
    controller = CampaignController.open(tmp_path / "negative", inspect_only=True)
    assert controller.state().decisions[-1].selected_id is None
    direct = CampaignController.create(path, ROOT, tmp_path / "negative-direct")
    direct.advance()
    assert direct.state().decisions[-1] == controller.state().decisions[-1]


def test_committed_markdown_links_resolve_to_immutable_records(tmp_path):
    import re

    controller = CampaignController.create(fresh_spec(tmp_path), ROOT, tmp_path / "report-links")
    controller.advance()
    final = controller.store.replay().events[-1]
    report = next(ref for ref in final.artifacts if ref.media_type == "text/markdown")
    location = controller.store.root / report.path
    body = location.read_text()
    links = re.findall(r"\]\(([^)]+)\)", body)
    assert len(links) == 3  # Two model outputs and the complete immutable checks/metrics.
    for target in links:
        resolved = (location.parent / target).resolve()
        assert resolved.is_file()
        assert resolved.is_relative_to(controller.store.root)
    assert any(target.endswith("state.json") for target in links)
