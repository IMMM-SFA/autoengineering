"""Trusted metadata never selects another model or enters provider context."""

import json

import pytest

from autoengineering.agents.hosts.model_catalog import read_model_catalog, validate_model_catalog


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"x" * 65537,
        b'{"models":[],"models":[]}',
        b'{"tokens":{}}',
        b'{"models":[]}',
        b'{"models":[{"slug":"other"}]}',
        b'{"models":[{"slug":"chosen"},{"slug":"other"}]}',
    ],
)
def test_catalog_refuses_invalid_or_expanded_selection(raw):
    with pytest.raises((ValueError, UnicodeError)):
        validate_model_catalog(raw, "chosen")


def test_catalog_reads_only_named_regular_bounded_file(tmp_path):
    path = tmp_path / "catalog.json"
    raw = json.dumps({"models": [{"slug": "chosen", "description": "metadata"}]}).encode()
    path.write_bytes(raw)
    assert read_model_catalog(path, "chosen") == raw
    alias = tmp_path / "alias.json"
    alias.symlink_to(path)
    with pytest.raises(ValueError):
        read_model_catalog(alias, "chosen")
    path.write_bytes(b"x" * 65537)
    with pytest.raises(ValueError, match="limit"):
        read_model_catalog(path, "chosen")
