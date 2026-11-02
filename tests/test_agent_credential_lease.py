"""Explicit synthetic managed-cache preparation. Never open an existing cache."""

from datetime import datetime, timedelta, timezone
import json

import pytest

from autoengineering.agents.hosts.credential_lease import (
    CredentialPreparationError,
    prepare_subscription_lease,
    recover_prepared_subscription_lease,
)

ACCESS = "synthetic-access-for-one-owned-request"
REFRESH = "synthetic-refresh-must-never-leave-source"
ID_TOKEN = "synthetic-id-must-never-leave-source"
ACCOUNT = "synthetic-account"


def fixture(tmp_path):
    tmp_path.chmod(0o700)
    source_dir = tmp_path / "source"
    source_dir.mkdir(mode=0o700)
    client = tmp_path / "client"
    client.mkdir(mode=0o700)
    source = source_dir / "auth.json"
    cache = {
        "auth_mode": "chatgpt",
        "OPENAI_API_KEY": None,
        "last_refresh": datetime.now(timezone.utc).isoformat(),
        "tokens": {
            "access_token": ACCESS,
            "refresh_token": REFRESH,
            "id_token": ID_TOKEN,
            "account_id": ACCOUNT,
        },
    }
    source.write_text(json.dumps(cache))
    source.chmod(0o600)
    options = {
        "lease_id": "lease-one",
        "expected_account_id": ACCOUNT,
        "not_after_utc": (datetime.now(timezone.utc) + timedelta(minutes=5)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "client_roots": (client,),
    }
    return source, cache, options


def test_prepare_keeps_source_unchanged_and_only_copies_access_token_to_private_lease(tmp_path):
    source, _, options = fixture(tmp_path)
    before = source.read_bytes()
    prepared = prepare_subscription_lease(source, tmp_path / "lease", **options)
    assert source.read_bytes() == before
    lease = json.loads(prepared.credential_path.read_text())
    assert lease["bearer_token"] == ACCESS and lease["account_id"] == ACCOUNT
    assert prepared.credential_path.stat().st_mode & 0o777 == 0o600
    assert prepared.directory.stat().st_mode & 0o777 == 0o700
    receipt = (prepared.directory / "prepared.json").read_bytes()
    assert all(value.encode() not in receipt for value in (ACCESS, REFRESH, ID_TOKEN, ACCOUNT))
    assert REFRESH.encode() not in prepared.credential_path.read_bytes()
    assert ID_TOKEN.encode() not in prepared.credential_path.read_bytes()
    assert json.loads(receipt) == prepared.receipt()
    assert prepared.receipt()["refresh_performed"] is False
    assert prepared.receipt()["server_validity_verified"] is False
    source.unlink()
    with pytest.raises(CredentialPreparationError, match="destination_exists"):
        prepare_subscription_lease(source, tmp_path / "lease", **options)
    assert receipt == (prepared.directory / "prepared.json").read_bytes()


@pytest.mark.parametrize(
    "problem",
    [
        "mode",
        "api-key",
        "external-tokens",
        "unknown",
        "unknown-token",
        "no-refresh",
        "account",
        "stale",
        "future-refresh",
        "naive-refresh",
        "long-expiry",
        "expired",
        "bad-access",
        "duplicate",
        "not-object",
        "permissions",
        "symlink",
        "hardlink",
    ],
)
def test_bad_or_stale_sources_fail_without_secret_diagnostics_or_lease(tmp_path, problem):
    source, cache, options = fixture(tmp_path)
    if problem == "mode":
        cache["auth_mode"] = "apikey"
    elif problem == "api-key":
        cache["OPENAI_API_KEY"] = "synthetic-api-key"
    elif problem == "external-tokens":
        cache["auth_mode"] = "chatgptAuthTokens"
    elif problem == "unknown":
        cache["unexpected_secret"] = REFRESH
    elif problem == "unknown-token":
        cache["tokens"]["unexpected"] = REFRESH
    elif problem == "no-refresh":
        cache["tokens"].pop("refresh_token")
    elif problem == "account":
        options["expected_account_id"] = "different-account"
    elif problem == "stale":
        cache["last_refresh"] = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    elif problem == "future-refresh":
        cache["last_refresh"] = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    elif problem == "naive-refresh":
        cache["last_refresh"] = "2026-10-26T00:00:00"
    elif problem == "long-expiry":
        options["not_after_utc"] = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    elif problem == "expired":
        options["not_after_utc"] = "2000-01-01T00:00:00Z"
    elif problem == "bad-access":
        cache["tokens"]["access_token"] = ACCESS + "\r\nheader"
    source.write_text(json.dumps(cache))
    if problem == "duplicate":
        source.write_text('{"auth_mode":"chatgpt","auth_mode":"' + REFRESH + '"}')
    elif problem == "not-object":
        source.write_text('["' + REFRESH + '"]')
    elif problem == "permissions":
        source.chmod(0o644)
    elif problem == "symlink":
        original = source.with_name("other.json")
        source.rename(original)
        source.symlink_to(original)
    elif problem == "hardlink":
        import os

        os.link(source, source.with_name("alias.json"))
    before = source.read_bytes()
    with pytest.raises(CredentialPreparationError) as exc:
        prepare_subscription_lease(source, tmp_path / "lease", **options)
    assert all(value not in str(exc.value) for value in (ACCESS, REFRESH, ID_TOKEN, ACCOUNT))
    assert source.read_bytes() == before
    assert not (tmp_path / "lease/lease.json").exists()


def test_source_rotation_during_read_is_rejected(tmp_path, monkeypatch):
    import autoengineering.agents.hosts.credential_lease as module

    source, cache, options = fixture(tmp_path)
    real_read = module.private_read

    def rotated(path, limit):
        raw = real_read(path, limit)
        cache["tokens"]["access_token"] = "replacement-synthetic-access"
        replacement = source.with_name("replacement.json")
        replacement.write_text(json.dumps(cache))
        replacement.chmod(0o600)
        replacement.replace(source)
        return raw

    monkeypatch.setattr(module, "private_read", rotated)
    with pytest.raises(CredentialPreparationError, match="source_changed"):
        prepare_subscription_lease(source, tmp_path / "lease", **options)
    assert not (tmp_path / "lease/lease.json").exists()


@pytest.mark.parametrize(
    "kind", ["source-in-client", "destination-in-client", "git-checkout", "traversal"]
)
def test_prepare_refuses_client_or_committable_destinations(tmp_path, kind):
    source, _, options = fixture(tmp_path)
    destination = tmp_path / "lease"
    if kind == "source-in-client":
        options["client_roots"] = (source.parent,)
    elif kind == "destination-in-client":
        destination = tmp_path / "client/lease"
    elif kind == "git-checkout":
        (tmp_path / ".git").write_text("gitdir: synthetic-checkout")
    else:
        destination = tmp_path / "source/../client/lease"
    with pytest.raises(CredentialPreparationError, match="source_scope"):
        prepare_subscription_lease(source, destination, **options)
    assert not (destination / "lease.json").exists()


@pytest.mark.parametrize("problem", [None, "missing-receipt", "account", "expiry", "foreign-scope"])
def test_prepared_recovery_never_reopens_source_or_changes_lease(tmp_path, problem):
    import shutil

    source, _, options = fixture(tmp_path)
    lease = prepare_subscription_lease(source, tmp_path / "lease", **options)
    source.unlink()
    if problem == "missing-receipt":
        (lease.directory / "prepared.json").unlink()
    elif problem == "account":
        options["expected_account_id"] = "wrong-account"
    elif problem == "expiry":
        options["not_after_utc"] = "2000-01-01T00:00:00Z"
    elif problem == "foreign-scope":
        shutil.copytree(lease.directory, tmp_path / "foreign")
        lease = type(lease)(tmp_path / "foreign", lease.lease_id, lease.not_after_utc)
    before = {p.name: p.read_bytes() for p in lease.directory.iterdir()}
    if problem is None:
        assert recover_prepared_subscription_lease(lease.directory, **options) == lease
    else:
        with pytest.raises(CredentialPreparationError):
            recover_prepared_subscription_lease(lease.directory, **options)
    assert before == {p.name: p.read_bytes() for p in lease.directory.iterdir()}
