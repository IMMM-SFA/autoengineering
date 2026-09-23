"""Recalculate every final BMI observation and held-out recommendation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from examples.local_models.models import MODELS, load_data, metrics


def audit(directory: Path) -> dict:
    records = json.loads((directory / "results.json").read_text())["runs"]
    checked, issues, ledger_hashes = 0, [], {}
    for row in records:
        domain = row["domain"]
        data = load_data(domain)
        development = data.loc[data.split != "test"]
        stem = f"{domain}-{row['method']}-{row['seed']}"
        path = directory / stem / "observations.jsonl"
        ledger_hashes[stem] = hashlib.sha256(path.read_bytes()).hexdigest()
        entries = [json.loads(line) for line in path.read_text().splitlines()]
        for entry in entries:
            action, result = entry["action"], entry["result"]
            value = metrics(
                domain, development, MODELS[domain](development, action["config"]), "validation"
            )["rmse"]
            checked += 1
            if (
                result["status"] != "success"
                or result["cost"] != 1.0
                or result["cost_unit"] != "model_call"
                or set(result["outcomes"]) != {"rmse"}
                or not math.isclose(value, result["outcomes"]["rmse"], abs_tol=1e-10, rel_tol=1e-10)
            ):
                issues.append(f"{stem}/{action['id']}: observation mismatch")
        recommendation = row["recommendation"]
        selected = [
            entry for entry in entries if entry["action"]["id"] == recommendation["action_id"]
        ]
        if (
            len(selected) != 1
            or selected[0]["action"]["config"] != recommendation["config"]
            or recommendation["outcomes"] != selected[0]["result"]["outcomes"]
        ):
            issues.append(f"{stem}: recommendation does not match observed action")
        test = metrics(domain, data, MODELS[domain](data, recommendation["config"]), "test")
        for name, value in test.items():
            if not math.isclose(value, row["test"][name], rel_tol=1e-10, abs_tol=1e-10):
                issues.append(f"{stem}: held-out {name} differs")
        print(f"Audited {stem}", flush=True)
    return {
        "observations_recalculated": checked,
        "recommendations_recalculated": len(records),
        "issues": issues,
        "ledger_sha256": ledger_hashes,
        "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.directory)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    if result["issues"]:
        raise SystemExit("Audit failed: " + str(result["issues"]))
    print(f"Recalculated {result['observations_recalculated']} observations with zero issues.")
