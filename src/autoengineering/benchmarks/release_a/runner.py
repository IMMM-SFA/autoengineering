"""Sequential execution and raw evidence writing for the Release A benchmark."""

from __future__ import annotations

from collections.abc import Iterable
import hashlib
import json
import math
from pathlib import Path
import time

from .methods import METHOD_NAMES, NATIVE_METHODS, MemoryLedger, build_method
from .problems import BENCHMARK_SEEDS, EVALUATIONS_PER_RUN, BenchmarkProblem, benchmark_problems

SCHEMA_VERSION = "1.0"


class RunExecutionError(RuntimeError):
    """Preserve completed evaluation records when a run later fails."""

    def __init__(self, records: list[dict[str, object]], cause: Exception) -> None:
        super().__init__(str(cause))
        self.records = records
        self.cause = cause


def execute_suite(
    *,
    problems: Iterable[BenchmarkProblem] | None = None,
    methods: Iterable[str] = METHOD_NAMES,
    seeds: Iterable[int] = BENCHMARK_SEEDS,
    replay_native: bool = True,
    progress: bool = True,
) -> list[dict[str, object]]:
    """Execute selected combinations while retaining failed runs as raw records."""
    selected_problems = tuple(benchmark_problems() if problems is None else problems)
    selected_methods = tuple(methods)
    selected_seeds = tuple(seeds)
    total = len(selected_problems) * len(selected_methods) * len(selected_seeds)
    records: list[dict[str, object]] = []
    completed = 0
    for problem in selected_problems:
        for method in selected_methods:
            for seed in selected_seeds:
                completed += 1
                if progress:
                    print(
                        f"[{completed}/{total}] problem={problem.name} method={method} seed={seed}",
                        flush=True,
                    )
                try:
                    run_records = execute_run(problem, method, seed)
                except RunExecutionError as error:
                    records.extend(error.records)
                    records.append(_error_record(problem, method, seed, error.cause, "primary"))
                    continue
                except Exception as error:
                    records.append(_error_record(problem, method, seed, error, "primary"))
                    continue
                if replay_native and method in NATIVE_METHODS:
                    try:
                        replay_records = execute_run(problem, method, seed)
                        consistent = scientific_signature(run_records) == scientific_signature(
                            replay_records
                        )
                    except RunExecutionError as error:
                        consistent = False
                        records.append(_error_record(problem, method, seed, error.cause, "replay"))
                    except Exception as error:
                        consistent = False
                        records.append(_error_record(problem, method, seed, error, "replay"))
                    for record in run_records:
                        record["replay_consistent"] = consistent
                records.extend(run_records)
    return records


def _error_record(
    problem: BenchmarkProblem,
    method: str,
    seed: int,
    error: Exception,
    stage: str,
) -> dict[str, object]:
    message = str(error)
    return {
        "record_type": "run_error",
        "schema_version": SCHEMA_VERSION,
        "problem": problem.name,
        "method": method,
        "seed": seed,
        "stage": stage,
        "error_type": type(error).__name__,
        "error": message,
        "invalid_configuration": isinstance(error, (TypeError, ValueError)),
        "budget_overrun": "budget overrun" in message,
    }


def execute_run(
    problem: BenchmarkProblem,
    method_name: str,
    benchmark_seed: int,
) -> list[dict[str, object]]:
    """Execute one problem-method-seed run with exact accounting."""
    adapter = build_method(method_name, problem, benchmark_seed)
    ledger = MemoryLedger()
    records: list[dict[str, object]] = []
    cumulative_cost = 0.0
    best_feasible: float | None = None
    try:
        for evaluation_index in range(EVALUATIONS_PER_RUN):
            started = time.perf_counter()
            suggestion = adapter.suggest(ledger)
            overhead = time.perf_counter() - started
            action = suggestion.action
            problem.space.encode(action.config)
            expected_id = f"eval-{evaluation_index:06d}"
            if action.id != expected_id:
                raise ValueError(
                    f"method returned action ID {action.id!r}; expected {expected_id!r}"
                )
            preview_cost = problem.preview_cost(dict(action.config))
            if cumulative_cost + preview_cost > problem.cost_budget + 1e-12:
                raise RuntimeError(
                    f"evaluator budget overrun: {cumulative_cost + preview_cost} "
                    f"> {problem.cost_budget}"
                )
            result = problem.evaluate(
                action,
                benchmark_seed=benchmark_seed,
                evaluation_index=evaluation_index,
            )
            if not math.isclose(result.cost, preview_cost, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError("previewed and recorded evaluator costs differ")
            cumulative_cost += result.cost
            ledger.append(action, result)
            adapter.observe(action, result, problem)
            feasible = problem.is_feasible(result)
            if feasible:
                objective = result.outcomes[problem.objective.outcome]
                best_feasible = (
                    objective if best_feasible is None else max(best_feasible, objective)
                )
            unresolved = tuple(
                event
                for event in suggestion.fallback_events
                if not event.startswith("cold_start_insufficient_usable_observations")
            )
            records.append(
                {
                    "record_type": "evaluation",
                    "schema_version": SCHEMA_VERSION,
                    "problem": problem.name,
                    "method": method_name,
                    "seed": benchmark_seed,
                    "study_seed": problem.study(benchmark_seed).seed,
                    "evaluation_index": evaluation_index,
                    "action": action.to_dict(),
                    "result": result.to_dict(),
                    "cumulative_cost": cumulative_cost,
                    "cost_budget": problem.cost_budget,
                    "feasible": feasible,
                    "constraint_violation": problem.constraint_violation(result),
                    "best_feasible_objective": best_feasible,
                    "normalized_regret": problem.normalized_regret(best_feasible),
                    "optimizer_overhead_seconds": overhead,
                    "fallback_events": list(suggestion.fallback_events),
                    "unresolved_fallback_events": list(unresolved),
                    "invalid_configuration": False,
                    "budget_overrun": False,
                    "replay_consistent": None,
                }
            )
    except Exception as error:
        raise RunExecutionError(records, error) from error
    finally:
        adapter.close()
    return records


def scientific_signature(records: Iterable[dict[str, object]]) -> str:
    """Hash action and scientific result fields while excluding timing."""
    scientific = []
    for record in records:
        if record["record_type"] != "evaluation":
            scientific.append(record)
            continue
        result = dict(record["result"])
        result.pop("optimizer_seconds", None)
        result.pop("evaluator_seconds", None)
        scientific.append(
            {
                "problem": record["problem"],
                "method": record["method"],
                "seed": record["seed"],
                "evaluation_index": record["evaluation_index"],
                "action": record["action"],
                "result": result,
                "fallback_events": record["fallback_events"],
            }
        )
    encoded = canonical_json(scientific).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_json(value: object) -> str:
    """Return canonical benchmark JSON."""
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def write_raw_records(path: str | Path, records: Iterable[dict[str, object]]) -> None:
    """Write canonical JSONL records with one terminal newline."""
    output = Path(path)
    with output.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(canonical_json(record))
            stream.write("\n")


def read_raw_records(path: str | Path) -> list[dict[str, object]]:
    """Read and validate the top-level raw record envelope."""
    records = []
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid raw JSONL line {line_number}: {error}") from error
            if not isinstance(record, dict) or record.get("record_type") not in {
                "evaluation",
                "run_error",
            }:
                raise ValueError(f"invalid raw record envelope at line {line_number}")
            if record.get("schema_version") != SCHEMA_VERSION:
                raise ValueError(f"raw record schema differs at line {line_number}")
            records.append(record)
    return records
