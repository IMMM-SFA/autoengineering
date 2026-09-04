"""Execute the preregistered full-observability comparison."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time
from typing import TYPE_CHECKING

import numpy as np
from scipy.stats import qmc

from autoengineering.optimization import (
    EvaluationScope,
    EvaluationStatus,
    FunctionNetworkEvaluator,
    SobolBackend,
)
from autoengineering.research.runner import EvaluationContext

from .problems import FullNetworkProblem, benchmark_problems

if TYPE_CHECKING:
    from autoengineering.optimization.full_network_backend import FullNetworkBayesBackend

SCHEMA_VERSION = "1.0"
METHODS = ("system", "function_network_full")
BENCHMARK_SEEDS = tuple(range(10))
WARM_START_COUNT = 4
EVALUATIONS_PER_RUN = 10
CALIBRATION_POINTS = 16
CALIBRATION_SAMPLES = 256


class RunExecutionError(RuntimeError):
    """Retain completed raw and calibration records when a run later fails."""

    def __init__(self, records, calibration, cause: Exception) -> None:
        super().__init__(str(cause))
        self.records = records
        self.calibration = calibration
        self.cause = cause


class MemoryLedger:
    """Small append-only ledger used while trace artifacts remain available."""

    def __init__(self) -> None:
        self._entries = []

    def append(self, action, result) -> None:
        if action.id != result.action_id:
            raise ValueError("benchmark action and result IDs must match")
        if any(existing.id == action.id for existing, _ in self._entries):
            raise ValueError(f"duplicate benchmark action ID: {action.id}")
        self._entries.append((action, result))

    def entries(self):
        return tuple(self._entries)

    def snapshot(self):
        payload = b"".join(
            json.dumps(
                {"action": action.to_dict(), "result": result.to_dict()},
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
            for action, result in self._entries
        )
        return self.entries(), payload

    def scientific_training_entries(self):
        statuses = {EvaluationStatus.SUCCESS, EvaluationStatus.SCIENTIFIC_INFEASIBLE}
        return tuple(entry for entry in self._entries if entry[1].status in statuses)

    def constraint_training_entries(self):
        return self.scientific_training_entries()

    def objective_training_entries(self):
        return tuple(
            entry for entry in self._entries if entry[1].status is EvaluationStatus.SUCCESS
        )


class _UnitClock:
    def __init__(self) -> None:
        self._value = -1.0

    def __call__(self) -> float:
        self._value += 1.0
        return self._value


def _backend(problem: FullNetworkProblem, method: str, seed: int):
    study = problem.study(seed, method)
    if method == "system":
        from autoengineering.optimization.system_backend import SystemBayesBackend

        return SystemBayesBackend(study, problem.space, min_initial=WARM_START_COUNT)
    if method == "function_network_full":
        from autoengineering.optimization.full_network_backend import FullNetworkBayesBackend

        return FullNetworkBayesBackend(
            study,
            problem.space,
            problem.network,
            problem.system,
            min_initial=WARM_START_COUNT,
            candidate_pool_size=64,
            posterior_samples=128,
        )
    raise ValueError(f"unknown benchmark method: {method!r}")


def _warm_backend(problem: FullNetworkProblem, seed: int) -> SobolBackend:
    return SobolBackend(problem.study(seed, "system"), problem.space)


def _context(problem: FullNetworkProblem, artifact_dir: Path) -> EvaluationContext:
    return EvaluationContext(
        system=problem.system,
        alternatives=problem.alternatives,
        source_arrays=problem.source_arrays,
        observed={},
        outcome_functions={"placeholder": lambda _: 0.0},
        cost_unit="evaluation",
        artifact_dir=artifact_dir,
        cost_per_evaluator_second=1.0,
    )


def execute_suite(
    *,
    problems: Iterable[FullNetworkProblem] | None = None,
    methods: Iterable[str] = METHODS,
    seeds: Iterable[int] = BENCHMARK_SEEDS,
    progress: bool = True,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Execute all requested runs and retain failures in the raw record stream."""
    selected_problems = tuple(benchmark_problems() if problems is None else problems)
    selected_methods = tuple(methods)
    selected_seeds = tuple(seeds)
    total = len(selected_problems) * len(selected_methods) * len(selected_seeds)
    records: list[dict[str, object]] = []
    calibration: list[dict[str, object]] = []
    completed = 0
    for problem in selected_problems:
        for seed in selected_seeds:
            for method in selected_methods:
                completed += 1
                if progress:
                    print(
                        f"[{completed}/{total}] problem={problem.name} method={method} seed={seed}",
                        flush=True,
                    )
                try:
                    run_records, run_calibration = execute_run(problem, method, seed)
                except RunExecutionError as error:
                    records.extend(error.records)
                    calibration.extend(error.calibration)
                    records.append(_error_record(problem, method, seed, error.cause))
                    continue
                except Exception as error:
                    records.append(_error_record(problem, method, seed, error))
                    continue
                records.extend(run_records)
                calibration.extend(run_calibration)
    return records, calibration


def execute_run(
    problem: FullNetworkProblem, method: str, seed: int
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Execute one ten-evaluation closed loop and replay every suggestion."""
    records: list[dict[str, object]] = []
    calibration: list[dict[str, object]] = []
    try:
        return _execute_run(problem, method, seed, records, calibration)
    except Exception as error:
        raise RunExecutionError(records, calibration, error) from error


def _execute_run(
    problem: FullNetworkProblem,
    method: str,
    seed: int,
    records: list[dict[str, object]],
    calibration: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    temporary_root = Path(tempfile.gettempdir()).resolve(strict=True)
    with tempfile.TemporaryDirectory(
        prefix="autoengineering-full-network-", dir=temporary_root
    ) as directory:
        ledger = MemoryLedger()
        evaluator = FunctionNetworkEvaluator(
            problem.network,
            _context(problem, Path(directory)),
            runner=problem.runner,
            clock=_UnitClock(),
        )
        backend = _backend(problem, method, seed)
        warm = _warm_backend(problem, seed)
        cumulative_cost = 0.0
        best: float | None = None
        for index in range(EVALUATIONS_PER_RUN):
            active = warm if index < WARM_START_COUNT else backend
            started = time.perf_counter()
            action = active.suggest(ledger, n=1)[0]
            overhead = time.perf_counter() - started
            fresh = (
                _warm_backend(problem, seed)
                if index < WARM_START_COUNT
                else _backend(problem, method, seed)
            )
            replay_action = fresh.suggest(ledger, n=1)[0]
            replay_consistent = action.to_dict() == replay_action.to_dict()
            problem.space.encode(action.config)
            if action.scope is not EvaluationScope.SYSTEM:
                raise ValueError("benchmark backend returned a non-system action")
            if action.id != f"eval-{index:06d}":
                raise ValueError("benchmark backend returned a noncanonical action ID")
            diagnostics = active.diagnostics(ledger)
            replay_diagnostics = fresh.diagnostics(ledger)
            replay_consistent &= _diagnostic_signature(diagnostics.to_dict()) == (
                _diagnostic_signature(replay_diagnostics.to_dict())
            )
            if not replay_consistent:
                raise ValueError("fresh backend suggestion replay differed")
            if index >= WARM_START_COUNT:
                records.append(
                    {
                        "record_type": "acquisition",
                        "schema_version": SCHEMA_VERSION,
                        "problem": problem.name,
                        "method": method,
                        "seed": seed,
                        "evaluation_index": index,
                        "action": action.to_dict(),
                        "diagnostics": _diagnostic_signature(diagnostics.to_dict()),
                        "replay_consistent": replay_consistent,
                        "optimizer_overhead_seconds": overhead,
                    }
                )
            result = evaluator.evaluate(action)
            if result.status is not EvaluationStatus.SUCCESS:
                raise RuntimeError(
                    f"evaluation {action.id} failed with {result.status.value}: {result.message}"
                )
            if not math.isclose(result.cost, 1.0, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError("deterministic evaluator cost differed from one unit")
            cumulative_cost += result.cost
            if cumulative_cost > 10.0 + 1e-12:
                raise ValueError("benchmark exceeded its evaluation budget")
            ledger.append(action, result)
            feasible = problem.feasible(result.outcomes)
            if feasible:
                objective = result.outcomes[problem.network.objective.outcome]
                best = objective if best is None else max(best, objective)
            records.append(
                {
                    "record_type": "evaluation",
                    "schema_version": SCHEMA_VERSION,
                    "problem": problem.name,
                    "method": method,
                    "seed": seed,
                    "evaluation_index": index,
                    "action": action.to_dict(),
                    "result": _portable_result(result.to_dict()),
                    "cumulative_cost": cumulative_cost,
                    "feasible": feasible,
                    "best_feasible_objective": best,
                    "normalized_regret": problem.normalized_regret(best),
                    "invalid_configuration": False,
                    "budget_overrun": False,
                    "artifact_error": False,
                    "replay_consistent": replay_consistent,
                    "optimizer_overhead_seconds": overhead,
                }
            )
            if method == "function_network_full" and index == WARM_START_COUNT - 1:
                calibration = _calibrate(problem, seed, backend, ledger)
        recommendation = backend.recommend(ledger)
        if recommendation.action_id is not None and recommendation.action_id not in {
            action.id for action, _ in ledger.entries()
        }:
            raise ValueError("backend recommendation was not an observed action")
        return records, calibration


def _calibrate(
    problem: FullNetworkProblem,
    seed: int,
    backend: FullNetworkBayesBackend,
    ledger: MemoryLedger,
) -> list[dict[str, object]]:
    sampler = qmc.Sobol(
        d=problem.space.encoded_dimension,
        scramble=True,
        seed=problem.study(seed, "function_network_full").seed + 500_000,
    )
    points = sampler.random_base2(m=4)
    configs = tuple(problem.space.decode(point) for point in points)
    posteriors = backend.posterior_samples_many(ledger, configs, sample_count=CALIBRATION_SAMPLES)
    records = []
    for index, (config, posterior) in enumerate(zip(configs, posteriors, strict=True)):
        truth = problem.analytic(config)
        constraints = {}
        for constraint in problem.network.constraints:
            samples = posterior.constraints[constraint.outcome]
            probability = float(
                np.mean(
                    samples >= constraint.threshold
                    if constraint.operator == ">="
                    else samples <= constraint.threshold
                )
            )
            constraints[constraint.outcome] = {
                "probability": probability,
                "feasible": bool(
                    truth[constraint.outcome] >= constraint.threshold
                    if constraint.operator == ">="
                    else truth[constraint.outcome] <= constraint.threshold
                ),
            }
        records.append(
            {
                "schema_version": SCHEMA_VERSION,
                "problem": problem.name,
                "seed": seed,
                "heldout_index": index,
                "config": dict(config),
                "truth": dict(truth),
                "objective_mean": float(np.mean(posterior.objective)),
                "objective_lower": float(np.quantile(posterior.objective, 0.05)),
                "objective_upper": float(np.quantile(posterior.objective, 0.95)),
                "objective_variance": float(np.var(posterior.objective, ddof=0)),
                "constraints": constraints,
            }
        )
    return records


def _portable_result(result: Mapping[str, object]) -> dict[str, object]:
    portable = dict(result)
    portable["artifacts"] = {
        artifact_id: f"trace:{artifact_id}" for artifact_id in result["artifacts"]
    }
    return portable


def _diagnostic_signature(data: Mapping[str, object]) -> dict[str, object]:
    result = dict(data)
    result.pop("optimizer_seconds", None)
    return result


def _error_record(
    problem: FullNetworkProblem, method: str, seed: int, error: Exception
) -> dict[str, object]:
    message = str(error)
    return {
        "record_type": "run_error",
        "schema_version": SCHEMA_VERSION,
        "problem": problem.name,
        "method": method,
        "seed": seed,
        "error_type": type(error).__name__,
        "error": message,
        "invalid_configuration": "configuration" in message,
        "budget_overrun": "budget" in message,
        "artifact_error": "artifact" in message,
    }


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def scientific_signature(records: Iterable[Mapping[str, object]]) -> str:
    scientific = []
    for source in records:
        record = dict(source)
        record.pop("optimizer_overhead_seconds", None)
        if record.get("record_type") == "evaluation":
            result = dict(record["result"])
            result.pop("optimizer_seconds", None)
            result.pop("evaluator_seconds", None)
            record["result"] = result
        scientific.append(record)
    return hashlib.sha256(canonical_json(scientific).encode("utf-8")).hexdigest()


def write_raw_records(path: Path, records: Iterable[Mapping[str, object]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(canonical_json(record) + "\n")


def read_raw_records(path: Path) -> list[dict[str, object]]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid raw JSON on line {line_number}") from error
            if not isinstance(value, dict):
                raise ValueError(f"raw record on line {line_number} is not an object")
            records.append(value)
    return records
