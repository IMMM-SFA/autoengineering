"""Metadata contracts cannot manufacture independent confirmation evidence."""
from dataclasses import replace

import pytest

from autoengineering.utility.exposure import ExposureRecord, PartitionManifest, TimePartition

H = "1" * 64


def exposure():
    return ExposureRecord("source", "site", [H], "2026-10-28", "2020-01-01", "2020-12-31",
                          [], "custodian_unexposed", [], ["custodian"], ["metadata"], H, H)


def manifest():
    return PartitionManifest(
        "utility-partitions-v1", "source", "site", exposure().digest,
        [TimePartition("fitting", "2018-01-01", "2018-12-31", H),
         TimePartition("selection", "2019-01-10", "2019-12-20", H),
         TimePartition("confirmation", "2020-01-01", "2020-12-31", H)],
        7, 7, 30, H, "causal_drivers_only", H, H, "fitting", H, H)


def test_roundtrip_and_custody_binding():
    m = manifest()
    assert PartitionManifest.from_json(m.to_json()) == m
    m.check_exposure(exposure())
    with pytest.raises(ValueError, match="identity"):
        m.check_exposure(replace(exposure(), rights_digest="2" * 64))


@pytest.mark.parametrize("field,value", [("source_hashes", []), ("rights_digest", None),
                                         ("custodian_attestation_digest", None),
                                         ("people_or_workers", []), ("access_date", None)])
def test_unexposed_requires_evidence(field, value):
    with pytest.raises(ValueError, match="custody"):
        replace(exposure(), **{field: value})


def test_unknown_history_remains_blocked():
    e = replace(exposure(), exposure="unknown_exposure", rights_digest=None)
    assert e.admission_blockers() == ("unknown_exposure", "missing_rights_digest")
    m = replace(manifest(), exposure_digest=e.digest)
    with pytest.raises(ValueError, match="not admitted"):
        m.check_exposure(e)


def test_overlap_and_insufficient_embargo():
    m = manifest()
    with pytest.raises(ValueError, match="feature window"):
        replace(m, embargo_days=6)
    with pytest.raises(ValueError, match="overlap"):
        replace(m, partitions=(*m.partitions[:2], replace(m.partitions[2], start="2019-12-20")))
    with pytest.raises(ValueError, match="ordered"):
        replace(m, partitions=tuple(reversed(m.partitions)))


def test_date_and_period_coverage():
    with pytest.raises(ValueError, match="ISO"):
        replace(exposure(), access_date="20261028")
    e = replace(exposure(), period_end="2020-06-30")
    with pytest.raises(ValueError, match="cover"):
        replace(manifest(), exposure_digest=e.digest).check_exposure(e)


def test_prior_exposure_cannot_be_erased_by_new_custody_record():
    from autoengineering.campaign.serialization import digest
    from autoengineering.utility.exposure import admit_partition
    e = exposure()
    prior = replace(e, exposure="known_exposed", content=["aggregates"], uses=["old-study"])
    register = (prior, e)
    pin = digest([record.to_dict() for record in register])
    with pytest.raises(ValueError, match="prior exposure"):
        admit_partition(manifest(), e, register, pin)
    with pytest.raises(ValueError, match="register identity"):
        admit_partition(manifest(), e, (e,), pin)
    historical = replace(prior, period_start="2018-01-01", period_end="2019-12-31")
    register = (historical, e)
    pin = digest([record.to_dict() for record in register])
    assert admit_partition(manifest(), e, register, pin) == pin
