"""Development hourly NOJ profile with explicit 80 m hardware and no resource bins.

The raw HDF5 direction convention is an explicit development assumption. This
profile is not admitted for confirmation and does not certify real hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from importlib.metadata import version
import io
import re
import zipfile

import numpy as np

from autoengineering.adapters.contracts import PrepareContext
from autoengineering.adapters.python import PythonAdapter
from autoengineering.campaign.artifacts import read_bytes, reference
from autoengineering.campaign.records import ModelSnapshot, PortContract
from autoengineering.campaign.serialization import digest
from examples.utility.wind import ROOT, UNITS
from examples.utility.wind_parameters import WindGeometry
from examples.utility.wind_point import decode_variable, utc_axis

POLICY = {
    "schema": "utility-wind-hourly-development-v1",
    "height_m": 80.0,
    "rotor_diameter_m": 80.0,
    "turbines": 4,
    "curve": "py-wake-2.6.20:V80-linear",
    "wake": "NOJ-defaults",
    "site": "UniformSite-flat-no-shear",
    "ti": 0.1,
    "direction_assumption": "meteorological-from-degrees-clockwise-from-north",
    "direction_360": "wrap-to-zero",
    "quadrature": "each-source-instantaneous-hour-represents-one-hour",
    "missing": "reject-any-incomplete-joint-hour",
    "density": "fixed-tabular-curve-no-weather-density-correction",
    "task_admitted": False,
    "raw_direction_convention_qualified": False,
}
SOURCE_FILES = (
    "examples/utility/wind_hourly.py",
    "examples/utility/wind_point.py",
    "examples/utility/wind_parameters.py",
    "examples/utility/wind.py",
    "pixi.lock",
)


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("hourly profile needs SHA-256 source and assumption identities")
    return value


def read_point(root, ref, year):
    """Verify a small pinned extraction with exact headers before NumPy allocates."""
    blob = read_bytes(root, ref, max_bytes=512 * 1024)
    hours = len(utc_axis_for_year(year))
    fields = {
        "time_utc": "<U20",
        "raw_speed": "<u2",
        "raw_direction": "<u2",
        "speed_m_s": "<f8",
        "direction_source_deg": "<f8",
        "speed_valid": "|b1",
        "direction_valid": "|b1",
    }
    with zipfile.ZipFile(io.BytesIO(blob)) as zipped:
        if sorted(zipped.namelist()) != sorted(k + ".npy" for k in fields):
            raise ValueError("point archive members differ")
        if sum(i.file_size for i in zipped.infolist()) > 2 * 1024**2:
            raise ValueError("point archive exceeds decompressed cap")
        for name, dtype in fields.items():
            item = zipped.getinfo(name + ".npy")
            if item.file_size > 1024**2 or item.flag_bits & 1:
                raise ValueError("point archive member exceeds profile")
            with zipped.open(item) as member:
                fmt = np.lib.format.read_magic(member)
                readers = {
                    (1, 0): np.lib.format.read_array_header_1_0,
                    (2, 0): np.lib.format.read_array_header_2_0,
                }
                if fmt not in readers:
                    raise ValueError("point array format differs")
                shape, order, actual = readers[fmt](member, max_header_size=4096)
                if shape != (hours,) or order or actual.str != dtype:
                    raise ValueError("point array header differs")
    with np.load(io.BytesIO(blob), allow_pickle=False) as values:
        result = {name: values[name].copy() for name in fields}
    utc_axis(result["time_utc"], year, "UTC")
    for kind, unit, target in (
        ("speed", "m s-1", "speed_m_s"),
        ("direction", "degree", "direction_source_deg"),
    ):
        decoded, mask = decode_variable(
            result["raw_" + kind], kind=kind, units=unit, scale_factor=100.0, fill_value=65535
        )
        if not np.array_equal(decoded, result[target], equal_nan=True) or not np.array_equal(
            mask, result[kind + "_valid"]
        ):
            raise ValueError("point raw values, masks and decoded values disagree")
        if not mask.all():
            raise ValueError("hourly profile rejects incomplete joint hours")
    return result


def utc_axis_for_year(year):
    import calendar
    from datetime import datetime, timedelta, timezone

    if type(year) is not int or not 2007 <= year <= 2011:
        raise ValueError("hourly profile requires a development year")
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    return tuple(
        (start + timedelta(hours=i)).isoformat().replace("+00:00", "Z")
        for i in range((366 if calendar.isleap(year) else 365) * 24)
    )


def _backend():
    if version("py-wake") != "2.6.20":
        raise ValueError("hourly profile requires reviewed PyWake 2.6.20")
    from py_wake import NOJ
    from py_wake.examples.data.hornsrev1 import V80
    from py_wake.site import UniformSite
    from py_wake.wind_turbines import WindTurbine

    original = V80(method="linear")
    turbine = WindTurbine(
        name="V80_curve_80m", diameter=80, hub_height=80, powerCtFunction=original.powerCtFunction
    )
    if turbine.hub_height() != 80 or turbine.diameter() != 80:
        raise ValueError("hourly turbine hardware differs")
    return NOJ(UniformSite(p_wd=[1], ti=0.1, shear=None), turbine), turbine


@dataclass(frozen=True)
class WindHourly:
    geometry: WindGeometry
    year: int
    time_utc: tuple[str, ...]
    speed: np.ndarray
    direction: np.ndarray
    point_sha256: str
    assumption_digest: str

    def __post_init__(self):
        if len(self.geometry.x) != 4:
            raise ValueError("hourly profile requires four turbines")
        self.geometry.validate(self.geometry.baseline)
        axis = utc_axis(self.time_utc, self.year, "UTC")
        object.__setattr__(self, "time_utc", axis)
        _sha(self.point_sha256)
        _sha(self.assumption_digest)
        for name, upper in (("speed", 100), ("direction", 360)):
            values = np.asarray(getattr(self, name), dtype=float)
            if (
                values.shape != (len(axis),)
                or not np.isfinite(values).all()
                or (values < 0).any()
                or (values > upper).any()
            ):
                raise ValueError("hourly wind vectors exceed complete finite source domains")
            object.__setattr__(self, name, np.frombuffer(values.tobytes(), dtype=values.dtype))

    @property
    def identity(self):
        return digest(
            {
                "policy": POLICY,
                "geometry": self.geometry.to_dict(),
                "year": self.year,
                "axis": digest(self.time_utc),
                "point": self.point_sha256,
                "assumption": self.assumption_digest,
                "speed": hashlib.sha256(self.speed.tobytes()).hexdigest(),
                "direction": hashlib.sha256(self.direction.tobytes()).hexdigest(),
            }
        )

    def _power(self, power):
        values = np.asarray(power, dtype=float)
        if (
            values.shape != (4, len(self.time_utc))
            or not np.isfinite(values).all()
            or values.min() < 0
            or values.max() > 2e6 * (1 + 1e-10)
        ):
            raise ValueError("hourly turbine power violates shape, finiteness or 2 MW rating")
        return values

    def summarize(self, power, configuration):
        self.geometry.validate(configuration)
        values = self._power(power)
        x, y = map(np.asarray, self.geometry.positions(configuration))
        distance = np.hypot(x[:, None] - x, y[:, None] - y)
        np.fill_diagonal(distance, np.inf)
        return {
            name: np.asarray(value, dtype=float)
            for name, value in {
                "annual_energy": float(values.sum(dtype=np.float64)) / 1e9,
                "minimum_spacing": distance.min(),
                "boundary_violation": 0.0,
                "maximum_power": values.max(),
                "minimum_power": values.min(),
            }.items()
        }

    def physical(self, forcing, configuration):
        self.geometry.validate(configuration)
        if forcing:
            raise ValueError("hourly source is frozen; forcing overrides are forbidden")
        model, _ = _backend()
        x, y = self.geometry.positions(configuration)
        axis = np.asarray([t[:-1] for t in self.time_utc], dtype="datetime64[s]")
        result = model(
            x=np.asarray(x),
            y=np.asarray(y),
            h=np.full(4, 80.0),
            wd=self.direction.copy() % 360,
            ws=self.speed.copy(),
            time=axis,
        )
        if not np.array_equal(result.time.values, axis) or not np.array_equal(
            result.h.values, np.full(4, 80.0)
        ):
            raise ValueError("hourly model changed time support or hub height")
        power = result.Power.transpose("wt", "time").values
        return self.summarize(power, configuration)

    def reference(self):
        """One diagnostic turbine-curve call, separate from wake-model work."""
        _, turbine = _backend()
        power = np.asarray(turbine.power(self.speed.copy()), dtype=float)
        farm = np.broadcast_to(power, (4, len(self.time_utc)))
        return self.summarize(farm, self.geometry.baseline)

    def adapter(self):
        return PythonAdapter(self.physical, self.geometry.validate)

    def context(self, configuration, scratch):
        self.geometry.validate(configuration)
        refs = tuple(
            reference(ROOT, name, media_type="text/plain", producer="wind-hourly")
            for name in SOURCE_FILES
        )
        ports = tuple(
            PortContract(name, (), unit, "float", (), "scalar", digest({"grid": "scalar"}), None)
            for name, unit in UNITS.items()
        )
        model = ModelSnapshot(
            self.identity,
            {"wind": POLICY["schema"]},
            refs,
            digest({"py-wake": version("py-wake")}),
            (),
            ports,
        )
        return PrepareContext(model, dict(configuration), 0, str(scratch), ())
