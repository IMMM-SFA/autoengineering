"""Pinned CLI execution and read-only reporting with authored host/provider fixtures."""

import json
import os
from pathlib import Path
import subprocess
import sys

from click.testing import CliRunner
import pytest

from autoengineering.cli import cli
from autoengineering.agents.conformance import prepare_conformance
from autoengineering.agents.conformance_report import _live_complete
from test_agent_conformance import fixture as prepare_fixture, snapshot
from test_agent_conformance_runtime import fixture


def test_run_requires_original_pin_and_refuses_existing_runtime(tmp_path, monkeypatch):
    root, worker, config, config_file, calls = prepare_fixture(tmp_path, monkeypatch)
    plan = prepare_conformance(
        worker, root / "campaign", config, tmp_path / "proposal", tmp_path / "runtime"
    )
    args = [
        "agents",
        "conformance-run",
        str(tmp_path / "proposal"),
        "--expected-digest",
        plan.digest,
        "--host-config",
        str(config_file),
        "--max-new-cases",
        "0",
    ]
    wrong = CliRunner().invoke(cli, args[:4] + ["0" * 64] + args[5:])
    assert wrong.exit_code == 2 and not (tmp_path / "runtime").exists()
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    receipt = json.loads(result.stderr)
    assert receipt["event"] == "conformance_runtime_created"
    assert receipt["runtime_digest"] == report["batch_digest"]
    assert receipt["preparation_digest"] == plan.digest
    assert report["status"] == "ready" and report["host_reservations_charged"] == 0
    before = snapshot(tmp_path / "runtime")
    assert CliRunner().invoke(cli, args).exit_code == 2
    assert not calls and before == snapshot(tmp_path / "runtime")


def test_resume_keeps_pins_allowances_and_failed_gate_status(tmp_path, monkeypatch):
    runtime, config, calls = fixture(tmp_path, monkeypatch, provider=False)
    args = [
        "agents",
        "conformance-resume",
        str(runtime.preparation),
        "--expected-digest",
        runtime.preparation_digest,
        "--runtime-digest",
        runtime.batch.digest,
        "--host-config",
        str(tmp_path / "host.toml"),
    ]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 4, result.output
    report = json.loads(result.stdout)
    assert report["status"] == "failed" and report["case_results"] == {"text": "failed"}
    assert report["host_reservations_charged"] == len(calls) == 1
    before = snapshot(runtime.batch.root)
    replay = CliRunner().invoke(cli, args)
    assert replay.exit_code == 4 and json.loads(replay.stdout) == report
    assert len(calls) == 1 and snapshot(runtime.batch.root) == before
    wrong = list(args)
    wrong[wrong.index("--runtime-digest") + 1] = "0" * 64
    assert CliRunner().invoke(cli, wrong).exit_code == 2
    assert snapshot(runtime.batch.root) == before


def test_status_verifies_saved_proofs_without_physical_imports(tmp_path, monkeypatch):
    runtime, _, _ = fixture(tmp_path, monkeypatch)
    runtime.advance(max_new_cases=1)
    before = snapshot(runtime.batch.root)
    code = """
import sys,json
from click.testing import CliRunner
from autoengineering.cli import cli
r=CliRunner().invoke(cli,['agents','conformance-status',sys.argv[1],'--expected-digest',sys.argv[2]])
assert r.exit_code==0,r.output
assert json.loads(r.stdout)['case_results']=={'text':'passed'}
for name in ('autoengineering.agents.conformance_runtime','autoengineering.agents.batch_native',
             'autoengineering.agents.batch_science','autoengineering.agents.hosts.brokered_host',
             'autoengineering.campaign.controller','torch','openai'):
    assert name not in sys.modules,name
"""
    result = subprocess.run(
        [sys.executable, "-c", code, str(runtime.batch.root), runtime.batch.digest],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")},
    )
    assert result.returncode == 0, result.stderr
    assert before == snapshot(runtime.batch.root)
    status = CliRunner().invoke(
        cli,
        [
            "agents",
            "conformance-status",
            str(runtime.batch.root),
            "--expected-digest",
            runtime.batch.digest,
        ],
    )
    assert status.exit_code == 0 and json.loads(status.stdout) == runtime.report()


@pytest.mark.parametrize("problem", ["unit_attestation", "missing_case", "failed_case"])
def test_live_complete_does_not_accept_authored_or_partial_case_evidence(problem):
    from autoengineering.agents.conformance_protocol import IMPLEMENTED_CASES

    proofs = {
        name: {"kind": name, "passed": True, "provider": {"verified": True}}
        for name in IMPLEMENTED_CASES
    }
    # This isolated classifier test makes no provider or ownership claim.
    assert _live_complete({"status": "completed"}, proofs)
    if problem == "unit_attestation":
        proofs["text"]["provider"]["unit_attestation_only"] = True
    elif problem == "missing_case":
        del proofs["text"]
    else:
        proofs["text"]["passed"] = False
    assert not _live_complete({"status": "completed"}, proofs)
