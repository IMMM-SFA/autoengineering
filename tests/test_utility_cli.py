"""Utility CLI never turns offline preparation into execution authority."""
import json
import subprocess
import sys

from click.testing import CliRunner

from autoengineering.cli import cli
from autoengineering.utility.confirmation import SelectionManifest, SelectedCell
from test_utility_contracts import suite


def test_prepare_status_report_freeze_and_verify(tmp_path):
    spec = suite()
    source = tmp_path / "suite.json"
    source.write_text(spec.to_json())
    work = tmp_path / "work"
    runner = CliRunner()
    valid = runner.invoke(cli, ["utility", "validate", str(source)])
    assert valid.exit_code == 0 and json.loads(valid.output)["cells"] == 2
    prepared = runner.invoke(cli, ["utility", "prepare", str(source), "--source-root", str(tmp_path),
                                    "--workdir", str(work)])
    assert prepared.exit_code == 0, prepared.output
    assert json.loads(prepared.output)["status"] == "blocked"
    state = runner.invoke(cli, ["utility", "status", str(work)])
    assert json.loads(state.output)["revision"] == 0
    report = runner.invoke(cli, ["utility", "report", str(work), "--format", "markdown"])
    assert report.exit_code == 0 and "Cost evidence is incomplete" in report.output
    manifest = SelectionManifest("utility-selection-v1", spec.digest, spec.protocol_digest,
        [SelectedCell(c.digest, "not_attempted", None, None, None, "Blocked fixture") for c in spec.cells])
    selection = tmp_path / "selection.json"
    selection.write_text(manifest.to_json())
    assert runner.invoke(cli, ["utility", "freeze", str(work), str(selection)]).exit_code == 0
    verified = runner.invoke(cli, ["utility", "verify", str(work)])
    assert verified.exit_code == 0
    assert json.loads(verified.output)["status"] == "verified_integrity"
    assert json.loads(verified.output)["utility_verdict"] == "not_attempted"


def test_offline_cli_does_not_import_optional_frameworks(tmp_path):
    spec = suite()
    path = tmp_path / "suite.json"
    path.write_text(spec.to_json())
    code = '''
import sys
from click.testing import CliRunner
from autoengineering.cli import cli
r = CliRunner().invoke(cli, ['utility', 'validate', sys.argv[1]])
assert r.exit_code == 0, r.output
assert not {'torch','botorch','openmdao','pvlib','py_wake','topfarm'} & set(sys.modules)
'''
    subprocess.run([sys.executable, "-c", code, str(path)], check=True)


def test_malformed_inputs_do_not_leak_payload(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"private-canary":"DO-NOT-PRINT"}')
    result = CliRunner().invoke(cli, ["utility", "validate", str(path)])
    assert result.exit_code == 2
    assert "DO-NOT-PRINT" not in result.output
    assert json.loads(result.output)["error"] == "invalid_utility_evidence"


def test_execution_requires_explicit_scripted_development_mode(tmp_path):
    from autoengineering.utility.store import SuiteStore
    root = SuiteStore.create(tmp_path / "suite", suite()).root
    plan = tmp_path / "plan.json"
    plan.write_text('{}')
    result = CliRunner().invoke(cli, ["utility", "run", str(root), str(plan),
                                     "--source-root", str(tmp_path)])
    assert result.exit_code == 2
    assert not (root / "control/execution-plan.json").exists()
