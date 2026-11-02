"""Development parity for intact coupled solver with explicit ground scenarios."""
import importlib.util

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(importlib.util.find_spec("openmdao") is None,
                                reason="optional OpenMDAO environment required")


def test_scenario_direct_wrapped_parity_and_derivatives(tmp_path):
    from autoengineering.adapters.python import run_lifecycle
    from examples.utility.engineering import adapter, context, direct
    for ground in (-.05, 0., .05):
        reference = direct(.05, ground, tmp_path, derivatives=True)
        ctx = context(.05, tmp_path)
        forcing = {"ground_voltage": np.array(ground)}
        wrapped = run_lifecycle(adapter(), ctx, forcing, ctx.model.inputs, ctx.model.outputs)
        for name, value in reference["outputs"].items():
            np.testing.assert_allclose(wrapped.outputs[name], value, rtol=1e-10, atol=1e-12)
        assert wrapped.diagnostics["residual_norm"] <= 1e-10
        assert reference["work"]["derivative_calls"] > 0
        step = 1e-6
        left = direct(.05-step, ground, tmp_path)
        right = direct(.05+step, ground, tmp_path)
        numerical = (right["outputs"]["node2_voltage"] - left["outputs"]["node2_voltage"])/(2*step)
        np.testing.assert_allclose(reference["node2_current_derivative"], numerical, rtol=1e-5)
        assert forcing["ground_voltage"] == ground
        assert wrapped.training.status == "not_applicable"


def test_source_power_is_an_engineering_objective_with_voltage_veto(tmp_path):
    from autoengineering.adapters.python import run_lifecycle
    from autoengineering.campaign.acceptance import CheckContext, CheckRegistry
    from autoengineering.campaign.records import EvaluationRecord
    from autoengineering.utility.outcomes import OutcomeRegistry, engineering_decision
    from examples.utility.engineering import adapter, context, required_voltage, rules, source_power
    acceptance = rules(.62, .001)
    records = []
    for name, current in (("baseline", .05), ("lower-current", .04), ("invalid", .01)):
        contexts = {}
        for index, ground in enumerate((-.05, 0., .05)):
            ctx = context(current, tmp_path)
            forcing = {"ground_voltage": np.array(ground)}
            result = run_lifecycle(adapter(), ctx, forcing, ctx.model.inputs, ctx.model.outputs)
            contexts[f"scenario-{index}"] = CheckContext(result.outputs, forcing, ctx.parameters)
        template = EvaluationRecord(name, name, {"source_current": current}, "success", {}, (), (),
                                    "development", name, 0., {})
        records.append(OutcomeRegistry({"source_power": source_power}).evaluate(
            acceptance, contexts, CheckRegistry({("node_voltage", "1"): required_voltage}), template))
    decision = engineering_decision(records[0], tuple(records[1:]), acceptance)
    assert decision.selected_id == "lower-current"
    assert "invalid" not in decision.eligible_alternatives


def test_native_driver_preserves_derivatives_and_counts_inner_solves(tmp_path):
    from examples.utility.engineering import native_design
    result = native_design((-.05, 0., .05), .62, tmp_path)
    assert result["driver_success"]
    assert result["feasible"]
    assert .01 <= result["source_current_A"] < .05
    assert result["physical_solves"] == len(result["native_solves"]) + 3
    assert result["physical_solves"] <= 40
    assert any(s["work"]["derivative_calls"] > 0 for s in result["native_solves"])
    with pytest.raises(ValueError, match="cannot cover"):
        native_design((-.05, 0., .05), .62, tmp_path, max_solves=3)


def test_real_calibration_bridge_pauses_and_resumes_without_duplicate_starts(tmp_path):
    from examples.utility.engineering_study import run
    result = run(tmp_path / "engineering-study")
    assert result["physical_starts_before_resume"] == 3
    assert result["physical_starts_total"] == 12
    assert result["repeat_completed_run_added_starts"] == 0
    assert result["host_invocations"] == 0
    assert result["utility_verdict"] == "not_attempted"
