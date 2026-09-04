"""Deterministic evaluator for the self-contained optimization example."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from autoengineering.optimization import EvaluationResult

_COMPONENTS = ("observations", "configurable_transform", "score")
_DATA_PATH = Path(__file__).with_name("input.csv")


def _observations() -> tuple[tuple[float, float], ...]:
    with _DATA_PATH.open(encoding="utf-8", newline="") as stream:
        rows = csv.DictReader(stream)
        return tuple((float(row["x"]), float(row["target"])) for row in rows)


def make_evaluator(system):
    """Return an action evaluator after checking the example system contract."""
    if tuple(system.component_names) != _COMPONENTS:
        raise ValueError(f"example system components must be {_COMPONENTS}")
    observations = _observations()

    def evaluate(action):
        architecture = action.config["architecture"]
        gain = float(action.config["gain"])
        stages = int(action.config["stages"])
        if gain * stages > 6.8:
            return EvaluationResult.model_failure(
                action.id,
                "controlled instability when gain times stages exceeds 6.8",
                cost=1.0,
                cost_unit="model_run",
            )

        curvature = float(action.config["curvature"]) if architecture == "nonlinear" else 0.0
        residuals = []
        for predictor, target in observations:
            prediction = gain * predictor + 0.1 * (stages - 2)
            if architecture == "nonlinear":
                prediction += 0.05 + curvature * predictor**2
            residuals.append(prediction - target)
        bias = sum(residuals) / len(residuals)
        rmse = math.sqrt(sum(value**2 for value in residuals) / len(residuals))
        return EvaluationResult.success(
            action.id,
            {"score": -rmse, "absolute_bias": abs(bias)},
            {},
            1.0,
            "model_run",
            message="deterministic optimization-chain evaluation",
        )

    return evaluate
