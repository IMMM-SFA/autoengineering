"""Finite numeric stress drivers preserve the frozen fitting prefix and ownership."""

import math

import numpy as np
import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import guest_numeric_control as module


def forcing():
    return {
        "precip_mm": np.full(6, 2.0),
        "tmin_c": np.full(6, 10.0),
        "tmean_c": np.full(6, 15.0),
        "tmax_c": np.full(6, 20.0),
        "day_of_year": np.arange(1, 7),
    }


def test_stress_changes_only_temperature_suffix_and_never_original_arrays():
    original = forcing()
    before = {k: v.copy() for k, v in original.items()}
    result = module.overflow_suffix(original, 4)
    for name, value in result.items():
        assert np.isfinite(value).all()
        np.testing.assert_array_equal(value[:4], original[name][:4])
        np.testing.assert_array_equal(before[name], original[name])
        assert not np.shares_memory(value, original[name])
        if name in module.TEMPERATURES:
            np.testing.assert_array_equal(value[4:], module.TEMPERATURES[name])
        else:
            np.testing.assert_array_equal(value, original[name])
    assert (result["tmin_c"] <= result["tmean_c"]).all()
    assert (result["tmean_c"] <= result["tmax_c"]).all()
    # The fixed Hamon implementation has exp(0.062 * mean temperature).
    # This analytic overflow check executes no scientific model or fitting.
    with pytest.raises(OverflowError):
        math.exp(0.062 * module.TEMPERATURES["tmean_c"])


@pytest.mark.parametrize("prefix", [0, 6, 7, -1, True, 1.0])
def test_missing_suffix_and_noninteger_prefix_refuse(prefix):
    with pytest.raises(ValueError):
        module.overflow_suffix(forcing(), prefix)


@pytest.mark.parametrize(
    "kind", ["nan", "shape", "length", "object", "missing", "negative_precip", "order"]
)
def test_invalid_original_input_never_becomes_a_stress_fixture(kind):
    values = forcing()
    if kind == "nan":
        values["tmean_c"][0] = float("nan")
    elif kind == "shape":
        values["tmax_c"] = np.ones((2, 3))
    elif kind == "length":
        values["tmax_c"] = np.ones(5)
    elif kind == "object":
        values["tmax_c"] = np.array(["20"] * 6, dtype=object)
    elif kind == "missing":
        values.pop("tmax_c")
    elif kind == "negative_precip":
        values["precip_mm"][0] = -1
    elif kind == "order":
        values["tmax_c"][0] = 0
    with pytest.raises(ValueError):
        module.overflow_suffix(values, 4)


def test_consumed_request_refuses_before_loading_drivers_or_runtime(tmp_path, monkeypatch):
    control = {
        "schema": "utility-guest-numeric-control-v1",
        "scope_digest": digest(str(tmp_path)),
        "sources": module.helper_sources(),
        "limits": module.LIMITS,
    }
    module.fixture.save(tmp_path, "numeric-request.json", control)
    (tmp_path / "numeric-execution-intent.json").write_text("{}")
    monkeypatch.setattr(
        module, "GuestDaemonAPI", lambda *a, **kw: pytest.fail("runtime constructed")
    )
    with pytest.raises(module.StoreError, match="consumed"):
        module.execute(tmp_path, expected_digest=digest(control))
