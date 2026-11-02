"""Authored solar partition canaries, driver continuity and manifest-last commits."""

from dataclasses import replace
import json

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import solar_partitions as module
from examples.utility import solar_intervals as alignment
from test_utility_solar_intervals import t, avg, sample


def fixture(tmp_path, *, missing_ac=(), missing_driver=()):
    raw_plan = alignment.SolarAlignmentPlan(
        "utility-solar-interval-alignment-v1",
        "1" * 64,
        "2" * 64,
        t(0),
        t(80),
        300,
        300,
        "C",
        "m/s",
        "causal_hold",
    )
    windows = tuple(
        module.SolarWindow(role, t(i * 20), t((i + 1) * 20))
        for i, role in enumerate(("warmup", "fitting", "selection", "confirmation"))
    )
    plan = module.SolarPartitionPlan(
        "utility-solar-partitions-v1",
        raw_plan,
        windows,
        "3" * 64,
        1,
        "forcing_only_continuity_reset_on_driver_gaps",
    )
    source = alignment.align(
        raw_plan,
        ac=[
            avg(
                i * 5,
                (i + 1) * 5,
                None if i in missing_ac else (987654.25 if i == 15 else 2),
                quality=i not in missing_ac,
            )
            for i in range(16)
        ],
        poa=[
            avg(
                i * 5,
                (i + 1) * 5,
                None if i in missing_driver else (876543.5 if i == 15 else 600),
                quality=i not in missing_driver,
            )
            for i in range(16)
        ],
        temperature=[sample(i * 5, 20) for i in range(16)],
        wind=[sample(i * 5, 4) for i in range(16)],
    )
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    return plan, tuple(source), public, private


def read(root, name):
    return json.loads((root / name).read_text())


def test_confirmation_labels_and_drivers_never_enter_public_bundle(tmp_path):
    plan, rows, public, private = fixture(tmp_path)
    original = tuple(r.to_json() for r in rows)
    manifest = module.prepare(plan, rows, public, private)
    public_bytes = b"".join(p.read_bytes() for p in public.iterdir())
    assert b"987654.25" not in public_bytes and b"876543.5" not in public_bytes
    assert str(private).encode() not in public_bytes
    assert len(read(public, "forcing.json")["start"]) == 12
    assert len(read(private, "forcing.json")["start"]) == 16
    labels = read(private, "labels.json")
    assert labels["score_mask"] == [False] * 12 + [True] * 4
    assert labels["ac_kw"][:12] == [None] * 12 and labels["ac_kw"][-1] == 987654.25
    assert read(public, "fitting.json")["score_mask"] == [False] * 4 + [True] * 4 + [False] * 4
    assert read(public, "selection.json")["score_mask"] == [False] * 8 + [True] * 4
    assert tuple(r.to_json() for r in rows) == original
    assert all(
        manifest[key] is False
        for key in (
            "source_bytes_verified",
            "exposure_attested",
            "scientific_adapter_admitted",
            "private_boundary_qualified",
        )
    )
    assert digest(read(private, "manifest.json")) == manifest["private_bundle_digest"]


def test_missing_ac_does_not_reset_model_driver_history(tmp_path):
    plan, rows, public, private = fixture(tmp_path, missing_ac=(5,))
    module.prepare(plan, rows, public, private)
    forcing = read(public, "forcing.json")
    assert forcing["drivers_usable"] == [True] * 12 and forcing["segment_id"] == [0] * 12
    mask = read(public, "fitting.json")["score_mask"]
    assert mask[4:8] == [True, False, True, True]


def test_driver_gap_requires_new_segment_warmup_without_reset_at_role_boundary(tmp_path):
    plan, rows, public, private = fixture(tmp_path, missing_driver=(6,))
    module.prepare(plan, rows, public, private)
    forcing = read(public, "forcing.json")
    assert forcing["segment_id"][6:9] == [None, 1, 1]
    assert read(public, "fitting.json")["score_mask"][4:8] == [True, True, False, False]
    assert read(public, "selection.json")["score_mask"][8] is True


def test_claims_precede_iterator_and_private_manifest_precedes_public(tmp_path, monkeypatch):
    plan, rows, public, private = fixture(tmp_path)
    order = []
    original = module.durable_write

    def record(path, data):
        order.append(path)
        return original(path, data)

    monkeypatch.setattr(module, "durable_write", record)

    def iterator():
        assert (public / "preparation-claim.json").exists() and (
            private / "preparation-claim.json"
        ).exists()
        yield from rows

    module.prepare(plan, iterator(), public, private)
    assert (
        order.index(private / "manifest.json")
        < order.index(public / "forcing.json")
        < order.index(public / "manifest.json")
    )


def test_private_error_is_sanitized_and_consumed_preparation_cannot_retry(tmp_path):
    plan, rows, public, private = fixture(tmp_path)

    def broken():
        assert (private / "preparation-claim.json").exists()
        raise RuntimeError("AUTHORED-PRIVATE-CANARY")
        yield

    with pytest.raises(ValueError) as observed:
        module.prepare(plan, broken(), public, private)
    assert str(observed.value) == "solar partition preparation failed"
    assert observed.value.__cause__ is observed.value.__context__ is None
    assert not (public / "manifest.json").exists()
    with pytest.raises(ValueError):
        module.prepare(plan, rows, public, private)


def test_incomplete_role_or_axis_never_publishes_bundle(tmp_path):
    plan, rows, public, private = fixture(tmp_path, missing_ac=(8, 9, 10, 11))
    with pytest.raises(ValueError):
        module.prepare(plan, rows, public, private)
    assert not (public / "manifest.json").exists() and not (private / "labels.json").exists()


def test_wrong_axis_and_incorrect_window_boundaries_refuse(tmp_path):
    plan, rows, public, private = fixture(tmp_path)
    with pytest.raises(ValueError):
        module.prepare(plan, rows[:-1], public, private)
    assert not (public / "manifest.json").exists()
    with pytest.raises(ValueError):
        replace(plan, windows=(replace(plan.windows[0], end=t(19)), *plan.windows[1:]))


def test_nonempty_and_nested_roots_are_preserved(tmp_path):
    plan, rows, public, private = fixture(tmp_path)
    (public / "keep.txt").write_text("preserve")
    with pytest.raises(ValueError):
        module.prepare(plan, rows, public, private)
    assert (public / "keep.txt").read_text() == "preserve" and list(private.iterdir()) == []
    child = private / "child"
    child.mkdir(mode=0o700)
    with pytest.raises(ValueError):
        module.prepare(plan, rows, private, child)
    assert list(child.iterdir()) == []


def test_same_clock_rows_from_different_units_or_age_policy_refuse(tmp_path):
    plan, rows, public, private = fixture(tmp_path)
    changed = replace(plan, alignment=replace(plan.alignment, max_sample_age_seconds=600))
    with pytest.raises(ValueError):
        module.prepare(changed, rows, public, private)
    assert not (public / "manifest.json").exists() and not (private / "labels.json").exists()


def test_rows_from_different_alignment_implementation_refuse(tmp_path):
    plan, rows, public, private = fixture(tmp_path)
    changed = (replace(rows[0], alignment_implementation_digest="0" * 64), *rows[1:])
    with pytest.raises(ValueError):
        module.prepare(plan, changed, public, private)
    assert not (public / "manifest.json").exists() and not (private / "labels.json").exists()
