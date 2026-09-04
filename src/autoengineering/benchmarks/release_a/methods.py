"""Lazy method adapters for the Release A benchmark."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
import tempfile
from typing import Protocol

import numpy as np
from scipy.stats import qmc

from autoengineering.optimization import (
    CategoricalParameter,
    ContinuousParameter,
    EvaluationAction,
    EvaluationResult,
    EvaluationStatus,
    IntegerParameter,
    RandomBackend,
    SobolBackend,
)

from .problems import BenchmarkProblem

METHOD_NAMES = ("fixed", "random", "sobol", "smac", "botorch")
NATIVE_METHODS = frozenset(("fixed", "random", "sobol", "botorch"))
WARM_START_COUNT = 5


class MemoryLedger:
    """Append-only in-memory ledger implementing the optimizer reader protocol."""

    def __init__(self) -> None:
        self._entries: list[tuple[EvaluationAction, EvaluationResult]] = []

    def append(self, action: EvaluationAction, result: EvaluationResult) -> None:
        if action.id != result.action_id:
            raise ValueError("benchmark action and result IDs must match")
        if any(existing.id == action.id for existing, _ in self._entries):
            raise ValueError(f"duplicate benchmark action ID: {action.id}")
        self._entries.append((action, result))

    def entries(self) -> tuple[tuple[EvaluationAction, EvaluationResult], ...]:
        return tuple(self._entries)

    def snapshot(self):
        return self.entries(), b""

    def scientific_training_entries(self):
        statuses = {EvaluationStatus.SUCCESS, EvaluationStatus.SCIENTIFIC_INFEASIBLE}
        return tuple(entry for entry in self._entries if entry[1].status in statuses)

    def constraint_training_entries(self):
        return self.scientific_training_entries()

    def objective_training_entries(self):
        return tuple(
            entry for entry in self._entries if entry[1].status is EvaluationStatus.SUCCESS
        )


@dataclass(frozen=True)
class Suggestion:
    """One proposed action and the backend diagnostics caused by that proposal."""

    action: EvaluationAction
    fallback_events: tuple[str, ...] = ()


class MethodAdapter(Protocol):
    """Sequential method surface shared by native and external optimizers."""

    name: str
    replayable: bool

    def suggest(self, ledger: MemoryLedger) -> Suggestion: ...

    def observe(
        self,
        action: EvaluationAction,
        result: EvaluationResult,
        problem: BenchmarkProblem,
    ) -> None: ...

    def close(self) -> None: ...


class NativeAdapter:
    """Adapter for an autoengineering optimizer backend."""

    replayable = True

    def __init__(self, name: str, backend) -> None:
        self.name = name
        self.backend = backend

    def suggest(self, ledger: MemoryLedger) -> Suggestion:
        action = self.backend.suggest(ledger, n=1)[0]
        diagnostics = self.backend.diagnostics(ledger)
        if self.name == "fixed":
            action = replace(action, suggested_by="fixed")
        return Suggestion(action, diagnostics.fallback_reasons)

    def observe(
        self,
        action: EvaluationAction,
        result: EvaluationResult,
        problem: BenchmarkProblem,
    ) -> None:
        return None

    def close(self) -> None:
        return None


class FixedOrderBackend(SobolBackend):
    """Use one deterministic, unscrambled Sobol order for every benchmark seed."""

    name = "fixed"

    def suggest(self, ledger: MemoryLedger, n: int = 1) -> tuple[EvaluationAction, ...]:
        self._validate_n(n)
        next_index, _ = self._next_index_and_observed(ledger)
        observed = {self.space.encode(action.config) for action, _ in ledger.entries()}
        selected: list[dict[str, object]] = []
        selected_keys = set(observed)
        sampler = qmc.Sobol(d=self.space.encoded_dimension, scramble=False)
        for point in sampler.random_base2(m=12):
            config = self._decode_projected(point)
            key = self.space.encode(config)
            if key in selected_keys:
                continue
            selected_keys.add(key)
            selected.append(config)
            if len(selected) == n:
                break
        if len(selected) < n:
            raise RuntimeError("fixed Sobol scan could not supply a new configuration")
        return tuple(
            self._action(next_index + offset, config) for offset, config in enumerate(selected)
        )


class SmacAdapter:
    """Benchmark-only SMAC ask-and-tell adapter with a shared Sobol prefix."""

    name = "smac"
    replayable = False

    def __init__(self, problem: BenchmarkProblem, benchmark_seed: int) -> None:
        try:
            from smac import HyperparameterOptimizationFacade, Scenario
            from smac.runhistory.dataclasses import TrialInfo, TrialValue
        except ImportError as error:
            raise ImportError(
                "Release A SMAC comparison requires the Bayesian Pixi environment"
            ) from error
        self.problem = problem
        self.study = problem.study(benchmark_seed)
        self._warm_backend = SobolBackend(self.study, problem.space)
        self._facade_type = HyperparameterOptimizationFacade
        self._scenario_type = Scenario
        self._trial_info_type = TrialInfo
        self._trial_value_type = TrialValue
        self._configuration_space = _configspace(problem, self.study.seed)
        self._temporary = tempfile.TemporaryDirectory(prefix="autoengineering-smac-")
        self._facade = None
        self._pending = None
        self._observed: list[tuple[EvaluationAction, EvaluationResult]] = []

    def suggest(self, ledger: MemoryLedger) -> Suggestion:
        index = len(ledger.entries())
        if index < WARM_START_COUNT:
            action = self._warm_backend.suggest(ledger, n=1)[0]
            return Suggestion(replace(action, suggested_by="smac:warm_start"))
        if self._facade is None:
            self._initialize_facade()
        info = self._facade.ask()
        config = _plain_config(dict(info.config), self.problem)
        self.problem.space.encode(config)
        self._pending = info
        return Suggestion(
            EvaluationAction.system(
                f"eval-{index:06d}",
                config,
                seed=self.study.seed + index,
                suggested_by="smac",
            )
        )

    def observe(
        self,
        action: EvaluationAction,
        result: EvaluationResult,
        problem: BenchmarkProblem,
    ) -> None:
        self._observed.append((action, result))
        if self._facade is None:
            return
        if self._pending is None:
            raise RuntimeError("SMAC has no pending trial for the observed result")
        self._facade.tell(
            self._pending,
            self._trial_value_type(cost=_smac_cost(problem, result)),
            save=False,
        )
        self._pending = None

    def close(self) -> None:
        self._temporary.cleanup()

    def _initialize_facade(self) -> None:
        scenario = self._scenario_type(
            self._configuration_space,
            name=f"release-a-{self.problem.name}-{self.study.seed}",
            output_directory=Path(self._temporary.name),
            deterministic=True,
            n_trials=10,
            seed=self.study.seed,
            n_workers=1,
        )
        initial_design = self._facade_type.get_initial_design(scenario, n_configs=0)
        intensifier = self._facade_type.get_intensifier(scenario, max_config_calls=1)
        self._facade = self._facade_type(
            scenario,
            lambda config, seed=0: 0.0,
            initial_design=initial_design,
            intensifier=intensifier,
            logging_level=False,
            overwrite=True,
        )
        for action, result in self._observed:
            configuration = _configuration(self._configuration_space, dict(action.config))
            info = self._trial_info_type(config=configuration, seed=self.study.seed)
            self._facade.tell(
                info,
                self._trial_value_type(cost=_smac_cost(self.problem, result)),
                save=False,
            )


def build_method(
    name: str,
    problem: BenchmarkProblem,
    benchmark_seed: int,
) -> MethodAdapter:
    """Construct one selected method without eager optional imports."""
    if name not in METHOD_NAMES:
        raise ValueError(f"unknown Release A benchmark method: {name}")
    study = problem.study(benchmark_seed)
    if name == "fixed":
        return NativeAdapter(name, FixedOrderBackend(study, problem.space))
    if name == "random":
        return NativeAdapter(name, RandomBackend(study, problem.space))
    if name == "sobol":
        return NativeAdapter(name, SobolBackend(study, problem.space))
    if name == "botorch":
        try:
            from autoengineering.optimization.system_backend import SystemBayesBackend
        except ImportError as error:
            raise ImportError(
                "Release A BoTorch comparison requires the Bayesian Pixi environment"
            ) from error
        backend = SystemBayesBackend(
            study,
            problem.space,
            min_initial=5,
            num_restarts=2,
            raw_samples=16,
            max_categorical_assignments=16,
            candidate_retry_limit=2,
        )
        return NativeAdapter(name, backend)
    return SmacAdapter(problem, benchmark_seed)


def _smac_cost(problem: BenchmarkProblem, result: EvaluationResult) -> float:
    if result.status is not EvaluationStatus.SUCCESS:
        return 10.0
    if not problem.is_feasible(result):
        violation = 0.0
        for constraint in problem.constraints:
            observed = result.outcomes[constraint.outcome]
            violation += (
                max(0.0, constraint.threshold - observed)
                if constraint.operator == ">="
                else max(0.0, observed - constraint.threshold)
            )
        return 5.0 + violation
    return problem.reference_objective - result.outcomes[problem.objective.outcome]


def _configspace(problem: BenchmarkProblem, seed: int):
    from ConfigSpace import (
        AndConjunction,
        CategoricalHyperparameter,
        ConfigurationSpace,
        InCondition,
        UniformFloatHyperparameter,
        UniformIntegerHyperparameter,
    )

    space = ConfigurationSpace(seed=seed)
    hyperparameters = {}
    for parameter in problem.space.parameters:
        if isinstance(parameter, CategoricalParameter):
            converted = CategoricalHyperparameter(parameter.name, list(parameter.categories))
        elif isinstance(parameter, IntegerParameter):
            converted = UniformIntegerHyperparameter(
                parameter.name,
                lower=parameter.lower,
                upper=parameter.upper,
                log=parameter.scale == "log",
            )
        elif isinstance(parameter, ContinuousParameter):
            converted = UniformFloatHyperparameter(
                parameter.name,
                lower=parameter.lower,
                upper=parameter.upper,
                log=parameter.scale == "log",
            )
        else:  # pragma: no cover - SearchSpace has a closed public parameter union
            raise TypeError(f"unsupported benchmark parameter: {parameter!r}")
        hyperparameters[parameter.name] = converted
    space.add(list(hyperparameters.values()))
    for parameter in problem.space.parameters:
        if not getattr(parameter, "active_when", None):
            continue
        conditions = [
            InCondition(
                hyperparameters[parameter.name],
                hyperparameters[parent],
                list(values),
            )
            for parent, values in parameter.active_when.items()
        ]
        space.add(conditions[0] if len(conditions) == 1 else AndConjunction(*conditions))
    return space


def _configuration(space, config: dict[str, object]):
    from ConfigSpace import Configuration

    return Configuration(space, values=config)


def _plain_config(config: dict[str, object], problem: BenchmarkProblem) -> dict[str, object]:
    plain: dict[str, object] = {}
    by_name = {parameter.name: parameter for parameter in problem.space.parameters}
    for name, value in config.items():
        parameter = by_name[name]
        if isinstance(parameter, IntegerParameter):
            plain[name] = int(value)
        elif isinstance(parameter, ContinuousParameter):
            plain[name] = float(value)
        elif isinstance(value, np.generic):
            plain[name] = value.item()
        else:
            plain[name] = value
    return plain
