"""Consumed development requests retain failures and reserve calls before dispatch."""

from types import SimpleNamespace

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import wind_hourly_check as check


def prepared(tmp_path, monkeypatch, physical):
    root = tmp_path / "run"
    root.mkdir(mode=0o700)
    request = dict(
        scope_digest=digest(str(root)),
        pins={"authored": True},
        assumptions=check.ASSUMPTIONS,
        policy=check.POLICY,
        profile_identity="a" * 64,
        wake_calls_cap=2,
        curve_reference_calls_cap=1,
        automatic_retries=0,
        elapsed_application_cap_seconds=120.0,
    )
    check.save(root, "request.json", request)
    monkeypatch.setattr(check, "pins", lambda: {"authored": True})
    profile = SimpleNamespace(
        identity="a" * 64,
        geometry=SimpleNamespace(baseline={}),
        context=lambda *a: SimpleNamespace(),
        physical=physical,
    )
    monkeypatch.setattr(check, "load_task", lambda r: profile)
    return root, request


def test_failure_preserves_pre_dispatch_reservation_and_cannot_retry(tmp_path, monkeypatch):
    calls = []

    def physical(*args):
        calls.append(1)
        assert (root / "consumed.json").exists()
        assert check.read(root, "0-intent.json")["wake_calls_reserved"] == 1
        raise ValueError("authored physical failure")

    root, request = prepared(tmp_path, monkeypatch, physical)
    with pytest.raises(ValueError, match="authored physical failure"):
        check.execute(root, digest(request))
    failure = check.read(root, "failed.json")
    assert failure["wake_calls_reserved"] == 1
    assert failure["curve_reference_calls_reserved"] == 0
    assert failure["completed_receipts"] == 0
    assert not failure["automatic_retry_allowed"]
    with pytest.raises(FileExistsError):
        check.execute(root, digest(request))
    assert calls == [1]


@pytest.mark.parametrize("change", ["digest", "sources", "caps", "assumptions", "identity"])
def test_invalid_scope_refuses_without_consuming_or_model_call(tmp_path, monkeypatch, change):
    def denied(*args):
        raise AssertionError("invalid request reached physical call")

    root, request = prepared(tmp_path, monkeypatch, denied)
    if change == "sources":
        monkeypatch.setattr(check, "pins", lambda: {"changed": True})
    elif change == "caps":
        request["wake_calls_cap"] = 3
    elif change == "assumptions":
        request["assumptions"] = {}
    elif change == "identity":
        request["profile_identity"] = "c" * 64
    if change in ("caps", "assumptions", "identity"):
        # Isolated authored request replacement occurs before any consumption.
        (root / "request.json").unlink()
        check.save(root, "request.json", request)
    with pytest.raises(ValueError):
        check.execute(root, "0" * 64 if change == "digest" else digest(request))
    assert not (root / "consumed.json").exists()
