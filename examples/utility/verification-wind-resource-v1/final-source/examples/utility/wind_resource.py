"""Explicit discrete wind resources for supplied development scenarios.

Probabilities are joint bin masses, not densities or Weibull parameters. Loading
one does not establish independent exposure, data rights or private-score safety.
Optional PyWake/xarray imports occur only when constructing the physical model.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Literal

import numpy as np

from autoengineering.campaign.artifacts import read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record

RESOURCE_PATH = "inputs/wind-resource.json"
MAX_RESOURCE_BYTES = 262144


@dataclass(frozen=True)
class WindResource(Record):
    schema: Literal["utility-wind-resource-v1"]
    directions_deg: tuple[float, ...]
    speeds_m_s: tuple[float, ...]
    probability: tuple[tuple[float, ...], ...]
    turbulence_intensity: float = 0.1
    annualization_hours: Literal[8760] = 8760

    def _validate(self):
        n, m = len(self.directions_deg), len(self.speeds_m_s)
        if not 1 <= n <= 72 or 360 % n or not 1 <= m <= 64:
            raise ValueError("wind resource grid exceeds the uniform-direction profile")
        if self.directions_deg != tuple(float(i * (360 // n)) for i in range(n)):
            raise ValueError("wind resource directions must cover a uniform 0..360 grid")
        if any(not 0 <= speed <= 100 for speed in self.speeds_m_s) or any(
            a >= b for a, b in zip(self.speeds_m_s, self.speeds_m_s[1:])
        ):
            raise ValueError("wind resource speeds need increasing finite m/s values in 0..100")
        if len(self.probability) != n or any(len(row) != m for row in self.probability):
            raise ValueError("wind joint probability dimensions differ from the grid")
        mass = [p for row in self.probability for p in row]
        if any(p < 0 for p in mass) or not math.isclose(
            math.fsum(mass), 1.0, rel_tol=0, abs_tol=1e-12
        ):
            raise ValueError("wind joint probability mass must be nonnegative and sum to one")
        if not 0 < self.turbulence_intensity <= 1:
            raise ValueError("wind resource turbulence intensity must be in (0,1]")

    @property
    def direction_step(self):
        return 360 // len(self.directions_deg)

    def validate_geometry(self, geometry):
        if geometry.direction_step != self.direction_step:
            raise ValueError("wind resource direction grid differs from frozen geometry")

    def wake_model(self):
        """Fixed NOJ/V80, flat uniform terrain and exact supplied flow cases.

        PyWake 2.6.20 XRSite uses P(wd,ws) as joint flow-case mass. Its direction
        sector scaling is unity when queried at the complete supplied grid.
        Reference: https://topfarm.pages.windenergy.dtu.dk/PyWake/notebooks/Site
        """
        import xarray as xr
        from py_wake import NOJ
        from py_wake.examples.data.hornsrev1 import V80
        from py_wake.site import XRSite

        data = xr.Dataset(
            {"P": (("wd", "ws"), np.array(self.probability)), "TI": self.turbulence_intensity},
            coords={"wd": np.array(self.directions_deg), "ws": np.array(self.speeds_m_s)},
        )
        return NOJ(XRSite(data, interp_method="nearest", bounds="check"), V80())

    def evaluate(self, x, y):
        """Return per-turbine/case GWh and W, with no implicit normalization."""
        x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
        if (
            x.ndim != 1
            or y.shape != x.shape
            or not 1 <= len(x) <= 128
            or not np.isfinite(x).all()
            or not np.isfinite(y).all()
        ):
            raise ValueError("wind resource evaluation needs aligned finite coordinates")
        result = self.wake_model()(x.copy(), y.copy(), wd=self.directions_deg, ws=self.speeds_m_s)
        power = np.asarray(result.Power.transpose("wt", "wd", "ws").values)
        expected_shape = (len(x), len(self.directions_deg), len(self.speeds_m_s))
        if (
            power.shape != expected_shape
            or not np.isfinite(power).all()
            or np.min(power) < 0
            or np.max(power) > 2e6 * (1 + 1e-10)
            or tuple(result.wd.values) != self.directions_deg
            or tuple(result.ws.values) != self.speeds_m_s
        ):
            raise ValueError("wind resource power or flow-case alignment failed")
        # Verify the actual library probabilities. Never let sector interpolation
        # or normalization silently change the supplied distribution.
        probability = np.asarray(
            result.P.broadcast_like(result.Power).transpose("wt", "wd", "ws").values
        )
        if not np.allclose(probability, np.array(self.probability)[None, :, :], rtol=0, atol=1e-12):
            raise ValueError("PyWake altered the supplied joint probability mass")
        aep = np.asarray(result.aep(normalize_probabilities=False, hours_pr_year=8760).values)
        analytic = power * np.array(self.probability)[None, :, :] * (8760 / 1e9)
        if aep.shape != expected_shape or not np.allclose(aep, analytic, rtol=1e-12, atol=1e-12):
            raise ValueError("wind resource energy differs from explicit weighted power")
        return aep, power


def read_resource(root: Path, reference: ArtifactRef) -> WindResource:
    """Verify bounded original artifact bytes before parsing or importing PyWake."""
    if reference.path != RESOURCE_PATH:
        raise ValueError("wind resource requires the registered artifact path")
    raw = read_bytes(Path(root), reference, max_bytes=MAX_RESOURCE_BYTES)
    return WindResource.from_json(raw.decode())


def demo(output: Path):
    """One bundled synthetic example. No optimization or private data access."""
    from importlib.resources import files
    from importlib.metadata import version
    from autoengineering.campaign.artifacts import reference
    from autoengineering.campaign.serialization import canonical_json
    from autoengineering.campaign.store import checked_directory, durable_write

    output = Path(output).absolute()
    if any(p.is_symlink() for p in (output, *output.parents)):
        raise ValueError("wind demo output cannot contain symlinks")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    checked_directory(output)
    resource = WindResource.from_json(
        files("examples.utility").joinpath("fixtures/wind-resource-demo.json").read_text()
    )
    durable_write(output / "resource.json", resource.to_json().encode())
    aep, power = resource.evaluate((0.0, 600.0, 0.0, 600.0), (0.0, 0.0, 600.0, 600.0))
    path = output / "prediction.npz"
    np.savez(path, aep_gwh=aep, power_w=power)
    path.chmod(0o600)
    summary = {
        "profile": "wind-resource-demo-v1",
        "scope": "authored synthetic resource and layout",
        "resource_digest": resource.digest,
        "turbines": 4,
        "annual_energy_gwh": float(aep.sum()),
        "prediction": reference(
            output, path.name, media_type="application/octet-stream", producer="wind-resource-demo"
        ).to_dict(),
        "py_wake_version": version("py-wake"),
        "independent_confirmation": "not_attempted",
        "optimization": "not_attempted",
        "provider_calls": 0,
        "limits": "standalone single evaluation, not a managed comparison or private scorer",
    }
    durable_write(output / "summary.json", canonical_json(summary).encode())
    return summary


if __name__ == "__main__":
    import argparse
    from autoengineering.campaign.serialization import canonical_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Fresh directory for the bundled synthetic example",
    )
    print(canonical_json(demo(parser.parse_args().output)))
