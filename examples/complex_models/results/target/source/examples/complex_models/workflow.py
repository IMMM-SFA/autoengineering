"""Validate and swap declared BMI components in the larger model chains."""

from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np

from autoengineering.analyze.metrics import rank_opportunities
from autoengineering.execute.swap import swap_component
from autoengineering.system.component import Component
from autoengineering.system.graph import System
from autoengineering.validate.compare import validate_arrays
from examples.complex_models.models import (
    BASELINES,
    BASE_DOMAIN,
    ROOT,
    evaluate,
    load_data,
    original,
    score,
)
from examples.local_models.run import write_json


def workflow(output: Path) -> list:
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for domain, owner, cls in [
        ("hymod", "routing", "SingleFastRoutingBmi"),
        ("solar_diode", "diode", "EmpiricalDcBmi"),
    ]:
        data = load_data(domain)
        dev = data.loc[data.split != "test"]
        system = System.from_yaml(ROOT / f"{domain}-system.yaml")
        replacement = Component.from_dict(system.get_component(owner).to_dict())
        replacement.metadata["bmi_class"] = f"examples.complex_models.models:{cls}"
        replacement.model_type = cls
        swapped = swap_component(system, owner, replacement)
        candidates = []
        for label, graph in [("complex", system), ("simpler_swap", swapped)]:
            outputs = evaluate(domain, dev, BASELINES[domain], graph)
            validation = score(domain, dev, outputs, "validation")
            target = original.TARGETS[BASE_DOMAIN[domain]]
            mask = dev.split == "validation"
            reference = float(
                np.sqrt(
                    np.mean(
                        (dev.loc[mask, target] - dev.loc[dev.split == "train", target].mean()) ** 2
                    )
                )
            )
            checks = validate_arrays(
                "system_output",
                dev.loc[mask, target].to_numpy(),
                outputs["prediction"][mask],
                metrics=["rmse"],
                thresholds={"rmse": reference},
            )
            graph.to_yaml(output / f"{domain}-{label}.yaml")
            candidates.append(
                {"label": label, "validation": validation, "ranking": rank_opportunities(checks)}
            )
        selected = min(candidates, key=lambda c: c["validation"]["rmse"])["label"]
        write_json(
            output / f"{domain}-frozen-selection.json",
            {"selected": selected, "config": BASELINES[domain]},
        )
        for candidate, graph in zip(candidates, [system, swapped], strict=True):
            candidate["test"] = score(
                domain, data, evaluate(domain, data, BASELINES[domain], graph), "test"
            )
        rows.append({"domain": domain, "selected": selected, "candidates": candidates})
    write_json(output / "results.json", rows)
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    workflow(parser.parse_args().output)
