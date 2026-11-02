"""Capture the scientific source snapshot and precise remaining admission state."""

from __future__ import annotations

import json
from pathlib import Path
import platform
import shutil

from examples.utility.consolidated_sources import DEFAULT, save, sha


def main():
    snapshot = DEFAULT / "source-snapshot"
    snapshot.mkdir(mode=0o700, exist_ok=False)
    paths = list(Path("src/autoengineering").rglob("*.py"))
    for folder in (
        "examples/utility",
        "examples/campaign_contracts",
        "examples/leaf_river/models",
        "examples/interoperability/circuit",
        "examples/open_chains/wind",
    ):
        paths.extend(Path(folder).glob("*.py"))
    paths.extend([Path("pixi.lock"), Path("pixi.toml"), Path("pyproject.toml")])
    inventory = {}
    for path in sorted(set(paths)):
        target = snapshot / path
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        target.chmod(0o444)
        inventory[str(path)] = sha(target)
    for path in sorted(snapshot.rglob("*"), reverse=True):
        if path.is_dir():
            path.chmod(0o555)
    snapshot.chmod(0o555)
    source = {
        "schema": "utility-consolidated-scientific-snapshot-v1",
        "files": inventory,
        "snapshot_path": str(snapshot),
        "immutability": "read-only files plus SHA256 verification",
        "host_snapshot": "not frozen: required qualification artifact missing",
        "platform": platform.platform(),
    }
    public = Path("examples/utility/consolidated")
    save(public / "scientific-source-snapshot.json", source)
    refs = json.loads((DEFAULT / "baselines/complete.json").read_text())
    save(public / "baseline-references.json", refs)
    tasks = {}
    for name in ("hydrology", "solar", "wind", "wind_development"):
        path = DEFAULT / name / "complete.json"
        receipt = json.loads(path.read_text())
        tasks[name] = {
            "receipt_path": str(path),
            "sha256": sha(path),
            "status": receipt["status"],
            **{
                k: receipt[k]
                for k in (
                    "rows",
                    "usable_rows",
                    "network_requests",
                    "actual_response_bytes",
                    "elapsed_seconds",
                )
                if k in receipt
            },
        }
    tasks["wind"]["staged_binary_encoding"] = (
        "interleaved little-endian speed/direction float64; not the annual source service concatenated encoding"
    )
    host = Path("outputs/campaign-part3-proposal-context-20261027/prepared-study/host.toml")
    runtime = {
        "schema": "utility-consolidated-runtime-readiness-v1",
        "source_staging": tasks,
        "study_binding_sha256": sha(public / "task-bindings.json"),
        "snapshot_manifest_sha256": sha(public / "scientific-source-snapshot.json"),
        "baselines": {
            task: {"value": r["value"], "absolute_gain": r["absolute_gain"], "units": r["units"]}
            for task, r in refs["references"].items()
        },
        "selection_entrypoints": {
            task: f"examples.utility.consolidated_runtime:{task}"
            for task in ("hydrology", "solar", "engineering", "wind")
        },
        "selection_limits": {
            "seconds_shared_host_and_science": 600,
            "fixed_evaluations_maximum": 8,
            "fixed_cost_candidate_safety_cap": 32,
            "host_invocations": 12,
            "accounting": "full timeout reserved before launch; no refunds or automatic retries",
        },
        "confirmation_entrypoints": {
            "wind": "examples.utility.wind_common_confirmation:CommonConfirmationWindScorer",
            "engineering": "examples.utility.engineering_common_confirmation:CommonConfirmationLoadScorer",
        },
        "confirmation_private_boundary_qualified": False,
        "host": {
            "configuration_path": str(host),
            "configuration_sha256": sha(host),
            "verification": "failed",
            "missing_artifact": "qualification.json",
            "qualification_root": "/private/tmp/part3-proposal-context-20261027/native",
            "credentials_read": False,
            "provider_calls": 0,
        },
        "dispatch_status": "blocked_missing_host_evidence_and_incomplete_suite_integration",
        "execution_allowed": False,
        "remaining": [
            "Supply or recreate the native host qualification and verify its current executable/runtime identities",
            "Assemble the two final suite manifests and protected worker/scorer registrations, including hydrology and solar confirmation adapters",
            "Create the single fresh engineering draw under that final suite identity, then seal the staged sources to it",
        ],
        "new_development_model_starts": 4,
        "confirmation_model_starts": 0,
        "limits": [
            "Scientific entry points and tested supervisor are not a live-agent suite coordinator",
            "Hydrology development baseline volume bias is 0.23065126211954046; the 0.10 tolerance is unchanged",
            "Prior confirmation grants and historical source hashes are not silently updated",
        ],
    }
    save(public / "execution-readiness.json", runtime)
    print(
        json.dumps(
            {
                "snapshot_files": len(inventory),
                "readiness_path": str(public / "execution-readiness.json"),
                "execution_allowed": False,
            }
        )
    )


if __name__ == "__main__":
    main()
