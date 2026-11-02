"""Fixed-hardware wind geometry with scalar layout parameters.

This development profile uses the existing bundled wind distribution. It adds no
array-port capability, new weather information or independent confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Mapping

import numpy as np

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.adapters.python import PythonAdapter
from autoengineering.campaign.artifacts import reference
from autoengineering.campaign.serialization import Record, digest
from autoengineering.campaign.records import ModelSnapshot, PortContract
from examples.utility.wind import ROOT, UNITS, WindTask


@dataclass(frozen=True)
class WindGeometry(Record):
    x: tuple[float, ...]
    y: tuple[float, ...]
    direction_step: int = 30

    def _validate(self):
        if len(self.x) < 2 or len(self.x) != len(self.y):
            raise ValueError("wind geometry requires aligned coordinates for fixed hardware")
        if min(self.x) == max(self.x) or min(self.y) == max(self.y):
            raise ValueError("parameterized layout requires a rectangle with positive area")
        task = WindTask(
            {"baseline": (self.x, self.y)}, (self.x, self.y), direction_step=self.direction_step
        )
        task.validate({"layout_id": "baseline"})

    @property
    def preflight(self):
        from autoengineering.utility.preflight import MinimumDistance

        return tuple(
            MinimumDistance(
                f"wind-spacing-{i}-{j}", (f"x_{i}", f"y_{i}"), (f"x_{j}", f"y_{j}"), 320.0 - 1e-3
            )
            for i in range(len(self.x))
            for j in range(i + 1, len(self.x))
        )

    @property
    def bounds(self):
        return {
            f"{axis}_{i}": (min(values), max(values))
            for axis, values in (("x", self.x), ("y", self.y))
            for i in range(len(self.x))
        }

    @property
    def baseline(self):
        return {
            f"{axis}_{i}": value
            for axis, values in (("x", self.x), ("y", self.y))
            for i, value in enumerate(values)
        }

    def positions(self, configuration: Mapping[str, float]):
        if set(configuration) != set(self.baseline):
            raise ValueError("layout parameters must match the fixed turbine coordinates")
        if any(type(v) not in (int, float) or not np.isfinite(v) for v in configuration.values()):
            raise ValueError("layout coordinates must be finite numeric scalars")
        return tuple(
            tuple(float(configuration[f"{axis}_{i}"]) for i in range(len(self.x)))
            for axis in ("x", "y")
        )

    def configuration(self, x, y):
        positions = WindTask._positions((x, y))
        if len(positions[0]) != len(self.x):
            raise ValueError("layout turbine count differs from fixed hardware")
        configuration = {
            f"{axis}_{i}": float(value)
            for axis, values in zip(("x", "y"), positions)
            for i, value in enumerate(values)
        }
        self.validate(configuration)
        return configuration

    def validate(self, configuration):
        candidate = self.positions(configuration)
        if any(
            not lower <= configuration[name] <= upper
            for name, (lower, upper) in self.bounds.items()
        ):
            raise ValueError("layout exceeds the frozen parameter domain")
        WindTask(
            {"candidate": candidate}, (self.x, self.y), direction_step=self.direction_step
        ).validate({"layout_id": "candidate"})

    def physical(self, forcing, configuration):
        self.validate(configuration)
        candidate = self.positions(configuration)
        return WindTask(
            {"candidate": candidate}, (self.x, self.y), direction_step=self.direction_step
        ).physical(forcing, {"layout_id": "candidate"})

    def adapter(self):
        return PythonAdapter(self.physical, self.validate)

    def context(self, configuration, scratch, *, source_root=None):
        self.validate(configuration)
        root = Path(source_root) if source_root is not None else ROOT
        names = (
            "examples/utility/wind.py",
            "examples/open_chains/wind/models.py",
            "pixi.lock",
            "examples/utility/wind_parameters.py",
        )
        refs = tuple(
            reference(root, name, media_type="text/plain", producer="utility-wind-parameters")
            for name in names
        )
        ports = tuple(
            PortContract(name, (), unit, "float", (), "scalar", digest({"grid": "scalar"}), None)
            for name, unit in UNITS.items()
        )
        model = ModelSnapshot(
            digest(
                {
                    "profile": "utility-wind-parameters-v1",
                    "geometry": self.to_dict(),
                    "hardware": "V80",
                    "wake": "NOJ",
                }
            ),
            {"wind": "parameterized-layout-noj-v1"},
            refs,
            digest({"py-wake": version("py-wake")}),
            (),
            ports,
        )
        return PrepareContext(model, dict(configuration), 0, str(scratch), ())
