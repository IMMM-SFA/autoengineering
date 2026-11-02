"""Exposure and chronological partition contracts without observation access."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from autoengineering.campaign.serialization import Record
from .contracts import identifier, sha256


def iso_date(value):
    try:
        result = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("date must be ISO YYYY-MM-DD") from error
    if result.isoformat() != value:
        raise ValueError("date must be ISO YYYY-MM-DD")
    return result


@dataclass(frozen=True)
class ExposureRecord(Record):
    source_id: str
    site_id: str
    source_hashes: tuple[str, ...]
    access_date: str | None
    period_start: str | None
    period_end: str | None
    scenario_digests: tuple[str, ...]
    exposure: Literal["known_exposed", "unknown_exposure", "custodian_unexposed"]
    uses: tuple[str, ...]
    people_or_workers: tuple[str, ...]
    content: tuple[Literal["metadata", "drivers", "labels", "diagnostics", "aggregates"], ...]
    custodian_attestation_digest: str | None
    rights_digest: str | None

    def _validate(self):
        identifier(self.source_id)
        identifier(self.site_id)
        for value in (*self.source_hashes, *self.scenario_digests):
            sha256(value)
        for values in (self.source_hashes, self.scenario_digests, self.uses,
                       self.people_or_workers, self.content):
            if len(set(values)) != len(values):
                raise ValueError("duplicate exposure field entry")
        if self.access_date is not None:
            iso_date(self.access_date)
        if (self.period_start is None) != (self.period_end is None):
            raise ValueError("exposure period needs both boundaries")
        if self.period_start is not None:
            if iso_date(self.period_start) > iso_date(self.period_end):
                raise ValueError("exposure period is reversed")
        for value in (self.custodian_attestation_digest, self.rights_digest):
            if value is not None:
                sha256(value)
        if self.exposure == "custodian_unexposed" and self.admission_blockers():
            raise ValueError("unexposed classification needs complete custody and rights evidence")

    def admission_blockers(self) -> tuple[str, ...]:
        blockers = []
        if self.exposure != "custodian_unexposed":
            blockers.append(self.exposure)
        for name in ("source_hashes", "access_date", "people_or_workers", "content",
                     "custodian_attestation_digest", "rights_digest"):
            if not getattr(self, name):
                blockers.append("missing_" + name)
        if self.period_start is None and not self.scenario_digests:
            blockers.append("missing_period_or_scenario")
        return tuple(blockers)


@dataclass(frozen=True)
class TimePartition(Record):
    role: Literal["fitting", "selection", "confirmation"]
    start: str
    end: str
    mask_digest: str

    def _validate(self):
        if iso_date(self.start) > iso_date(self.end):
            raise ValueError("partition period is reversed")
        sha256(self.mask_digest)


@dataclass(frozen=True)
class PartitionManifest(Record):
    schema: Literal["utility-partitions-v1"]
    source_id: str
    site_id: str
    exposure_digest: str
    partitions: tuple[TimePartition, ...]
    embargo_days: int
    feature_window_days: int
    warmup_days: int
    initial_state_digest: str
    carryover: Literal["reset", "causal_drivers_only"]
    gap_policy_digest: str
    preprocessing_artifact_digest: str
    preprocessing_fit_role: Literal["fitting"]
    seasonal_coverage_digest: str
    access_policy_digest: str

    def _validate(self):
        identifier(self.source_id)
        identifier(self.site_id)
        for value in (self.exposure_digest, self.initial_state_digest, self.gap_policy_digest,
                      self.preprocessing_artifact_digest, self.seasonal_coverage_digest,
                      self.access_policy_digest):
            sha256(value)
        if min(self.embargo_days, self.feature_window_days, self.warmup_days) < 0:
            raise ValueError("partition day counts must be nonnegative")
        if self.embargo_days < self.feature_window_days:
            raise ValueError("embargo must cover the feature window")
        if tuple(p.role for p in self.partitions) != ("fitting", "selection", "confirmation"):
            raise ValueError("partitions must be ordered fitting, selection, confirmation")
        for left, right in zip(self.partitions, self.partitions[1:]):
            gap = (iso_date(right.start) - iso_date(left.end)).days - 1
            if gap < self.embargo_days:
                raise ValueError("partitions overlap or violate embargo")

    def check_exposure(self, exposure: ExposureRecord):
        if exposure.digest != self.exposure_digest or (exposure.source_id, exposure.site_id) != (
                self.source_id, self.site_id):
            raise ValueError("partition exposure identity mismatch")
        blockers = exposure.admission_blockers()
        if blockers:
            raise ValueError("confirmation exposure is not admitted: " + ", ".join(blockers))
        confirmation = self.partitions[-1]
        if exposure.period_start is None or not (
                iso_date(exposure.period_start) <= iso_date(confirmation.start)
                <= iso_date(confirmation.end) <= iso_date(exposure.period_end)):
            raise ValueError("custody evidence does not cover confirmation period")


def admit_partition(manifest: PartitionManifest, exposure: ExposureRecord,
                    register: tuple[ExposureRecord, ...], expected_register_digest: str):
    """Check the complete pinned history, including conflicting prior uses."""
    from autoengineering.campaign.serialization import digest

    sha256(expected_register_digest)
    actual = digest([record.to_dict() for record in register])
    if actual != expected_register_digest:
        raise ValueError("exposure register identity mismatch")
    if len({record.digest for record in register}) != len(register):
        raise ValueError("duplicate exposure register entry")
    if exposure not in register:
        raise ValueError("confirmation custody record absent from register")
    manifest.check_exposure(exposure)
    confirmation = manifest.partitions[-1]
    for prior in register:
        if prior == exposure or (prior.source_id, prior.site_id) != (
                manifest.source_id, manifest.site_id):
            continue
        if prior.exposure == "custodian_unexposed":
            continue
        # Unknown dates cannot establish nonoverlap. Metadata-only known access
        # is allowed, but unknown exposure history always blocks admission.
        if prior.exposure == "known_exposed" and set(prior.content) <= {"metadata", "drivers"}:
            if prior.content:
                continue
        overlaps = prior.period_start is None or not (
            iso_date(prior.period_end) < iso_date(confirmation.start)
            or iso_date(prior.period_start) > iso_date(confirmation.end))
        if overlaps:
            raise ValueError("prior exposure conflicts with proposed confirmation")
    return actual
