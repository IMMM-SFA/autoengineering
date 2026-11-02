"""Install a local wheel and run authored Claude transport fixtures outside checkout."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import sysconfig
import xml.etree.ElementTree as ET
import zipfile

project = Path.cwd()
record = project / "examples/utility/verification-second-host-v1"
root = Path("/private/tmp/utility-claude-installed-v3")
root.mkdir(mode=0o700)
wheels = root / "wheels"
wheels.mkdir()
with (record / "wheel-build.log").open("w") as log:
    subprocess.run([sys.executable, "-c", "import setuptools.build_meta as b; b.build_wheel(" + repr(str(wheels)) + ")"], check=True, stdout=log, stderr=subprocess.STDOUT)
wheel = next(wheels.glob("*.whl"))
with zipfile.ZipFile(wheel) as archive:
    for p in (project / "src/autoengineering").rglob("*.py"):
        assert archive.read(str(p.relative_to(project / "src"))) == p.read_bytes()
subprocess.run([str(Path(sys.executable).resolve()), "-m", "venv", str(root / "venv")], check=True)
python = root / "venv/bin/python"
site = Path(subprocess.check_output([str(python), "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"], text=True).strip())
(site / "dependencies.pth").write_text(str(Path(sysconfig.get_paths()["purelib"]).resolve()) + "\n")
with (record / "wheel-install.log").open("w") as log:
    subprocess.run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", "--ignore-installed", str(wheel)], check=True, stdout=log, stderr=subprocess.STDOUT)
shutil.copyfile(project / "tests/test_agent_claude.py", root / "test_agent_claude.py")
policy = project / "examples/utility/verification-installed-science-v1/sitecustomize.py"
shutil.copyfile(policy, site / "sitecustomize.py")
check = "from pathlib import Path;import importlib.util;import autoengineering.agents.hosts.claude as c;assert not Path(c.__file__).resolve().is_relative_to(Path('/Users/cam/projects/autoengineering'));assert importlib.util.find_spec('anthropic') is None;print(c.__file__)"
with (record / "installed-origin.log").open("w") as log:
    subprocess.run([str(python), "-c", check], cwd=root, check=True, stdout=log, stderr=subprocess.STDOUT)
with (record / "installed-tests.log").open("w") as log:
    subprocess.run([str(python), "-m", "pytest", str(root / "test_agent_claude.py"), "-q", "-p", "no:cacheprovider", "--junitxml=" + str(root / "tests.xml")], cwd=root, env=os.environ | {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}, check=True, stdout=log, stderr=subprocess.STDOUT)
shutil.copyfile(root / "tests.xml", record / "installed-tests.xml")
suite = ET.parse(root / "tests.xml").getroot().find("testsuite")
assert int(suite.get("failures")) == int(suite.get("errors")) == 0
result = {"status": "passed", "tests": int(suite.get("tests")), "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "all_current_core_python_bytes_match": True, "module_origin": "fresh installed wheel outside checkout", "original_checkout_python_opens": "denied", "network_sockets": "denied", "anthropic_sdk": "absent", "real_claude_inference": "not_attempted", "scope": "authored offline transport fixtures only; not an admitted scheduler host or live conformance", "dependencies": "cached default paths without editable activation; not a clean minimal solve"}
(record / "installed-summary.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
