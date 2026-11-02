"""Source point geometry, calendar and decoding use no wind performance feedback."""

from datetime import datetime, timedelta
import numpy as np
import pytest

from examples.utility.wind_point import nearest_site, utc_axis, decode_variable


def test_nearest_is_chunk_independent_with_first_index_ties():
    data = np.array([[41.5, -70.6], [41.5, -70.5], [41.5, -70.5], [40, -70]])
    whole = nearest_site([data], 41.5, -70.5)
    split = nearest_site([data[:1], data[1:3], data[3:]], 41.5, -70.5)
    assert whole == split and whole["index"] == 1 and whole["distance_m"] == 0
    np.testing.assert_array_equal(data[1], [41.5, -70.5])


def test_nearest_wraps_antimeridian_and_rejects_bad_source():
    assert nearest_site([[[0, 170], [0, -179.9]]], 0, 179.9)["index"] == 1
    for blocks in ([], [[[91, 0]]], [[[0, float("nan")]]], [[[1, 2, 3]]]):
        with pytest.raises(ValueError):
            nearest_site(blocks, 0, 0)


@pytest.mark.parametrize("year,hours", [(2007, 8760), (2008, 8784)])
def test_complete_declared_utc_calendar_including_leap_year(year, hours):
    values = [
        (datetime(year, 1, 1) + timedelta(hours=i)).isoformat().encode() for i in range(hours)
    ]
    result = utc_axis(values, year, "UTC")
    assert len(result) == hours and result[0] == f"{year}-01-01T00:00:00Z"
    assert result[-1] == f"{year}-12-31T23:00:00Z"
    with pytest.raises(ValueError):
        utc_axis(values[:-1], year, "UTC")
    values[1] = values[0]
    with pytest.raises(ValueError):
        utc_axis(values, year, "UTC")


def test_unknown_timezone_or_reserved_year_refuses():
    with pytest.raises(ValueError):
        utc_axis([], 2007, "PST")
    with pytest.raises(ValueError):
        utc_axis([], 2012, "UTC")


def test_raw_fill_is_masked_before_division_and_direction_is_preserved():
    original = np.array([0, 1234, 65535], dtype=np.uint16)
    values, mask = decode_variable(
        original, kind="speed", units="m s-1", scale_factor=100.0, fill_value=65535
    )
    np.testing.assert_allclose(values[:2], [0, 12.34])
    assert np.isnan(values[2])
    assert list(mask) == [True, True, False] and original[-1] == 65535
    values, _ = decode_variable(
        np.array([0, 36000], dtype=np.uint16),
        kind="direction",
        units="degree",
        scale_factor=100.0,
        fill_value=65535,
    )
    np.testing.assert_array_equal(values, [0, 360])


@pytest.mark.parametrize("change", [{"units": "mph"}, {"scale_factor": 0.01}, {"fill_value": -1}])
def test_unreviewed_source_conventions_refuse(change):
    args = dict(kind="speed", units="m s-1", scale_factor=100.0, fill_value=65535)
    args.update(change)
    with pytest.raises(ValueError):
        decode_variable(np.array([12], dtype=np.uint16), **args)


def test_out_of_domain_values_are_not_clipped_into_valid_weather():
    for kind, units, raw in [("speed", "m s-1", 10001), ("direction", "degree", 36001)]:
        with pytest.raises(ValueError):
            decode_variable(
                np.array([raw], dtype=np.uint16),
                kind=kind,
                units=units,
                scale_factor=100.0,
                fill_value=65535,
            )
