"""Existing pvlib/OEDI physics with explicit supplied thermal/loss alternatives."""
from __future__ import annotations

import numpy as np

from autoengineering.adapters.python import PythonAdapter
from examples.open_chains.solar import models


def validate(parameters):
    if set(parameters) != {"method", "u0", "u1", "dc_loss_scale"}:
        raise ValueError("solar parameters differ from supplied candidate contract")
    if parameters["method"] not in ("faiman_prilliman", "faiman", "sapm_module"):
        raise ValueError("unsupported thermal implementation")
    for name, bounds in (("u0", (20., 35.)), ("u1", (4., 10.)), ("dc_loss_scale", (.9, 1.))):
        value = parameters[name]
        if type(value) not in (int, float) or not np.isfinite(value) or not bounds[0] <= value <= bounds[1]:
            raise ValueError(f"solar physical parameter outside declared bounds: {name}")


def physical(forcing, parameters):
    validate(parameters)
    temp = models.temperature(forcing["poa"], forcing["ambient"], forcing["wind"],
                              forcing["timestamp"], method=parameters["method"],
                              u0=parameters["u0"], u1=parameters["u1"])
    dc, voltage = models.dc_power(forcing["poa"], temp)
    ac = models.inverter(dc * parameters["dc_loss_scale"], voltage)
    return {"prediction": ac, "module_temperature": temp}


def adapter():
    return PythonAdapter(physical, validate)
