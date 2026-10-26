"""Probe macOS filesystem restrictions without running a live model or candidate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import tempfile

from .science import ROOT, task, write_json


def stage(directory: Path) -> dict:
    directory.mkdir(parents=True, exist_ok=False)
    # No observations, source paths, credentials, or evaluator records are staged.
    public = dict(
        task_id=task()["task_id"],
        scope=task()["scope"],
        candidate="supplied-gamma-v1",
        families=task()["families"],
        instructions="Propose supplied gamma routing; request equal-budget calibration; "
        "review evaluator decision without claiming catchment conservation.",
    )
    write_json(directory / "brief.json", public)
    import hashlib

    manifest = {"brief.json": hashlib.sha256((directory / "brief.json").read_bytes()).hexdigest()}
    write_json(directory / "manifest.json", manifest)
    return manifest


def probe(output: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="ae-boundary-") as temporary:
        directory = Path(temporary).resolve()
        manifest = stage(directory / "worker")
        # Protect every checkout, not only the linked worktree.
        repository = ROOT.parent.parent if ROOT.parent.name == ".worktrees" else ROOT
        quoted = json.dumps(str(repository.resolve()))
        profile = (
            f"(version 1)(allow default)(deny network*)"
            f"(deny file-read* (subpath {quoted}))"
            f"(deny file-write* (subpath {quoted}))"
        )
        profile_path = directory / "profile.sb"
        profile_path.write_text(profile)
        prefix = ["/usr/bin/sandbox-exec", "-f", str(profile_path)]
        commands = {
            "staged_read": ["/bin/cat", str(directory / "worker/brief.json")],
            "protected_read": ["/bin/cat", str(ROOT / "examples/leaf_river/data/streamflow.csv")],
            "protected_write": ["/usr/bin/touch", str(output.parent / "forbidden-write")],
        }
        results = {}
        for name, command in commands.items():
            result = subprocess.run(prefix + command, capture_output=True, text=True, timeout=10)
            results[name] = dict(returncode=result.returncode, stderr=result.stderr.strip())
        passed = (
            results["staged_read"]["returncode"] == 0
            and results["protected_read"]["returncode"] != 0
            and results["protected_write"]["returncode"] != 0
            and not (output.parent / "forbidden-write").exists()
        )
        report = dict(
            passed=passed,
            mechanism="macOS sandbox-exec deny repository reads/writes",
            scope="cat/touch probes only; no live agent or generated code executed",
            staged_manifest=manifest,
            tests=results,
        )
        write_json(output, report)
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(json.dumps(probe(parser.parse_args().output)))
