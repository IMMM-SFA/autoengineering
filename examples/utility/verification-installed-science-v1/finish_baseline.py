"""Finish and verify the installed four-family baseline smoke through the public CLI."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.utility.store import SuiteStore

parser = argparse.ArgumentParser()
parser.add_argument("root", type=Path)
args = parser.parse_args()
root = args.root.resolve()
suite = root / "prepared-baseline-suite"
plan = root / "prepared-baseline-plan.json"
source = root / "captured"
results = []


def command(name, values):
    before = time.monotonic()
    result = subprocess.run(
        [sys.executable, "-I", "-m", "autoengineering.cli", "utility", *values],
        capture_output=True,
        text=True,
        check=True,
        timeout=180,
    )
    doc = json.loads(result.stdout)
    results.append(
        {
            "command": name,
            "returncode": result.returncode,
            "elapsed_seconds": time.monotonic() - before,
            "result": doc,
        }
    )
    (root / ("baseline-" + name + ".json")).write_text(json.dumps(doc, indent=2) + "\n")
    return doc


repeated = command(
    "completed-resume",
    ["resume", str(suite), str(plan), "--source-root", str(source), "--scripted-development"],
)
assert repeated["completed_this_call"] == 0 and repeated["finished_cells"] == 4
proposal = ArtifactRef.from_dict(repeated["selection_proposal"])
manifest = root / "baseline-selection.json"
manifest.write_bytes(read_bytes(suite, proposal))
command("freeze", ["freeze", str(suite), str(manifest)])
command("verify", ["verify", str(suite)])
command("status", ["status", str(suite)])
state = SuiteStore(suite).replay()
assert state["frozen"] is not None and not state["confirmation_accesses"]
summary = {
    "status": "passed",
    "scope": "installed four-family baseline smoke from exported exposed inputs",
    "cells": 4,
    "completed_resume_added_cells": 0,
    "selection": state["frozen"],
    "commands": results,
    "confirmation_accesses": 0,
    "utility_verdict": "not_attempted",
}
(root / "baseline-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps({k: v for k, v in summary.items() if k != "commands"}))
