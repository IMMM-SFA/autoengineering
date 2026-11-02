"""Build and check a local installed reader without optional scientific packages."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig
import zipfile

project = Path.cwd()
record = project / "examples/utility/verification-preflight-v1"
root = Path("/private/tmp/utility-preflight-reader-v2")
root.mkdir(mode=0o700)
wheel_dir = root / "wheels"
wheel_dir.mkdir()
with (record / "wheel-build.log").open("w") as log:
    subprocess.run([sys.executable, "-c", "import setuptools.build_meta as b; b.build_wheel(" + repr(str(wheel_dir)) + ")"], check=True, stdout=log, stderr=subprocess.STDOUT)
wheel = next(wheel_dir.glob("*.whl"))
with zipfile.ZipFile(wheel) as z:
    for source in (project / "src/autoengineering").rglob("*.py"):
        assert z.read(str(source.relative_to(project / "src"))) == source.read_bytes()
subprocess.run([str(Path(sys.executable).resolve()), "-m", "venv", str(root / "venv")], check=True)
python = root / "venv/bin/python"
site = Path(subprocess.check_output([str(python), "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], text=True).strip())
(site / "dependencies.pth").write_text(str(Path(sysconfig.get_paths()["purelib"]).resolve()) + "\n")
with (record / "wheel-install.log").open("w") as log:
    subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", "--ignore-installed", str(wheel)], check=True, stdout=log, stderr=subprocess.STDOUT)
probe = project / "examples/utility/development/wind-preflight-v1"
archive = root / "probe"
shutil.copytree(probe / "batch", archive / "batch")
shutil.copyfile(probe / "execution.json", archive / "execution.json")
reader = (record / "check-reader.py").read_text().replace('root = Path("examples/utility/development/wind-preflight-v1").absolute()', 'root = Path(' + repr(str(archive)) + ')')
(root / "reader.py").write_text(reader)
policy = (project / "examples/utility/verification-installed-science-v1/sitecustomize.py").read_text()
(site / "sitecustomize.py").write_text(policy)
check = "import importlib.util, autoengineering; from pathlib import Path; p=Path(autoengineering.__file__).resolve(); assert not p.is_relative_to(Path('/Users/cam/projects/autoengineering')); assert all(importlib.util.find_spec(n) is None for n in ('py_wake','topfarm','openmdao','pvlib')); print(p)"
subprocess.run([str(python), "-c", check], cwd=root, check=True)
with (record / "installed-reader.log").open("w") as log:
    subprocess.run([str(python), str(root / "reader.py")], cwd=root, check=True, stdout=log, stderr=subprocess.STDOUT)
summary = {
    "wheel": wheel.name,
    "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
    "all_core_python_bytes_match": True,
    "optional_scientific_packages_present": False,
    "original_checkout_python_opens": "denied",
    "network_sockets": "denied",
    "installed_rejection_reader": json.loads((archive / "reader-summary.json").read_text()),
    "dependency_scope": "cached default environment paths without editable activation; not a clean minimal dependency solve",
    "boundary": "Python audit policy, not an OS private scorer boundary",
}
(record / "installed-reader-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary))
