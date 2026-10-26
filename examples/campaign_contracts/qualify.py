"""Bounded measured-data qualification and independent verification for Part 2.

Never overwrites a prior run. Three campaign ceilings plus two kernel oracles reserve
80 executions through invocation limits, below the cumulative ceiling of 320.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd

from autoengineering.campaign.artifacts import put_bytes, read_arrays, reference
from autoengineering.campaign.controller import CampaignController
from autoengineering.campaign.execution import supervise
from autoengineering.campaign.identity import scientific_identity, verify_dependencies
from autoengineering.campaign.records import AttemptRecord, CampaignEvent, Response
from autoengineering.campaign.serialization import canonical_json
from autoengineering.campaign.spec import CampaignSpec, ExecutionSpec
from autoengineering.campaign.store import EventStore, durable_write

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "examples/campaign_contracts"
LEGACY = ROOT / "background-research/agentic-architecture/reference-recovery"


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def oracle_job(path):
    from examples.local_models.kernels import hydro_model

    job = json.loads(path.read_text())
    data = pd.read_csv(ROOT / "examples/local_models/data/hydro.csv")
    data = data[data.date < "2020-01-01"].copy()
    outputs = hydro_model(data, job["configuration"])
    with Path(job["output"]).open("xb") as stream:
        np.savez(stream, **outputs)


def run_oracles(output):
    store = EventStore.create(output / "oracles")
    refs = {}
    for index, family in enumerate(("hamon", "hargreaves"), 1):
        attempt = AttemptRecord(
            f"oracle-{family}",
            "two-oracles",
            "launched",
            None,
            f"oracle-nonce-{family}",
            None,
            None,
            True,
            None,
        )
        ref = put_bytes(
            store.root,
            attempt.to_json().encode(),
            name="attempt.json",
            media_type="application/json",
            producer="qualification",
        )
        with store.writer():
            projection = store.replay()
            response = Response(
                f"oracle-start-{family}",
                "ok",
                projection.revision + 1,
                {"attempt_id": attempt.id},
                None,
                (ref.sha256,),
            )
            store.commit(
                CampaignEvent(
                    response.revision,
                    attempt.digest,
                    projection.head_hash,
                    "controller",
                    "oracle_reserved",
                    projection.state,
                    "evaluating",
                    response,
                    (ref,),
                )
            )
        job = store.root / f"job-{family}.json"
        target = store.root / f"{family}.npz"
        durable_write(
            job,
            canonical_json(
                {
                    "configuration": {"pet": family, "capacity": 100.0, "recession": 0.7},
                    "output": str(target),
                }
            ).encode(),
        )
        result = supervise(
            (sys.executable, "-m", "examples.campaign_contracts.qualify", "--oracle-job", str(job)),
            root=store.root,
            attempt_id=attempt.id,
            campaign_id="kernel-oracles",
            settings=ExecutionSpec(("hydrology",)),
            cwd=ROOT,
            launch_nonce=attempt.launch_nonce,
        )
        if result.status != "success" or not result.stopped:
            raise ValueError("kernel oracle failed")
        refs[family] = reference(
            store.root, target.name, media_type="application/x-npz", producer=attempt.id
        )
        resolved = replace(
            attempt,
            state="finished",
            measured_cost=1.0,
            elapsed_seconds=result.elapsed_seconds,
            uncertain_cost=False,
        )
        ref = put_bytes(
            store.root,
            resolved.to_json().encode(),
            name="attempt.json",
            media_type="application/json",
            producer="qualification",
        )
        with store.writer():
            projection = store.replay()
            response = Response(
                f"oracle-finish-{family}",
                "ok",
                projection.revision + 1,
                {},
                None,
                (ref.sha256, refs[family].sha256),
            )
            store.commit(
                CampaignEvent(
                    response.revision,
                    resolved.digest,
                    projection.head_hash,
                    "controller",
                    "oracle_finished",
                    projection.state,
                    "completed" if index == 2 else "evaluating",
                    response,
                    (ref, refs[family]),
                )
            )
        print(f"Kernel oracle {family}: complete", flush=True)
    durable_write(
        output / "oracle-outputs.json",
        canonical_json({key: value.to_dict() for key, value in refs.items()}).encode(),
    )


def independent_metrics(observed, predicted):
    residual = predicted - observed
    correlation = float(np.corrcoef(observed, predicted)[0, 1])
    return {
        "rmse": float(np.sqrt(np.mean(residual**2))),
        "bias": float(np.mean(residual)),
        "relative_bias": float(np.mean(residual) / observed.mean()),
        "correlation": correlation,
        "nse": float(1 - np.sum(residual**2) / np.sum((observed - observed.mean()) ** 2)),
        "kge": float(
            1
            - np.sqrt(
                (correlation - 1) ** 2
                + (predicted.std() / observed.std() - 1) ** 2
                + (predicted.mean() / observed.mean() - 1) ** 2
            )
        ),
    }


def verify_hydrology(controller):
    state, spec = controller.state(), controller.spec
    if controller.store.replay().state != "completed" or len(state.budget.attempts) != 38:
        raise ValueError("hydrology qualification did not complete exactly 38 attempts")
    if state.budget.unresolved_attempts or state.budget.confirmed_attempts != 38:
        raise ValueError("hydrology attempts are not reconciled")
    if state.confirmation != "confirmation_not_attempted":
        raise ValueError("exposed observations cannot establish confirmation")
    forcing = read_arrays(controller.bundle, controller._data("forcing").artifact)
    observed = {
        role: read_arrays(controller.bundle, controller._data(role).artifact)["prediction"]
        for role in ("fitting", "comparison")
    }
    dates = spec.baseline.model.outputs[0].time.dates
    rows = []
    for evaluation in state.evaluations:
        arrays = read_arrays(controller.store.root, evaluation.outputs[0])
        if evaluation.status != "success" or any(
            check.required and check.status != "pass" for check in evaluation.checks
        ):
            raise ValueError("a hydrology execution or hard check failed")
        capacity = evaluation.configuration["capacity"]
        for key in ("soil", "reservoir", "aet", "prediction", "pet"):
            if np.min(arrays[key]) < -1e-10 or not np.isfinite(arrays[key]).all():
                raise ValueError("nonnegative/finite output check failed independently")
        if np.max(arrays["soil"]) > capacity + 1e-10:
            raise ValueError("soil capacity failed independently")
        if arrays["initial_soil"] != capacity / 2 or arrays["initial_reservoir"] != 0:
            raise ValueError("initial conditions differ")
        precip = forcing["precip_mm"].copy()
        if evaluation.split_id == "diagnostic":
            cutoff = dates.index(controller._data("comparison").ports[0].time.dates[0])
            precip[cutoff:] += 100.0
            source_id = evaluation.provenance["purpose"].removeprefix("causal:")
            original = next(item for item in state.evaluations if item.id == source_id)
            original_arrays = read_arrays(controller.store.root, original.outputs[0])
            np.testing.assert_array_equal(
                arrays["prediction"][:cutoff], original_arrays["prediction"][:cutoff]
            )
        change = np.diff(np.r_[capacity / 2, arrays["soil"] + arrays["reservoir"]])
        residual = precip - arrays["aet"] - arrays["prediction"] - change
        scale = np.maximum.reduce(
            [
                np.ones_like(precip),
                abs(precip),
                abs(arrays["aet"]),
                abs(arrays["prediction"]),
                abs(change),
            ]
        )
        if not np.all(abs(residual) <= 1e-8 + 1e-10 * scale):
            raise ValueError("independent daily balance failed")
        if evaluation.split_id != "diagnostic":
            role = evaluation.split_id
            selected = [dates.index(value) for value in controller._data(role).ports[0].time.dates]
            computed = independent_metrics(observed[role], arrays["prediction"][selected])
            for name, value in computed.items():
                np.testing.assert_allclose(evaluation.metrics[name], value, rtol=1e-12, atol=1e-12)
        rows.append(
            {
                "id": evaluation.id,
                "split": evaluation.split_id,
                "max_balance_error": float(np.max(abs(residual))),
                "metrics": dict(evaluation.metrics),
                "configuration": dict(evaluation.configuration),
            }
        )
    if [
        sum(item.split_id == role for item in state.evaluations)
        for role in ("fitting", "comparison", "diagnostic")
    ] != [32, 4, 2]:
        raise ValueError("hydrology call categories differ from the frozen profile")
    if len(state.decisions) != 4:
        raise ValueError("three pair comparisons and final selection must be separate")
    return rows


def verify(output, *, write=False):
    frozen = json.loads((output / "frozen.json").read_text())
    direct = CampaignController.open(output / "hydrology-direct", inspect_only=True)
    cli = CampaignController.open(output / "hydrology-cli", inspect_only=True)
    route = CampaignController.open(output / "routing", inspect_only=True)
    for name, controller in (("hydrology", direct), ("hydrology", cli), ("routing", route)):
        if scientific_identity(controller.spec, controller.bundle) != frozen["identities"][name]:
            raise ValueError("archived scientific identity differs from freeze")
    rows = verify_hydrology(direct)
    verify_hydrology(cli)
    first, second = direct.state(), cli.state()
    if [item.to_dict() for item in first.decisions] != [
        item.to_dict() for item in second.decisions
    ]:
        raise ValueError("direct and CLI scientific decisions differ")
    for left, right in zip(first.evaluations, second.evaluations, strict=True):
        if (left.configuration, left.metrics, left.status) != (
            right.configuration,
            right.metrics,
            right.status,
        ):
            raise ValueError("direct and CLI observations differ")
    oracle_refs = json.loads((output / "oracle-outputs.json").read_text())
    from autoengineering.campaign.records import ArtifactRef

    for family in ("hamon", "hargreaves"):
        oracle = read_arrays(output / "oracles", ArtifactRef.from_dict(oracle_refs[family]))
        default = next(
            item
            for item in first.evaluations
            if item.split_id == "comparison"
            and dict(item.configuration) == {"pet": family, "capacity": 100.0, "recession": 0.7}
        )
        actual = read_arrays(direct.store.root, default.outputs[0])
        for key in ("prediction", "soil", "pet", "aet"):
            np.testing.assert_allclose(actual[key], oracle[key], rtol=0, atol=1e-12)
    legacy = json.loads((LEGACY / "evaluation.json").read_text())["response"]
    route_state = route.state()
    if len(route_state.budget.attempts) != 2 or route_state.budget.unresolved_attempts:
        raise ValueError("routing reference requires two confirmed executions")
    for evaluation, family in zip(route_state.evaluations, ("triangular", "gamma"), strict=True):
        old_ref = reference(
            ROOT,
            str((LEGACY / f"{family}.npz").relative_to(ROOT)),
            media_type="application/x-npz",
            producer="Part1",
        )
        old = read_arrays(ROOT, old_ref)
        actual = read_arrays(route.store.root, evaluation.outputs[0])
        np.testing.assert_allclose(actual["prediction"], old["predicted"], rtol=0, atol=1e-10)
        for name, value in legacy["families"][family]["comparison"].items():
            np.testing.assert_allclose(evaluation.metrics[name], value, rtol=1e-12, atol=1e-12)
    if route_state.outcome != "accepted_candidate" or legacy["decision"] != "retain_gamma":
        raise ValueError("routing decision parity failed")
    attempts = (
        sum(len(controller.state().budget.attempts) for controller in (direct, cli, route)) + 2
    )
    if attempts != 80 or attempts > frozen["execution_ceiling"]:
        raise ValueError("qualification physical count differs")
    try:
        current_matches = all(
            scientific_identity(controller.spec, ROOT) == frozen["identities"][name]
            for name, controller in (("hydrology", direct), ("routing", route))
        )
    except (ValueError, OSError):
        current_matches = False
    summary = {
        "passed": True,
        "platform": frozen["platform"],
        "source_identities": frozen["identities"],
        "physical_executions": {
            "hydrology_direct": 38,
            "hydrology_cli": 38,
            "routing": 2,
            "kernel_oracles": 2,
            "total": attempts,
        },
        "current_source_matches": current_matches,
        "prior_executions": frozen.get("prior_executions", 0),
        "cumulative_executions": attempts + frozen.get("prior_executions", 0),
        "outcome": first.outcome,
        "confirmation": first.confirmation,
        "decisions": [item.to_dict() for item in first.decisions],
        "evaluations": rows,
        "limits": [
            "macOS ARM64 qualification only",
            "all hydrology observations previously exposed",
            "no scientific generalization claim",
            "strict tokens and new providers deferred",
        ],
    }
    if write:
        durable_write(output / "qualification.json", canonical_json(summary).encode())
    return summary


def previous_executions(output):
    """Conservatively count prior charged/uncertain starts under this qualification root."""
    total = 0
    for previous in output.parent.glob("campaign-qualification-*"):
        if previous == output or not (previous / "frozen.json").is_file():
            continue
        for name in ("hydrology-direct", "hydrology-cli", "routing"):
            if (previous / name / "identity.json").is_file():
                total += len(
                    CampaignController.open(previous / name, inspect_only=True)
                    .state()
                    .budget.attempts
                )
        if (previous / "oracles/events").is_dir():
            total += sum(
                event.operation == "oracle_reserved"
                for event in EventStore(previous / "oracles").replay().events
            )
    return total


def run(output):
    hydro_path = HERE / "profile/campaign.yaml"
    route_path = HERE / "routing-profile/campaign.yaml"
    hydro, routing = CampaignSpec.from_yaml(hydro_path), CampaignSpec.from_yaml(route_path)
    for spec in (hydro, routing):
        verify_dependencies(spec, ROOT)
    prior = previous_executions(output)
    # Invocation limits also enforce the qualification-wide reservation. Child and
    # campaign scientific budgets are unchanged; an unexpected extra call fails visibly.
    reserved = 38 + 38 + 2 + 2
    if prior + reserved > 320:
        raise ValueError("qualification worst-case reservations exceed 320")
    if output.exists():
        raise ValueError("qualification requires a fresh output directory")
    output.mkdir(mode=0o700, parents=True)
    frozen = {
        "schema_version": "1.0",
        "execution_ceiling": 320,
        "reserved_ceiling": reserved,
        "prior_executions": prior,
        "identities": {
            "hydrology": scientific_identity(hydro, ROOT),
            "routing": scientific_identity(routing, ROOT),
        },
        "source_manifest": verify_dependencies(hydro, ROOT),
        "runner_sha256": file_hash(__file__),
        "packages": {
            name: importlib.metadata.version(name)
            for name in (
                "autoengineering",
                "numpy",
                "scipy",
                "pandas",
                "PyYAML",
                "networkx",
                "click",
            )
        },
        "git_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
        ).stdout.strip(),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "command": sys.argv,
        "confirmation": "disabled",
    }
    durable_write(output / "frozen.json", canonical_json(frozen).encode())
    try:
        direct = CampaignController.create(
            hydro_path, ROOT, output / "hydrology-direct", max_new_evaluations=38
        )

        def progress(stage):
            if stage == "before_acknowledgment":
                projection = direct.store.replay()
                if projection.events[-1].operation == "action_finished":
                    print(
                        f"Direct hydrology: {len(direct.state(projection).budget.attempts)}/38 attempts",
                        flush=True,
                    )

        direct.store.fault = progress
        direct.advance()
        # Bounded CLI invocations exercise the same frozen profile through independent requests.
        cli_starts = 0
        for index in range(20):
            allowance = min(4, 38 - cli_starts)
            if allowance <= 0:
                raise ValueError("CLI qualification start allowance exhausted before completion")
            args = (
                ["run", str(hydro_path), "--workdir", str(output / "hydrology-cli")]
                if index == 0
                else ["resume", str(output / "hydrology-cli")]
            )
            command = [
                sys.executable,
                "-m",
                "autoengineering.cli",
                "campaign",
                *args,
                "--max-new-evaluations",
                str(allowance),
            ]
            result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
            state = json.loads(result.stdout)
            cli_starts = state["physical_attempts"]
            print(
                f"CLI hydrology: {state['physical_attempts']}/38 attempts; {state['state']}",
                flush=True,
            )
            if state["state"] == "completed":
                break
        else:
            raise ValueError("CLI campaign did not terminate within bounded invocations")
        route = CampaignController.create(
            route_path, ROOT, output / "routing", max_new_evaluations=2
        )
        route.advance()
        print("Routing reference: 2 attempts complete", flush=True)
        run_oracles(output)
        summary = verify(output, write=True)
        print(
            canonical_json(
                {
                    "passed": summary["passed"],
                    "physical_executions": summary["physical_executions"],
                    "outcome": summary["outcome"],
                }
            ),
            flush=True,
        )
    except BaseException as error:
        durable_write(
            output / "failure.json",
            canonical_json(
                {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "attempts": {
                        name: len(
                            CampaignController.open(output / name, inspect_only=True)
                            .state()
                            .budget.attempts
                        )
                        for name in ("hydrology-direct", "hydrology-cli", "routing")
                        if (output / name / "identity.json").exists()
                    },
                }
            ).encode(),
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--oracle-job", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.oracle_job:
        oracle_job(args.oracle_job)
    elif args.output:
        if args.verify:
            result = verify(args.output.absolute())
            print(
                canonical_json(
                    {
                        "passed": result["passed"],
                        "physical_executions": result["physical_executions"],
                    }
                )
            )
        else:
            run(args.output.absolute())
    else:
        parser.error("--output is required")
