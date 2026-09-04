"""Frozen synthetic problems for the preregistered Release A benchmark."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from autoengineering.optimization import (
    BudgetSpec,
    CategoricalParameter,
    ConstraintSpec,
    ContinuousParameter,
    EvaluationAction,
    EvaluationResult,
    EvaluationStatus,
    IntegerParameter,
    NoiseSpec,
    ObjectiveSpec,
    SearchSpace,
    StudySpec,
)

EVALUATIONS_PER_RUN = 10
BENCHMARK_SEEDS = tuple(range(30))


@dataclass(frozen=True)
class BenchmarkProblem:
    """One immutable benchmark problem with a known reference objective."""

    name: str
    ordinal: int
    space: SearchSpace
    objective: ObjectiveSpec
    constraints: tuple[ConstraintSpec, ...]
    noise: NoiseSpec
    cost_budget: float
    reference_objective: float
    reference_config: dict[str, str | int | float | bool]

    def study(self, benchmark_seed: int) -> StudySpec:
        """Build the common study contract with the preregistered seed mapping."""
        if benchmark_seed not in BENCHMARK_SEEDS:
            raise ValueError("benchmark seed must be an integer from 0 through 29")
        return StudySpec(
            name=f"release-a-{self.name}",
            objective=self.objective,
            constraints=self.constraints,
            budget=BudgetSpec(
                self.cost_budget,
                "evaluation_cost",
                max_evaluations=EVALUATIONS_PER_RUN,
                initial_cost_estimate=1.0,
            ),
            noise=self.noise,
            backend="system",
            seed=10_000 * self.ordinal + benchmark_seed,
        )

    def evaluate(
        self,
        action: EvaluationAction,
        *,
        benchmark_seed: int,
        evaluation_index: int,
    ) -> EvaluationResult:
        """Evaluate one validated configuration with deterministic seed mapping."""
        self.space.encode(action.config)
        study_seed = self.study(benchmark_seed).seed
        if self.name == "smooth_continuous":
            x, y = float(action.config["x"]), float(action.config["y"])
            score = 1.0 - ((x - 0.25) ** 2 + (y - 0.75) ** 2) / 1.125
            return _success(action, {"score": score}, 1.0)
        if self.name == "constrained_continuous":
            x, y = float(action.config["x"]), float(action.config["y"])
            score = 1.0 - (x - 0.7) ** 2 - (y - 0.3) ** 2
            margin = 0.10 - (x - 0.5) ** 2 - (y - 0.5) ** 2
            return _success(action, {"score": score, "feasibility_margin": margin}, 1.0)
        if self.name == "mixed_space":
            rate = float(action.config["rate"])
            depth = int(action.config["depth"])
            if action.config["algorithm"] == "robust":
                score = 1.0 - (rate - 0.65) ** 2 - 0.04 * (depth - 4) ** 2
            else:
                score = 0.92 - (rate - 0.35) ** 2 - 0.04 * (depth - 2) ** 2
            return _success(action, {"score": score}, 1.0)
        if self.name == "conditional_space":
            if action.config["family"] == "linear":
                score = 0.9 - (float(action.config["slope"]) - 0.6) ** 2
            else:
                score = (
                    1.0
                    - (float(action.config["curvature"]) - 0.7) ** 2
                    - (float(action.config["shift"]) - 0.3) ** 2
                )
            return _success(action, {"score": score}, 1.0)
        if self.name == "noisy_chain":
            return self._evaluate_noisy_chain(action, study_seed, evaluation_index)
        raise AssertionError(f"unknown frozen benchmark problem: {self.name}")

    def preview_cost(self, config: dict[str, Any]) -> float:
        """Return evaluator cost before an evaluation starts."""
        self.space.encode(config)
        if self.name != "noisy_chain":
            return 1.0
        stages = int(config["stages"])
        if config["architecture"] == "reliable":
            return 1.0 + 0.15 * (stages - 1)
        return 1.4 + 0.2 * (stages - 1) + 0.3 * float(config["boost"])

    def is_feasible(self, result: EvaluationResult) -> bool:
        """Return whether a successful result satisfies every scientific constraint."""
        if result.status is not EvaluationStatus.SUCCESS:
            return False
        return all(
            result.outcomes[constraint.outcome] >= constraint.threshold
            if constraint.operator == ">="
            else result.outcomes[constraint.outcome] <= constraint.threshold
            for constraint in self.constraints
        )

    def constraint_violation(self, result: EvaluationResult) -> bool:
        """Return whether a successful result violates any declared threshold."""
        return result.status is EvaluationStatus.SUCCESS and not self.is_feasible(result)

    def normalized_regret(self, best_feasible_objective: float | None) -> float:
        """Compute the frozen scale-one feasible regret."""
        if best_feasible_objective is None:
            return 1.0
        return min(1.0, max(0.0, self.reference_objective - best_feasible_objective))

    def _evaluate_noisy_chain(
        self,
        action: EvaluationAction,
        study_seed: int,
        evaluation_index: int,
    ) -> EvaluationResult:
        config = action.config
        control = float(config["control"])
        stages = int(config["stages"])
        cost = self.preview_cost(dict(config))
        if config["architecture"] == "turbo" and control > 0.9 and float(config["boost"]) > 0.75:
            return EvaluationResult.model_failure(
                action.id,
                "declared turbo instability",
                cost=cost,
                cost_unit="evaluation_cost",
            )
        if config["architecture"] == "reliable":
            mean = 0.94 - (control - 0.6) ** 2 - 0.03 * (stages - 2) ** 2
            stability = 0.30 - abs(control - 0.6) - 0.03 * abs(stages - 2)
        else:
            boost = float(config["boost"])
            mean = (
                1.03 - (control - 0.75) ** 2 - 0.03 * (stages - 3) ** 2 - 0.2 * (boost - 0.4) ** 2
            )
            stability = 0.22 - abs(control - 0.7) - 0.08 * abs(boost - 0.4) - 0.03 * abs(stages - 3)
        generator = np.random.default_rng(np.random.SeedSequence([study_seed, evaluation_index, 5]))
        score = mean + float(generator.normal(0.0, 0.02))
        return _success(
            action,
            {"score": score, "stability_margin": stability},
            cost,
            standard_errors={"score": 0.02, "stability_margin": 1e-6},
        )


def _success(
    action: EvaluationAction,
    outcomes: dict[str, float],
    cost: float,
    *,
    standard_errors: dict[str, float] | None = None,
) -> EvaluationResult:
    return EvaluationResult.success(
        action.id,
        outcomes,
        {} if standard_errors is None else standard_errors,
        cost,
        "evaluation_cost",
    )


def benchmark_problems() -> tuple[BenchmarkProblem, ...]:
    """Return the five problems in preregistered ordinal order."""
    return (
        BenchmarkProblem(
            "smooth_continuous",
            1,
            SearchSpace(
                (
                    ContinuousParameter("x", 0.0, 1.0),
                    ContinuousParameter("y", 0.0, 1.0),
                )
            ),
            ObjectiveSpec("score", "maximize"),
            (),
            NoiseSpec(),
            10.0,
            1.0,
            {"x": 0.25, "y": 0.75},
        ),
        BenchmarkProblem(
            "constrained_continuous",
            2,
            SearchSpace(
                (
                    ContinuousParameter("x", 0.0, 1.0),
                    ContinuousParameter("y", 0.0, 1.0),
                )
            ),
            ObjectiveSpec("score", "maximize"),
            (ConstraintSpec("feasibility_margin", ">=", 0.0),),
            NoiseSpec(),
            10.0,
            1.0,
            {"x": 0.7, "y": 0.3},
        ),
        BenchmarkProblem(
            "mixed_space",
            3,
            SearchSpace(
                (
                    CategoricalParameter("algorithm", ("fast", "robust")),
                    IntegerParameter("depth", 1, 5),
                    ContinuousParameter("rate", 0.0, 1.0),
                )
            ),
            ObjectiveSpec("score", "maximize"),
            (),
            NoiseSpec(),
            10.0,
            1.0,
            {"algorithm": "robust", "depth": 4, "rate": 0.65},
        ),
        BenchmarkProblem(
            "conditional_space",
            4,
            SearchSpace(
                (
                    CategoricalParameter("family", ("linear", "quadratic")),
                    ContinuousParameter("slope", 0.0, 1.0, active_when={"family": ("linear",)}),
                    ContinuousParameter(
                        "curvature", 0.0, 1.0, active_when={"family": ("quadratic",)}
                    ),
                    ContinuousParameter("shift", 0.0, 1.0, active_when={"family": ("quadratic",)}),
                )
            ),
            ObjectiveSpec("score", "maximize"),
            (),
            NoiseSpec(),
            10.0,
            1.0,
            {"family": "quadratic", "curvature": 0.7, "shift": 0.3},
        ),
        BenchmarkProblem(
            "noisy_chain",
            5,
            SearchSpace(
                (
                    CategoricalParameter("architecture", ("reliable", "turbo")),
                    ContinuousParameter("control", 0.0, 1.0),
                    IntegerParameter("stages", 1, 4),
                    ContinuousParameter(
                        "boost", 0.0, 1.0, active_when={"architecture": ("turbo",)}
                    ),
                )
            ),
            ObjectiveSpec("score", "maximize"),
            (ConstraintSpec("stability_margin", ">=", 0.0),),
            NoiseSpec("known", 1e-6),
            23.0,
            1.03,
            {"architecture": "turbo", "control": 0.75, "stages": 3, "boost": 0.4},
        ),
    )


def problem_by_name(name: str) -> BenchmarkProblem:
    """Return one frozen problem by name."""
    for problem in benchmark_problems():
        if problem.name == name:
            return problem
    raise KeyError(f"unknown Release A benchmark problem: {name}")
