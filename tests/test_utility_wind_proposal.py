"""Wind proposals preserve native limits, work types and fresh scoring requirements."""

from dataclasses import replace
import importlib.util

import pytest

from examples.utility.wind_native import NativeCall, NativeWindResult
from examples.utility.wind_parameters import WindGeometry
from examples.utility.wind_proposal import WindNativeSpec, WindNativeProposal, propose


def specification():
    return WindNativeSpec(
        "utility-wind-native-spec-v1",
        WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0)),
        2,
        12,
        4,
    )


def result():
    spec = specification()
    x, y = spec.geometry.x, spec.geometry.y
    return NativeWindResult(
        "not_converged",
        False,
        True,
        x,
        y,
        (
            NativeCall("wake", 1, "completed", x, y, 1.0),
            NativeCall("gradient", 1, "failed", x, y, None),
        ),
        spec.maximum_wake_calls,
        spec.maximum_gradient_calls,
        spec.maximum_iterations,
    )


def test_native_proposal_is_unscored_and_keeps_call_types_separate():
    value = WindNativeProposal("utility-wind-native-proposal-v1", specification(), result())
    assert value.configuration == specification().geometry.baseline
    assert value.eligibility == "fresh_evaluation_required"
    assert value.work == {
        "wake": {"attempted": 1, "completed": 1, "failed": 0, "unresolved": 0},
        "gradient": {"attempted": 1, "completed": 0, "failed": 1, "unresolved": 0},
    }
    assert WindNativeProposal.from_json(value.to_json()) == value
    failed = replace(value, result=replace(value.result, status="budget_exhausted", feasible=False))
    assert failed.configuration is None and failed.work == value.work
    with pytest.raises(ValueError):
        replace(value, eligibility="eligible")


def test_native_proposal_rejects_changed_limits_hardware_and_false_feasibility():
    spec, r = specification(), result()
    with pytest.raises(ValueError, match="limits"):
        WindNativeProposal(
            "utility-wind-native-proposal-v1", spec, replace(r, maximum_wake_calls=13)
        )
    with pytest.raises(ValueError, match="hardware"):
        WindNativeProposal(
            "utility-wind-native-proposal-v1", spec, replace(r, x=r.x[:2], y=r.y[:2])
        )
    with pytest.raises(ValueError, match="spacing"):
        WindNativeProposal(
            "utility-wind-native-proposal-v1", spec, replace(r, x=(0.0, 0.0, 0.0, 600.0))
        )


def test_unsupported_native_profiles_reject_before_model_call(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Unsupported profile reached native execution")

    monkeypatch.setattr("examples.utility.wind_proposal.native_layout", denied)
    with pytest.raises(ValueError, match="128"):
        propose(replace(specification(), maximum_wake_calls=128))
    with pytest.raises(ValueError, match="four turbines"):
        propose(replace(specification(), geometry=WindGeometry((0.0, 600.0), (0.0, 600.0))))
    with pytest.raises(ValueError, match="30-degree"):
        propose(
            replace(specification(), geometry=replace(specification().geometry, direction_step=15))
        )


@pytest.mark.skipif(importlib.util.find_spec("topfarm") is None, reason="optional wind runtime")
def test_real_native_proposal_roundtrips_and_needs_fresh_physics(tmp_path):
    from autoengineering.adapters.python import run_lifecycle

    proposal = propose(specification())
    assert proposal.result.status in ("converged", "not_converged")
    assert proposal.configuration is not None
    assert WindNativeProposal.from_json(proposal.to_json()) == proposal
    geometry = proposal.specification.geometry
    ctx = geometry.context(proposal.configuration, tmp_path)
    fresh = run_lifecycle(geometry.adapter(), ctx, {}, (), ctx.model.outputs)
    assert fresh.outputs["annual_energy"] > 0
    assert fresh.outputs["minimum_spacing"] >= 320 - 1e-3
    assert proposal.eligibility == "fresh_evaluation_required"


def test_native_layout_outside_exact_domain_keeps_work_without_a_proposal():
    spec, r = specification(), result()
    raw = replace(r, x=(-0.0005, *r.x[1:]))
    value = WindNativeProposal("utility-wind-native-proposal-v1", spec, raw)
    assert value.result.feasible
    assert value.configuration is None
    assert value.work["wake"]["completed"] == 1
    assert value.work["gradient"]["failed"] == 1


def test_unresolved_callback_work_never_provides_a_configuration():
    raw = result()
    raw = replace(raw, calls=(replace(raw.calls[0], status="started", energy_gwh=None),))
    value = WindNativeProposal("utility-wind-native-proposal-v1", specification(), raw)
    assert value.configuration is None
    assert value.work["wake"]["unresolved"] == 1
