"""Native design on supplied load sets without a combined worst corner."""

from dataclasses import replace
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from autoengineering.utility.engineering_process import EngineeringScenario
from examples.utility import engineering_load_robust_native as native
from examples.utility.engineering_load_native import dominant_scenario


def scenarios(count=24):
    rng = np.random.default_rng(41)
    return tuple(
        EngineeringScenario(
            f"authored-{i:02d}",
            {
                "ground_voltage": float(rng.uniform(-0.02, 0.02)),
                "resistor1_ohm": float(rng.uniform(90.0, 110.0)),
                "resistor2_ohm": float(rng.uniform(9000.0, 11000.0)),
            },
        )
        for i in range(count)
    )


def test_no_corner_is_required_and_selection_responds_to_voltage_threshold():
    cases = scenarios()
    with pytest.raises(ValueError, match="dominating corner"):
        dominant_scenario(cases)
    assert native.controlling_scenario(cases, 0.62) in cases
    # With equal ground, small R1 controls low voltage; large R2 can control high voltage.
    cases = (
        EngineeringScenario(
            "a", {"ground_voltage": 0.0, "resistor1_ohm": 80.0, "resistor2_ohm": 1000.0}
        ),
        EngineeringScenario(
            "b", {"ground_voltage": 0.0, "resistor1_ohm": 120.0, "resistor2_ohm": 20000.0}
        ),
    )
    assert native.controlling_scenario(cases, 0.1).scenario_id == "a"
    assert native.controlling_scenario(cases, 0.7).scenario_id == "b"


@pytest.mark.parametrize(
    "damage",
    [
        "empty",
        "duplicate",
        "too_many",
        "resistance",
        "nonfinite",
        "bool_voltage",
        "overflow",
        "budget",
    ],
)
def test_invalid_or_unbounded_inputs_refuse_before_constructing_model(
    tmp_path, monkeypatch, damage
):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid native job constructed an OpenMDAO problem")

    monkeypatch.setattr(native, "factory", forbidden)
    cases, voltage, kwargs = scenarios(), 0.62, {}
    if damage == "empty":
        cases = ()
    elif damage == "duplicate":
        cases = (cases[0], cases[0])
    elif damage == "too_many":
        cases = scenarios(25)
    elif damage == "resistance":
        cases = (replace(cases[0], forcing=dict(cases[0].forcing) | {"resistor1_ohm": 0.0}),)
    elif damage == "nonfinite":
        voltage = float("nan")
    elif damage == "bool_voltage":
        voltage = True
    elif damage == "overflow":
        voltage = 100.0
    elif damage == "budget":
        kwargs = {"max_solves": 24}
    with pytest.raises(ValueError):
        native.native_design(cases, voltage, tmp_path, **kwargs)


@pytest.mark.skipif(
    importlib.util.find_spec("openmdao") is None, reason="optional OpenMDAO environment required"
)
class TestRobustNative:
    def test_full_24_case_design_and_neighboring_feasibility(self, tmp_path):
        cases = scenarios()
        result = native.native_design(cases, 0.66, tmp_path)
        assert result["driver_success"]
        assert result["physical_solves"] == len(result["native_solves"]) + 24 <= 40
        assert len(result["scenario_solves"]) == 24
        assert result["driver_final_work"]["derivative_calls"] > 0
        # Native convergence does not override the exact final voltage check.
        feasible = all(
            row["outputs"]["node2_voltage"] >= 0.66 and row["work"]["residual_norm"] <= 1e-10
            for row in result["scenario_solves"]
        )
        assert result["feasible"] == feasible
        assert feasible
        current = result["source_current_A"]
        worst = native.controlling_scenario(cases, 0.66)
        assert result["controlling_scenario"] == worst.scenario_id
        lower = native.direct(current - 1e-6, worst, tmp_path)
        assert lower["outputs"]["node2_voltage"] < 0.66
        higher = [native.direct(current + 1e-6, case, tmp_path) for case in cases]
        assert all(row["outputs"]["node2_voltage"] >= 0.66 for row in higher)
        higher_power = np.mean(
            [
                (current + 1e-6)
                * (row["outputs"]["node1_voltage"] - case.forcing["ground_voltage"])
                for case, row in zip(cases, higher, strict=True)
            ]
        )
        assert higher_power > result["mean_source_power_W"]

    def test_lower_bound_remains_a_valid_design(self, tmp_path):
        result = native.native_design(scenarios(), 0.62, tmp_path)
        assert result["driver_success"] and result["feasible"]
        assert result["source_current_A"] == pytest.approx(0.01, abs=1e-12)

    def test_exhausted_cap_cleans_up_without_final_scenario_work(self, tmp_path, monkeypatch):
        factory = native.factory
        counts = {"solves": 0, "cleanup": 0}

        def tracked(ctx):
            p = factory(ctx)
            solve, cleanup = p.model.run_solve_nonlinear, p.cleanup

            def counted(*args, **kwargs):
                counts["solves"] += 1
                return solve(*args, **kwargs)

            def cleaned():
                counts["cleanup"] += 1
                return cleanup()

            p.model.run_solve_nonlinear, p.cleanup = counted, cleaned
            return p

        monkeypatch.setattr(native, "factory", tracked)
        monkeypatch.setattr(
            native, "direct", lambda *a, **kw: pytest.fail("exhausted cap entered cases")
        )
        with pytest.raises(RuntimeError, match="budget exhausted"):
            native.native_design(scenarios(), 0.62, tmp_path, max_solves=25)
        assert counts == {"solves": 1, "cleanup": 1}

    def test_owned_24_case_job_and_saved_cost_recovery(self, tmp_path, monkeypatch):
        from autoengineering.agents.batch import BatchStore
        from autoengineering.campaign.artifacts import reference
        from autoengineering.optimization import (
            BudgetSpec,
            ContinuousParameter,
            NoiseSpec,
            ObjectiveSpec,
            OptimizationRunSpec,
            SearchSpace,
            StudySpec,
        )
        from autoengineering.utility.engineering_native import (
            NativeDriverSpec,
            SupervisedNativeDriver,
            native_cost_records,
            verify_native_report,
        )
        from autoengineering.utility.engineering_process import (
            EngineeringExecutionSpec,
            SupervisedEngineeringExecutor,
            execution_identity,
        )
        from autoengineering.utility.studies import EngineeringStudySpec
        from examples.utility.engineering import rules
        from test_agent_batch import specification

        root = Path(__file__).resolve().parents[1]
        source = tmp_path / "source"
        source.mkdir(mode=0o700)
        names = [str(p.relative_to(root)) for p in (root / "src/autoengineering").rglob("*.py")]
        names += [
            "examples/utility/__init__.py",
            "examples/utility/engineering.py",
            "examples/utility/engineering_load.py",
            "examples/utility/engineering_load_native.py",
            "examples/utility/engineering_load_robust_native.py",
            "examples/interoperability/circuit/model.py",
            "examples/interoperability/circuit/fixture.py",
        ]
        for name in (*names, "pixi.lock"):
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / name).read_bytes())
        refs = tuple(
            reference(source, name, media_type="text/plain", producer="authored-native-load")
            for name in names
        )
        lock = reference(
            source, "pixi.lock", media_type="text/plain", producer="authored-native-load"
        )
        cases = scenarios()
        entry = "examples.utility.engineering_load:execute"
        run = OptimizationRunSpec(
            StudySpec(
                "authored-native-load",
                ObjectiveSpec("source_power", "minimize"),
                (),
                BudgetSpec(2, "physical_executions", 1),
                NoiseSpec(),
                "system",
                17,
            ),
            SearchSpace((ContinuousParameter("source_current", 0.01, 0.1),)),
            "sobol",
            {},
            "autoengineering.utility.studies:engineering_evaluator",
        )
        study = EngineeringStudySpec(
            run,
            rules(0.66, 0.001),
            tuple(s.scenario_id for s in cases),
            execution_identity(entry, refs, lock, cases, 10.0, 32768),
        )
        execution = EngineeringExecutionSpec(
            "utility-engineering-execution-v1", study, entry, refs, lock, cases, 10.0, 32768
        )
        spec = NativeDriverSpec(
            "utility-native-driver-v1",
            execution,
            "examples.utility.engineering_load_robust_native:execute",
            20,
            40,
            10.0,
            32768,
        )
        batch = BatchStore.create(tmp_path / "batch", specification(science=48))
        batch.start_case("first", batch.spec.cases[0].configuration_digest)
        driver = SupervisedNativeDriver(
            spec, SupervisedEngineeringExecutor(execution, batch, "first", source)
        )
        report = driver.run()
        assert report.status == "success"
        verify_native_report(batch, "first", spec, report)
        assert len(batch.replay().reservations) == 1
        assert [s.scenario_id for s in report.result.solves if s.phase == "scenario"] == [
            s.scenario_id for s in cases
        ]
        costs = {r.resource: r.quantity for r in native_cost_records(report, "0" * 64)}
        assert costs["native_inner_model_calls"] == len(report.result.solves)
        assert costs["native_driver_derivative_calls"] > 0
        from autoengineering.optimization import EvaluationAction

        action = EvaluationAction(
            "fresh-native-design", report.result.configuration, "system", None, seed=17
        )
        value = driver.executor(action)
        assert value.evaluation.eligible
        assert len(value.scenarios) == 24
        assert all(c.status == "pass" for c in value.evaluation.checks)
        assert len(batch.replay().reservations) == 25
        (tmp_path / "native-spec.json").write_text(spec.to_json())
        (tmp_path / "native-report.json").write_text(report.to_json())
        (tmp_path / "scientific-evaluation.json").write_text(value.to_json())

        def forbidden(*args, **kwargs):
            raise AssertionError("native recovery started a process")

        monkeypatch.setattr(
            "autoengineering.utility.engineering_native.supervise_process", forbidden
        )
        monkeypatch.setattr(
            "autoengineering.utility.engineering_process.supervise_process", forbidden
        )
        assert SupervisedNativeDriver(spec, driver.executor).run(recover_only=True) == report
        assert driver.executor.recover_completed(action) == value
        assert len(batch.replay().reservations) == 25

    def test_changed_diode_refuses_before_driver_or_case_work(self, tmp_path, monkeypatch):
        original = native.factory
        observed = {"cleanup": 0}

        def factory(ctx):
            p = original(ctx)
            circuit = p.model.circuit
            configure, cleanup = circuit.configure, p.cleanup

            def changed():
                configure()
                circuit.D1.options["Is"] = 2e-15

            def cleaned():
                observed["cleanup"] += 1
                return cleanup()

            def forbidden(*a, **kw):
                pytest.fail("changed physics entered a solve")

            circuit.configure, p.cleanup = changed, cleaned
            p.model.run_solve_nonlinear = forbidden
            return p

        monkeypatch.setattr(native, "factory", factory)
        with pytest.raises(ValueError, match="supplied diode"):
            native.native_design(scenarios(), 0.66, tmp_path)
        assert observed == {"cleanup": 1}
