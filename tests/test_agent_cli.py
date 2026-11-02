"""CLI parity and report reconstruction without host/scientific imports."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys

from click.testing import CliRunner

from autoengineering.agents.report import evidence_report
from autoengineering.agents.store import WorkerStore
from autoengineering.cli import cli
from examples.agent_campaign.run import prepare


def test_all_agent_commands_are_registered_and_validate_never_launches(tmp_path):
    root = tmp_path / "example"
    prepare(root)
    runner = CliRunner()
    help_result = runner.invoke(cli, ["agents", "--help"])
    assert help_result.exit_code == 0
    for name in ("validate", "run", "resume", "status", "cancel", "report"):
        assert name in help_result.output
    validated = runner.invoke(
        cli,
        ["agents", "validate", str(root / "agent-run.json"), "--campaign", str(root / "campaign")],
    )
    assert validated.exit_code == 0, validated.output
    assert json.loads(validated.stdout)["status"] == "ok"
    assert not (root / "worker").exists()
    wrong = root / "agent-run.json"
    data = json.loads(wrong.read_text())
    data["campaign_identity"] = "0" * 64
    wrong.write_text(json.dumps(data))
    rejected = runner.invoke(
        cli,
        [
            "agents",
            "run",
            str(wrong),
            "--campaign",
            str(root / "campaign"),
            "--workdir",
            str(root / "worker"),
        ],
    )
    assert rejected.exit_code == 2
    assert not (root / "worker").exists()


def test_cli_supplied_workflow_matches_script_and_replay_has_no_new_work(tmp_path):
    root = tmp_path / "cli"
    prepare(root)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "agents",
            "run",
            str(root / "agent-run.json"),
            "--campaign",
            str(root / "campaign"),
            "--workdir",
            str(root / "worker"),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "completed"
    assert report["campaign_outcome"] == "accepted_candidate"
    assert len(report["invocations"]) == 7
    assert report["allowances"]["invocations_with_unknown_usage"] == 7
    assert report["physical_work"]["attempts"] == 2
    assert report["physical_work"]["cost_is_uncertain"] is False
    assert report["scientific_evidence"]["selected_configuration"] == {"multiplier": 1.5}
    assert report["scientific_evidence"]["objective_value"] == 0
    assert report["confirmation"] == "confirmation_not_attempted"
    assert report["wall_seconds_observed"] > 0
    before = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    resumed = runner.invoke(
        cli, ["agents", "resume", str(root / "worker"), "--campaign", str(root / "campaign")]
    )
    assert resumed.exit_code == 0, resumed.output
    assert json.loads(resumed.stdout)["invocations"] == report["invocations"]
    assert before == {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }
    # Compare scientific outcomes and call counts with the direct broker test
    # rather than requiring randomized run/nonce hashes to coincide.
    worker = WorkerStore(root / "worker")
    assert evidence_report(worker) == report
    markdown = runner.invoke(
        cli, ["agents", "report", str(root / "worker"), "--format", "markdown"]
    )
    assert markdown.exit_code == 0
    links = re.findall(r"\]\(([^)]+)\)", markdown.stdout)
    assert links
    for target in links:
        resolved = (root / "worker" / target).resolve()
        assert resolved.is_file()
        assert resolved.is_relative_to(root / "worker")
    # Completed reports remain available when the evaluator-owned campaign is offline.
    (root / "campaign").rename(root / "campaign-offline")
    offline = runner.invoke(cli, ["agents", "report", str(root / "worker")])
    assert offline.exit_code == 0, offline.output
    assert json.loads(offline.stdout)["scientific_evidence"] == report["scientific_evidence"]
    task = next(iter(worker.replay().tasks.values()))
    (worker.root / task.grants[0].artifact.path).write_bytes(b"corrupt summary")
    corrupt = runner.invoke(cli, ["agents", "report", str(root / "worker")])
    assert corrupt.exit_code == 2


def test_status_report_import_neither_host_nor_scientific_controller(tmp_path):
    root = tmp_path / "prepared"
    _, spec = prepare(root)
    WorkerStore.create(root / "worker", spec)
    source = """
import json,sys
from click.testing import CliRunner
from autoengineering.cli import cli
result = CliRunner().invoke(cli, ['agents', 'report', sys.argv[1]])
assert result.exit_code == 0, result.output
assert json.loads(result.stdout)['status'] == 'idle'
status = CliRunner().invoke(cli, ['agents', 'status', sys.argv[1]])
assert status.exit_code == 0
for name in ('autoengineering.campaign.controller', 'autoengineering.campaign.runtime',
             'autoengineering.agents.hosts.fake', 'autoengineering.agents.hosts.scripted',
             'autoengineering.agents.hosts.codex', 'torch', 'openai'):
    assert name not in sys.modules, name
"""
    process = subprocess.run(
        [sys.executable, "-c", source, str(root / "worker")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
    )
    assert process.returncode == 0, process.stderr


def test_corruption_is_visible_and_cancellation_does_not_claim_a_stop(tmp_path):
    root = tmp_path / "prepared"
    _, spec = prepare(root)
    store = WorkerStore.create(root / "worker", spec)
    runner = CliRunner()
    with store.writer():
        cancelled = runner.invoke(
            cli, ["agents", "cancel", str(store.root), "--campaign", str(root / "campaign")]
        )
    assert cancelled.exit_code == 0, cancelled.output
    assert json.loads(cancelled.stdout)["scientific_stop"] == "queued"
    status = runner.invoke(cli, ["agents", "status", str(store.root)])
    assert json.loads(status.stdout)["status"] == "cancel_queued"
    event = store.events_path / "000000000001.json"
    event.write_bytes(b"corrupt")
    report = runner.invoke(cli, ["agents", "report", str(store.root)])
    assert report.exit_code == 2
    assert json.loads(report.stdout)["status"] == "error"
