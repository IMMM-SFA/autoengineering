"""Authored partition canaries, quality masks and immutable preparation."""

from dataclasses import replace
from datetime import date, timedelta
import hashlib
import json
import stat
import runpy

import pytest

from examples.utility.hydrology_partitions import (
    DailyHydrologyPlan,
    DailyHydrologyRow,
    DailyWindow,
    prepare,
)


def fixture(tmp_path):
    plan = DailyHydrologyPlan(
        "utility-daily-hydrology-preparation-v1",
        "authored",
        "authored-basin",
        "1" * 64,
        1.0,
        40.0,
        tuple(
            DailyWindow(role, date, date)
            for role, date in (
                ("warmup", "2000-02-27"),
                ("fitting", "2000-02-28"),
                ("selection", "2000-02-29"),
                ("confirmation", "2000-03-01"),
            )
        ),
        ("A",),
    )
    rows = tuple(
        DailyHydrologyRow(date, 3.0, 4.0, 10.0, value, "A")
        for date, value in (
            ("2000-02-27", 11.0),
            ("2000-02-28", 1.0),
            ("2000-02-29", 2.0),
            ("2000-03-01", 876543.210987),
        )
    )
    public, private = tmp_path / "public", tmp_path / "private"
    public.mkdir(mode=0o700)
    private.mkdir(mode=0o700)
    return plan, rows, public, private


def test_labels_and_future_drivers_stay_in_their_scopes(tmp_path):
    from pathlib import Path
    import examples.utility.hydrology_partitions as module

    plan, rows, public, private = fixture(tmp_path)
    rows = (*rows[:-1], replace(rows[-1], precip_mm=765432.109876))
    original = tuple(row.to_json() for row in rows)
    manifest = prepare(plan, rows, public, private)
    assert (
        manifest["preparer_source_digest"]
        == hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
    )
    payload = b"".join(p.read_bytes() for p in public.iterdir())
    assert b"876543.210987" not in payload and b"765432.109876" not in payload
    assert str(private).encode() not in payload
    assert json.loads((public / "forcing.json").read_text())["dates"] == [r.date for r in rows[:3]]
    assert json.loads((public / "forcing.json").read_text())["day_of_year"] == [58, 59, 60]
    fitting = json.loads((public / "fitting.json").read_text())
    selection = json.loads((public / "selection.json").read_text())
    assert fitting["mask"] == [False, True, False]
    assert selection["mask"] == [False, False, True]
    assert fitting["labels"] == pytest.approx([0.0, 2.4465755455488, 0.0])
    assert selection["labels"] == pytest.approx([0.0, 0.0, 2 * 2.4465755455488])
    labels = json.loads((private / "labels.json").read_text())
    assert set(labels) == {"labels", "mask"}
    assert labels["mask"] == [False, False, False, True]
    assert labels["labels"][-1] == pytest.approx(rows[-1].flow_cfs * 2.4465755455488)
    assert str(labels["labels"][-1]).encode() not in payload
    assert len(json.loads((private / "forcing.json").read_text())["dates"]) == 4
    assert all(
        manifest[key] is False
        for key in (
            "source_bytes_verified",
            "scientific_adapter_admitted",
            "exposure_attested",
            "private_boundary_qualified",
        )
    )
    assert original == tuple(row.to_json() for row in rows)
    for path in (*public.iterdir(), *private.iterdir()):
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    for name, expected in manifest["files"].items():
        assert hashlib.sha256((public / name).read_bytes()).hexdigest() == expected


def test_reuse_refuses_before_consuming_rows(tmp_path):
    plan, rows, public, private = fixture(tmp_path)
    prepare(plan, rows, public, private)
    before = {str(p): p.read_bytes() for root in (public, private) for p in root.iterdir()}

    def forbidden():
        raise AssertionError("occupied scope consumed data")
        yield

    with pytest.raises(ValueError, match="preparation failed"):
        prepare(plan, forbidden(), public, private)
    assert before == {str(p): p.read_bytes() for root in (public, private) for p in root.iterdir()}


@pytest.mark.parametrize(
    "change", ["duplicate", "missing", "order", "bad_flag", "missing_label", "bad_value"]
)
def test_bad_rows_publish_no_data_or_private_error_text(tmp_path, change):
    plan, rows, public, private = fixture(tmp_path)
    if change == "duplicate":
        rows = (*rows[:2], rows[1], rows[-1])
    elif change == "missing":
        rows = rows[:-1]
    elif change == "order":
        rows = tuple(reversed(rows))
    elif change == "bad_flag":
        rows = (*rows[:-1], replace(rows[-1], flow_flag="REJECT"))
    elif change == "missing_label":
        rows = (*rows[:-1], replace(rows[-1], flow_cfs=None))
    else:
        values = rows[-1].to_dict() | {"flow_cfs": "PRIVATE-LABEL-CANARY"}
        rows = (*rows[:-1], values)
    with pytest.raises(ValueError) as error:
        prepare(plan, rows, public, private)
    assert str(error.value) == "daily hydrology preparation failed"
    assert error.value.__suppress_context__
    assert not (public / "manifest.json").exists()
    assert not (private / "labels.json").exists()
    assert set(p.name for p in public.iterdir()) <= {"preparation-claim.json"}


def test_scopes_and_windows_refuse_before_iteration(tmp_path):
    plan, rows, public, private = fixture(tmp_path)
    with pytest.raises(ValueError, match="contiguous"):
        replace(plan, windows=(*plan.windows[:3], replace(plan.windows[-1], start="2000-02-29")))
    link = tmp_path / "linked"
    link.symlink_to(private)
    with pytest.raises(ValueError, match="preparation failed"):
        prepare(plan, iter(rows), public, link)
    assert not list(public.iterdir())
    with pytest.raises(ValueError, match="preparation failed"):
        prepare(plan, iter(rows), public, public)
    assert not list(public.iterdir())


def test_partial_write_keeps_claims_and_original_private_artifact(tmp_path, monkeypatch):
    import examples.utility.hydrology_partitions as module

    plan, rows, public, private = fixture(tmp_path)
    original = module.durable_write

    def interrupted(path, raw):
        if path == private / "labels.json":
            raise OSError("PRIVATE-PATH-CANARY")
        return original(path, raw)

    monkeypatch.setattr(module, "durable_write", interrupted)
    with pytest.raises(ValueError, match="preparation failed") as error:
        prepare(plan, rows, public, private)
    assert "CANARY" not in str(error.value)
    assert (private / "forcing.json").exists()
    assert not (public / "manifest.json").exists()
    saved = (private / "forcing.json").read_bytes()
    monkeypatch.setattr(module, "durable_write", original)
    with pytest.raises(ValueError, match="preparation failed"):
        prepare(plan, rows, public, private)
    assert (private / "forcing.json").read_bytes() == saved


def test_claims_precede_row_access_and_quality_masks_are_role_specific(tmp_path):
    plan, _, public, private = fixture(tmp_path)
    plan = replace(
        plan,
        windows=tuple(
            DailyWindow(*values)
            for values in (
                ("warmup", "2000-02-27", "2000-02-27"),
                ("fitting", "2000-02-28", "2000-02-29"),
                ("selection", "2000-03-01", "2000-03-02"),
                ("confirmation", "2000-03-03", "2000-03-04"),
            )
        ),
    )
    rows = tuple(
        DailyHydrologyRow(
            (date(2000, 2, 27) + timedelta(days=i)).isoformat(),
            3.0,
            4.0,
            10.0,
            None if i == 5 else float(i + 1),
            "REJECT" if i in (1, 4) else "A",
        )
        for i in range(7)
    )

    def guarded():
        for path, scope in ((public, "public"), (private, "private")):
            claim = json.loads((path / "preparation-claim.json").read_text())
            assert claim["scope"] == scope and claim["plan_digest"] == plan.digest
        yield from rows

    prepare(plan, guarded(), public, private)
    fitting = json.loads((public / "fitting.json").read_text())
    selection = json.loads((public / "selection.json").read_text())
    final = json.loads((private / "labels.json").read_text())
    assert fitting["mask"] == [False, False, True, False, False]
    assert selection["mask"] == [False, False, False, True, False]
    assert final["mask"] == [False] * 6 + [True]
    assert all(value == 0.0 for value, keep in zip(final["labels"], final["mask"]) if not keep)


def test_reserved_label_format_is_consumed_by_fixed_rmse_worker(tmp_path, capsys):
    from pathlib import Path
    from autoengineering.utility import private_score_worker

    plan, rows, public, private = fixture(tmp_path)
    prepare(plan, rows, public, private)
    labels = json.loads((private / "labels.json").read_text())
    predictions = [
        value if keep else 999.0 for value, keep in zip(labels["labels"], labels["mask"])
    ]
    (private / "job.json").write_text(
        json.dumps({"prediction": predictions, "outcome": "rmse", "units": "mm/day"})
    )
    script = private / "score.py"
    script.write_bytes(Path(private_score_worker.__file__).read_bytes())
    runpy.run_path(str(script), run_name="__main__")
    score = json.loads(capsys.readouterr().out)
    assert score["status"] == "success" and score["feasible"] is True
    assert score["value"] == 0.0 and score["units"] == "mm/day"


def test_row_iterator_exception_does_not_export_values_or_paths(tmp_path):
    plan, _, public, private = fixture(tmp_path)

    def broken():
        raise RuntimeError("PRIVATE-CANARY-" + str(private))
        yield

    with pytest.raises(ValueError) as error:
        prepare(plan, broken(), public, private)
    assert str(error.value) == "daily hydrology preparation failed"
    assert not (public / "manifest.json").exists()
    assert not (private / "labels.json").exists()
