"""PVDAQ metadata links require keys, never suggestive names or array order."""

import copy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from examples.utility.solar_metadata import review_ac_metadata, SolarMetadataReview

KEY = "inv_01_ac_power_inv_149583"
SNAPSHOT = Path(__file__).resolve().parents[1] / (
    "examples/utility/proposals/confirmation-v2/metadata-refresh/2107_system_metadata.json"
)


def source():
    return json.loads(SNAPSHOT.read_bytes())


def review(value):
    content = json.dumps(value).encode()
    return review_ac_metadata(
        content,
        expected_sha256=hashlib.sha256(content).hexdigest(),
        system_id=2107,
        channel_key=KEY,
    )


def linked():
    value = source()
    value["Metrics"][KEY]["source_id"] = 29943
    inverter = value["Inverters"]["Inverter 0"]
    inverter["modules_per_string"] = "12"
    inverter["num_strings"] = 10
    value["Modules"]["Module 0"]["inverter_id"] = "29943"
    return value


def test_pinned_source_resolves_csv_header_but_refuses_name_and_order_hardware_joins(monkeypatch):
    content = SNAPSHOT.read_bytes()

    def forbidden(*args, **kwargs):
        pytest.fail("metadata review attempted network or a process")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = review_ac_metadata(
        content,
        expected_sha256="17e4f7f448fcb2bec43f7610b40c1f7f4fc794ccc185e41dcde0514afba73ae5",
        system_id=2107,
        channel_key=KEY,
    )
    assert result.csv_header == "inv_01_ac_power (kW)"
    assert result.inverter_id is None and result.module_ids == ()
    assert result.blockers[:3] == (
        "ac_channel_inverter_join_missing",
        "module_inverter_join_missing",
        "string_topology_missing",
    )
    assert result.qualification == "not_admitted"
    assert result.timezone_code == "PST8PDT" and result.data_time_resolution == "5-15 min"
    assert SolarMetadataReview.from_json(result.to_json()) == result


def test_explicit_keys_resolve_independent_of_order_but_do_not_admit_timing_or_equipment():
    value = linked()
    before = copy.deepcopy(value)
    value["Inverters"] = dict(reversed(list(value["Inverters"].items())))
    value["Modules"] = dict(reversed(list(value["Modules"].items())))
    result = review(value)
    assert result.inverter_id == "29943" and result.module_ids == ("55773",)
    assert not any("join_missing" in v or "topology_missing" in v for v in result.blockers)
    assert result.inverter_time_interval_code == "L"
    assert "timestamp_support_and_availability_unqualified" in result.blockers
    assert result.qualification == "not_admitted"
    assert value == before


def test_dangling_device_id_is_not_repaired_from_sensor_name():
    value = linked()
    value["Metrics"][KEY]["source_id"] = 99999
    assert review(value).inverter_id is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("calc_scale", 1000),
        ("calc_offset", 1),
        ("calc_details", "eval('bad')"),
        ("aggregation_type", "sample"),
        ("units", "W"),
        ("raw_units", "W"),
        ("offline", True),
        ("source_id", True),
        ("metric_id", True),
    ],
)
def test_unreviewed_semantics_and_boolean_keys_refuse(field, value):
    data = linked()
    data["Metrics"][KEY][field] = value
    with pytest.raises(ValueError) as caught:
        review(data)
    assert str(caught.value) == "solar AC metadata review failed"
    assert caught.value.__cause__ is caught.value.__context__ is None


@pytest.mark.parametrize("which", ["header", "metric_id", "inverter_id", "module_id"])
def test_duplicate_identities_refuse(which):
    data = linked()
    if which in ("header", "metric_id"):
        row = copy.deepcopy(data["Metrics"][KEY])
        row["metric_id" if which == "header" else "sensor_name"] = (
            999999 if which == "header" else "other-header"
        )
        data["Metrics"]["duplicate"] = row
    elif which == "inverter_id":
        data["Inverters"]["duplicate"] = copy.deepcopy(data["Inverters"]["Inverter 0"])
    else:
        data["Modules"]["duplicate"] = copy.deepcopy(data["Modules"]["Module 0"])
    with pytest.raises(ValueError):
        review(data)


def test_wrong_hash_duplicate_json_keys_and_wrong_system_refuse():
    content = SNAPSHOT.read_bytes()
    with pytest.raises(ValueError):
        review_ac_metadata(content, expected_sha256="0" * 64, system_id=2107, channel_key=KEY)
    content = b'{"System":{},"System":{}}'
    with pytest.raises(ValueError):
        review_ac_metadata(
            content,
            expected_sha256=hashlib.sha256(content).hexdigest(),
            system_id=2107,
            channel_key=KEY,
        )
    data = linked()
    data["System"]["system_id"] = 9068
    with pytest.raises(ValueError):
        review(data)
