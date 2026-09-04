"""Evaluate and replay the checked function-network example."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import time

import numpy as np

from autoengineering.optimization import (
    EvaluationAction,
    FunctionNetworkEvaluator,
    FunctionNetworkSpec,
    ObservationLedger,
    reconstruct_component_training_tables,
)
from autoengineering.research.runner import EvaluationContext, ParentArtifactReference
from autoengineering.system.graph import System


def _context(system, artifact_dir, *, parents=None):
    alternatives = {
        name: {"base": system.get_component(name)} for name in ("transform", "score")
    }
    return EvaluationContext(
        system=system,
        alternatives=alternatives,
        source_arrays={"source.driver": np.array([1.0, 2.0, 3.0])},
        observed={},
        outcome_functions={"placeholder": lambda _: 0.0},
        cost_unit="second",
        artifact_dir=artifact_dir,
        parent_artifacts={} if parents is None else parents,
    )


def run(output_dir: Path) -> dict[str, object]:
    """Run one system action, one component action, and durable reconstruction."""
    root = Path(__file__).resolve().parent
    system = System.from_yaml(root / "system.yaml")
    network = FunctionNetworkSpec.from_yaml(root / "network.yaml")
    network.validate(system)

    output_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    if os.name != "nt":
        output_dir.chmod(0o700)
    artifact_dir = output_dir / "artifacts"
    artifact_dir.mkdir(mode=0o700)
    if os.name != "nt":
        artifact_dir.chmod(0o700)
    ledger = ObservationLedger(output_dir / "observations.jsonl")

    system_action = EvaluationAction.system(
        "eval-000001",
        {
            "transform.choice": "base",
            "transform.gain": 2.0,
            "score.choice": "base",
            "score.offset": 1.0,
        },
        seed=20260904,
        suggested_by="checked-example",
    )
    system_result = FunctionNetworkEvaluator(
        network, _context(system, artifact_dir)
    ).evaluate(system_action)
    ledger.append(system_action, system_result)

    parent_id = next(iter(system_result.artifacts))
    parents = {
        parent_id: ParentArtifactReference(
            system_result.artifacts[parent_id], system_result.artifact_sha256[parent_id]
        )
    }
    component_action = EvaluationAction.component(
        "eval-000002",
        "score",
        {"score.choice": "base", "score.offset": -1.0},
        parent_artifact_ids=(parent_id,),
        seed=20260905,
        suggested_by="checked-example",
    )
    component_result = FunctionNetworkEvaluator(
        network, replace(_context(system, artifact_dir), parent_artifacts=parents)
    ).evaluate(component_action)
    ledger.append(component_action, component_result)

    tables = reconstruct_component_training_tables(network, system, ledger)
    scientific_tables = {
        component: [
            {
                "action_id": row.action_id,
                "component": row.component,
                "scope": row.scope.value,
                "inputs": dict(row.inputs),
                "outputs": dict(row.outputs),
                "artifact_ids": list(row.artifact_ids),
                "artifact_sha256": dict(row.artifact_sha256),
            }
            for row in rows
        ]
        for component, rows in tables.items()
    }
    result = {
        "execution_order": list(network.validate(system)),
        "system_outcomes": dict(system_result.outcomes),
        "component_outcomes": dict(component_result.outcomes),
        "training_tables": scientific_tables,
    }
    (output_dir / "training-tables.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    result = run(args.output)
    print(
        f"reconstructed {sum(len(rows) for rows in result['training_tables'].values())} "
        f"component rows in {time.perf_counter() - started:.3f} seconds"
    )


if __name__ == "__main__":
    main()
