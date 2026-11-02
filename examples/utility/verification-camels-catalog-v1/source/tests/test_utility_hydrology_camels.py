"""Authored CAMELS text tests source integrity and partition preparation."""

from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json

import pytest

from examples.utility.hydrology_camels import CamelsDaymetSource, FORCING_COLUMNS, iter_rows
from examples.utility.hydrology_partitions import DailyHydrologyPlan, DailyWindow, prepare


def fixture(start=date(2000, 2, 27)):
    dates = [start + timedelta(days=i) for i in range(8)]
    forcing = (
        "40.0\n100.0\n1000000\n"
        + " ".join(FORCING_COLUMNS)
        + "\n"
        + "\n".join(f"{d.year} {d.month:02} {d.day:02} 12 40000 3 100 0 10 4 500" for d in dates)
        + "\n"
    ).encode()
    values = ("1", "-999.00", "0", "4", "5", "6", "7", "876543.210987")
    flow = (
        "\n".join(
            f"01491000 {d.year} {d.month:02} {d.day:02} {q} {flag}"
            for d, q, flag in zip(dates, values, ("A", "M", "A", "E", "A", "A", "A", "A"))
        )
        + "\n"
    ).encode()
    source = CamelsDaymetSource(
        "utility-camels-us-daymet-source-v1",
        "01491000",
        hashlib.sha256(forcing).hexdigest(),
        hashlib.sha256(flow).hexdigest(),
        12,
    )
    plan = DailyHydrologyPlan(
        "utility-daily-hydrology-preparation-v1",
        "camels-daymet",
        "usgs-01491000",
        source.digest,
        1.0,
        40.0,
        tuple(
            DailyWindow(role, dates[i * 2].isoformat(), dates[i * 2 + 1].isoformat())
            for i, role in enumerate(("warmup", "fitting", "selection", "confirmation"))
        ),
        ("A",),
    )
    return source, plan, forcing, flow


def rebind(source, plan, forcing, flow):
    source = replace(
        source,
        forcing_sha256=hashlib.sha256(forcing).hexdigest(),
        streamflow_sha256=hashlib.sha256(flow).hexdigest(),
    )
    return source, replace(plan, declared_source_digest=source.digest), forcing, flow


def test_authored_raw_to_prepared_roles_and_site_lifecycle(tmp_path):
    from autoengineering.adapters.python import run_lifecycle
    from examples.utility.hydrology import BASELINE, physical_checks
    from examples.utility.hydrology_site import SiteHydrologyAdapter, prepared_development

    source, plan, forcing, flow = fixture()
    rows = tuple(iter_rows(source, plan, forcing, flow))
    assert rows[1].flow_cfs is None and rows[1].flow_flag == "M"
    assert rows[2].flow_cfs == 0.0 and rows[3].flow_flag == "E"
    assert rows[2].date == "2000-02-29"
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    manifest = prepare(plan, iter_rows(source, plan, forcing, flow), public, private)
    assert manifest["plan"]["declared_source_digest"] == source.digest
    fit = json.loads((public / "fitting.json").read_bytes())
    assert fit["mask"] == [False, False, True, False, False, False]
    assert fit["labels"] == [0.0] * 6  # A measured zero remains usable.
    assert b"876543.210987" not in b"".join(p.read_bytes() for p in public.iterdir())
    document = json.loads((public / "forcing.json").read_bytes())
    site, ctx, inputs = prepared_development(plan, document, BASELINE, tmp_path, role="selection")
    result = run_lifecycle(
        SiteHydrologyAdapter(site), ctx, inputs, ctx.model.inputs, ctx.model.outputs
    )
    assert all(c.status == "pass" for c in physical_checks(result.outputs, inputs, BASELINE))
    # Checksum verification by this parser does not change the preparer's admission flags.
    assert manifest["source_bytes_verified"] is False
    assert manifest["scientific_adapter_admitted"] is False


@pytest.mark.parametrize("which", ["forcing", "flow"])
def test_changed_bytes_refuse_before_date_parsing(which, monkeypatch):
    import examples.utility.hydrology_camels as module

    source, plan, forcing, flow = fixture()

    def forbidden(*args):
        raise AssertionError("checksum failure reached source row parsing")

    monkeypatch.setattr(module, "_date", forbidden)
    if which == "forcing":
        forcing += b" "
    else:
        flow += b" "
    with pytest.raises(ValueError, match="^CAMELS Daymet parsing failed$") as error:
        next(iter_rows(source, plan, forcing, flow))
    assert error.value.__suppress_context__


@pytest.mark.parametrize(
    "change",
    [
        "columns",
        "area",
        "latitude",
        "hour",
        "date",
        "gauge",
        "negative_flow",
        "nonfinite",
        "missing_driver",
        "negative_precip",
        "temp_order",
        "duplicate",
        "reorder",
        "truncated",
        "extra",
        "line",
        "encoding",
        "flag",
    ],
)
def test_unsupported_source_refuses_before_yielding_any_rows(change):
    source, plan, forcing, flow = fixture()
    if change == "columns":
        forcing = forcing.replace(b"prcp(mm/day)", b"prcp(in/day)")
    elif change == "area":
        forcing = forcing.replace(b"1000000\n", b"2000000\n")
    elif change == "latitude":
        forcing = forcing.replace(b"40.0\n", b"41.0\n")
    elif change == "hour":
        forcing = forcing.replace(b" 12 ", b" 0 ")
    elif change == "date":
        flow = flow.replace(b"2000 03 05", b"2000 03 06")
    elif change == "gauge":
        flow = flow.replace(b"01491000", b"02472000")
    elif change == "negative_flow":
        flow = flow.replace(b"876543.210987", b"-888")
    elif change == "nonfinite":
        flow = flow.replace(b"876543.210987", b"nan")
    elif change == "missing_driver":
        forcing = forcing.replace(b" 10 4 ", b" -999 -999 ")
    elif change == "negative_precip":
        forcing = forcing.replace(b" 3 100 ", b" -1 100 ")
    elif change == "temp_order":
        forcing = forcing.replace(b" 10 4 ", b" 4 10 ")
    elif change in ("duplicate", "reorder"):
        driver_lines, flow_lines = forcing.splitlines(), flow.splitlines()
        if change == "duplicate":
            driver_lines[-1], flow_lines[-1] = driver_lines[-2], flow_lines[-2]
        else:
            driver_lines[-1], driver_lines[-2] = driver_lines[-2], driver_lines[-1]
            flow_lines[-1], flow_lines[-2] = flow_lines[-2], flow_lines[-1]
        forcing, flow = b"\n".join(driver_lines), b"\n".join(flow_lines)
    elif change == "truncated":
        flow = b"\n".join(flow.splitlines()[:-1])
    elif change == "extra":
        forcing += forcing.splitlines()[-1] + b"\n"
        flow += flow.splitlines()[-1] + b"\n"
    elif change == "line":
        flow += b"x" * 1025
    elif change == "encoding":
        flow += b"\xff"
    else:
        flow = flow.replace(b" A\n", b" \x00\n")
    with pytest.raises(ValueError) as error:
        next(iter_rows(*rebind(source, plan, forcing, flow)))
    assert str(error.value) == "CAMELS Daymet parsing failed"
    assert "876543" not in str(error.value)


def test_frozen_zero_hour_is_supported_without_date_shift():
    source, plan, forcing, flow = fixture()
    forcing = forcing.replace(b" 12 ", b" 0 ")
    source, plan, forcing, flow = rebind(replace(source, forcing_hour=0), plan, forcing, flow)
    rows = tuple(iter_rows(source, plan, forcing, flow))
    assert rows[0].date == plan.windows[0].start


@pytest.mark.parametrize(
    "change",
    [
        {"gauge_id": "1491000"},
        {"gauge_id": "abcdefgh"},
        {"forcing_hour": 6},
        {"forcing_hour": True},
    ],
)
def test_bad_source_declarations(change):
    source, _, _, _ = fixture()
    with pytest.raises((ValueError, TypeError)):
        replace(source, **change)


def test_source_plan_and_resource_bounds(monkeypatch):
    import examples.utility.hydrology_camels as module

    source, plan, forcing, flow = fixture()
    for bad in (
        replace(plan, site_id="usgs-02472000"),
        replace(plan, declared_source_digest="0" * 64),
    ):
        with pytest.raises(ValueError):
            next(iter_rows(source, bad, forcing, flow))
    monkeypatch.setattr(module, "MAX_BYTES", 8)
    with pytest.raises(ValueError):
        next(iter_rows(source, plan, forcing, flow))
    monkeypatch.setattr(module, "MAX_BYTES", 4 * 1024 * 1024)
    monkeypatch.setattr(module, "MAX_ROWS", 2)
    with pytest.raises(ValueError):
        next(iter_rows(source, plan, forcing, flow))


def test_preparer_claims_before_parsing_and_refuses_reuse(tmp_path, monkeypatch):
    import examples.utility.hydrology_camels as module

    source, plan, forcing, flow = fixture()
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    original = module._parse
    calls = []

    def guarded(*args):
        assert (public / "preparation-claim.json").is_file()
        assert (private / "preparation-claim.json").is_file()
        calls.append(1)
        return original(*args)

    monkeypatch.setattr(module, "_parse", guarded)
    with pytest.raises(ValueError, match="^daily hydrology preparation failed$"):
        prepare(
            plan, iter_rows(source, plan, forcing, flow + b"PRIVATE-ERROR-CANARY"), public, private
        )
    assert len(calls) == 1
    assert {p.name for p in public.iterdir()} == {"preparation-claim.json"}
    assert {p.name for p in private.iterdir()} == {"preparation-claim.json"}
    with pytest.raises(ValueError):
        prepare(plan, iter_rows(source, plan, forcing, flow), public, private)
    assert len(calls) == 1


def archive_source(original):
    from examples.utility.hydrology_camels import CamelsArchiveDaymetSource

    return CamelsArchiveDaymetSource(
        gauge_id=original.gauge_id,
        forcing_sha256=original.forcing_sha256,
        streamflow_sha256=original.streamflow_sha256,
        forcing_hour=original.forcing_hour,
        schema="utility-camels-us-daymet-source-v2",
        archive_sha256="a" * 64,
        archive_metadata_sha256="b" * 64,
        huc02="02",
    )


def test_archive_source_roundtrip_binds_version_and_preserves_published_dates():
    original, plan, forcing, flow = fixture()
    source = archive_source(original)
    assert CamelsDaymetSource.from_json(source.to_json()) == source
    assert CamelsDaymetSource.from_json(original.to_json()) == original
    assert source.forcing_member == (
        "basin_dataset_public_v1p2/basin_mean_forcing/daymet/02/01491000_lump_cida_forcing_leap.txt"
    )
    assert source.streamflow_member.endswith("/usgs_streamflow/02/01491000_streamflow_qc.txt")
    assert source.physical_interval == "unresolved"
    assert source.archive_membership_verified is False
    assert replace(source, archive_sha256="c" * 64).digest != source.digest
    assert replace(source, archive_metadata_sha256="c" * 64).digest != source.digest
    with pytest.raises(ValueError):
        tuple(iter_rows(source, plan, forcing, flow))  # Old plan cannot inherit a new identity.
    bound = replace(plan, declared_source_digest=source.digest)
    assert tuple(iter_rows(source, bound, forcing, flow)) == tuple(
        iter_rows(original, plan, forcing, flow)
    )


@pytest.mark.parametrize(
    "change",
    [
        {"product": "daymet-v4r1"},
        {"archive_name": "modern-daymet.nc"},
        {"date_policy": "choose-lag-by-performance"},
        {"calendar_policy": "interpolate-missing-days"},
        {"physical_interval": "UTC-midnight-to-midnight"},
        {"archive_membership_verified": True},
        {"huc02": "2"},
        {"huc02": "00"},
        {"huc02": "19"},
        {"huc02": "../"},
    ],
)
def test_archive_source_rejects_product_substitution_and_unverified_timing(change):
    source = archive_source(fixture()[0])
    with pytest.raises((ValueError, TypeError)):
        replace(source, **change)


def test_missing_leap_year_december_31_cannot_be_filled_or_shifted():
    original, plan, forcing, flow = fixture(date(2000, 12, 27))
    source = archive_source(original)
    forcing = (
        b"\n".join(line for line in forcing.splitlines() if not line.startswith(b"2000 12 31 "))
        + b"\n"
    )
    flow = (
        b"\n".join(
            line for line in flow.splitlines() if not line.startswith(b"01491000 2000 12 31 ")
        )
        + b"\n"
    )
    source, plan, forcing, flow = rebind(source, plan, forcing, flow)
    with pytest.raises(ValueError, match="^CAMELS Daymet parsing failed$"):
        next(iter_rows(source, plan, forcing, flow))


@pytest.mark.parametrize("versioned", [False, True])
@pytest.mark.parametrize("allowed", [("A",), ("A", "A:e"), ("A", "A:e", "M")])
def test_documented_estimated_flag_is_preserved_and_explicitly_masked(tmp_path, versioned, allowed):
    source, plan, forcing, flow = fixture()
    # The legacy README uses A:e, not the generic authored fixture's E flag.
    flow = flow.replace(b" 4 E\n", b" 4 A:e\n")
    source, plan, forcing, flow = rebind(source, plan, forcing, flow)
    if versioned:
        source = archive_source(source)
        plan = replace(plan, declared_source_digest=source.digest)
    plan = replace(plan, allowed_flow_flags=allowed)
    rows = tuple(iter_rows(source, plan, forcing, flow))
    assert rows[3].flow_flag == "A:e" and rows[3].flow_cfs == 4.0
    assert rows[1].flow_flag == "M" and rows[1].flow_cfs is None
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    prepare(plan, iter_rows(source, plan, forcing, flow), public, private)
    fit = json.loads((public / "fitting.json").read_bytes())
    assert fit["mask"][3] is ("A:e" in allowed)
    expected = 4.0 * 0.3048**3 * 86400 * 1000 / (plan.area_km2 * 1e6)
    assert fit["labels"][3] == (expected if "A:e" in allowed else 0.0)
    assert fit["mask"][1] is False
    assert b"876543.210987" not in b"".join(p.read_bytes() for p in public.iterdir())
    assert (
        replace(plan, allowed_flow_flags=("A",)).digest
        != replace(plan, allowed_flow_flags=("A", "A:e")).digest
    )
