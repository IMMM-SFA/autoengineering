"""Annual comparisons preserve source strata, year coverage and failure states."""

from dataclasses import replace
import builtins
import socket
import subprocess

import pytest

from examples.utility.wind_annual import (
    AnnualWindPlan,
    AnnualWindResult,
    AnnualWindRun,
    AnnualWindSource,
    compare_annual,
)


def plan():
    return AnnualWindPlan(
        "utility-wind-annual-plan-v1",
        tuple(
            AnnualWindSource(
                year,
                "v1.1.0" if year == 2014 else "v1.0.0",
                f"conus/{'v1.1.0' if year == 2014 else 'v1.0.0'}/wtk_conus_{year}.h5",
                str(year % 10) * 64,
                str(year % 10 + 1) * 64,
            )
            for year in (2012, 2013, 2014)
        ),
        "a" * 64,
        "b" * 64,
        "c" * 64,
    )


def run(spec, values, configuration="d"):
    return AnnualWindRun(
        "utility-wind-annual-run-v1",
        spec.digest,
        configuration * 64,
        tuple(
            AnnualWindResult(source.year, source.digest, "success", value)
            for source, value in zip(spec.sources, values, strict=True)
        ),
    )


def test_versions_are_stratified_without_dropping_2014_or_weighting_versions_equally():
    spec = plan()
    result = compare_annual(
        spec,
        run(spec, (20, 20, 20)),
        run(spec, (21, 23, 29), "e"),
        maximum_yearly_degradation=0.02,
    )
    assert result["overall"]["years"] == [2012, 2013, 2014]
    assert result["overall"]["candidate_mean_annual_energy_gwh"] == pytest.approx(73 / 3)
    assert result["by_source_version"]["v1.0.0"]["mean_gain_gwh"] == 2
    assert result["by_source_version"]["v1.1.0"]["mean_gain_gwh"] == 9
    assert result["overall"]["mean_gain_gwh"] == pytest.approx(13 / 3)
    assert result["useful_improvement_decided"] is result["task_admitted"] is False
    assert AnnualWindPlan.from_json(spec.to_json()) == spec


def test_positive_mean_cannot_hide_a_year_exceeding_degradation_limit():
    spec = plan()
    result = compare_annual(
        spec,
        run(spec, (20, 20, 20)),
        run(spec, (22, 19, 22)),
        maximum_yearly_degradation=0.02,
    )
    assert result["overall"]["mean_gain_gwh"] == 1
    assert result["overall"]["all_years_degradation_passed"] is False
    assert result["annual"][1]["degradation_passed"] is False


@pytest.mark.parametrize("candidate_failed", [True, False])
@pytest.mark.parametrize(
    "status", ["model_failure", "scientific_infeasible", "timeout", "infrastructure_failure"]
)
def test_unsuccessful_year_is_retained_and_never_imputed_or_dropped(status, candidate_failed):
    spec = plan()
    good = run(spec, (20, 20, 20))
    results = list(good.results)
    results[1] = replace(results[1], status=status, energy_gwh=None)
    failed = replace(good, results=tuple(results))
    baseline, candidate = (good, failed) if candidate_failed else (failed, good)
    result = compare_annual(spec, baseline, candidate, maximum_yearly_degradation=0.02)
    assert len(result["annual"]) == 3
    assert result["overall"]["mean_gain_gwh"] is None
    assert result["overall"]["complete"] is False
    assert result["by_source_version"]["v1.0.0"]["candidate_mean_annual_energy_gwh"] is None
    assert result["by_source_version"]["v1.1.0"]["complete"] is True
    assert result["overall"]["all_years_degradation_passed"] is False


@pytest.mark.parametrize("change", ["missing", "identity", "plan", "other_plan"])
def test_annual_binding_refuses_unpaired_sources(change):
    spec = plan()
    original = run(spec, (20, 20, 20))
    changed = original
    if change == "missing":
        changed = replace(original, results=original.results[:-1])
    elif change == "identity":
        changed = replace(
            original,
            results=(replace(original.results[0], source_digest="f" * 64), *original.results[1:]),
        )
    elif change == "plan":
        changed = replace(original, plan_digest="f" * 64)
    else:
        spec = replace(spec, interpretation_digest="f" * 64)
    with pytest.raises(ValueError):
        compare_annual(spec, original, changed, maximum_yearly_degradation=0.02)


@pytest.mark.parametrize("year", [2006, 2015, True])
def test_unknown_source_year_refuses(year):
    with pytest.raises(ValueError):
        replace(plan().sources[0], year=year)


def test_wrong_version_object_duplicate_or_out_of_order_years_refuse():
    spec = plan()
    for change in ({"source_version": "v1.1.0"}, {"object_key": "other.h5"}):
        with pytest.raises(ValueError):
            replace(spec.sources[0], **change)
    for sources in ((), spec.sources[::-1], (spec.sources[0], spec.sources[0])):
        with pytest.raises(ValueError):
            replace(spec, sources=sources)
    original = run(spec, (20, 20, 20))
    with pytest.raises(ValueError):
        replace(original, results=original.results[::-1])


@pytest.mark.parametrize("energy", [True, -1, float("nan"), float("inf"), 71])
def test_nonphysical_energy_and_unsuccessful_values_refuse(energy):
    item = run(plan(), (20, 20, 20)).results[0]
    with pytest.raises(ValueError):
        replace(item, energy_gwh=energy)
    with pytest.raises(ValueError):
        replace(item, status="model_failure")


def test_leap_year_duration_and_zero_reference_have_explicit_semantics():
    spec = plan()
    item = run(spec, (0, 0, 0)).results[0]
    replace(item, energy_gwh=70.272)
    with pytest.raises(ValueError):
        replace(run(spec, (0, 0, 0)).results[1], energy_gwh=70.272)
    result = compare_annual(
        spec,
        run(spec, (0, 0, 0)),
        run(spec, (0, 1, 2)),
        maximum_yearly_degradation=0.02,
    )
    assert result["overall"]["all_years_degradation_passed"] is True
    assert result["overall"]["mean_gain_gwh"] == 1


@pytest.mark.parametrize("limit", [True, -0.01, 1, float("nan"), float("inf")])
def test_tolerance_must_be_explicit_finite_fraction(limit):
    spec = plan()
    with pytest.raises(ValueError):
        compare_annual(
            spec, run(spec, (20, 20, 20)), run(spec, (20, 20, 20)), maximum_yearly_degradation=limit
        )


def test_comparison_never_dispatches_or_imports_optional_models(monkeypatch):
    spec = plan()
    baseline = run(spec, (20, 20, 20))
    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name.startswith(("py_wake", "h5py", "pandas", "examples.utility.wind_hourly")):
            raise AssertionError("annual metadata imported a source or model runtime")
        return original_import(name, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("annual metadata attempted source access or execution")

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    result = compare_annual(spec, baseline, baseline, maximum_yearly_degradation=0.02)
    assert result["overall"]["mean_gain_gwh"] == 0
