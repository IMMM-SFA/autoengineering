"""Round-trip contracts at continuous parameter boundaries."""

from __future__ import annotations

import math

import pytest

from autoengineering.optimization import ContinuousParameter, SearchSpace


@pytest.mark.parametrize(
    "lower,upper,scale", [(1e-8, 0.1, "log"), (0.1, 10.0, "log"), (-1.0, 0.1, "linear")]
)
def test_decoded_endpoints_remain_exact_valid_bounds(lower, upper, scale):
    space = SearchSpace((ContinuousParameter("x", lower, upper, scale=scale),))
    for unit, expected in [(0.0, lower), (1.0, upper)]:
        decoded = space.decode((unit,))
        assert decoded["x"] == expected
        assert space.encode(decoded) == (unit,)
    for unit in [math.nextafter(0.0, 1.0), math.nextafter(1.0, 0.0), 0.5]:
        decoded = space.decode((unit,))
        assert lower <= decoded["x"] <= upper
        space.encode(decoded)
    for invalid in [math.nextafter(lower, -math.inf), math.nextafter(upper, math.inf)]:
        with pytest.raises(ValueError, match="within"):
            space.encode({"x": invalid})
