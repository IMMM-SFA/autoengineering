"""Batch preparation and inspection have no host, science or credential access."""

import json
import os
from pathlib import Path
import subprocess
import sys

from click.testing import CliRunner

from autoengineering.cli import cli
from test_agent_batch import specification


def test_prepare_freezes_batch_and_status_reconstructs_without_calls(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "spec.json"
    source.write_text(specification().to_json())
    args = ["agents", "batch-prepare", str(source), "--workdir", str(tmp_path / "batch")]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "ready" and report["host_reservations_charged"] == 0
    before = {str(p): p.read_bytes() for p in (tmp_path / "batch").rglob("*") if p.is_file()}
    status = CliRunner().invoke(
        cli,
        [
            "agents",
            "batch-status",
            str(tmp_path / "batch"),
            "--expected-digest",
            report["batch_digest"],
        ],
    )
    assert status.exit_code == 0 and json.loads(status.stdout) == report
    assert before == {
        str(p): p.read_bytes() for p in (tmp_path / "batch").rglob("*") if p.is_file()
    }
    duplicate = CliRunner().invoke(cli, args)
    assert duplicate.exit_code == 2
    assert before == {
        str(p): p.read_bytes() for p in (tmp_path / "batch").rglob("*") if p.is_file()
    }


def test_batch_status_does_not_import_physical_implementations(tmp_path):
    tmp_path.chmod(0o700)
    source = tmp_path / "spec.json"
    source.write_text(specification().to_json())
    prepared = CliRunner().invoke(
        cli, ["agents", "batch-prepare", str(source), "--workdir", str(tmp_path / "batch")]
    )
    assert prepared.exit_code == 0, prepared.output
    code = """
import sys
from click.testing import CliRunner
from autoengineering.cli import cli
r=CliRunner().invoke(cli,['agents','batch-status',sys.argv[1]])
assert r.exit_code==0,r.output
for name in ('autoengineering.agents.batch_native','autoengineering.agents.batch_science',
             'autoengineering.agents.hosts.brokered_host','autoengineering.campaign.controller',
             'torch','openai'):
    assert name not in sys.modules,name
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(tmp_path / "batch")],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
    )
    assert result.returncode == 0, result.stderr
