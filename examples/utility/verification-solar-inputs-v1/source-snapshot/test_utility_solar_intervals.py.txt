"""Analytic solar support, causal-driver and interval-energy checks on authored rows."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import socket
import subprocess

import pytest

from examples.utility import solar_intervals as module


def t(minutes):
    return (
        (datetime(2021, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes))
        .isoformat()
        .replace("+00:00", "Z")
    )


def avg(start, end, value, *, available=None, quality=True):
    return module.AverageValue(
        t(start), t(end), t(end if available is None else available), value, quality
    )


def sample(at, value, *, available=None, quality=True):
    return module.DriverSample(t(at), t(at if available is None else available), value, quality)


def plan(**kwargs):
    return replace(
        module.SolarAlignmentPlan(
            "utility-solar-interval-alignment-v1",
            "1" * 64,
            "2" * 64,
            t(0),
            t(15),
            900,
            900,
            "F",
            "mph",
            "causal_hold",
        ),
        **kwargs,
    )


def rows(p=None, **kwargs):
    values = dict(
        ac=[avg(0, 5, 1), avg(5, 10, 2), avg(10, 15, 3)],
        poa=[avg(0, 15, 600)],
        temperature=[sample(0, 68)],
        wind=[sample(0, 10)],
    )
    values.update(kwargs)
    return list(module.align(p or plan(), **values))


def test_energy_conserving_coarsening_and_unit_conversions():
    (row,) = rows()
    assert row.usable and row.reasons == ()
    assert row.ac_kw == pytest.approx(2)
    assert row.ac_energy_kwh == pytest.approx(sum(v * 5 / 60 for v in (1, 2, 3)))
    assert row.poa_w_m2 == pytest.approx(600)
    assert row.temperature_c == pytest.approx(20)
    assert row.wind_m_s == pytest.approx(4.4704)
    assert row.duration_seconds == 900 and row.start == t(0) and row.end == t(15)
    assert module.AlignedInterval.from_json(row.to_json()) == row


def test_variable_source_support_is_duration_weighted():
    (row,) = rows(ac=[avg(0, 5, 1), avg(5, 15, 3)])
    assert row.ac_kw == pytest.approx(7 / 3)
    assert row.ac_energy_kwh == pytest.approx(1 * 5 / 60 + 3 * 10 / 60)


def test_samples_are_used_only_after_availability_and_end_point_has_zero_weight():
    (row,) = rows(temperature=[sample(0, 32), sample(5, 122, available=10), sample(15, 999)])
    assert row.temperature_c == pytest.approx(50 / 3)  # Zero until minute 10, then 50 C.
    (row,) = rows(temperature=[sample(0, 32), sample(5, 212), sample(15, 999)])
    assert row.temperature_c == pytest.approx(200 / 3)


def test_coarse_averages_cannot_be_disaggregated_to_fake_finer_rows():
    values = rows(plan(step_seconds=300), ac=[avg(0, 15, 2)])
    assert len(values) == 3
    assert all(not r.usable and "ac:support_crosses_target" in r.reasons for r in values)
    assert all(
        r.ac_kw is r.ac_energy_kwh is r.poa_w_m2 is r.temperature_c is r.wind_m_s is None
        for r in values
    )


@pytest.mark.parametrize(
    "kwargs,reason",
    [
        ({"ac": [avg(0, 5, 1), avg(10, 15, 3)]}, "ac:gap"),
        ({"ac": [avg(0, 15, 2, available=16)]}, "ac:late_available"),
        ({"ac": [avg(0, 15, None, quality=False)]}, "ac:quality"),
        ({"temperature": [sample(15, 68)]}, "temperature:no_available_sample"),
        ({"wind": [sample(0, -1), sample(5, 10)]}, "wind:below_domain"),
        ({"poa": [avg(0, 5, -1), avg(5, 15, 600)]}, "poa:below_domain"),
    ],
)
def test_missing_late_or_invalid_channel_blocks_common_score(kwargs, reason):
    (row,) = rows(**kwargs)
    assert not row.usable and reason in row.reasons
    assert row.ac_kw is row.ac_energy_kwh is None
    if reason.startswith("ac:"):
        assert row.drivers_usable
        assert all(v is not None for v in (row.poa_w_m2, row.temperature_c, row.wind_m_s))
    else:
        assert not row.drivers_usable
        assert row.poa_w_m2 is row.temperature_c is row.wind_m_s is None


def test_sample_age_boundary_is_inclusive_and_stale_rows_are_masked():
    assert rows(plan(max_sample_age_seconds=900))[0].usable
    (row,) = rows(plan(max_sample_age_seconds=899))
    assert not row.usable and "wind:stale_sample" in row.reasons


def test_overlapping_averages_and_reversed_sample_availability_refuse():
    with pytest.raises(ValueError, match="overlap"):
        rows(ac=[avg(0, 10, 1), avg(5, 15, 1)])
    with pytest.raises(ValueError, match="ordered"):
        rows(temperature=[sample(0, 68, available=10), sample(5, 68, available=5)])
    with pytest.raises(ValueError, match="duplicate"):
        rows(wind=[sample(0, 1), sample(0, 2)])


def test_ambiguous_local_clock_and_fractional_seconds_refuse():
    for value in ("2021-11-07T01:30:00", "PST8PDT", "2021-01-01T00:00:00.1Z"):
        with pytest.raises(ValueError, match="explicit offsets"):
            module.instant(value)
    first = module.instant("2021-11-07T01:30:00-07:00")
    second = module.instant("2021-11-07T01:30:00-08:00")
    assert (second - first).total_seconds() == 3600


def test_bounded_source_ingestion_and_target_count(monkeypatch):
    monkeypatch.setattr(module, "MAX_SOURCE_ROWS", 1)
    with pytest.raises(ValueError, match="row bound"):
        rows()
    monkeypatch.setattr(module, "MAX_SOURCE_ROWS", 100)
    monkeypatch.setattr(module, "MAX_TOTAL_SOURCE_ROWS", 3)
    with pytest.raises(ValueError, match="row bound"):
        rows(ac=[avg(0, 15, 2)])
    with pytest.raises(ValueError, match="bounded whole"):
        plan(end="2030-01-01T00:00:00Z", step_seconds=60)


def test_negative_standby_is_retained_for_later_equipment_checks():
    (row,) = rows(ac=[avg(0, 15, -0.01)])
    assert row.usable and row.ac_kw == -0.01
    assert row.ac_energy_kwh == pytest.approx(-0.0025)


def test_masks_cannot_retain_scoring_values_or_hide_missing_forcing():
    (row,) = rows(ac=[avg(0, 15, None, quality=False)])
    with pytest.raises(ValueError, match="common score masks"):
        replace(row, ac_kw=1.0)
    with pytest.raises(ValueError, match="common score masks"):
        replace(row, wind_m_s=None)
    (good,) = rows()
    with pytest.raises(ValueError, match="energy"):
        replace(good, ac_energy_kwh=99.0)


def test_alignment_is_immutable_and_starts_no_process_or_network(monkeypatch):
    ac = [avg(0, 15, 2)]
    original = ac[0].to_json()
    progress = []

    def forbidden(*args, **kwargs):
        pytest.fail("alignment attempted execution or network")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    values = list(
        module.align(
            plan(),
            ac=ac,
            poa=[avg(0, 15, 600)],
            temperature=[sample(0, 68)],
            wind=[sample(0, 10)],
            on_progress=progress.append,
        )
    )
    assert values[0].usable and progress == [1]
    assert ac[0].to_json() == original


def test_missing_observations_preserve_driver_continuity():
    values = rows(
        plan(end=t(30)),
        ac=[avg(0, 15, None, quality=False), avg(15, 30, 2)],
        poa=[avg(0, 15, 600), avg(15, 30, 500)],
        temperature=[sample(0, 68), sample(15, 70)],
        wind=[sample(0, 10), sample(15, 11)],
    )
    assert [r.drivers_usable for r in values] == [True, True]
    assert [r.usable for r in values] == [False, True]
    assert values[0].ac_kw is values[0].ac_energy_kwh is None
    assert values[0].temperature_c == pytest.approx(20)
    assert values[1].temperature_c == pytest.approx((70 - 32) * 5 / 9)
