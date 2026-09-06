"""Project recorded studies to a reduced cap and run the missing matrix members."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from examples.complex_models.models import DOMAINS, evaluate, load_data, score
from examples.complex_models.run import METHODS, hashes, study
from examples.local_models.run import write_json


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cutoff(entries: list, trajectory: list, cap: int, target: float) -> tuple[list, list, dict]:
    """Select only observed successful configurations at or before the stopping call."""
    if cap < 1:
        raise ValueError("cap must be positive")
    first = next(
        (
            i + 1
            for i, e in enumerate(entries[:cap])
            if e["result"]["status"] == "success" and e["result"]["outcomes"]["rmse"] <= target
        ),
        None,
    )
    n = first or cap
    if len(entries) < n or len(trajectory) < n:
        raise ValueError("Incomplete prefix: neither target hit nor requested cap available")
    retained = entries[:n]
    for i, entry in enumerate(retained):
        if (
            entry["action"]["id"] != f"eval-{i:06d}"
            or entry["result"]["cost"] != 1.0
            or entry["result"]["cost_unit"] != "model_call"
        ):
            raise ValueError("Expected canonical action order and unit model-call cost")
    steps = trajectory[:n]
    best = None
    for i, (entry, step) in enumerate(zip(retained, steps, strict=True)):
        if entry["result"]["status"] == "success":
            if (
                best is None
                or entry["result"]["outcomes"]["rmse"] < best["result"]["outcomes"]["rmse"]
            ):
                best = entry
        value = None if best is None else best["result"]["outcomes"]["rmse"]
        if step["evaluations"] != i + 1 or step["best_validation_rmse"] != value:
            raise ValueError("Trajectory disagrees with recorded observations")
        if step["target_reached"] != (value is not None and value <= target):
            raise ValueError("Trajectory target disagrees with frozen target")
    if best is None:
        raise ValueError("No successful recommendation in retained prefix")
    recommendation = {
        "action_id": best["action"]["id"],
        "config": best["action"]["config"],
        "feasible": True,
        "message": "best feasible observed configuration",
        "outcomes": best["result"]["outcomes"],
    }
    return retained, steps, recommendation


def project(
    source: Path, output: Path, domain: str, method: str, seed: int, cap: int, target: float
) -> dict:
    ledger = source / "observations.jsonl"
    raw = ledger.read_bytes().splitlines(keepends=True)
    entries = [json.loads(line) for line in raw]
    trajectory = json.loads((source / "trajectory.json").read_text())
    kept, steps, rec = cutoff(entries, trajectory, cap, target)
    output.mkdir(parents=True, exist_ok=False)
    (output / "observations.jsonl").write_bytes(b"".join(raw[: len(kept)]))
    write_json(output / "trajectory.json", steps)
    write_json(output / "frozen-recommendation.json", rec)
    # Freeze the prefix recommendation before recomputing its held-out score.
    data = load_data(domain)
    test = score(domain, data, evaluate(domain, data, rec["config"]), "test")
    seconds, model = steps[-1]["study_seconds"], steps[-1]["model_seconds"]
    provenance = {
        "kind": "retrospective_prefix",
        "source_directory": source.name,
        "source_ledger_sha256": digest(ledger),
        "source_trajectory_sha256": digest(source / "trajectory.json"),
        "source_observations": len(entries),
        "retained_observations": len(kept),
        "discarded_from_analysis": len(entries) - len(kept),
        "timing": "cumulative trajectory timer at retained final call",
        "controller_state": "not copied; this is a reporting projection, not a resumable study",
    }
    row = dict(
        domain=domain,
        method=method,
        seed=seed,
        cap=cap,
        target=target,
        target_reached=steps[-1]["target_reached"],
        stop_reason="target_reached" if steps[-1]["target_reached"] else "evaluation_cap",
        evaluations=len(kept),
        recommendation=rec,
        test=test,
        checkpoints=[],
        trajectory=steps,
        study_seconds=seconds,
        model_seconds=model,
        controller_and_optimizer_seconds=seconds - model,
        diagnostics=None,
        projection=provenance,
    )
    write_json(output / "projection.json", provenance)
    write_json(output / "application-result.json", row)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cap", type=int, default=2000)
    args = parser.parse_args()
    import torch

    torch.set_num_threads(1)
    source, output = args.source.resolve(), args.output.resolve()
    old = json.loads((source / "manifest.json").read_text())
    if not 0 < args.cap < old["cap"]:
        raise ValueError("Expected positive reduced cap")
    repo = Path(__file__).resolve().parents[1]
    inventory = json.loads((source / "ledger-inventory.json").read_text())
    actual = {str(p.relative_to(source)) for p in source.glob("*/observations.jsonl")}
    if actual != set(inventory):
        raise ValueError("Source inventory membership changed")
    for name, expected in inventory.items():
        path = source / name
        if (
            digest(path) != expected["sha256"]
            or len(path.read_text().splitlines()) != expected["observations"]
        ):
            raise ValueError(f"Source inventory mismatch: {name}")
    frozen = json.loads((repo / "examples/complex_models/results/targets.json").read_text())
    if old["targets"] != frozen:
        raise ValueError("Source manifest targets changed")
    for name, expected in frozen["source_sha256"].items():
        if digest(repo / name) != expected:
            raise ValueError(f"Frozen target source changed: {name}")
    inputs = hashes()
    inputs[str(Path(__file__).resolve().relative_to(repo))] = digest(Path(__file__))
    inputs["examples/complex_models/results/targets.json"] = digest(
        repo / "examples/complex_models/results/targets.json"
    )
    output.mkdir(parents=True, exist_ok=False)
    manifest = {
        **old,
        "cap": args.cap,
        "inputs": inputs,
        "amendment": "User-requested retrospective cutoff; targets and seeds unchanged",
        "projection_source": str(source.relative_to(repo)),
        "source_inventory_sha256": digest(source / "ledger-inventory.json"),
    }
    write_json(output / "manifest.json", manifest)
    for name, value in inputs.items():
        path = repo / name
        if digest(path) != value:
            raise ValueError(f"Source changed: {name}")
        dest = output / "source" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, dest)
    rows = []
    # Derive all available prefixes before spending time on new studies.
    pending = []
    for domain in DOMAINS:
        for seed in old["seeds"]:
            offset = seed % 3
            for method in METHODS[offset:] + METHODS[:offset]:
                name = f"{domain}-{method}-{seed}"
                target = old["targets"]["targets"][domain]
                if (source / name / "observations.jsonl").exists():
                    row = project(
                        source / name, output / name, domain, method, seed, args.cap, target
                    )
                    rows.append(row)
                    write_json(output / "results.json", {"runs": rows})
                    print(
                        f"Projected {name}: {row['evaluations']} calls, {row['stop_reason']}",
                        flush=True,
                    )
                else:
                    pending.append((domain, method, seed, name, target))
    for domain, method, seed, name, target in pending:
        rows.append(study(domain, method, seed, args.cap, output / name, inputs, target))
        write_json(output / "results.json", {"runs": rows})
    print(f"Completed {len(rows)} studies at cap {args.cap}", flush=True)


if __name__ == "__main__":
    main()
