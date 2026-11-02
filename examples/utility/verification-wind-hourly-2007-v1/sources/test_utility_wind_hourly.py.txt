"""Hourly resource contracts and pre-model refusal with authored model outputs."""

from dataclasses import replace
import io
from types import SimpleNamespace

import numpy as np
import pytest

from autoengineering.campaign.artifacts import reference
from examples.utility import wind_hourly as hourly
from examples.utility.wind_parameters import WindGeometry


def task(year=2007):
    axis = hourly.utc_axis_for_year(year)
    return hourly.WindHourly(
        WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0)),
        year,
        axis,
        np.full(len(axis), 10.0),
        np.full(len(axis), 360.0),
        "a" * 64,
        "b" * 64,
    )


def test_inputs_copy_and_cannot_be_made_writable():
    source = np.full(8760, 10.0)
    profile = replace(task(), speed=source)
    identity = profile.identity
    source[:] = 20.0
    assert profile.speed[0] == 10.0
    assert profile.identity == identity
    with pytest.raises(ValueError):
        profile.speed.setflags(write=True)
    assert replace(profile, assumption_digest="c" * 64).identity != identity


@pytest.mark.parametrize(
    "change",
    ["nan", "negative", "shape", "direction", "year", "axis", "source", "assumption", "geometry"],
)
def test_invalid_inputs_refuse(change):
    profile = task()
    changes = {
        "nan": {"speed": np.full(8760, np.nan)},
        "negative": {"speed": np.full(8760, -1.0)},
        "shape": {"direction": np.ones(10)},
        "direction": {"direction": np.full(8760, 360.01)},
        "year": {"year": 2012},
        "axis": {"time_utc": profile.time_utc[::-1]},
        "source": {"point_sha256": ""},
        "assumption": {"assumption_digest": "approved"},
        "geometry": {"geometry": WindGeometry((0.0, 600.0), (0.0, 600.0))},
    }
    with pytest.raises(ValueError):
        replace(profile, **changes[change])


@pytest.mark.parametrize("case", ["forcing", "spacing", "bounds", "unknown", "boolean"])
def test_invalid_call_never_reaches_backend(monkeypatch, case):
    def denied():
        raise AssertionError("invalid input reached optional model runtime")

    monkeypatch.setattr(hourly, "_backend", denied)
    profile = task()
    config = profile.geometry.baseline
    forcing = {}
    if case == "forcing":
        forcing = {"ws": np.ones(8760)}
    elif case == "spacing":
        config["x_1"] = 0.0
    elif case == "bounds":
        config["x_0"] = -1.0
    elif case == "unknown":
        config["unknown"] = 1.0
    else:
        config["x_0"] = True
    with pytest.raises(ValueError):
        profile.physical(forcing, config)


def test_hourly_pairs_height_and_energy_have_no_cartesian_product(monkeypatch):
    profile = task()
    calls = []

    class Power:
        def transpose(self, *dims):
            assert dims == ("wt", "time")
            return SimpleNamespace(values=np.full((4, 8760), 1e6))

    def model(**kwargs):
        calls.append(kwargs)
        assert len(kwargs["ws"]) == len(kwargs["wd"]) == len(kwargs["time"]) == 8760
        assert np.all(kwargs["wd"] == 0.0)
        assert np.all(kwargs["h"] == 80.0)
        return SimpleNamespace(
            Power=Power(),
            time=SimpleNamespace(values=kwargs["time"]),
            h=SimpleNamespace(values=kwargs["h"]),
        )

    monkeypatch.setattr(hourly, "_backend", lambda: (model, None))
    outputs = profile.physical({}, profile.geometry.baseline)
    assert len(calls) == 1
    assert outputs["annual_energy"] == 35.04
    assert outputs["minimum_spacing"] == 600.0
    assert profile.direction[0] == 360.0


def test_leap_year_uses_actual_hour_count():
    profile = task(2008)
    assert len(profile.time_utc) == 8784
    outputs = profile.summarize(np.full((4, 8784), 1e6), profile.geometry.baseline)
    assert outputs["annual_energy"] == 35.136


@pytest.mark.parametrize(
    "power",
    [
        np.zeros((4, 1)),
        np.full((4, 8760), np.nan),
        np.full((4, 8760), -1.0),
        np.full((4, 8760), 2000001.0),
    ],
)
def test_power_validation(power):
    profile = task()
    with pytest.raises(ValueError, match="power"):
        profile.summarize(power, profile.geometry.baseline)


def point_arrays():
    return dict(
        time_utc=np.asarray(hourly.utc_axis_for_year(2007)),
        raw_speed=np.full(8760, 1000, dtype="<u2"),
        raw_direction=np.full(8760, 36000, dtype="<u2"),
        speed_m_s=np.full(8760, 10.0),
        direction_source_deg=np.full(8760, 360.0),
        speed_valid=np.ones(8760, dtype=bool),
        direction_valid=np.ones(8760, dtype=bool),
    )


@pytest.mark.parametrize(
    "change", ["none", "mask", "missing", "decoded", "shape", "extra", "object"]
)
def test_pinned_archive_headers_raw_decode_and_joint_support(tmp_path, change):
    values = point_arrays()
    if change == "mask":
        values["speed_valid"][0] = False
    elif change == "missing":
        values["raw_speed"][0] = 65535
        values["speed_valid"][0] = False
        values["speed_m_s"][0] = np.nan
    elif change == "decoded":
        values["speed_m_s"][0] = 11.0
    elif change == "shape":
        values["speed_m_s"] = np.ones(100)
    elif change == "extra":
        values["extra"] = np.ones(1)
    elif change == "object":
        values["time_utc"] = values["time_utc"].astype(object)
    stream = io.BytesIO()
    np.savez_compressed(stream, **values)
    (tmp_path / "point.npz").write_bytes(stream.getvalue())
    ref = reference(tmp_path, "point.npz", media_type="application/npz", producer="test")
    if change == "none":
        assert hourly.read_point(tmp_path, ref, 2007)["speed_m_s"][0] == 10.0
        (tmp_path / "point.npz").write_bytes(b"changed")
        with pytest.raises(ValueError):
            hourly.read_point(tmp_path, ref, 2007)
    else:
        with pytest.raises(ValueError):
            hourly.read_point(tmp_path, ref, 2007)


@pytest.mark.parametrize("changed", ["height", "time"])
def test_model_changed_support_refuses(monkeypatch, changed):
    profile = task()

    def model(**kwargs):
        axis = kwargs["time"].copy()
        height = kwargs["h"].copy()
        if changed == "height":
            height[:] = 70.0
        else:
            axis[0] += np.timedelta64(1, "h")
        return SimpleNamespace(time=SimpleNamespace(values=axis), h=SimpleNamespace(values=height))

    monkeypatch.setattr(hourly, "_backend", lambda: (model, None))
    with pytest.raises(ValueError, match="time support or hub height"):
        profile.physical({}, profile.geometry.baseline)
