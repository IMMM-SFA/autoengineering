"""Exercise public comparative exports from a freshly extracted local wheel.

Uses only bundled synthetic unattempted cells. No model or confirmation scorer
runs. Dependencies come from the invoking Python environment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


CHECK = r'''
import json
from pathlib import Path
import socket
import subprocess
import sys
sys.path.insert(0, sys.argv[1])
def forbidden(*args, **kwargs):
    raise AssertionError("offline installed reader attempted a process or socket")
subprocess.Popen = forbidden
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
socket.socket.bind = forbidden
socket.create_connection = forbidden
from click.testing import CliRunner
from autoengineering.cli import cli
from autoengineering.campaign.artifacts import put_bytes
from autoengineering.utility.analysis import AnalysisPlan, ContrastSpec
from autoengineering.utility.confirmation import SelectedCell, SelectionManifest
from autoengineering.utility.contracts import UtilitySuiteSpec
from autoengineering.utility.reporting import ReportSpec
from autoengineering.utility.store import SuiteStore
import autoengineering.utility.reporting as installed
from dataclasses import replace
root = Path(sys.argv[1])
assert Path(installed.__file__).is_relative_to(root)

spec = UtilitySuiteSpec.from_json((root / "examples/utility/fixtures/suite.json").read_text())
route = next(r.route_id for r in spec.routes if r.kind == "multi_agent")
comparator = next(r.route_id for r in spec.routes if r.kind == "conventional")
plan = AnalysisPlan("utility-analysis-v1", (ContrastSpec(spec.tasks[0].task_id, route, comparator,
    "power", "W", "minimize", .1, 1., .95, "paired_student_t", 500, 17, "single_prespecified"),),
    "complete_pairs_and_full_denominators", "1"*64)
spec = replace(spec, analysis_digest=plan.digest)
source, work = root / "suite.json", root / "work"
source.write_text(spec.to_json())
runner, commands = CliRunner(), []

def invoke(arguments):
    result = runner.invoke(cli, ["utility", *arguments])
    assert result.exit_code == 0, (arguments[0], result.output)
    commands.append(arguments[0])
    return result.output
invoke(["validate", str(source)])
assert json.loads(invoke(["prepare", str(source), "--source-root", str(root), "--workdir", str(work)]))["status"] == "blocked"
store = SuiteStore(work)
selection = SelectionManifest("utility-selection-v1", spec.digest, spec.protocol_digest,
    tuple(SelectedCell(c.digest, "not_attempted", None, None, None, "Synthetic installed reader check") for c in spec.cells))
selection_path = root / "selection.json"
selection_path.write_text(selection.to_json())
invoke(["freeze", str(work), str(selection_path)])
analysis_ref = put_bytes(work, plan.to_json().encode(), name="analysis.json", media_type="application/json", producer="installed-check")
request = ReportSpec("utility-report-inputs-v1", spec.digest, analysis_ref, None, ())
inputs = root / "report-inputs.json"
inputs.write_text(request.to_json())
arguments = [str(work), "--inputs", str(inputs)]
report = json.loads(invoke(["report", *arguments]))
assert len(report["cells"]) == len(spec.cells)
assert report["analysis"]["contrasts"][0]["verdict"] == "inconclusive"
assert all(row["value"] is None for row in report["cells"])
export = root / "export"
manifest = json.loads(invoke(["report", *arguments, "--export-directory", str(export)]))
verification = json.loads(invoke(["verify", *arguments, "--export-directory", str(export)]))
assert verification["status"] == "verified_reconstruction"
assert "inconclusive" in invoke(["report", *arguments, "--format", "markdown"])
assert not {"torch", "botorch", "openmdao", "py_wake", "pvlib"} & sys.modules.keys()
print(json.dumps({"status":"passed", "commands": commands, "exported_files":len(manifest["files"]),
    "assigned_cells":len(spec.cells), "models_started":0, "providers_contacted":0,
    "profile":"synthetic unattempted cells; public offline reconstruction only",
    "installed_module":str(Path(installed.__file__).relative_to(root))}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="utility-installed-report-") as temporary:
        root = Path(temporary).resolve()
        with zipfile.ZipFile(args.wheel) as wheel:
            wheel.extractall(root)
        result = subprocess.run([sys.executable, "-I", "-c", CHECK, str(root)], cwd=root,
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError(result.stderr)
        document = json.loads(result.stdout)
    document["wheel_sha256"] = hashlib.sha256(args.wheel.read_bytes()).hexdigest()
    raw = json.dumps(document, indent=2)+"\n"
    if args.output:
        if args.output.exists():
            raise ValueError("check evidence output already exists")
        args.output.write_text(raw)
    print(raw, end="")


if __name__ == "__main__":
    main()
