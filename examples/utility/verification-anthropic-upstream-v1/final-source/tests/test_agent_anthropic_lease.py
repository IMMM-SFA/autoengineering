"""Explicit API key reads use authored files only, never real auth caches."""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import time

import pytest

from autoengineering.agents.hosts import anthropic_lease as lease
from autoengineering.agents.hosts import anthropic_worker as worker

KEY = "authored-fixture-raw-key-not-real"


def setup(tmp_path):
    tmp_path.chmod(0o700)
    for name in ("auth", "client", "leases"):
        (tmp_path / name).mkdir(mode=0o700)
    source = tmp_path / "auth/raw-key"
    source.write_text(KEY + "\n")
    source.chmod(0o600)
    options = {
        "lease_id": "lease-one",
        "workspace_id": "wrkspc_fixture",
        "not_after_utc": (datetime.now(timezone.utc) + timedelta(minutes=10)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "client_read_roots": (tmp_path / "client",),
    }
    return source, tmp_path / "leases/one", options


def test_raw_key_source_remains_unchanged_and_only_private_lease_contains_key(tmp_path):
    source, destination, options = setup(tmp_path)
    before = source.read_bytes()
    result = lease.prepare_api_lease(source, destination, **options)
    assert source.read_bytes() == before
    value = json.loads(result.credential_path.read_text())
    assert value["api_key"] == KEY and value["kind"] == "anthropic-api-key"
    assert result.credential_path.stat().st_mode & 0o077 == 0
    receipt = result.receipt()
    assert receipt["authentication_mode"] == "api"
    assert (
        receipt["server_validity_verified"] is False
        and receipt["actual_key_expiry_verified"] is False
    )
    assert KEY not in repr(receipt) and hashlib.sha256(KEY.encode()).hexdigest() not in repr(
        receipt
    )
    support = worker.load_support(
        hashlib.sha256(
            Path(worker.__file__).with_name("subscription_worker.py").read_bytes()
        ).hexdigest()
    )
    policy = {
        "lease_id": "lease-one",
        "credential_path": str(result.credential_path),
        "client_read_roots": [str(tmp_path / "client")],
        "deadline_monotonic": time.monotonic() + 2,
    }
    assert worker.credential(policy, support)["api_key"] == KEY


def test_repeated_or_partial_destination_cannot_read_a_key_again(tmp_path, monkeypatch):
    source, destination, options = setup(tmp_path)
    lease.prepare_api_lease(source, destination, **options)
    monkeypatch.setattr(lease, "private_read", lambda *_: pytest.fail("duplicate key read"))
    with pytest.raises(lease.ApiLeaseError, match="destination_reserved"):
        lease.prepare_api_lease(source, destination, **options)
    partial = tmp_path / "leases/partial"
    partial.mkdir(mode=0o700)
    with pytest.raises(lease.ApiLeaseError, match="destination_reserved"):
        lease.prepare_api_lease(source, partial, **options)


@pytest.mark.parametrize(
    "problem",
    [
        "expiry",
        "workspace",
        "source-client",
        "destination-client",
        "source-git",
        "destination-git",
        "public-key",
        "symlink",
        "multiline",
    ],
)
def test_bad_scopes_and_sources_refuse_without_exposing_key(tmp_path, problem):
    source, destination, options = setup(tmp_path)
    if problem == "expiry":
        options["not_after_utc"] = "2000-01-01T00:00:00Z"
    elif problem == "workspace":
        options["workspace_id"] = "unqualified"
    elif problem == "source-client":
        options["client_read_roots"] = (tmp_path / "auth",)
    elif problem == "destination-client":
        options["client_read_roots"] = (tmp_path / "leases",)
    elif problem == "source-git":
        (tmp_path / "auth/.git").mkdir()
    elif problem == "destination-git":
        (tmp_path / "leases/.git").mkdir()
    elif problem == "public-key":
        source.chmod(0o644)
    elif problem == "symlink":
        original = source.with_name("original")
        source.rename(original)
        source.symlink_to(original)
    else:
        source.write_text(KEY + "\nsecond-line")
    with pytest.raises(lease.ApiLeaseError) as error:
        lease.prepare_api_lease(source, destination, **options)
    assert KEY not in str(error.value)
    assert not (destination / "lease.json").exists()


def test_source_change_after_read_is_not_committed_as_a_lease(tmp_path, monkeypatch):
    source, destination, options = setup(tmp_path)
    original = lease.private_read

    def changed(path, limit):
        value = original(path, limit)
        path.write_text("different fixture")
        return value

    monkeypatch.setattr(lease, "private_read", changed)
    with pytest.raises(lease.ApiLeaseError, match="source_changed"):
        lease.prepare_api_lease(source, destination, **options)
    assert not (destination / "lease.json").exists()
    with pytest.raises(lease.ApiLeaseError, match="destination_reserved"):
        lease.prepare_api_lease(source, destination, **options)


def test_fifo_source_is_refused_without_reading(tmp_path, monkeypatch):
    source, destination, options = setup(tmp_path)
    source.unlink()
    os.mkfifo(source, 0o600)
    monkeypatch.setattr(lease, "private_read", lambda *_: pytest.fail("FIFO read attempted"))
    with pytest.raises(lease.ApiLeaseError, match="source_regular_file"):
        lease.prepare_api_lease(source, destination, **options)
    assert not (destination / "lease.json").exists()


def test_private_reader_opens_leaf_nonblocking_before_regular_file_check(tmp_path, monkeypatch):
    source, _, _ = setup(tmp_path)
    original = os.open
    observed = []

    def checked_open(path, flags, *args, **kwargs):
        if path == source.name:
            observed.append(flags)
            assert flags & os.O_NONBLOCK and flags & os.O_NOFOLLOW
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", checked_open)
    assert lease.private_read(source, 4097) == (KEY + "\n").encode()
    assert len(observed) == 1
