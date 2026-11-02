"""Read sealed normalized solar bundles without models, sources or private fallback.

Expected manifest and preparer pins are caller-owned. Reading preparation output
never establishes source, scientific, exposure or private-runtime admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import math
from typing import Literal, Mapping

from autoengineering.campaign.artifacts import confined_file, read_bytes
from autoengineering.campaign.records import ArtifactRef
from autoengineering.campaign.serialization import Record, digest, unique_json
from autoengineering.campaign.store import checked_directory
from autoengineering.utility.contracts import sha256
from examples.utility.solar_intervals import instant, stamp
from examples.utility.solar_partitions import SolarPartitionPlan, MAX_ARTIFACT_BYTES


@dataclass(frozen=True)
class SolarPublicManifest(Record):
    schema: Literal["utility-solar-public-v1"]
    plan: SolarPartitionPlan
    plan_digest: str
    preparer_sources: Mapping[str, str]
    normalized_rows_digest: str
    files: Mapping[str, str]
    private_bundle_digest: str
    development_roles: tuple[Literal["warmup", "fitting", "selection"], ...]
    confirmation_rows: int
    state_policy: Literal["forcing_only_continuity_reset_on_driver_gaps"]
    source_bytes_verified: Literal[False]
    exposure_attested: Literal[False]
    scientific_adapter_admitted: Literal[False]
    private_boundary_qualified: Literal[False]

    def _validate(self):
        for value in (
            self.plan_digest,
            self.normalized_rows_digest,
            self.private_bundle_digest,
            *self.files.values(),
            *self.preparer_sources.values(),
        ):
            sha256(value)
        if (
            self.plan_digest != self.plan.digest
            or self.state_policy != self.plan.state_policy
            or set(self.preparer_sources) != {"alignment", "partition"}
            or set(self.files) != {"forcing.json", "fitting.json", "selection.json"}
        ):
            raise ValueError("solar manifest identities or file roles differ")
        roles = []
        for window in self.plan.windows:
            size = (
                int((instant(window.end) - instant(window.start)).total_seconds())
                // self.plan.alignment.step_seconds
            )
            if window.role == "confirmation":
                if self.confirmation_rows != size:
                    raise ValueError("solar confirmation count differs")
            else:
                roles.extend([window.role] * size)
        if tuple(roles) != self.development_roles:
            raise ValueError("solar development roles differ")


@dataclass(frozen=True)
class SolarPrivateManifest(Record):
    schema: Literal["utility-solar-private-v1"]
    plan_digest: str
    preparer_sources: Mapping[str, str]
    files: Mapping[str, str]

    def _validate(self):
        for value in (self.plan_digest, *self.preparer_sources.values(), *self.files.values()):
            sha256(value)
        if set(self.preparer_sources) != {"alignment", "partition"} or set(self.files) != {
            "forcing.json",
            "labels.json",
        }:
            raise ValueError("solar reserved file roles differ")


@dataclass(frozen=True)
class SolarForcing(Record):
    start: tuple[str, ...]
    end: tuple[str, ...]
    duration_seconds: tuple[int, ...]
    poa_w_m2: tuple[float | None, ...]
    temperature_c: tuple[float | None, ...]
    wind_m_s: tuple[float | None, ...]
    drivers_usable: tuple[bool, ...]
    segment_id: tuple[int | None, ...]

    def _validate(self):
        size = len(self.start)
        if not size or any(
            len(value) != size
            for value in (
                self.end,
                self.duration_seconds,
                self.poa_w_m2,
                self.temperature_c,
                self.wind_m_s,
                self.drivers_usable,
                self.segment_id,
            )
        ):
            raise ValueError("solar forcing columns differ in length")
        segment, previous = -1, False
        for i, usable in enumerate(self.drivers_usable):
            values = (self.poa_w_m2[i], self.temperature_c[i], self.wind_m_s[i])
            if usable:
                if any(v is None for v in values) or self.poa_w_m2[i] < 0 or self.wind_m_s[i] < 0:
                    raise ValueError("solar forcing availability or domain differs")
                if not previous:
                    segment += 1
                if self.segment_id[i] != segment:
                    raise ValueError("solar segment continuity differs")
            elif any(v is not None for v in values) or self.segment_id[i] is not None:
                raise ValueError("solar forcing gap retains partial values")
            previous = usable


@dataclass(frozen=True)
class SolarLabels(Record):
    ac_kw: tuple[float | None, ...]
    energy_kwh: tuple[float | None, ...]
    score_mask: tuple[bool, ...]

    def _validate(self):
        if len(self.ac_kw) != len(self.energy_kwh) or len(self.ac_kw) != len(self.score_mask):
            raise ValueError("solar label columns differ")
        for ac, energy, keep in zip(self.ac_kw, self.energy_kwh, self.score_mask):
            if (keep and (ac is None or energy is None)) or (
                not keep and (ac is not None or energy is not None)
            ):
                raise ValueError("solar labels differ from their score mask")


@dataclass(frozen=True)
class SolarInputs(Record):
    schema: Literal["utility-solar-prepared-inputs-v1"]
    scope: Literal["development", "reserved"]
    manifest_digest: str
    plan: SolarPartitionPlan
    forcing: SolarForcing
    labels: Mapping[str, SolarLabels]
    qualification: Literal["not_admitted"] = "not_admitted"

    def _validate(self):
        sha256(self.manifest_digest)
        expected = {"fitting", "selection"} if self.scope == "development" else {"confirmation"}
        if set(self.labels) != expected:
            raise ValueError("solar input label roles differ")


def _read(root, name, pin, kind, limit=MAX_ARTIFACT_BYTES):
    sha256(pin)
    path = confined_file(root, name)
    ref = ArtifactRef(name, pin, path.stat().st_size, "application/json", "solar-preparation", {})
    value = unique_json(read_bytes(root, ref, max_bytes=limit).decode())
    # The writer commits canonical bytes, so semantic re-encoding is also exact.
    if digest(value) != pin:
        raise ValueError("solar canonical identity differs")
    return kind.from_dict(value)


def _public(root, pin, sources):
    root = checked_directory(root)
    if set(sources) != {"alignment", "partition"}:
        raise ValueError("solar caller pins incomplete")
    for value in sources.values():
        sha256(value)
    manifest = _read(root, "manifest.json", pin, SolarPublicManifest, 8 * 1024**2)
    if dict(manifest.preparer_sources) != dict(sources):
        raise ValueError("solar preparer source pins differ")
    return root, manifest


def _validate_inputs(plan, forcing, labels, roles):
    step = plan.alignment.step_seconds
    if len(forcing.start) != len(roles):
        raise ValueError("solar input scope count differs")
    start = instant(plan.alignment.start)
    for i, (left, right, duration) in enumerate(
        zip(forcing.start, forcing.end, forcing.duration_seconds)
    ):
        expected = start + timedelta(seconds=i * step)
        if (
            left != stamp(expected)
            or right != stamp(expected + timedelta(seconds=step))
            or duration != step
        ):
            raise ValueError("solar input chronology differs from plan")
    run = 0
    for role, values in labels.items():
        if len(values.ac_kw) != len(roles) or not any(values.score_mask):
            raise ValueError("solar label role has no support")
        run = 0
        for i, keep in enumerate(values.score_mask):
            run = run + 1 if forcing.drivers_usable[i] else 0
            if keep:
                if roles[i] != role or run <= plan.segment_warmup_intervals:
                    raise ValueError("solar score leaks role, gap or warmup")
                if not math.isclose(
                    values.energy_kwh[i],
                    values.ac_kw[i] * (step / 3600),
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                ):
                    raise ValueError("solar label energy differs from support")


def read_development(root, *, expected_manifest_digest, expected_preparer_sources):
    """Read only the public manifest and its three declared development files."""
    try:
        root, manifest = _public(root, expected_manifest_digest, expected_preparer_sources)
        forcing = _read(root, "forcing.json", manifest.files["forcing.json"], SolarForcing)
        labels = {
            role: _read(root, role + ".json", manifest.files[role + ".json"], SolarLabels)
            for role in ("fitting", "selection")
        }
        _validate_inputs(manifest.plan, forcing, labels, manifest.development_roles)
        return SolarInputs(
            "utility-solar-prepared-inputs-v1",
            "development",
            expected_manifest_digest,
            manifest.plan,
            forcing,
            labels,
        )
    except Exception:
        pass
    raise ValueError("solar development input verification failed") from None


def read_reserved(
    public_root, private_root, *, expected_manifest_digest, expected_preparer_sources
):
    """Trusted caller only: verify reserved inputs against the sealed public identity.

    This reader grants no label access authority. It must not be registered as an
    advisory-worker tool or used before the admitted preparation/scoring boundary.
    """
    try:
        public, manifest = _public(public_root, expected_manifest_digest, expected_preparer_sources)
        private = checked_directory(private_root)
        if public.is_relative_to(private) or private.is_relative_to(public):
            raise ValueError("solar reserved scopes overlap")
        saved = _read(
            private, "manifest.json", manifest.private_bundle_digest, SolarPrivateManifest, 65536
        )
        if saved.plan_digest != manifest.plan_digest or dict(saved.preparer_sources) != dict(
            manifest.preparer_sources
        ):
            raise ValueError("solar reserved plan/source identity differs")
        forcing = _read(private, "forcing.json", saved.files["forcing.json"], SolarForcing)
        labels = {
            "confirmation": _read(private, "labels.json", saved.files["labels.json"], SolarLabels)
        }
        roles = (*manifest.development_roles, *("confirmation",) * manifest.confirmation_rows)
        _validate_inputs(manifest.plan, forcing, labels, roles)
        # Reserved inference replays the exact development forcing prefix.
        development = _read(public, "forcing.json", manifest.files["forcing.json"], SolarForcing)
        size = len(manifest.development_roles)
        if any(
            getattr(forcing, name)[:size] != getattr(development, name)
            for name in development.to_dict()
        ):
            raise ValueError("solar reserved inference prefix differs")
        return SolarInputs(
            "utility-solar-prepared-inputs-v1",
            "reserved",
            manifest.private_bundle_digest,
            manifest.plan,
            forcing,
            labels,
        )
    except Exception:
        pass
    raise ValueError("solar reserved input verification failed") from None
