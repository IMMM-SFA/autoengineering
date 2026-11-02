"""Trusted preparation of normalized daily rows, without model or network calls.

This is a separate profile from the historical Leaf River cache. It separates
artifacts, but does not attest exposure, verify original source bytes, or provide
an OS boundary against code running as the same user. Raw source parsing and
scientific admission remain separate responsibilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
from pathlib import Path
from typing import Literal

from autoengineering.campaign.serialization import Record, canonical_json, digest
from autoengineering.campaign.store import checked_directory, durable_write
from autoengineering.utility.contracts import identifier, sha256
from autoengineering.utility.exposure import iso_date


@dataclass(frozen=True)
class DailyWindow(Record):
    role: Literal["warmup", "fitting", "selection", "confirmation"]
    start: str
    end: str

    def _validate(self):
        if iso_date(self.start) > iso_date(self.end):
            raise ValueError("daily window is reversed")


@dataclass(frozen=True)
class DailyHydrologyPlan(Record):
    schema: Literal["utility-daily-hydrology-preparation-v1"]
    source_id: str
    site_id: str
    declared_source_digest: str
    area_km2: float
    latitude_deg: float
    windows: tuple[DailyWindow, ...]
    allowed_flow_flags: tuple[str, ...]
    mean_temperature: Literal["midrange_min_max"] = "midrange_min_max"

    def _validate(self):
        identifier(self.source_id)
        identifier(self.site_id)
        sha256(self.declared_source_digest)
        if self.area_km2 <= 0 or not -90 < self.latitude_deg < 90:
            raise ValueError("invalid basin area or latitude")
        if tuple(w.role for w in self.windows) != (
            "warmup",
            "fitting",
            "selection",
            "confirmation",
        ):
            raise ValueError("daily preparation needs four ordered windows")
        for left, right in zip(self.windows, self.windows[1:]):
            if iso_date(left.end) + timedelta(days=1) != iso_date(right.start):
                raise ValueError("daily preparation requires contiguous nonoverlapping windows")
        count = (iso_date(self.windows[-1].end) - iso_date(self.windows[0].start)).days + 1
        if count > 20000:
            raise ValueError("daily preparation exceeds 20000 rows")
        if not self.allowed_flow_flags or len(set(self.allowed_flow_flags)) != len(
            self.allowed_flow_flags
        ):
            raise ValueError("daily preparation needs unique accepted quality flags")
        if any(not value or len(value) > 32 for value in self.allowed_flow_flags):
            raise ValueError("invalid accepted quality flag")


@dataclass(frozen=True)
class DailyHydrologyRow(Record):
    date: str
    precip_mm: float
    tmin_c: float
    tmax_c: float
    flow_cfs: float | None
    flow_flag: str

    def _validate(self):
        iso_date(self.date)
        if self.precip_mm < 0 or self.tmin_c > self.tmax_c:
            raise ValueError("invalid daily forcing")
        if self.flow_cfs is not None and self.flow_cfs < 0:
            raise ValueError("negative flow must be resolved by explicit source preprocessing")
        if len(self.flow_flag) > 32:
            raise ValueError("invalid source quality flag")


def _forcing(rows):
    return {
        "dates": [row.date for row in rows],
        "precip_mm": [row.precip_mm for row in rows],
        "tmin_c": [row.tmin_c for row in rows],
        "tmax_c": [row.tmax_c for row in rows],
        "tmean_c": [(row.tmin_c + row.tmax_c) / 2 for row in rows],
        "day_of_year": [iso_date(row.date).timetuple().tm_yday for row in rows],
    }


def prepare(plan: DailyHydrologyPlan, rows, public_root: Path, private_root: Path):
    """Create immutable artifacts in two empty owner-private separate scopes.

    ``rows`` must be canonical source-normalized records, not an executable
    parser registration. Both roles are claimed before iteration. Row validation
    precedes data writes. The private bundle commits first and the public
    manifest last. Partial preparation refuses reuse of the same roots.
    """
    try:
        if not isinstance(plan, DailyHydrologyPlan):
            raise ValueError("invalid daily plan")
        public, private = checked_directory(public_root), checked_directory(private_root)
        if public.is_relative_to(private) or private.is_relative_to(public):
            raise ValueError("daily preparation requires separate public and private scopes")
        if any(public.iterdir()) or any(private.iterdir()):
            raise ValueError("daily preparation requires empty output scopes")
        preparer = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        binding = digest(
            {
                "plan": plan.digest,
                "preparer": preparer,
                "public": str(public),
                "private": str(private),
            }
        )
        for path, role in sorted(
            ((public, "public"), (private, "private")), key=lambda p: str(p[0])
        ):
            durable_write(
                path / "preparation-claim.json",
                canonical_json(
                    {
                        "schema": "utility-hydrology-preparation-claim-v1",
                        "binding": binding,
                        "plan_digest": plan.digest,
                        "preparer_source_digest": preparer,
                        "scope": role,
                    }
                ).encode(),
            )
        saved = []
        for row in rows:
            if len(saved) >= 20000:
                raise ValueError("daily row bound")
            saved.append(
                row if isinstance(row, DailyHydrologyRow) else DailyHydrologyRow.from_dict(row)
            )
        start, end = iso_date(plan.windows[0].start), iso_date(plan.windows[-1].end)
        expected = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
        if [row.date for row in saved] != expected:
            raise ValueError("daily dates differ from plan")
        roles = []
        for window in plan.windows:
            roles.extend([window.role] * ((iso_date(window.end) - iso_date(window.start)).days + 1))
        # Defined SI conversion, distinct from the old cache's rounded factor.
        factor = 0.3048**3 * 86400 * 1000 / (plan.area_km2 * 1e6)
        valid = [
            row.flow_cfs is not None and row.flow_flag in plan.allowed_flow_flags for row in saved
        ]
        development = [row for row, role in zip(saved, roles) if role != "confirmation"]
        public_roles = roles[: len(development)]

        def labels(role, size):
            mask = [r == role and keep for r, keep in zip(roles[:size], valid[:size])]
            # Masked values are placeholders, not observations or imputed scores.
            values = [
                row.flow_cfs * factor if keep else 0.0 for row, keep in zip(saved[:size], mask)
            ]
            return {"labels": values, "mask": mask}

        public_documents = {
            "forcing.json": _forcing(development),
            "fitting.json": labels("fitting", len(development)),
            "selection.json": labels("selection", len(development)),
        }
        private_documents = {
            "forcing.json": _forcing(saved),
            "labels.json": labels("confirmation", len(saved)),
        }
        if any(
            not any(labels(role, len(saved))["mask"])
            for role in ("fitting", "selection", "confirmation")
        ):
            raise ValueError("a requested role has no usable labels")
        encoded_public = {
            name: canonical_json(value).encode() for name, value in public_documents.items()
        }
        encoded_private = {
            name: canonical_json(value).encode() for name, value in private_documents.items()
        }
        if any(len(raw) > 4194304 for raw in (*encoded_public.values(), *encoded_private.values())):
            raise ValueError("daily artifact byte bound")
        private_manifest = {
            "schema": "utility-daily-hydrology-private-v1",
            "plan_digest": plan.digest,
            "preparer_source_digest": preparer,
            "files": {name: digest(value) for name, value in private_documents.items()},
        }
        manifest = {
            "schema": "utility-daily-hydrology-public-v1",
            "plan": plan.to_dict(),
            "plan_digest": plan.digest,
            "preparer_source_digest": preparer,
            "normalized_rows_digest": digest([r.to_dict() for r in saved]),
            "files": {name: digest(value) for name, value in public_documents.items()},
            "private_bundle_digest": digest(private_manifest),
            "development_roles": public_roles,
            "confirmation_rows": roles.count("confirmation"),
            "flow_units": "mm/day",
            "forcing_units": {
                "precip_mm": "mm",
                "tmin_c": "degC",
                "tmax_c": "degC",
                "tmean_c": "degC",
                "day_of_year": "day",
            },
            "precipitation_support": "P1D_interval_total",
            "state_policy": "replay_from_initial_state_using_drivers_only",
            "source_bytes_verified": False,
            "scientific_adapter_admitted": False,
            "exposure_attested": False,
            "private_boundary_qualified": False,
        }
        for name, raw in encoded_private.items():
            durable_write(private / name, raw)
        durable_write(private / "manifest.json", canonical_json(private_manifest).encode())
        for name, raw in encoded_public.items():
            durable_write(public / name, raw)
        durable_write(public / "manifest.json", canonical_json(manifest).encode())
        return manifest
    except Exception:
        # Input, parser and filesystem exceptions must not export private values
        # or paths. Partial files remain in their original owner-private scopes.
        raise ValueError("daily hydrology preparation failed") from None
