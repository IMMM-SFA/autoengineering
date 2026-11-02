"""Two source-bound processes compare direct and wrapped bundled wind evaluations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from autoengineering.agents.batch import BatchCase, BatchSpec, BatchStore
from autoengineering.agents.hosts.fake import FakeHost
from autoengineering.agents.identity import host_environment_identity, host_source_identity
from autoengineering.agents.records import HostSelection, ResourceLimits
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import digest
from autoengineering.optimization import (
    BudgetSpec,
    ContinuousParameter,
    EvaluationAction,
    NoiseSpec,
    ObjectiveSpec,
    OptimizationRunSpec,
    SearchSpace,
    StudySpec,
)
from autoengineering.utility.engineering_process import (
    EngineeringExecutionSpec,
    EngineeringScenario,
    SupervisedEngineeringExecutor,
    execution_identity,
)
from autoengineering.utility.studies import EngineeringStudySpec
from examples.utility.wind import ROOT
from examples.utility.wind_parameters import WindGeometry
from examples.utility.wind_scenario import rules


def prepare(output):
    from py_wake.examples.data.hornsrev1 import wt16_x, wt16_y

    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("wind scenario rehearsal requires an absent output directory")
    output.mkdir(mode=0o700, parents=True)
    source = output / "captured"
    source.mkdir(mode=0o700)
    corners = [0, 3, 12, 15]
    geometry = WindGeometry(
        tuple(float(v) for v in np.asarray(wt16_x)[corners]),
        tuple(float(v) for v in np.asarray(wt16_y)[corners]),
    )
    names = [str(p.relative_to(ROOT)) for p in (ROOT / "src/autoengineering").rglob("*.py")]
    names += [
        "examples/utility/__init__.py",
        "examples/utility/wind.py",
        "examples/utility/wind_parameters.py",
        "examples/utility/wind_scenario.py",
        "examples/utility/rehearse_wind_scenario.py",
        "examples/open_chains/wind/models.py",
    ]
    for name in (*names, "pixi.lock"):
        target = source / name
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    (source / "inputs").mkdir(mode=0o700)
    (source / "inputs/wind-geometry.json").write_text(geometry.to_json())
    names += ["inputs/wind-geometry.json"]
    refs = tuple(
        reference(source, name, media_type="text/plain", producer="wind-development-capture")
        for name in names
    )
    lock = reference(
        source, "pixi.lock", media_type="text/plain", producer="wind-development-capture"
    )
    scenarios = (EngineeringScenario("bundled-distribution", {"direction_step": 30.0}),)
    run = OptimizationRunSpec(
        StudySpec(
            "wind-scenario-parity",
            ObjectiveSpec("annual_energy", "maximize"),
            (),
            BudgetSpec(1.0, "physical_executions", 1),
            NoiseSpec(),
            "system",
            17,
        ),
        SearchSpace(
            tuple(ContinuousParameter(name, *bounds) for name, bounds in geometry.bounds.items())
        ),
        "sobol",
        {},
        "autoengineering.utility.studies:engineering_evaluator",
    )
    executions = []
    for name in ("direct", "execute"):
        entry = "examples.utility.wind_scenario:" + name
        study = EngineeringStudySpec(
            run,
            rules(),
            ("bundled-distribution",),
            execution_identity(
                entry, refs, lock, scenarios, 30.0, 16384, profile="supervised-engineering-v2"
            ),
        )
        executions.append(
            EngineeringExecutionSpec(
                "utility-engineering-execution-v2", study, entry, refs, lock, scenarios, 30.0, 16384
            )
        )
    return output, source, geometry, tuple(executions)


def run(output):
    output, source, geometry, executions = prepare(output)
    profile = BatchSpec(
        "1.0",
        "wind-scenario-parity",
        host_source_identity(),
        host_environment_identity(),
        HostSelection("fake", "none", "not-used", "1.0"),
        FakeHost(()).capabilities(),
        digest({"profile": "wind-direct-wrapped-development-v1"}),
        ResourceLimits(1, 1, 0, 0, 180.0, 10.0, 8388608, 1048576),
        2,
        tuple(
            BatchCase(name, "comparison", spec.digest, 0, 1)
            for name, spec in zip(("direct", "wrapped"), executions)
        ),
    )
    batch = BatchStore.create(output / "batch", profile)
    results = []
    for name, spec in zip(("direct", "wrapped"), executions):
        print("Wind scenario: " + name, flush=True)
        batch.start_case(name, spec.digest)
        executor = SupervisedEngineeringExecutor(spec, batch, name, source)
        action = EvaluationAction(
            name, geometry.baseline, "system", None, seed=17, suggested_by="wind-parity"
        )
        result = executor(action)
        assert result.evaluation.eligible and result.evaluation.status == "success"
        evidence = batch.evidence(
            {"profile": "wind-scenario-parity-v1", "mode": name, "result": result.to_dict()}
        )
        batch.finish_case(name, "passed", (evidence,))
        results.append(result)
        before = len(batch.replay().reservations)
        assert executor.recover_completed(action) == result
        assert len(batch.replay().reservations) == before
    np.testing.assert_allclose(
        results[0].evaluation.metrics["annual_energy"],
        results[1].evaluation.metrics["annual_energy"],
        rtol=1e-12,
        atol=0,
    )
    state = batch.replay()
    assert len(state.reservations) == len(state.observations) == 2 and not state.pending
    summary = {
        "purpose": "supervised bundled wind development parity; not independent weather",
        "geometry": geometry.to_dict(),
        "evaluations": [r.to_dict() for r in results],
        "reservations": 2,
        "observed_stops": 2,
        "completed_replay_added_reservations": 0,
        "units": "GWh",
        "confirmation": "not_attempted",
        "utility_verdict": "not_attempted",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in summary.items() if k not in ("geometry", "evaluations")}),
        flush=True,
    )
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
