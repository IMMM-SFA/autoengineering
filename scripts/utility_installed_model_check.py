"""Qualify an installed wheel with a bounded authored development campaign.

The producer uses the repository's tiny test fixture. All execution occurs through
an installed wheel outside the checkout. Dependencies are inherited from the
invoking environment; no dependency download or global installation occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


ROOT = Path(__file__).resolve().parents[1]


def checked_run(command, *, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"installed check command failed: {result.stderr}\n{result.stdout}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--output", type=Path, required=True,
                        help="New retained evidence directory outside the checkout")
    args = parser.parse_args()
    root, wheel = args.output.absolute(), args.wheel.absolute()
    if root.is_relative_to(ROOT) or root.exists() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError("use an absent evidence directory outside the checkout without symlink ancestors")
    root.mkdir(mode=0o700, parents=True)
    # Compile the trusted authored fixture before switching interpreter/package.
    sys.path[:0] = [str(ROOT / "tests"), str(ROOT), str(ROOT / "src")]
    from test_utility_execution import setup
    store, plan, source = setup(root)
    execution = root / "execution.json"
    execution.write_text(plan.to_json())
    operations = []
    with tempfile.TemporaryDirectory(prefix="utility-model-venv-") as temporary:
        prefix = Path(temporary).resolve() / "venv"
        venv.EnvBuilder(system_site_packages=True, with_pip=False).create(prefix)
        python = prefix / "bin/python"
        env = {"PATH": str(prefix / "bin")+os.pathsep+os.defpath,
               "LANG": "C.UTF-8", "PYTHONDONTWRITEBYTECODE": "1",
               "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1"}
        checked_run([str(python), "-I", "-m", "pip", "--isolated", "--disable-pip-version-check",
            "--no-cache-dir", "install", "--no-deps", "--no-index", "--ignore-installed", "--no-user",
            "--prefix", str(prefix), str(wheel)], cwd=root, env=env)
        probe = checked_run([str(python), "-I", "-c",
            "import json,sys; import autoengineering.utility.execution as e; "
            "import examples.campaign_contracts.fixture_model as m; "
            "print(json.dumps({'prefix':sys.prefix,'execution':e.__file__,'model':m.__file__}))"], cwd=root, env=env)
        modules = json.loads(probe)
        assert all(Path(modules[name]).is_relative_to(prefix) for name in ("execution", "model"))
        driver = prefix / "bin/autoengineering"

        def invoke(command, *arguments):
            raw = checked_run([str(driver), "utility", command, str(store.root), *map(str, arguments)], cwd=root, env=env)
            document = json.loads(raw)
            operations.append({"command": command, "result": document})
            return document

        common = [execution, "--source-root", source, "--scripted-development"]
        first = invoke("run", *common, "--max-new-cells", 1)
        assert first["finished_cells"] == 1
        second = invoke("resume", *common)
        assert second["finished_cells"] == second["assigned_cells"] == 2
        jobs = sorted(store.root.glob("children/*/cases/*/campaign/attempts/*/job.json"))
        assert len(jobs) == 4
        for job in jobs:
            command = json.loads(job.read_text())["command"]
            assert command[:3] == [str(python), "-m", "autoengineering.campaign.model_worker"]
            result = json.loads(job.with_name("supervisor-result.json").read_text())
            assert result["status"] == "success" and result["stopped"] and result["receipt_valid"]
        repeated = invoke("resume", *common)
        assert repeated["completed_this_call"] == 0
        assert len(list(store.root.glob("children/*/cases/*/campaign/attempts/*/job.json"))) == len(jobs)
        proposal = store.root / second["selection_proposal"]["path"]
        invoke("freeze", proposal)
        report = invoke("report")
        assert report["assigned_cells"] == 2 and report["confirmation_state"] == "not_attempted"
        assert invoke("verify")["status"] == "verified_integrity"
        invoke("status")
        summary = {"status": "passed", "profile": "authored scripted supplied development only",
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "installed_modules": {key: str(Path(value).relative_to(prefix)) for key, value in modules.items() if key != "prefix"},
            "fixture_source": "tests/test_utility_execution.py:setup", "assigned_cells": 2,
            "verified_scientific_processes": len(jobs), "repeat_resume_added_processes": 0,
            "confirmation": "not_attempted", "providers_contacted": 0,
            "dependency_profile": "temporary venv inherits invoking environment packages",
            "executed_commands": [entry["command"] for entry in operations]}
        (root / "operations.json").write_text(json.dumps(operations, indent=2)+"\n")
        (root / "summary.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
