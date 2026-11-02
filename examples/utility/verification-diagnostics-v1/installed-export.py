"""Reconstruct all diagnostic tables from copied pins using the qualified wheel."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

project = Path.cwd()
record = project / "examples/utility/verification-diagnostics-v1"
original = project / "examples/utility/development/diagnostics-four-family-v4"
summary = json.loads((original / "summary.json").read_text())
root = Path("/private/tmp/utility-diagnostics-reader-v2")
root.mkdir(mode=0o700)
source = root / "inputs"
source.mkdir(mode=0o700)
for name, expected in summary["inputs"].items():
    raw = (project / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected
    target = source / name
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    target.write_bytes(raw)
reader = root / "export.py"
shutil.copyfile(project / "scripts/utility_development_diagnostics.py", reader)
python = Path("/private/tmp/utility-preflight-reader-v2/venv/bin/python")
check = "import importlib.util,autoengineering;from pathlib import Path;assert not Path(autoengineering.__file__).resolve().is_relative_to(Path('/Users/cam/projects/autoengineering'));assert all(importlib.util.find_spec(n) is None for n in ('py_wake','topfarm','openmdao','pvlib'));print(autoengineering.__file__)"
with (record / "installed-origins.log").open("w") as log:
    subprocess.run([str(python), "-c", check], cwd=root, check=True, stdout=log, stderr=subprocess.STDOUT)
with (record / "installed-export.log").open("w") as log:
    subprocess.run([str(python), str(reader), "--project", str(source), "--output", str(root / "export")], cwd=root, check=True, stdout=log, stderr=subprocess.STDOUT)
reconstructed = json.loads((root / "export/summary.json").read_text())
assert reconstructed == summary
for name in summary["tables"]:
    assert (root / "export" / name).read_bytes() == (original / name).read_bytes()
wheel = json.loads((project / "examples/utility/verification-preflight-v1/installed-reader-summary.json").read_text())
result = {
    "status": "passed",
    "wheel_sha256": wheel["sha256"],
    "all_tables_byte_identical": True,
    "summary_identical": True,
    "files_copied": len(summary["inputs"]),
    "table_rows": summary["table_rows"],
    "original_checkout_opens": "denied by existing installed Python audit policy",
    "optional_scientific_packages": "absent",
    "model_imports_process_and_socket_dispatch": "denied inside exporter",
    "confirmation": "not_attempted",
    "scope": "fresh installed reader reconstructs saved development diagnostics, not a complete private confirmation package",
}
(record / "installed-export-summary.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
