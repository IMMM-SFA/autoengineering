"""Sealed solar inputs replay offline with role, clock and segment checks."""

import json
import socket
import subprocess
from pathlib import Path

import pytest

from autoengineering.campaign.serialization import canonical_json, digest
from examples.utility import solar_inputs as module
from examples.utility.solar_partitions import prepare
from test_utility_solar_partitions import fixture


def prepared(tmp_path, **kwargs):
    plan, rows, public, private = fixture(tmp_path, **kwargs)
    manifest = prepare(plan, rows, public, private)
    return plan, public, private, manifest


def args(manifest):
    return dict(
        expected_manifest_digest=digest(manifest),
        expected_preparer_sources=manifest["preparer_sources"],
    )


def overwrite(root, name, value):
    (root / name).write_bytes(canonical_json(value).encode())


def read(root, name):
    return json.loads((root / name).read_text())


def seal_file(public, name, value):
    overwrite(public, name, value)
    manifest = read(public, "manifest.json")
    manifest["files"][name] = digest(value)
    overwrite(public, "manifest.json", manifest)
    return manifest


def test_development_reader_never_opens_reserved_or_sources_and_returns_immutable_data(
    tmp_path, monkeypatch
):
    _, public, private, manifest = prepared(tmp_path, missing_ac=(5,))
    private.rename(tmp_path / "unavailable-reserved")
    original = module.read_bytes
    opened = []

    def scoped(root, ref, **kwargs):
        assert Path(root) == public
        opened.append(ref.path)
        return original(root, ref, **kwargs)

    def forbidden(*a, **kw):
        pytest.fail("input reader attempted process/network")

    monkeypatch.setattr(module, "read_bytes", scoped)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    result = module.read_development(public, **args(manifest))
    assert opened == ["manifest.json", "forcing.json", "fitting.json", "selection.json"]
    assert result.qualification == "not_admitted" and result.scope == "development"
    assert result.labels["fitting"].score_mask[4:8] == (True, False, True, True)
    assert result.forcing.segment_id == (0,) * 12
    with pytest.raises(TypeError):
        result.labels["new"] = result.labels["fitting"]
    assert module.SolarInputs.from_json(result.to_json()) == result


def test_reserved_reader_replays_full_prefix_and_only_confirmation_labels(tmp_path):
    _, public, private, manifest = prepared(tmp_path)
    result = module.read_reserved(public, private, **args(manifest))
    assert len(result.forcing.start) == 16
    assert result.labels["confirmation"].score_mask == (False,) * 12 + (True,) * 4
    assert result.labels["confirmation"].ac_kw[:12] == (None,) * 12
    assert result.qualification == "not_admitted"


def test_changed_bytes_refuse_without_any_repair_or_private_fallback(tmp_path):
    _, public, private, manifest = prepared(tmp_path)
    path = public / "forcing.json"
    path.write_bytes(path.read_bytes() + b" ")
    before = {p.name: p.read_bytes() for p in public.iterdir()}
    with pytest.raises(ValueError) as observed:
        module.read_development(public, **args(manifest))
    assert str(observed.value) == "solar development input verification failed"
    assert observed.value.__cause__ is observed.value.__context__ is None
    assert {p.name: p.read_bytes() for p in public.iterdir()} == before


def test_resealed_warmup_label_is_semantically_refused(tmp_path):
    _, public, private, manifest = prepared(tmp_path)
    labels = read(public, "fitting.json")
    labels["score_mask"][0] = True
    labels["ac_kw"][0] = 2
    labels["energy_kwh"][0] = 2 / 12
    manifest = seal_file(public, "fitting.json", labels)
    with pytest.raises(ValueError):
        module.read_development(public, **args(manifest))


def test_resealed_invalid_driver_segment_is_refused(tmp_path):
    _, public, private, manifest = prepared(tmp_path, missing_driver=(6,))
    forcing = read(public, "forcing.json")
    forcing["segment_id"][7] = 0
    manifest = seal_file(public, "forcing.json", forcing)
    with pytest.raises(ValueError):
        module.read_development(public, **args(manifest))


def test_resealed_reserved_prefix_cannot_change_development_inputs(tmp_path):
    _, public, private, manifest = prepared(tmp_path)
    forcing = read(private, "forcing.json")
    forcing["temperature_c"][0] += 1
    overwrite(private, "forcing.json", forcing)
    saved = read(private, "manifest.json")
    saved["files"]["forcing.json"] = digest(forcing)
    overwrite(private, "manifest.json", saved)
    manifest["private_bundle_digest"] = digest(saved)
    overwrite(public, "manifest.json", manifest)
    with pytest.raises(ValueError):
        module.read_reserved(public, private, **args(manifest))


def test_wrong_source_pins_refuse_before_column_reads(tmp_path, monkeypatch):
    _, public, private, manifest = prepared(tmp_path)
    original = module._read

    def metadata_only(root, name, *a, **kwargs):
        assert name == "manifest.json"
        return original(root, name, *a, **kwargs)

    monkeypatch.setattr(module, "_read", metadata_only)
    pins = dict(manifest["preparer_sources"])
    pins["alignment"] = "0" * 64
    with pytest.raises(ValueError):
        module.read_development(
            public, expected_manifest_digest=digest(manifest), expected_preparer_sources=pins
        )


def test_no_reader_can_promote_preparation_to_admitted(tmp_path):
    _, public, private, manifest = prepared(tmp_path)
    manifest["scientific_adapter_admitted"] = True
    overwrite(public, "manifest.json", manifest)
    with pytest.raises(ValueError):
        module.read_development(public, **args(manifest))


def test_uncommitted_preparation_is_not_recovered_by_reexecuting(tmp_path):
    _, public, private, manifest = prepared(tmp_path)
    (public / "manifest.json").unlink()
    with pytest.raises(ValueError):
        module.read_development(public, **args(manifest))
    assert not (public / "manifest.json").exists()
