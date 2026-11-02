"""Native load optimization on authored cases outside the proposed final grid."""
from pathlib import Path
import importlib.util

import numpy as np
import pytest

from autoengineering.utility.engineering_process import EngineeringScenario
from examples.utility.engineering_load_native import dominant_scenario, native_design


def scenarios():
    return (EngineeringScenario("authored-a", {"ground_voltage": .025,
                "resistor1_ohm": 110., "resistor2_ohm": 9000.}),
            EngineeringScenario("authored-b", {"ground_voltage": -.025,
                "resistor1_ohm": 90., "resistor2_ohm": 11000.}))


def test_missing_dominating_case_and_insufficient_budget_refuse_before_factory(monkeypatch, tmp_path):
    from dataclasses import replace
    from examples.utility import engineering_load_native as native
    def forbidden(*args, **kwargs):
        raise AssertionError("refused setup constructed a model")
    monkeypatch.setattr(native, "factory", forbidden)
    cases = scenarios()
    assert dominant_scenario(cases) == cases[1]
    incomplete = (replace(cases[0], forcing=dict(cases[0].forcing) | {"resistor1_ohm": 80.}), cases[1])
    with pytest.raises(ValueError, match="dominating corner"):
        native_design(incomplete, .62, tmp_path)
    with pytest.raises(ValueError, match="cannot cover"):
        native_design(cases, .62, tmp_path, max_solves=2)


@pytest.mark.parametrize("key,value", [("resistor1_ohm", 0.), ("resistor2_ohm", -1.),
                                      ("ground_voltage", float("nan")), ("ground_voltage", True)])
def test_invalid_native_loads_refuse(key, value):
    from dataclasses import replace
    cases = scenarios()
    with pytest.raises(ValueError):
        dominant_scenario((replace(cases[0], forcing=dict(cases[0].forcing) | {key: value}), cases[1]))


@pytest.mark.skipif(importlib.util.find_spec("openmdao") is None,
                    reason="optional OpenMDAO environment required")
class TestNativeLoad:
    def test_native_solution_matches_circuit_law_and_counts_fresh_solves(self, tmp_path):
        cases = scenarios()
        result = native_design(cases, .62, tmp_path)
        assert result["driver_success"]
        expected = []
        for case in cases:
            ground, r1, r2 = (case.forcing[k]
                for k in ("ground_voltage", "resistor1_ohm", "resistor2_ohm"))
            voltage = .62 - ground
            expected.append(voltage / r1 + (1 + r2 / r1) * 1e-15 * np.expm1(voltage / .025875))
        target = max(.01, max(expected))
        np.testing.assert_allclose(result["source_current_A"], target, atol=1e-8, rtol=1e-6)
        assert result["controlling_scenario"] == "authored-b"
        assert result["physical_solves"] == len(result["native_solves"]) + len(cases) <= 40
        assert result["driver_final_work"]["derivative_calls"] > 0
        assert all(row["work"]["residual_norm"] <= 1e-10 for row in result["scenario_solves"])
        assert result["feasible"] == all(row["outputs"]["node2_voltage"] >= .62
                                          for row in result["scenario_solves"])

    def test_exhausted_driver_preserves_cap_and_cleans_up(self, tmp_path, monkeypatch):
        from examples.utility import engineering_load_native as native
        original_factory = native.factory
        observed = {"solves": 0, "cleanup": 0}
        def factory(ctx):
            problem = original_factory(ctx)
            original = problem.model.run_solve_nonlinear
            cleanup = problem.cleanup
            def counted(*args, **kwargs):
                observed["solves"] += 1
                return original(*args, **kwargs)
            def cleaned():
                observed["cleanup"] += 1
                return cleanup()
            problem.model.run_solve_nonlinear = counted
            problem.cleanup = cleaned
            return problem
        def forbidden(*args, **kwargs):
            raise AssertionError("exhausted driver entered fresh scenario work")
        monkeypatch.setattr(native, "factory", factory)
        monkeypatch.setattr(native, "direct", forbidden)
        with pytest.raises(RuntimeError, match="budget exhausted"):
            native_design(scenarios(), .62, tmp_path, max_solves=3)
        assert observed == {"solves": 1, "cleanup": 1}

    def test_owned_native_job_recovers_original_result_and_costs(self, tmp_path, monkeypatch):
        from autoengineering.agents.batch import BatchStore
        from autoengineering.campaign.artifacts import reference
        from autoengineering.optimization import (
            BudgetSpec, ContinuousParameter, NoiseSpec, ObjectiveSpec, OptimizationRunSpec,
            SearchSpace, StudySpec,
        )
        from autoengineering.utility.engineering_native import (
            NativeDriverSpec, SupervisedNativeDriver, native_cost_records, verify_native_report,
        )
        from autoengineering.utility.engineering_process import (
            EngineeringExecutionSpec, SupervisedEngineeringExecutor, execution_identity,
        )
        from autoengineering.utility.studies import EngineeringStudySpec
        from examples.utility.engineering import rules
        from test_agent_batch import specification

        root = Path(__file__).resolve().parents[1]
        source = tmp_path / "source"
        source.mkdir(mode=0o700)
        names = [str(p.relative_to(root)) for p in (root / "src/autoengineering").rglob("*.py")]
        names += ["examples/utility/__init__.py", "examples/utility/engineering.py",
                  "examples/utility/engineering_load.py", "examples/utility/engineering_load_native.py",
                  "examples/interoperability/circuit/model.py", "examples/interoperability/circuit/fixture.py"]
        for name in (*names, "pixi.lock"):
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / name).read_bytes())
        refs = tuple(reference(source, name, media_type="text/plain", producer="authored-native-load")
                     for name in names)
        lock = reference(source, "pixi.lock", media_type="text/plain", producer="authored-native-load")
        cases = scenarios()
        entry = "examples.utility.engineering_load:execute"
        run = OptimizationRunSpec(StudySpec("authored-native-load", ObjectiveSpec("source_power", "minimize"),
            (), BudgetSpec(2, "physical_executions", 1), NoiseSpec(), "system", 17),
            SearchSpace((ContinuousParameter("source_current", .01, .1),)), "sobol", {},
            "autoengineering.utility.studies:engineering_evaluator")
        study = EngineeringStudySpec(run, rules(.62, .001), tuple(s.scenario_id for s in cases),
            execution_identity(entry, refs, lock, cases, 10., 32768))
        execution = EngineeringExecutionSpec("utility-engineering-execution-v1", study, entry,
                                             refs, lock, cases, 10., 32768)
        spec = NativeDriverSpec("utility-native-driver-v1", execution,
            "examples.utility.engineering_load_native:execute", 20, 40, 10., 32768)
        batch = BatchStore.create(tmp_path / "batch", specification(science=4))
        batch.start_case("first", batch.spec.cases[0].configuration_digest)
        driver = SupervisedNativeDriver(spec,
            SupervisedEngineeringExecutor(execution, batch, "first", source))
        report = driver.run()
        assert report.status == "success"
        verify_native_report(batch, "first", spec, report)
        assert len(batch.replay().reservations) == 1
        assert [s.scenario_id for s in report.result.solves if s.phase == "scenario"] == [s.scenario_id for s in cases]
        costs = {r.resource: r.quantity for r in native_cost_records(report, "0" * 64)}
        assert costs["native_inner_model_calls"] == len(report.result.solves)
        assert costs["native_driver_derivative_calls"] > 0
        def forbidden(*args, **kwargs):
            raise AssertionError("native recovery started a process")
        monkeypatch.setattr("autoengineering.utility.engineering_native.supervise_process", forbidden)
        assert SupervisedNativeDriver(spec, driver.executor).run(recover_only=True) == report
        assert len(batch.replay().reservations) == 1
