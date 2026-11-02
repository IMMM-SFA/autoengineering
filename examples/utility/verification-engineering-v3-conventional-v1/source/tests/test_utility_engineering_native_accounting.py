"""Native pass accounting preserves bootstrap and stale-state distinctions."""

from dataclasses import replace

import pytest

from examples.utility.engineering_native_accounting import account_circuit_pass, CircuitPassWork


def test_unchanged_counters_do_not_recharge_retained_solver_iterations():
    counters = {"component_calls": 100, "component_linearize_calls": 20}
    record = account_circuit_pass(counters, counters, diagnostic_solver_iterations=13)
    assert record.circuit_work_observed is False
    assert record.nonlinear_iterations_this_pass == 0
    assert record.design_eligibility == "not_assessed"
    assert counters == {"component_calls": 100, "component_linearize_calls": 20}
    assert CircuitPassWork.from_json(record.to_json()) == record
    with pytest.raises(ValueError):
        replace(record, nonlinear_iterations_this_pass=13)


def test_deltas_keep_native_lifetime_counters_separate():
    record = account_circuit_pass(
        {"component_calls": 100, "component_linearize_calls": 20},
        {"component_calls": 130, "component_linearize_calls": 25},
        diagnostic_solver_iterations=4,
    )
    assert (record.component_calls, record.component_linearize_calls) == (30, 5)
    assert record.nonlinear_iterations_this_pass == 4
    assert record.circuit_work_observed and record.design_eligibility == "not_assessed"


def test_saved_failed_profile_is_a_no_circuit_work_pass():
    # No ignored output is required for this regression; the observed values are
    # explicit and will also be checked against archived evidence at handoff.
    before = {"component_calls": 0, "component_linearize_calls": 0}
    record = account_circuit_pass(before, before, diagnostic_solver_iterations=0)
    assert not record.circuit_work_observed
    assert record.design_eligibility == "not_assessed"
    assert record.component_calls == record.component_linearize_calls == 0


@pytest.mark.parametrize(
    "before,after,iterations",
    [
        (
            {"component_calls": 2, "component_linearize_calls": 1},
            {"component_calls": 1, "component_linearize_calls": 1},
            3,
        ),
        (
            {"component_calls": 0, "component_linearize_calls": 0},
            {"component_calls": True, "component_linearize_calls": 1},
            3,
        ),
        (
            {"component_calls": 0, "component_linearize_calls": 0},
            {"component_calls": 1.0, "component_linearize_calls": 1},
            3,
        ),
        (
            {"component_calls": 0, "component_linearize_calls": 0},
            {"component_calls": 1, "component_linearize_calls": 1},
            True,
        ),
        (
            {"component_calls": 0, "component_linearize_calls": 0},
            {"component_calls": 1, "component_linearize_calls": 1},
            -1,
        ),
        (
            {"component_calls": 0, "component_linearize_calls": 0},
            {"component_calls": 1, "component_linearize_calls": 1, "extra": 0},
            1,
        ),
    ],
)
def test_unknown_or_reset_counters_refuse(before, after, iterations):
    with pytest.raises(ValueError):
        account_circuit_pass(before, after, diagnostic_solver_iterations=iterations)
