"""Trusted supplied-layout wind adapter with scalar engineering outputs.

Layouts stay immutable internal model data. This profile does not claim general
array-port support or independent weather confirmation.
"""
from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from types import MappingProxyType

import numpy as np

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.adapters.python import PythonAdapter
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.records import ModelSnapshot, PortContract
from autoengineering.campaign.serialization import digest

ROOT = Path(__file__).resolve().parents[2]
UNITS = {"annual_energy": "GWh", "minimum_spacing": "m", "boundary_violation": "m",
         "maximum_power": "W", "minimum_power": "W"}


class WindTask:
    def __init__(self, layouts, baseline, *, direction_step=30):
        if type(direction_step) is not int or direction_step < 1 or 360 % direction_step:
            raise ValueError("direction step must divide 360 degrees")
        self.direction_step = direction_step
        self.baseline = self._positions(baseline)
        if len(self.baseline[0]) < 2:
            raise ValueError("wind profile requires at least two turbines")
        copied = {name: self._positions(positions) for name, positions in layouts.items()}
        if not copied:
            raise ValueError("wind task needs a supplied layout catalogue")
        self.layouts = MappingProxyType(copied)
        self.catalogue_digest = digest({name: [x.tolist(), y.tolist()]
                                        for name, (x, y) in self.layouts.items()})

    @staticmethod
    def _positions(positions):
        if len(positions) != 2:
            raise ValueError("positions need x and y")
        arrays = tuple(np.array(value, dtype=float, copy=True) for value in positions)
        if arrays[0].ndim != 1 or arrays[1].shape != arrays[0].shape or not all(
                np.isfinite(a).all() for a in arrays):
            raise ValueError("coordinates must be aligned finite vectors")
        return tuple(np.frombuffer(array.tobytes(), dtype=array.dtype) for array in arrays)

    def validate(self, parameters):
        if set(parameters) != {"layout_id"} or parameters["layout_id"] not in self.layouts:
            raise ValueError("layout must be supplied by the frozen catalogue")
        x, y = self.layouts[parameters["layout_id"]]
        # Check geometry before importing or invoking PyWake.
        bx, by = self.baseline
        if len(x) != len(bx):
            raise ValueError("turbine count differs from fixed hardware")
        if min(x) < min(bx)-1e-3 or max(x) > max(bx)+1e-3 or min(y) < min(by)-1e-3 or max(y) > max(by)+1e-3:
            raise ValueError("layout exceeds frozen rectangle")
        distance = np.hypot(x[:, None]-x, y[:, None]-y)
        np.fill_diagonal(distance, np.inf)
        if distance.min() < 320-1e-3:
            raise ValueError("layout violates four-diameter spacing")

    def physical(self, forcing, parameters):
        self.validate(parameters)
        if forcing:
            raise ValueError("bundled wind-distribution profile accepts no weather overrides")
        from examples.open_chains.wind.models import wakes
        x, y = self.layouts[parameters["layout_id"]]
        aep, power = wakes(x.copy(), y.copy(), self.direction_step)
        if not np.isfinite(aep).all() or not np.isfinite(power).all() or np.min(aep) < 0:
            raise ValueError("nonfinite or negative wind energy")
        if np.min(power) < 0 or np.max(power) > 2e6*(1+1e-10):
            raise ValueError("V80 turbine power violates fixed 2 MW rating")
        distance = np.hypot(x[:, None]-x, y[:, None]-y)
        np.fill_diagonal(distance, np.inf)
        return {name: np.array(value, dtype=float) for name, value in {
            "annual_energy": np.sum(aep), "minimum_spacing": distance.min(),
            "boundary_violation": 0., "maximum_power": np.max(power),
            "minimum_power": np.min(power)}.items()}

    def adapter(self):
        return PythonAdapter(self.physical, self.validate)

    def context(self, layout_id, scratch):
        self.validate({"layout_id": layout_id})
        files = ("examples/utility/wind.py", "examples/open_chains/wind/models.py", "pixi.lock")
        refs = tuple(reference(ROOT, name, media_type="text/plain", producer="utility-wind")
                     for name in files)
        profile = digest({"catalogue": self.catalogue_digest, "baseline": [a.tolist() for a in self.baseline],
                          "direction_step": self.direction_step, "hardware": "V80", "wake": "NOJ"})
        ports = tuple(PortContract(name, (), unit, "float", (), "scalar",
                                   digest({"grid": "scalar"}), None) for name, unit in UNITS.items())
        model = ModelSnapshot(profile, {"wind": "supplied-layout-noj-v1"}, refs,
                              digest({"py-wake": version("py-wake")}), (), ports)
        return PrepareContext(model, {"layout_id": layout_id}, 0, str(scratch), ())
