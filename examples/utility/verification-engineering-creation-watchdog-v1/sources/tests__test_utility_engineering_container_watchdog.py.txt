"""Owner-pipe EOF/deadline cleanup uses exact acknowledged ownership only."""

from copy import deepcopy
import json
import os
import time
from types import SimpleNamespace

import pytest

from autoengineering.campaign.serialization import canonical_json
from examples.utility import engineering_container_runtime as owner
from examples.utility import engineering_container_watchdog as watchdog
from test_utility_engineering_container_runtime import setup, H


def prepared(tmp_path, monkeypatch, mode):
    runtime, grant, _, pin = setup(monkeypatch)
    api = runtime.api
    nonce = "a" * 32
    name = "ae-coupled-load-" + nonce
    config = owner.configuration(nonce, pin, grant.digest)
    api.created = True
    api.config = deepcopy(config)
    api.name = name
    if mode == "done":
        api.deleted = True
    now = time.monotonic()
    plan = {
        "schema": "utility-coupled-watchdog-plan-v1",
        "container_id": H,
        "nonce": nonce,
        "grant_digest": grant.digest,
        "packet_sha256": pin,
        "name": name,
        "configuration": config,
        "endpoint": "/explicit/socket",
        "api_version": "1.56",
        "server_digest": api.profile.server_digest,
        "api_profile_digest": api.identity,
        "owner_source_digest": owner.source_identity(),
        "watchdog_source_digest": watchdog.source_identity(),
        "active_deadline": now - 0.01 if mode == "deadline" else now + 2,
        "deadline": now + 3,
    }
    (tmp_path / "watchdog-plan.json").write_text(canonical_json(plan))
    monkeypatch.setattr(watchdog, "GuestDaemonAPI", lambda *a, **kw: api)
    return api


@pytest.mark.parametrize("mode", ["lost", "deadline", "done"])
def test_original_container_cleaned_on_eof_or_deadline(tmp_path, monkeypatch, mode):
    api = prepared(tmp_path, monkeypatch, mode)
    # Ready requires the original container. For normal finish, make the first
    # readiness inspection visible and the later cleanup inspection absent.
    if mode == "done":
        api.deleted = False
        original = api.inspect
        calls = []

        def inspect(*a, **kw):
            if calls:
                api.deleted = True
            calls.append(1)
            return original(*a, **kw)

        monkeypatch.setattr(api, "inspect", inspect)
    read_fd, write_fd = os.pipe()
    if mode == "done":
        os.write(write_fd, b"D")
    os.close(write_fd)
    try:
        watchdog.run_watchdog(tmp_path, read_fd)
    finally:
        os.close(read_fd)
    outcome = json.loads((tmp_path / "watchdog-outcome.json").read_bytes())
    assert outcome["absent"] is True and api.deleted
    assert (
        outcome["reason"]
        == {"lost": "owner_lost", "deadline": "deadline", "done": "owner_done"}[mode]
    )
    assert outcome["delete_intended"] is (mode != "done")


def test_foreign_original_labels_refuse_cleanup(tmp_path, monkeypatch):
    api = prepared(tmp_path, monkeypatch, "lost")
    api.config["Labels"]["org.autoengineering.grant"] = "2" * 64
    read_fd, write_fd = os.pipe()
    os.close(write_fd)
    try:
        with pytest.raises(ValueError):
            watchdog.run_watchdog(tmp_path, read_fd)
    finally:
        os.close(read_fd)
    assert not api.deleted and not (tmp_path / "watchdog-ready.json").exists()


def test_dead_watchdog_revokes_score_authority_and_retains_exact_process(tmp_path):
    supervisor = watchdog.CoupledWatchdog.__new__(watchdog.CoupledWatchdog)
    supervisor.root = tmp_path
    supervisor.plan_digest = H
    supervisor.process = SimpleNamespace(pid=123, poll=lambda: -9)
    with pytest.raises(ValueError, match="authority revoked"):
        supervisor.check_alive()
    loss = json.loads((tmp_path / "watchdog-loss.json").read_bytes())
    assert loss["watchdog_pid"] == 123 and loss["exit_code"] == -9
    assert loss["score_authority_revoked"] is True
    assert loss["automatic_retry_allowed"] is False


@pytest.mark.parametrize("mode", ["no_create", "unbound_created", "uncertain", "foreign"])
def test_prospective_name_survives_owner_loss_without_inventing_acknowledgement(
    tmp_path, monkeypatch, mode
):
    api = prepared(tmp_path, monkeypatch, "deadline" if mode == "uncertain" else "lost")
    plan = json.loads((tmp_path / "watchdog-plan.json").read_bytes())
    plan.update(schema="utility-coupled-watchdog-plan-v2", container_id=None)
    (tmp_path / "watchdog-plan.json").write_text(canonical_json(plan))
    api.created = False
    if mode != "no_create":
        (tmp_path / "create-intent.json").write_text("{}")
    original = api._request
    lookups = []

    def request(method, path, **kwargs):
        if method == "GET":
            lookups.append(1)
            if len(lookups) == 2 and mode in ("unbound_created", "foreign"):
                api.created = True
                if mode == "foreign":
                    api.config["Labels"]["org.autoengineering.grant"] = "2" * 64
        return original(method, path, **kwargs)

    monkeypatch.setattr(api, "_request", request)
    read_fd, write_fd = os.pipe()
    os.close(write_fd)
    try:
        if mode in ("uncertain", "foreign"):
            with pytest.raises(ValueError):
                watchdog.run_watchdog(tmp_path, read_fd)
        else:
            watchdog.run_watchdog(tmp_path, read_fd)
    finally:
        os.close(read_fd)
    if mode == "foreign":
        assert not api.deleted
    else:
        outcome = json.loads((tmp_path / "watchdog-outcome.json").read_bytes())
        assert outcome["absent"] is (mode != "uncertain")
        assert outcome["unacknowledged_creation_unverified"] is (mode == "uncertain")
        assert api.deleted is (mode == "unbound_created")
