"""Run paired 12/24/48/96-call checkpoints and a separate configurable target experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time

from autoengineering.optimization import (
    BudgetSpec,
    EvaluationResult,
    NoiseSpec,
    ObjectiveSpec,
    ObservationLedger,
    OptimizationStudy,
    RandomBackend,
    SobolBackend,
    StudySpec,
)
from examples.complex_models.models import DOMAINS, ROOT, evaluate, load_data, score, search_space
from examples.local_models.convergence import reached
from examples.local_models.run import provenance, write_json

CHECKPOINTS = (12, 24, 48, 96)
METHODS = ("random", "sobol", "bo")
TARGET_CAP = 10000


def hashes() -> dict:
    result = provenance()
    for p in sorted(ROOT.glob("*")):
        if p.suffix in {".py", ".md", ".json", ".yaml"}:
            result[str(p.relative_to(ROOT.parents[1]))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def study(
    domain: str,
    method: str,
    seed: int,
    cap: int,
    output: Path,
    inputs: dict,
    target: float | None = None,
    checkpoints: tuple = CHECKPOINTS,
) -> dict:
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 1:
        raise ValueError("cap must be a positive integer")
    if target is not None and (not math.isfinite(target) or target < 0):
        raise ValueError("target must be finite and nonnegative")
    data = load_data(domain)
    development = data.loc[data.split != "test"].copy()
    space = search_space(domain)
    spec = StudySpec(
        f"{domain}-{method}-{seed}",
        ObjectiveSpec("rmse", "minimize"),
        (),
        BudgetSpec(float(cap), "model_call", cap),
        NoiseSpec(),
        "system",
        seed,
    )
    if method == "bo":
        from autoengineering.optimization.system_backend import SystemBayesBackend

        backend = SystemBayesBackend(
            spec,
            space,
            min_initial=8 if domain in ["hymod", "solar_diode"] else 4,
            num_restarts=2,
            raw_samples=32,
        )
    else:
        backend = {"random": RandomBackend, "sobol": SobolBackend}[method](spec, space)
    model_times = []

    def evaluator(action):
        started = time.perf_counter()
        try:
            value = score(
                domain,
                development,
                evaluate(domain, development, dict(action.config)),
                "validation",
            )["rmse"]
            return EvaluationResult.success(action.id, {"rmse": value}, {}, 1.0, "model_call")
        except (ValueError, FloatingPointError) as error:
            return EvaluationResult.model_failure(
                action.id, str(error), cost=1.0, cost_unit="model_call"
            )
        finally:
            model_times.append(time.perf_counter() - started)

    started = time.perf_counter()
    controller = OptimizationStudy(
        spec,
        space,
        backend,
        ObservationLedger(output / "observations.jsonl"),
        evaluator,
        output,
        input_artifact_hashes=inputs,
    )
    trajectory = []
    snapshots = []
    for _ in range(cap):
        step = controller.run_result(max_new_evaluations=1)
        if not step.new_evaluation_count:
            break
        n = len(step.entries)
        rec = step.recommendation
        hit = target is not None and reached(rec.outcomes, target)
        trajectory.append(
            {
                "evaluations": n,
                "best_validation_rmse": rec.outcomes.get("rmse"),
                "target_reached": hit,
                "study_seconds": time.perf_counter() - started,
                "model_seconds": sum(model_times),
            }
        )
        write_json(output / "trajectory.json", trajectory)
        if target is None and n in checkpoints:
            snapshot = {"evaluations": n, "recommendation": rec.to_dict()}
            write_json(output / f"frozen-{n}.json", snapshot)
            snapshots.append(snapshot)
        print(
            f"{domain}/{method}/{seed}: {n}/{cap} RMSE={rec.outcomes.get('rmse')} target={target}",
            flush=True,
        )
        if hit:
            break
    elapsed = time.perf_counter() - started
    rec = controller.recommend()
    hit = target is not None and reached(rec.outcomes, target)
    status = (
        "target_reached"
        if hit
        else (
            "evaluation_cap" if len(step.entries) == cap else step.stop_reason or "backend_stopped"
        )
    )
    write_json(output / "frozen-recommendation.json", rec.to_dict())
    # Reveal all test results only after every optimization call has finished.
    for snapshot in snapshots:
        recommendation = snapshot["recommendation"]
        snapshot["test"] = (
            None
            if recommendation["action_id"] is None
            else score(domain, data, evaluate(domain, data, recommendation["config"]), "test")
        )
    test = (
        None
        if rec.action_id is None
        else score(domain, data, evaluate(domain, data, dict(rec.config)), "test")
    )
    row = {
        "domain": domain,
        "method": method,
        "seed": seed,
        "cap": cap,
        "target": target,
        "target_reached": hit,
        "stop_reason": status,
        "evaluations": len(step.entries),
        "recommendation": rec.to_dict(),
        "test": test,
        "checkpoints": snapshots,
        "trajectory": trajectory,
        "study_seconds": elapsed,
        "model_seconds": sum(model_times),
        "controller_and_optimizer_seconds": elapsed - sum(model_times),
        "diagnostics": backend.diagnostics(
            ObservationLedger(output / "observations.jsonl")
        ).to_dict(),
    }
    write_json(output / "application-result.json", row)
    return row


def freeze_targets(fixed: Path, output: Path) -> None:
    fixed = fixed.resolve()
    output = output.resolve()
    if output.exists():
        raise ValueError("Target file already exists")
    rows = json.loads((fixed / "results.json").read_text())["runs"]
    expected = {(d, m, s) for d in DOMAINS for m in METHODS for s in [0, 1, 2]}
    if (
        len(rows) != len(expected)
        or {(r["domain"], r["method"], r["seed"]) for r in rows} != expected
    ):
        raise ValueError("Incomplete fixed comparison")
    manifest = json.loads((fixed / "manifest.json").read_text())
    for name, digest in manifest["inputs"].items():
        if hashlib.sha256((ROOT.parents[1] / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Fixed source changed: {name}")
    for row in rows:
        directory = fixed / f"{row['domain']}-{row['method']}-{row['seed']}"
        ledger = (directory / "observations.jsonl").read_text().splitlines()
        if (
            row["evaluations"] != 96
            or len(ledger) != 96
            or row["stop_reason"] != "evaluation_cap"
            or [c["evaluations"] for c in row["checkpoints"]] != list(CHECKPOINTS)
            or json.loads((directory / "application-result.json").read_text()) != row
        ):
            raise ValueError(f"Incomplete fixed study: {directory.name}")
    old = ROOT.parent / "local_models/convergence-targets.json"
    targets = json.loads(old.read_text())["targets"]
    sources = {str(old.relative_to(ROOT.parents[1])): hashlib.sha256(old.read_bytes()).hexdigest()}
    for domain in ["hymod", "solar_diode"]:
        values = []
        for path in [
            fixed / f"{domain}-{method}-{seed}" / "observations.jsonl"
            for method in METHODS
            for seed in [0, 1, 2]
        ]:
            sources[str(path.relative_to(ROOT.parents[1]))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            values.extend(
                json.loads(line)["result"]["outcomes"]["rmse"]
                for line in path.read_text().splitlines()
                if json.loads(line)["result"]["status"] == "success"
            )
        targets[domain] = 1.05 * min(values)
    write_json(output, {"targets": targets, "source_sha256": sources, "new_model_factor": 1.05})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fixed", "freeze-targets", "target"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--fixed", type=Path)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--target-cap", type=int, default=TARGET_CAP)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if args.fixed is not None:
        args.fixed = args.fixed.resolve()
    if args.targets is not None:
        args.targets = args.targets.resolve()
    if args.mode == "freeze-targets":
        if args.fixed is None:
            parser.error("--fixed is required")
        freeze_targets(args.fixed, args.output)
        return
    import torch
    import pvlib  # noqa: F401

    torch.set_num_threads(1)
    inputs = hashes()
    targets = None
    if args.mode == "target":
        if args.targets is None:
            parser.error("--targets is required")
        targets = json.loads(args.targets.read_text())
        for name, digest in targets["source_sha256"].items():
            if hashlib.sha256((ROOT.parents[1] / name).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Target source changed: {name}")
        inputs[str(args.targets.relative_to(ROOT.parents[1]))] = hashlib.sha256(
            args.targets.read_bytes()
        ).hexdigest()
    cap = 96 if args.mode == "fixed" else args.target_cap
    if cap < 1:
        parser.error("--target-cap must be positive")
    seeds = [0, 1, 2] if args.mode == "fixed" else [3, 4, 5, 6, 7]
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(
        args.output / "manifest.json",
        {
            "mode": args.mode,
            "inputs": inputs,
            "domains": DOMAINS,
            "methods": METHODS,
            "seeds": seeds,
            "cap": cap,
            "checkpoints": CHECKPOINTS if targets is None else [],
            "targets": targets,
            "platform": platform.platform(),
            "python": sys.version,
        },
    )
    rows = []
    for domain in DOMAINS:
        for seed in seeds:
            offset = seed % 3
            for method in METHODS[offset:] + METHODS[:offset]:
                path = args.output / f"{domain}-{method}-{seed}"
                rows.append(
                    study(
                        domain,
                        method,
                        seed,
                        cap,
                        path,
                        inputs,
                        None if targets is None else targets["targets"][domain],
                    )
                )
                write_json(args.output / "results.json", {"runs": rows})
    print(f"Completed {len(rows)} studies", flush=True)


if __name__ == "__main__":
    main()
