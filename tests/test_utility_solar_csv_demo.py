"""Bundled example keeps source acquisition after custody claims and remains unadmitted."""

import subprocess
import socket

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import solar_csv_demo as demo
from examples.utility.solar_inputs import read_development, read_reserved


def test_bundled_example_prepares_then_readers_replay_without_execution(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        pytest.fail("authored CSV example attempted network or a process")

    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    root = tmp_path / "new"
    opened = []
    original = demo.resource

    def resource(name):
        if name == demo.SOURCE_RESOURCE:
            assert (root / "public/preparation-claim.json").exists()
            assert (root / "reserved/preparation-claim.json").exists()
        opened.append(name)
        return original(name)

    monkeypatch.setattr(demo, "resource", resource)
    manifest = demo.prepare_demo(root)
    assert opened == [demo.PLAN_RESOURCE, demo.SOURCE_RESOURCE]
    kwargs = dict(
        expected_manifest_digest=digest(manifest),
        expected_preparer_sources=manifest["preparer_sources"],
    )
    public = read_development(root / "public", **kwargs)
    reserved = read_reserved(root / "public", root / "reserved", **kwargs)
    assert len(public.forcing.start) == 12 and len(reserved.forcing.start) == 16
    assert sum(public.labels["fitting"].score_mask) == 4
    assert sum(reserved.labels["confirmation"].score_mask) == 4
    assert public.qualification == reserved.qualification == "not_admitted"
    with pytest.raises(ValueError, match="absent"):
        demo.prepare_demo(root)
    assert opened == [demo.PLAN_RESOURCE, demo.SOURCE_RESOURCE]


def test_corrupt_bundled_source_preserves_consumed_claims(tmp_path, monkeypatch):
    original = demo.resource

    def resource(name):
        value = original(name)
        if name == demo.SOURCE_RESOURCE:
            value["csv_utf8"] += "changed"
        return value

    monkeypatch.setattr(demo, "resource", resource)
    root = tmp_path / "failed"
    with pytest.raises(ValueError):
        demo.prepare_demo(root)
    assert (root / "public/preparation-claim.json").exists()
    assert (root / "reserved/preparation-claim.json").exists()
    assert not (root / "public/manifest.json").exists()
    with pytest.raises(ValueError):
        demo.prepare_demo(root)
