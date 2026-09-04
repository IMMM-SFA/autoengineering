"""Execute the preregistered Item 9 mixed-scope comparison."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import tempfile
import time

from autoengineering.optimization import (
    EvaluationScope,
    EvaluationStatus,
    LedgerBackedFunctionNetworkEvaluator,
    MarginalValueExhausted,
    ObservationLedger,
    SearchSpaceExhausted,
    SobolBackend,
    read_verified_npz,
)
from autoengineering.research.runner import EvaluationContext

from .problems import PartialNetworkProblem, benchmark_problems

SCHEMA_VERSION = "1.0"
METHODS = (
    "function_network_full",
    "function_network_partial",
    "function_network_partial_random",
    "function_network_partial_cheapest_informative",
)
BENCHMARK_SEEDS = tuple(range(5))
WARM_START_COUNT = 4
MAX_ACTIONS = 12
BUDGET = 8.0

PARTIAL_SETTINGS = {
    "min_initial": 4,
    "min_component_observations": 3,
    "candidate_pool_size": 16,
    "decision_pool_size": 4,
    "posterior_samples": 16,
    "fantasy_samples": 4,
    "fit_retry_limit": 2,
    "max_component_streak": 2,
    "minimum_value_per_cost": 0.0,
    "cost_quantile": 0.9,
}


class RunExecutionError(RuntimeError):
    """Carry completed raw records when one run later fails."""

    def __init__(self, records, cause: Exception) -> None:
        super().__init__(str(cause))
        self.records = records
        self.cause = cause


class _CostClock:
    def __init__(self, cost: float) -> None:
        self._values = iter((0.0, float(cost)))

    def __call__(self) -> float:
        return next(self._values)


def _backend(problem: PartialNetworkProblem, method: str, seed: int):
    if method == "function_network_full":
        from autoengineering.optimization.full_network_backend import FullNetworkBayesBackend

        return FullNetworkBayesBackend(
            problem.study(seed, "function_network_full"),
            problem.space,
            problem.network,
            problem.system,
            min_initial=WARM_START_COUNT,
            candidate_pool_size=16,
            posterior_samples=64,
            fit_retry_limit=2,
        )
    study = problem.study(seed, "function_network_partial")
    if method == "function_network_partial":
        from autoengineering.optimization.partial_network_backend import PartialNetworkBayesBackend

        backend_type = PartialNetworkBayesBackend
    elif method == "function_network_partial_random":
        from autoengineering.optimization.partial_network_baselines import (
            RandomPartialNetworkBackend,
        )

        backend_type = RandomPartialNetworkBackend
    elif method == "function_network_partial_cheapest_informative":
        from autoengineering.optimization.partial_network_baselines import (
            CheapestInformativePartialNetworkBackend,
        )

        backend_type = CheapestInformativePartialNetworkBackend
    else:
        raise ValueError(f"unknown benchmark method: {method!r}")
    return backend_type(study, problem.space, problem.network, problem.system, **PARTIAL_SETTINGS)


def _warm_backend(problem: PartialNetworkProblem, seed: int) -> SobolBackend:
    return SobolBackend(problem.study(seed, "function_network_full"), problem.space)


def _context(problem: PartialNetworkProblem, artifact_dir: Path) -> EvaluationContext:
    artifact_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    artifact_dir.chmod(0o700)
    return EvaluationContext(
        system=problem.system,
        alternatives=problem.alternatives,
        source_arrays=problem.source_arrays,
        observed={},
        outcome_functions={"placeholder": lambda _: 0.0},
        cost_unit="evaluation",
        artifact_dir=artifact_dir,
    )


def execute_suite(
    *,
    problems: Iterable[PartialNetworkProblem] | None = None,
    methods: Iterable[str] = METHODS,
    seeds: Iterable[int] = BENCHMARK_SEEDS,
    progress: bool = True,
) -> list[dict[str, object]]:
    """Execute selected runs and preserve explicit errors in the raw stream."""
    selected_problems = tuple(benchmark_problems() if problems is None else problems)
    selected_methods = tuple(methods)
    selected_seeds = tuple(seeds)
    total = len(selected_problems) * len(selected_methods) * len(selected_seeds)
    records = []
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
                    records.extend(execute_run(problem, method, seed))
                except RunExecutionError as error:
                    records.extend(error.records)
                    records.append(_error_record(problem, method, seed, error.cause))
                except Exception as error:
                    records.append(_error_record(problem, method, seed, error))
    return records


def execute_run(
    problem: PartialNetworkProblem, method: str, seed: int
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    try:
        return _execute_run(problem, method, seed, records)
    except Exception as error:
        raise RunExecutionError(records, error) from error


def _execute_run(problem, method, seed, records):
    temporary_root = Path(tempfile.gettempdir()).resolve(strict=True)
    with tempfile.TemporaryDirectory(
        prefix="autoengineering-partial-network-", dir=temporary_root
    ) as directory_text:
        directory = Path(directory_text)
        ledger = ObservationLedger(directory / "observations.jsonl")
        ledger.initialize()
        backend = _backend(problem, method, seed)
        warm_backend = _warm_backend(problem, seed)
        cumulative_cost = 0.0
        best: float | None = None
        stop_reason = None
        artifact_producers = {}
        for index in range(MAX_ACTIONS):
            remaining = BUDGET - cumulative_cost
            if remaining <= 1e-12:
                stop_reason = "max_cost"
                break
            if index < WARM_START_COUNT:
                action = replace(
                    warm_backend.suggest(ledger)[0], suggested_by="shared_warm_start"
                )
                replay_action = replace(
                    _warm_backend(problem, seed).suggest(ledger)[0],
                    suggested_by="shared_warm_start",
                )
                estimate = 1.0
                diagnostics = None
                overhead = 0.0
            else:
                minimum = (
                    1.0
                    if method == "function_network_full"
                    else backend.minimum_action_cost(ledger.entries())
                )
                if minimum > remaining + 1e-12:
                    stop_reason = "insufficient_remaining_budget"
                    break
                started = time.perf_counter()
                try:
                    action = backend.suggest(ledger)[0]
                except MarginalValueExhausted:
                    stop_reason = "marginal_value_below_cost"
                    break
                except SearchSpaceExhausted:
                    stop_reason = "search_space_exhausted"
                    break
                overhead = time.perf_counter() - started
                replay_action = _backend(problem, method, seed).suggest(ledger)[0]
                estimate = (
                    1.0
                    if method == "function_network_full"
                    else backend.estimated_action_cost(action, ledger.entries())
                )
                diagnostics = _diagnostic_signature(backend.diagnostics(ledger).to_dict())
                if estimate > remaining + 1e-12:
                    raise ValueError("backend proposed an action beyond the remaining budget")
                records.append(
                    {
                        "record_type": "acquisition",
                        "schema_version": SCHEMA_VERSION,
                        "problem": problem.name,
                        "method": method,
                        "seed": seed,
                        "evaluation_index": index,
                        "action": action.to_dict(),
                        "estimated_cost": estimate,
                        "diagnostics": diagnostics,
                        "replay_consistent": action == replay_action,
                        "optimizer_overhead_seconds": overhead,
                    }
                )
            if action != replay_action:
                raise ValueError("fresh backend suggestion replay differed")
            if action.id != f"eval-{index:06d}":
                raise ValueError("backend returned a noncanonical mixed-scope action ID")
            if index < WARM_START_COUNT and action.scope is not EvaluationScope.SYSTEM:
                raise ValueError("shared warm action was not a complete system evaluation")
            if method == "function_network_full" and action.scope is not EvaluationScope.SYSTEM:
                raise ValueError("full-network method returned a component action")
            if action.scope is EvaluationScope.SYSTEM:
                problem.space.encode(action.config)
            else:
                backend.validate_action(action, ledger.entries())
            expected_cost = problem.expected_cost(action.component)
            if not math.isclose(estimate, expected_cost, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError("conservative action cost differed from deterministic cost")
            result = _evaluate(problem, ledger, directory / "artifacts", action, expected_cost)
            replay_result = _evaluate(
                problem,
                ObservationLedger(ledger.path),
                directory / "replay" / action.id,
                action,
                expected_cost,
            )
            result_replay_consistent = _result_signature(result) == _result_signature(replay_result)
            if not result_replay_consistent:
                raise ValueError("fresh evaluator result replay differed")
            if result.status is not EvaluationStatus.SUCCESS:
                raise RuntimeError(
                    f"evaluation {action.id} failed with {result.status.value}: {result.message}"
                )
            expected = _expected_outcomes(problem, action, artifact_producers)
            if set(result.outcomes) != set(expected) or any(
                not math.isclose(result.outcomes[name], value, rel_tol=0.0, abs_tol=1e-12)
                for name, value in expected.items()
            ):
                raise ValueError("evaluator outcomes differ from analytic truth")
            if not math.isclose(result.cost, expected_cost, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError("realized evaluator cost differs from declared component cost")
            cumulative_cost = math.fsum(item.cost for _, item in (*ledger.entries(), (action, result)))
            if cumulative_cost > BUDGET + 1e-12:
                raise ValueError("benchmark exceeded its evaluator-cost budget")
            ledger.append(action, result)
            if action.scope is EvaluationScope.SYSTEM:
                for artifact_id in result.artifacts:
                    artifact_producers[artifact_id] = (action.id, dict(action.config))
                if problem.feasible(result.outcomes):
                    objective = result.outcomes["utility"]
                    best = objective if best is None else max(best, objective)
                feasible = problem.feasible(result.outcomes)
            else:
                feasible = None
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
                    "artifact_members": {
                        artifact_id: tuple(
                            sorted(
                                read_verified_npz(
                                    result.artifacts[artifact_id],
                                    result.artifact_sha256[artifact_id],
                                )
                            )
                        )
                        for artifact_id in result.artifacts
                    },
                    "estimated_cost": estimate,
                    "cumulative_cost": cumulative_cost,
                    "system_feasible": feasible,
                    "best_feasible_objective": best,
                    "normalized_regret": problem.normalized_regret(best),
                    "parent_system_action_id": (
                        None
                        if action.scope is EvaluationScope.SYSTEM
                        else artifact_producers[action.parent_artifact_ids[0]][0]
                    ),
                    "replay_consistent": action == replay_action and result_replay_consistent,
                    "optimizer_overhead_seconds": overhead,
                }
            )
        else:
            stop_reason = "max_evaluations"
        if stop_reason is None:
            stop_reason = "max_evaluations"
        recommendation = backend.recommend(ledger)
        records.append(
            {
                "record_type": "run_end",
                "schema_version": SCHEMA_VERSION,
                "problem": problem.name,
                "method": method,
                "seed": seed,
                "stop_reason": stop_reason,
                "evaluation_count": len(ledger.entries()),
                "total_cost": cumulative_cost,
                "recommendation": recommendation.to_dict(),
            }
        )
        return records


def _evaluate(problem, ledger, artifact_dir, action, cost):
    evaluator = LedgerBackedFunctionNetworkEvaluator(
        problem.network,
        _context(problem, artifact_dir),
        ledger,
        runner=problem.runner,
        clock=_CostClock(cost),
    )
    return evaluator(action)


def _expected_outcomes(problem, action, artifact_producers):
    if action.scope is EvaluationScope.SYSTEM:
        expected = {}
        analytic = problem.analytic(action.config)
        for component in problem.network.components:
            for output in component.scalar_outputs:
                if EvaluationScope.SYSTEM not in output.observed_in:
                    continue
                name = f"{component.component}.{output.name}"
                if name == "source.driver":
                    expected[name] = 1.0
                elif name in {"upstream.signal", "left.left_value", "right.right_value"}:
                    key = {
                        "upstream.signal": "minimum_signal",
                        "left.left_value": "left.x",
                        "right.right_value": "right.y",
                    }[name]
                    expected[name] = analytic[key] if key in analytic else float(action.config[key])
                elif name == "terminal.utility":
                    expected[name] = analytic["utility"]
                elif name == "terminal.balance":
                    expected[name] = analytic["balance"]
        expected.update(analytic)
        return expected
    parent_config = artifact_producers[action.parent_artifact_ids[0]][1]
    return problem.component_truth(action.component, action.config, parent_config)


def _portable_result(result: Mapping[str, object]) -> dict[str, object]:
    portable = dict(result)
    portable["artifacts"] = {
        artifact_id: f"trace:{artifact_id}" for artifact_id in result["artifacts"]
    }
    return portable


def _result_signature(result) -> dict[str, object]:
    signature = _portable_result(result.to_dict())
    signature.pop("optimizer_seconds", None)
    signature.pop("evaluator_seconds", None)
    return signature


def _diagnostic_signature(data: Mapping[str, object]) -> dict[str, object]:
    signature = dict(data)
    signature.pop("optimizer_seconds", None)
    return signature


def _error_record(problem, method, seed, error):
    return {
        "record_type": "run_error",
        "schema_version": SCHEMA_VERSION,
        "problem": problem.name,
        "method": method,
        "seed": seed,
        "error_type": type(error).__name__,
        "error": str(error),
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
    return hashlib.sha256(canonical_json(scientific).encode()).hexdigest()


def write_raw_records(path: Path, records: Iterable[Mapping[str, object]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(canonical_json(record) + "\n")


def read_raw_records(path: Path) -> list[dict[str, object]]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"raw record on line {line_number} is not an object")
            records.append(value)
    return records
