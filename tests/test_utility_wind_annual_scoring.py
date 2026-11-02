"""Trusted annual wind kernel consumes authored drivers without private source access."""

from dataclasses import replace
import json
from types import SimpleNamespace

import numpy as np
import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import wind_annual_scoring as module
from examples.utility.wind_annual import AnnualWindPlan, AnnualWindSource, compare_annual
from examples.utility.wind_parameters import WindGeometry


def inputs(years=(2012, 2013, 2014)):
    geometry = WindGeometry((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0))
    drivers = tuple(
        module.AnnualWindDrivers(
            year,
            str(year % 10) * 64,
            module._axis(year),
            np.full(len(module._axis(year)), 10.0),
            np.full(len(module._axis(year)), 360.0),
        )
        for year in years
    )
    sources = tuple(
        AnnualWindSource(
            data.year,
            "v1.1.0" if data.year == 2014 else "v1.0.0",
            f"conus/{'v1.1.0' if data.year == 2014 else 'v1.0.0'}/wtk_conus_{data.year}.h5",
            data.object_identity_digest,
            data.manifest_digest,
        )
        for data in drivers
    )
    plan = AnnualWindPlan(
        "utility-wind-annual-plan-v1",
        sources,
        module.model_identity(),
        geometry.digest,
        digest(module.INTERPRETATION),
    )
    policy = module.AnnualWindScorePolicy(
        "utility-wind-annual-score-v1",
        module.source_identity(),
        plan.model_digest,
        plan.digest,
    )
    return geometry, plan, drivers, policy


def evaluate(root, args):
    geometry, plan, drivers, policy = args
    return module.score_annual(
        geometry.baseline,
        geometry,
        plan,
        drivers,
        root,
        policy=policy,
        execution_digest="f" * 64,
    )


def backend(calls, root, *, failure=None, changed=None):
    def build():
        def model(**kwargs):
            index = len(calls)
            assert (root / f"{index:02d}-start.json").exists()
            assert np.all(kwargs["wd"] == 0)
            assert np.all(kwargs["h"] == 80)
            assert len(kwargs["ws"]) == len(kwargs["time"])
            calls.append(kwargs)
            if failure and index == 1:
                raise failure("private forcing, path or input must not escape")
            power = np.full((4, len(kwargs["time"])), 1e6)
            if changed == "power":
                power[:] = 3e6
            return SimpleNamespace(
                time=SimpleNamespace(
                    values=kwargs["time"][::-1] if changed == "time" else kwargs["time"]
                ),
                h=SimpleNamespace(values=np.full(4, 90 if changed == "height" else 80)),
                Power=SimpleNamespace(transpose=lambda *dims: SimpleNamespace(values=power)),
            )

        return model, None

    return build


def test_all_declared_years_execute_once_with_actual_duration_and_source_binding(
    tmp_path, monkeypatch
):
    tmp_path.chmod(0o700)
    calls = []
    monkeypatch.setattr(module.wind_hourly, "_backend", backend(calls, tmp_path))
    args = inputs()
    result = evaluate(tmp_path, args)
    assert len(calls) == result.attempted_model_starts == result.completed_model_starts == 3
    assert [len(call["ws"]) for call in calls] == [8784, 8760, 8760]
    assert result.score.value == pytest.approx((35.136 + 35.04 + 35.04) / 3)
    assert result.score.status == "success"
    assert result.last_attempt_work_unknown is False
    comparison = compare_annual(args[1], result.run, result.run, maximum_yearly_degradation=0.02)
    assert comparison["overall"]["mean_gain_gwh"] == 0
    with pytest.raises(ValueError, match="consumed"):
        evaluate(tmp_path, args)
    assert len(calls) == 3
    # No hourly inputs or power vectors are written, even in the private journal.
    for path in tmp_path.iterdir():
        text = path.read_text()
        assert "speed_m_s" not in text and "direction_deg" not in text
    assert json.loads((tmp_path / "complete.json").read_text())["inner_solver_work"] is None


@pytest.mark.parametrize(
    "failure,status",
    [
        (RuntimeError, "model_failure"),
        (TimeoutError, "timeout"),
        (ImportError, "infrastructure_failure"),
    ],
)
def test_failure_keeps_charge_unknown_work_and_unattempted_years(
    tmp_path, monkeypatch, failure, status
):
    tmp_path.chmod(0o700)
    calls = []
    monkeypatch.setattr(module.wind_hourly, "_backend", backend(calls, tmp_path, failure=failure))
    result = evaluate(tmp_path, inputs())
    assert len(calls) == result.attempted_model_starts == 2
    assert result.completed_model_starts == 1
    assert [item.status for item in result.run.results] == ["success", status, "not_attempted"]
    assert result.score.status == status
    assert result.score.value is result.score.feasible is None
    assert result.last_attempt_work_unknown is True
    assert not (tmp_path / "02-start.json").exists()
    assert all("must not escape" not in path.read_text() for path in tmp_path.iterdir())


@pytest.mark.parametrize("change", ["power", "time", "height"])
def test_invalid_physics_has_no_penalty_or_later_model_start(tmp_path, monkeypatch, change):
    tmp_path.chmod(0o700)
    calls = []
    monkeypatch.setattr(module.wind_hourly, "_backend", backend(calls, tmp_path, changed=change))
    result = evaluate(tmp_path, inputs())
    assert len(calls) == result.attempted_model_starts == 1
    assert result.score.status == "scientific_infeasible"
    assert result.score.value is None and result.score.feasible is False
    assert [item.status for item in result.run.results] == [
        "scientific_infeasible",
        "not_attempted",
        "not_attempted",
    ]


@pytest.mark.parametrize(
    "change", ["policy", "source", "interpretation", "missing", "order", "geometry", "payload"]
)
def test_preflight_mismatch_cannot_import_or_start_optional_model(tmp_path, monkeypatch, change):
    tmp_path.chmod(0o700)
    geometry, plan, drivers, policy = inputs()
    if change == "policy":
        policy = replace(policy, scorer_source_digest="a" * 64)
    elif change == "source":
        drivers = (replace(drivers[0], object_identity_digest="a" * 64), *drivers[1:])
    elif change == "interpretation":
        plan = replace(plan, interpretation_digest="a" * 64)
        policy = replace(policy, plan_digest=plan.digest)
    elif change == "missing":
        drivers = drivers[:-1]
    elif change == "order":
        drivers = drivers[::-1]
    elif change == "geometry":
        geometry = WindGeometry((0.0, 800.0, 0.0, 800.0), geometry.y)
    else:
        drivers = (replace(drivers[0], speed_m_s=np.full(8784, 11.0)), *drivers[1:])

    def denied():
        pytest.fail("invalid annual input reached optional model backend")

    monkeypatch.setattr(module.wind_hourly, "_backend", denied)
    with pytest.raises(ValueError):
        evaluate(tmp_path, (geometry, plan, drivers, policy))
    assert not list(tmp_path.iterdir())


def test_driver_arrays_are_copied_read_only_and_boolean_vectors_refuse():
    data = inputs((2007,))[2][0]
    source = np.full(8760, 10.0)
    copied = replace(data, speed_m_s=source)
    identity = copied.manifest_digest
    source[:] = 30
    assert copied.manifest_digest == identity
    with pytest.raises(ValueError):
        copied.speed_m_s.setflags(write=True)
    for change in (
        {"speed_m_s": np.ones(8760, dtype=bool)},
        {"direction_deg": np.full(8760, np.nan)},
        {"time_utc": data.time_utc[::-1]},
    ):
        with pytest.raises(ValueError):
            replace(data, **change)


def test_development_reader_still_refuses_reserved_years():
    with pytest.raises(ValueError, match="development"):
        module.wind_hourly.utc_axis_for_year(2012)


def test_invalid_selected_layout_refuses_before_model_or_journal(tmp_path, monkeypatch):
    tmp_path.chmod(0o700)
    geometry, plan, drivers, policy = inputs()
    configuration = geometry.baseline
    configuration["x_1"] = 0

    def denied():
        pytest.fail("invalid selected layout entered the annual backend")

    monkeypatch.setattr(module.wind_hourly, "_backend", denied)
    with pytest.raises(ValueError):
        module.score_annual(
            configuration,
            geometry,
            plan,
            drivers,
            tmp_path,
            policy=policy,
            execution_digest="f" * 64,
        )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("lost_name,starts", [("00-result.json", 1), ("complete.json", 3)])
def test_publication_failure_never_allows_a_model_retry(tmp_path, monkeypatch, lost_name, starts):
    tmp_path.chmod(0o700)
    calls = []
    monkeypatch.setattr(module.wind_hourly, "_backend", backend(calls, tmp_path))
    original = module.durable_write

    def lose_publication(path, data, **kwargs):
        if path.name == lost_name:
            raise OSError("authored durable publication loss")
        return original(path, data, **kwargs)

    monkeypatch.setattr(module, "durable_write", lose_publication)
    args = inputs()
    with pytest.raises(OSError, match="publication loss"):
        evaluate(tmp_path, args)
    assert len(calls) == starts
    assert (tmp_path / "00-start.json").exists()
    assert not (tmp_path / "complete.json").exists()
    monkeypatch.setattr(module, "durable_write", original)
    with pytest.raises(ValueError, match="consumed"):
        evaluate(tmp_path, args)
    assert len(calls) == starts
