"""Fixed-budget extension and validation-target stopping for the BMI examples."""

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
from examples.local_models.models import DOMAINS, MODELS, ROOT, load_data, metrics, search_space
from examples.local_models.run import provenance, study_run, write_json

PROTOCOL = ROOT / "CONVERGENCE_PROTOCOL.md"
TARGETS_FILE = ROOT / "convergence-targets.json"


def reached(outcomes: dict, target: float) -> bool:
    """Only a finite observed validation value can satisfy the inclusive target."""
    value = outcomes.get("rmse")
    return value is not None and math.isfinite(value) and value <= target


def target_run(
    domain: str,
    method: str,
    seed: int,
    cap: int,
    target: float,
    output: Path,
    hashes: dict[str, str],
) -> dict:
    if cap < 1 or not math.isfinite(target) or target < 0:
        raise ValueError("Require a positive cap and finite nonnegative target")
    data = load_data(domain)
    development = data.loc[data.split != "test"].copy()
    spec = StudySpec(
        f"{domain}-{method}-{seed}",
        ObjectiveSpec("rmse", "minimize"),
        (),
        BudgetSpec(float(cap), "model_call", cap),
        NoiseSpec(),
        "system",
        seed,
    )
    space = search_space(domain)
    if method == "bo":
        from autoengineering.optimization.system_backend import SystemBayesBackend

        backend = SystemBayesBackend(spec, space, min_initial=4, num_restarts=2, raw_samples=32)
    else:
        backend = {"random": RandomBackend, "sobol": SobolBackend}[method](spec, space)
    model_times = []

    def evaluate(action):
        started = time.perf_counter()
        try:
            outputs = MODELS[domain](development, dict(action.config))
            value = metrics(domain, development, outputs, "validation")["rmse"]
            result = EvaluationResult.success(action.id, {"rmse": value}, {}, 1.0, "model_call")
        except (ValueError, FloatingPointError) as error:
            result = EvaluationResult.model_failure(
                action.id, str(error), cost=1.0, cost_unit="model_call"
            )
        finally:
            model_times.append(time.perf_counter() - started)
        return result

    started = time.perf_counter()
    controller = OptimizationStudy(
        spec,
        space,
        backend,
        ObservationLedger(output / "observations.jsonl"),
        evaluate,
        output,
        input_artifact_hashes=hashes,
    )
    trajectory = []
    for _ in range(cap):
        result = controller.run_result(max_new_evaluations=1)
        recommendation = result.recommendation
        if result.new_evaluation_count == 0:
            break
        trajectory.append(
            {
                "evaluations": len(result.entries),
                "best_validation_rmse": recommendation.outcomes.get("rmse"),
                "study_seconds": time.perf_counter() - started,
                "model_seconds": sum(model_times),
                "target_reached": reached(recommendation.outcomes, target),
            }
        )
        write_json(output / "trajectory.json", trajectory)
        print(
            f"{domain}/{method}/{seed}: {len(model_times)}/{cap} "
            f"RMSE={recommendation.outcomes.get('rmse')} target={target:.6g}",
            flush=True,
        )
        if trajectory[-1]["target_reached"]:
            break
    elapsed = time.perf_counter() - started
    recommendation = controller.recommend()
    attained = reached(recommendation.outcomes, target)
    stop_reason = (
        "target_reached"
        if attained
        else (
            "evaluation_cap"
            if len(result.entries) == cap
            else result.stop_reason or "backend_stopped"
        )
    )
    # Application stopping is external to the durable controller. Its budget can remain open.
    write_json(output / "frozen-recommendation.json", recommendation.to_dict())
    test = None
    if recommendation.action_id is not None:
        test = metrics(domain, data, MODELS[domain](data, dict(recommendation.config)), "test")
    row = {
        "domain": domain,
        "method": method,
        "seed": seed,
        "target": target,
        "target_reached": attained,
        "stop_reason": stop_reason,
        "cap": cap,
        "evaluations": len(result.entries),
        "trajectory": trajectory,
        "recommendation": recommendation.to_dict(),
        "test": test,
        "model_seconds": sum(model_times),
        "study_seconds": elapsed,
        "controller_and_optimizer_seconds": elapsed - sum(model_times),
    }
    write_json(output / "application-result.json", row)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=["fixed", "target"], required=True)
    args = parser.parse_args()
    import torch
    import pvlib  # noqa: F401 - keep solar library startup outside measured studies

    torch.set_num_threads(1)
    targets = json.loads(TARGETS_FILE.read_text())
    for name, digest in targets["source_ledger_sha256"].items():
        if hashlib.sha256((ROOT.parents[1] / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Historical target source changed: {name}")
    hashes = provenance()
    for path in [PROTOCOL, TARGETS_FILE]:
        hashes[str(path.relative_to(ROOT.parents[1]))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    seeds = [0, 1, 2] if args.mode == "fixed" else [3, 4, 5, 6, 7]
    cap = 24 if args.mode == "fixed" else 60
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(
        args.output / "manifest.json",
        {
            "mode": args.mode,
            "inputs": hashes,
            "seeds": seeds,
            "evaluations": cap,
            "domains": list(DOMAINS),
            "methods": ["random", "sobol", "bo"],
            "targets": targets,
            "python": sys.version,
            "platform": platform.platform(),
        },
    )
    rows = []
    for domain in DOMAINS:
        for seed in seeds:
            # Rotate execution order to reduce systematic timing-order effects.
            methods = ["random", "sobol", "bo"]
            offset = seed % 3
            for method in methods[offset:] + methods[:offset]:
                output = args.output / f"{domain}-{method}-{seed}"
                if args.mode == "fixed":
                    row = study_run(domain, method, seed, cap, output)
                else:
                    row = target_run(
                        domain, method, seed, cap, targets["targets"][domain], output, hashes
                    )
                rows.append(row)
                write_json(args.output / "results.json", {"runs": rows})
    print(f"Completed {len(rows)} studies", flush=True)


if __name__ == "__main__":
    main()
