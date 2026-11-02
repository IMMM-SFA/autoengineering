"""Authored source tables exercise explicit clocks, intervals and custody order."""

import csv
from dataclasses import replace
from datetime import timedelta
import hashlib
import io
import json
import socket
import subprocess

import pytest

from examples.utility import solar_csv as module
from examples.utility.solar_metadata import SolarMetadataReview
from examples.utility.solar_intervals import SolarAlignmentPlan, instant, stamp
from examples.utility.solar_partitions import SolarPartitionPlan, SolarWindow


def t(minutes):
    return stamp(instant("2020-01-01T00:00:00Z") + timedelta(minutes=minutes))


def review():
    return SolarMetadataReview(
        "utility-solar-metadata-review-v1",
        "1" * 64,
        2107,
        "authored-ac",
        "149583",
        "AC (kW)",
        "kW",
        "avg",
        None,
        (),
        "PST8PDT",
        "5-15 min",
        "L",
        ("authored_fixture_not_site_qualification",),
    )


def table(count=16):
    return [[t((i + 1) * 5), t(i * 5), "300", "2", "600", "20", "4", "good"] for i in range(count)]


def fixture(rows=None, *, encoding="utf-8"):
    rows = table() if rows is None else rows
    headers = ("end", "start", "seconds", "AC (kW)", "POA", "T", "WS", "AC_Q")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(headers)
    writer.writerows(rows)
    blob = stream.getvalue().encode(encoding)
    sensors = tuple(
        module.CsvSensor(
            role=role,
            value_header=value,
            timestamp_header="end" if role in ("ac", "poa") else "start",
            units=units,
            clock="offset_in_text",
            fixed_offset_minutes=None,
            support="end_average" if role in ("ac", "poa") else "instantaneous",
            duration_seconds=None,
            duration_header="seconds" if role in ("ac", "poa") else None,
            availability_delay_seconds=0,
            missing_tokens=("NaN", "-9999"),
            quality_header="AC_Q" if role == "ac" else None,
            quality_good=("good",) if role == "ac" else (),
            quality_bad=("bad",) if role == "ac" else (),
        )
        for role, value, units in (
            ("ac", "AC (kW)", "kW"),
            ("poa", "POA", "W/m2"),
            ("temperature", "T", "C"),
            ("wind", "WS", "m/s"),
        )
    )
    plan = module.SolarCsvPlan(
        "utility-solar-csv-v1",
        hashlib.sha256(blob).hexdigest(),
        review().digest,
        "2" * 64,
        headers,
        sensors,
    )
    return plan, blob


def parsed(rows=None):
    plan, blob = fixture(rows)
    return module.parse_csv(plan, blob, review())


def partition(csv_plan):
    alignment = SolarAlignmentPlan(
        "utility-solar-interval-alignment-v1",
        module.source_binding_digest(csv_plan),
        csv_plan.semantics_review_digest,
        t(0),
        t(80),
        300,
        300,
        "C",
        "m/s",
        "causal_hold",
    )
    return SolarPartitionPlan(
        "utility-solar-partitions-v1",
        alignment,
        tuple(
            SolarWindow(role, t(i * 20), t((i + 1) * 20))
            for i, role in enumerate(("warmup", "fitting", "selection", "confirmation"))
        ),
        review().digest,
        1,
        "forcing_only_continuity_reset_on_driver_gaps",
    )


def test_explicit_source_pins_and_record_roundtrip_without_model_or_network(monkeypatch):
    def denied(*a, **kw):
        pytest.fail("CSV parser attempted external execution")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    plan, blob = fixture()
    original = blob
    result = module.parse_csv(plan, blob, review())
    assert result.row_count == 16 and result.qualification == "not_admitted"
    assert result.ac[0].start == t(0) and result.ac[0].end == t(5)
    assert result.ac[0].available_at == t(5) and result.temperature[0].timestamp == t(0)
    assert module.ParsedSolarCsv.from_json(result.to_json()) == result
    assert module.SolarCsvPlan.from_json(plan.to_json()) == plan
    assert blob == original


def test_mixed_durations_and_gaps_never_infer_support_from_next_timestamp():
    rows = table(3)
    rows[1][:3] = [t(20), t(5), "900"]
    rows[2][:3] = [t(35), t(25), "300"]
    result = parsed(rows)
    assert [(x.start, x.end) for x in result.ac] == [(t(0), t(5)), (t(5), t(20)), (t(30), t(35))]


def test_average_start_and_fixed_duration_are_separate_declared_policy():
    plan, blob = fixture()
    sensors = tuple(
        replace(
            s,
            support="start_average",
            timestamp_header="start",
            duration_seconds=300,
            duration_header=None,
        )
        if s.role in ("ac", "poa")
        else s
        for s in plan.sensors
    )
    result = module.parse_csv(replace(plan, sensors=sensors), blob, review())
    assert result.ac[0].start == t(0) and result.ac[0].end == t(5)


def test_delayed_average_and_sample_availability():
    plan, blob = fixture()
    plan = replace(
        plan, sensors=tuple(replace(s, availability_delay_seconds=60) for s in plan.sensors)
    )
    result = module.parse_csv(plan, blob, review())
    assert result.ac[0].available_at == t(6) and result.temperature[0].available_at == t(1)


def test_missing_tokens_and_bad_quality_are_not_zero_filled():
    rows = table()
    rows[1][3] = "NaN"
    rows[2][3] = "-9999"
    rows[3][7] = "bad"
    result = parsed(rows)
    assert result.ac[1].value is None and result.ac[2].value is None
    assert result.ac[3].value == 2.0 and not result.ac[3].quality_ok
    assert all(not result.ac[i].quality_ok for i in (1, 2, 3))


def test_negative_standby_remains_a_finite_measurement():
    rows = table(1)
    rows[0][3] = "-0.02"
    assert parsed(rows).ac[0].value == -0.02


def test_explicit_offsets_disambiguate_repeated_wall_time():
    rows = table(2)
    for i, offset in enumerate(("-07:00", "-08:00")):
        rows[i][0] = "2020-11-01T01:05:00" + offset
        rows[i][1] = "2020-11-01T01:00:00" + offset
    result = parsed(rows)
    assert result.ac[0].start == "2020-11-01T08:00:00Z"
    assert result.ac[1].start == "2020-11-01T09:00:00Z"


def test_fixed_clock_is_explicit_and_does_not_use_metadata_timezone_code():
    rows = table(1)
    rows[0][0] = rows[0][0][:-1]
    rows[0][1] = rows[0][1][:-1]
    plan, blob = fixture(rows)
    with pytest.raises(ValueError):
        module.parse_csv(plan, blob, review())
    plan = replace(
        plan,
        sensors=tuple(
            replace(s, clock="fixed_utc_offset", fixed_offset_minutes=-480) for s in plan.sensors
        ),
    )
    assert module.parse_csv(plan, blob, review()).ac[0].start == "2020-01-01T08:00:00Z"


@pytest.mark.parametrize(
    "change",
    [
        "hash",
        "metadata",
        "header",
        "duplicate_header",
        "width",
        "empty",
        "utf8",
        "naive",
        "subsecond",
        "invalid_date",
        "overlap",
        "sample_duplicate",
        "duration",
        "quality",
        "inf",
        "object",
        "numeric_code",
        "nul",
        "field",
    ],
)
def test_invalid_source_is_sanitized_without_values_or_context(change):
    rows = table()
    canary = "PRIVATE-CELL-98431"
    if change == "naive":
        rows[0][0] = t(5)[:-1]
    elif change == "subsecond":
        rows[0][0] = "2020-01-01T00:05:00.5Z"
    elif change == "invalid_date":
        rows[0][0] = "2020-02-31T00:05:00Z"
    elif change == "overlap":
        rows[1][0] = t(5)
    elif change == "sample_duplicate":
        rows[1][1] = t(0)
    elif change == "duration":
        rows[0][2] = "5.0"
    elif change == "quality":
        rows[0][7] = canary
    elif change == "inf":
        rows[0][3] = "1e9999"
    elif change == "object":
        rows[0][3] = canary
    elif change == "numeric_code":
        rows[0][3] = "1_000"
    elif change == "nul":
        rows[0][3] = "2\x00"
    elif change == "field":
        rows[0][3] = "2" * (module.MAX_FIELD + 1)
    elif change == "width":
        rows[0].pop()
    elif change == "empty":
        rows = []
    plan, blob = fixture(rows)
    metadata = review()
    if change == "hash":
        blob += b"\n"
    elif change == "metadata":
        metadata = replace(metadata, metric_id="different")
    elif change in ("header", "duplicate_header"):
        replacement = b"unknown" if change == "header" else b"end"
        blob = blob.replace(b"AC (kW)", replacement, 1)
        plan = replace(plan, source_sha256=hashlib.sha256(blob).hexdigest())
    elif change == "utf8":
        blob = b"\xff" + blob
        plan = replace(plan, source_sha256=hashlib.sha256(blob).hexdigest())
    with pytest.raises(ValueError) as caught:
        module.parse_csv(plan, blob, metadata)
    assert str(caught.value) == "solar CSV normalization failed"
    assert caught.value.__context__ is None and caught.value.__cause__ is None
    assert canary not in repr(caught.value)


@pytest.mark.parametrize("kind", ["bytes", "rows", "columns"])
def test_envelope_bounds_are_checked(kind, monkeypatch):
    plan, blob = fixture()
    if kind == "bytes":
        monkeypatch.setattr(module, "MAX_BYTES", len(blob) - 1)
    elif kind == "rows":
        monkeypatch.setattr(module, "MAX_ROWS", 15)
    else:
        monkeypatch.setattr(module, "MAX_COLUMNS", 7)
        with pytest.raises(ValueError):
            replace(plan, headers=plan.headers)
        return
    with pytest.raises(ValueError):
        module.parse_csv(plan, blob, review())


def test_partition_claims_precede_source_access_and_reserved_canaries_stay_private(tmp_path):
    rows = table()
    rows[-1][3] = "987654.25"
    csv_plan, blob = fixture(rows)
    plan = partition(csv_plan)
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    calls = []

    def source():
        assert (public / "preparation-claim.json").exists()
        assert (private / "preparation-claim.json").exists()
        assert not (public / "manifest.json").exists()
        calls.append(1)
        return blob

    manifest = module.prepare_csv(plan, csv_plan, source, review(), public, private)
    assert calls == [1]
    public_bytes = b"".join(p.read_bytes() for p in public.iterdir())
    assert b"987654.25" not in public_bytes and b"AC (kW)" not in public_bytes
    assert json.loads((private / "labels.json").read_text())["ac_kw"][-1] == 987654.25
    assert (
        manifest["source_bytes_verified"] is False
        and manifest["scientific_adapter_admitted"] is False
    )
    with pytest.raises(ValueError):
        module.prepare_csv(plan, csv_plan, source, review(), public, private)
    assert calls == [1]


def test_failed_source_is_consumed_without_disclosing_exception_payload(tmp_path):
    csv_plan, _ = fixture()
    plan = partition(csv_plan)
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)

    def source():
        raise RuntimeError("PRIVATE-SOURCE-ERROR-8123")

    with pytest.raises(ValueError) as caught:
        module.prepare_csv(plan, csv_plan, source, review(), public, private)
    assert "PRIVATE" not in str(caught.value) and caught.value.__context__ is None
    assert (public / "preparation-claim.json").exists() and (
        private / "preparation-claim.json"
    ).exists()
    assert not (public / "manifest.json").exists() and not (private / "manifest.json").exists()


def test_blank_value_and_blank_quality_have_distinct_declared_rules():
    rows = table(1)
    rows[0][3] = ""
    assert parsed(rows).ac[0].value is None
    rows[0][3] = "2"
    rows[0][7] = ""
    plan, blob = fixture(rows)
    with pytest.raises(ValueError):
        module.parse_csv(plan, blob, review())
    plan = replace(plan, sensors=(replace(plan.sensors[0], blank_quality="bad"), *plan.sensors[1:]))
    result = module.parse_csv(plan, blob, review())
    assert result.ac[0].value == 2.0 and not result.ac[0].quality_ok


def test_delayed_poa_is_masked_before_conditional_prediction():
    from examples.utility.solar_intervals import align

    plan, blob = fixture()
    plan = replace(
        plan,
        sensors=tuple(
            replace(s, availability_delay_seconds=60) if s.role == "poa" else s
            for s in plan.sensors
        ),
    )
    source = module.parse_csv(plan, blob, review())
    aligned = tuple(
        align(
            partition(plan).alignment,
            ac=source.ac,
            poa=source.poa,
            temperature=source.temperature,
            wind=source.wind,
        )
    )
    assert len(aligned) == 16
    assert all(not r.drivers_usable and "poa:late_available" in r.reasons for r in aligned)
    assert all(r.poa_w_m2 is None and r.ac_kw is None for r in aligned)


@pytest.mark.parametrize("binding", ["source", "semantics", "metadata", "units"])
def test_mismatched_preparation_starts_no_source_access(tmp_path, binding):
    csv_plan, _ = fixture()
    plan = partition(csv_plan)
    if binding == "metadata":
        plan = replace(plan, hardware_review_digest="3" * 64)
    else:
        field = {
            "source": "source_digest",
            "semantics": "semantics_review_digest",
            "units": "wind_units",
        }[binding]
        plan = replace(
            plan,
            alignment=replace(plan.alignment, **{field: "mph" if binding == "units" else "3" * 64}),
        )
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    calls = []

    def source():
        calls.append(1)
        return b"must not be read"

    with pytest.raises(ValueError):
        module.prepare_csv(plan, csv_plan, source, review(), public, private)
    assert not calls
    assert (public / "preparation-claim.json").exists()
    assert (private / "preparation-claim.json").exists()


def test_raw_units_convert_only_in_existing_alignment_and_reader(tmp_path):
    from examples.utility.solar_inputs import read_development
    from autoengineering.campaign.serialization import digest

    rows = table()
    for row in rows:
        row[5] = "68"
    csv_plan, blob = fixture(rows)
    csv_plan = replace(
        csv_plan,
        sensors=tuple(
            replace(s, units="F")
            if s.role == "temperature"
            else replace(s, units="mph")
            if s.role == "wind"
            else s
            for s in csv_plan.sensors
        ),
    )
    plan = partition(csv_plan)
    plan = replace(plan, alignment=replace(plan.alignment, temperature_units="F", wind_units="mph"))
    raw = module.parse_csv(csv_plan, blob, review())
    assert raw.temperature[0].value == 68.0 and raw.wind[0].value == 4.0
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    manifest = module.prepare_csv(plan, csv_plan, lambda: blob, review(), public, private)
    result = read_development(
        public,
        expected_manifest_digest=digest(manifest),
        expected_preparer_sources=manifest["preparer_sources"],
    )
    assert result.forcing.temperature_c[0] == 20.0
    assert result.forcing.wind_m_s[0] == pytest.approx(1.78816)
