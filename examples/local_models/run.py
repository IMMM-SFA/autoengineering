"""Compare component replacement, random, Sobol and BO on small measured datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np


from examples.local_models.models import (
    BASELINES,
    DOMAINS,
    MODELS,
    ROOT,
    SWAPS,
    TARGETS,
    evaluate_system,
    load_data,
    metrics,
    search_space,
)
from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.execute.swap import swap_component
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
from autoengineering.system.component import Component
from autoengineering.system.graph import System
from autoengineering.validate.compare import validate_arrays


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def provenance() -> dict[str, str]:
    paths = list(ROOT.glob("*.py")) + list((ROOT / "data").glob("*.*"))
    paths += list(ROOT.glob("*-system.yaml"))
    paths += list((ROOT.parents[1] / "src" / "autoengineering").rglob("*.py"))
    paths += [ROOT / "PROTOCOL.md", ROOT.parents[1] / "pixi.lock"]
    paths += list((ROOT.parent / "leaf_river" / "data").glob("*.*"))
    paths += list((ROOT.parent / "leaf_river" / "models").glob("*.py"))
    return {
        str(p.relative_to(ROOT.parents[1])): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
    }


def study_run(
    domain: str, method: str, seed: int, evaluations: int, output: Path
) -> dict[str, object]:
    """Optimize validation error and reveal test outcomes after freezing the recommendation."""
    data = load_data(domain)
    development = data.loc[data.split != "test"].copy()
    spec = StudySpec(
        f"{domain}-{method}-{seed}",
        ObjectiveSpec("rmse", "minimize"),
        (),
        BudgetSpec(float(evaluations), "model_call", evaluations),
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
    timings = []

    def evaluate(action):
        started = time.perf_counter()
        try:
            outputs = MODELS[domain](development, dict(action.config))
            outcome = metrics(domain, development, outputs, "validation")["rmse"]
            result = EvaluationResult.success(action.id, {"rmse": outcome}, {}, 1.0, "model_call")
        except (ValueError, FloatingPointError) as error:
            result = EvaluationResult.model_failure(
                action.id, str(error), cost=1.0, cost_unit="model_call"
            )
        timings.append(time.perf_counter() - started)
        print(
            f"  {domain}/{method}/{seed}: {len(timings)}/{evaluations} {result.status.value}",
            flush=True,
        )
        return result

    started = time.perf_counter()
    controller = OptimizationStudy(
        spec,
        space,
        backend,
        ObservationLedger(output / "observations.jsonl"),
        evaluate,
        output,
        input_artifact_hashes=provenance(),
    )
    recommendation = controller.run()
    elapsed = time.perf_counter() - started
    # Persist the recommendation before evaluating any held-out response.
    write_json(output / "frozen-recommendation.json", recommendation.to_dict())
    test = None
    if recommendation.action_id is not None:
        test = metrics(domain, data, MODELS[domain](data, dict(recommendation.config)), "test")
    result = {
        "domain": domain,
        "method": method,
        "seed": seed,
        "recommendation": recommendation.to_dict(),
        "test": test,
        "model_seconds": sum(timings),
        "study_seconds": elapsed,
        "controller_and_optimizer_seconds": elapsed - sum(timings),
        "evaluations": len(timings),
        "diagnostics": backend.diagnostics(
            ObservationLedger(output / "observations.jsonl")
        ).to_dict(),
    }
    write_json(output / "application-result.json", result)
    return result


def workflow(domain: str, output: Path) -> dict[str, object]:
    """Run validate, rank, swap and re-evaluate using actual observations."""
    data = load_data(domain)
    development = data.loc[data.split != "test"].copy()
    system = System.from_yaml(ROOT / f"{domain}-system.yaml")
    owner = {"hydro": "pet", "solar": "temperature", "copper": "regression"}[domain]
    candidates = []
    for index, config in enumerate([BASELINES[domain], *SWAPS[domain]]):
        replacement = Component.from_dict(system.get_component(owner).to_dict())
        replacement.metadata["configuration"] = config
        candidate_system = swap_component(system, owner, replacement)
        started = time.perf_counter()
        outputs = evaluate_system(domain, development, candidate_system)
        seconds = time.perf_counter() - started
        mask = development.split == "validation"
        validations = validate_arrays(
            "system_output",
            development.loc[mask, TARGETS[domain]].to_numpy(),
            outputs["prediction"][mask],
            metrics=["rmse"],
            thresholds={
                "rmse": float(
                    np.sqrt(
                        np.mean(
                            (
                                development.loc[mask, TARGETS[domain]].to_numpy()
                                - development.loc[
                                    development.split == "train", TARGETS[domain]
                                ].mean()
                            )
                            ** 2
                        )
                    )
                )
            },
        )
        if domain == "solar":
            validations += validate_arrays(
                "temperature",
                development.loc[mask, "module_c"].to_numpy(),
                outputs["temperature"][mask],
                metrics=["rmse"],
                thresholds={
                    "rmse": float(
                        np.sqrt(
                            np.mean(
                                (development.loc[mask, "module_c"] - development.loc[mask, "air_c"])
                                ** 2
                            )
                        )
                    )
                },
            )
        candidates.append(
            {
                "index": index,
                "config": config,
                "validation": metrics(domain, development, outputs, "validation"),
                "model_seconds": seconds,
                "ranking": rank_opportunities(validations),
            }
        )
        candidate_system.to_yaml(output / f"{domain}-candidate-{index}.yaml")
    selected = min(candidates, key=lambda item: item["validation"]["rmse"])
    write_json(output / f"{domain}-frozen-swap.json", selected)
    for candidate in candidates:
        candidate["test"] = metrics(domain, data, MODELS[domain](data, candidate["config"]), "test")
    result = {"domain": domain, "candidates": candidates, "selected_index": selected["index"]}
    write_json(output / f"{domain}-workflow.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--domains", nargs="+", choices=DOMAINS, default=list(DOMAINS))
    parser.add_argument(
        "--methods", nargs="+", choices=["random", "sobol", "bo"], default=["random", "sobol", "bo"]
    )
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--evaluations", type=int, default=12)
    args = parser.parse_args()
    if args.evaluations < 1 or len(set(args.seeds)) != len(args.seeds):
        parser.error("Evaluations must be positive and seeds unique")
    # Single CPU thread makes tiny GP fits faster and bounds local compute.
    if "bo" in args.methods:
        import torch

        torch.set_num_threads(1)
    args.output.mkdir(parents=True, exist_ok=False)
    write_json(
        args.output / "manifest.json",
        {
            "inputs": provenance(),
            "python": sys.version,
            "platform": platform.platform(),
            "domains": args.domains,
            "methods": args.methods,
            "seeds": args.seeds,
            "evaluations": args.evaluations,
        },
    )
    results, workflows = [], []
    for domain in args.domains:
        workflows.append(workflow(domain, args.output))
        for seed in args.seeds:
            for method in args.methods:
                path = args.output / f"{domain}-{method}-{seed}"
                results.append(study_run(domain, method, seed, args.evaluations, path))
                write_json(args.output / "results.json", {"workflows": workflows, "runs": results})
    print(f"Completed {len(results)} studies: {args.output}", flush=True)


if __name__ == "__main__":
    main()
