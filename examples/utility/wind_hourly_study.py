"""Bounded local development rehearsal through the shared scientific controller.

One unchanged baseline plus four Sobol trials in a predeclared 40 m corner domain.
This local qualification domain is not the final task or conventional recipe.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import time

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.records import HostSelection, ResourceLimits
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import canonical_json, digest, unique_json
from autoengineering.campaign.store import checked_directory, durable_write, StoreError
from autoengineering.optimization import (
    OptimizationRunSpec,
    StudySpec,
    ObjectiveSpec,
    BudgetSpec,
    NoiseSpec,
    SearchSpace,
    ContinuousParameter,
    EvaluationAction,
)
from autoengineering.utility.engineering_process import (
    EngineeringScenario,
    EngineeringExecutionSpec,
    SupervisedEngineeringExecutor,
    execution_identity,
    verify_sources,
)
from autoengineering.utility.studies import EngineeringStudy, EngineeringStudySpec
from examples.utility import wind_hourly_scenario as scenario
from examples.utility.wind_hourly_check import pins as hourly_pins

CASE = "hourly-development"
ENTRYPOINT = "examples.utility.wind_hourly_scenario:execute"


def save(root, name, value):
    durable_write(root / name, canonical_json(value).encode())


def read(root, name):
    return unique_json((root / name).read_text())


def pins():
    return {
        "controller": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "hourly_runtime": hourly_pins(),
        "host_environment": host_environment_identity(),
    }


def prepare(output):
    root = Path(output).absolute()
    if (
        root.exists()
        or root.is_symlink()
        or ".." in root.parts
        or any(p.is_symlink() for p in root.parents)
    ):
        raise ValueError("hourly study requires an absent separate output")
    root.mkdir(mode=0o700)
    source = root / "source"
    source.mkdir(mode=0o700)
    binding = scenario.materialize_inputs(source)
    names = [
        str(p.relative_to(scenario.ROOT))
        for p in (scenario.ROOT / "src/autoengineering").rglob("*.py")
    ]
    names += ["examples/utility/__init__.py", *scenario.MODEL_SOURCES]
    for name in sorted(set(names)):
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((scenario.ROOT / name).read_bytes())
    names += [scenario.BINDING_PATH, scenario.POINT_PATH, scenario.REVIEW_PATH]
    refs = tuple(
        reference(source, n, media_type="text/plain", producer="hourly-study")
        for n in sorted(set(names))
        if n not in (scenario.POINT_PATH, scenario.REVIEW_PATH)
    )
    refs += (binding.point, binding.assumptions)
    lock = next(r for r in refs if r.path == "pixi.lock")
    flows = (EngineeringScenario(scenario.SCENARIO_ID, scenario.SCENARIO_FORCING),)
    bounds = {
        name: (value, value + 40.0) if value == 0.0 else (value - 40.0, value)
        for name, value in binding.geometry.baseline.items()
    }
    run = OptimizationRunSpec(
        StudySpec(
            "hourly-wind-development",
            ObjectiveSpec("annual_energy", "maximize"),
            (),
            BudgetSpec(4.0, "physical_executions", 4),
            NoiseSpec(),
            "system",
            17,
        ),
        SearchSpace(tuple(ContinuousParameter(n, *b) for n, b in bounds.items())),
        "sobol",
        {},
        "autoengineering.utility.studies:engineering_evaluator",
    )
    identity = execution_identity(
        ENTRYPOINT,
        refs,
        lock,
        flows,
        60.0,
        16384,
        profile="supervised-engineering-v3",
        preflight=binding.geometry.preflight,
    )
    study = EngineeringStudySpec(run, scenario.rules(), (scenario.SCENARIO_ID,), identity)
    execution = EngineeringExecutionSpec(
        "utility-engineering-execution-v3",
        study,
        ENTRYPOINT,
        refs,
        lock,
        flows,
        60.0,
        16384,
        binding.geometry.preflight,
    )
    verify_sources(execution, source)
    # The fake host supplies unused bookkeeping capabilities. No host is dispatched.
    batch = BatchSpec(
        "1.0",
        "hourly-wind-development",
        host_source_identity(),
        host_environment_identity(),
        HostSelection("fake", "none", "unused-no-host-calls", "1.0"),
        FakeHost(()).capabilities(),
        digest(execution.to_dict()),
        ResourceLimits(1, 1, 0, 0, 600.0, 65.0, 131072, 1048576),
        5,
        (BatchCase(CASE, "roles", digest(binding.geometry.baseline), 1, 5),),
    )
    request = {
        "schema": "utility-hourly-wind-study-request-v1",
        "scope_digest": digest(str(root)),
        "pins": pins(),
        "execution": execution.to_dict(),
        "batch": batch.to_dict(),
        "baseline": binding.geometry.baseline,
        "baseline_action_id": "hourly-baseline",
        "scientific_starts_cap": 5,
        "baseline_calls": 1,
        "sobol_calls": 4,
        "provider_calls": 0,
        "automatic_retries": 0,
        "task_admitted": False,
        "independent_confirmation": False,
        "domain_purpose": "40 m corner neighborhood for shared-controller development qualification",
        "source_year": 2007,
        "scope_elapsed_seconds": 600.0,
        "process_timeout_seconds": 60.0,
        "aggregate_rss_qualified": False,
        "guest_runtime_used": False,
        "prior_standalone_baseline_gwh": 30.107811267852263,
        "parity_rtol": 1e-12,
        "parity_atol": 1e-10,
    }
    save(root, "request.json", request)
    return request


def execute(output, expected):
    root = checked_directory(output)
    request = read(root, "request.json")
    if (
        digest(request) != expected
        or request["scope_digest"] != digest(str(root))
        or request["pins"] != pins()
        or request["scientific_starts_cap"] != 5
        or request["automatic_retries"] != 0
    ):
        raise ValueError("hourly study identity or limits differ")
    if (root / "consumed.json").exists() or (root / "consumed.json").is_symlink():
        raise StoreError("hourly study consumed; saved evidence recovery only")
    spec = EngineeringExecutionSpec.from_dict(request["execution"])
    verify_sources(spec, root / "source")
    batch_spec = BatchSpec.from_dict(request["batch"])
    if (
        spec.study.run.study.budget.max_evaluations != 4
        or len(spec.scenarios) != 1
        or batch_spec.scientific_starts != 5
    ):
        raise ValueError("hourly study matrix differs")
    save(root, "consumed.json", {"request_digest": expected, "automatic_retry_allowed": False})
    batch = BatchStore.create(root / "batch", batch_spec)
    batch.start_case(CASE, batch.spec.cases[0].configuration_digest)
    runner = SupervisedEngineeringExecutor(spec, batch, CASE, root / "source")
    baseline_action = EvaluationAction(
        request["baseline_action_id"], request["baseline"], "system", None, seed=17
    )
    print("Executing one supervised hourly baseline, then four Sobol trials", flush=True)
    baseline = runner(baseline_action)
    save(root, "baseline.json", baseline.to_dict())
    bridge = EngineeringStudy(spec.study, batch, CASE, runner)
    recommendation = bridge.run()
    save(root, "recommendation.json", recommendation.to_dict())
    before = batch.replay()
    recovered = runner.recover_completed(baseline_action)
    second = EngineeringStudy(spec.study, batch, CASE, runner).run()
    after = batch.replay()
    if (
        recovered != baseline
        or recommendation != second
        or before.reservations != after.reservations
        or before.observations != after.observations
    ):
        raise ValueError("completed hourly study replay changed physical work or result")
    if (
        after.pending
        or len(after.reservations) > 5
        or len(after.reservations) != len(after.observations)
    ):
        raise ValueError("hourly study physical accounting incomplete")
    if baseline.evaluation.status != "success" or not recommendation.feasible:
        raise ValueError("hourly development baseline or conventional selection failed")
    baseline_energy = baseline.evaluation.metrics["annual_energy"]
    if abs(baseline_energy - request["prior_standalone_baseline_gwh"]) > request[
        "parity_atol"
    ] + request["parity_rtol"] * abs(baseline_energy):
        raise ValueError("supervised baseline differs from standalone hourly result")
    done = {
        "schema": "utility-hourly-wind-study-completion-v1",
        "request_digest": expected,
        "execution_digest": spec.digest,
        "batch_digest": batch.digest,
        "baseline_energy_gwh": baseline_energy,
        "recommendation": recommendation.to_dict(),
        "scientific_reservations": len(after.reservations),
        "physical_observations": len(after.observations),
        "pending": len(after.pending),
        "baseline_and_study_replayed_without_new_work": True,
        "supervised_baseline_matches_standalone": True,
        "provider_calls": 0,
        "task_admitted": False,
        "independent_confirmation": False,
        "guest_runtime_used": False,
        "aggregate_rss_qualified": False,
        "elapsed_since_batch_creation_seconds": time.time() - batch.created_at,
    }
    save(root, "complete.json", done)
    return done


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("phase", choices=("prepare", "execute"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-digest")
    args = parser.parse_args()
    result = (
        prepare(args.output)
        if args.phase == "prepare"
        else execute(args.output, args.expected_digest)
    )
    print(canonical_json({"schema": result["schema"], "digest": digest(result)}))


if __name__ == "__main__":
    main()
