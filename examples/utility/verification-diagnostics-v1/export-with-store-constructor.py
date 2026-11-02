"""Export saved development predictions and scenario checks without running models."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import csv
import hashlib
import importlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from autoengineering.campaign.artifacts import confined_file, read_arrays, read_bytes
from autoengineering.campaign.serialization import digest, unique_json
from autoengineering.optimization import EvaluationAction
from autoengineering.utility.confirmation import SelectedState, read_manifest
from autoengineering.utility.engineering_process import SupervisedEngineeringExecutor
from autoengineering.utility.mixed_execution import ScriptedMixedPlan
from autoengineering.utility.outcomes import EngineeringEvaluation, aggregate, scenario_checks
from autoengineering.utility.store import SuiteStore


def export(project: Path, output: Path):
    project = project.resolve()
    study = project / "examples/utility/development/four-family-v1"
    suite = study / "suite"
    inventory_path = project / "examples/utility/source-inventory-preflight-qualified.json"
    inventory = unique_json(inventory_path.read_text())
    inputs = {
        str(inventory_path.relative_to(project)): hashlib.sha256(
            inventory_path.read_bytes()
        ).hexdigest()
    }

    def raw(path):
        path = Path(path)
        name = str(path.relative_to(project))
        expected = inventory["files"][name]
        result = confined_file(project, name).read_bytes()
        if hashlib.sha256(result).hexdigest() != expected:
            raise ValueError("diagnostic input differs from its pinned inventory: " + name)
        inputs[name] = expected
        return result

    def arrays(folder, ref):
        assert hashlib.sha256(raw(folder / ref.path)).hexdigest() == ref.sha256
        return read_arrays(folder, ref)

    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    meta = unique_json(
        raw(project / "examples/utility/verification-four-family-v1/offline-reader.json").decode()
    )
    raw(suite / "suite.json")
    store = SuiteStore(suite)
    raw(suite / f"artifacts/{meta['suite_selection']}/selection.json")
    manifest = read_manifest(suite, meta["suite_selection"])
    plan = ScriptedMixedPlan.from_json(raw(study / "execution-plan.json").decode())
    campaigns = {t.task_id: t.campaign for t in plan.campaigns}
    cells = {c.digest: c for c in store.spec.cells}
    routes = {r.route_id: r.kind for r in store.spec.routes}
    bindings = {}
    for path in (suite / "children").glob("*.json"):
        if path.name.endswith("-manifest.json"):
            continue
        document = unique_json(raw(path).decode())
        assert digest(document) == path.stem
        for b in document["bindings"]:
            bindings[b["cell_digest"]] = path.with_suffix("") / "cases" / b["case_id"]
    check_units = {
        "finite": None,
        "node_voltage": "V",
        "wind_spacing": "m",
        "wind_nonnegative_power": "W",
        "wind_rated_power": "W",
        "wind_boundary": "m",
    }
    prediction_rows, scenario_rows, check_rows, layout_rows, summaries = [], [], [], [], []
    counts = {}
    for selected in manifest.cells:
        assert selected.status == "selected"
        raw(suite / selected.selected_state.path)
        bound = SelectedState.from_json(read_bytes(suite, selected.selected_state).decode())
        cell = cells[selected.cell_digest]
        task, route = cell.task_id, routes[cell.route_id]
        counts[task] = counts.get(task, 0) + 1
        campaign = campaigns[task]
        case = bindings[cell.digest]
        common = {
            "task": task,
            "route": route,
            "cell": cell.digest,
            "evaluation": bound.evaluation.id,
        }
        if task in ("leaf", "solar"):
            data = next(d for d in campaign.data if d.role == "comparison")
            observed = arrays(study / "archived-sources", data.artifact)["prediction"]
            assert len(bound.evaluation.outputs) == 1
            predicted = arrays(case / "campaign", bound.evaluation.outputs[0])["prediction"]
            port = next(p for p in bound.model.outputs if p.name == "prediction")
            lookup = {d: i for i, d in enumerate(port.time.dates)}
            support = data.ports[0].time
            index = [lookup[d] for d in support.dates]
            assert all(port.time.scoring_mask[i] and not port.time.warmup_mask[i] for i in index)
            prediction = predicted[index]
            assert prediction.shape == observed.shape == (len(support.dates),)
            assert np.isfinite(prediction).all() and np.isfinite(observed).all()
            error = prediction - observed
            rmse = float(np.sqrt(np.mean(error**2)))
            bias = float(np.mean(error))
            assert np.isclose(rmse, bound.evaluation.metrics["rmse"], rtol=1e-12, atol=1e-12)
            assert np.isclose(bias, bound.evaluation.metrics["bias"], rtol=1e-12, atol=1e-12)
            for date, y, yhat, residual in zip(support.dates, observed, prediction, error):
                prediction_rows.append(
                    {
                        **common,
                        "date": date,
                        "observed": float(y),
                        "prediction": float(yhat),
                        "residual": float(residual),
                        "units": port.units,
                    }
                )
            summaries.append(
                {**common, "points": len(error), "rmse": rmse, "bias": bias, "units": port.units}
            )
        else:
            matches = []
            for path in (case / "engineering/artifacts").glob("*/engineering-values.json"):
                document = unique_json(raw(path).decode())
                for item in document["values"]:
                    if item["value"]["evaluation"]["id"] == bound.evaluation.id:
                        action = EvaluationAction.from_dict(item["action"])
                        value = EngineeringEvaluation.from_dict(item["value"])
                        assert value.evaluation == bound.evaluation
                        assert dict(action.config) == dict(bound.configuration)
                        matches.append(value)
            assert matches and all(v == matches[0] for v in matches)
            value = matches[0]
            rules = campaign.execution.study.rules
            assert {
                o.name: aggregate([s.values[o.name] for s in value.scenarios], o.aggregation)
                for o in rules.outcomes
            } == dict(bound.evaluation.metrics)
            assert scenario_checks(value.scenarios, rules.checks) == bound.evaluation.checks
            scenarios = {s.scenario_id: s for s in campaign.execution.scenarios}
            units = {o.name: o.units for o in rules.outcomes}
            for score in value.scenarios:
                scenario = scenarios[score.scenario_id]
                assert score.forcing_digest == SupervisedEngineeringExecutor._forcing_digest(
                    scenario
                )
                for name, number in score.values.items():
                    scenario_rows.append(
                        {
                            **common,
                            "scenario": score.scenario_id,
                            "outcome": name,
                            "value": number,
                            "units": units[name],
                            "forcing": json.dumps(dict(scenario.forcing), sort_keys=True),
                        }
                    )
                for check in score.checks:
                    check_rows.append(
                        {
                            **common,
                            "scenario": score.scenario_id,
                            "check": check.name,
                            "units": check_units[check.name],
                            "status": check.status,
                            "required": check.required,
                            "value": check.value,
                            "threshold": check.threshold,
                            "reason": check.reason,
                        }
                    )
            if task == "wind":
                for i in range(4):
                    layout_rows.append(
                        {
                            **common,
                            "turbine": i,
                            "x_m": bound.configuration[f"x_{i}"],
                            "y_m": bound.configuration[f"y_{i}"],
                        }
                    )
    assert counts == {"leaf": 7, "solar": 7, "circuit": 7, "wind": 7}
    tables = {
        "predictions.csv": prediction_rows,
        "scenarios.csv": scenario_rows,
        "checks.csv": check_rows,
        "layouts.csv": layout_rows,
    }
    for name, rows in tables.items():
        with (output / name).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=tuple(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    summary = {
        "scope": "one exposed scripted development repetition; comparison data only; not independent confirmation",
        "claim": "saved comparison arrays reproduce selected prediction metrics; scenario checks remain separate from those prediction errors",
        "cells": counts,
        "prediction_summaries": summaries,
        "table_rows": {name: len(rows) for name, rows in tables.items()},
        "inputs": inputs,
        "tables": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in tables
        },
        "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_work": "none; imports and process/network dispatch denied",
        "confirmation_access": "none",
        "utility_verdict": "not_attempted",
        "verification_scope": "hash-pinned prior qualified reader and saved artifacts; not a new full parent/child ledger replay",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"cells": counts, "table_rows": summary["table_rows"]}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    original_import = importlib.import_module
    original_builtin = __import__
    forbidden = args.project.resolve() / "examples/utility/development/four-family-v1"
    forbidden = tuple(
        forbidden / p
        for p in (
            "engineering-preparation/captured",
            "solar-preparation/source",
            "wind-preparation/captured",
        )
    )

    def denied(*args, **kwargs):
        raise AssertionError("diagnostics attempted physical/network dispatch")

    def guarded_import(name, *args, **kwargs):
        if name.startswith(("examples.", "py_wake", "topfarm", "openmdao", "pvlib")):
            raise AssertionError("diagnostics imported scientific implementation")
        return original_import(name, *args, **kwargs)

    def guarded_builtin(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(("examples.", "py_wake", "topfarm", "openmdao", "pvlib")):
            raise AssertionError("diagnostics imported scientific implementation")
        return original_builtin(name, globals, locals, fromlist, level)

    def guard_open(original):
        def opened(path, *args, **kwargs):
            if not isinstance(path, int) and any(
                Path(path).absolute().is_relative_to(p) for p in forbidden
            ):
                raise AssertionError("diagnostics read original captured inputs")
            return original(path, *args, **kwargs)

        return opened

    with ExitStack() as stack:
        for target, replacement in (
            ("subprocess.Popen", denied),
            ("socket.socket", denied),
            ("importlib.import_module", guarded_import),
            ("builtins.__import__", guarded_builtin),
            ("builtins.open", guard_open(open)),
            ("io.open", guard_open(io.open)),
        ):
            stack.enter_context(patch(target, replacement))
        export(args.project, args.output)


if __name__ == "__main__":
    main()
