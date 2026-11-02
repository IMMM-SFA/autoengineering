"""Buffered selection preserves physical rules and all independent work."""

from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from autoengineering.optimization import ContinuousParameter, SearchSpace
from autoengineering.utility.engineering_native import (
    NativeDriverReport,
    NativeDriverResultV3,
    native_cost_records,
    native_result_from_json,
    validate_native_result,
)
from autoengineering.utility.engineering_process import EngineeringScenario
from examples.utility import engineering_load_envelope_native as recipe
from examples.utility.engineering import rules


def job():
    cases = (EngineeringScenario("public-case", {
        "ground_voltage": 0.0, "resistor1_ohm": 100.0, "resistor2_ohm": 10000.0,
    }),)
    run = SimpleNamespace(search_space=SearchSpace((ContinuousParameter("source_current", .01, .1),)))
    study = SimpleNamespace(run=run, rules=rules(.62, .001), scenario_ids=("public-case",))
    execution = SimpleNamespace(
        entrypoint="examples.utility.engineering_load:execute", scenarios=cases, study=study,
    )
    spec = SimpleNamespace(execution=execution, max_iterations=20, max_model_solves=40)
    return SimpleNamespace(specification=spec, scratch_path="/private/tmp", source_root="/private/tmp",
                           digest="0" * 64)


def row(voltage=.6200099999935591):
    return {"outputs": {"node1_voltage": 2.0, "node2_voltage": voltage}, "work": {
        "converged": True, "residual_norm": 1e-12, "residual_tolerance": 1e-10,
        "solver_iterations": 10, "component_calls": 100, "derivative_calls": 5,
    }}


def install(monkeypatch, *, voltage=.6200099999935591, success=True):
    calls = []

    def design(cases, minimum, scratch, **kwargs):
        calls.append((cases, minimum, kwargs))
        return {"source_current_A": .014, "driver_success": success,
                "scenario_solves": [row(voltage)], "physical_solves": 3,
                "native_solves": [row(), row()], "driver_final_work": row()["work"],
                "feasible": False}

    monkeypatch.setattr(recipe.native, "native_design", design)
    monkeypatch.setattr(recipe.native, "direct", lambda *a, **kw: row())
    return calls


def test_buffer_flag_is_separate_and_support_is_charged(monkeypatch):
    calls = install(monkeypatch)
    task = job()
    result = recipe.execute(task)
    assert isinstance(result, NativeDriverResultV3)
    assert result.driver_success and not result.optimizer_target_met
    assert calls[0][1] == .62001
    assert calls[0][2]["max_solves"] == 39  # Leaves one call for the scored population.
    assert calls[0][0][0].scenario_id == recipe.SUPPORT_ID
    assert len(result.solves) == 3 and len(result.support_solves) == 1
    assert result.support_solves[0].counter_scope == "independent_problem"
    assert native_result_from_json(result.to_json()) == result
    validate_native_result(task.specification, task, result)
    task.specification.max_model_solves = 3
    with pytest.raises(ValueError, match="ceiling"):
        validate_native_result(task.specification, task, result)
    report = NativeDriverReport(
        "utility-native-report-v1", "1" * 64, "2" * 64, task.digest, "native",
        "success", "completed", None, True, 1.0, result,
    )
    assert NativeDriverReport.from_json(report.to_json()) == report
    costs = {r.resource: r.quantity for r in native_cost_records(report, "3" * 64)}
    assert costs["native_inner_model_calls"] == 4
    assert costs["native_support_component_calls"] == 100
    assert costs["native_scenario_component_calls"] == 100
    assert costs["native_driver_final_component_calls"] == 100
    # Two cumulative driver snapshots are never summed as 200 component calls.


@pytest.mark.parametrize("voltage,success", [(.619999999, True), (.62001, False)])
def test_original_physical_limit_and_driver_failure_survive(monkeypatch, voltage, success):
    install(monkeypatch, voltage=voltage, success=success)
    result = recipe.execute(job())
    assert not result.driver_success
    assert len(result.support_solves) == 1 and len(result.solves) == 3


@pytest.mark.parametrize("damage", ["voltage", "bounds", "forcing", "duplicate", "budget",
                                   "iterations", "entrypoint", "support-id"])
def test_invalid_recipe_refuses_before_model(monkeypatch, damage):
    task = job()
    spec, execution = task.specification, task.specification.execution
    if damage == "voltage":
        execution.study.rules = rules(.61, .001)
    elif damage == "bounds":
        execution.study.run.search_space = SearchSpace((ContinuousParameter("source_current", .01, .2),))
    elif damage == "forcing":
        case = execution.scenarios[0]
        execution.scenarios = (replace(case, forcing=dict(case.forcing) | {"ground_voltage": .03}),)
    elif damage == "duplicate":
        execution.scenarios *= 2
    elif damage == "budget":
        spec.max_model_solves = 2
    elif damage == "iterations":
        spec.max_iterations = 21
    elif damage == "entrypoint":
        execution.entrypoint = "elsewhere:execute"
    else:
        execution.scenarios = (replace(execution.scenarios[0], scenario_id=recipe.SUPPORT_ID),)
    monkeypatch.setattr(recipe.native, "native_design", lambda *a, **kw: pytest.fail("model started"))
    with pytest.raises(ValueError):
        recipe.execute(task)


def test_support_cannot_duplicate_scored_scenario(monkeypatch):
    install(monkeypatch)
    task = job()
    result = recipe.execute(task)
    changed = replace(result, support_solves=(replace(result.support_solves[0], support_id="public-case"),))
    with pytest.raises(ValueError, match="omits"):
        validate_native_result(task.specification, task, changed)


@pytest.mark.parametrize("raw", ['[]', '{}', '{"schema":[]}', '{"schema":"unknown"}'])
def test_native_version_decoder_rejects_malformed_documents(raw):
    with pytest.raises(ValueError):
        native_result_from_json(raw)


@pytest.mark.skipif(importlib.util.find_spec("openmdao") is None,
                    reason="optional OpenMDAO environment required")
def test_registered_recipe_runs_intact_model_with_all_calls_counted(tmp_path, monkeypatch):
    from examples.utility import engineering_load
    from test_utility_engineering_load_robust_native import scenarios

    task = job()
    task.scratch_path = str(tmp_path)
    task.source_root = str(Path(__file__).resolve().parents[1])
    task.specification.execution.scenarios = scenarios()
    task.specification.execution.study.scenario_ids = tuple(s.scenario_id for s in scenarios())
    task.specification.max_model_solves = 53
    observed = {"problems": 0, "model_calls": 0, "cleanups_returned": 0}
    original_factory = recipe.native.factory

    def tracked(ctx):
        observed["problems"] += 1
        problem = original_factory(ctx)
        run, cleanup = problem.model.run_solve_nonlinear, problem.cleanup

        def counted(*args, **kwargs):
            observed["model_calls"] += 1
            assert observed["model_calls"] <= 53
            return run(*args, **kwargs)

        def cleaned():
            value = cleanup()
            observed["cleanups_returned"] += 1
            return value

        problem.model.run_solve_nonlinear, problem.cleanup = counted, cleaned
        return problem

    monkeypatch.setattr(recipe.native, "factory", tracked)
    monkeypatch.setattr(engineering_load, "factory", tracked)
    result = recipe.execute(task)
    (tmp_path / "registration-result.json").write_text(result.to_json())
    (tmp_path / "observed-work.json").write_text(json.dumps(observed, sort_keys=True))
    validate_native_result(task.specification, task, result)
    assert result.driver_success
    assert observed["problems"] == observed["cleanups_returned"] == 26
    assert observed["model_calls"] == len(result.solves) + len(result.support_solves) <= 53
    assert len([s for s in result.solves if s.phase == "scenario"]) == 24
