"""Trusted routing fixture: the upstream drivers are saved Part 1 evidence.

This is a routing accounting example, not a complete catchment water balance.
"""

from __future__ import annotations

import numpy as np

from autoengineering.adapters.python import PythonAdapter
from examples.leaf_river.models.routing import route_streamflow
from examples.leaf_river.models.routing_calibrated import route_streamflow_calibrated


PARAMETERS = {
    "triangular": {
        "family": "triangular",
        "uh_peak": 3,
        "gamma_shape": 2.5,
        "gamma_scale": 1.5,
        "k_base": 0.8099801635742188,
        "recharge_frac": 0.04457894548773765,
        "uh_length": 10,
    },
    "gamma": {
        "family": "gamma",
        "uh_peak": 3,
        "gamma_shape": 2.5,
        "gamma_scale": 1.5,
        "k_base": 0.92,
        "recharge_frac": 0.03,
        "uh_length": 15,
    },
}


def validate(parameters):
    family = parameters.get("family")
    if family not in PARAMETERS or set(parameters) != set(PARAMETERS[family]):
        raise ValueError("invalid routing parameter interface")
    bounds = {
        "uh_peak": (1, 8),
        "gamma_shape": (1.1, 5),
        "gamma_scale": (0.5, 3),
        "k_base": (0.5, 0.98),
        "recharge_frac": (0, 0.12),
        "uh_length": (10, 15),
    }
    for name, (low, high) in bounds.items():
        value = parameters[name]
        if type(value) not in (float, int) or not np.isfinite(value) or not low <= value <= high:
            raise ValueError("routing parameter outside declared bounds")
    if type(parameters["uh_peak"]) is not int or type(parameters["uh_length"]) is not int:
        raise ValueError("routing kernel length/peak must be integers")


def run(forcing, parameters):
    family = parameters["family"]
    function = route_streamflow if family == "triangular" else route_streamflow_calibrated
    names = ("uh_peak",) if family == "triangular" else ("gamma_shape", "gamma_scale")
    config = {name: parameters[name] for name in (*names, "k_base", "recharge_frac", "uh_length")}
    return {
        "prediction": function(
            forcing["runoff"].copy(), precip=forcing["recharge"].copy(), **config
        )
    }


def adapter():
    return PythonAdapter(run, validate)
