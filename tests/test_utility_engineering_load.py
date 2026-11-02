"""Authored load-binding controls, disjoint from proposed final load cases."""
from dataclasses import replace
import importlib.util
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


def test_load_module_import_and_adapter_need_no_optional_framework():
    script = """
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'openmdao' or name.startswith('openmdao.'):
        raise AssertionError('optional framework imported')
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from examples.utility.engineering_load import adapter
adapter()
"""
    subprocess.run([sys.executable, "-c", script], check=True, capture_output=True)


@pytest.mark.skipif(importlib.util.find_spec("openmdao") is None,
                    reason="optional OpenMDAO environment required")
class TestLoadCircuit:
    def test_supervised_load_result_recovers_without_new_start(self, tmp_path, monkeypatch):
        from autoengineering.agents.batch import BatchStore
        from autoengineering.campaign.artifacts import reference
        from autoengineering.optimization import (
            BudgetSpec, ContinuousParameter, NoiseSpec, ObjectiveSpec, OptimizationRunSpec,
            SearchSpace, StudySpec,
        )
        from autoengineering.optimization.records import EvaluationAction
        from autoengineering.utility.engineering_process import (
            EngineeringExecutionSpec, EngineeringScenario, SupervisedEngineeringExecutor,
            execution_identity,
        )
        from autoengineering.utility.studies import EngineeringStudySpec
        from examples.utility.engineering import rules
        from test_agent_batch import specification

        root = Path(__file__).resolve().parents[1]
        source = tmp_path / "source"
        source.mkdir(mode=0o700)
        names = [str(p.relative_to(root)) for p in (root / "src/autoengineering").rglob("*.py")]
        names += ["examples/utility/__init__.py", "examples/utility/engineering.py",
                  "examples/utility/engineering_load.py", "examples/interoperability/circuit/model.py",
                  "examples/interoperability/circuit/fixture.py"]
        for name in (*names, "pixi.lock"):
            target = source / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((root / name).read_bytes())
        refs = tuple(reference(source, name, media_type="text/plain", producer="authored-load")
                     for name in names)
        lock = reference(source, "pixi.lock", media_type="text/plain", producer="authored-load")
        scenario = EngineeringScenario("authored-load", {
            "ground_voltage": .025, "resistor1_ohm": 110., "resistor2_ohm": 9000.})
        entry = "examples.utility.engineering_load:execute"
        run = OptimizationRunSpec(StudySpec("authored-load", ObjectiveSpec("source_power", "minimize"),
            (), BudgetSpec(1, "physical_executions", 1), NoiseSpec(), "system", 17),
            SearchSpace((ContinuousParameter("source_current", .01, .1),)), "sobol", {},
            "autoengineering.utility.studies:engineering_evaluator")
        study = EngineeringStudySpec(run, rules(.62, .001), (scenario.scenario_id,),
            execution_identity(entry, refs, lock, (scenario,), 10., 32768))
        execution = EngineeringExecutionSpec("utility-engineering-execution-v1", study,
            entry, refs, lock, (scenario,), 10., 32768)
        batch = BatchStore.create(tmp_path / "batch", specification(science=4))
        batch.start_case("first", batch.spec.cases[0].configuration_digest)
        runner = SupervisedEngineeringExecutor(execution, batch, "first", source)
        action = EvaluationAction("load-control", {"source_current": .05}, "system", None, seed=17)
        value = runner(action)
        assert value.evaluation.status == "success"
        assert value.scenarios[0].values["source_power"] > 0
        assert len(batch.replay().reservations) == 1
        assert all(observation.stop_verified for observation in batch.replay().observations.values())
        def forbidden(*args, **kwargs):
            raise AssertionError("recovery launched a new process")
        monkeypatch.setattr("autoengineering.utility.engineering_process.supervise_process", forbidden)
        assert runner.recover_completed(action) == value
        assert len(batch.replay().reservations) == 1

    @pytest.mark.parametrize("r1,r2,ground", [(110., 9000., .025), (90., 11000., -.025)])
    def test_native_parity_residuals_and_current_derivative(self, tmp_path, r1, r2, ground):
        from autoengineering.adapters.python import run_lifecycle
        from examples.interoperability.circuit.fixture import VARIABLES
        from examples.interoperability.circuit.model import factory
        from examples.utility.engineering import context as original_context
        from examples.utility.engineering_load import adapter, context

        def direct(current):
            problem = factory(original_context(current, tmp_path))
            try:
                problem.setup()
                problem.final_setup()
                problem.model.circuit.R1.options["R"] = r1
                problem.model.circuit.R2.options["R"] = r2
                problem.set_val("source.I", current, units="A")
                problem.set_val("ground.V", ground, units="V")
                problem.run_model()
                return {name: float(problem.get_val(variable).item())
                        for name, (variable, _) in VARIABLES.items()}
            finally:
                problem.cleanup()

        ctx = context(.05, tmp_path)
        forcing = {"ground_voltage": np.array(ground), "resistor1_ohm": np.array(r1),
                   "resistor2_ohm": np.array(r2)}
        saved = {key: value.copy() for key, value in forcing.items()}
        result = run_lifecycle(adapter(), ctx, forcing, ctx.model.inputs, ctx.model.outputs)
        expected = direct(.05)
        for name in VARIABLES:
            np.testing.assert_allclose(result.outputs[name], expected[name], rtol=1e-10, atol=1e-12)
        assert result.diagnostics["converged"] == 1
        assert result.diagnostics["residual_norm"] <= 1e-10
        assert result.diagnostics["component_calls"] > 0
        assert result.training.status == "not_applicable"
        for key in saved:
            np.testing.assert_array_equal(forcing[key], saved[key])

        wrapped = adapter()
        handle = wrapped.prepare(ctx)
        try:
            wrapped.run(handle, forcing)
            derivative = handle.native.problem.compute_totals(
                of=["circuit.n2.V"], wrt=["source.I"])["circuit.n2.V", "source.I"].item()
            assert handle.native.problem.derivative_calls > 0
            with pytest.raises(ValueError, match="twice"):
                wrapped.run(handle, forcing)
        finally:
            wrapped.cleanup(handle)
        assert handle.native.closed
        left, right = direct(.05 - 1e-6), direct(.05 + 1e-6)
        numerical = (right["node2_voltage"] - left["node2_voltage"]) / 2e-6
        np.testing.assert_allclose(derivative, numerical, rtol=1e-5)

    @pytest.mark.parametrize("bad", [0., -1., float("nan"), float("inf")])
    def test_invalid_resistance_never_runs_model(self, tmp_path, monkeypatch, bad):
        from examples.utility.engineering_load import adapter, context
        wrapped = adapter()
        handle = wrapped.prepare(context(.05, tmp_path))
        def forbidden():
            raise AssertionError("invalid load ran model")
        monkeypatch.setattr(handle.native.problem, "run_model", forbidden)
        try:
            with pytest.raises(ValueError):
                wrapped.run(handle, {"ground_voltage": np.array(.025),
                    "resistor1_ohm": np.array(bad), "resistor2_ohm": np.array(9000.)})
            assert not handle.native.consumed
        finally:
            wrapped.cleanup(handle)
        assert handle.native.closed

    def test_units_refuse_before_factory_and_old_profile_is_unchanged(self, tmp_path, monkeypatch):
        from examples.utility import engineering_load as load
        from examples.utility.engineering import context as old_context, direct
        old = old_context(.05, tmp_path)
        before = old.to_json()
        reference = direct(.05, 0., tmp_path)["outputs"]
        ctx = load.context(.05, tmp_path)
        assert ctx.model.digest != old.model.digest
        assert set(ctx.parameters) == {"source_current"}
        assert {p.name for p in old.model.inputs} == {"ground_voltage"}
        assert {r.path for r in old.model.source_bundle} < {r.path for r in ctx.model.source_bundle}
        bad = replace(ctx, model=replace(ctx.model, inputs=tuple(
            replace(p, units="kohm") if p.name == "resistor1_ohm" else p
            for p in ctx.model.inputs)))
        def forbidden(_):
            raise AssertionError("invalid units constructed model")
        monkeypatch.setattr(load, "factory", forbidden)
        with pytest.raises(ValueError, match="exact units"):
            load.adapter().prepare(bad)
        assert old.to_json() == before
        assert direct(.05, 0., tmp_path)["outputs"] == reference
