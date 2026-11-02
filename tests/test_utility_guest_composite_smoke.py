"""The actual authored-chain controller refuses invalid requests before any API."""

from pathlib import Path

import pytest

from autoengineering.campaign.serialization import digest
from examples.utility import guest_composite_smoke as module


def control(root):
    return {
        "schema": "utility-authored-guest-composite-smoke-v1",
        "scope_digest": digest(str(root)),
        "sources": module.controller_sources(),
        "max_container_creations": 2,
        "max_container_starts": 2,
        "inference_starts_allowed": 1,
        "scoring_starts_allowed": 1,
        "fitting_starts_allowed": 0,
        "automatic_retries": 0,
        "parent_active_seconds_reserved": 94,
        "runtime_qualified": False,
    }


def guarded(monkeypatch):
    def forbidden(*a, **kw):
        pytest.fail("refusal constructed a runtime or read execution inputs")

    monkeypatch.setattr(module, "context", forbidden)


@pytest.mark.parametrize(
    "change",
    [
        {"sources": {}},
        {"scope_digest": "0" * 64},
        {"max_container_starts": 0},
        {"max_container_creations": True},
        {"automatic_retries": 1},
        {"scoring_starts_allowed": 0},
        {"runtime_qualified": True},
    ],
)
def test_changed_controller_scope_or_caps_refuse_before_runtime(tmp_path, monkeypatch, change):
    guarded(monkeypatch)
    request = control(tmp_path)
    request.update(change)
    module.fixture.save(tmp_path, "composite-request.json", request)
    with pytest.raises(ValueError):
        module.execute(tmp_path, expected_digest=digest(request))
    assert not (tmp_path / "composite-execution-intent.json").exists()


def test_wrong_request_identity_refuses_before_runtime(tmp_path, monkeypatch):
    guarded(monkeypatch)
    request = control(tmp_path)
    module.fixture.save(tmp_path, "composite-request.json", request)
    with pytest.raises(ValueError):
        module.execute(tmp_path, expected_digest="0" * 64)


def test_consumed_request_never_reconstructs_or_restarts_runtime(tmp_path, monkeypatch):
    guarded(monkeypatch)
    request = control(tmp_path)
    module.fixture.save(tmp_path, "composite-request.json", request)
    Path(tmp_path / "composite-execution-intent.json").write_text("{}")
    with pytest.raises(module.StoreError, match="consumed"):
        module.execute(tmp_path, expected_digest=digest(request))
