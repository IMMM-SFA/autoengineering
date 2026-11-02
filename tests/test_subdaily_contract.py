"""Versioned subdaily contracts preserve UTC, gaps and power semantics."""
from dataclasses import replace

import pytest

from autoengineering.campaign.records import SubdailyTimeContract
from test_bmi_adapter import context


def axis():
    return SubdailyTimeContract(
        "2.0", ("2018-06-01T00:00:00Z", "2018-06-01T00:05:00Z", "2018-06-01T00:20:00Z"),
        "instantaneous", "PT5M", "proleptic_gregorian", "instant", "UTC", "restart_state",
        (True, True, True), (False, False, False),
    )


def test_subdaily_roundtrip_and_port_dispatch():
    value = axis()
    assert SubdailyTimeContract.from_json(value.to_json()) == value
    port = replace(context().model.inputs[0], time=value)
    assert type(port.from_json(port.to_json()).time) is SubdailyTimeContract
    daily = context().model.inputs[0]
    assert type(daily.from_json(daily.to_json()).time) is type(daily.time)


@pytest.mark.parametrize("changes", [
    {"dates": ("2018-06-01T00:00:00",)},
    {"dates": ("2018-06-01T00:00:00-06:00",)},
    {"dates": ("2018-06-01T00:03:00Z",)},
    {"dates": ("2018-06-01T00:00:00Z",) * 3},
    {"timestep": "P1D"}, {"semantics": "interval_total"},
    {"gap_policy": "interpolate"}, {"scoring_mask": (True, True, True)},
])
def test_unsupported_time_semantics_reject(changes):
    with pytest.raises(ValueError):
        replace(axis(), **changes)
